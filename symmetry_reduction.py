"""
symmetry_reduction.py — WP4: (Z₂)^(n-1) ⋊ S_n 작용 아래의 정확한 orbit 축소 (#41).

Epic #37 / docs/AUTONOMOUS_VERIFICATION_PIPELINE.md. (source: chatgpt, relayed by user)

## 무엇을 하는가

uniform chirotope 공간에는 두 종류의 대칭이 있다:
  1. 재배향 (Z₂)^(n-1): 원소 부호 반전 (전역 몫 — 원소 0 고정과 동치, WP1 convention)
  2. relabeling S_n: ground set 원소의 이름 바꾸기

witness 여부(어떤 재배향으로도 convex 불가)는 두 작용 모두에 **불변**이다:
재배향은 정의상 orbit 내부 이동이고, relabeling σ 는 circuit 을 circuit 으로
(support 를 σ(support) 로, 부호 구조를 보존한 채) 옮기므로 convex position 여부와
"재배향으로 convex 가능" 여부를 보존한다 — 이 불변성 자체도 자체 테스트에서
실측으로 재확인한다 (믿음이 아니라 검증).

## 정확성 계약 (Issue #41 수용 조건)

- `orbit_dedup` 은 제거한 candidate 마다 **동일 orbit 대표를 제시**한다
  (silent drop 금지 — 모든 입력이 어느 대표에 흡수됐는지 추적 가능).
- witness orbit 손실 0: 전수 가능한 (n,r) 에서 "orbit 대표의 witness 여부 =
  orbit 모든 원소의 witness 여부"를 전수 검증한다.
- 현재 om_core.canonical_key() 의 간이 `symmetry_order` 지표와 이 모듈의 실제
  automorphism 개수를 혼동하지 않는다 — 여기의 `automorphism_count` 가
  |Aut(χ)| = |{(σ,ρ): χ^{σ,ρ} = χ}| 의 정확한 값이다.

## 비용 (정직)

canonical_form 은 n!·2^(n-1) 개 군 원소를 전부 시도하는 exact 구현이다
(사전식 최소 부호열 = lex-leader). n ≤ 7 에서 실용적이고 그 이상은 비현실적 —
대규모 n 을 위한 canonical labeling 휴리스틱은 이 모듈의 범위 밖이며, 이 exact
버전이 그 휴리스틱들의 정확성 기준선(oracle) 역할을 한다.

의존성: 표준 라이브러리 + om_core (+ 선택적으로 cegis 연동은 별도 함수).
"""
from __future__ import annotations
from itertools import combinations, permutations, product
from math import factorial
from typing import Iterable, Optional

from om_core import Chirotope


def relabel(ch: Chirotope, perm: tuple) -> Chirotope:
    """ground set relabeling: 원소 e 를 perm[e] 로 개명한 chirotope.
    χ'(B) = χ(perm⁻¹(B)) (교대성으로 부호 자동 처리 — om_core.chi 재사용)."""
    inv = [0] * ch.n
    for e, pe in enumerate(perm):
        inv[pe] = e
    signs = {}
    for B in combinations(range(ch.n), ch.r):
        signs[B] = ch.chi(tuple(inv[b] for b in B))
    return Chirotope(ch.n, ch.r, signs)


def _sign_vector(ch: Chirotope, subs: list) -> tuple:
    return tuple(ch.signs[s] for s in subs)


def canonical_form(ch: Chirotope) -> tuple:
    """전체 동형군 (Z₂)^n ⋊ S_n orbit 의 lex-leader 부호열 (exact 전수).
    같은 orbit ⟺ 같은 canonical_form. n ≤ 7 권장.

    주의(0025): "0-고정 flip × relabel" 만 열거하면 합성에 닫혀 있지 않다 —
    σ(A) 가 0 을 포함하면 그 합성은 (홀수 r 에서) 전역 부정으로 나타나 열거 밖으로
    나가고, 한 isomorphism class 가 두 canonical key 로 쪼개질 수 있다 (실측 재현).
    전역 부정은 '모든 원소 재배향'이라는 적법한 군 원소이므로 후보에 포함한다
    (짝수 r 에선 χ^E = χ 라 무해한 중복)."""
    subs = sorted(combinations(range(ch.n), ch.r))
    others = list(range(1, ch.n))
    best = None
    for perm in permutations(range(ch.n)):
        rch = relabel(ch, perm)
        for bits in product((0, 1), repeat=ch.n - 1):
            flip = {others[i] for i, b in enumerate(bits) if b}
            seq = _sign_vector(rch.reorient(flip), subs)
            neg = tuple(-x for x in seq)               # 전역 부정 = flip(E)
            if best is None or seq < best:
                best = seq
            if neg < best:
                best = neg
    return best


