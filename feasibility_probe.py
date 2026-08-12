"""
feasibility_probe.py — d=5, n=12 프로젝트 착수 전 실측 (일회성 진단 스크립트).

판단해야 할 것:
  1. (12,6) 후보 하나를 판정하는 데 실제로 얼마나 걸리는가 (README §10 의 '빠르다'가
     구체적으로 몇 ms 인가)
  2. 실현가능 무작위 표집으로 witness 를 만날 확률이 차원에 따라 어떻게 변하는가
     → d=5 에서 무작위 탐색이 승산이 있는지에 대한 정량적 근거
  3. 어휘/채굴/반증 계층이 (12,6) 규모에서 실제로 도는가

이 스크립트는 연구 산출물이 아니라 **착수 판단 근거**다. 결과는 그대로
knowledge/known_results.md 에 실측으로 기록한다.
"""
from __future__ import annotations

import json
import time

from console import enable_utf8_stdout
from om_core import Chirotope, mcmullen_evaluate
from generator import generate_random_realizable
import invariants as INV
import conjecture as CJ


def probe_cost(n: int, r: int, *, samples: int = 20, seed: int = 1) -> dict:
    """후보 생성 + 라벨(궤도 판정) + 저렴한 불변량 전체의 실측 비용."""
    names = [nm for nm in INV.active_names(max_cost="cheap")
             if nm != INV.LABEL_NAME]
    gen = generate_random_realizable(n, r, dedup=False, max_candidates=samples,
                                     seed=seed, max_tries=200_000)
    t_gen = t_lbl = t_inv = 0.0
    got = 0
    wit = 0
    t0 = time.perf_counter()
    for ch in gen:
        t_gen += time.perf_counter() - t0
        t1 = time.perf_counter()
        lab = INV.label(ch)
        t_lbl += time.perf_counter() - t1
        t2 = time.perf_counter()
        INV.evaluate(ch, names)
        t_inv += time.perf_counter() - t2
        got += 1
        wit += int(lab)
        t0 = time.perf_counter()
    if got == 0:
        return {"n": n, "r": r, "samples": 0}
    return {"n": n, "r": r, "samples": got, "witness": wit,
            "gen_ms": round(1000 * t_gen / got, 2),
            "label_ms": round(1000 * t_lbl / got, 2),
            "invariants_ms": round(1000 * t_inv / got, 2),
            "total_ms": round(1000 * (t_gen + t_lbl + t_inv) / got, 2),
            "per_hour": int(3600 / max(1e-9, (t_gen + t_lbl + t_inv) / got))}


def probe_density(n: int, r: int, *, samples: int, seed: int = 7) -> dict:
    """실현가능 무작위 표집에서의 witness 비율 — d 에 따른 감쇠를 본다."""
    t0 = time.perf_counter()
    got = wit = 0
    best_ratio = None
    for ch in generate_random_realizable(n, r, dedup=False, max_candidates=samples,
                                         seed=seed, max_tries=500_000):
        got += 1
        cvx = INV.REGISTRY["num_convex_reorientations"].fn(ch)
        topes = INV.REGISTRY["num_tope_pairs"].fn(ch)
        ratio = cvx / topes if topes else 1.0
        if best_ratio is None or ratio < best_ratio:
            best_ratio = ratio
        if cvx == 0:
            wit += 1
    dt = time.perf_counter() - t0
    return {"n": n, "r": r, "d": r - 1, "sampled": got, "witness": wit,
            "witness_rate": (wit / got if got else None),
            "min_convex_tope_ratio": (round(best_ratio, 6)
                                      if best_ratio is not None else None),
            "elapsed_s": round(dt, 1)}


if __name__ == "__main__":
    enable_utf8_stdout()
    out = {"cost": [], "density": []}

    print("── 1. 후보당 비용 실측 (실현가능 무작위) ──")
    for (n, r, s) in [(6, 3, 60), (8, 4, 40), (10, 5, 25), (12, 6, 12)]:
        rec = probe_cost(n, r, samples=s, seed=100 + n)
        out["cost"].append(rec)
        print(f"  (n={n:2}, r={r}) d={r-1}: 총 {rec['total_ms']:8.2f} ms/후보 "
              f"(생성 {rec['gen_ms']:.2f} / 라벨 {rec['label_ms']:.2f} / "
              f"불변량 {rec['invariants_ms']:.2f}) → 시간당 {rec['per_hour']:,}개")

    print("\n── 2. witness 밀도 (실현가능 표본) ──")
    for (n, r, s) in [(6, 3, 3000), (8, 4, 1500), (10, 5, 400), (12, 6, 120)]:
        rec = probe_density(n, r, samples=s, seed=200 + n)
        out["density"].append(rec)
        rate = rec["witness_rate"]
        print(f"  (n={n:2}, r={r}) d={rec['d']}: {rec['sampled']:5}개 중 "
              f"witness {rec['witness']:5}개 "
              f"({rate:.4%})  최소 convex/tope 비 {rec['min_convex_tope_ratio']}  "
              f"[{rec['elapsed_s']}s]")

    print("\n── 3. (12,6) 에서 파이프라인 계층이 도는가 ──")
    t0 = time.perf_counter()
    chs = list(generate_random_realizable(12, 6, dedup=False, max_candidates=30,
                                          seed=999, max_tries=200_000))
    names = INV.active_names(max_cost="cheap")
    corpus = CJ.build_corpus(chs, {"n": 12, "r": 6, "om_class": "realizable_uniform",
                                   "backend": "random", "exhaustive": False},
                             feature_names=names)
    cjs = CJ.mine(corpus, min_support=3, max_conjectures=10)
    print(f"  코퍼스 {corpus.summary()} / 채굴 {len(cjs)}건 "
          f"[{time.perf_counter()-t0:.1f}s]")
    for c in cjs[:3]:
        print(f"    [{c.invariance[:6]}] {c.text()}")

    # om_core 와의 일치를 (12,6) 에서도 확인 — 규모가 커져도 신뢰 앵커가 같은지
    t1 = time.perf_counter()
    agree = all(INV.label(ch) == mcmullen_evaluate(ch)["witness"] for ch in chs[:3])
    print(f"  라벨 <-> om_core 일치 (12,6) 3건: {agree} "
          f"[{time.perf_counter()-t1:.1f}s — legacy 경로는 훨씬 느림]")

    with open("feasibility_probe.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n결과 저장: feasibility_probe.json")
