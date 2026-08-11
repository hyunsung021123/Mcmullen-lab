"""math_dialogue.py — 여러 수학 Codex 세션을 위한 로컬 비동기 우편함.

이 모듈은 **토론 운반 계층**일 뿐 수학적 판정자가 아니다. 저장된 메시지, 증명 초안,
반례 후보, 합성문은 전부 기본적으로 UNASSESSED 이며 ``om_core``, ``falsify``,
``process_verifier`` 또는 재현 가능한 evidence를 거치기 전에는 어떤 권한도 없다.

여러 Codex heartbeat가 같은 checkout에서 이 CLI를 호출하는 사용례를 겨냥한다. SQLite의
``BEGIN IMMEDIATE`` 트랜잭션으로 한 메시지를 두 세션이 동시에 선점하지 못하게 하고,
라운드·메시지 수·TTL·lease 만료로 무한 대화를 막는다. 런타임 DB는 기본적으로
``.math_dialogue/dialogue.sqlite3``에 있으며 Git 공유 상태가 아니다.

빠른 시작::

    python math_dialogue.py init
    python math_dialogue.py register --agent explorer --role "구성·추측 제안"
    python math_dialogue.py register --agent skeptic --role "반례·가정 감사"
    python math_dialogue.py topic --title "작은 범위의 접합 보조정리" --created-by human
    python math_dialogue.py post --topic T-... --sender human --to explorer \
        --kind QUESTION --body "가장 싼 반증 시험을 제안하라."
    python math_dialogue.py claim --agent explorer

실제 Codex 호출 없이 프로토콜을 검사하려면 ``python math_dialogue.py selftest``를 쓴다.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB = Path(os.environ.get(
    "MCMULLEN_MATH_DIALOGUE_DB",
    Path(__file__).resolve().parent / ".math_dialogue" / "dialogue.sqlite3",
))

KINDS = {
    "QUESTION",
    "DIRECTION",
    "CONJECTURE",
    "PROOF_SKETCH",
    "COUNTEREXAMPLE_CANDIDATE",
    "COMPUTATIONAL_CLAIM",
    "CRITIQUE",
    "SYNTHESIS",
}
GRADES = {
    "UNASSESSED",
    "SPECULATION",
    "CONJECTURE",
    "NUMERICAL",
    "VERIFIED",
    "PROVEN",
}
MESSAGE_STATES = {"queued", "leased", "done", "expired"}
TOPIC_STATES = {"open", "closed"}


def _now() -> float:
    return time.time()


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _topic_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"T-{stamp}-{uuid.uuid4().hex[:6]}"


def _connect(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    # WAL은 같은 로컬 checkout의 여러 heartbeat가 읽기/쓰기를 겹치는 경우를 위한 선택이다.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def _db(db_path: Path | str = DEFAULT_DB):
    """Commit or roll back a unit of work, then always release the DB file."""
    conn = _connect(db_path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path: Path | str = DEFAULT_DB) -> Path:
    path = Path(db_path)
    with _db(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_by TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('open', 'closed')),
                max_rounds INTEGER NOT NULL CHECK(max_rounds >= 1),
                max_messages INTEGER NOT NULL CHECK(max_messages >= 1),
                created_at REAL NOT NULL,
                closed_at REAL,
                close_reason TEXT,
                final_by TEXT,
                final_kind TEXT,
                final_grade TEXT,
                final_summary TEXT,
                final_evidence_refs TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL REFERENCES topics(id),
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL REFERENCES agents(name),
                kind TEXT NOT NULL,
                grade TEXT NOT NULL,
                body TEXT NOT NULL,
                evidence_refs TEXT NOT NULL DEFAULT '[]',
                parent_id INTEGER REFERENCES messages(id),
                round_no INTEGER NOT NULL CHECK(round_no >= 1),
                status TEXT NOT NULL CHECK(status IN ('queued', 'leased', 'done', 'expired')),
                lease_owner TEXT,
                lease_until REAL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                completed_at REAL
            );

            CREATE UNIQUE INDEX IF NOT EXISTS one_reply_per_message
                ON messages(parent_id) WHERE parent_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS inbox_order
                ON messages(recipient, status, created_at, id);
            CREATE INDEX IF NOT EXISTS topic_order
                ON messages(topic_id, id);
            """
        )
    return path