def automorphism_count(ch: Chirotope) -> int:
    """전체 군 (Z₂)^n ⋊ S_n 에서의 |Stab(χ)| 정확값 (0025 정정).
    (σ, A⊆E) 는 (σ, A'⊆{1..n-1}) + 선택적 전역 부정으로 유일 분해되므로
    |Stab| = #{(σ,A'): image == χ} + #{(σ,A'): image == -χ}.
    orbit-stabilizer: |full orbit| = 2^n·n!/|Stab|, 게이지 슬라이스 = 그 절반.
    om_core 의 간이 symmetry_order(재배향만)와 다른 개념이다."""
    subs = sorted(combinations(range(ch.n), ch.r))
    target = _sign_vector(ch, subs)
    neg_target = tuple(-x for x in target)
    others = list(range(1, ch.n))
    cnt = 0
    for perm in permutations(range(ch.n)):
        rch = relabel(ch, perm)
        for bits in product((0, 1), repeat=ch.n - 1):
            flip = {others[i] for i, b in enumerate(bits) if b}
            seq = _sign_vector(rch.reorient(flip), subs)
            if seq == target or seq == neg_target:
                cnt += 1
    return cnt


def orbit_dedup(chirotopes: Iterable[Chirotope]) -> dict:
    """orbit 단위 중복 제거. 반환:
       {"representatives": [Chirotope,...],           # canonical 대표 (입력 첫 등장 순)
        "orbit_of": [int,...],                        # 입력 i 번째 → 대표 index
        "orbit_sizes_seen": [int,...]}                # 대표별 흡수된 입력 수
    제거된 모든 candidate 는 orbit_of 로 자기 대표를 가리킨다 (silent drop 없음)."""
    reps: list[Chirotope] = []
    keys: dict = {}
    orbit_of: list[int] = []
    sizes: list[int] = []
    for ch in chirotopes:
        k = canonical_form(ch)
        if k in keys:
            idx = keys[k]
            sizes[idx] += 1
        else:
            idx = len(reps)
            keys[k] = idx
            reps.append(ch)
            sizes.append(1)
        orbit_of.append(idx)
    return {"representatives": reps, "orbit_of": orbit_of, "orbit_sizes_seen": sizes}


def group_order(n: int) -> int:
    """전체 동형군 (Z₂)^n ⋊ S_n 의 크기 = n! · 2^n (0025 정정 — 전역 부정 포함)."""
    return factorial(n) * (1 << n)


def orbit_images(ch: Chirotope, *, gauge_fixed: bool = True) -> list[dict]:
    """χ 의 orbit 에 속한 서로 다른 chirotope 들의 signs dict 목록 (exact 전수).

    gauge_fixed=True 면 첫 r-부분집합의 부호가 +1 인 이미지들만 반환 —
    generator/CEGIS outer 의 모델 공간(전역 부호 게이지 고정)과 같은 공간이라
    orbit 단위 모델 블로킹에 그대로 쓸 수 있다."""
    subs = sorted(combinations(range(ch.n), ch.r))
    first = subs[0]
    others = list(range(1, ch.n))
    seen: set = set()
    out: list[dict] = []
    for perm in permutations(range(ch.n)):
        rch = relabel(ch, perm)
        for bits in product((0, 1), repeat=ch.n - 1):
            flip = {others[i] for i, b in enumerate(bits) if b}
            img = rch.reorient(flip)
            for signs in (img.signs,
                          {t: -v for t, v in img.signs.items()}):   # 전역 부정 포함 (0025)
                if gauge_fixed and signs[first] != 1:
                    continue
                key = tuple(signs[s] for s in subs)
                if key not in seen:
                    seen.add(key)
                    out.append(dict(signs))
    return out


