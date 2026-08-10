"""layer_search.py — rank-2 layer 공간 탐색으로 **ν(d) 상한을 낮춘다**.

## 왜 이 공간인가 (실측 근거)

지금까지 세 공간을 시험했고 앞의 둘은 원리적으로 막혔다.

| 탐색 공간 | 기울기 | 실현가능성 |
|---|---|---|
| 좌표 공간 (`climb.py`) | **없음** — realization chamber 내부에서 f 는 상수 (PROVEN) | 유지 |
| OM 돌연변이 공간 (`mutation_lab.py`) | 하강 방향은 많으나 **전부 GP 위반** (0/125, 0/813) | — |
| **layer 공간 (이 모듈)** | **7/69 하강, 한 수로 f 40→23** | **모든 상태가 증명서 보유** |

layer 공간의 상태는 rank-2 layer m 개(= signed permutation m 개)이고, 이동은 order 의
인접 전치와 원소 부호 뒤집기다. 어느 상태든 `extended_lawrence.realize_union` 이 정수 좌표
실현 증명서를 붙일 수 있으므로(HI-0004), **탐색 도중 한 번도 실현가능성을 잃지 않는다.**
덮개-CEGIS 가 추상 OM 만 주어 ν(d) 결론에 못 쓰이던 문제가 여기서는 생기지 않는다.

## 목표는 n=2d+2 가 아니다 (설계 수정)

witness at n  ⟹  ν(d) ≤ n−1 이고, 알려진 상한은 U(d) = 2d + ⌊(1+d)/2⌋ 다. 따라서

    **n ≤ U(d) 인 witness 는 무엇이든 상한을 개선한다.**

    d=5 : 개선 구간 n ∈ {12, 13}      (n=13 이면 ν(5) ≤ 12 < 13)
    d=7 : 개선 구간 n ∈ {16, 17, 18}
    d=9 : 개선 구간 n ∈ {20, …, 23}

Larman 목표(n=2d+2)만 보던 것은 전부-아니면-전무였다. 게다가 **witness 는 n 에 단조**다:
볼록위치는 부분집합에 유전되고 사영변환은 부분집합으로 제한되므로, n 점 witness 에 일반위치
점을 더해도 witness 다. 즉 n 이 클수록 엄격히 쉽다. 그래서 이 모듈은 **n 을 U(d) 부터
아래로 훑는다.**

## 보상 체계

    bound_gain(d, n) = (U(d) + 1) − n      witness 를 찾았을 때만 의미가 있다
                                            > 0 이면 상한 개선, = 2 면 Larman 도달

탐색 내부의 목적함수는 f(=convex 재배향 수) 지만, **라운드의 성패는 bound_gain 으로 잰다.**
f 를 1 낮추는 것과 n 을 1 낮추는 것은 가치가 다르다.

## 규모 확장: 단락(short-circuit) 덮개 주사

f 를 전부 계산하면 2^(n−1) × C(n,r+1) 이라 d=7 에서 이미 불가능하다. 그런데 덮개 중복도가
매우 높다(d=5 에서 평균 99겹) — circuit 하나가 무작위 재배향을 덮을 확률이 (r+2)/2^r 이다.
따라서 재배향마다 **덮는 circuit 하나만 찾으면 즉시 끊는다.** 기대 시도 횟수는 2^r/(r+2) 로
d=5 면 약 8, d=7 이면 약 26 이다. survivor 만 전수 주사를 받는다.

    d=5 (12,6): 전수 1.6M 연산 → 단락 주사 약 2만  (약 30배)

`om_core` 는 여전히 유일한 판정자다. f=0 이 나오면 반드시 `mcmullen_evaluate` 로 재확인하고,
실현 증명서를 함께 저장한다.

    python layer_search.py selftest
    python layer_search.py climb --d 5 --n 13 --hours 2 --out sweep_d5_n13
    python layer_search.py sweep --d 5 --hours 6 --out sweep_d5
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
from extended_lawrence import (Rank2Layer, lawrence_union_chirotope,
                               realize_union)


def known_upper_bound(d: int) -> int:
    """기존 상한 U(d) = 2d + ⌊(1+d)/2⌋.

    ※ `knowledge/known_results.md` 가 이 값을 `[출처 확인 필요]` 로 표시하고 있다.
    원문 대조 전까지 '개선' 주장은 이 기준선에 상대적인 것임을 함께 밝혀야 한다."""
    return 2 * d + (1 + d) // 2


def bound_gain(d: int, n: int) -> int:
    """n 점 witness 를 찾았을 때의 상한 개선폭. >0 이면 개선, 2 면 Larman 도달."""
    return (known_upper_bound(d) + 1) - n


# ── 단락 덮개 주사 ────────────────────────────────────────────────────
class CoverageScanner:
    """circuit 부호벡터 기반 survivor 계수기 — 덮는 circuit 을 찾으면 즉시 끊는다."""

    def __init__(self, ch: Chirotope):
        self.n, self.r = ch.n, ch.r
        self.size = self.r + 1
        self.K = 1 << (self.n - 1)
        self.gamma: list[int] = []
        self.smask: list[int] = []
        for S in combinations(range(self.n), self.size):
            C = ch.circuit(S)
            self.gamma.append(sum(1 << e for e in S if C[e] < 0))
            self.smask.append(sum(1 << e for e in S))
        self.num_circuits = len(self.gamma)

    def survivors(self, stop_after: int | None = None) -> tuple[int, list[int]]:
        """(survivor 수, survivor 인덱스). stop_after 개를 넘으면 조기 중단한다
        — '이미 나쁘다'가 확정된 후보에 시간을 더 쓰지 않기 위한 가지치기."""
        gamma, smask, size = self.gamma, self.smask, self.size
        num = self.num_circuits
        hot = list(range(min(48, num)))      # 최근 성공한 circuit 을 먼저 시도
        found: list[int] = []
        for k in range(self.K):
            fm = k << 1
            covered = False
            for ci in hot:
                neg = ((fm ^ gamma[ci]) & smask[ci]).bit_count()
                if neg <= 1 or neg >= size - 1:
                    covered = True
                    break
            if not covered:
                for ci in range(num):
                    neg = ((fm ^ gamma[ci]) & smask[ci]).bit_count()
                    if neg <= 1 or neg >= size - 1:
                        covered = True
                        hot.pop()
                        hot.insert(0, ci)
                        break
            if not covered:
                found.append(k)
                if stop_after is not None and len(found) > stop_after:
                    return len(found), found
        return len(found), found


def evaluate_layers(layers, stop_after: int | None = None):
    """layer tuple → (f, survivor 목록, chirotope). 균일하지 않으면 None."""
    try:
        ch = lawrence_union_chirotope(layers)
    except ValueError:
        return None
    f, surv = CoverageScanner(ch).survivors(stop_after=stop_after)
    return f, surv, ch


# ── layer 공간 ────────────────────────────────────────────────────────
def random_layers(n: int, m: int, rng: random.Random) -> tuple:
    out = []
    for i in range(m):
        order = list(range(n)); rng.shuffle(order)
        # 모든 layer 에 같은 부호반전을 가하면 union 의 재배향이 되므로 첫 layer 는
        # 전부 + 로 게이지 고정해도 궤도를 잃지 않는다.
        signs = [1] * n if i == 0 else [rng.choice((-1, 1)) for _ in range(n)]
        if i and signs[0] < 0:
            signs = [-s for s in signs]      # 전역 반전은 rank-2 chirotope 를 안 바꾼다
        out.append(Rank2Layer(tuple(order), tuple(signs)))
    return tuple(out)


def neighbors(layers) -> list[tuple]:
    """단일 이동: order 의 인접 전치 + 원소 부호 뒤집기. 모든 이웃이 실현가능하다."""
    out = []
    n, m = layers[0].n, len(layers)
    for i in range(m):
        L = layers[i]
        for p in range(n - 1):
            o = list(L.order); o[p], o[p + 1] = o[p + 1], o[p]
            out.append(tuple(layers[:i]) + (Rank2Layer(tuple(o), L.signs),)
                       + tuple(layers[i + 1:]))
        for e in range(n):
            s = list(L.signs); s[e] = -s[e]
            out.append(tuple(layers[:i]) + (Rank2Layer(L.order, tuple(s)),)
                       + tuple(layers[i + 1:]))
    return out


def climb(d: int, n: int, *, seed: int = 0, budget_s: float = 600.0,
          stall_limit: int = 40, verbose: bool = True, log=None) -> dict:
    """layer 공간 언덕오르기. f=0 이면 om_core 재확인 + 실현 증명서까지 붙여 돌려준다."""
    if d % 2 == 0:
        raise ValueError("rank-2 layer family 는 rank=d+1 이 짝수여야 하므로 홀수 d 전용")
    m, r = (d + 1) // 2, d + 1
    if n <= r:
        raise ValueError("n > r 이어야 함")
    rng = random.Random(seed)
    t0 = time.time()
    best_f = None; best_layers = None
    evals = restarts = 0

    def say(msg):
        if verbose:
            print(msg, flush=True)
        if log is not None:
            log.append(msg)

    say(f"[climb] d={d} n={n} r={r} (layer {m}개) | 예산 {budget_s:.0f}s "
        f"| 개선 기준선 U({d})={known_upper_bound(d)} → 이 n 의 bound_gain="
        f"{bound_gain(d, n)}")

    while time.time() - t0 < budget_s:
        cur = random_layers(n, m, rng)
        got = evaluate_layers(cur)
        evals += 1
        if got is None:
            continue
        cur_f = got[0]
        restarts += 1
        stall = 0
        while stall < stall_limit and time.time() - t0 < budget_s:
            cand_list = neighbors(cur)
            rng.shuffle(cand_list)
            improved = False
            for cand in cand_list:
                if time.time() - t0 > budget_s:
                    break
                g = evaluate_layers(cand, stop_after=cur_f)
                evals += 1
                if g is None:
                    continue
                f = g[0]
                if f < cur_f:
                    cur, cur_f = cand, f
                    improved = True
                    break
            if best_f is None or cur_f < best_f:
                best_f, best_layers = cur_f, cur
                say(f"  최선 f={best_f} (평가 {evals}, {time.time()-t0:.0f}s)")
            if cur_f == 0:
                ch = lawrence_union_chirotope(cur)
                ev = mcmullen_evaluate(ch)
                cert = realize_union(cur, target=ch)
                say(f"  ★★ witness! om_core={ev.get('witness')} "
                    f"| 실현 증명서={'있음' if cert else '없음'} "
                    f"| ν({d}) ≤ {n-1} (기존 {known_upper_bound(d)}, "
                    f"개선폭 {bound_gain(d, n)})")
                return {"status": "WITNESS", "d": d, "n": n, "r": r,
                        "bound_gain": bound_gain(d, n),
                        "implied_upper_bound": n - 1,
                        "known_upper_bound": known_upper_bound(d),
                        "om_core_evaluate": ev,
                        "layers": [L.to_dict() for L in cur],
                        "realization_certificate": cert,
                        "realizability": ("REALIZABLE" if cert
                                          else "CLAIMED_UNVERIFIED"),
                        "evals": evals, "restarts": restarts,
                        "elapsed_s": round(time.time() - t0, 1), "seed": seed}
            if not improved:
                # 평탄면: 같은 f 의 이웃으로 한 걸음 (무작위 보행)
                stall += 1
                for cand in cand_list:
                    g = evaluate_layers(cand, stop_after=cur_f)
                    evals += 1
                    if g is not None and g[0] == cur_f:
                        cur = cand
                        break
            else:
                stall = 0

    return {"status": "NO_WITNESS", "d": d, "n": n, "r": r,
            "best_f": best_f,
            "bound_gain_if_found": bound_gain(d, n),
            "layers": ([L.to_dict() for L in best_layers] if best_layers else None),
            "evals": evals, "restarts": restarts,
            "elapsed_s": round(time.time() - t0, 1), "seed": seed,
            "note": "witness 를 못 찾은 것은 없다는 증명이 아니다"}


def sweep(d: int, *, n_start: int | None = None, n_stop: int | None = None,
          hours: float = 6.0, seed: int = 0, out: str | None = None) -> dict:
    """n 을 U(d) 부터 아래로 훑으며 witness 가 존재하는 최소 n 을 좁힌다.

    각 n 에서 witness 를 찾으면 상한이 그만큼 내려가고, 다음 라운드는 n−1 로 간다.
    실패하면 거기서 멈춘다 — 단조성(witness at n ⟹ witness at n+1) 때문에 더 작은 n 은
    더 어렵기만 하기 때문이다."""
    U = known_upper_bound(d)
    n_hi = n_start if n_start is not None else U
    n_lo = n_stop if n_stop is not None else 2 * d + 2
    t0 = time.time()
    budget_total = hours * 3600
    results = []
    best_n = None
    n = n_hi
    while n >= n_lo and time.time() - t0 < budget_total:
        left = budget_total - (time.time() - t0)
        res = climb(d, n, seed=seed + 7919 * n,
                    budget_s=min(left, budget_total / max(1, n_hi - n_lo + 1) * 2))
        results.append(res)
        if res["status"] == "WITNESS":
            best_n = n
            n -= 1
        else:
            break
    summary = {"d": d, "known_upper_bound": U,
               "larman_target_n": 2 * d + 2,
               "minimal_witness_n": best_n,
               "implied_upper_bound": (best_n - 1) if best_n else None,
               "bound_gain": bound_gain(d, best_n) if best_n else 0,
               "rounds": results,
               "elapsed_s": round(time.time() - t0, 1)}
    if out:
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=1)
    return summary


def selftest() -> int:
    """답을 아는 곳에서 평가기와 탐색을 검증한다."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'OK ' if good else 'FAIL'} {label}: {got}"
              + ("" if good else f" (기대 {want})"))

    print("\n[1] 단락 주사 ↔ mutation_lab 완전 일치 + 속도")
    from mutation_lab import MutationLab
    rng = random.Random(4242)
    for (n, m) in [(8, 2), (9, 3), (12, 3)]:
        layers = random_layers(n, m, rng)
        ch = lawrence_union_chirotope(layers)
        t0 = time.time(); ref = MutationLab(ch).evaluate()[1]; t_ref = time.time() - t0
        t0 = time.time(); got = CoverageScanner(ch).survivors()[0]; t_new = time.time() - t0
        chk(f"(n={n}, r={2*m}) f", got, ref)
        print(f"       전수 {t_ref*1000:.0f}ms → 단락 {t_new*1000:.0f}ms "
              f"({t_ref/max(t_new,1e-9):.1f}배)")

    print("\n[2] 보상 체계 — 개선 구간이 맞게 계산되는가")
    chk("U(5)", known_upper_bound(5), 13)
    chk("bound_gain(5, 13) — 개선 1", bound_gain(5, 13), 1)
    chk("bound_gain(5, 12) — Larman 도달", bound_gain(5, 12), 2)
    chk("bound_gain(5, 14) — 개선 없음", bound_gain(5, 14), 0)

    print("\n[3] d=3 보정 — n=8 에 witness 가 존재함이 알려져 있다")
    res = climb(3, 8, seed=11, budget_s=120, verbose=False)
    chk("status", res["status"], "WITNESS")
    if res["status"] == "WITNESS":
        chk("om_core witness", res["om_core_evaluate"].get("witness"), True)
        chk("실현 증명서 존재", res["realization_certificate"] is not None, True)
        cert = res["realization_certificate"]
        rebuilt = Chirotope.from_vectors(cert["vectors"])
        layers = tuple(Rank2Layer.from_dict(x) for x in res["layers"])
        chk("증명서 재검증", rebuilt.signs == lawrence_union_chirotope(layers).signs, True)
        print(f"       ν(3) ≤ {res['implied_upper_bound']} "
              f"(기존 {res['known_upper_bound']}), 평가 {res['evals']}회")

    print("\n[4] 짝수 d 는 이 family 에서 정의되지 않는다")
    try:
        climb(4, 10, budget_s=1, verbose=False)
        chk("짝수 d 거부", False, True)
    except ValueError:
        chk("짝수 d 거부", True, True)

    print("\n" + ("전체 통과" if ok else "실패 항목 있음"))
    return 0 if ok else 1


