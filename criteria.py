"""
criteria.py — 탐색 기준(옵션) 시스템.

요구사항 #2("이론적 성질을 쉽게 넣고 뺄 수 있는 옵션화")와 #3(어떤 성질을 썼는지 명확한 도출)의 핵심.

개념:
  * Criterion = (이름, OM에 대한 술어 predicate, mode, 설명).
  * mode 는 셋 중 하나:
      - "require": 후보가 탐색에 채택되려면 이 성질을 만족해야 한다.
      - "forbid" : 이 성질을 만족하면 탈락.
      - "target" : '달성하면 성공(hit)'으로 보는 목표 성질. 여러 개면 AND.
  * REGISTRY: 이름 -> Criterion 팩토리. config(YAML)에서 이름으로 참조한다.
  * 사용자 정의 기준은 register() 한 줄로 추가 (아래 예시 참조).

설계 원칙: 모든 술어는 om_core 의 결정론적 판별만 호출한다. 여기서 '주관'은 들어가지 않는다.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

from om_core import Chirotope

Predicate = Callable[[Chirotope], bool]


@dataclass
class Criterion:
    name: str
    predicate: Predicate
    mode: str = "require"          # "require" | "forbid" | "target"
    description: str = ""

    def holds(self, ch: Chirotope) -> bool:
        return bool(self.predicate(ch))


# ───────────────────────────── 내장 기준 레지스트리 ─────────────────────────────
# 각 항목은 mode 를 인자로 받아 Criterion 을 만드는 팩토리. config 에서 이름으로 부른다.
REGISTRY: dict[str, Callable[..., Criterion]] = {}


def register(name: str, predicate: Predicate, description: str = ""):
    """사용자 정의 기준 등록. 예:
        register("my_prop", lambda ch: ..., "내 성질 설명")
    이후 config 의 criteria 목록에서 {name: my_prop, mode: require} 로 사용 가능."""
    REGISTRY[name] = lambda mode="require": Criterion(name, predicate, mode, description)
    return REGISTRY[name]


# 기본 제공 술어들 — 전부 om_core 결정론적 판별
register("valid",
         lambda ch: ch.is_valid(),
         "Grassmann–Plücker 공리를 만족하는 적법한 uniform OM")
register("acyclic",
         lambda ch: ch.is_acyclic(),
         "양의 회로가 없음 (점 배치로 실현 시 '뒤집힘' 없음)")
register("totally_cyclic",
         lambda ch: ch.is_totally_cyclic(),
         "양의 코회로가 없음 = acyclic 의 쌍대 (원점이 내부). convex 와 무관")
register("convex_position",
         lambda ch: ch.is_convex_position(),
         "모든 Radon 분할이 균형 = convex independent")
register("reorientable_to_convex",
         lambda ch: ch.is_reorientable_to_convex()[0],
         "어떤 재배향으로 convex position 이 됨")
register("not_reorientable_to_convex",
         lambda ch: not ch.is_reorientable_to_convex()[0],
         "어떤 재배향으로도 convex 가 안 됨 → McMullen 상한 witness")


# 매개변수형 기준 예시 (팩토리 직접 등록) — 확장 방법의 본보기
def min_symmetry_order(k: int, mode: str = "require") -> Criterion:
    """재배향-서명이 자기 자신과 겹치는 정도로 본 '대칭 풍부함' 하한.
    (간이 지표: canonical_key 가 안정적일수록 대칭이 크다고 가정)."""
    def pred(ch: Chirotope) -> bool:
        # 간단화: 전역반전을 제외한 재배향 중 부호열을 보존하는 개수를 센다.
        from itertools import product as _p
        subs = sorted(ch.signs)
        base = tuple(ch.signs[s] for s in subs)
        cnt = 0
        others = list(range(1, ch.n))
        for bits in _p((0, 1), repeat=len(others)):
            flip = {others[i] for i, b in enumerate(bits) if b}
            if tuple(ch.reorient(flip).signs[s] for s in subs) == base:
                cnt += 1
        return cnt >= k
    return Criterion(f"min_symmetry_order({k})", pred, mode,
                     f"부호 보존 재배향 수 >= {k}")


def circuit_balance_at_least(min_side: int, mode: str = "require") -> Criterion:
    """모든 회로에서 작은 쪽 크기가 min_side 이상 (convex_position 은 min_side=2 특수경우)."""
    from itertools import combinations as _c

    def pred(ch: Chirotope) -> bool:
        for S in _c(range(ch.n), ch.r + 1):
            C = ch.circuit(S)
            pos = sum(1 for v in C.values() if v > 0)
            if min(pos, len(C) - pos) < min_side:
                return False
        return True
    return Criterion(f"circuit_balance_at_least({min_side})", pred, mode,
                     f"모든 Radon 분할의 작은 쪽 >= {min_side}")


REGISTRY["min_symmetry_order"] = min_symmetry_order
REGISTRY["circuit_balance_at_least"] = circuit_balance_at_least


# ───────────────────────────── 기준 집합 ─────────────────────────────
@dataclass
class CriterionReport:
    accepted: bool                       # require 모두 통과 & forbid 모두 불성립
    is_target_hit: bool                  # target 모두 성립
    satisfied: list[str] = field(default_factory=list)   # 성립한 기준 이름들
    failed: list[str] = field(default_factory=list)      # 불성립/위반한 기준 이름들


@dataclass
class CriteriaSet:
    """활성화된 기준들의 모음. config 에서 빌드된다."""
    criteria: list[Criterion] = field(default_factory=list)

    @classmethod
    def from_config(cls, items: list[dict]) -> "CriteriaSet":
        """items 예:
            [{name: valid, mode: require},
             {name: acyclic, mode: require},
             {name: totally_cyclic, mode: forbid},
             {name: not_reorientable_to_convex, mode: target},
             {name: circuit_balance_at_least, mode: require, args: [2]}]
        """
        built = []
        for it in items:
            name = it["name"]; mode = it.get("mode", "require"); args = it.get("args", [])
            if name not in REGISTRY:
                raise KeyError(f"알 수 없는 기준 '{name}'. 사용 가능: {sorted(REGISTRY)}")
            factory = REGISTRY[name]
            crit = factory(*args, mode=mode) if args else factory(mode=mode)
            built.append(crit)
        return cls(built)

    def evaluate(self, ch: Chirotope) -> CriterionReport:
        satisfied, failed = [], []
        accepted, target_hit = True, True
        any_target = False
        for c in self.criteria:
            ok = c.holds(ch)
            (satisfied if ok else failed).append(c.name)
            if c.mode == "require" and not ok:
                accepted = False
            elif c.mode == "forbid" and ok:
                accepted = False
            elif c.mode == "target":
                any_target = True
                if not ok:
                    target_hit = False
        if not any_target:
            target_hit = False     # 목표가 하나도 없으면 'hit' 정의 불가
        return CriterionReport(accepted=accepted, is_target_hit=target_hit,
                               satisfied=satisfied, failed=failed)

    def active_summary(self) -> list[dict]:
        """provenance 기록용: 어떤 기준이 어떤 mode 로 활성화됐는지."""
        return [{"name": c.name, "mode": c.mode, "description": c.description}
                for c in self.criteria]


if __name__ == "__main__":
    # 데모: 삼각형+내부점은 acyclic 이지만 convex 가 아니고 재배향으로 convex 가능
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    cs = CriteriaSet.from_config([
        {"name": "valid", "mode": "require"},
        {"name": "acyclic", "mode": "require"},
        {"name": "totally_cyclic", "mode": "forbid"},
        {"name": "not_reorientable_to_convex", "mode": "target"},
    ])
    rep = cs.evaluate(tri)
    print("accepted:", rep.accepted, "| target_hit:", rep.is_target_hit)
    print("satisfied:", rep.satisfied, "| failed:", rep.failed)
    print("active:", cs.active_summary())
