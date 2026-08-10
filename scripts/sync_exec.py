"""sync_exec.py — main(단일 진실) → exec(동결 스냅샷) 동기화와 실행 잠금.

## 저장소 운영 규약 (사용자 지정)

  1. **main 은 항상 접근·수정이 가능하다.** 단일 진실은 언제나 main 이다.
  2. **exec 는 실험 직전에 main 과 동기화된다.** 실험은 항상 그 시점의 main 스냅샷 위에서
     돈다.
  3. **실험 진행 중에는 main 이 변해도 exec 를 건드리지 않는다.** 실행 중 코드가 바뀌면
     결과의 provenance 가 깨지기 때문이다.

이 규약을 문서가 아니라 **코드로 강제**한다. 3번은 사람이 기억으로 지킬 수 없다.

    sync    main 의 소스를 exec 로 미러링하고 매니페스트를 남긴다. 잠금이 있으면 거부.
    lock    실험 시작 — 이후 sync 가 거부된다.
    unlock  실험 종료 — 다시 sync 가 가능해진다.
    verify  exec 가 매니페스트와 같은지(실행 중 오염 여부) + main 이 그 뒤로 변했는지.
    status  한눈에 보기.

## 실행 산출물은 절대 건드리지 않는다

미러링은 **매니페스트 기반**이다. 지운 파일은 "직전 매니페스트에 있었는데 지금 main 에
없는 것"뿐이다. exec 가 스스로 만든 것(worker 스냅샷, 로그, 중간 결과)은 main 에 존재한
적이 없으므로 매니페스트에도 없고, 따라서 **삭제 대상이 되지 않는다.**

## provenance

동기화할 때마다 exec 에 `.exec_sync.json` 을 남긴다: main 의 커밋 SHA + 미러링한 모든
파일의 sha256 + 시각. 실험 결과에 이 매니페스트의 `snapshot_id` 를 함께 적으면 "어떤
코드 상태에서 나온 결과인가"가 사후에 정확히 복원된다.

의존성: 표준 라이브러리만.

    python scripts/sync_exec.py sync   --exec ../Mcmullen-lab-exec
    python scripts/sync_exec.py lock   --exec ../Mcmullen-lab-exec --note "(10,5) 덮개-CEGIS"
    python scripts/sync_exec.py verify --exec ../Mcmullen-lab-exec
    python scripts/sync_exec.py unlock --exec ../Mcmullen-lab-exec
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

MANIFEST = ".exec_sync.json"
LOCK = ".exec_run.lock"

# 미러링에서 제외 — 도구 캐시, 가상환경, 그리고 '실행 산출물'.
EXCLUDE_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    "local_runs", "node_modules",
}
EXCLUDE_DIR_PREFIXES = ("climb_", "sweep_", "run_")
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp", ".lock", ".egg-info")
EXCLUDE_NAMES = {MANIFEST, LOCK, "memory.json", "memory_llm_test.json",
                 "results_llm_test.json", "autopull.log"}


def _skip_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS or name.startswith(EXCLUDE_DIR_PREFIXES) \
        or name.endswith(".egg-info")


def _skip_file(name: str) -> bool:
    return name in EXCLUDE_NAMES or name.endswith(EXCLUDE_SUFFIXES)


def source_files(root: str) -> list[str]:
    """미러링 대상 파일의 상대경로 목록 (정렬)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not _skip_dir(d))
        for fn in sorted(filenames):
            if _skip_file(fn):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            out.append(rel.replace("\\", "/"))
    return sorted(out)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(root: str) -> dict:
    def run(*a):
        try:
            return subprocess.run(("git", "-C", root) + a, capture_output=True,
                                  text=True, timeout=20).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    return {"sha": run("rev-parse", "HEAD"),
            "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(run("status", "--porcelain"))}


def read_manifest(exec_root: str) -> dict | None:
    p = os.path.join(exec_root, MANIFEST)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def read_lock(exec_root: str) -> dict | None:
    p = os.path.join(exec_root, LOCK)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"note": "(잠금 파일 파손 — 그래도 잠금으로 취급한다)"}


