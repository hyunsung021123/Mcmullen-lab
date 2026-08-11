"""
insight_ledger.py — 인간 수학 insight의 append-only 공동 기록 계층.

채팅 안의 아이디어는 다른 에이전트나 다음 세션에 자동으로 전달되지 않는다. 이 모듈은
아이디어를 짧은 공개 명제, 가정, 범위, 실현가능성, 불변성, 반증 계획으로 정규화하고
Claude/Codex가 같은 상태를 재구성할 수 있는 hash-chain JSONL에 기록한다.

이 ledger는 증거 저장소가 아니다. SUPPORTED/REFUTED/INTEGRATED 전이는 외부의 재현 가능한
evidence/implementation 참조를 요구하지만, 참/거짓 판정 자체는 om_core, falsify,
process_verifier 등 기존 결정론적 경로가 담당한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


SCHEMA_ID = "human-insight-ledger/v1"
ZERO_HASH = "0" * 64
DEFAULT_PATH = Path(__file__).resolve().parent / "knowledge" / "insights" / "ledger.jsonl"

ACTORS = ("human", "claude", "codex", "chatgpt")
GRADES = ("UNASSESSED", "PROVEN", "VERIFIED", "NUMERICAL", "CONJECTURE", "SPECULATION")
STATUSES = ("PROPOSED", "FORMALIZED", "TESTING", "SUPPORTED", "REFUTED", "INTEGRATED", "RETIRED")
REALIZABILITY = ("NOT_APPLICABLE", "UNKNOWN", "REQUIRED", "REALIZABLE", "NONREALIZABLE")
INVARIANCE = ("UNKNOWN", "PROVEN", "REFUTED", "NOT_APPLICABLE")
TARGETS = (
    "definition", "invariant", "conjecture", "generator_family", "search_objective",
    "pruning_rule", "symmetry_reduction", "encoding", "falsifier", "certificate",
    "performance", "documentation",
)

ALLOWED_TRANSITIONS = {
    "PROPOSED": {"FORMALIZED", "RETIRED"},
    "FORMALIZED": {"TESTING", "RETIRED"},
    "TESTING": {"FORMALIZED", "SUPPORTED", "REFUTED", "RETIRED"},
    "SUPPORTED": {"TESTING", "REFUTED", "INTEGRATED", "RETIRED"},
    "REFUTED": {"FORMALIZED", "RETIRED"},
    "INTEGRATED": {"TESTING", "REFUTED", "RETIRED"},
    "RETIRED": {"FORMALIZED"},
}


class InsightError(ValueError):
    """스키마, 상태 전이 또는 hash-chain 계약 위반."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical(data: dict) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _record_hash(record_without_hash: dict) -> str:
    return hashlib.sha256(_canonical(record_without_hash)).hexdigest()


