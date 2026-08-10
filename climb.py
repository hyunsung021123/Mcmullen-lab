"""
climb.py — 목적함수 국소탐색(hill-climbing)으로 witness 점배치를 구성한다.

## 왜 이게 필요한가 (실측 근거)

`sweep.py` 로 (10,5)=d=4 에서 **실현가능 무작위 표본 153,379개를 검사해 witness 0건**을
얻었다(95% 신뢰 상한 0.002%). 그런데 d=4 의 witness 는 문헌상 **존재한다**
(`knowledge/known_results.md` — Forge–Las Vergnas–Schuchert 의 10점 구성). 즉

    witness 는 존재하지만 무작위 표집으로는 사실상 도달할 수 없다.

따라서 필요한 것은 표본 수가 아니라 **방향**이다. 이 모듈은 witness 를 0/1 목표가
아니라 **연속적인 목적함수**로 바꿔 내려간다:

    목적함수  f(점배치) = num_convex_reorientations  (0 이면 witness)

무작위 표본의 최선이 d=4 에서 f=4 (tope 256개 중 convex 4개)였으므로, 남은 거리는
'4'다 — 국소탐색이 메울 수 있는 거리인지가 이 실험의 질문이다.

## 방법론 검증을 먼저 한다 (중요)

d=5 에 바로 쓰지 않는다. **답이 있다고 알려진 d=4 에서 먼저 보정**한다:
국소탐색이 (10,5) witness 를 실제로 찾아내면 그때 (12,6) 에 적용할 근거가 생긴다.
못 찾으면 그 사실 자체가 "이 방법으로는 d=5 도 안 된다"는 결론이며, 시간을 낭비하기
전에 알 수 있다. 이것이 `AGENTS.md` 의 "먼저 반증을 시도한다" 규율의 탐색 판본이다.

## 탐색 규칙

  · 상태: Z^d 안의 n 점 (좌표는 [-C, C])
  · 이동: 점 하나를 골라 좌표 일부를 작게 흔들거나 재표집
  · 수용: f 가 줄면 항상, 같으면 항상(평탄면 임의보행), 늘면 온도에 따라 가끔
  · 재시작: 개선 없이 stall_limit 스텝이 지나면 새 임의 시작점으로

f 가 0 이 되면 즉시 `om_core.mcmullen_evaluate` 로 독립 재확인하고 점배치를 파일로
못박는다. **국소탐색은 판정하지 않는다 — 판정은 언제나 om_core 다.**

진행 확인:  python climb.py status --out climb_d4
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from itertools import combinations

from om_core import Chirotope, mcmullen_evaluate

REPORT_EVERY_S = 5.0


def _objective(pts) -> tuple[int, int] | None:
    """(convex 재배향 수, tope 수). 일반위치가 아니면 None."""
    import invariants as INV
    try:
        ch = Chirotope.from_points(pts)
    except ValueError:
        return None
    d = INV._ORBIT.get(ch)
    return d["convex"], d["topes"]


def _encode(pts, n, r) -> str:
    ch = Chirotope.from_points(pts)
    subs = sorted(combinations(range(n), r))
    return "".join("+" if ch.signs[s] > 0 else "-" for s in subs)


def _random_pts(rng, n, dim, coord):
    return [tuple(rng.randint(-coord, coord) for _ in range(dim)) for _ in range(n)]


def _perturb(rng, pts, dim, coord, strength):
    """점 하나를 골라 좌표 일부를 흔든다. strength 가 크면 더 과감하게."""
    new = list(pts)
    i = rng.randrange(len(pts))
    p = list(new[i])
    if rng.random() < 0.25:
        p = [rng.randint(-coord, coord) for _ in range(dim)]     # 완전 재표집
    else:
        k = rng.randint(1, dim)
        for j in rng.sample(range(dim), k):
            p[j] = max(-coord, min(coord, p[j] + rng.randint(-strength, strength)))
    new[i] = tuple(p)
    return new


def _load_checkpoint(path: str):
    """이전 실행의 스냅샷에서 (f, topes, pts, evals, restarts, hist) 복원."""
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    pts = rec.get("best_points")
    if not pts:
        return None
    return {"pts": [tuple(p) for p in pts], "f": rec.get("best_f"),
            "topes": rec.get("best_topes"), "evals": rec.get("evals", 0),
            "restarts": rec.get("restarts", 0),
            "hist": {int(k): v for k, v in (rec.get("f_histogram") or {}).items()}}


def worker(wid: int, n: int, r: int, coord: int, seed: int, out_dir: str,
           deadline: float, stall_limit: int, temp0: float,
           resume: bool = False) -> dict:
    rng = random.Random(seed)
    dim = r - 1
    path = os.path.join(out_dir, f"worker_{wid:02d}.json")
    t_start = time.time()
    evals = restarts = witnesses = 0
    global_best = None          # (f, topes, pts)
    last_report = 0.0
    hist: dict[int, int] = {}   # f 값별 도달 횟수 — 지형의 모양을 본다
    resumed_from = None

    # ── 체크포인트 복원 ──────────────────────────────────────────────
    # 이 탐색은 사용자의 PC 에서 돌고, PC 를 끄면 프로세스가 죽는다. 매 스냅샷에
    # 최선 점배치가 들어 있으므로, 재시작 시 그 지점에서 이어갈 수 있어야 한다.
    # 복원값도 그대로 믿지 않고 반드시 다시 계산해 검증한다.
    if resume:
        ck = _load_checkpoint(path)
        if ck:
            got = _objective(ck["pts"])
            evals += 1
            if got is not None:
                global_best = (got[0], got[1], ck["pts"])
                evals += ck["evals"]
                restarts = ck["restarts"]
                hist = ck["hist"]
                resumed_from = {"f_recomputed": got[0], "f_recorded": ck["f"],
                                "consistent": got[0] == ck["f"]}

    def snapshot(final=False):
        rec = {"worker": wid, "n": n, "r": r, "coord": coord, "seed": seed,
               "evals": evals, "restarts": restarts, "witnesses": witnesses,
               "elapsed_s": round(time.time() - t_start, 1),
               "rate_per_s": round(evals / max(1e-9, time.time() - t_start), 1),
               "best_f": (global_best[0] if global_best else None),
               "best_topes": (global_best[1] if global_best else None),
               "best_points": ([list(p) for p in global_best[2]]
                               if global_best else None),
               "f_histogram": dict(sorted(hist.items())[:16]),
               "resumed_from": resumed_from,
               "final": final, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.replace(tmp, path)
        return rec

    # 복원에 성공했으면 첫 라운드는 임의 시작점 대신 그 지점에서 이어간다.
    pending_resume = global_best is not None

    snapshot()
    while time.time() < deadline:
        # ── 새 시작점 ──
        cur = None
        if pending_resume:
            cur = global_best
            pending_resume = False
        while cur is None and time.time() < deadline:
            pts = _random_pts(rng, n, dim, coord)
            got = _objective(pts)
            evals += 1
            if got is not None:
                cur = (got[0], got[1], pts)
        if cur is None:
            break
        restarts += 1
        stall = 0
        while stall < stall_limit and time.time() < deadline:
            temp = temp0 * math.exp(-3.0 * stall / max(1, stall_limit))
            strength = 1 if rng.random() < 0.7 else max(1, coord // 3)
            cand = _perturb(rng, cur[2], dim, coord, strength)
            got = _objective(cand)
            evals += 1
            if got is None:
                stall += 1
                continue
            f_new, topes_new = got
            f_old = cur[0]
            accept = (f_new < f_old or f_new == f_old or
                      (temp > 0 and rng.random() < math.exp(-(f_new - f_old) / temp)))
            if f_new < f_old:
                stall = 0
            else:
                stall += 1
            if accept:
                cur = (f_new, topes_new, cand)
                hist[f_new] = hist.get(f_new, 0) + 1
                if global_best is None or f_new < global_best[0]:
                    global_best = cur
                    snapshot()
                if f_new == 0:
                    ev = mcmullen_evaluate(Chirotope.from_points(cand))
                    hit = {"points": [list(p) for p in cand], "n": n, "r": r,
                           "coord": coord, "seed": seed, "worker": wid,
                           "signs": _encode(cand, n, r),
                           "topes": topes_new, "convex_reorientations": 0,
                           "om_core_evaluate": ev,
                           "confirmed_by_om_core": bool(ev.get("witness")),
                           "evals_used": evals, "restarts_used": restarts,
                           "at": time.strftime("%Y-%m-%d %H:%M:%S")}
                    wf = os.path.join(out_dir,
                                      f"WITNESS_w{wid:02d}_{witnesses:03d}.json")
                    with open(wf, "w", encoding="utf-8", newline="\n") as f:
                        json.dump(hit, f, ensure_ascii=False, indent=1)
                    witnesses += 1
                    snapshot()
                    if hit["confirmed_by_om_core"]:
                        return snapshot(final=True)
            now = time.time()
            if now - last_report > REPORT_EVERY_S:
                last_report = now
                snapshot()
    return snapshot(final=True)





def _worker_entry(a):
    return worker(*a)


def aggregate(out_dir: str) -> dict:
    recs = []
    for fn in sorted(os.listdir(out_dir)):
        if fn.startswith("worker_") and fn.endswith(".json"):
            try:
                with open(os.path.join(out_dir, fn), encoding="utf-8") as f:
                    recs.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                continue
    confirmed = []
    for fn in sorted(os.listdir(out_dir)):
        if fn.startswith("WITNESS_"):
            with open(os.path.join(out_dir, fn), encoding="utf-8") as f:
                h = json.load(f)
            if h.get("confirmed_by_om_core"):
                confirmed.append({"file": fn, "points": h["points"],
                                  "evals_used": h.get("evals_used"),
                                  "implied_upper_bound":
                                      h["om_core_evaluate"].get("implied_upper_bound")})
    hist: dict[int, int] = {}
    for rec in recs:
        for k, v in (rec.get("f_histogram") or {}).items():
            hist[int(k)] = hist.get(int(k), 0) + v
    bests = [r for r in recs if r.get("best_f") is not None]
    best = min(bests, key=lambda r: r["best_f"]) if bests else None
    return {"workers": len(recs), "active": sum(1 for r in recs if not r.get("final")),
            "evals": sum(r.get("evals", 0) for r in recs),
            "restarts": sum(r.get("restarts", 0) for r in recs),
            "elapsed_s": max((r.get("elapsed_s", 0) for r in recs), default=0),
            "rate_per_s": round(sum(r.get("rate_per_s", 0) for r in recs), 1),
            "best_f": (best["best_f"] if best else None),
            "best_topes": (best["best_topes"] if best else None),
            "best_points": (best["best_points"] if best else None),
            "best_coord": (best["coord"] if best else None),
            "f_histogram": dict(sorted(hist.items())[:12]),
            "witnesses_confirmed": len(confirmed), "witness_files": confirmed,
            "scope": {"n": recs[0]["n"], "r": recs[0]["r"]} if recs else {}}


def print_status(out_dir: str) -> int:
    if not os.path.isdir(out_dir):
        print(f"진행 폴더가 없습니다: {out_dir}")
        return 1
    a = aggregate(out_dir)
    sc = a.get("scope", {})
    print(f"[climb {out_dir}] n={sc.get('n')} r={sc.get('r')} "
          f"워커 {a['workers']}개 (실행 중 {a['active']})")
    print(f"  평가 {a['evals']:,}회 / 재시작 {a['restarts']:,}회 "
          f"| 경과 {a['elapsed_s']:.0f}s | 초당 {a['rate_per_s']}회")
    if a["witnesses_confirmed"]:
        print(f"  ★★ witness {a['witnesses_confirmed']}건 확인 (om_core 재확인 완료)")
        for w in a["witness_files"]:
            print(f"     {w['file']} → 상한 {w['implied_upper_bound']} "
                  f"(평가 {w['evals_used']:,}회 만에)")
    else:
        print(f"  최선 목적함수 f = {a['best_f']} "
              f"(convex 재배향 수, 0 이면 witness) / tope {a['best_topes']} "
              f"[coord={a['best_coord']}]")
        print(f"  도달한 f 값 분포(작은 쪽): {a['f_histogram']}")
    return 0


def cmd_run(args) -> int:
    import multiprocessing as mp
    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    if not args.resume:
        for fn in os.listdir(out_dir):
            if fn.startswith("worker_"):
                os.remove(os.path.join(out_dir, fn))
    coords = [int(c) for c in args.coords.split(",")]
    deadline = time.time() + args.hours * 3600
    jobs = [(i, args.n, args.r, coords[i % len(coords)], args.seed + 7919 * i,
             out_dir, deadline, args.stall, args.temp, args.resume)
            for i in range(args.workers)]
    meta = {"n": args.n, "r": args.r, "d": args.r - 1, "workers": args.workers,
            "coords": coords, "seed_base": args.seed, "hours": args.hours,
            "stall_limit": args.stall, "temp0": args.temp,
            "objective": "num_convex_reorientations (0 이면 witness)",
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8",
              newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"[climb] n={args.n} r={args.r} (d={args.r-1}) 워커 {args.workers}개 "
          f"coord={coords} 최대 {args.hours}시간")
    print(f"  진행 확인:  python climb.py status --out {out_dir}")
    with mp.Pool(args.workers) as pool:
        pool.map(_worker_entry, jobs)
    print("\n[climb] 종료")
    return print_status(out_dir)


def main(argv=None) -> int:
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(prog="climb",
                                 description="목적함수 국소탐색으로 witness 점배치 구성")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--r", type=int, required=True)
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--coords", default="3,4,5,7,9,12,3,4,5,7")
    p.add_argument("--seed", type=int, default=20260809)
    p.add_argument("--hours", type=float, default=0.5)
    p.add_argument("--stall", type=int, default=400,
                   help="개선 없이 이 스텝이 지나면 재시작")
    p.add_argument("--temp", type=float, default=0.6,
                   help="초기 온도(0 이면 순수 언덕오르기)")
    p.add_argument("--out", required=True)
    p.add_argument("--resume", action="store_true",
                   help="이전 실행의 worker_*.json 최선 점배치에서 이어서 탐색")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("status")
    p.add_argument("--out", required=True)
    p.set_defaults(func=lambda a: print_status(a.out))
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
