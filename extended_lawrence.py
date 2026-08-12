"""
extended_lawrence.py — rank-2 layer union 기반 extended Lawrence 탐색 class (HI-0001).

같은 전순서 ground set E 위의 uniform rank-2 oriented matroid M_i를 signed permutation으로
표현한다. 정렬된 basis B=(j_1<...<j_2m)에 대해

    chi(B) = product_i chi_i(j_{2i-1}, j_{2i})

로 정의한 rank-2m chirotope는 Lawrence-Weinberg oriented-matroid union이다. 각 rank-2 OM은
realizable이고 realizable OM의 이 union도 realizable하므로, 이 모듈의 후보는 추상 uniform
전체와 구별되는 구조적 realizable 탐색 family다.

참고: J. Lawrence and L. Weinberg, "Unions of oriented matroids",
Linear Algebra and its Applications 41 (1981), 183-200,
DOI 10.1016/0024-3795(81)90098-7.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import combinations
import random
from typing import Callable, Iterable, Iterator, Optional, Sequence

from om_core import Chirotope


@dataclass(frozen=True)
class Rank2Layer:
    """uniform rank-2 OM의 signed-permutation 표현.

    order는 원소가 projective line에서 나타나는 순서이고 signs[e]는 원소 e의 재배향 부호다.
    i!=j일 때 chi(i,j)=signs[i]signs[j]sign(pos(j)-pos(i)).
    """

    order: tuple[int, ...]
    signs: tuple[int, ...]

    def __post_init__(self):
        n = len(self.order)
        if n < 2:
            raise ValueError("rank-2 layer는 원소가 둘 이상이어야 함")
        if tuple(sorted(self.order)) != tuple(range(n)):
            raise ValueError("order는 0,...,n-1의 순열이어야 함")
        if len(self.signs) != n or any(sign not in (-1, 1) for sign in self.signs):
            raise ValueError("signs는 원소별 ±1 tuple이어야 함")

    @property
    def n(self) -> int:
        return len(self.order)

    @cached_property
    def positions(self) -> tuple[int, ...]:
        out = [0] * self.n
        for position, element in enumerate(self.order):
            out[element] = position
        return tuple(out)

    def chi(self, i: int, j: int) -> int:
        if not (0 <= i < self.n and 0 <= j < self.n):
            raise IndexError("rank-2 layer 원소 범위 밖")
        if i == j:
            return 0
        sign = self.signs[i] * self.signs[j]
        return sign if self.positions[i] < self.positions[j] else -sign

    def to_chirotope(self) -> Chirotope:
        return Chirotope(self.n, 2, {
            pair: self.chi(*pair) for pair in combinations(range(self.n), 2)
        })

    def reorient(self, flip: Iterable[int]) -> "Rank2Layer":
        flipped = frozenset(flip)
        return Rank2Layer(self.order, tuple(
            -sign if element in flipped else sign
            for element, sign in enumerate(self.signs)
        ))

    def to_dict(self) -> dict:
        return {"rank": 2, "order": list(self.order), "signs": list(self.signs)}

    @classmethod
    def from_dict(cls, data: dict) -> "Rank2Layer":
        if data.get("rank", 2) != 2:
            raise ValueError("현재 extended Lawrence 구현은 rank-2 layer만 지원")
        return cls(tuple(data["order"]), tuple(data["signs"]))


def alternating_rank2_layer(n: int) -> Rank2Layer:
    return Rank2Layer(tuple(range(n)), (1,) * n)


def lawrence_union_chirotope(layers: Sequence[Rank2Layer]) -> Chirotope:
    """rank-2 layer들의 Lawrence-Weinberg union chirotope를 직접 만든다."""
    layers = tuple(layers)
    if not layers:
        raise ValueError("layer가 하나 이상 필요함")
    n = layers[0].n
    if any(layer.n != n for layer in layers):
        raise ValueError("모든 layer는 같은 ground set을 사용해야 함")
    rank = 2 * len(layers)
    if rank >= n:
        raise ValueError(f"Lawrence union은 현재 탐색 범위에서 rank={rank} < n={n}이어야 함")

    signs = {}
    for basis in combinations(range(n), rank):
        sign = 1
        for layer_index, layer in enumerate(layers):
            offset = 2 * layer_index
            sign *= layer.chi(basis[offset], basis[offset + 1])
        signs[basis] = sign
    ch = Chirotope(n, rank, signs)
    # fail-closed: 곱 공식이 항상 GP를 만족한다는 것은 **아직 이 저장소에서 증명되지 않았다**
    # (감사 328표본 위반 0 — 반증되지 않았을 뿐이다). mcmullen_evaluate는 is_valid를
    # 확인하지 않으므로, 비-OM이 witness로 보고되는 경로를 여기서 막는다.
    if not ch.is_valid():
        raise ValueError(
            "Lawrence union이 GP 3항 공리를 위반했다 — HI-0001의 union validity 주장에 "
            "대한 반례다. layers를 반드시 보존해 research_log에 기록할 것: "
            f"{[layer.to_dict() for layer in layers]}")
    # Chirotope 직렬화 계약은 건드리지 않고, ResultsStore가 읽을 수 있는 구성 provenance를
    # 부가 속성으로 둔다. witness 판정에는 이 필드를 사용하지 않는다.
    ch.construction = {
        "family": "extended_lawrence_r2",
        "encoding": "lawrence-weinberg-ordered-chirotope-product/v1",
        # ⚠ CLAUDE.md 불변조건 7. 이 값을 "REALIZABLE"로 되돌리지 말 것.
        # 근거: (a) Lawrence-Weinberg 원문을 이 저장소가 아직 대조하지 못했고,
        #       (b) 감사 결과 **자명한 실현이 이 chirotope를 재현하지 못한다** —
        #           각 layer를 R^2에 실현해 세로로 쌓아도 2m x 2m 행렬식은 한 짝짓기의
        #           곱이 아니라 Laplace 전개상 모든 짝짓기의 부호합이므로 일치하지 않는다
        #           (scripts/audit_extended_lawrence.py, 12/12 불일치).
        # 따라서 이 family의 witness는 그것만으로 ν(d) 상한을 증명하지 않는다.
        "realizability": "CLAIMED_UNVERIFIED",
        "realizability_note": (
            "layer가 realizable이므로 union도 realizable이라는 주장은 미검증이다. "
            "실현가능성이 필요한 결론에는 명시적 정수 좌표 실현이 별도로 필요하다."),
        "realizability_refs": ["HI-0001", "scripts/audit_extended_lawrence.py",
                               "docs/DECISIONS.md#0034"],
        "rank": rank,
        "n": n,
        "layer_ranks": [2] * len(layers),
        "layers": [layer.to_dict() for layer in layers],
        "insight_ids": ["HI-0001"],
    }
    return ch


# ══ 명시적 실현 (HI-0004) ══════════════════════════════════════════════
#
# ## 왜 '층을 그냥 쌓기'로는 안 되는가
#
# 원소 j 의 최종 벡터를 w_j = (c_{0,j} v^(0)_j, ..., c_{m-1,j} v^(m-1)_j) ∈ R^{2m} 로 두면
# basis B={j_1<...<j_{2m}} 의 2m×2m 행렬식은 **행 블록에 대한 일반화 Laplace 전개**로
#
#     det = Σ_{(S_0,...,S_{m-1})} ε(S) ∏_i det2_i(S_i)                        (∗)
#
# 이고, 합은 B 를 블록마다 2개씩 나누는 **모든 순서 분할**을 훑는다. union chirotope 가 쓰는
# 것은 그중 연속 짝짓기 S_i={j_{2i+1}, j_{2i+2}} **한 항**뿐이며 그 ε 는 항등순열이라 +1 이다.
#
# 여기서 **층마다 상수배 c_i 를 곱하는 것은 완전히 무력하다**: 어떤 항이든 각 블록에서 2×2
# 소행렬식을 정확히 하나씩 가지므로 모든 항에 똑같이 ∏_i c_i^2 가 붙는다. 부호 비교가 전혀
# 바뀌지 않는다. (감사 T3 가 12/12 실패한 이유가 이것이다.)
#
# ## 무엇을 곱해야 하는가
#
# 계수를 **원소마다·블록마다** 다르게 준다. c_{i,j} = t^{i·λ_j} 로 두면 항 (S_0..S_{m-1}) 의
# t-지수는
#
#     E(S) = Σ_i i·(λ_a + λ_b),   S_i = {a, b}
#
# 즉 **각 원소가 어느 블록에 배정됐는지만**으로 결정된다. λ 가 증가수열이면 재배열 부등식에
# 의해 E 를 최대화하는 배정은 "가장 큰 λ 둘 → 블록 m-1, 그다음 둘 → 블록 m-2, …" 이고,
# 이는 정확히 **연속 짝짓기**다. 따라서 t 를 충분히 키우면 (∗) 에서 그 항이 나머지를 압도하여
#
#     sign(det) = ∏_i χ_i(j_{2i+1}, j_{2i+2})
#
# 가 된다 — union chirotope 가 **명시적 좌표로 실현**된다.
#
# ## 이 저장소가 취하는 입장
#
# 위 논증은 λ 동점(E 가 같은 두 배정)이 없다는 조건이 필요하고, t 하한도 소행렬식 크기에
# 의존한다. 그래서 **일반 정리로 가정하지 않는다.** 대신 후보마다 정수 좌표를 실제로 만들고
# `om_core` 로 **정확히 대조**한다. 대조에 성공한 좌표 자체가 그 후보의 실현 증명서다
# (per-object 검증). 일반 명제(모든 이런 union 이 realizable)는 HI-0004 로 별도 추적한다.

_REALIZATION_SCHEMES = (
    ("lambda=j+1", lambda j: j + 1),
    ("lambda=(j+1)^2", lambda j: (j + 1) ** 2),
    ("lambda=2^j", lambda j: 2 ** j),
)
_REALIZATION_SCALES = (3, 11, 101, 10007)


def layer_vectors(layer: Rank2Layer) -> list[tuple[int, int]]:
    """rank-2 layer 의 정수 실현. v_j = s_j·(1, x_j), x 는 order 를 따르는 증가수열.

    det[v_i; v_j] = s_i s_j (x_j − x_i) 이므로 부호가 `Rank2Layer.chi` 와 정확히 같다."""
    return [(layer.signs[j], layer.signs[j] * (layer.positions[j] + 1))
            for j in range(layer.n)]


def stack_vectors(layers: Sequence[Rank2Layer], t: int, lam) -> list[list[int]]:
    """블록·원소별 계수 t^(i·λ_j) 로 rank-2 실현들을 쌓아 R^(2m) 정수 벡터를 만든다."""
    n = layers[0].n
    per_layer = [layer_vectors(layer) for layer in layers]
    out = []
    for j in range(n):
        row: list[int] = []
        for i in range(len(layers)):
            c = t ** (i * lam(j))
            row += [c * per_layer[i][j][0], c * per_layer[i][j][1]]
        out.append(row)
    return out


def realize_union(layers: Sequence[Rank2Layer],
                  target: Optional[Chirotope] = None) -> Optional[dict]:
    """union chirotope 를 재현하는 **정수 벡터 실현**을 찾는다. 못 찾으면 None.

    반환값은 실현 증명서다: 좌표와 (스킴, t) 를 담고, 이미 `om_core` 의 정확한 정수
    행렬식으로 대조를 마친 상태다. 실패 시 None 을 돌려주는 fail-closed 설계이며,
    **추정으로 REALIZABLE 을 붙이는 경로는 없다.**"""
    if target is None:
        target = lawrence_union_chirotope(layers)
    for name, lam in _REALIZATION_SCHEMES:
        for t in _REALIZATION_SCALES:
            vectors = stack_vectors(layers, t, lam)
            try:
                candidate = Chirotope.from_vectors(vectors)
            except ValueError:
                continue                       # 균일하지 않으면(=0 행렬식) 다음 계수로
            if candidate.signs == target.signs:
                return {"kind": "integer_vector_realization",
                        "rank": target.r, "n": target.n,
                        "scheme": name, "scale_t": t,
                        "vectors": [list(v) for v in vectors],
                        "verified_by": "om_core.Chirotope.from_vectors 부호 완전 일치",
                        "insight_ids": ["HI-0001", "HI-0004"]}
    return None


def generate_extended_lawrence_rank2_realized(
    n: int,
    r: int,
    *,
    accept: Optional[Callable[[Chirotope], bool]] = None,
    dedup: bool = True,
    max_candidates: int = 200,
    seed: Optional[int] = None,
    max_tries: Optional[int] = None,
) -> Iterator[Chirotope]:
    """실현 증명서가 **검증된 후보만** 방출한다 (extended_lawrence_r2_realized).

    `extended_lawrence_r2` 와 같은 family 지만, 후보마다 정수 벡터 실현을 만들어
    `om_core` 로 대조하고 **성공한 것만** 내보낸다. 따라서 이 class 의 후보는
    `realizability = "REALIZABLE"` 을 주장이 아니라 **증명서와 함께** 갖는다.
    대조에 실패한 후보는 조용히 버린다(fail-closed) — 그 경우 realizability 를
    낮춰 붙이는 대신 아예 방출하지 않는다."""
    emitted = 0
    for ch in generate_extended_lawrence_rank2(
            n, r, accept=None, dedup=dedup,
            max_candidates=max_candidates * 4 if max_candidates else 0,
            seed=seed, max_tries=max_tries):
        cert = realize_union(layers_from_construction(ch.construction), target=ch)
        if cert is None:
            continue
        ch.construction = dict(ch.construction)
        ch.construction["realizability"] = "REALIZABLE"
        ch.construction["realizability_note"] = (
            "명시적 정수 벡터 실현을 om_core 로 대조해 확인했다 (per-object 검증). "
            "이 후보에서 witness 가 나오면 ν(d) 상한 결론에 사용할 수 있다.")
        ch.construction["realization_certificate"] = cert
        ch.construction["insight_ids"] = list(ch.construction["insight_ids"]) + ["HI-0004"]
        if accept is not None and not accept(ch):
            continue
        emitted += 1
        yield ch
        if emitted >= max_candidates:
            return


def layers_from_construction(data: dict) -> tuple[Rank2Layer, ...]:
    if data.get("family") != "extended_lawrence_r2":
        raise ValueError("extended_lawrence_r2 construction이 아님")
    return tuple(Rank2Layer.from_dict(layer) for layer in data["layers"])


def _random_layer_tuple(n: int, num_layers: int,
                        rng: random.Random) -> tuple[Rank2Layer, ...]:
    layers = []
    for layer_index in range(num_layers):
        order = list(range(n)); rng.shuffle(order)
        if layer_index == 0:
            # 모든 layer에 같은 재배향을 가하면 최종 union의 재배향이다. 따라서 첫 layer의
            # sign vector를 +로 gauge-fix해도 McMullen 재배향 궤도를 잃지 않는다.
            signs = [1] * n
        else:
            signs = [rng.choice((-1, 1)) for _ in range(n)]
            # 전체 sign vector 반전은 rank-2 chirotope 자체를 바꾸지 않는다.
            if signs[0] < 0:
                signs = [-sign for sign in signs]
        layers.append(Rank2Layer(tuple(order), tuple(signs)))
    return tuple(layers)


def _heuristic_limit(mode, sampled_reorientations: int) -> int | None | bool:
    if mode in (False, None, "", "off", "none"):
        return False
    if mode in (True, "sampled", "on"):
        if sampled_reorientations < 1:
            raise ValueError("interval_reorientations는 1 이상이어야 함")
        return sampled_reorientations
    if mode == "exhaustive":
        return None
    raise ValueError("interval_heuristic은 off, sampled, exhaustive 중 하나여야 함")


def generate_extended_lawrence_rank2(
    n: int,
    r: int,
    *,
    accept: Optional[Callable[[Chirotope], bool]] = None,
    dedup: bool = True,
    max_candidates: int = 200,
    seed: Optional[int] = None,
    max_tries: Optional[int] = None,
    interval_heuristic=False,
    interval_pool_size: int = 8,
    interval_reorientations: int = 64,
) -> Iterator[Chirotope]:
    """signed-permutation layer tuple을 표집해 rank-r extended Lawrence 후보를 방출한다.

    interval_heuristic="sampled" 또는 "exhaustive"이면 작은 후보 pool 안에서 layer map
    composition score가 큰 후보를 먼저 방출한다(HI-0003). 순서만 바꾸며 후보를 제거하지
    않는다. 최종 witness 여부는 호출부의 mcmullen_evaluate가 별도로 결정한다.
    """
    if r < 2 or r % 2:
        raise ValueError("extended_lawrence_r2는 짝수 rank r=2m만 지원")
    if n <= r:
        raise ValueError("uniform McMullen 탐색에는 n>r가 필요함")
    if max_candidates < 0:
        raise ValueError("max_candidates는 음수일 수 없음")
    if interval_pool_size < 1:
        raise ValueError("interval_pool_size는 1 이상이어야 함")
    heuristic_limit = _heuristic_limit(interval_heuristic, interval_reorientations)
    if heuristic_limit is False:
        interval_pool_size = 1

    num_layers = r // 2
    rng = random.Random(seed)
    if max_tries is None:
        max_tries = max(100, max_candidates * 100)
    if max_tries < 1:
        raise ValueError("max_tries는 1 이상이어야 함")

    seen: set[tuple[int, ...]] = set()
    emitted = 0
    attempts = 0
    baseline = tuple(alternating_rank2_layer(n) for _ in range(num_layers))

    while emitted < max_candidates and attempts < max_tries:
        pool = []
        while len(pool) < interval_pool_size and attempts < max_tries:
            layers = baseline if attempts == 0 else _random_layer_tuple(n, num_layers, rng)
            attempts += 1
            ch = lawrence_union_chirotope(layers)
            key = tuple(ch.signs[basis] for basis in sorted(ch.signs))
            if dedup and key in seen:
                continue
            seen.add(key)

            score_key = (0.0,)
            if heuristic_limit is not False:
                from interval_maps import interval_heuristic_profile
                profile = interval_heuristic_profile(
                    layers, reorientation_limit=heuristic_limit)
                ch.construction["interval_heuristic"] = profile.to_dict()
                ch.construction["insight_ids"].append("HI-0003")
                score_key = profile.score_key
            pool.append((score_key, -attempts, ch))

        pool.sort(key=lambda item: (item[0], item[1]), reverse=True)
        for _, __, ch in pool:
            if accept is not None and not accept(ch):
                continue
            emitted += 1
            yield ch
            if emitted >= max_candidates:
                return


def _selftest() -> None:
    # 모든 layer가 alternating이면 product도 alternating이다.
    all_alt = lawrence_union_chirotope([alternating_rank2_layer(8)] * 3)
    assert all_alt.r == 6 and all(sign == 1 for sign in all_alt.signs.values())
    assert all_alt.is_valid()

    layers = (
        Rank2Layer((0, 2, 4, 1, 3, 5, 6), (1, 1, -1, 1, -1, 1, 1)),
        Rank2Layer((4, 3, 1, 5, 0, 2, 6), (1, -1, 1, 1, -1, 1, -1)),
    )
    ch = lawrence_union_chirotope(layers)
    assert ch.is_valid()
    rebuilt = lawrence_union_chirotope(layers_from_construction(ch.construction))
    assert rebuilt.signs == ch.signs

    # 모든 layer에 같은 flip을 적용하면 최종 union을 한 번 reorient한 것과 정확히 같다.
    for mask in range(1 << (ch.n - 1)):
        flip = {e for e in range(1, ch.n) if mask & (1 << (e - 1))}
        via_layers = lawrence_union_chirotope([layer.reorient(flip) for layer in layers])
        assert via_layers.signs == ch.reorient(flip).signs

    generated = list(generate_extended_lawrence_rank2(
        7, 4, max_candidates=6, seed=17, dedup=True))
    assert len(generated) == 6
    assert all(candidate.is_valid() for candidate in generated)
    # 실현가능성 라벨은 미검증이어야 한다 — "REALIZABLE"로 되돌리는 회귀를 여기서 막는다.
    assert all(candidate.construction["realizability"] == "CLAIMED_UNVERIFIED"
               for candidate in generated)

    ranked = list(generate_extended_lawrence_rank2(
        7, 4, max_candidates=3, seed=17, interval_heuristic="sampled",
        interval_pool_size=3, interval_reorientations=9))
    assert len(ranked) == 3
    assert all(candidate.construction["interval_heuristic"]["kind"] == "heuristic"
               for candidate in ranked)

    try:
        list(generate_extended_lawrence_rank2(7, 3, max_candidates=1))
        raise AssertionError("홀수 rank가 통과함")
    except ValueError:
        pass

    # ── 명시적 실현 (HI-0004) ────────────────────────────────────────
    # (a) 층마다 상수배만 곱하는 것은 **원리상 무력**하다: Laplace 전개의 모든 항에
    #     ∏ c_i^2 가 똑같이 붙는다. 회귀로 되돌아오지 않도록 여기서 못박는다.
    probe = (Rank2Layer((0, 2, 4, 1, 3, 5, 6, 7), (1, 1, -1, 1, -1, 1, 1, -1)),
             Rank2Layer((4, 3, 1, 5, 0, 2, 7, 6), (1, -1, 1, 1, -1, 1, -1, 1)),
             Rank2Layer((7, 1, 0, 6, 2, 5, 3, 4), (1, 1, 1, -1, -1, 1, 1, 1)))
    union = lawrence_union_chirotope(probe)
    flat = [layer_vectors(layer) for layer in probe]
    for constants in ([1, 1, 1], [1, 10 ** 3, 10 ** 6]):
        naive = [[constants[i] * value for i in range(3) for value in flat[i][j]]
                 for j in range(union.n)]
        try:
            reproduced = Chirotope.from_vectors(naive).signs == union.signs
        except ValueError:
            reproduced = False          # 행렬식 0 — uniform 조차 아니다(더 강한 실패)
        assert not reproduced, "층별 상수배가 union을 재현했다 — 위 Laplace 논증을 다시 볼 것"

    # (b) 블록·원소별 계수 t^(i·λ_j) 는 재현한다. 그 좌표가 곧 실현 증명서다.
    certificate = realize_union(probe, target=union)
    assert certificate is not None, "유도한 계수로도 실현하지 못했다"
    assert Chirotope.from_vectors(certificate["vectors"]).signs == union.signs

    realized = list(generate_extended_lawrence_rank2_realized(
        8, 6, max_candidates=4, seed=17))
    assert len(realized) == 4
    for candidate in realized:
        assert candidate.construction["realizability"] == "REALIZABLE"
        cert = candidate.construction["realization_certificate"]
        # 증명서를 **다시** 처음부터 검증한다 — 저장된 라벨을 믿지 않는다.
        assert Chirotope.from_vectors(cert["vectors"]).signs == candidate.signs

    print("extended_lawrence core-contract assertions OK")


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    _selftest()
