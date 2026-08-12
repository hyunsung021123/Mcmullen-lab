"""math_dialogue.py — 여러 수학 Codex 세션을 위한 로컬 비동기 우편함.

이 모듈은 **토론 운반 계층**일 뿐 수학적 판정자가 아니다. 저장된 메시지, 증명 초안,
반례 후보, 합성문은 전부 기본적으로 UNASSESSED 이며 ``om_core``, ``falsify``,
``process_verifier`` 또는 재현 가능한 evidence를 거치기 전에는 어떤 권한도 없다.

여러 Codex heartbeat가 같은 checkout에서 이 CLI를 호출하는 사용례를 겨냥한다. SQLite의
``BEGIN IMMEDIATE`` 트랜잭션으로 한 메시지를 두 세션이 동시에 선점하지 못하게 하고,
라운드·메시지 수·TTL·lease 만료로 무한 대화를 막는다. 런타임 DB는 기본적으로
``local_runs/math_dialogue/dialogue.sqlite3``에 있으며 Git 공유 상태가 아니다.

빠른 시작::

    python math_dialogue.py init
    python math_dialogue.py register --agent builder --role "정식화·증명 구성"
    python math_dialogue.py register --agent critic --role "반증·계산 감사"
    python math_dialogue.py enqueue --title "새 증명 방향" --to builder \
        --kind QUESTION --body "제시된 방향을 정확한 보조정리로 분해하라."
    python math_dialogue.py claim --agent builder

실제 Codex 호출 없이 프로토콜을 검사하려면 ``python math_dialogue.py selftest``를 쓴다.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import secrets
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
from urllib.parse import urlparse


DEFAULT_DB = Path(os.environ.get(
    "MCMULLEN_MATH_DIALOGUE_DB",
    Path(__file__).resolve().parent / "local_runs" / "math_dialogue" / "dialogue.sqlite3",
))

#: 토론 자체의 메시지 종류. 기존 값은 절대 제거하지 않는다 — DB 의 kind 컬럼에는 CHECK
#: 제약이 없어 과거 행이 그대로 남아 있고, 이 집합을 좁히면 옛 대화가 읽히지 않는다.
DIALOGUE_KINDS = {
    "QUESTION",
    "DIRECTION",
    "CONJECTURE",
    "PROOF_SKETCH",
    "COUNTEREXAMPLE_CANDIDATE",
    "COMPUTATIONAL_CLAIM",
    "CRITIQUE",
    "SYNTHESIS",
}

#: 계산 전달 계층(`computation_relay.py`)이 쓰는 종류. 토론 메시지와 달리 본문이
#: 산출물 파일을 **참조**하며, 어느 것도 실행 대상이 아니다 — 실행되는 것은
#: 검토된 experiment-plan/v1 의 commands 뿐이다.
COMPUTATION_KINDS = {
    "COMPUTATION_REQUEST",     # 수학 세션 → 계산 세션: 기계가독 계산 의무
    "EXPERIMENT_PLAN",         # 계산 세션이 작성·검토한 실행 계획 (유일한 실행 대상)
    "COMPUTATION_RESULT",      # 계산 세션 → 원래 agent: 재현 가능한 결과 회신
}

KINDS = DIALOGUE_KINDS | COMPUTATION_KINDS
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

# 적합성을 오래 논증한 뒤 분야를 고르는 대신, 넓은 덱에서 먼저 뽑아 짧게 시험한다.
# key/label/lens를 DB에 함께 보존해 선택 자체도 나중에 재현·분석할 수 있게 한다.
EXPLORATION_DOMAIN_DECK = (
    ("extremal-combinatorics", "극값 조합론", "금지 구조·밀도 임계값·최소 반례로 번역"),
    ("matroid-theory", "매트로이드 이론", "minor·duality·rank 함수·excluded minor로 번역"),
    ("discrete-geometry", "이산기하", "배치·분리·Radon/Helly형 국소 조건으로 번역"),
    ("convex-geometry", "볼록기하", "극점·쌍대성·지지 초평면·재배향 궤도로 번역"),
    ("graph-theory", "그래프 이론", "국소 obstruction·cut/flow·tree decomposition으로 번역"),
    ("order-theory", "순서론·격자론", "부분순서·closure·Möbius/격자 불변량으로 번역"),
    ("algebraic-topology", "대수적 위상수학", "복합체·homology·nerve·obstruction으로 번역"),
    ("commutative-algebra", "가환대수", "Stanley–Reisner ideal·syzygy·Hilbert 자료로 번역"),
    ("algebraic-geometry", "대수기하·실현공간", "방정식계·퇴화·realization space 성분으로 번역"),
    ("group-actions", "군 작용·표현론", "orbit·stabilizer·character·대칭 축소로 번역"),
    ("probabilistic-method", "확률론적 방법", "무작위 구성·첫/둘째 모멘트·국소 보조정리로 번역"),
    ("information-theory", "정보이론·부호이론", "entropy·code distance·압축 불가능성으로 번역"),
    ("optimization", "조합최적화·선형/반정정부호 최적화", "relaxation·duality gap·분리 oracle로 번역"),
    ("constraint-solving", "SAT·CSP·모델검사", "기계가독 제약·unsat core·bounded model로 번역"),
    ("discrete-morse", "이산 Morse 이론", "collapse·critical cell·위상적 단순화로 번역"),
    ("category-theory", "범주론·함자적 관점", "보존되는 구조·자연성·보편 성질로 번역"),
)
RESEARCH_EVENT_TYPES = {
    "QUESTION", "HYPOTHESIS", "ATTEMPT", "CRITIQUE", "COMPUTATION",
    "SOURCE_NOTE", "FAILURE", "PIVOT", "SYNTHESIS",
}
RESEARCH_OUTCOMES = {
    "OPEN", "ADVANCED", "REFUTED", "BLOCKED", "LOW_YIELD", "DUPLICATE",
    "INCONCLUSIVE",
}
SOURCE_VERIFICATION_LEVELS = {"FULLTEXT", "ABSTRACT_ONLY", "SECONDHAND"}


def _now() -> float:
    return time.time()


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _topic_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"T-{stamp}-{uuid.uuid4().hex[:6]}"


def _cycle_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"ER-{stamp}-{uuid.uuid4().hex[:6]}"


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
                created_at REAL NOT NULL,
                last_seen REAL NOT NULL
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
                final_evidence_refs TEXT NOT NULL DEFAULT '[]',
                source_key TEXT
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
                available_at REAL NOT NULL,
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

            CREATE TABLE IF NOT EXISTS research_cycles (
                id TEXT PRIMARY KEY,
                topic_id TEXT NOT NULL UNIQUE REFERENCES topics(id),
                agent TEXT NOT NULL REFERENCES agents(name),
                domain_key TEXT NOT NULL,
                domain_label TEXT NOT NULL,
                domain_lens TEXT NOT NULL,
                rng_seed INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN
                    ('active', 'advanced', 'refuted', 'blocked', 'low_yield',
                     'duplicate', 'inconclusive')),
                created_at REAL NOT NULL,
                closed_at REAL,
                final_summary TEXT,
                failure_reason TEXT,
                reusable_clues TEXT NOT NULL DEFAULT '[]',
                next_questions TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS research_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL REFERENCES topics(id),
                cycle_id TEXT REFERENCES research_cycles(id),
                message_id INTEGER NOT NULL REFERENCES messages(id),
                agent TEXT NOT NULL,
                event_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                approach TEXT NOT NULL,
                outcome TEXT NOT NULL,
                failure_reason TEXT,
                reusable_clues TEXT NOT NULL DEFAULT '[]',
                next_questions TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_research_event_per_message
                ON research_events(message_id);
            CREATE INDEX IF NOT EXISTS research_event_order
                ON research_events(cycle_id, created_at, id);

            CREATE TABLE IF NOT EXISTS research_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL REFERENCES topics(id),
                cycle_id TEXT REFERENCES research_cycles(id),
                message_id INTEGER NOT NULL REFERENCES messages(id),
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                accessed_at REAL NOT NULL,
                verification_level TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(message_id, url)
            );
            CREATE INDEX IF NOT EXISTS research_source_order
                ON research_sources(cycle_id, accessed_at, id);
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(topics)")}
        if "source_key" not in columns:
            conn.execute("ALTER TABLE topics ADD COLUMN source_key TEXT")
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS unique_topic_source
               ON topics(source_key) WHERE source_key IS NOT NULL"""
        )
        agent_columns = {row["name"] for row in conn.execute("PRAGMA table_info(agents)")}
        if "last_seen" not in agent_columns:
            conn.execute("ALTER TABLE agents ADD COLUMN last_seen REAL")
            conn.execute("UPDATE agents SET last_seen=created_at WHERE last_seen IS NULL")
        message_columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
        if "available_at" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN available_at REAL NOT NULL DEFAULT 0")
    return path


