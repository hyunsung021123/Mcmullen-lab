"""scripts/export_dialogue_research.py — 우편함 DB의 연구 기록을 tracked Markdown 으로 내보낸다.

`math_dialogue.py` 의 자율 토론 루프는 설계상 tracked 파일을 절대 수정하지 않는다(0038 결정 5).
그래서 연구 기록 전체가 `.gitignore` 된 `local_runs/math_dialogue/dialogue.sqlite3` 안에만
남는다 — 사람이 승격시키기 전에 세션이 끊기면 **저장소에는 아무 기록도 남지 않는다.**
2026-08-12 에 Codex 루프가 토큰 소진으로 멈추면서 실제로 그 상태가 됐다.

이 스크립트는 그 간극을 메우는 **읽기 전용 내보내기**다:

  · DB 를 `mode=ro` 로만 열고 아무것도 쓰지 않는다.
  · 대화 계층의 등급을 **그대로** 옮긴다. 어떤 것도 승격하지 않고, 요약하거나 판정하지 않는다.
  · 산출물은 `UNASSESSED_DIALOGUE_ONLY` 배너를 달고 나간다. 이 문서는 연구 **이력**이며
    `research_log.md`(검증된 실험 이력)나 evidence DB 를 대체하지 않는다.

사용::

    python scripts/export_dialogue_research.py \
        --db local_runs/math_dialogue/dialogue.sqlite3 \
        --out knowledge/dialogue_research/2026-08-12-emergent-loop.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:                                              # 표시 계층 — Windows cp949 에서 죽지 않게
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                 # noqa: BLE001
    pass

AUTHORITY = "UNASSESSED_DIALOGUE_ONLY"


def _iso(ts: float | None) -> str:
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _rows(conn: sqlite3.Connection, table: str, order: str = "rowid") -> list[dict]:
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if table not in names:
        return []
    return [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY {order}")]


def _jlist(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return [str(value)]
    return [str(v) for v in parsed] if isinstance(parsed, list) else [str(parsed)]


def _bullets(items: list[str], indent: str = "  ") -> str:
    return "\n".join(f"{indent}- {item}" for item in items)


def _block(text: str | None) -> str:
    """긴 서술을 그대로 옮긴다 — 줄여 쓰면 등급 정보가 사라진다."""
    if not text:
        return ""
    return "\n".join(line.rstrip() for line in str(text).splitlines())


def export(db_path: Path, out_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    agents = _rows(conn, "agents", "name")
    topics = _rows(conn, "topics", "created_at")
    cycles = _rows(conn, "research_cycles", "created_at")
    events = _rows(conn, "research_events", "rowid")
    distils = _rows(conn, "distillation_attempts", "created_at")
    kinds = {r["kind"]: r["n"] for r in conn.execute(
        "SELECT kind, COUNT(*) AS n FROM messages GROUP BY kind ORDER BY n DESC")}
    msg_total = conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
    conn.close()

    digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
    lines: list[str] = []
    add = lines.append

    add("# 자율 토론 루프 연구 기록 — 2026-08-12")
    add("")
    add(f"> **권한: `{AUTHORITY}`.** 이 문서는 `math_dialogue.py` 우편함에 쌓인 대화 계층의")
    add("> 기록을 기계적으로 옮긴 것이다. **아무것도 증명되지 않았고 승격되지 않았다.**")
    add("> 각 항목의 등급(`ADVANCED`/`REFUTED`/`BLOCKED`/`LOW_YIELD`, `EXHAUSTED_ON_SCOPE` 등)은")
    add("> 원문 그대로이며, `om_core`·`falsify`·evidence DB 를 거친 것이 아니다.")
    add("> 검증된 실험 이력은 `research_log.md`, 승격된 근거는 evidence DB 를 보라.")
    add(">")
    add("> 내보내기 근거: `scripts/export_dialogue_research.py` (읽기 전용).")
    add(f"> 원본 DB `{db_path.as_posix()}` SHA-256 `{digest}`.")
    add("> 원문 응답 JSON 은 `local_runs/math_dialogue/responses/` 에 있고 gitignore 대상이다 —")
    add("> 이 문서가 저장소에 남는 유일한 기록이므로 원본 백업을 따로 보관할 것.")
    add("")
    add("## 규모")
    add("")
    add(f"- agent {len(agents)}명 · topic {len(topics)}개 · 메시지 {msg_total}건")
    add(f"- 연구 사이클 {len(cycles)}개 · research_event {len(events)}건 · 개념 증류 {len(distils)}건")
    if kinds:
        add(f"- 메시지 종류: {', '.join(f'{k} {v}' for k, v in kinds.items())}")
    add("")
    if agents:
        add("| agent | 역할 | 마지막 관측 |")
        add("|---|---|---|")
        for a in agents:
            add(f"| `{a['name']}` | {a.get('role', '')} | {_iso(a.get('last_seen'))} |")
        add("")

    # ── 연구 사이클별 event 흐름 ──────────────────────────────────────────
    by_cycle: dict[str, list[dict]] = {}
    for ev in events:
        by_cycle.setdefault(str(ev.get("cycle_id")), []).append(ev)

    if by_cycle:
        add("## 연구 사이클 — 가설에서 종합까지")
        add("")
        add("각 사이클은 `창발 탐사` 한 바퀴다. event 의 `outcome` 은 대화 계층의 자체 분류다.")
        add("")
        label_by_cycle = {}
        for c in cycles:
            cid = c.get("cycle_id") or c.get("id")
            if cid:
                label_by_cycle[str(cid)] = c.get("domain_label") or c.get("domain_key") or ""
        for cid, evs in by_cycle.items():
            label = label_by_cycle.get(cid, "")
            add(f"### `{cid}`" + (f" — {label}" if label else ""))
            add("")
            for ev in evs:
                head = f"**{ev.get('event_type')} / {ev.get('outcome')}**"
                add(f"- {head} — {ev.get('agent')}")
                if ev.get("summary"):
                    add(f"  - 요약: {_block(ev['summary'])}")
                if ev.get("approach"):
                    add(f"  - 접근: {_block(ev['approach'])}")
                clues = _jlist(ev.get("reusable_clues"))
                if clues:
                    add("  - 재사용 가능한 단서:")
                    add(_bullets(clues, "    "))
                nxt = _jlist(ev.get("next_questions"))
                if nxt:
                    add("  - 다음 질문:")
                    add(_bullets(nxt, "    "))
            add("")

    # ── topic 최종 종합 ───────────────────────────────────────────────────
    closed = [t for t in topics if t.get("final_summary")]
    if closed:
        add("## topic 최종 종합 (원문 전문)")
        add("")
        add("종합문은 `CLAIM / ASSUMPTIONS / WORK / STATUS / NEXT_TEST / ROUTE` 구조다.")
        add("**`STATUS` 절이 무엇이 확정이고 무엇이 미확인인지 구분한다 — 반드시 함께 읽을 것.**")
        add("")
        for t in closed:
            add(f"### {t.get('title')}")
            add("")
            add(f"- topic `{t.get('id')}` · 작성 `{t.get('final_by')}` "
                f"· 종류 `{t.get('final_kind')}` · 등급 `{t.get('final_grade')}`")
            add(f"- 종료 사유: `{t.get('close_reason')}` · 종료 시각 {_iso(t.get('closed_at'))}")
            if t.get("source_key"):
                add(f"- source_key: `{t['source_key']}`")
            refs = _jlist(t.get("final_evidence_refs"))
            if refs:
                add("- evidence_refs:")
                add(_bullets([f"`{r}`" for r in refs], "  "))
            add("")
            add(_block(t.get("final_summary")))
            add("")

    open_topics = [t for t in topics if t.get("status") == "open"]
    if open_topics:
        add("## 중단 시점에 열려 있던 topic")
        add("")
        for t in open_topics:
            add(f"- `{t.get('id')}` — {t.get('title')} (생성 {_iso(t.get('created_at'))})")
        add("")

    # ── 개념 증류 ────────────────────────────────────────────────────────
    if distils:
        add("## 개념 증류 — 다른 분야 언어로의 번역")
        add("")
        add("한 사이클의 결과를 다른 수학 분야 렌즈로 다시 쓴 것이다. **재표현이므로 원 결과의")
        add("증명 등급을 바꾸지 않는다.**")
        add("")
        for d in distils:
            add(f"### {d.get('domain_label')} — `{d.get('status')}`")
            add("")
            add(f"- 원 사이클 `{d.get('source_cycle_id')}` → 증류 `{d.get('attempt_cycle_id')}`")
            add(f"- 렌즈: {d.get('domain_lens')}")
            add("")
            if d.get("human_statement"):
                add(f"**사람이 읽는 문장** — {_block(d['human_statement'])}")
                add("")
            if d.get("mechanism"):
                add(f"**작동 원리** — {_block(d['mechanism'])}")
                add("")
            if d.get("minimal_example"):
                add(f"**최소 예** — {_block(d['minimal_example'])}")
                add("")
            if d.get("transfer_scope"):
                add(f"**전이 범위** — {_block(d['transfer_scope'])}")
                add("")
            for key, title in (("standard_objects", "표준 대상"),
                               ("limitations", "한계 (반드시 함께 읽을 것)"),
                               ("literature_queries", "문헌 검색어")):
                items = _jlist(d.get(key))
                if items:
                    add(f"**{title}**")
                    add(_bullets(items, ""))
                    add("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return {"out": str(out_path), "db_sha256": digest, "agents": len(agents),
            "topics": len(topics), "messages": msg_total, "cycles": len(cycles),
            "events": len(events), "distillations": len(distils),
            "bytes": out_path.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="우편함 연구 기록을 Markdown 으로 내보낸다")
    ap.add_argument("--db", default="local_runs/math_dialogue/dialogue.sqlite3")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    db = Path(args.db)
    if not db.exists():
        print(f"오류: DB 가 없다 — {db}", file=sys.stderr)
        return 2
    summary = export(db, Path(args.out))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