# ── 명령 ─────────────────────────────────────────────────────────────
def cmd_sync(main_root: str, exec_root: str, *, dry_run: bool = False,
             force: bool = False) -> int:
    lock = read_lock(exec_root)
    if lock and not force:
        print(f"거부: exec 가 실험 중이다 — {lock.get('note', '')}"
              f" (시작 {lock.get('started_at')})")
        print("  규약 3: 실행 중에는 main 이 변해도 exec 를 건드리지 않는다.")
        print("  정말 덮어써야 하면 unlock 후 다시 sync 하라.")
        return 2

    files = source_files(main_root)
    prev = read_manifest(exec_root) or {}
    prev_files = set((prev.get("files") or {}).keys())

    copied = skipped = 0
    entries: dict[str, str] = {}
    for rel in files:
        src = os.path.join(main_root, rel)
        dst = os.path.join(exec_root, rel)
        digest = sha256(src)
        entries[rel] = digest
        same = os.path.exists(dst) and sha256(dst) == digest
        if same:
            skipped += 1
            continue
        copied += 1
        if not dry_run:
            os.makedirs(os.path.dirname(dst) or exec_root, exist_ok=True)
            shutil.copy2(src, dst)

    # 삭제: 직전 매니페스트에 있었는데 main 에서 사라진 것만. exec 가 스스로 만든
    # 실행 산출물은 매니페스트에 없으므로 절대 지워지지 않는다.
    removed = []
    for rel in sorted(prev_files - set(files)):
        dst = os.path.join(exec_root, rel)
        if os.path.exists(dst):
            removed.append(rel)
            if not dry_run:
                os.remove(dst)

    head = git_head(main_root)
    snapshot_id = hashlib.sha256(
        json.dumps(entries, sort_keys=True).encode()).hexdigest()[:16]
    man = {"snapshot_id": snapshot_id,
           "synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "main_root": os.path.abspath(main_root),
           "main_git": head, "num_files": len(entries),
           "copied": copied, "skipped": skipped, "removed": removed,
           "files": entries}
    if not dry_run:
        with open(os.path.join(exec_root, MANIFEST), "w",
                  encoding="utf-8", newline="\n") as f:
            json.dump(man, f, ensure_ascii=False, indent=1)

    print(f"[sync] {'(모의) ' if dry_run else ''}main → exec")
    print(f"  main: {head['branch']} @ {head['sha'][:8]}"
          f"{' (미커밋 변경 있음)' if head['dirty'] else ''}")
    print(f"  파일 {len(entries)}개 | 복사 {copied} · 동일 {skipped} · 삭제 {len(removed)}")
    if removed:
        print(f"  삭제됨: {', '.join(removed[:8])}"
              + (" …" if len(removed) > 8 else ""))
    print(f"  snapshot_id = {snapshot_id}")
    print("  → 실험을 시작하려면: sync_exec.py lock --exec <path> --note '...'")
    return 0