def register_agent(name: str, role: str, *, db_path: Path | str = DEFAULT_DB) -> None:
    if not name.strip() or not role.strip():
        raise ValueError("agent 이름과 role은 비어 있을 수 없음")
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute(
            """INSERT INTO agents(name, role, active, created_at) VALUES (?, ?, 1, ?)
               ON CONFLICT(name) DO UPDATE SET role=excluded.role, active=1""",
            (name.strip(), role.strip(), _now()),
        )


def create_topic(title: str, created_by: str, *, max_rounds: int = 6,
                 max_messages: int = 12, db_path: Path | str = DEFAULT_DB) -> str:
    if max_rounds < 1 or max_messages < 1:
        raise ValueError("max_rounds와 max_messages는 1 이상이어야 함")
    topic_id = _topic_id()
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute(
            """INSERT INTO topics
               (id, title, created_by, status, max_rounds, max_messages, created_at)
               VALUES (?, ?, ?, 'open', ?, ?, ?)""",
            (topic_id, title.strip(), created_by.strip(), max_rounds, max_messages, _now()),
        )
    return topic_id


def _validate_message(kind: str, grade: str, body: str, evidence_refs: list[str]) -> None:
    if kind not in KINDS:
        raise ValueError(f"kind는 다음 중 하나여야 함: {sorted(KINDS)}")
    if grade not in GRADES:
        raise ValueError(f"grade는 다음 중 하나여야 함: {sorted(GRADES)}")
    if not body.strip():
        raise ValueError("메시지 body는 비어 있을 수 없음")
    if not isinstance(evidence_refs, list) or not all(isinstance(x, str) for x in evidence_refs):
        raise ValueError("evidence_refs는 문자열 목록이어야 함")


