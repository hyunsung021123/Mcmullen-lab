"""
nearmiss.py — '근접 실패' 구성의 구조를 뜯어본다 (프롬프트에 넣을 핵심 데이터 생성).

climb.py 가 내놓는 것은 f = (convex 가 되는 재배향의 수) 뿐이다. 그런데 f=1 인
구성에서 정작 알고 싶은 것은:

  · **어떤** 재배향이 살아남았는가 (원소 뒤집기 집합)
  · 그 재배향에서 circuit(Radon 분할) 균형이 어떻게 분포하는가
  · 그중 **가장 깨지기 쉬운(min-side == 2) circuit** 은 무엇인가
    → 이걸 하나만 무너뜨리면 witness 가 된다. 즉 남은 거리의 구체적 정체.

이 정보가 있어야 "무엇을 건드려야 하는가"를 물을 수 있다. f 값만으로는 물을 수 없다.

의존성: 표준 라이브러리 + om_core + invariants.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from itertools import combinations

from om_core import Chirotope, mcmullen_evaluate
from reorientation_cover import flip_set_from_index


def analyze(points: list, *, top_fragile: int = 8) -> dict:
    """근접 실패 구성 하나의 구조 보고서."""
    pts = [tuple(p) for p in points]
    ch = Chirotope.from_points(pts)
    n, r = ch.n, ch.r
    total = 1 << (n - 1)

    survivors = []          # convex 로 살아남은 재배향 index
    acyclic_cnt = 0
    for k in range(total):
        flip = flip_set_from_index(k, n)
        rch = ch.reorient(flip)
        if rch.is_acyclic():
            acyclic_cnt += 1
            if rch.is_convex_position():
                survivors.append(k)

    out = {"n": n, "r": r, "d": r - 1, "points": [list(p) for p in pts],
           "num_tope_pairs": acyclic_cnt,
           "num_convex_reorientations": len(survivors),
           "is_witness": len(survivors) == 0,
           "om_core_evaluate": mcmullen_evaluate(ch),
           "survivors": []}

    for k in survivors[:4]:
        flip = sorted(flip_set_from_index(k, n))
        rch = ch.reorient(flip_set_from_index(k, n))
        bal = []
        for S in combinations(range(n), r + 1):
            C = rch.circuit(S)
            pos = sum(1 for v in C.values() if v > 0)
            bal.append((min(pos, len(C) - pos), S))
        hist = Counter(b for b, _ in bal)
        fragile = sorted(S for b, S in bal if b == 2)
        # 각 원소가 '깨지기 쉬운' circuit 에 얼마나 자주 등장하는지 —
        # 어느 점을 움직이면 효과가 큰지에 대한 힌트
        touch = Counter(e for S in fragile for e in S)
        out["survivors"].append({
            "reorientation_index": k,
            "flip_set": flip,
            "circuit_balance_histogram": dict(sorted(hist.items())),
            "num_fragile_circuits": len(fragile),
            "fragile_circuits_sample": [list(S) for S in fragile[:top_fragile]],
            "element_fragility_degree": dict(sorted(touch.items())),
            "note": ("이 재배향에서 min-side==2 인 circuit 을 하나라도 무너뜨리면 "
                     "(=한쪽을 크기 1 이하로 만들면) 이 재배향은 convex 가 아니게 된다."),
        })
    return out


def from_worker_files(out_dir: str, limit: int = 3) -> list[dict]:
    """climb 출력 폴더에서 f 가 가장 작은 구성들을 골라 분석."""
    cands = []
    for fn in sorted(os.listdir(out_dir)):
        if not (fn.startswith("worker_") and fn.endswith(".json")):
            continue
        with open(os.path.join(out_dir, fn), encoding="utf-8") as f:
            rec = json.load(f)
        if rec.get("best_points") and rec.get("best_f") is not None:
            cands.append((rec["best_f"], rec["worker"], rec["coord"],
                          rec["best_points"]))
    cands.sort(key=lambda c: c[0])
    reports = []
    for f_val, wid, coord, pts in cands[:limit]:
        rep = analyze(pts)
        rep["source"] = {"dir": out_dir, "worker": wid, "coord": coord,
                         "recorded_f": f_val}
        rep["consistent_with_climb"] = (rep["num_convex_reorientations"] == f_val)
        reports.append(rep)
    return reports


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(prog="nearmiss")
    ap.add_argument("--dir", required=True, help="climb 출력 폴더")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--out", default=None, help="JSON 저장 경로")
    args = ap.parse_args()

    reps = from_worker_files(args.dir, limit=args.limit)
    for rep in reps:
        src = rep["source"]
        print(f"\n=== w{src['worker']} coord={src['coord']} "
              f"n={rep['n']} r={rep['r']} (d={rep['d']}) ===")
        print(f"  tope 쌍 {rep['num_tope_pairs']} / convex 재배향 "
              f"{rep['num_convex_reorientations']} "
              f"(climb 기록과 일치: {rep['consistent_with_climb']})")
        print(f"  witness: {rep['is_witness']}  "
              f"| om_core: {rep['om_core_evaluate'].get('witness')}")
        for s in rep["survivors"]:
            print(f"  · 살아남은 재배향 #{s['reorientation_index']} "
                  f"flip={s['flip_set']}")
            print(f"    circuit 균형 분포: {s['circuit_balance_histogram']}")
            print(f"    깨지기 쉬운(min-side=2) circuit {s['num_fragile_circuits']}개, "
                  f"예: {s['fragile_circuits_sample'][:4]}")
            print(f"    원소별 취약도: {s['element_fragility_degree']}")
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(reps, f, ensure_ascii=False, indent=1)
        print(f"\n저장: {args.out}")