def register_agent(name: str, role: str, *, db_path: Path | str = DEFAULT_DB) -> None:
    if not name.strip() or not role.strip():
        raise ValueError("agent 이름과 role은 비어 있을 수 없음")
    init_db(db_path)
    with _db(db_path) as conn:
        now = _now()
        conn.execute(
            """INSERT INTO agents(name, role, active, created_at, last_seen)
               VALUES (?, ?, 1, ?, ?)
               ON CONFLICT(name) DO UPDATE SET role=excluded.role, active=1,
                   last_seen=excluded.last_seen""",
            (name.strip(), role.strip(), now, now),
        )


def create_topic(title: str, created_by: str, *, max_rounds: int = 6,
                 max_messages: int = 12, source_key: str | None = None,
                 db_path: Path | str = DEFAULT_DB) -> str:
    if max_rounds < 1 or max_messages < 1:
        raise ValueError("max_rounds와 max_messages는 1 이상이어야 함")
    topic_id = _topic_id()
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if source_key:
            existing = conn.execute(
                "SELECT id FROM topics WHERE source_key=?", (source_key.strip(),)
            ).fetchone()
            if existing is not None:
                conn.commit()
                return str(existing["id"])
        conn.execute(
            """INSERT INTO topics
               (id, title, created_by, status, max_rounds, max_messages, created_at,
                source_key)
               VALUES (?, ?, ?, 'open', ?, ?, ?, ?)""",
            (topic_id, title.strip(), created_by.strip(), max_rounds, max_messages, _now(),
             source_key.strip() if source_key else None),
        )
        conn.commit()
    return topic_id


