"""
interval_maps.py — ordered OM의 minimum interval map 분석 계층 (HI-0002/HI-0003).

ground set E={0,...,n-1}의 순서를 고정하고 재배향 rho에서 circuit defect를

    delta_rho(C) = min(|C^+|, |C^-|)

로 둔다. beta_k(a)는 min(C)>=a, delta_rho(C)<=k인 circuit support 가운데 가장 작은
max(C)다(없으면 sentinel n). k=0은 interval cyclicity의 정확한 lower envelope이고,
k=1에서 beta_1(0)=n은 그 재배향이 convex position이라는 것과 동치다.

단일 layer의 map과 위 동치는 결정론적 분석량이다. 여러 layer의 map composition이 최종
Lawrence union의 McMullen 성질을 예측한다는 주장은 아직 정리가 아니므로, 이 모듈의 profile은
후보 순위를 정하는 휴리스틱으로만 사용한다. 후보 제거와 witness 판정 권한은 없다.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence

from om_core import Chirotope


Support = tuple[int, ...]


@dataclass(frozen=True)
class MinimumIntervalMap:
    """beta_k와 endpoint를 실제로 달성한 circuit support.

    endpoints[a] == n은 조건을 만족하는 circuit이 없다는 sentinel이다. rank-2 sign-variation
    fast path처럼 support 복원을 생략한 경우 witnesses[a]는 None일 수 있다.
    """

    n: int
    endpoints: tuple[int, ...]
    witnesses: tuple[Support | None, ...]
    max_defect: int = 0

    def __post_init__(self):
        if self.n < 1 or len(self.endpoints) != self.n or len(self.witnesses) != self.n:
            raise ValueError("minimum interval map의 길이는 n과 같아야 함")
        if self.max_defect < 0:
            raise ValueError("max_defect는 음수일 수 없음")
        previous = -1
        for a, endpoint in enumerate(self.endpoints):
            if not isinstance(endpoint, int) or not (a <= endpoint <= self.n):
                raise ValueError(f"beta({a})={endpoint}: 허용 범위 [{a},{self.n}] 위반")
            if endpoint < previous:
                raise ValueError("minimum interval map은 nondecreasing이어야 함")
            previous = endpoint

    @property
    def sentinel(self) -> int:
        return self.n

    @property
    def area(self) -> int:
        """더 이른 finite endpoint에 더 큰 값을 주는 cyclic-interval mass."""
        return sum(self.n - endpoint for endpoint in self.endpoints
                   if endpoint < self.n)

    def strict_corners(self) -> tuple[tuple[int, int, Support | None], ...]:
        """beta(a)<beta(a+1)인 finite corner와 그 witness support."""
        return tuple(
            (a, self.endpoints[a], self.witnesses[a])
            for a in range(self.n - 1)
            if self.endpoints[a] < self.endpoints[a + 1]
            and self.endpoints[a] < self.n
        )

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "max_defect": self.max_defect,
            "sentinel": self.n,
            "endpoints": list(self.endpoints),
            "area": self.area,
            "strict_corners": [
                {"left": a, "right": b,
                 "support": list(support) if support is not None else None}
                for a, b, support in self.strict_corners()
            ],
        }


def circuit_defect(ch: Chirotope, support: Iterable[int],
                   flip: Iterable[int] = ()) -> int:
    """재배향 뒤 signed circuit의 작은 쪽 크기.

    signed circuit 자체의 전역 부호는 defect에 영향을 주지 않는다. 재배향은 support 안의
    해당 좌표 부호만 뒤집는다.
    """
    support = tuple(sorted(support))
    if len(support) != ch.r + 1:
        raise ValueError(f"uniform rank-{ch.r} circuit support는 {ch.r + 1}원소여야 함")
    flipped = frozenset(flip)
    circuit = ch.circuit(support)
    positive = sum(1 for e, sign in circuit.items()
                   if sign * (-1 if e in flipped else 1) > 0)
    return min(positive, len(support) - positive)


def minimum_interval_map(ch: Chirotope, flip: Iterable[int] = (), *,
                         max_defect: int = 0) -> MinimumIntervalMap:
    """circuit enumeration으로 beta_k를 정확히 계산한다.

    먼저 circuit의 실제 left endpoint별 최소 right endpoint를 모은 뒤 suffix minimum을
    취한다. 따라서 순진한 모든 [a,b] restriction 검사를 반복하지 않는다.
    """
    if max_defect < 0:
        raise ValueError("max_defect는 음수일 수 없음")
    n = ch.n
    best_right = [n] * n
    best_support: list[Support | None] = [None] * n
    flipped = frozenset(flip)
    for support in combinations(range(n), ch.r + 1):
        if circuit_defect(ch, support, flipped) > max_defect:
            continue
        left, right = support[0], support[-1]
        current = best_support[left]
        if right < best_right[left] or (right == best_right[left]
                                       and (current is None or support < current)):
            best_right[left] = right
            best_support[left] = support

    endpoints = [n] * n
    witnesses: list[Support | None] = [None] * n
    running_right = n
    running_support: Support | None = None
    for a in range(n - 1, -1, -1):
        candidate = best_support[a]
        if (best_right[a] < running_right
                or (best_right[a] == running_right and candidate is not None
                    and (running_support is None or candidate < running_support))):
            running_right = best_right[a]
            running_support = candidate
        endpoints[a] = running_right
        witnesses[a] = running_support
    return MinimumIntervalMap(n, tuple(endpoints), tuple(witnesses), max_defect)


def _sign_variations(word: Sequence[int]) -> int:
    return sum(1 for left, right in zip(word, word[1:]) if left != right)


def rank2_minimum_interval_map(layer, flip: Iterable[int] = ()) -> MinimumIntervalMap:
    """signed-permutation rank-2 layer의 beta_0 fast path.

    label interval [a,b]에 속한 원소를 layer.order 순서로 읽은 effective sign word의 variation이
    2 이상인 최초 b를 찾는다. rank 2에서는 이것이 positive triple 존재와 동치다.
    """
    n = layer.n
    flipped = frozenset(flip)
    effective = tuple(layer.signs[e] * (-1 if e in flipped else 1)
                      for e in range(n))
    endpoints = [n] * n
    for a in range(n):
        for b in range(a, n):
            word = [effective[e] for e in layer.order if a <= e <= b]
            if len(word) >= 3 and _sign_variations(word) >= 2:
                endpoints[a] = b
                break
    return MinimumIntervalMap(n, tuple(endpoints), (None,) * n, 0)


def compose_interval_maps(*maps: MinimumIntervalMap) -> MinimumIntervalMap:
    """beta_m o ... o beta_1. sentinel은 흡수 원소로 취급한다.

    합성 endpoint는 정확히 계산하지만 final Lawrence circuit의 certificate는 아니다. 합성 뒤
    단일 circuit witness를 일반적으로 복원할 수 없으므로 witnesses는 비워 둔다.
    """
    if not maps:
        raise ValueError("합성할 map이 하나 이상 필요함")
    n = maps[0].n
    if any(mapping.n != n for mapping in maps):
        raise ValueError("모든 map의 ground-set 크기가 같아야 함")
    endpoints = list(range(n))
    for mapping in maps:
        endpoints = [n if value == n else mapping.endpoints[value]
                     for value in endpoints]
    return MinimumIntervalMap(n, tuple(endpoints), (None,) * n,
                              max(mapping.max_defect for mapping in maps))


@dataclass(frozen=True)
class IntervalHeuristicProfile:
    """공통 재배향들에서 layer-map composition을 측정한 순위 전용 통계."""

    n: int
    evaluated_reorientations: int
    total_reorientations: int
    exhaustive: bool
    min_area: int
    mean_area: float
    max_area: int
    sentinel_at_origin: int

    @property
    def score_key(self) -> tuple[float, ...]:
        """내림차순 정렬용. worst-case area를 가장 먼저 높인다."""
        return (float(self.min_area), self.mean_area,
                float(-self.sentinel_at_origin), float(self.max_area))

    def to_dict(self) -> dict:
        return {
            "kind": "heuristic",
            "n": self.n,
            "evaluated_reorientations": self.evaluated_reorientations,
            "total_reorientations": self.total_reorientations,
            "exhaustive": self.exhaustive,
            "min_area": self.min_area,
            "mean_area": self.mean_area,
            "max_area": self.max_area,
            "sentinel_at_origin": self.sentinel_at_origin,
            "score_key": list(self.score_key),
            "warning": "layer-map composition은 ranking 전용이며 final witness certificate가 아님",
        }


def _sample_reorientation_masks(total: int, limit: int | None) -> tuple[int, ...]:
    if limit is None or limit >= total:
        return tuple(range(total))
    if limit < 1:
        raise ValueError("reorientation 표본 수는 1 이상이어야 함")
    if limit == 1:
        return (0,)
    # 양 끝을 포함한 결정론적 균등 표본. seed에 의존하지 않아 후보 간 비교가 공정하다.
    return tuple(round(i * (total - 1) / (limit - 1)) for i in range(limit))


def interval_heuristic_profile(layers: Sequence, *,
                               reorientation_limit: int | None = 64
                               ) -> IntervalHeuristicProfile:
    """rank-2 layer tuple을 공통 재배향 아래 평가한다.

    원소 0은 전역 반전 gauge로 고정한다. reorientation_limit=None이면 2^(n-1)개를 전수
    평가하지만, 전수여도 map composition과 final McMullen 성질 사이의 관계는 휴리스틱이다.
    """
    if not layers:
        raise ValueError("layer가 하나 이상 필요함")
    n = layers[0].n
    if any(layer.n != n for layer in layers):
        raise ValueError("모든 layer의 ground-set 크기가 같아야 함")
    total = 1 << max(0, n - 1)
    masks = _sample_reorientation_masks(total, reorientation_limit)
    areas: list[int] = []
    sentinel_at_origin = 0
    for mask in masks:
        flip = {e for e in range(1, n) if mask & (1 << (e - 1))}
        composed = compose_interval_maps(
            *(rank2_minimum_interval_map(layer, flip) for layer in layers))
        areas.append(composed.area)
        sentinel_at_origin += int(composed.endpoints[0] == n)
    return IntervalHeuristicProfile(
        n=n,
        evaluated_reorientations=len(masks),
        total_reorientations=total,
        exhaustive=len(masks) == total,
        min_area=min(areas),
        mean_area=sum(areas) / len(areas),
        max_area=max(areas),
        sentinel_at_origin=sentinel_at_origin,
    )


def _selftest() -> None:
    import random
    from extended_lawrence import Rank2Layer, lawrence_union_chirotope

    rng = random.Random(20260810)
    for n in (5, 6):
        for _ in range(4):
            order = list(range(n)); rng.shuffle(order)
            signs = tuple(rng.choice((-1, 1)) for _ in range(n))
            layer = Rank2Layer(tuple(order), signs)
            ch = layer.to_chirotope()
            assert ch.is_valid()
            for mask in range(1 << (n - 1)):
                flip = {e for e in range(1, n) if mask & (1 << (e - 1))}
                exact0 = minimum_interval_map(ch, flip, max_defect=0)
                fast0 = rank2_minimum_interval_map(layer, flip)
                assert exact0.endpoints == fast0.endpoints
                assert (exact0.endpoints[0] == n) == ch.reorient(flip).is_acyclic()
                exact1 = minimum_interval_map(ch, flip, max_defect=1)
                assert (exact1.endpoints[0] == n) == ch.reorient(flip).is_convex_position()
                for left, right, support in exact0.strict_corners():
                    assert support is not None and support[0] == left and support[-1] == right

    layers = (
        Rank2Layer((0, 2, 4, 1, 3, 5, 6), (1, 1, -1, 1, -1, 1, 1)),
        Rank2Layer((4, 3, 1, 5, 0, 2, 6), (1, -1, 1, 1, -1, 1, -1)),
    )
    union = lawrence_union_chirotope(layers)
    for mask in range(1 << (union.n - 1)):
        flip = {e for e in range(1, union.n) if mask & (1 << (e - 1))}
        beta0 = minimum_interval_map(union, flip, max_defect=0)
        beta1 = minimum_interval_map(union, flip, max_defect=1)
        oriented = union.reorient(flip)
        assert (beta0.endpoints[0] == union.n) == oriented.is_acyclic()
        assert (beta1.endpoints[0] == union.n) == oriented.is_convex_position()

    sampled = interval_heuristic_profile(layers, reorientation_limit=9)
    exhaustive = interval_heuristic_profile(layers, reorientation_limit=None)
    assert sampled.evaluated_reorientations == 9 and not sampled.exhaustive
    assert exhaustive.evaluated_reorientations == (1 << (layers[0].n - 1))
    assert exhaustive.exhaustive
    print("interval_maps core-contract assertions OK")


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    _selftest()