def main(argv=None) -> int:
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(
        prog="layer_search",
        description="rank-2 layer 공간 탐색으로 ν(d) 상한을 낮춘다")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("climb", help="고정 (d, n) 에서 witness 탐색")
    p.add_argument("--d", type=int, required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--hours", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=20260810)
    p.add_argument("--out", default=None)
    p.set_defaults(func=lambda a: _cmd_climb(a))
    p = sub.add_parser("sweep", help="n 을 U(d) 부터 아래로 훑는다")
    p.add_argument("--d", type=int, required=True)
    p.add_argument("--n-start", type=int, default=None)
    p.add_argument("--n-stop", type=int, default=None)
    p.add_argument("--hours", type=float, default=6.0)
    p.add_argument("--seed", type=int, default=20260810)
    p.add_argument("--out", default=None)
    p.set_defaults(func=lambda a: _cmd_sweep(a))
    sub.add_parser("selftest").set_defaults(func=lambda a: selftest())
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        return selftest()
    return args.func(args)


def _stamp_snapshot(rec: dict) -> dict:
    snap = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".exec_sync.json")
    if os.path.exists(snap):
        with open(snap, encoding="utf-8") as fh:
            rec["snapshot_id"] = json.load(fh).get("snapshot_id")
    return rec


def _cmd_climb(a) -> int:
    log: list[str] = []
    res = _stamp_snapshot(climb(a.d, a.n, seed=a.seed,
                                budget_s=a.hours * 3600, log=log))
    print(f"\n[결과] {res['status']} | d={a.d} n={a.n} "
          f"| 최선 f={res.get('best_f', 0)} | {res['elapsed_s']}s")
    if a.out:
        res["log"] = log
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
        print(f"저장: {a.out}")
    return 0


def _cmd_sweep(a) -> int:
    res = _stamp_snapshot(sweep(a.d, n_start=a.n_start, n_stop=a.n_stop,
                                hours=a.hours, seed=a.seed, out=None))
    print(f"\n[스윕 결과] d={a.d} | 최소 witness n = {res['minimal_witness_n']} "
          f"| ν({a.d}) ≤ {res['implied_upper_bound']} "
          f"(기존 {res['known_upper_bound']}) | 개선폭 {res['bound_gain']}")
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
        print(f"저장: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
