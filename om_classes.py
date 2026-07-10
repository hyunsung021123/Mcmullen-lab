"""
om_classes.py — '클래스(탐색 공간) 선택' 시스템 (요구사항 #1).

루프를 어떤 OM 집합 위에서 돌릴지 이름 하나로 지정한다. 각 클래스는
  · rank (고정 여부)         · 생성 백엔드        · 자동 적용 기준(base_criteria)
  · realizable 여부          · 솔직성 주석(note)
를 묶는다. config/CLI/대시보드에서 이름으로 참조한다.

사용자 클래스 추가(예: 당신의 REOM rank-2 Lawrence 인코딩):
    from om_classes import OMClass, register_class
    register_class(OMClass("reom", "rank-2 Lawrence(REOM)", backend="custom", rank=2),
                   generator=my_reom_generator)   # my_reom_generator(n, r, *, accept, **kw) -> Iterator[Chirotope]
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Iterator

from om_core import Chirotope
from generator import (generate_backtracking, generate_random_realizable,
                       generate_z3, generate_cyclic)


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
    backend="backtracking", rank=2,
    note="rank=2 는 문자 그대로는 d=1. rank-6 McMullen 의 REOM 인코딩은 별도 해석층."))

register_class(OMClass(
    "cyclic", "순환다면체(교대) OM 계열 — 기준선/시드용 (witness 아님)",
    backend="cyclic"))

register_class(OMClass(
    "lawrence", "Lawrence OM — 소켓(현재 코어는 uniform 전용)",
    backend="custom",
    note="일반 Lawrence 는 비균일이라 코어 확장 필요. rank-2 REOM 인코딩을 "
         "register_class(...,generator=generate_reom) 로 연결하면 이 자리에서 동작."))


def list_classes() -> list[dict]:
    return [{"name": c.name, "description": c.description,
             "rank": c.rank, "realizable": c.realizable, "note": c.note}
            for c in CLASS_REGISTRY.values()]


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
    for c in list_classes():
        print(f"  {c['name']:20} rank={c['rank']!s:4} realizable={c['realizable']!s:5} "
              f"{c['description']}")
    # rank2_uniform 동작 점검
    got = list(class_generator("rank2_uniform", 5, 2, dedup=True, max_candidates=5,
                               accept=None))
    print(f"\nrank2_uniform n=5 → {len(got)}개 생성, 모두 valid:",
          all(ch.is_valid() for ch in got))
