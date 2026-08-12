"""
sweep.py — 실현가능(realizable) 무작위 점배치 대량 스윕. d=5, n=12 프로젝트의 탐색 엔진.

## 왜 '실현가능' 경로인가

추상 OM 을 뒤지면 비실현 witness 를 먼저 만나게 되고, 그건 ν(d) 상한에 대해 아무것도
증명하지 않는다(`knowledge/problem.md` §3.2). 반면 이 스윕은 **R^d 의 정수 점배치에서
출발**하므로 witness 를 하나라도 찾으면 그 점배치 자체가 곧 증거다:

    (12,6) witness 발견  ⟹  ν(5) ≤ 11  (하한 2d+1=11 과 합쳐 ν(5)=11)

## 판정

`num_convex_reorientations(χ) == 0` 이 witness 다 (= 2^(n−1) 개 재배향 중 convex
position 이 되는 것이 하나도 없음). 계산은 `invariants` 의 hypercube 마스크 경로를
쓰고, **발견 시에는 `om_core.mcmullen_evaluate` 로 독립 재확인**한다.

## 근접 실패도 함께 수집한다

witness 를 못 찾아도 `convex_tope_ratio = convex 재배향 / tope 수` 가 가장 작은
구성들을 보관한다. 이것이 다음 라운드의 구조 분석 재료이고, 값의 분포 자체가
"무작위 탐색으로 도달 가능한가"에 대한 정량적 답이다.

## 진행 상황 확인

각 워커가 `<out>/worker_XX.json` 에 주기적으로 상태를 쓴다. 언제든:

    python sweep.py status --out sweep_d5

의존성: 표준 라이브러리 + om_core + invariants (+ multiprocessing).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from itertools import combinations

from om_core import Chirotope, mcmullen_evaluate

REPORT_EVERY_S = 5.0
KEEP_BEST = 12


# ═══════════════════════ 판정 (invariants 의 마스크 경로 재사용) ═══════════════════════
def _orbit_counts(ch: Chirotope) -> tuple[int, int]:
    """(tope 수, convex 재배향 수). 둘 다 전역반전 몫 (Z/2)^(n−1) 위에서 센다."""
    import invariants as INV
    data = INV._ORBIT.get(ch)
    return data["topes"], data["convex"]


def _encode(ch: Chirotope) -> str:
    subs = sorted(combinations(range(ch.n), ch.r))
    return "".join("+" if ch.signs[s] > 0 else "-" for s in subs)


# ═══════════════════════════ 워커 ═══════════════════════════
def worker(wid: int, n: int, r: int, coord: int, seed: int, out_dir: str,
           max_candidates: int, deadline: float) -> dict:
    rng = random.Random(seed)
    path = os.path.join(out_dir, f"worker_{wid:02d}.json")
    tried = tested = witnesses = 0
    best: list[tuple[float, dict]] = []          # (ratio, record) 오름차순 상위 KEEP_BEST
    t_start = time.time()
    last_report = 0.0

    def snapshot(final=False):
        rec = {"worker": wid, "n": n, "r": r, "coord": coord, "seed": seed,
               "tried": tried, "tested": tested, "witnesses": witnesses,
               "elapsed_s": round(time.time() - t_start, 1),
               "rate_per_s": round(tested / max(1e-9, time.time() - t_start), 2),
               "best": [b[1] for b in best], "final": final,
               "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.replace(tmp, path)
        return rec

    snapshot()
    while tested < max_candidates and time.time() < deadline:
        tried += 1
        pts = [tuple(rng.randint(-coord, coord) for _ in range(r - 1))
               for _ in range(n)]
        try:
            ch = Chirotope.from_points(pts)      # 비균일(일반위치 아님)이면 탈락
        except ValueError:
            continue
        tested += 1
        topes, convex = _orbit_counts(ch)
        ratio = convex / topes if topes else 1.0
        if convex == 0:
            # ★ witness 후보 — 즉시 om_core 로 독립 재확인 후 파일로 못박는다
            ev = mcmullen_evaluate(ch)
            hit = {"points": [list(p) for p in pts], "n": n, "r": r, "coord": coord,
                   "seed": seed, "worker": wid, "signs": _encode(ch),
                   "topes": topes, "convex_reorientations": convex,
                   "om_core_evaluate": ev,
                   "confirmed_by_om_core": bool(ev.get("witness")),
                   "at": time.strftime("%Y-%m-%d %H:%M:%S")}
            wf = os.path.join(out_dir, f"WITNESS_w{wid:02d}_{witnesses:03d}.json")
            with open(wf, "w", encoding="utf-8", newline="\n") as f:
                json.dump(hit, f, ensure_ascii=False, indent=1)
            witnesses += 1
            snapshot()
            if hit["confirmed_by_om_core"]:
                return snapshot(final=True)      # 목표 달성 — 이 워커는 즉시 종료
        if len(best) < KEEP_BEST or ratio < best[-1][0]:
            rec = {"ratio": round(ratio, 8), "convex": convex, "topes": topes,
                   "points": [list(p) for p in pts], "coord": coord}
            best.append((ratio, rec))
            best.sort(key=lambda x: x[0])
            del best[KEEP_BEST:]
        now = time.time()
        if now - last_report > REPORT_EVERY_S:
            last_report = now
            snapshot()
    return snapshot(final=True)


def _worker_entry(args):
    return worker(*args)


# ═══════════════════════════ 집계 ═══════════════════════════
def aggregate(out_dir: str) -> dict:
    recs = []
    for fn in sorted(os.listdir(out_dir)):
        if fn.startswith("worker_") and fn.endswith(".json"):
            try:
                with open(os.path.join(out_dir, fn), encoding="utf-8") as f:
                    recs.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                continue
    wit_files = sorted(fn for fn in os.listdir(out_dir) if fn.startswith("WITNESS_"))
    confirmed = []
    for fn in wit_files:
        with open(os.path.join(out_dir, fn), encoding="utf-8") as f:
            h = json.load(f)
        if h.get("confirmed_by_om_core"):
            confirmed.append({"file": fn, "points": h["points"],
                              "implied_upper_bound":
                                  h["om_core_evaluate"].get("implied_upper_bound")})
    all_best = sorted((b for rec in recs for b in rec.get("best", [])),
                      key=lambda b: b["ratio"])[:KEEP_BEST]
    tested = sum(r.get("tested", 0) for r in recs)
    tried = sum(r.get("tried", 0) for r in recs)
    elapsed = max((r.get("elapsed_s", 0) for r in recs), default=0)
    return {"workers": len(recs), "active": sum(1 for r in recs if not r.get("final")),
            "tried": tried, "tested": tested,
            "general_position_rate": (tested / tried) if tried else None,
            "witnesses_confirmed": len(confirmed), "witness_files": confirmed,
            "elapsed_s": elapsed,
            "rate_per_s": round(sum(r.get("rate_per_s", 0) for r in recs), 1),
            "best_ratios": [b["ratio"] for b in all_best],
            "best": all_best,
            "scope": {"n": recs[0]["n"], "r": recs[0]["r"]} if recs else {}}


def print_status(out_dir: str) -> int:
    if not os.path.isdir(out_dir):
        print(f"진행 폴더가 없습니다: {out_dir}")
        return 1
    a = aggregate(out_dir)
    sc = a.get("scope", {})
    print(f"[sweep {out_dir}] n={sc.get('n')} r={sc.get('r')} "
          f"워커 {a['workers']}개 (실행 중 {a['active']})")
    print(f"  검사한 후보 {a['tested']:,}개 "
          f"(일반위치 통과율 {a['general_position_rate']:.1%}) "
          f"| 경과 {a['elapsed_s']:.0f}s | 초당 {a['rate_per_s']}개")
    if a["witnesses_confirmed"]:
        print(f"  ★★ witness {a['witnesses_confirmed']}건 확인됨 (om_core 재확인 완료)")
        for w in a["witness_files"]:
            print(f"     {w['file']} → 상한 {w['implied_upper_bound']}")
    else:
        print(f"  witness 0건. 가장 가까운 근접 실패 convex/tope 비: "
              f"{a['best_ratios'][:5]}")
        if a["best"]:
            b = a["best"][0]
            print(f"     최선: convex 재배향 {b['convex']} / tope {b['topes']} "
                  f"(coord={b['coord']})")
    # 기대 도달 시간 추정 (관측 witness 가 있을 때만 의미 있음)
    if a["tested"] and not a["witnesses_confirmed"]:
        print(f"  → 이 표본에서 witness 비율의 95% 신뢰 상한 ≈ "
              f"{3.0 / a['tested']:.3%} (0건 관측 시 3/n 법칙)")
    return 0


# ═══════════════════════════ CLI ═══════════════════════════
def cmd_run(args) -> int:
    import multiprocessing as mp

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(out_dir):
        if fn.startswith("worker_"):
            os.remove(os.path.join(out_dir, fn))

    coords = [int(c) for c in args.coords.split(",")]
    deadline = time.time() + args.hours * 3600
    per_worker = args.max_candidates // args.workers if args.max_candidates else 10 ** 12

    jobs = []
    for i in range(args.workers):
        jobs.append((i, args.n, args.r, coords[i % len(coords)],
                     args.seed + 1000 * i, out_dir, per_worker, deadline))

    meta = {"n": args.n, "r": args.r, "d": args.r - 1, "workers": args.workers,
            "coords": coords, "seed_base": args.seed, "hours": args.hours,
            "max_candidates": args.max_candidates,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "how": ("R^(r-1) 의 [-coord,coord]^(r-1) 정수 격자에서 n 점을 균등 무작위로 "
                    "뽑아 동차화 → uniform chirotope. witness 판정은 "
                    "num_convex_reorientations==0, 발견 시 om_core.mcmullen_evaluate "
                    "로 독립 재확인.")}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8",
              newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    print(f"[sweep] n={args.n} r={args.r} (d={args.r-1}) 워커 {args.workers}개 "
          f"coord={coords} 최대 {args.hours}시간")
    print(f"  진행 확인:  python sweep.py status --out {out_dir}")
    with mp.Pool(args.workers) as pool:
        pool.map(_worker_entry, jobs)
    print("\n[sweep] 종료")
    return print_status(out_dir)


def main(argv=None) -> int:
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(prog="sweep",
                                 description="실현가능 무작위 점배치 대량 스윕")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="스윕 실행")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--r", type=int, required=True)
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--coords", default="3,5,9,15,30",
                   help="워커별 좌표 범위(쉼표). 한 격자에만 갇히지 않게 분산")
    p.add_argument("--seed", type=int, default=20260809)
    p.add_argument("--hours", type=float, default=1.0)
    p.add_argument("--max-candidates", dest="max_candidates", type=int, default=0,
                   help="0 이면 시간 제한만 적용")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="진행 상황")
    p.add_argument("--out", required=True)
    p.set_defaults(func=lambda a: print_status(a.out))

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
