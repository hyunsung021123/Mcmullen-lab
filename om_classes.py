"""
om_classes.py — '클래스(탐색 공간) 선택' 시스템 (요구사항 #1).

루프를 어떤 OM 집합 위에서 돌릴지 이름 하나로 지정한다. 각 클래스는
  · rank (고정 여부)         · 생성 백엔드        · 자동 적용 기준(base_criteria)
  · realizable 여부          · 솔직성 주석(note)
를 묶는다. config/CLI/대시보드에서 이름으로 참조한다.

사용자 클래스 추가(내장 rank-2 확장은 extended_lawrence_r2 참고):
    from om_classes import OMClass, register_class
    register_class(OMClass("my_family", "사용자 구조적 family", backend="custom"),
                   generator=my_generator)  # (n, r, *, accept, **kw) -> Iterator[Chirotope]
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Iterator

from om_core import Chirotope
from generator import (generate_backtracking, generate_random_realizable,
                       generate_z3, generate_cyclic)
from extended_lawrence import (generate_extended_lawrence_rank2,
                               generate_extended_lawrence_rank2_realized)


@dataclass
class OMClass:
    name: str
    description: str
    backend: str = "backtracking"        # backtracking | random | z3 | cyclic | custom
    rank: Optional[int] = None           # 설정 시 rank 고정(d 무시), 아니면 d+1
    base_criteria: list = field(default_factory=list)   # 자동 적용 기준 항목
    realizable: bool = False
    note: str = ""

    def resolve_rank(self, d: int) -> int:
        return self.rank if self.rank is not None else d + 1


CLASS_REGISTRY: dict[str, OMClass] = {}
_CLASS_GENERATORS: dict[str, Callable] = {}     # name -> custom generator (소켓)


def register_class(om_class: OMClass, generator: Optional[Callable] = None):
    CLASS_REGISTRY[om_class.name] = om_class
    if generator is not None:
        _CLASS_GENERATORS[om_class.name] = generator
    return om_class


# ───────────────────────────── 내장 클래스 ─────────────────────────────
register_class(OMClass(
    "uniform", "모든 uniform OM (rank d+1, 전수 백트래킹; 비실현 포함)",
    backend="backtracking"))

register_class(OMClass(
    "realizable_uniform", "모든 realizable uniform OM (rank d+1, 무작위 점배치)",
    backend="random", realizable=True))

register_class(OMClass(
    "rank2_uniform", "모든 rank-2 uniform OM (rank=2 고정; 원형 부호열) — REOM 실험 기반",
    backend="backtracking", rank=2, realizable=True,
    note="rank=2 자체는 문자 그대로 d=1. rank-6 후보는 extended_lawrence_r2를 사용."))

register_class(OMClass(
    "cyclic", "순환다면체(교대) OM 계열 — 기준선/시드용 (witness 아님)",
    backend="cyclic"))

register_class(OMClass(
    "extended_lawrence_r2",
    "uniform rank-2 layer들의 Lawrence-Weinberg union (rank=2m)",
    backend="custom", realizable=False,
    note="rank=d+1이 짝수여야 함 → **홀수 d에서만 정의된다**(d=4 보정 불가, d=3에서 보정할 것). "
         "d=5에서는 rank-2 layer 3개를 합쳐 rank-6 후보를 생성한다. "
         "realizable=False는 '비실현임이 밝혀졌다'가 아니라 '실현가능성이 아직 확립되지 "
         "않았다'는 뜻이다 — search.py가 이 값을 om_class_realizable로 결과에 저장하므로 "
         "미검증 주장이 상한 결론으로 전파되지 않도록 fail-closed로 둔다(DECISIONS 0034). "
         "minimum interval map은 class 정의가 아닌 opt-in ranking 휴리스틱."),
    generator=generate_extended_lawrence_rank2)

register_class(OMClass(
    "extended_lawrence_r2_realized",
    "extended Lawrence union 중 **정수 좌표 실현이 검증된 것만** (rank=2m)",
    backend="custom", realizable=True,
    note="extended_lawrence_r2 와 같은 family 지만, 후보마다 블록·원소별 계수 t^(i·λ_j) 로 "
         "정수 벡터 실현을 만들어 om_core 로 대조하고 성공한 것만 방출한다(fail-closed). "
         "따라서 realizable=True 는 class 수준의 주장이 아니라 **후보마다 붙는 증명서**에 "
         "근거한다 — construction.realization_certificate 참조. 실현 실패 후보는 라벨을 "
         "낮추는 대신 아예 버린다. rank=d+1 이 짝수여야 하므로 홀수 d 전용(DECISIONS 0035)."),
    generator=generate_extended_lawrence_rank2_realized)

register_class(OMClass(
    "lawrence", "고전 rank-1 Lawrence OM — 미연결 legacy 소켓",
    backend="custom",
    note="rank-2 layer 확장은 extended_lawrence_r2를 사용. 이 이름은 기존 설정 호환을 "
         "위해 생성기 없는 소켓으로 유지."))


def list_classes() -> list[dict]:
    return [{"name": c.name, "description": c.description,
             "rank": c.rank, "realizable": c.realizable, "note": c.note}
            for c in CLASS_REGISTRY.values()]


def has_generator(name: str) -> bool:
    """이 클래스 이름으로 실제 후보를 생성할 수 있는지(UI가 실행 전에 확인하기 위한
    read-only 조회). backend='custom' 인데 소켓에 생성기가 연결되지 않았으면 False —
    이 경우 class_generator() 는 NotImplementedError 를 던진다. 판정/생성 로직 자체는
    변경하지 않는다."""
    if name not in CLASS_REGISTRY:
        return False
    oc = CLASS_REGISTRY[name]
    if oc.backend != "custom":
        return True
    return name in _CLASS_GENERATORS


def class_generator(name: str, n: int, r: int, *,
                    backend_override: Optional[str] = None, **kw) -> Iterator[Chirotope]:
    """클래스 이름으로 후보 생성기 반환. backend_override 는 generic 클래스에 적용."""
    if name not in CLASS_REGISTRY:
        raise KeyError(f"알 수 없는 클래스 '{name}'. 사용 가능: {sorted(CLASS_REGISTRY)}")
    oc = CLASS_REGISTRY[name]
    if name in _CLASS_GENERATORS:                 # 커스텀 소켓(REOM 등) 우선
        return _CLASS_GENERATORS[name](n, r, **kw)
    backend = backend_override or oc.backend
    if backend == "custom":
        raise NotImplementedError(
            f"클래스 '{name}' 에는 생성기가 없습니다. "
            f"register_class(OMClass('{name}',...), generator=...) 로 연결하세요. ({oc.note})")
    if backend == "cyclic":
        return generate_cyclic(n, r, **kw)
    if backend == "random":
        return generate_random_realizable(n, r, **kw)
    if backend == "z3":
        return generate_z3(n, r, **{k: v for k, v in kw.items() if k != "seed"})
    return generate_backtracking(n, r, **{k: v for k, v in kw.items() if k != "seed"})


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    for c in list_classes():
        print(f"  {c['name']:20} rank={c['rank']!s:4} realizable={c['realizable']!s:5} "
              f"{c['description']}")
    # rank2_uniform 동작 점검
    got = list(class_generator("rank2_uniform", 5, 2, dedup=True, max_candidates=5,
                               accept=None))
    print(f"\nrank2_uniform n=5 → {len(got)}개 생성, 모두 valid:",
          all(ch.is_valid() for ch in got))

    # has_generator: custom 백엔드인데 생성기가 없는 소켓(lawrence)은 False,
    # 그 외 내장 클래스는 전부 True 여야 한다 (UI 실행 전 차단용 read-only 조회).
    assert has_generator("uniform") is True
    assert has_generator("realizable_uniform") is True
    assert has_generator("rank2_uniform") is True
    assert has_generator("cyclic") is True
    assert has_generator("extended_lawrence_r2") is True
    assert has_generator("lawrence") is False
    assert has_generator("존재하지-않는-클래스") is False

    extended = list(class_generator(
        "extended_lawrence_r2", 7, 4, accept=None, dedup=True,
        max_candidates=4, seed=20260810))
    assert len(extended) == 4
    assert all(ch.r == 4 and ch.is_valid() for ch in extended)
    assert all(ch.construction["family"] == "extended_lawrence_r2" for ch in extended)

    # 실현 검증 class: 후보마다 증명서가 붙고, 그 증명서를 처음부터 다시 검증한다.
    realized = list(class_generator("extended_lawrence_r2_realized", 8, 6,
                                    accept=None, max_candidates=3, seed=20260810))
    assert len(realized) == 3
    for ch in realized:
        assert ch.construction["realizability"] == "REALIZABLE"
        cert = ch.construction["realization_certificate"]
        assert Chirotope.from_vectors(cert["vectors"]).signs == ch.signs
    print("has_generator core-contract assertions OK")