def _require_text(name: str, value, *, max_chars: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InsightError(f"{name}: 비어있지 않은 문자열이어야 함")
    value = value.strip()
    if len(value) > max_chars:
        raise InsightError(f"{name}: {len(value)}자 > 상한 {max_chars}자")
    return value


def _string_list(name: str, value, *, max_items: int = 40,
                 item_chars: int = 1000) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > max_items:
        raise InsightError(f"{name}: 최대 {max_items}개의 문자열 list여야 함")
    return [_require_text(f"{name}[{i}]", item, max_chars=item_chars)
            for i, item in enumerate(value)]


def _choice(name: str, value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise InsightError(f"{name}: {value!r}; 허용값={choices}")
    return value


def _validate_proposal(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise InsightError("proposal: JSON object여야 함")
    actor = _choice("actor", spec.get("actor", "human"), ACTORS)
    grade = _choice("grade", spec.get("grade", "UNASSESSED"), GRADES)
    realizability = _choice("realizability", spec.get("realizability", "UNKNOWN"),
                            REALIZABILITY)
    invariance = spec.get("invariance") or {}
    if not isinstance(invariance, dict):
        raise InsightError("invariance: object여야 함")
    relabel = _choice("invariance.relabel", invariance.get("relabel", "UNKNOWN"),
                      INVARIANCE)
    reorient = _choice("invariance.reorient", invariance.get("reorient", "UNKNOWN"),
                       INVARIANCE)
    targets = _string_list("targets", spec.get("targets"), max_items=12, item_chars=80)
    unknown_targets = [target for target in targets if target not in TARGETS]
    if unknown_targets:
        raise InsightError(f"targets: 알 수 없는 값 {unknown_targets}; 허용값={TARGETS}")
    scope = spec.get("scope") or {}
    if not isinstance(scope, dict):
        raise InsightError("scope: object여야 함")
    try:
        json.dumps(scope, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise InsightError(f"scope: JSON 직렬화 불가: {exc}") from None
    return {
        "actor": actor,
        "title": _require_text("title", spec.get("title"), max_chars=200),
        "statement": _require_text("statement", spec.get("statement"), max_chars=4000),
        "grade": grade,
        "scope": scope,
        "assumptions": _string_list("assumptions", spec.get("assumptions")),
        "realizability": realizability,
        "invariance": {"relabel": relabel, "reorient": reorient},
        "targets": targets,
        "falsification_plan": _string_list("falsification_plan",
                                            spec.get("falsification_plan")),
        "source_refs": _string_list("source_refs", spec.get("source_refs"),
                                     item_chars=500),
        "parent_ids": _string_list("parent_ids", spec.get("parent_ids"),
                                    item_chars=40),
        "claim_dsl": str(spec.get("claim_dsl", "")).strip()[:2000],
    }


@contextmanager
def _file_lock(lock_path: Path, timeout_s: float = 10.0):
    """같은 checkout에서 Claude/Codex 동시 append를 직렬화하는 OS 파일 잠금."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + timeout_s
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise InsightError("insight ledger lock 시간 초과") from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise InsightError("insight ledger lock 시간 초과") from None
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


class InsightLedger:
    """append-only insight event ledger. update/delete API를 의도적으로 제공하지 않는다."""

    def __init__(self, path: str | os.PathLike = DEFAULT_PATH):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def iter_events(self) -> Iterator[dict]:
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise InsightError(f"line {line_no}: JSON 오류: {exc}") from None

    def verify_chain(self) -> int:
        previous = ZERO_HASH
        count = 0
        for count, event in enumerate(self.iter_events(), 1):
            if event.get("schema") != SCHEMA_ID:
                raise InsightError(f"event {count}: schema 불일치")
            if event.get("seq") != count:
                raise InsightError(f"event {count}: seq 불일치")
            if event.get("prev_hash") != previous:
                raise InsightError(f"event {count}: prev_hash 불일치")
            claimed = event.get("event_hash")
            body = {key: value for key, value in event.items() if key != "event_hash"}
            actual = _record_hash(body)
            if claimed != actual:
                raise InsightError(f"event {count}: event_hash 불일치 (개찬 의심)")
            previous = claimed
        return count

    def _events_verified(self) -> list[dict]:
        self.verify_chain()
        return list(self.iter_events())

    def states(self) -> dict[str, dict]:
        states: dict[str, dict] = {}
        for event in self._events_verified():
            insight_id = event["insight_id"]
            if event["kind"] == "INSIGHT":
                if insight_id in states:
                    raise InsightError(f"중복 insight id: {insight_id}")
                states[insight_id] = {
                    **event["proposal"],
                    "id": insight_id,
                    "status": "PROPOSED",
                    "created_at": event["at"],
                    "updated_at": event["at"],
                    "status_note": "",
                    "evidence_refs": [],
                    "implementation_refs": [],
                }
            elif event["kind"] == "STATUS":
                if insight_id not in states:
                    raise InsightError(f"선행 INSIGHT가 없는 STATUS: {insight_id}")
                state = states[insight_id]
                state["status"] = event["to_status"]
                state["updated_at"] = event["at"]
                state["status_note"] = event["note"]
                state["evidence_refs"] = event["evidence_refs"]
                state["implementation_refs"] = event["implementation_refs"]
                if event.get("grade"):
                    state["grade"] = event["grade"]
            else:
                raise InsightError(f"알 수 없는 event kind: {event.get('kind')!r}")
        return states

    def _append_locked(self, body: dict, previous: str) -> dict:
        body["prev_hash"] = previous
        body["event_hash"] = _record_hash(body)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(body, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return body

    def propose(self, spec: dict) -> dict:
        proposal = _validate_proposal(spec)
        with _file_lock(self.lock_path):
            events = self._events_verified()
            insight_number = sum(1 for event in events if event["kind"] == "INSIGHT") + 1
            insight_id = f"HI-{insight_number:04d}"
            existing = {event["insight_id"] for event in events}
            missing_parents = [pid for pid in proposal["parent_ids"] if pid not in existing]
            if missing_parents:
                raise InsightError(f"존재하지 않는 parent_ids: {missing_parents}")
            event = {
                "schema": SCHEMA_ID,
                "seq": len(events) + 1,
                "kind": "INSIGHT",
                "insight_id": insight_id,
                "at": _now(),
                "actor": proposal["actor"],
                "proposal": proposal,
            }
            previous = events[-1]["event_hash"] if events else ZERO_HASH
            return self._append_locked(event, previous)

    def transition(self, insight_id: str, *, actor: str, to_status: str,
                   note: str, grade: str | None = None,
                   evidence_refs: list[str] | None = None,
                   implementation_refs: list[str] | None = None) -> dict:
        actor = _choice("actor", actor, ACTORS)
        to_status = _choice("to_status", to_status, STATUSES)
        note = _require_text("note", note, max_chars=2000)
        evidence = _string_list("evidence_refs", evidence_refs, item_chars=500)
        implementation = _string_list("implementation_refs", implementation_refs,
                                      item_chars=500)
        if grade is not None:
            grade = _choice("grade", grade, GRADES)
        with _file_lock(self.lock_path):
            events = self._events_verified()
            states = self.states()
            if insight_id not in states:
                raise InsightError(f"없는 insight id: {insight_id}")
            current = states[insight_id]["status"]
            if to_status not in ALLOWED_TRANSITIONS[current]:
                raise InsightError(f"허용되지 않은 상태 전이: {current} -> {to_status}")
            if to_status in ("SUPPORTED", "REFUTED") and not evidence:
                raise InsightError(f"{to_status} 전이는 evidence_refs가 필요함")
            if to_status == "INTEGRATED" and (not evidence or not implementation):
                raise InsightError("INTEGRATED 전이는 evidence_refs와 implementation_refs가 필요함")
            event = {
                "schema": SCHEMA_ID,
                "seq": len(events) + 1,
                "kind": "STATUS",
                "insight_id": insight_id,
                "at": _now(),
                "actor": actor,
                "from_status": current,
                "to_status": to_status,
                "note": note,
                "grade": grade,
                "evidence_refs": evidence,
                "implementation_refs": implementation,
            }
            previous = events[-1]["event_hash"] if events else ZERO_HASH
            return self._append_locked(event, previous)

    def get(self, insight_id: str) -> dict:
        states = self.states()
        if insight_id not in states:
            raise InsightError(f"없는 insight id: {insight_id}")
        return states[insight_id]


def render_markdown(states: dict[str, dict]) -> str:
    lines = ["| ID | 상태 | 등급 | 제목 | 대상 | 갱신 |",
             "|---|---|---|---|---|---|"]
    for insight_id, state in sorted(states.items()):
        title = state["title"].replace("|", "\\|")
        targets = ", ".join(state["targets"]) or "-"
        lines.append(f"| {insight_id} | {state['status']} | {state['grade']} | "
                     f"{title} | {targets} | {state['updated_at']} |")
    return "\n".join(lines)


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="인간 수학 insight 공동 ledger")
    parser.add_argument("--ledger", default=str(DEFAULT_PATH), help="ledger JSONL 경로")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="JSON 제안을 PROPOSED로 append")
    add.add_argument("--from-json", required=True, help="proposal JSON 파일")

    status = sub.add_parser("status", help="상태 전이 event append")
    status.add_argument("insight_id")
    status.add_argument("--actor", required=True, choices=ACTORS)
    status.add_argument("--to", required=True, choices=STATUSES)
    status.add_argument("--note", required=True)
    status.add_argument("--grade", choices=GRADES)
    status.add_argument("--evidence", action="append", default=[])
    status.add_argument("--implementation", action="append", default=[])

    listing = sub.add_parser("list", help="최신 상태 목록")
    listing.add_argument("--json", action="store_true", dest="as_json")
    listing.add_argument("--status", choices=STATUSES)

    show = sub.add_parser("show", help="insight 하나의 최신 상태")
    show.add_argument("insight_id")
    sub.add_parser("verify", help="JSONL hash chain 검증")

    template = sub.add_parser("template", help="proposal JSON 템플릿 출력")
    template.add_argument("--actor", choices=ACTORS, default="human")
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    ledger = InsightLedger(args.ledger)
    try:
        if args.command == "add":
            event = ledger.propose(_load_json(args.from_json))
            print(f"등록: {event['insight_id']} (PROPOSED)")
        elif args.command == "status":
            event = ledger.transition(
                args.insight_id, actor=args.actor, to_status=args.to, note=args.note,
                grade=args.grade, evidence_refs=args.evidence,
                implementation_refs=args.implementation)
            print(f"전이: {event['insight_id']} {event['from_status']} -> {event['to_status']}")
        elif args.command == "list":
            states = ledger.states()
            if args.status:
                states = {key: value for key, value in states.items()
                          if value["status"] == args.status}
            print(json.dumps(states, ensure_ascii=False, indent=2)
                  if args.as_json else render_markdown(states))
        elif args.command == "show":
            print(json.dumps(ledger.get(args.insight_id), ensure_ascii=False, indent=2))
        elif args.command == "verify":
            print(f"insight ledger OK: {ledger.verify_chain()} events")
        elif args.command == "template":
            print(json.dumps({
                "actor": args.actor,
                "title": "짧은 이름",
                "statement": "반증 가능한 공개 명제 또는 탐색 아이디어",
                "grade": "CONJECTURE",
                "scope": {"n": 12, "r": 6},
                "assumptions": [],
                "realizability": "REQUIRED",
                "invariance": {"relabel": "UNKNOWN", "reorient": "UNKNOWN"},
                "targets": ["search_objective"],
                "falsification_plan": ["작은 범위 또는 기존 corpus에서 먼저 반례 탐색"],
                "source_refs": [],
                "parent_ids": [],
                "claim_dsl": "",
            }, ensure_ascii=False, indent=2))
    except (InsightError, OSError, json.JSONDecodeError) as exc:
        print(f"오류: {exc}")
        return 1
    return 0


def _selftest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ledger.jsonl"
        ledger = InsightLedger(path)
        first = ledger.propose({
            "actor": "human",
            "title": "교집합 기반 탐색",
            "statement": "작은 circuit 교집합이 coverage 중첩을 줄일 수 있다.",
            "grade": "CONJECTURE",
            "scope": {"n": 12, "r": 6},
            "realizability": "REQUIRED",
            "invariance": {"relabel": "UNKNOWN", "reorient": "UNKNOWN"},
            "targets": ["invariant", "search_objective"],
            "falsification_plan": ["(6,3) 전수 corpus에서 상수 여부 확인"],
        })
        assert first["insight_id"] == "HI-0001"
        second = ledger.propose({
            "actor": "codex", "title": "파생 아이디어", "statement": "쌍별 에너지를 잰다.",
            "parent_ids": ["HI-0001"], "targets": ["invariant"],
        })
        assert second["insight_id"] == "HI-0002" and ledger.verify_chain() == 2
        ledger.transition("HI-0001", actor="codex", to_status="FORMALIZED",
                          note="재배향 불변 정수로 형식화")
        ledger.transition("HI-0001", actor="codex", to_status="TESTING",
                          note="작은 범위 반증 시작")
        try:
            ledger.transition("HI-0001", actor="codex", to_status="SUPPORTED",
                              note="근거 없는 승격")
            raise AssertionError("evidence 없는 SUPPORTED가 통과함")
        except InsightError:
            pass
        ledger.transition("HI-0001", actor="codex", to_status="SUPPORTED",
                          note="전수 범위에서 생존", grade="VERIFIED",
                          evidence_refs=["experiments/run_0001/falsification.json"])
        assert ledger.get("HI-0001")["status"] == "SUPPORTED"
        assert not hasattr(ledger, "update") and not hasattr(ledger, "delete")
        count = ledger.verify_chain()
        assert count == 5

        lines = path.read_text(encoding="utf-8").splitlines()
        tampered = json.loads(lines[0])
        tampered["proposal"]["grade"] = "PROVEN"
        path.write_text(json.dumps(tampered, ensure_ascii=False) + "\n"
                        + "\n".join(lines[1:]) + "\n", encoding="utf-8")
        try:
            ledger.verify_chain()
            raise AssertionError("ledger 개찬을 탐지하지 못함")
        except InsightError:
            pass
    print("insight_ledger core-contract assertions OK")


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    if len(os.sys.argv) == 1:
        _selftest()
    else:
        raise SystemExit(main())