def cmd_lock(exec_root: str, note: str) -> int:
    if read_lock(exec_root):
        print("이미 잠겨 있다. 먼저 unlock 하라.")
        return 2
    man = read_manifest(exec_root)
    if man is None:
        print("거부: 매니페스트가 없다. 규약 2 — 실험 직전에 먼저 sync 하라.")
        return 2
    rec = {"note": note, "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "snapshot_id": man["snapshot_id"], "pid": os.getpid()}
    with open(os.path.join(exec_root, LOCK), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print(f"[lock] 실험 시작 — {note}")
    print(f"  snapshot_id = {man['snapshot_id']} (결과에 이 값을 함께 기록할 것)")
    return 0


def cmd_unlock(exec_root: str) -> int:
    lock = read_lock(exec_root)
    if not lock:
        print("잠겨 있지 않다.")
        return 0
    os.remove(os.path.join(exec_root, LOCK))
    print(f"[unlock] 실험 종료 — {lock.get('note', '')} "
          f"(시작 {lock.get('started_at')})")
    return 0


def cmd_verify(main_root: str, exec_root: str) -> int:
    man = read_manifest(exec_root)
    if man is None:
        print("매니페스트 없음 — 한 번도 sync 하지 않았다.")
        return 1
    # (a) exec 가 스냅샷에서 벗어났는가 (실행 중 오염)
    drift = []
    for rel, digest in man["files"].items():
        dst = os.path.join(exec_root, rel)
        if not os.path.exists(dst):
            drift.append(("삭제됨", rel))
        elif sha256(dst) != digest:
            drift.append(("변경됨", rel))
    # (b) main 이 sync 이후 변했는가 (정상 — 규약 1)
    ahead = []
    cur = source_files(main_root)
    for rel in cur:
        d = sha256(os.path.join(main_root, rel))
        if man["files"].get(rel) != d:
            ahead.append(rel)
    ahead += [r for r in man["files"] if r not in set(cur)]

    lock = read_lock(exec_root)
    print(f"[verify] snapshot_id = {man['snapshot_id']} "
          f"(sync {man['synced_at']})")
    print(f"  실험 중: {'예 — ' + lock.get('note', '') if lock else '아니오'}")
    if drift:
        print(f"  ⚠ exec 오염 {len(drift)}건 — 스냅샷과 다르다:")
        for kind, rel in drift[:12]:
            print(f"     {kind}: {rel}")
        print("     이 상태의 실험 결과는 매니페스트로 재현되지 않는다.")
    else:
        print("  exec 는 스냅샷과 정확히 일치한다.")
    print(f"  main 은 이후 {len(ahead)}개 파일이 앞서 있다"
          f"{' (실험 끝나고 다시 sync 하면 된다)' if ahead else ''}")
    if ahead:
        for rel in sorted(ahead)[:12]:
            print(f"     {rel}")
    return 1 if drift else 0


def cmd_status(main_root: str, exec_root: str) -> int:
    man = read_manifest(exec_root)
    lock = read_lock(exec_root)
    head = git_head(main_root)
    print(f"main : {os.path.abspath(main_root)}")
    print(f"       {head['branch']} @ {head['sha'][:8]}"
          f"{' (미커밋 변경 있음)' if head['dirty'] else ''}")
    print(f"exec : {os.path.abspath(exec_root)}")
    if man:
        print(f"       snapshot {man['snapshot_id']} · {man['num_files']}개 파일 "
              f"· sync {man['synced_at']}")
    else:
        print("       (동기화된 적 없음)")
    print(f"상태 : {'실험 중 — ' + lock.get('note', '') if lock else '유휴 (sync 가능)'}")
    return 0


# ── 자체 테스트 ───────────────────────────────────────────────────────
def selftest() -> int:
    """임시 디렉터리로 규약 3가지를 실제로 시험한다."""
    import tempfile
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'OK ' if good else 'FAIL'} {label}: {got}"
              + ("" if good else f" (기대 {want})"))

    with tempfile.TemporaryDirectory() as tmp:
        m = os.path.join(tmp, "main"); e = os.path.join(tmp, "exec")
        os.makedirs(os.path.join(m, "sub")); os.makedirs(e)
        for rel, body in [("a.py", "print(1)\n"), ("sub/b.py", "print(2)\n"),
                          ("gone.py", "x=0\n")]:
            with open(os.path.join(m, rel), "w", newline="\n") as f:
                f.write(body)

        print("\n[규약 2] 실험 직전 동기화")
        chk("sync 성공", cmd_sync(m, e), 0)
        chk("exec 에 파일 도착", os.path.exists(os.path.join(e, "sub", "b.py")), True)

        # exec 가 스스로 만든 실행 산출물
        os.makedirs(os.path.join(e, "climb_test"))
        with open(os.path.join(e, "climb_test", "worker_00.json"), "w") as f:
            f.write("{}")
        with open(os.path.join(e, "out.json"), "w") as f:
            f.write("{}")

        print("\n[규약 3] 실행 중에는 main 이 변해도 exec 를 건드리지 않는다")
        chk("lock", cmd_lock(e, "테스트 실험"), 0)
        with open(os.path.join(m, "a.py"), "w", newline="\n") as f:
            f.write("print('main 이 변했다')\n")
        chk("잠긴 동안 sync 거부", cmd_sync(m, e), 2)
        with open(os.path.join(e, "a.py")) as f:
            chk("exec 는 그대로", f.read().strip(), "print(1)")
        chk("verify: 오염 없음", cmd_verify(m, e), 0)

        print("\n[규약 1] 실험 종료 후 다시 동기화")
        chk("unlock", cmd_unlock(e), 0)
        os.remove(os.path.join(m, "gone.py"))
        chk("sync 성공", cmd_sync(m, e), 0)
        with open(os.path.join(e, "a.py")) as f:
            chk("main 변경 반영", f.read().strip(), "print('main 이 변했다')")
        chk("main 에서 지운 파일은 exec 에서도 삭제",
            os.path.exists(os.path.join(e, "gone.py")), False)

        print("\n[불변] 실행 산출물은 절대 삭제되지 않는다")
        chk("climb_test/ 보존",
            os.path.exists(os.path.join(e, "climb_test", "worker_00.json")), True)
        chk("out.json 보존", os.path.exists(os.path.join(e, "out.json")), True)

        print("\n[오염 탐지] 실행 중 exec 를 손대면 잡아낸다")
        cmd_lock(e, "오염 시험")
        with open(os.path.join(e, "a.py"), "a", newline="\n") as f:
            f.write("# 실행 중 손댐\n")
        chk("verify 가 오염을 보고", cmd_verify(m, e), 1)
        cmd_unlock(e)

    print("\n" + ("전체 통과" if ok else "실패 항목 있음"))
    return 0 if ok else 1


def main(argv=None) -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # scripts/ 에서 실행하면 저장소 루트가 sys.path 에 없다 — console 을 쓰려면 넣어준다.
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        from console import enable_utf8_stdout
        enable_utf8_stdout()
    except ImportError:
        pass
    ap = argparse.ArgumentParser(
        prog="sync_exec", description="main(단일 진실) → exec(동결 스냅샷) 동기화")
    ap.add_argument("--main", default=here, help="기본값: 이 스크립트의 저장소 루트")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("sync", "lock", "unlock", "verify", "status"):
        p = sub.add_parser(name)
        p.add_argument("--exec", dest="exec_root", required=True)
        if name == "sync":
            p.add_argument("--dry-run", action="store_true")
            p.add_argument("--force", action="store_true",
                           help="잠금을 무시한다 (규약 3 위반 — 정말 필요할 때만)")
        if name == "lock":
            p.add_argument("--note", required=True, help="무슨 실험인지 한 줄")
    sub.add_parser("selftest")

    args = ap.parse_args(argv)
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "sync":
        return cmd_sync(args.main, args.exec_root,
                        dry_run=args.dry_run, force=args.force)
    if args.cmd == "lock":
        return cmd_lock(args.exec_root, args.note)
    if args.cmd == "unlock":
        return cmd_unlock(args.exec_root)
    if args.cmd == "verify":
        return cmd_verify(args.main, args.exec_root)
    return cmd_status(args.main, args.exec_root)


if __name__ == "__main__":
    sys.exit(main())
