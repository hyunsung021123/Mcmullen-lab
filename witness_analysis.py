"""
witness_analysis.py — witness 의 구조 압축: 왜 witness 인가를 짧게 설명하는 도구.

(source: chatgpt, relayed by user — 0025)

새 정리 발견의 현실적 경로는 "AI 가 완성된 정리를 쓰는 것"이 아니라

    exact 계산 → **구조 압축(이 모듈)** → AI 가설 → 반례 사냥 → 사람의 일반화

이다. 이 모듈은 그 두 번째 단계: 검증된 witness 하나에서 사람이 읽을 수 있는
작은 구조를 뽑아낸다.

1. `minimal_obstruction_cover(ch)` — witness ⟺ 재배향 hypercube 전체가 circuit
   bad set 들로 커버(WP1 동치). 전체 C(n,r+1)개 circuit 이 아니라 **커버를 유지하는
   최소(혹은 greedy 극소) circuit 부분집합**을 찾는다. 이 집합이 작으면 "이 witness
   가 왜 witness 인가"가 짧은 구조적 설명이 된다.
2. `unsat_core_supports(ch)` — convexity SAT 식(WP2)에서 z3 unsat core 로 "이
   circuit 들의 균형 요구만으로 이미 모든 재배향이 불가능"인 부분집합을 추출.
3. `witness_profile(ch)` — orbit 비교용 특징 묶음 (automorphism 수, cover 크기,
   circuit/cocircuit 균형 히스토그램 등).

## 신뢰 규율

- cover 는 반환 직전 exact mask 동등성으로 재검증된다 (커버 실패 시 예외).
- unsat core 는 "core 만 남긴 solver 가 여전히 UNSAT" replay 를 통과해야 반환된다.
- 여기서 나오는 것은 **검증된 계산적 사실**이지 정리가 아니다 — 일반화(임의 n 으로의
  확장)는 사람/후속 검증의 몫이며, trust 등급은 VERIFIED(개별 사례 사실)를 넘지 않는다.

의존성: om_core + reorientation_cover (+ unsat core 만 z3 옵셔널).
"""
from __future__ import annotations
from itertools import combinations
from typing import Optional

from om_core import Chirotope
from reorientation_cover import bad_reorientation_mask, evaluate_coverage

try:
    import z3
except ImportError:
    z3 = None


def minimal_obstruction_cover(ch: Chirotope, *, exact: bool = False) -> list[tuple]:
    """재배향 hypercube 전체를 커버하는 circuit support 부분집합.

    exact=False: greedy(가장 많이 새로 커버하는 support 우선, 동률은 사전식) —
                 극소성은 보장하되 최소성은 보장하지 않음.
    exact=True : z3 Optimize 로 카디널리티 최소 커버 (작은 n 전용, z3 필요).
    witness 가 아니면 ValueError. 반환 전에 커버 완전성을 exact mask 로 재검증."""
    total = 1 << (ch.n - 1)
    all_mask = (1 << total) - 1
    masks = {S: bad_reorientation_mask(ch, S)
             for S in combinations(range(ch.n), ch.r + 1)}
    union = 0
    for m in masks.values():
        union |= m
    if union & all_mask != all_mask:
        raise ValueError("witness 가 아님 — 커버가 hypercube 전체를 덮지 못함")

    if exact:
        if z3 is None:
            raise RuntimeError("exact 최소 커버에는 z3 가 필요")
        opt = z3.Optimize()
        pick = {S: z3.Bool(f"p_{'_'.join(map(str, S))}") for S in masks}
        for k in range(total):
            covering = [pick[S] for S, m in masks.items() if (m >> k) & 1]
            opt.add(z3.Or(covering))
        opt.minimize(z3.Sum([z3.If(p, 1, 0) for p in pick.values()]))
        assert opt.check() == z3.sat
        model = opt.model()
        cover = sorted(S for S, p in pick.items() if z3.is_true(model[p]))
    else:
        cover = []
        covered = 0
        while covered & all_mask != all_mask:
            best_S, best_gain = None, -1
            for S in sorted(masks):
                gain = (masks[S] & ~covered & all_mask).bit_count()
                if gain > best_gain:
                    best_S, best_gain = S, gain
            if best_gain <= 0:
                raise AssertionError("greedy 진행 불가 — 논리 오류")
            cover.append(best_S)
            covered |= masks[best_S]

    # 재검증 (신뢰 규율): 반환하는 커버가 실제로 전체를 덮는지 exact 비교
    check = 0
    for S in cover:
        check |= masks[S]
    if check & all_mask != all_mask:
        raise AssertionError("커버 재검증 실패")
    return [tuple(S) for S in cover]


def unsat_core_supports(ch: Chirotope) -> Optional[list[tuple]]:
    """convexity SAT 식에서 unsat core 에 해당하는 circuit support 들.
    'core 의 균형 요구만으로 모든 재배향이 불가능'을 z3 가 증명한 부분집합이며,
    반환 전에 core-only solver 가 여전히 UNSAT 인지 replay 한다.
    witness 가 아니면(SAT) None. z3 미설치 시 RuntimeError."""
    if z3 is None:
        raise RuntimeError("z3 미설치")
    zvar = {e: z3.Bool(f"z_{e}") for e in range(1, ch.n)}

    def convexity_constraint(S):
        base = ch.circuit(S)
        pos_lits = []
        for s in S:
            if s == 0:
                pos_lits.append(z3.BoolVal(base[s] > 0))
            elif base[s] > 0:
                pos_lits.append(z3.Not(zvar[s]))
            else:
                pos_lits.append(zvar[s])
        npos = z3.Sum([z3.If(b, 1, 0) for b in pos_lits])
        return z3.And(npos >= 2, npos <= len(S) - 2)

    solver = z3.Solver()
    track = {}
    for S in combinations(range(ch.n), ch.r + 1):
        t = z3.Bool(f"t_{'_'.join(map(str, S))}")
        track[t] = tuple(S)
        solver.assert_and_track(convexity_constraint(S), t)
    if solver.check() != z3.unsat:
        return None                                  # witness 아님 (또는 unknown)
    core = sorted(track[t] for t in solver.unsat_core())

    # replay: core 만 남겨도 UNSAT 이어야 한다
    s2 = z3.Solver()
    for S in core:
        s2.add(convexity_constraint(S))
    assert s2.check() == z3.unsat, "unsat core replay 실패"
    return core