def _evidence_refs(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("evidence_refs는 문자열 목록이어야 함")
    return value


def _post_in_tx(conn: sqlite3.Connection, *, topic_id: str, sender: str,
                recipient: str, kind: str, grade: str, body: str,
                evidence_refs: list[str], parent_id: int | None, round_no: int,
                ttl_seconds: int) -> int:
    _validate_message(kind, grade, body, evidence_refs)
    if ttl_seconds < 1:
        raise ValueError("ttl_seconds는 1 이상이어야 함")
    topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
    if topic is None:
        raise KeyError(f"존재하지 않는 topic: {topic_id}")
    if topic["status"] != "open":
        raise ValueError(f"topic {topic_id}은 닫혀 있음")
    agent = conn.execute(
        "SELECT active FROM agents WHERE name=?", (recipient,)
    ).fetchone()
    if agent is None or not agent["active"]:
        raise KeyError(f"활성 agent가 아님: {recipient}")
    count = conn.execute(
        "SELECT COUNT(*) AS n FROM messages WHERE topic_id=?", (topic_id,)
    ).fetchone()["n"]
    if count >= topic["max_messages"]:
        raise ValueError(f"topic {topic_id}의 max_messages에 도달함")
    if round_no > topic["max_rounds"]:
        raise ValueError(f"topic {topic_id}의 max_rounds를 초과함")
    now = _now()
    cur = conn.execute(
        """INSERT INTO messages
           (topic_id, sender, recipient, kind, grade, body, evidence_refs,
            parent_id, round_no, status, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)""",
        (topic_id, sender, recipient, kind, grade, body,
         json.dumps(evidence_refs, ensure_ascii=False), parent_id, round_no,
         now, now + ttl_seconds),
    )
    return int(cur.lastrowid)


def post_message(topic_id: str, sender: str, recipient: str, kind: str, body: str,
                 *, grade: str = "UNASSESSED", evidence_refs: list[str] | None = None,
                 ttl_seconds: int = 86400, db_path: Path | str = DEFAULT_DB) -> int:
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            message_id = _post_in_tx(
                conn, topic_id=topic_id, sender=sender, recipient=recipient,
                kind=kind, grade=grade, body=body,
                evidence_refs=evidence_refs or [], parent_id=None, round_no=1,
                ttl_seconds=ttl_seconds,
            )
            conn.commit()
            return message_id
        except Exception:
            conn.rollback()
            raise


def _message_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    out = dict(row)
    out["evidence_refs"] = json.loads(out["evidence_refs"])
    for key in ("created_at", "expires_at", "lease_until", "completed_at"):
        out[key] = _iso(out[key])
    return out


def claim_message(agent: str, *, lease_seconds: int = 900,
                  db_path: Path | str = DEFAULT_DB) -> dict[str, Any] | None:
    if lease_seconds < 1:
        raise ValueError("lease_seconds는 1 이상이어야 함")
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            now = _now()
            # 실패한 heartbeat의 lease는 다시 큐로, TTL이 지난 큐는 expired로 이동한다.
            conn.execute(
                """UPDATE messages SET status='queued', lease_owner=NULL, lease_until=NULL
                   WHERE status='leased' AND lease_until < ?""",
                (now,),
            )
            conn.execute(
                """UPDATE messages SET status='expired'
                   WHERE status='queued' AND expires_at < ?""",
                (now,),
            )
            row = conn.execute(
                """SELECT m.*, t.title AS topic_title
                   FROM messages m JOIN topics t ON t.id=m.topic_id
                   WHERE m.recipient=? AND m.status='queued' AND t.status='open'
                   ORDER BY m.created_at, m.id LIMIT 1""",
                (agent,),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            updated = conn.execute(
                """UPDATE messages SET status='leased', lease_owner=?, lease_until=?
                   WHERE id=? AND status='queued'""",
                (agent, now + lease_seconds, row["id"]),
            ).rowcount
            if updated != 1:
                raise RuntimeError("메시지 선점 경쟁을 해결하지 못함")
            claimed = conn.execute(
                """SELECT m.*, t.title AS topic_title
                   FROM messages m JOIN topics t ON t.id=m.topic_id WHERE m.id=?""",
                (row["id"],),
            ).fetchone()
            conn.commit()
            return _message_dict(claimed)
        except Exception:
            conn.rollback()
            raise


def submit_response(agent: str, message_id: int, response: dict[str, Any], *,
                    db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """선점한 메시지를 완료하고 선택적으로 다음 메시지 하나를 만든다.

    response 스키마::

        {"to": "skeptic", "kind": "CONJECTURE", "grade": "UNASSESSED",
         "body": "...", "evidence_refs": [], "close_topic": false,
         "close_reason": ""}

    ``close_topic=true``이면 다음 메시지를 만들지 않는다. 재시도 시 parent_id의 unique
    index와 완료 상태를 이용해 같은 응답을 두 번 만들지 않는 idempotent 결과를 돌려준다.
    """
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            msg = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
            if msg is None:
                raise KeyError(f"존재하지 않는 message: {message_id}")
            if msg["status"] == "done":
                child = conn.execute(
                    "SELECT id FROM messages WHERE parent_id=?", (message_id,)
                ).fetchone()
                conn.commit()
                return {"status": "already_submitted",
                        "reply_message_id": child["id"] if child else None}
            if msg["status"] != "leased" or msg["lease_owner"] != agent:
                raise ValueError(f"message {message_id}은 {agent}가 선점한 작업이 아님")

            topic = conn.execute("SELECT * FROM topics WHERE id=?", (msg["topic_id"],)).fetchone()
            if topic["status"] == "closed":
                conn.execute(
                    """UPDATE messages SET status='done', completed_at=?,
                       lease_owner=NULL, lease_until=NULL WHERE id=?""",
                    (_now(), message_id),
                )
                conn.commit()
                return {"status": "topic_already_closed", "reply_message_id": None,
                        "topic_closed": True, "stop_reason": topic["close_reason"]}
            close_topic = bool(response.get("close_topic", False))
            next_round = msg["round_no"] + 1
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM messages WHERE topic_id=?", (msg["topic_id"],)
            ).fetchone()["n"]
            stop_reason = None
            if next_round > topic["max_rounds"]:
                close_topic = True
                stop_reason = "max_rounds"
            elif count >= topic["max_messages"]:
                close_topic = True
                stop_reason = "max_messages"

            now = _now()
            conn.execute(
                """UPDATE messages SET status='done', completed_at=?,
                   lease_owner=NULL, lease_until=NULL
                   WHERE id=?""",
                (now, message_id),
            )
            reply_id = None
            if close_topic:
                reason = response.get("close_reason") or stop_reason or "agent_conclusion"
                final_body = str(response.get("body", "")).strip()
                final_kind = str(response.get("kind", "SYNTHESIS"))
                final_grade = str(response.get("grade", "UNASSESSED"))
                final_refs = _evidence_refs(response.get("evidence_refs", []))
                _validate_message(final_kind, final_grade, final_body, final_refs)
                conn.execute(
                    """UPDATE topics SET status='closed', closed_at=?, close_reason=?,
                       final_by=?, final_kind=?, final_grade=?, final_summary=?,
                       final_evidence_refs=?
                       WHERE id=?""",
                    (now, reason, agent, final_kind, final_grade, final_body,
                     json.dumps(final_refs, ensure_ascii=False), msg["topic_id"]),
                )
                conn.execute(
                    """UPDATE messages SET status='expired'
                       WHERE topic_id=? AND status='queued'""",
                    (msg["topic_id"],),
                )
            else:
                recipient = str(response.get("to", "")).strip()
                reply_id = _post_in_tx(
                    conn, topic_id=msg["topic_id"], sender=agent,
                    recipient=recipient, kind=str(response.get("kind", "SYNTHESIS")),
                    grade=str(response.get("grade", "UNASSESSED")),
                    body=str(response.get("body", "")),
                    evidence_refs=_evidence_refs(response.get("evidence_refs", [])),
                    parent_id=message_id, round_no=next_round,
                    ttl_seconds=int(response.get("ttl_seconds", 86400)),
                )
            conn.commit()
            return {"status": "submitted", "reply_message_id": reply_id,
                    "topic_closed": close_topic, "stop_reason": stop_reason}
        except Exception:
            conn.rollback()
            raise


def topic_transcript(topic_id: str, *, db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    init_db(db_path)
    with _db(db_path) as conn:
        topic = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
        if topic is None:
            raise KeyError(f"존재하지 않는 topic: {topic_id}")
        messages = conn.execute(
            "SELECT * FROM messages WHERE topic_id=? ORDER BY id", (topic_id,)
        ).fetchall()
    t = dict(topic)
    t["final_evidence_refs"] = json.loads(t["final_evidence_refs"])
    for key in ("created_at", "closed_at"):
        t[key] = _iso(t[key])
    return {"topic": t, "messages": [_message_dict(row) for row in messages],
            "authority": "UNASSESSED_DIALOGUE_ONLY"}


def system_status(*, db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    init_db(db_path)
    with _db(db_path) as conn:
        agents = [dict(row) for row in conn.execute(
            "SELECT name, role, active FROM agents ORDER BY name"
        )]
        topics = [dict(row) for row in conn.execute(
            """SELECT t.*, COUNT(m.id) AS message_count
               FROM topics t LEFT JOIN messages m ON m.topic_id=t.id
               GROUP BY t.id ORDER BY t.created_at DESC"""
        )]
        states = {row["status"]: row["n"] for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM messages GROUP BY status"
        )}
    for topic in topics:
        topic["created_at"] = _iso(topic["created_at"])
        topic["closed_at"] = _iso(topic["closed_at"])
        topic["final_evidence_refs"] = json.loads(topic["final_evidence_refs"])
    return {"db": str(Path(db_path).resolve()), "agents": agents,
            "topics": topics, "message_states": states,
            "authority": "UNASSESSED_DIALOGUE_ONLY"}


def _read_body(args: argparse.Namespace) -> str:
    if getattr(args, "body_file", None):
        return Path(args.body_file).read_text(encoding="utf-8")
    return args.body


def _json_print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="math-dialogue-") as td:
        db = Path(td) / "dialogue.sqlite3"
        init_db(db)
        register_agent("explorer", "구성·추측 제안", db_path=db)
        register_agent("skeptic", "반례·가정 감사", db_path=db)
        topic = create_topic("모의 접합 보조정리", "selftest", max_rounds=3,
                             max_messages=4, db_path=db)
        first = post_message(topic, "human", "explorer", "QUESTION",
                             "작은 범위에서 반증 계획을 제안하라.", db_path=db)
        job1 = claim_message("explorer", db_path=db)
        assert job1 and job1["id"] == first and job1["status"] == "leased"
        out1 = submit_response("explorer", first, {
            "to": "skeptic", "kind": "CONJECTURE", "grade": "UNASSESSED",
            "body": "(n,r)=(6,3) 전수를 먼저 확인하자.", "evidence_refs": [],
        }, db_path=db)
        second = out1["reply_message_id"]
        job2 = claim_message("skeptic", db_path=db)
        assert job2 and job2["id"] == second and job2["round_no"] == 2
        out2 = submit_response("skeptic", second, {
            "to": "explorer", "kind": "CRITIQUE", "grade": "UNASSESSED",
            "body": "범위 내 전수와 일반 정리를 구분해야 한다.",
            "evidence_refs": ["falsify.py"],
        }, db_path=db)
        third = out2["reply_message_id"]
        job3 = claim_message("explorer", db_path=db)
        assert job3 and job3["id"] == third and job3["round_no"] == 3
        stopped = submit_response("explorer", third, {
            "to": "skeptic", "kind": "SYNTHESIS", "grade": "UNASSESSED",
            "body": "전수 결과는 EXHAUSTED_ON_SCOPE로만 기록한다.",
            "evidence_refs": ["falsify.py"],
        }, db_path=db)
        assert stopped["topic_closed"] is True and stopped["stop_reason"] == "max_rounds"
        assert submit_response("explorer", third, {}, db_path=db)["status"] == "already_submitted"
        transcript = topic_transcript(topic, db_path=db)
        assert len(transcript["messages"]) == 3
        assert transcript["topic"]["status"] == "closed"
        assert transcript["topic"]["final_summary"].startswith("전수 결과는")
        assert transcript["authority"] == "UNASSESSED_DIALOGUE_ONLY"

        # 동시 heartbeat가 같은 메시지를 두 번 선점하지 않는지 검사한다.
        concurrency = create_topic("동시 선점", "selftest", max_rounds=1,
                                   max_messages=24, db_path=db)
        for i in range(20):
            post_message(concurrency, "selftest", "skeptic", "QUESTION", f"q{i}",
                         db_path=db)
        claimed: list[int] = []
        submission_states: list[str] = []
        guard = threading.Lock()

        def worker() -> None:
            while True:
                item = claim_message("skeptic", lease_seconds=30, db_path=db)
                if item is None:
                    return
                with guard:
                    claimed.append(item["id"])
                result = submit_response("skeptic", item["id"], {
                    "close_topic": False,
                    "to": "explorer",
                    "kind": "SYNTHESIS",
                    "body": "max_rounds에서 자동 종료되어 이 본문은 방출되지 않는다.",
                }, db_path=db)
                with guard:
                    submission_states.append(result["status"])

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(worker) for _ in range(4)]
            for future in futures:
                future.result()
        # 첫 완료만 topic을 닫고, 이미 lease된 나머지 작업은 최종 요약을 덮어쓰지 않는다.
        assert len(claimed) == len(set(claimed))
        assert len(claimed) >= 1
        assert submission_states.count("submitted") == 1
        assert len(submission_states) == len(claimed)

    print("math_dialogue selftest OK (3-round 토론, idempotence, 동시 선점 중복 0)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="수학 Codex 세션 로컬 토론 우편함")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB 경로")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="DB 초기화")
    p = sub.add_parser("register", help="agent 등록/갱신")
    p.add_argument("--agent", required=True)
    p.add_argument("--role", required=True)

    p = sub.add_parser("topic", help="새 토론 topic 생성")
    p.add_argument("--title", required=True)
    p.add_argument("--created-by", default="human")
    p.add_argument("--max-rounds", type=int, default=6)
    p.add_argument("--max-messages", type=int, default=12)

    p = sub.add_parser("post", help="topic에 첫 메시지 게시")
    p.add_argument("--topic", required=True)
    p.add_argument("--sender", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--kind", required=True, choices=sorted(KINDS))
    p.add_argument("--grade", default="UNASSESSED", choices=sorted(GRADES))
    body = p.add_mutually_exclusive_group(required=True)
    body.add_argument("--body")
    body.add_argument("--body-file")
    p.add_argument("--evidence-ref", action="append", default=[])
    p.add_argument("--ttl-seconds", type=int, default=86400)

    p = sub.add_parser("claim", help="agent inbox에서 메시지 하나 선점")
    p.add_argument("--agent", required=True)
    p.add_argument("--lease-seconds", type=int, default=900)

    p = sub.add_parser("submit", help="선점 메시지에 JSON 응답 제출")
    p.add_argument("--agent", required=True)
    p.add_argument("--message-id", required=True, type=int)
    p.add_argument("--response-file", required=True)

    p = sub.add_parser("transcript", help="topic 전체 대화 조회")
    p.add_argument("--topic", required=True)
    sub.add_parser("status", help="전체 상태 조회")
    sub.add_parser("selftest", help="실제 Codex 없이 프로토콜 자체 테스트")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = Path(args.db)
    if args.command == "init":
        _json_print({"db": str(init_db(db).resolve()),
                     "authority": "UNASSESSED_DIALOGUE_ONLY"})
    elif args.command == "register":
        register_agent(args.agent, args.role, db_path=db)
        _json_print({"registered": args.agent, "role": args.role})
    elif args.command == "topic":
        topic = create_topic(args.title, args.created_by, max_rounds=args.max_rounds,
                             max_messages=args.max_messages, db_path=db)
        _json_print({"topic_id": topic})
    elif args.command == "post":
        message = post_message(
            args.topic, args.sender, args.to, args.kind, _read_body(args),
            grade=args.grade, evidence_refs=args.evidence_ref,
            ttl_seconds=args.ttl_seconds, db_path=db,
        )
        _json_print({"message_id": message})
    elif args.command == "claim":
        item = claim_message(args.agent, lease_seconds=args.lease_seconds, db_path=db)
        _json_print({"status": "claimed", "message": item} if item else
                    {"status": "no_work", "message": None})
    elif args.command == "submit":
        response = json.loads(Path(args.response_file).read_text(encoding="utf-8"))
        _json_print(submit_response(args.agent, args.message_id, response, db_path=db))
    elif args.command == "transcript":
        _json_print(topic_transcript(args.topic, db_path=db))
    elif args.command == "status":
        _json_print(system_status(db_path=db))
    elif args.command == "selftest":
        selftest()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
