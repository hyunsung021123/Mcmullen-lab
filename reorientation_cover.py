"""
reorientation_cover.py — 재배향 하이퍼큐브 커버리지 기반의 정확한(exact) witness 검증기.

Epic #37 / Task #38 (source: chatgpt, relayed by user). 상세 설계와 수학적 정당화는
docs/AUTONOMOUS_VERIFICATION_PIPELINE.md 참고.

## 수학적 번역 (Boolean hypercube covering)

Ground set E={0..n-1}, uniform rank-r chirotope χ. (r+1)-부분집합 S={s_0<…<s_r}의
signed circuit 은 C_{χ,S}(s_i) = (-1)^i χ(S\{s_i}) 로 정의된다 (om_core.circuit 과 동일).

재배향 ρ ∈ {±1}^E 에 대해 χ^ρ(B) = χ(B)·∏_{e∈B} ρ_e 이므로

    C_{χ^ρ,S}(s_i) = (-1)^i χ(S\{s_i}) ∏_{e∈S\{s_i}} ρ_e
                   = C_{χ,S}(s_i) · (∏_{e∈S} ρ_e) · ρ_{s_i}.

∏_{e∈S} ρ_e 는 support S 전체에 공통인 전역 부호라 circuit 의 양/음 분할 균형
min(pos,neg) 에 영향을 주지 않는다. 따라서:

    unbalanced(χ^ρ, S)  ⟺  min-count of ( ρ_{s_i}·C_{χ,S}(s_i) )_i ≤ 1.

전역 부호반전은 convexity 를 보존하므로 원소 0 을 고정하면 재배향 공간은
G = {±1}^E/{±1} ≅ (Z/2Z)^(n-1), |G| = 2^(n-1). 각 support S 의 "bad set"

    B_S = { ρ ∈ G : min(|(ρC)^+|, |(ρC)^-|) ≤ 1 }

에 대해 다음 동치가 성립한다 (양방향 논증은 위 문서 §3):

    χ 가 witness  ⟺  G = ∪_S B_S      (모든 재배향이 어떤 unbalanced circuit 에 차단됨)

## 신뢰 상태

이 모듈은 om_core.py 를 대체하지 않는다 — 독립적으로 같은 결과를 계산하는 두 번째
경로이며, legacy(is_reorientable_to_convex)와 불일치하면 이 모듈을 채택하지 않는다.
witness 판정은 반드시 exact mask 비교(covered_count == total)로만 하고, 부동소수
coverage ratio 를 truth condition 으로 쓰지 않는다.

## Bit convention (certificate/Lean export 까지 동일하게 유지)

    k ∈ [0, 2^(n-1)),  k 의 bit i  ⟺  원소 i+1 을 반전.  원소 0 은 절대 반전 안 함.

의존성: 표준 라이브러리 + om_core.Chirotope 만 사용 (streamlit/pandas/requests/z3 금지).
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations, product
from math import comb
from typing import Optional

from om_core import Chirotope

# 기본 메모리 안전 한도 (bitmask + obstruction map 추정치 상한). 초과 시 명시적 오류.
DEFAULT_MEMORY_LIMIT_BYTES = 64 * 1024 * 1024


def flip_set_from_index(index: int, n: int) -> frozenset[int]:
    """재배향 index k → 반전할 원소 집합. bit i ⟺ 원소 i+1, 원소 0 은 불변."""
    return frozenset(i + 1 for i in range(n - 1) if (index >> i) & 1)


def estimate_memory_bytes(n: int, r: int, build_obstruction_map: bool = False) -> int:
    """evaluate_coverage 가 쓸 대략적 메모리(bytes) 사전 계산.
    bitmask ≈ 2^(n-1)/8 bytes, obstruction map ≈ 2^(n-1) × (support tuple 저장) bytes."""
    total = 1 << (n - 1)
    mask_bytes = total // 8 + 64
    if not build_obstruction_map:
        return mask_bytes
    # 대략: 튜플 1개 ≈ 8*(r+2) bytes (원소 포인터 + 헤더의 보수적 근사)
    return mask_bytes + total * 8 * (r + 3)


@dataclass(frozen=True)
class CoverageResult:
    n: int
    r: int
    total_reorientations: int
    covered_count: int
    coverage_mask: int
    is_witness: bool
    first_uncovered_index: Optional[int]
    # build_obstruction_map=True 일 때만 길이 total 의 튜플(커버 안 된 index 는 None),
    # 아니면 빈 튜플.
    obstruction_supports: tuple


def is_unbalanced_circuit_after_reorientation(
    ch: Chirotope, support: tuple, flip_index: int,
) -> bool:
    """재배향 flip_index 적용 후 support 의 circuit 이 unbalanced(min(pos,neg)≤1)인지.
    reorient 된 chirotope 를 만들지 않고 위 공식(ρ 를 base circuit 에 원소별 곱)으로 계산."""
    S = tuple(sorted(support))
    base = ch.circuit(S)
    pos = 0
    for s in S:
        v = base[s]
        if s >= 1 and (flip_index >> (s - 1)) & 1:
            v = -v
        if v > 0:
            pos += 1
    return min(pos, len(S) - pos) <= 1


def _subcube_mask(n_bits: int, fixed: dict) -> int:
    """(n_bits)-차원 hypercube 에서 fixed{bit위치: 0/1} 를 만족하는 모든 index 의 bitmask.
    자유 좌표는 doubling 으로 확장 — big-int OR/shift 만 사용하는 결정론적 구성."""
    m = 1
    for p in range(n_bits):
        b = fixed.get(p)
        if b is None:
            m |= m << (1 << p)
        elif b:
            m <<= (1 << p)
    return m


def bad_reorientation_mask(ch: Chirotope, support: tuple) -> int:
    """support 의 circuit 이 unbalanced 가 되는 재배향 전체의 bitmask (2^(n-1) bits).

    circuit 균형은 support 위의 ρ 값에만 의존하므로, support 의 국소 패턴
    (≤ 2^(r+1) 개)만 검사한 뒤 각 bad 패턴을 subcube 로 확장한다."""
    S = tuple(sorted(support))
    base = ch.circuit(S)
    flippable = [s for s in S if s >= 1]        # 원소 0 은 고정
    k = len(S)
    mask = 0
    for bits in product((1, -1), repeat=len(flippable)):
        rho = dict(zip(flippable, bits))
        pos = sum(1 for s in S if base[s] * rho.get(s, 1) > 0)
        if min(pos, k - pos) <= 1:
            fixed = {s - 1: (1 if rho[s] == -1 else 0) for s in flippable}
            mask |= _subcube_mask(ch.n - 1, fixed)
    return mask


def evaluate_coverage(
    ch: Chirotope, *,
    build_obstruction_map: bool = False,
    memory_limit_bytes: int = DEFAULT_MEMORY_LIMIT_BYTES,
) -> CoverageResult:
    """χ 의 witness 여부를 hypercube covering 으로 정확히 판정.

    is_witness ⟺ coverage_mask == (1 << 2^(n-1)) - 1   (exact 비교, float ratio 금지)

    build_obstruction_map=True 면 각 재배향 index 마다 그것을 차단한 circuit support
    하나를 기록한다 — support 를 사전식 오름차순으로 순회하며 '가장 먼저 발견한'
    support 를 기록하므로 결정론적이다. witness 면 모든 index 에 obstruction 이 있고,
    non-witness 면 first_uncovered_index 가 존재한다."""
    n, r = ch.n, ch.r
    need = estimate_memory_bytes(n, r, build_obstruction_map)
    if need > memory_limit_bytes:
        raise ValueError(
            f"메모리 한도 초과 예상: n={n} 에서 약 {need} bytes 필요 "
            f"(한도 {memory_limit_bytes}). memory_limit_bytes 를 명시적으로 올려서 "
            f"호출하거나 더 작은 n 을 사용할 것.")

    total = 1 << (n - 1)
    all_mask = (1 << total) - 1
    coverage_mask = 0
    obstructions: list = [None] * total if build_obstruction_map else []

    for S in combinations(range(n), r + 1):     # 사전식 오름차순 (결정론)
        bad = bad_reorientation_mask(ch, S)
        if build_obstruction_map:
            newly = bad & ~coverage_mask & all_mask
            while newly:
                low = newly & -newly
                obstructions[low.bit_length() - 1] = tuple(S)
                newly ^= low
        coverage_mask |= bad

    coverage_mask &= all_mask
    covered = coverage_mask.bit_count()
    is_witness = coverage_mask == all_mask
    first_uncovered = None
    if not is_witness:
        low = (~coverage_mask) & all_mask
        low &= -low
        first_uncovered = low.bit_length() - 1

    return CoverageResult(
        n=n, r=r, total_reorientations=total, covered_count=covered,
        coverage_mask=coverage_mask, is_witness=is_witness,
        first_uncovered_index=first_uncovered,
        obstruction_supports=tuple(obstructions) if build_obstruction_map else (),
    )


if __name__ == "__main__":
    # ── 자체 테스트: 공식 → mask → coverage → legacy 순으로 신뢰를 쌓는다 ──
    from om_core import mcmullen_evaluate

    # (1) 공식 검증: reorient 를 실제로 수행한 결과와 국소 공식이 완전히 일치하는지.
    #     작은 (n,r) 에서 모든 support × 모든 재배향 전수 비교.
    def _direct_unbalanced(ch, S, k):
        rch = ch.reorient(flip_set_from_index(k, ch.n))
        C = rch.circuit(S)
        pos = sum(1 for v in C.values() if v > 0)
        return min(pos, len(C) - pos) <= 1

    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    penta = Chirotope.from_points([(0, 0), (4, 0), (5, 3), (2, 5), (-1, 3)])
    for ch in (quad, tri, penta):
        for S in combinations(range(ch.n), ch.r + 1):
            bad = bad_reorientation_mask(ch, S)
            for k in range(1 << (ch.n - 1)):
                formula = is_unbalanced_circuit_after_reorientation(ch, S, k)
                assert formula == _direct_unbalanced(ch, S, k), (S, k)
                assert formula == bool((bad >> k) & 1), (S, k)
    print("공식/서브큐브 mask 전수 일치 OK (n=4,5 전 support × 전 재배향)")

    # (2) coverage ⟷ legacy 차등 검증 (non-witness 쪽): convex 사각형/삼각형+내부점
    for ch in (quad, tri, penta):
        cov = evaluate_coverage(ch, build_obstruction_map=True)
        legacy = not ch.is_reorientable_to_convex()[0]
        assert cov.is_witness == legacy == False
        assert cov.first_uncovered_index is not None
        flip = flip_set_from_index(cov.first_uncovered_index, ch.n)
        assert ch.reorient(flip).is_convex_position()   # 반례 재배향 replay
    print("non-witness 판정 + first_uncovered replay OK")

    # (3) rank-2 특이 사례 (README §5): 모든 rank-2 uniform OM 은 정의상 witness.
    #     legacy 와 coverage 가 이 특이 케이스에서도 일치해야 한다.
    r2 = Chirotope.from_vectors([(1, 0), (0, 1), (-1, -2), (-2, -1)])
    cov = evaluate_coverage(r2, build_obstruction_map=True)
    assert cov.is_witness is True
    assert not r2.is_reorientable_to_convex()[0]
    assert all(s is not None for s in cov.obstruction_supports)
    print("rank-2 특이 사례 일치 OK")

    # (4) (6,3) 에서 witness 를 찾아 obstruction map 을 legacy 경로(reorient+circuit)로
    #     전수 replay — mask 로직을 재사용하지 않는 독립 확인.
    from generator import generate_backtracking
    wit = None
    for cand in generate_backtracking(6, 3, dedup=False,
                                      max_candidates=10**9, max_nodes=10**9):
        if not cand.is_reorientable_to_convex()[0]:
            wit = cand
            break
    assert wit is not None, "(6,3) 에서 witness 를 찾지 못함"
    cov = evaluate_coverage(wit, build_obstruction_map=True)
    assert cov.is_witness is True
    assert cov.covered_count == cov.total_reorientations == 32
    for k, S in enumerate(cov.obstruction_supports):
        assert S is not None
        assert _direct_unbalanced(wit, S, k), (k, S)
    ev = mcmullen_evaluate(wit)
    assert ev["witness"] is True and ev["implied_upper_bound"] == 5
    print("(6,3) witness coverage + obstruction 전수 replay OK (상한 5 = 2d+1)")

    # (5) 교대(순환다면체) OM: 이미 convex → 항등 재배향(k=0)이 uncovered 여야 한다.
    alt = Chirotope.alternating(8, 4)
    cov = evaluate_coverage(alt)
    assert cov.is_witness is False and cov.first_uncovered_index == 0
    print("alternating(8,4) 항등 재배향 uncovered OK")

    # (6) 메모리 한도 가드: 큰 n 에서 조용히 폭발하지 않고 명시적 오류.
    try:
        evaluate_coverage(Chirotope.alternating(40, 3))
        raise AssertionError("메모리 한도 가드가 발동하지 않음")
    except ValueError as e:
        assert "메모리 한도" in str(e)
    print("메모리 한도 가드 OK")
    print("reorientation_cover core-contract assertions OK")