def enqueue_work(title: str, body: str, recipient: str, *, created_by: str = "human",
                 kind: str = "QUESTION", grade: str = "UNASSESSED",
                 evidence_refs: list[str] | None = None, max_rounds: int = 8,
                 max_messages: int = 12, source_key: str | None = None,
                 db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """Create a bounded topic and its first message as one idempotent operation."""
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            if source_key:
                existing = conn.execute(
                    "SELECT id FROM topics WHERE source_key=?", (source_key.strip(),)
                ).fetchone()
                if existing is not None:
                    conn.commit()
                    return {"topic_id": str(existing["id"]), "message_id": None,
                            "status": "already_exists"}
            if max_rounds < 1 or max_messages < 1:
                raise ValueError("max_rounds와 max_messages는 1 이상이어야 함")
            topic_id = _topic_id()
            conn.execute(
                """INSERT INTO topics
                   (id, title, created_by, status, max_rounds, max_messages,
                    created_at, source_key)
                   VALUES (?, ?, ?, 'open', ?, ?, ?, ?)""",
                (topic_id, title.strip(), created_by.strip(), max_rounds, max_messages,
                 _now(), source_key.strip() if source_key else None),
            )
            message_id = _post_in_tx(
                conn, topic_id=topic_id, sender=created_by, recipient=recipient,
                kind=kind, grade=grade, body=body,
                evidence_refs=evidence_refs or [], parent_id=None, round_no=1,
                ttl_seconds=86400,
            )
            conn.commit()
            return {"topic_id": topic_id, "message_id": message_id, "status": "created"}
        except Exception:
            conn.rollback()
            raise


def _open_question_index(markdown: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"^##\s+(QQ-\d+)\s+[—-]\s+(.+)$", re.MULTILINE)
    questions: list[tuple[str, str]] = []
    for match in pattern.finditer(markdown):
        question_id, header = match.groups()
        if "상태 `OPEN`" not in header and "상태 OPEN" not in header:
            continue
        title = re.split(r"\s+·\s+상태\s+", header, maxsplit=1)[0].strip()
        questions.append((question_id, title))
    return questions


def sync_open_questions(open_path: Path | str, recipient: str, *, min_active_agents: int = 2,
                        max_open_topics: int = 2, limit: int = 1,
                        stale_after_seconds: int = 1800,
                        db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """Idempotently seed a small number of repository OPEN questions.

    Only the question identifier, title, and source path enter the mailbox. Agents read the
    current file themselves, avoiding a stale or oversized copy in SQLite.
    """
    path = Path(open_path)
    if (min_active_agents < 1 or max_open_topics < 1 or limit < 1 or
            stale_after_seconds < 1):
        raise ValueError("min_active_agents, max_open_topics, limit, stale_after_seconds는 1 이상이어야 함")
    markdown = path.read_text(encoding="utf-8")
    questions = _open_question_index(markdown)
    init_db(db_path)
    created: list[dict[str, Any]] = []
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            now = _now()
            conn.execute(
                "UPDATE agents SET last_seen=? WHERE name=? AND active=1",
                (now, recipient),
            )
            active = conn.execute(
                """SELECT COUNT(*) AS n FROM agents
                   WHERE active=1 AND last_seen >= ?""",
                (now - stale_after_seconds,),
            ).fetchone()["n"]
            recipient_row = conn.execute(
                "SELECT active FROM agents WHERE name=?", (recipient,)
            ).fetchone()
            if recipient_row is None or not recipient_row["active"]:
                raise KeyError(f"활성 agent가 아님: {recipient}")
            if active < min_active_agents:
                conn.commit()
                return {"status": "waiting_for_peers", "active_agents": active,
                        "required_agents": min_active_agents, "created": []}
            open_count = conn.execute(
                """SELECT COUNT(*) AS n FROM topics
                   WHERE status='open' AND source_key LIKE 'questions/OPEN.md::%'"""
            ).fetchone()["n"]
            capacity = min(limit, max(0, max_open_topics - open_count))
            if capacity == 0:
                conn.commit()
                return {"status": "open_topic_limit", "active_agents": active,
                        "open_repository_topics": open_count, "created": []}
            source_display = path.as_posix()
            for question_id, title in questions:
                source_key = f"questions/OPEN.md::{question_id}"
                exists = conn.execute(
                    "SELECT id FROM topics WHERE source_key=?", (source_key,)
                ).fetchone()
                if exists is not None:
                    continue
                topic_id = _topic_id()
                conn.execute(
                    """INSERT INTO topics
                       (id, title, created_by, status, max_rounds, max_messages,
                        created_at, source_key)
                       VALUES (?, ?, 'repository_sync', 'open', 8, 12, ?, ?)""",
                    (topic_id, f"{question_id} — {title}", _now(), source_key),
                )
                body = (
                    f"저장소 공개 질문 {question_id}을 처리하라. 원문은 {source_display}의 "
                    f"'{question_id} — {title}' 절이다. 원문의 요구 형식과 검증 방법을 읽고, "
                    "정확한 명제·현재 근거·가장 값싼 다음 검증 의무로 분해한 뒤 적합한 다음 "
                    "agent에게 라우팅하라. 토론 결과 자체에는 판정 권한이 없다."
                )
                message_id = _post_in_tx(
                    conn, topic_id=topic_id, sender="repository_sync",
                    recipient=recipient, kind="QUESTION", grade="UNASSESSED",
                    body=body, evidence_refs=[source_display], parent_id=None,
                    round_no=1, ttl_seconds=86400,
                )
                created.append({"question_id": question_id, "topic_id": topic_id,
                                "message_id": message_id})
                if len(created) >= capacity:
                    break
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"status": "created" if created else "up_to_date",
            "active_agents": active, "created": created}


def seed_exploration(agent: str, *, seed: int | None = None,
                     max_cycles_per_day: int = 12, max_open_cycles: int = 1,
                     cooldown_seconds: int = 600, max_rounds: int = 6,
                     max_messages: int = 8,
                     domain_deck: tuple[tuple[str, str, str], ...] = EXPLORATION_DOMAIN_DECK,
                     db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """유휴 strategist에게 재현 가능한 무작위 분야 탐사 한 건을 원자적으로 투입한다.

    분야 선택은 최근 세 번과 겹치지 않는 후보 중 RNG로 수행한다. 이는 분야의 적합성을
    사전에 점수화하는 장치가 아니라 단순 다양성 장치다. 열린 사이클·일일 예산·cooldown과
    기존 inbox를 같은 트랜잭션에서 검사하므로 동시 heartbeat도 폭주시키지 못한다.
    """
    if (max_cycles_per_day < 1 or max_open_cycles < 1 or cooldown_seconds < 0 or
            max_rounds < 1 or max_messages < 1):
        raise ValueError("탐사 예산과 한도는 양수이고 cooldown은 0 이상이어야 함")
    if not domain_deck:
        raise ValueError("탐사 분야 덱은 비어 있을 수 없음")
    keys = [item[0] for item in domain_deck]
    if len(keys) != len(set(keys)):
        raise ValueError("탐사 분야 key는 서로 달라야 함")
    for item in domain_deck:
        if len(item) != 3 or not all(isinstance(value, str) and value.strip() for value in item):
            raise ValueError("각 탐사 분야는 비어 있지 않은 key/label/lens 삼중항이어야 함")
    if seed is None:
        seed = secrets.randbelow(2**63 - 1)
    if not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed는 0 이상 2^63 미만 정수여야 함")

    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            now = _now()
            registered = conn.execute(
                "SELECT active FROM agents WHERE name=?", (agent,)
            ).fetchone()
            if registered is None or not registered["active"]:
                raise KeyError(f"활성 agent가 아님: {agent}")
            conn.execute("UPDATE agents SET last_seen=? WHERE name=?", (now, agent))

            # TTL 만료나 중단된 heartbeat 뒤에 열린 cycle이 영원히 전역 한도를 점유하지
            # 않도록, 더 처리할 메시지가 없는 cycle은 보수적으로 INCONCLUSIVE 종료한다.
            conn.execute(
                """UPDATE research_cycles SET status='inconclusive', closed_at=?,
                   final_summary=COALESCE(final_summary,
                       'topic이 먼저 닫혀 탐사 사이클을 보수적으로 종료했다.'),
                   failure_reason=COALESCE(failure_reason, 'topic_already_closed')
                   WHERE status='active' AND topic_id IN (
                       SELECT id FROM topics WHERE status='closed'
                   )""",
                (now,),
            )
            abandoned = conn.execute(
                """SELECT c.id, c.topic_id FROM research_cycles c
                   JOIN topics t ON t.id=c.topic_id
                   WHERE c.status='active' AND t.status='open'
                     AND NOT EXISTS (
                         SELECT 1 FROM messages m
                         WHERE m.topic_id=c.topic_id
                           AND m.status IN ('queued', 'leased')
                     )"""
            ).fetchall()
            for row in abandoned:
                summary = "처리 가능한 메시지가 없어 탐사 사이클을 보수적으로 종료했다."
                conn.execute(
                    """UPDATE research_cycles SET status='inconclusive', closed_at=?,
                       final_summary=?, failure_reason=? WHERE id=?""",
                    (now, summary, "heartbeat 중단 또는 메시지 TTL 만료", row["id"]),
                )
                conn.execute(
                    """UPDATE topics SET status='closed', closed_at=?,
                       close_reason='exploration_abandoned', final_by='emergent-loop',
                       final_kind='SYNTHESIS', final_grade='UNASSESSED',
                       final_summary=? WHERE id=?""",
                    (now, summary, row["topic_id"]),
                )

            pending = conn.execute(
                """SELECT COUNT(*) AS n
                   FROM messages m JOIN topics t ON t.id=m.topic_id
                   WHERE m.recipient=?
                     AND (m.status='leased' OR
                          (m.status='queued' AND m.available_at<=?))
                     AND t.status='open'""",
                (agent, now),
            ).fetchone()["n"]
            if pending:
                conn.commit()
                return {"status": "inbox_not_empty", "pending_messages": pending,
                        "created": None}

            open_rows = conn.execute(
                """SELECT id, topic_id, domain_key, created_at FROM research_cycles
                   WHERE status='active' ORDER BY created_at"""
            ).fetchall()
            if len(open_rows) >= max_open_cycles:
                conn.commit()
                return {"status": "open_cycle_limit", "open_cycles": len(open_rows),
                        "created": None,
                        "existing_cycle_id": str(open_rows[0]["id"])}

            day_start = datetime.fromtimestamp(now, timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp()
            today_count = conn.execute(
                """SELECT COUNT(*) AS n FROM research_cycles
                   WHERE agent=? AND created_at>=?""",
                (agent, day_start),
            ).fetchone()["n"]
            if today_count >= max_cycles_per_day:
                conn.commit()
                return {"status": "daily_budget", "cycles_today": today_count,
                        "created": None}

            last = conn.execute(
                """SELECT created_at FROM research_cycles
                   WHERE agent=? ORDER BY created_at DESC LIMIT 1""",
                (agent,),
            ).fetchone()
            if last is not None and now - last["created_at"] < cooldown_seconds:
                remaining = int(cooldown_seconds - (now - last["created_at"]))
                conn.commit()
                return {"status": "cooldown", "retry_after_seconds": max(1, remaining),
                        "created": None}

            recent = {row["domain_key"] for row in conn.execute(
                """SELECT domain_key FROM research_cycles
                   WHERE agent=? ORDER BY created_at DESC LIMIT 3""",
                (agent,),
            )}
            candidates = [item for item in domain_deck if item[0] not in recent]
            if not candidates:
                candidates = list(domain_deck)
            domain_key, domain_label, domain_lens = random.Random(seed).choice(candidates)

            cycle_id = _cycle_id()
            topic_id = _topic_id()
            source_key = f"emergent-research::{cycle_id}"
            conn.execute(
                """INSERT INTO topics
                   (id, title, created_by, status, max_rounds, max_messages,
                    created_at, source_key)
                   VALUES (?, ?, ?, 'open', ?, ?, ?, ?)""",
                (topic_id, f"창발 탐사 — {domain_label}", agent, max_rounds,
                 max_messages, now, source_key),
            )
            conn.execute(
                """INSERT INTO research_cycles
                   (id, topic_id, agent, domain_key, domain_label, domain_lens,
                    rng_seed, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
                (cycle_id, topic_id, agent, domain_key, domain_label, domain_lens,
                 seed, now),
            )
            body = (
                "EMERGENT_RESEARCH_CYCLE v1\n"
                f"CYCLE_ID: {cycle_id}\nRNG_SEED: {seed}\n"
                f"DOMAIN: {domain_label} ({domain_key})\nLENS: {domain_lens}\n"
                "CONTEXT: AGENTS.md, docs/RESEARCH_STATUS.md, questions/OPEN.md와 존재하면 "
                "docs/STATE.md의 현재 목표·죽은 길을 읽어라.\n"
                "MISSION: 이 분야가 적합한지 오래 정당화하지 말고, 현재 목표의 한 국소 의무를 "
                "이 관점으로 즉시 번역해 한 번만 깊게 밀어라. 정확한 새 질문 1~3개, 반증 가능한 "
                "가설 또는 방향 1개, 가장 싼 판별 시험을 만든다. 실질적 연결이 없거나 이미 죽은 "
                "길이면 LOW_YIELD/DUPLICATE로 실패 이유와 재사용 단서를 기록하고 닫아라. "
                "유망하면 prover/falsifier/활성 계산 담당에게 넘겨라. 모든 산출물은 UNASSESSED다."
            )
            message_id = _post_in_tx(
                conn, topic_id=topic_id, sender="emergent-loop", recipient=agent,
                kind="DIRECTION", grade="UNASSESSED", body=body,
                evidence_refs=["docs/RESEARCH_STATUS.md"], parent_id=None,
                round_no=1, ttl_seconds=86400,
            )
            conn.commit()
            return {
                "status": "created",
                "created": {
                    "cycle_id": cycle_id, "topic_id": topic_id, "agent": agent,
                    "message_id": message_id, "rng_seed": seed,
                    "domain_key": domain_key, "domain_label": domain_label,
                    "domain_lens": domain_lens,
                },
            }
        except Exception:
            conn.rollback()
            raise


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


def _nonempty_string_list(value: Any, field: str) -> list[str]:
    if (not isinstance(value, list) or
            not all(isinstance(item, str) and item.strip() for item in value)):
        raise ValueError(f"{field}는 비어 있지 않은 문자열 목록이어야 함")
    return [item.strip() for item in value]


def _research_log(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("research_log는 객체여야 함")
    allowed = {
        "event_type", "summary", "approach", "outcome", "failure_reason",
        "reusable_clues", "next_questions",
    }
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"research_log의 알 수 없는 필드: {sorted(unknown)}")
    event_type = str(value.get("event_type", "")).strip().upper()
    outcome = str(value.get("outcome", "")).strip().upper()
    summary = str(value.get("summary", "")).strip()
    approach = str(value.get("approach", "")).strip()
    failure_reason = str(value.get("failure_reason", "")).strip()
    if event_type not in RESEARCH_EVENT_TYPES:
        raise ValueError(f"research_log.event_type은 다음 중 하나여야 함: {sorted(RESEARCH_EVENT_TYPES)}")
    if outcome not in RESEARCH_OUTCOMES:
        raise ValueError(f"research_log.outcome은 다음 중 하나여야 함: {sorted(RESEARCH_OUTCOMES)}")
    if not summary or not approach:
        raise ValueError("research_log.summary와 approach는 비어 있을 수 없음")
    if outcome in {"BLOCKED", "LOW_YIELD"} and not failure_reason:
        raise ValueError(f"{outcome}에는 failure_reason이 필요함")
    return {
        "event_type": event_type,
        "summary": summary,
        "approach": approach,
        "outcome": outcome,
        "failure_reason": failure_reason,
        "reusable_clues": _nonempty_string_list(
            value.get("reusable_clues", []), "research_log.reusable_clues"
        ),
        "next_questions": _nonempty_string_list(
            value.get("next_questions", []), "research_log.next_questions"
        ),
    }


def _research_sources(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("sources는 최대 20개의 객체 목록이어야 함")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("sources의 각 항목은 객체여야 함")
        allowed = {"url", "title", "verification_level", "note"}
        unknown = set(item) - allowed
        if unknown:
            raise ValueError(f"source의 알 수 없는 필드: {sorted(unknown)}")
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        level = str(item.get("verification_level", "")).strip().upper()
        note = str(item.get("note", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source.url은 http(s) URL이어야 함")
        if not title or not note:
            raise ValueError("source.title과 note는 비어 있을 수 없음")
        if level not in SOURCE_VERIFICATION_LEVELS:
            raise ValueError(
                f"source.verification_level은 다음 중 하나여야 함: "
                f"{sorted(SOURCE_VERIFICATION_LEVELS)}"
            )
        if url in seen:
            raise ValueError(f"한 응답에서 source URL이 중복됨: {url}")
        seen.add(url)
        normalized.append({"url": url, "title": title,
                           "verification_level": level, "note": note})
    return normalized


def _record_research_in_tx(conn: sqlite3.Connection, *, msg: sqlite3.Row,
                           agent: str, response: dict[str, Any], now: float,
                           close_topic: bool) -> None:
    """응답과 구조화 연구 로그를 같은 transaction에 기록한다."""
    cycle = conn.execute(
        "SELECT * FROM research_cycles WHERE topic_id=?", (msg["topic_id"],)
    ).fetchone()
    raw_log = response.get("research_log")
    if cycle is not None and raw_log is None:
        raise ValueError("창발 탐사 응답에는 research_log가 필요함")
    log = _research_log(raw_log) if raw_log is not None else None
    sources = _research_sources(response.get("sources", []))
    cycle_id = str(cycle["id"]) if cycle is not None else None

    if log is not None:
        conn.execute(
            """INSERT INTO research_events
               (topic_id, cycle_id, message_id, agent, event_type, summary,
                approach, outcome, failure_reason, reusable_clues,
                next_questions, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg["topic_id"], cycle_id, msg["id"], agent, log["event_type"],
             log["summary"], log["approach"], log["outcome"],
             log["failure_reason"] or None,
             json.dumps(log["reusable_clues"], ensure_ascii=False),
             json.dumps(log["next_questions"], ensure_ascii=False), now),
        )
    for source in sources:
        conn.execute(
            """INSERT INTO research_sources
               (topic_id, cycle_id, message_id, url, title, accessed_at,
                verification_level, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg["topic_id"], cycle_id, msg["id"], source["url"], source["title"],
             now, source["verification_level"], source["note"], now),
        )

    if cycle is not None and close_topic:
        assert log is not None
        final_outcome = log["outcome"]
        if final_outcome == "OPEN":
            final_outcome = "INCONCLUSIVE"
        conn.execute(
            """UPDATE research_cycles
               SET status=?, closed_at=?, final_summary=?, failure_reason=?,
                   reusable_clues=?, next_questions=?
               WHERE id=?""",
            (final_outcome.lower(), now, log["summary"],
             log["failure_reason"] or None,
             json.dumps(log["reusable_clues"], ensure_ascii=False),
             json.dumps(log["next_questions"], ensure_ascii=False), cycle_id),
        )


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
            parent_id, round_no, status, available_at, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?)""",
        (topic_id, sender, recipient, kind, grade, body,
         json.dumps(evidence_refs, ensure_ascii=False), parent_id, round_no,
         now, now, now + ttl_seconds),
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
    for key in ("available_at", "created_at", "expires_at", "lease_until", "completed_at"):
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
            registered = conn.execute(
                "SELECT active FROM agents WHERE name=?", (agent,)
            ).fetchone()
            if registered is None or not registered["active"]:
                raise KeyError(f"활성 agent가 아님: {agent}")
            conn.execute("UPDATE agents SET last_seen=? WHERE name=?", (now, agent))
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
                """SELECT m.*, t.title AS topic_title,
                          c.id AS exploration_cycle_id,
                          c.domain_key AS exploration_domain_key,
                          c.domain_label AS exploration_domain_label,
                          c.domain_lens AS exploration_domain_lens,
                          c.rng_seed AS exploration_rng_seed
                   FROM messages m JOIN topics t ON t.id=m.topic_id
                   LEFT JOIN research_cycles c ON c.topic_id=t.id
                   WHERE m.recipient=? AND m.status='queued' AND m.available_at<=?
                     AND t.status='open'
                   ORDER BY m.available_at, m.created_at, m.id LIMIT 1""",
                (agent, now),
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
                """SELECT m.*, t.title AS topic_title,
                          c.id AS exploration_cycle_id,
                          c.domain_key AS exploration_domain_key,
                          c.domain_label AS exploration_domain_label,
                          c.domain_lens AS exploration_domain_lens,
                          c.rng_seed AS exploration_rng_seed
                   FROM messages m JOIN topics t ON t.id=m.topic_id
                   LEFT JOIN research_cycles c ON c.topic_id=t.id
                   WHERE m.id=?""",
                (row["id"],),
            ).fetchone()
            conn.commit()
            return _message_dict(claimed)
        except Exception:
            conn.rollback()
            raise


def claim_for_heartbeat(agent: str, *, lease_seconds: int = 900,
                        idle_exploration: bool = True,
                        db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """기존 strategist automation도 수정 없이 창발 루프에 들어가게 하는 CLI 경계.

    먼저 일반 inbox를 선점한다. 비어 있고 agent가 strategist일 때만 bounded seed를 한 번
    호출하고, 생성됐다면 그 메시지를 즉시 선점한다. 라이브러리 API ``claim_message``의
    기존 의미는 바꾸지 않아 relay와 테스트의 하위호환을 유지한다.
    """
    item = claim_message(agent, lease_seconds=lease_seconds, db_path=db_path)
    seeded = None
    if item is None and idle_exploration and agent == "strategist":
        seeded = seed_exploration(agent, db_path=db_path)
        if seeded["status"] == "created":
            item = claim_message(agent, lease_seconds=lease_seconds, db_path=db_path)
            if item is None:
                raise RuntimeError("생성한 탐사 메시지를 즉시 선점하지 못함")
    return {
        "status": "claimed" if item is not None else "no_work",
        "message": item,
        "idle_exploration": seeded,
    }


def release_message(agent: str, message_id: int, *, defer_seconds: int = 0,
                    db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """Return an unprocessed leased message to the queue without changing its content."""
    if defer_seconds < 0:
        raise ValueError("defer_seconds는 0 이상이어야 함")
    init_db(db_path)
    with _db(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            updated = conn.execute(
                """UPDATE messages SET status='queued', lease_owner=NULL, lease_until=NULL,
                   available_at=?
                   WHERE id=? AND status='leased' AND lease_owner=?""",
                (_now() + defer_seconds, message_id, agent),
            ).rowcount
            if updated != 1:
                raise ValueError(f"message {message_id}은 {agent}가 선점한 작업이 아님")
            conn.commit()
            return {"status": "released", "message_id": message_id,
                    "defer_seconds": defer_seconds}
        except Exception:
            conn.rollback()
            raise


def submit_response(agent: str, message_id: int, response: dict[str, Any], *,
                    db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """선점한 메시지를 완료하고 선택적으로 다음 메시지 하나를 만든다.

    response 스키마::

        {"to": "falsifier", "kind": "CONJECTURE", "grade": "UNASSESSED",
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
            _record_research_in_tx(
                conn, msg=msg, agent=agent, response=response, now=now,
                close_topic=close_topic,
            )
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
        cycle = conn.execute(
            "SELECT * FROM research_cycles WHERE topic_id=?", (topic_id,)
        ).fetchone()
        events = conn.execute(
            "SELECT * FROM research_events WHERE topic_id=? ORDER BY id", (topic_id,)
        ).fetchall()
        sources = conn.execute(
            "SELECT * FROM research_sources WHERE topic_id=? ORDER BY id", (topic_id,)
        ).fetchall()
    t = dict(topic)
    t["final_evidence_refs"] = json.loads(t["final_evidence_refs"])
    for key in ("created_at", "closed_at"):
        t[key] = _iso(t[key])
    cycle_out = _cycle_dict(cycle) if cycle is not None else None
    return {
        "topic": t,
        "messages": [_message_dict(row) for row in messages],
        "research_cycle": cycle_out,
        "research_events": [_event_dict(row) for row in events],
        "research_sources": [_source_dict(row) for row in sources],
        "authority": "UNASSESSED_DIALOGUE_ONLY",
    }


def _cycle_dict(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    for key in ("created_at", "closed_at"):
        out[key] = _iso(out[key])
    for key in ("reusable_clues", "next_questions"):
        out[key] = json.loads(out[key])
    return out


def _event_dict(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    out["created_at"] = _iso(out["created_at"])
    for key in ("reusable_clues", "next_questions"):
        out[key] = json.loads(out[key])
    return out


def _source_dict(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    for key in ("accessed_at", "created_at"):
        out[key] = _iso(out[key])
    return out


def research_log_view(*, cycle_id: str | None = None, limit: int = 100,
                      db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    """Second-brain adapter가 소비할 수 있는 안정적인 JSON 연구 로그를 돌려준다."""
    if limit < 1 or limit > 1000:
        raise ValueError("limit은 1 이상 1000 이하여야 함")
    init_db(db_path)
    with _db(db_path) as conn:
        if cycle_id:
            cycles = conn.execute(
                "SELECT * FROM research_cycles WHERE id=?", (cycle_id,)
            ).fetchall()
            if not cycles:
                raise KeyError(f"존재하지 않는 research cycle: {cycle_id}")
            events = conn.execute(
                """SELECT * FROM research_events WHERE cycle_id=?
                   ORDER BY created_at, id LIMIT ?""",
                (cycle_id, limit),
            ).fetchall()
            sources = conn.execute(
                """SELECT * FROM research_sources WHERE cycle_id=?
                   ORDER BY accessed_at, id LIMIT ?""",
                (cycle_id, limit),
            ).fetchall()
        else:
            cycles = conn.execute(
                "SELECT * FROM research_cycles ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            events = conn.execute(
                "SELECT * FROM research_events ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            sources = conn.execute(
                "SELECT * FROM research_sources ORDER BY accessed_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return {
        "schema": "math-dialogue-research-log/v1",
        "cycles": [_cycle_dict(row) for row in cycles],
        "events": [_event_dict(row) for row in events],
        "sources": [_source_dict(row) for row in sources],
        "authority": "UNASSESSED_DIALOGUE_ONLY",
    }


def system_status(*, db_path: Path | str = DEFAULT_DB) -> dict[str, Any]:
    init_db(db_path)
    with _db(db_path) as conn:
        agents = [dict(row) for row in conn.execute(
            "SELECT name, role, active, last_seen FROM agents ORDER BY name"
        )]
        topics = [dict(row) for row in conn.execute(
            """SELECT t.*, COUNT(m.id) AS message_count
               FROM topics t LEFT JOIN messages m ON m.topic_id=t.id
               GROUP BY t.id ORDER BY t.created_at DESC"""
        )]
        states = {row["status"]: row["n"] for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM messages GROUP BY status"
        )}
        deferred_messages = conn.execute(
            """SELECT COUNT(*) AS n FROM messages
               WHERE status='queued' AND available_at>?""",
            (_now(),),
        ).fetchone()["n"]
        cycle_states = {row["status"]: row["n"] for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM research_cycles GROUP BY status"
        )}
        research_counts = {
            "events": conn.execute("SELECT COUNT(*) AS n FROM research_events").fetchone()["n"],
            "sources": conn.execute("SELECT COUNT(*) AS n FROM research_sources").fetchone()["n"],
        }
    freshness_cutoff = _now() - 1800
    for agent in agents:
        agent["fresh"] = bool(agent["active"] and agent["last_seen"] >= freshness_cutoff)
        agent["last_seen"] = _iso(agent["last_seen"])
    for topic in topics:
        topic["created_at"] = _iso(topic["created_at"])
        topic["closed_at"] = _iso(topic["closed_at"])
        topic["final_evidence_refs"] = json.loads(topic["final_evidence_refs"])
    return {"db": str(Path(db_path).resolve()), "agents": agents,
            "topics": topics, "message_states": states,
            "deferred_messages": deferred_messages,
            "research_cycle_states": cycle_states, "research_counts": research_counts,
            "authority": "UNASSESSED_DIALOGUE_ONLY"}


def _read_body(args: argparse.Namespace) -> str:
    if getattr(args, "body_file", None):
        return Path(args.body_file).read_text(encoding="utf-8")
    return args.body


def _json_print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _configure_stdio_utf8() -> None:
    """Windows legacy codepage에서도 DB commit 뒤 JSON 출력 실패가 나지 않게 한다."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="math-dialogue-") as td:
        db = Path(td) / "dialogue.sqlite3"
        init_db(db)
        register_agent("builder", "정식화·증명 구성", db_path=db)
        register_agent("critic", "반례·계산 감사", db_path=db)
        topic = create_topic("모의 접합 보조정리", "selftest", max_rounds=3,
                             max_messages=4, db_path=db)
        first = post_message(topic, "human", "builder", "QUESTION",
                             "작은 범위에서 반증 계획을 제안하라.", db_path=db)
        job1 = claim_message("builder", db_path=db)
        assert job1 and job1["id"] == first and job1["status"] == "leased"
        out1 = submit_response("builder", first, {
            "to": "critic", "kind": "CONJECTURE", "grade": "UNASSESSED",
            "body": "(n,r)=(6,3) 전수를 먼저 확인하자.", "evidence_refs": [],
        }, db_path=db)
        second = out1["reply_message_id"]
        job2 = claim_message("critic", db_path=db)
        assert job2 and job2["id"] == second and job2["round_no"] == 2
        out2 = submit_response("critic", second, {
            "to": "builder", "kind": "CRITIQUE", "grade": "UNASSESSED",
            "body": "범위 내 전수와 일반 정리를 구분해야 한다.",
            "evidence_refs": ["falsify.py"],
        }, db_path=db)
        third = out2["reply_message_id"]
        job3 = claim_message("builder", db_path=db)
        assert job3 and job3["id"] == third and job3["round_no"] == 3
        stopped = submit_response("builder", third, {
            "to": "critic", "kind": "SYNTHESIS", "grade": "UNASSESSED",
            "body": "전수 결과는 EXHAUSTED_ON_SCOPE로만 기록한다.",
            "evidence_refs": ["falsify.py"],
        }, db_path=db)
        assert stopped["topic_closed"] is True and stopped["stop_reason"] == "max_rounds"
        assert submit_response("builder", third, {}, db_path=db)["status"] == "already_submitted"
        transcript = topic_transcript(topic, db_path=db)
        assert len(transcript["messages"]) == 3
        assert transcript["topic"]["status"] == "closed"
        assert transcript["topic"]["final_summary"].startswith("전수 결과는")
        assert transcript["authority"] == "UNASSESSED_DIALOGUE_ONLY"

        # 동시 heartbeat가 같은 메시지를 두 번 선점하지 않는지 검사한다.
        concurrency = create_topic("동시 선점", "selftest", max_rounds=1,
                                   max_messages=24, db_path=db)
        for i in range(20):
            post_message(concurrency, "selftest", "critic", "QUESTION", f"q{i}",
                         db_path=db)
        claimed: list[int] = []
        submission_states: list[str] = []
        guard = threading.Lock()

        def worker() -> None:
            while True:
                item = claim_message("critic", lease_seconds=30, db_path=db)
                if item is None:
                    return
                with guard:
                    claimed.append(item["id"])
                result = submit_response("critic", item["id"], {
                    "close_topic": False,
                    "to": "builder",
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

        # 사람 지시와 저장소 OPEN 질문 수집은 source_key로 중복 투입되지 않는다.
        register_agent("strategist", "문제 정식화·라우팅·종합", db_path=db)
        register_agent("prover", "엄밀한 증명 구성", db_path=db)
        direct = enqueue_work(
            "범용 직접 지시", "주어진 명제를 정식화하라.", "strategist",
            source_key="user:test-direct", db_path=db,
        )
        repeated = enqueue_work(
            "범용 직접 지시", "이 본문은 중복 생성되면 안 된다.", "strategist",
            source_key="user:test-direct", db_path=db,
        )
        assert direct["status"] == "created"
        assert repeated == {"topic_id": direct["topic_id"], "message_id": None,
                            "status": "already_exists"}
        leased_direct = claim_message("strategist", db_path=db)
        assert leased_direct and leased_direct["id"] == direct["message_id"]
        assert release_message("strategist", leased_direct["id"], db_path=db)["status"] == "released"
        assert claim_message("strategist", db_path=db)["id"] == direct["message_id"]

        open_file = Path(td) / "OPEN.md"
        open_file.write_text(
            "# 질문\n\n"
            "## QQ-1001 — 첫 범용 질문 · 상태 `OPEN` · 우선순위 상\n\n### 답변\n\n"
            "## QQ-1002 — 두 번째 범용 질문 · 상태 `OPEN` · 우선순위 중\n\n### 답변\n\n"
            "## QQ-1003 — 닫힌 질문 · 상태 `ANSWERED`\n",
            encoding="utf-8",
        )
        sync1 = sync_open_questions(open_file, "strategist", max_open_topics=2,
                                    limit=1, db_path=db)
        sync2 = sync_open_questions(open_file, "strategist", max_open_topics=2,
                                    limit=1, db_path=db)
        sync3 = sync_open_questions(open_file, "strategist", max_open_topics=2,
                                    limit=1, db_path=db)
        assert [row["question_id"] for row in sync1["created"]] == ["QQ-1001"]
        assert [row["question_id"] for row in sync2["created"]] == ["QQ-1002"]
        assert sync3["status"] == "open_topic_limit" and not sync3["created"]

        # 유휴 상태의 무작위 분야 탐사와 실패까지 포함한 구조화 로그를 검사한다.
        register_agent("explorer-a", "창발 탐사 A", db_path=db)
        seeded = seed_exploration(
            "explorer-a", seed=20260812, cooldown_seconds=0,
            max_cycles_per_day=1, db_path=db,
        )
        assert seeded["status"] == "created"
        created = seeded["created"]
        assert created["rng_seed"] == 20260812
        exploration = claim_message("explorer-a", db_path=db)
        assert exploration and exploration["id"] == created["message_id"]
        assert exploration["exploration_cycle_id"] == created["cycle_id"]
        response = {
            "close_topic": True,
            "kind": "SYNTHESIS",
            "grade": "UNASSESSED",
            "body": "이 분야 전이는 현재 정의와 직접 연결되지 않아 종료한다.",
            "evidence_refs": ["https://example.org/paper"],
            "research_log": {
                "event_type": "FAILURE",
                "summary": "첫 전이는 낮은 정보가치로 판정했다.",
                "approach": "선택 분야의 표준 불변량을 현재 국소 의무에 대응시켰다.",
                "outcome": "LOW_YIELD",
                "failure_reason": "정의 보존 대응을 만들지 못했다.",
                "reusable_clues": ["불변량의 정의역이 맞지 않음"],
                "next_questions": ["쌍대 대상에서는 정의역이 맞는가?"],
            },
            "sources": [{
                "url": "https://example.org/paper",
                "title": "Example primary source",
                "verification_level": "FULLTEXT",
                "note": "정의역 조건만 확인했다.",
            }],
        }
        finished = submit_response("explorer-a", exploration["id"], response, db_path=db)
        assert finished["topic_closed"] is True
        assert submit_response(
            "explorer-a", exploration["id"], response, db_path=db
        )["status"] == "already_submitted"
        logged = research_log_view(cycle_id=created["cycle_id"], db_path=db)
        assert logged["schema"] == "math-dialogue-research-log/v1"
        assert logged["cycles"][0]["status"] == "low_yield"
        assert len(logged["events"]) == 1 and len(logged["sources"]) == 1
        assert logged["sources"][0]["verification_level"] == "FULLTEXT"
        cooling = seed_exploration(
            "explorer-a", seed=1, cooldown_seconds=1800,
            max_cycles_per_day=2, db_path=db,
        )
        assert cooling["status"] == "cooldown" and cooling["retry_after_seconds"] > 0
        budgeted = seed_exploration(
            "explorer-a", seed=1, cooldown_seconds=0,
            max_cycles_per_day=1, db_path=db,
        )
        assert budgeted["status"] == "daily_budget"

        # 동시에 seed해도 global open-cycle 한도를 넘지 않는다.
        register_agent("explorer-b", "창발 탐사 B", db_path=db)
        register_agent("explorer-c", "창발 탐사 C", db_path=db)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(seed_exploration, name, seed=seed_value,
                            cooldown_seconds=0, max_open_cycles=1, db_path=db)
                for name, seed_value in (("explorer-b", 2), ("explorer-c", 3))
            ]
            concurrent_seeds = [future.result() for future in futures]
        assert sorted(item["status"] for item in concurrent_seeds) == [
            "created", "open_cycle_limit"
        ]
        winner = next(item for item in concurrent_seeds if item["status"] == "created")
        winner_agent = winner["created"]["agent"]
        winner_message = winner["created"]["message_id"]
        claimed_winner = claim_message(winner_agent, db_path=db)
        assert claimed_winner and claimed_winner["id"] == winner_message
        try:
            submit_response(winner_agent, winner_message, {
                "close_topic": True, "kind": "SYNTHESIS",
                "body": "구조화 연구 로그가 빠진 잘못된 응답",
            }, db_path=db)
        except ValueError as exc:
            assert "research_log" in str(exc)
        else:
            raise AssertionError("창발 탐사에서 research_log 누락을 거부해야 함")
        assert submit_response(winner_agent, winner_message, {
            "close_topic": True, "kind": "SYNTHESIS",
            "body": "동시 seed 승자의 탐사를 명시적으로 종료한다.",
            "research_log": {
                "event_type": "SYNTHESIS", "summary": "동시 seed 한도 확인",
                "approach": "두 agent가 같은 open-cycle 예산을 경쟁했다.",
                "outcome": "INCONCLUSIVE", "failure_reason": "",
                "reusable_clues": ["global open-cycle limit이 직렬화됨"],
                "next_questions": [],
            },
        }, db_path=db)["topic_closed"] is True

        # 사용자/동료 inbox는 새 창발 탐사보다 우선한다.
        register_agent("explorer-d", "창발 탐사 D", db_path=db)
        enqueue_work("기존 의무", "먼저 처리할 질문", "explorer-d", db_path=db)
        prioritized = seed_exploration(
            "explorer-d", seed=4, cooldown_seconds=0, db_path=db,
        )
        assert prioritized["status"] == "inbox_not_empty"

        # 기존 automation이 호출하는 claim CLI 경계는 strategist idle을 자동 seed한다.
        auto_db = Path(td) / "auto-claim.sqlite3"
        register_agent("strategist", "자동 seed strategist", db_path=auto_db)
        auto_claim = claim_for_heartbeat("strategist", db_path=auto_db)
        assert auto_claim["status"] == "claimed"
        assert auto_claim["idle_exploration"]["status"] == "created"
        assert auto_claim["message"]["exploration_cycle_id"] is not None
        plain_db = Path(td) / "plain-claim.sqlite3"
        register_agent("strategist", "수동 strategist", db_path=plain_db)
        plain_claim = claim_for_heartbeat(
            "strategist", idle_exploration=False, db_path=plain_db,
        )
        assert plain_claim == {
            "status": "no_work", "message": None, "idle_exploration": None
        }

        # 동료 부재로 release한 일반 질문은 잠시 defer되어 탐사 pivot을 막지 않는다.
        defer_db = Path(td) / "deferred-inbox.sqlite3"
        register_agent("strategist", "defer strategist", db_path=defer_db)
        waiting = enqueue_work(
            "동료를 기다리는 의무", "지금은 적합한 동료가 없다.", "strategist",
            db_path=defer_db,
        )
        claimed_waiting = claim_for_heartbeat("strategist", db_path=defer_db)
        assert claimed_waiting["message"]["id"] == waiting["message_id"]
        released_waiting = release_message(
            "strategist", waiting["message_id"], defer_seconds=60, db_path=defer_db,
        )
        assert released_waiting["defer_seconds"] == 60
        pivot_claim = claim_for_heartbeat("strategist", db_path=defer_db)
        assert pivot_claim["status"] == "claimed"
        assert pivot_claim["message"]["exploration_cycle_id"] is not None
        assert system_status(db_path=defer_db)["deferred_messages"] == 1

        # TTL/중단으로 처리 가능 메시지가 사라진 cycle은 다음 seed에서 자동 회수된다.
        register_agent("explorer-e", "창발 탐사 E", db_path=db)
        abandoned = seed_exploration(
            "explorer-e", seed=5, cooldown_seconds=0, db_path=db,
        )
        assert abandoned["status"] == "created"
        with _db(db) as conn:
            conn.execute(
                "UPDATE messages SET status='expired' WHERE id=?",
                (abandoned["created"]["message_id"],),
            )
        register_agent("explorer-f", "창발 탐사 F", db_path=db)
        recovered = seed_exploration(
            "explorer-f", seed=6, cooldown_seconds=0, db_path=db,
        )
        assert recovered["status"] == "created"
        abandoned_log = research_log_view(
            cycle_id=abandoned["created"]["cycle_id"], db_path=db,
        )
        assert abandoned_log["cycles"][0]["status"] == "inconclusive"
        assert abandoned_log["cycles"][0]["failure_reason"] == (
            "heartbeat 중단 또는 메시지 TTL 만료"
        )

    print("math_dialogue selftest OK (토론, 동시선점, OPEN 동기화, 창발 탐사 로그)")


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
    p.add_argument("--source-key")

    p = sub.add_parser("enqueue", help="topic과 첫 메시지를 한 번에 생성")
    p.add_argument("--title", required=True)
    p.add_argument("--created-by", default="human")
    p.add_argument("--to", required=True)
    p.add_argument("--kind", default="QUESTION", choices=sorted(KINDS))
    p.add_argument("--grade", default="UNASSESSED", choices=sorted(GRADES))
    body = p.add_mutually_exclusive_group(required=True)
    body.add_argument("--body")
    body.add_argument("--body-file")
    p.add_argument("--evidence-ref", action="append", default=[])
    p.add_argument("--max-rounds", type=int, default=8)
    p.add_argument("--max-messages", type=int, default=12)
    p.add_argument("--source-key")

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
    p.add_argument("--no-idle-exploration", action="store_true",
                   help="strategist inbox가 비어도 창발 탐사를 만들지 않음")

    p = sub.add_parser("release", help="처리하지 않은 선점 메시지를 큐로 반환")
    p.add_argument("--agent", required=True)
    p.add_argument("--message-id", required=True, type=int)
    p.add_argument("--defer-seconds", type=int, default=1800,
                   help="CLI heartbeat 반환 후 재선점까지 대기(기본 30분)")

    p = sub.add_parser("submit", help="선점 메시지에 JSON 응답 제출")
    p.add_argument("--agent", required=True)
    p.add_argument("--message-id", required=True, type=int)
    p.add_argument("--response-file", required=True)

    p = sub.add_parser("transcript", help="topic 전체 대화 조회")
    p.add_argument("--topic", required=True)
    p = sub.add_parser("sync-open", help="questions/OPEN.md의 새 질문을 제한적으로 투입")
    p.add_argument("--open-file", default="questions/OPEN.md")
    p.add_argument("--to", default="strategist")
    p.add_argument("--min-active-agents", type=int, default=2)
    p.add_argument("--max-open-topics", type=int, default=2)
    p.add_argument("--limit", type=int, default=1)
    p.add_argument("--stale-after-seconds", type=int, default=1800)
    p = sub.add_parser("seed-exploration", help="유휴 strategist용 무작위 분야 탐사 생성")
    p.add_argument("--agent", default="strategist")
    p.add_argument("--seed", type=int)
    p.add_argument("--max-cycles-per-day", type=int, default=12)
    p.add_argument("--max-open-cycles", type=int, default=1)
    p.add_argument("--cooldown-seconds", type=int, default=600)
    p.add_argument("--max-rounds", type=int, default=6)
    p.add_argument("--max-messages", type=int, default=8)
    p = sub.add_parser("research-log", help="구조화 연구 사이클·사건·출처 JSON 조회")
    p.add_argument("--cycle")
    p.add_argument("--limit", type=int, default=100)
    sub.add_parser("status", help="전체 상태 조회")
    sub.add_parser("selftest", help="실제 Codex 없이 프로토콜 자체 테스트")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
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
                             max_messages=args.max_messages, source_key=args.source_key,
                             db_path=db)
        _json_print({"topic_id": topic})
    elif args.command == "enqueue":
        _json_print(enqueue_work(
            args.title, _read_body(args), args.to, created_by=args.created_by,
            kind=args.kind, grade=args.grade, evidence_refs=args.evidence_ref,
            max_rounds=args.max_rounds, max_messages=args.max_messages,
            source_key=args.source_key, db_path=db,
        ))
    elif args.command == "post":
        message = post_message(
            args.topic, args.sender, args.to, args.kind, _read_body(args),
            grade=args.grade, evidence_refs=args.evidence_ref,
            ttl_seconds=args.ttl_seconds, db_path=db,
        )
        _json_print({"message_id": message})
    elif args.command == "claim":
        _json_print(claim_for_heartbeat(
            args.agent, lease_seconds=args.lease_seconds,
            idle_exploration=not args.no_idle_exploration, db_path=db,
        ))
    elif args.command == "release":
        _json_print(release_message(
            args.agent, args.message_id, defer_seconds=args.defer_seconds, db_path=db,
        ))
    elif args.command == "submit":
        response = json.loads(Path(args.response_file).read_text(encoding="utf-8"))
        _json_print(submit_response(args.agent, args.message_id, response, db_path=db))
    elif args.command == "transcript":
        _json_print(topic_transcript(args.topic, db_path=db))
    elif args.command == "sync-open":
        _json_print(sync_open_questions(
            args.open_file, args.to, min_active_agents=args.min_active_agents,
            max_open_topics=args.max_open_topics, limit=args.limit,
            stale_after_seconds=args.stale_after_seconds, db_path=db,
        ))
    elif args.command == "seed-exploration":
        _json_print(seed_exploration(
            args.agent, seed=args.seed,
            max_cycles_per_day=args.max_cycles_per_day,
            max_open_cycles=args.max_open_cycles,
            cooldown_seconds=args.cooldown_seconds,
            max_rounds=args.max_rounds, max_messages=args.max_messages,
            db_path=db,
        ))
    elif args.command == "research-log":
        _json_print(research_log_view(
            cycle_id=args.cycle, limit=args.limit, db_path=db,
        ))
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
