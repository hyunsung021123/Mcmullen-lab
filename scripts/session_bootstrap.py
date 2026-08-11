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
    """git 출력을 문자열로. **인코딩을 반드시 UTF-8 로 고정한다** — Windows 기본
    코드페이지(cp949)로 읽으면 한국어 커밋 제목에서 UnicodeDecodeError 가 나고
    `stdout` 이 None 이 된다. 종전 호출은 전부 ASCII 만 돌려줘서 드러나지 않았다."""
    try:
        proc = subprocess.run(("git", "-C", ROOT) + args, capture_output=True,
                              encoding="utf-8", errors="replace", timeout=20)
        return (proc.stdout or "").strip()
    except (OSError, subprocess.SubprocessError, ValueError):
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


# 병합되면 프로젝트의 규칙·상태·판정 권한이 바뀌는 파일들. 다른 에이전트의 브랜치가
# 이것들을 건드리면 읽기 전에 지나치면 안 된다.
RULE_FILES = ("CLAUDE.md", "om_core.py", "COLLABORATION.md", "docs/STATE.md",
              "docs/DECISIONS.md", "questions/OPEN.md",
              "knowledge/insights/ledger.jsonl", "pyproject.toml")


def sibling_work(limit: int = 8, max_age_days: int = 21) -> list[str]:
    """**다른 에이전트의 미병합 브랜치**를 최근 순으로 보여준다.

    이 저장소는 Claude·Codex·ChatGPT 가 각자 브랜치에 쌓고 PR 로 합치는 구조라
    (`COLLABORATION.md`), 현재 브랜치의 파일만 보면 남의 작업을 통째로 놓친다.
    실제로 2026-08-12 에 Codex 가 `codex/69-math-dialogue-mailbox` 에 올린
    수학 토론 우편함(math_dialogue.py, 역할 프롬프트 8종)을 Claude 가 못 보고
    같은 것을 다시 설계하려 한 사고가 있었다. 그래서 부록에 상시로 띄운다."""
    head = _git("rev-parse", "--abbrev-ref", "HEAD")
    raw = _git("for-each-ref", "--sort=-committerdate",
               "--format=%(refname:short)\t%(committerdate:short)\t"
               "%(objectname:short)\t%(committerdate:unix)\t%(subject)",
               "refs/heads", "refs/remotes")
    if not raw:
        return ["- (git 정보를 읽지 못했다)"]
    cutoff = time.time() - max_age_days * 86400
    seen_sha: set[str] = set()
    out: list[str] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        name, date, sha, subject = parts[0], parts[1], parts[2], parts[4]
        # 오래된 브랜치는 대개 squash 병합 후 남은 껍데기다(원본 커밋이 조상이 아니라
        # 포함 검사로는 안 걸러진다). 최근성으로 자르는 편이 확실하다.
        try:
            if float(parts[3]) < cutoff:
                continue
        except ValueError:
            pass
        if name == head or name.endswith("/HEAD") or name in ("main", "develop"):
            continue
        if name.startswith("origin/") and name[7:] == head:
            continue
        ahead = _git("rev-list", "--count", f"HEAD..{name}")
        if not ahead or ahead == "0":
            continue                       # 이미 이 브랜치에 들어와 있다
        # 통합 브랜치에 이미 들어간 것은 '남의 진행 중 작업' 이 아니라 내 브랜치가
        # 아직 안 따라잡은 이력일 뿐이다. 그런 것까지 띄우면 정작 볼 것이 묻힌다.
        if any(_git("rev-list", "--count", f"{base}..{name}") == "0"
               for base in ("origin/develop", "develop", "origin/main", "main")
               if _git("rev-parse", "--verify", "--quiet", base)):
            continue
        if sha in seen_sha:
            continue                       # 로컬/원격 같은 커밋 중복 제거
        seen_sha.add(sha)
        touched = _git("diff", "--name-only", f"HEAD...{name}").splitlines()
        rules = sorted({f for f in touched if f in RULE_FILES})
        flag = f" ⚠ 규칙/상태 파일 변경: {', '.join(rules)}" if rules else ""
        out.append(f"- `{name}` +{ahead} · {date} · `{sha}` {subject[:60]}"
                   f" (파일 {len(touched)}개){flag}")
        if len(out) >= limit:
            break
    return out or ["- 미병합 타 브랜치 없음"]


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
             "### 다른 에이전트의 미병합 작업 (먼저 읽을 것)", ""]
    parts += sibling_work()
    parts += ["", "### 실험 워크스페이스 (exec)", ""]
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