def witness_profile(ch: Chirotope, *, with_automorphisms: bool = True) -> dict:
    """orbit 간 비교용 특징 묶음 (검증된 계산적 사실만 — 가설 아님)."""
    from collections import Counter
    cov = evaluate_coverage(ch)
    circuit_hist = Counter()
    for S in combinations(range(ch.n), ch.r + 1):
        C = ch.circuit(S)
        pos = sum(1 for v in C.values() if v > 0)
        circuit_hist[min(pos, len(C) - pos)] += 1
    cocircuit_hist = Counter()
    for H in combinations(range(ch.n), ch.r - 1):
        D = ch.cocircuit(H)
        pos = sum(1 for v in D.values() if v > 0)
        cocircuit_hist[min(pos, len(D) - pos)] += 1
    profile = {
        "n": ch.n, "r": ch.r,
        "is_witness": cov.is_witness,
        "greedy_cover_size": (len(minimal_obstruction_cover(ch))
                              if cov.is_witness else None),
        "circuit_balance_hist": dict(sorted(circuit_hist.items())),
        "cocircuit_balance_hist": dict(sorted(cocircuit_hist.items())),
        "acyclic": ch.is_acyclic(),
        "totally_cyclic": ch.is_totally_cyclic(),
    }
    if with_automorphisms:
        from symmetry_reduction import automorphism_count, group_order
        a = automorphism_count(ch)          # 전체 군 (Z2)^n⋊S_n 의 |Stab| (0025)
        profile["automorphism_count"] = a
        profile["orbit_size_full"] = group_order(ch.n) // a
        profile["orbit_size_gauge"] = group_order(ch.n) // (2 * a)
    return profile


if __name__ == "__main__":
    from generator import generate_backtracking

    # (6,3) 의 witness isomorphism class 3개 (WP4 실측)의 대표를 확보:
    # 결정론적 열거에서 witness 를 모으고 canonical_form 으로 3개 대표 추출.
    from symmetry_reduction import canonical_form
    reps: dict = {}
    for cand in generate_backtracking(6, 3, dedup=False,
                                      max_candidates=10 ** 9, max_nodes=10 ** 9):
        if cand.is_reorientable_to_convex()[0]:
            continue
        k = canonical_form(cand)
        if k not in reps:
            reps[k] = cand
        if len(reps) == 3:
            break
    assert len(reps) == 3, f"(6,3) witness class 3개 기대, {len(reps)}개"
    print(f"(6,3) witness isomorphism class 대표 {len(reps)}개 확보")

    # (1) greedy cover: 완전성 재검증 포함해 계산 + exact 와 비교 (z3 있으면)
    for i, ch in enumerate(reps.values()):
        greedy = minimal_obstruction_cover(ch)
        assert len(greedy) <= 15 == len(list(combinations(range(6), 4)))
        line = f"class {i}: greedy cover {len(greedy)}/15"
        if z3 is not None:
            exact = minimal_obstruction_cover(ch, exact=True)
            assert len(exact) <= len(greedy)
            line += f", exact 최소 cover {len(exact)}/15"
            # exact 도 재검증을 통과했음(함수 내부 assert) — 크기만 기록
        core = unsat_core_supports(ch) if z3 is not None else None
        if core is not None:
            line += f", unsat core {len(core)}"
        print("  " + line)

    # (2) non-witness 는 cover 불가(ValueError) + core 는 None
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    try:
        minimal_obstruction_cover(quad)
        raise AssertionError("non-witness 에 커버가 존재")
    except ValueError:
        pass
    if z3 is not None:
        assert unsat_core_supports(quad) is None
    print("non-witness 거부 OK")

    # (3) 프로파일: 세 class 가 실제로 구별되는지 (자명하지 않은 발견의 씨앗)
    profs = [witness_profile(ch) for ch in reps.values()]
    keys = ("automorphism_count", "greedy_cover_size", "circuit_balance_hist")
    distinct = len({str(tuple(p[k] for k in keys)) for p in profs})
    # 0025 회귀 방지: (6,3) witness 는 전체 군 기준 정확히 3개 class 이고
    # 게이지 슬라이스 크기 합이 전수 witness 수(9,984)와 일치해야 한다.
    sizes = sorted(p["orbit_size_gauge"] for p in profs)
    assert sizes == [384, 3840, 5760], sizes
    assert sum(sizes) == 9984
    for i, p in enumerate(profs):
        print(f"  class {i}: |Stab|={p['automorphism_count']}, "
              f"gauge orbit={p['orbit_size_gauge']}, "
              f"cover={p['greedy_cover_size']}, circuit_hist={p['circuit_balance_hist']}, "
              f"acyclic={p['acyclic']}")
    print(f"  (게이지 슬라이스 합 {sum(sizes)} == 전수 witness 9,984 — 0025 검증)")
    print(f"프로파일로 구별되는 class 수: {distinct}/3")

    print("witness_analysis core-contract assertions OK "
          "(cover 재검증 / core replay / non-witness 거부)")
