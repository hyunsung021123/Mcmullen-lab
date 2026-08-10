"""session_bootstrap.py — `docs/STATE.md` 의 자동 생성 부록을 갱신한다.

세션이 초기화돼도 맥락이 복원되게 하려면 상태 문서가 **최신**이어야 하는데, 손으로 쓰는
문서는 반드시 낡는다. 그래서 기계가 알 수 있는 것(최근 실험, insight 상태, 실행 잠금,
결과 파일)은 여기서 뽑아 `<!-- BOOTSTRAP:BEGIN -->` 블록만 덮어쓴다.
사람이 쓴 §1~§5 는 건드리지 않는다.

    python scripts/session_bootstrap.py            # STATE.md 갱신
    python scripts/session_bootstrap.py --print    # 출력만 (파일 수정 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "docs", "STATE.md")
BEGIN, END = "<!-- BOOTSTRAP:BEGIN -->", "<!-- BOOTSTRAP:END -->"


def _git(*args) -> str:
    try:
        return subprocess.run(("git", "-C", ROOT) + args, capture_output=True,
                              text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def recent_log(k: int = 8) -> list[str]:
    path = os.path.join(ROOT, "research_log.md")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        lines = [ln.rstrip() for ln in fh if ln.startswith("- ")]
    return lines[-k:]


def insight_states() -> list[str]:
    try:
        sys.path.insert(0, ROOT)
        from insight_ledger import InsightLedger, DEFAULT_PATH
        states = InsightLedger(str(DEFAULT_PATH)).states()
    except Exception as exc:                       # noqa: BLE001 — 부록이 본체를 막으면 안 된다
        return [f"(ledger 읽기 실패: {exc})"]
    out = []
    for key in sorted(states):
        rec = states[key]
        out.append(f"| `{key}` | {rec.get('status')} | {rec.get('grade') or '—'} | "
                   f"{(rec.get('title') or '')[:44]} |")
    return out


def exec_status(exec_root: str) -> list[str]:
    man = os.path.join(exec_root, ".exec_sync.json")
    lock = os.path.join(exec_root, ".exec_run.lock")
    out = []
    if os.path.exists(man):
        with open(man, encoding="utf-8") as fh:
            rec = json.load(fh)
        out.append(f"- 마지막 동기화: `{rec.get('snapshot_id')}` "
                   f"({rec.get('synced_at')}, 파일 {rec.get('num_files')}개)")
    else:
        out.append("- exec 동기화 이력 없음")
    if os.path.exists(lock):
        with open(lock, encoding="utf-8") as fh:
            rec = json.load(fh)
        out.append(f"- **실험 진행 중**: {rec.get('note')} "
                   f"(시작 {rec.get('started_at')}, snapshot `{rec.get('snapshot_id')}`)")
        out.append("  → 이 실험이 끝나기 전에는 `sync_exec.py sync` 가 거부된다(규약 3)")
    else:
        out.append("- 실행 잠금 없음 (sync 가능)")
    return out


def result_files() -> list[str]:
    """witness/근접실패 산출물 — 어떤 결론이 이미 확보돼 있는지 한눈에."""
    out = []
    for name in sorted(os.listdir(ROOT)):
        if not name.endswith(".json"):
            continue
        if not any(k in name for k in ("witness", "nearmiss", "cegis", "sweep")):
            continue
        try:
            with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(rec, list):
            rec = rec[0] if rec else {}
        bits = []
        for key in ("status", "n", "r", "d", "num_convex_reorientations",
                    "best_f", "minimal_witness_n", "bound_gain"):
            if key in rec:
                bits.append(f"{key}={rec[key]}")
        scope = rec.get("scope") or {}
        real = scope.get("realizability") or rec.get("realizability")
        if real:
            bits.append(f"realizability={str(real)[:24]}")
        out.append(f"| `{name}` | {', '.join(bits) or '—'} |")
    return out


def open_questions() -> list[str]:
    path = os.path.join(ROOT, "questions", "OPEN.md")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("## QQ-"):
                out.append("- " + line[3:].strip())
    return out


def render() -> str:
    exec_root = os.path.abspath(os.path.join(ROOT, "..", "Mcmullen-lab-exec"))
    parts = [BEGIN, "",
             f"_{time.strftime('%Y-%m-%d %H:%M:%S')} 자동 생성 "
             f"(`scripts/session_bootstrap.py`)._", "",
             f"**저장소**: `{_git('rev-parse', '--abbrev-ref', 'HEAD')}` @ "
             f"`{_git('rev-parse', '--short', 'HEAD')}`"
             f"{' · 미커밋 변경 있음' if _git('status', '--porcelain') else ''}", "",
             "### 실험 워크스페이스 (exec)", ""]
    parts += exec_status(exec_root)
    parts += ["", "### 최근 연구 기록 (research_log.md 끝 8줄)", ""]
    parts += recent_log()
    parts += ["", "### 확보된 산출물", "",
              "| 파일 | 요약 |", "|---|---|"]
    parts += result_files() or ["| — | 없음 |"]
    parts += ["", "### 인간 insight 상태 (knowledge/insights/ledger.jsonl)", "",
              "| ID | 상태 | 등급 | 제목 |", "|---|---|---|---|"]
    parts += insight_states() or ["| — | — | — | 없음 |"]
    parts += ["", "### 열린 자문 질문 (questions/OPEN.md)", ""]
    parts += open_questions() or ["- 없음"]
    parts += ["", END]
    return "\n".join(parts)


def main(argv=None) -> int:
    try:
        sys.path.insert(0, ROOT)
        from console import enable_utf8_stdout
        enable_utf8_stdout()
    except ImportError:
        pass
    ap = argparse.ArgumentParser(prog="session_bootstrap",
                                 description="docs/STATE.md 자동 부록 갱신")
    ap.add_argument("--print", action="store_true", dest="only_print")
    args = ap.parse_args(argv)

    block = render()
    if args.only_print:
        print(block)
        return 0
    with open(STATE, encoding="utf-8") as fh:
        text = fh.read()
    i, j = text.find(BEGIN), text.find(END)
    if i < 0 or j < 0:
        print(f"BOOTSTRAP 표식이 없다: {STATE}")
        return 1
    new = text[:i] + block + text[j + len(END):]
    with open(STATE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new)
    print(f"갱신: {STATE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