if __name__ == "__main__":
    import time
    from generator import generate_backtracking

    # (1) relabel 정합성: relabel 결과도 GP-valid 이고, 항등 치환은 항등 작용
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    ident = relabel(quad, tuple(range(4)))
    assert ident.signs == quad.signs
    for perm in permutations(range(4)):
        r = relabel(quad, perm)
        assert r.is_valid(), perm
    print("relabel 정합성 OK (GP-valid 보존, 항등 치환 = 항등 작용)")

    # (2) witness 불변성 실측: (6,3) 표본에서 임의 (σ, flip) 작용 후에도
    #     witness 여부가 정확히 보존되는지 — 이 불변성이 orbit 축소의 정당성이다.
    import random
    rng = random.Random(41)
    corpus = list(generate_backtracking(6, 3, dedup=False,
                                        max_candidates=60, max_nodes=10**9))
    for ch in corpus[:30]:
        w0 = not ch.is_reorientable_to_convex()[0]
        perm = tuple(rng.sample(range(6), 6))
        flip = {e for e in range(1, 6) if rng.random() < 0.5}
        moved = relabel(ch, perm).reorient(flip)
        w1 = not moved.is_reorientable_to_convex()[0]
        assert w0 == w1, (perm, flip)
    print("witness (σ,ρ)-불변성 실측 OK (30건, 무작위 군 원소)")

    # (3) canonical_form 이 orbit 불변인지: 같은 chirotope 에 임의 군 원소를 가해도
    #     canonical_form 이 동일해야 한다.
    base = corpus[0]
    k0 = canonical_form(base)
    for _ in range(5):
        perm = tuple(rng.sample(range(6), 6))
        flip = {e for e in range(1, 6) if rng.random() < 0.5}
        assert canonical_form(relabel(base, perm).reorient(flip)) == k0
    print("canonical_form orbit-불변성 OK")

    # (4) orbit_dedup 계약: silent drop 없음 + 크기 보존 + witness orbit 손실 0
    #     (5,3) 전수 192개 → orbit 축소 후, 모든 대표의 witness 여부가 그 orbit
    #     구성원 전체와 일치하는지 전수 확인.
    t0 = time.perf_counter()
    full53 = list(generate_backtracking(5, 3, dedup=False,
                                        max_candidates=10**9, max_nodes=10**9))
    dd = orbit_dedup(full53)
    t_dd = time.perf_counter() - t0
    assert len(dd["orbit_of"]) == len(full53) == sum(dd["orbit_sizes_seen"])
    reps = dd["representatives"]
    rep_w = [not r.is_reorientable_to_convex()[0] for r in reps]
    for i, ch in enumerate(full53):
        w = not ch.is_reorientable_to_convex()[0]
        assert w == rep_w[dd["orbit_of"][i]], f"witness orbit 손실: 입력 {i}"
    print(f"(5,3) 전수 192 → orbit {len(reps)}개 ({t_dd:.1f}s), "
          f"silent drop 0, witness orbit 손실 0")

    # (5) 간이 지표와의 구분: |Aut| 는 군 크기의 약수여야 한다 (Lagrange sanity)
    a = automorphism_count(quad)
    assert group_order(4) % a == 0 and a >= 1
    print(f"automorphism_count(볼록 사각형) = {a} (군 크기 {group_order(4)} 의 약수) — "
          f"om_core 간이 symmetry_order 와 별개 개념임을 명시")

    # (6) 0025 회귀 방지: orbit-stabilizer 정리 정합 — 게이지 슬라이스 크기가
    #     정확히 group_order/(2·|Stab|) 이어야 한다 (이 정합이 깨졌던 것이 0025 버그).
    wit63 = next(ch for ch in generate_backtracking(6, 3, dedup=False,
                                                    max_candidates=10**9,
                                                    max_nodes=10**9)
                 if not ch.is_reorientable_to_convex()[0])
    slice_size = len(orbit_images(wit63, gauge_fixed=True))
    stab = automorphism_count(wit63)
    assert slice_size == group_order(6) // (2 * stab), (slice_size, stab)
    print(f"orbit-stabilizer 정합 OK (slice {slice_size} == {group_order(6)}/(2·{stab}))")

    print("symmetry_reduction core-contract assertions OK "
          "(불변성 실측 / lex-leader orbit / silent drop 금지 / witness 손실 0)")
