"""
invariants.py — 개방형 불변량 어휘(vocabulary).

## 이 모듈이 푸는 문제

지금까지 이 저장소가 "수학적 성질"을 말할 수 있는 어휘는 `discovery.invariants` 의
고정된 5개와 `criteria.REGISTRY` 의 이름 8개뿐이었다. 정리는 어휘보다 풍부해질 수
없으므로, 그 구조에서는 **아무리 좋은 LLM 을 붙여도 새 수학적 성질이 나올 수 없다.**

이 모듈은 어휘를 두 방향으로 연다:

1. **내장 어휘를 대폭 확장** — 특히 재배향 궤도 전체를 보는 양들
   (`num_tope_pairs`, `num_convex_reorientations`, `convex_tope_ratio`).
   witness ⟺ `num_convex_reorientations == 0` 이므로, 이 양은 witness 를
   0/1 이 아니라 **연속적인 '얼마나 아슬아슬한가'로 측정**한다 — 근접 실패
   (near-miss) 구조를 볼 수 있게 하는 핵심 확장이다.
2. **LLM 이 새 불변량을 코드로 추가/폐기할 수 있게 함** — `sandbox.py` 의 제한
   문법으로 컴파일하고, 아래 vetting 을 통과한 것만 어휘에 들어간다.

## 신뢰 경계

  * 불변량은 **판정 권한이 전혀 없다.** witness 라벨은 항상 `om_core` 가 만든다.
    불변량은 이미 검증된 대상에 값을 붙이는 '자(ruler)'일 뿐이다.
  * 따라서 LLM 이 쓴 불변량이 틀려도 **틀린 정리가 참으로 승격되지 않는다.**
    잘못된 추측이 하나 늘 뿐이고, 그 추측은 `falsify.py` 가 반증한다.
  * `frozen=True` 인 내장 불변량(특히 라벨 `witness`)은 덮어쓰거나 폐기할 수 없다.
  * 어휘는 `criteria` 의 `target` 모드로 승격되지 않는다 (witness 정의를 바꾸는
    유일한 경로를 차단).

## 불변성(invariance) 분류 — 정리의 의미를 좌우하는 부분

McMullen witness 성질은 **재배향 궤도 전체의 성질**이고 **원소 이름과 무관**하다.
따라서:

  * `relabel_invariant=False` 인 양으로 만든 추측은 '이 대표원소에서만 참'일 수
    있으므로 정리 후보로 신뢰할 수 없다 → `conjecture.py` 가 자동으로 강등한다.
  * `reorient_invariant=False` 인 양(예: `acyclic`)은 witness 와 동치가 될 수
    없다 — witness 는 궤도 불변인데 그 양은 대표원소에 의존하기 때문이다.
    이것도 자동으로 표시된다.

두 성질은 선언이 아니라 **표본으로 실측**한다(반증 가능한 형태로만 기록).

의존성: 표준 라이브러리 + om_core + reorientation_cover + symmetry_reduction + sandbox.
"""
from __future__ import annotations

import json
import os
import random
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from itertools import combinations, product
from typing import Callable, Optional

from om_core import Chirotope
from reorientation_cover import _subcube_mask, bad_reorientation_mask
from symmetry_reduction import relabel, automorphism_count
from sandbox import compile_invariant, SandboxError

# LLM 이 추가한 어휘가 저장되는 곳 (사람이 열어 읽을 수 있는 JSON)
VOCAB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "knowledge", "vocabulary")

LABEL_NAME = "witness"          # 유일한 라벨 — om_core 가 만든다
VALUE_KINDS = ("bool", "int", "ratio", "tuple")


# ═══════════════════════════ 불변량 자료형 ═══════════════════════════
@dataclass
class Invariant:
    name: str
    fn: Callable = field(repr=False, compare=False, default=None)
    value_kind: str = "int"
    description: str = ""
    source: str = "builtin"              # "builtin" | "llm"
    frozen: bool = False                 # True 면 덮어쓰기/폐기 불가
    relabel_invariant: Optional[bool] = None    # None = 미검사
    reorient_invariant: Optional[bool] = None
    status: str = "active"               # "active" | "deprecated"
    deprecated_reason: str = ""
    # True 면 이 양은 witness 라벨의 '정의를 다시 쓴 것'이라 라벨과의 함의가
    # 자명하다. 추측 채굴에서 라벨 상대편으로 쓰이지 않는다 (동어반복 차단).
    defines_label: bool = False
    origin: str = ""                     # 어느 응답/실험에서 나왔는지
    sandbox_source: str = ""             # LLM 작성 코드 원문 (감사용)
    max_cost_ms: Optional[float] = None  # vetting 시 실측 최대 소요
    # 비용 등급. "expensive" 는 기본 어휘에서 빠지고 명시적으로 켜야 한다 —
    # 대량 반증(수천 후보)에서 한 개의 비싼 불변량이 전체를 못 쓰게 만들기 때문.
    cost: str = "cheap"                  # "cheap" | "moderate" | "expensive"

    def meta(self) -> dict:
        d = asdict(self)
        d.pop("fn", None)
        return d


REGISTRY: dict[str, Invariant] = {}


class VocabularyError(ValueError):
    """어휘 정책 위반 (frozen 덮어쓰기, vetting 실패 등)."""


def register(name: str, fn: Callable, *, value_kind: str = "int",
             description: str = "", source: str = "builtin",
             frozen: bool = False, **kw) -> Invariant:
    if value_kind not in VALUE_KINDS:
        raise VocabularyError(f"value_kind 는 {VALUE_KINDS} 중 하나여야 함")
    old = REGISTRY.get(name)
    if old is not None and old.frozen:
        raise VocabularyError(f"'{name}' 은 frozen 내장 불변량 — 덮어쓸 수 없음")
    inv = Invariant(name=name, fn=fn, value_kind=value_kind,
                    description=description, source=source, frozen=frozen, **kw)
    REGISTRY[name] = inv
    return inv


STATUS_LEDGER = os.path.join(VOCAB_DIR, "_status.json")


def _load_ledger() -> dict:
    if not os.path.exists(STATUS_LEDGER):
        return {}
    try:
        with open(STATUS_LEDGER, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_ledger(ledger: dict) -> None:
    os.makedirs(VOCAB_DIR, exist_ok=True)
    with open(STATUS_LEDGER, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


def deprecate(name: str, reason: str, *, origin: str = "", persist: bool = True):
    """폐기(삭제 아님). 어휘에서 빠지지만 기록과 코드는 남는다 —
    '실패한 아이디어도 보존' 규칙 때문이고, 나중에 되살릴 수 있어야 하기 때문이다.

    내장 불변량의 폐기도 허용한다(LLM 이 어휘를 좁힐 수 있어야 하므로). 다만
    frozen(라벨)은 예외 없이 금지다 — 그건 어휘가 아니라 판정이다."""
    inv = REGISTRY.get(name)
    if inv is None:
        raise VocabularyError(f"없는 불변량 '{name}'")
    if inv.frozen:
        raise VocabularyError(f"'{name}' 은 frozen — 폐기 불가")
    inv.status = "deprecated"
    inv.deprecated_reason = reason
    if persist:
        ledger = _load_ledger()
        ledger[name] = {"status": "deprecated", "reason": reason, "origin": origin,
                        "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        _save_ledger(ledger)
        if inv.source == "llm":
            _save_llm_invariant(inv)
    return inv


def reinstate(name: str, reason: str = "", *, persist: bool = True):
    """폐기 취소. 판단이 틀렸을 때 되돌리는 경로가 없으면 폐기를 쓰기 어렵다."""
    inv = REGISTRY.get(name)
    if inv is None:
        raise VocabularyError(f"없는 불변량 '{name}'")
    inv.status = "active"
    inv.deprecated_reason = ""
    if persist:
        ledger = _load_ledger()
        ledger.pop(name, None)
        _save_ledger(ledger)
        if inv.source == "llm":
            _save_llm_invariant(inv)
    return inv


def apply_status_ledger() -> list[str]:
    """저장된 폐기 결정을 현재 레지스트리에 적용. 프로세스 시작 시 호출된다."""
    applied = []
    for name, rec in _load_ledger().items():
        inv = REGISTRY.get(name)
        if inv is not None and not inv.frozen and rec.get("status") == "deprecated":
            inv.status = "deprecated"
            inv.deprecated_reason = rec.get("reason", "")
            applied.append(name)
    return applied


COST_ORDER = {"cheap": 0, "moderate": 1, "expensive": 2}


def active_names(kinds: tuple[str, ...] | None = None, *,
                 max_cost: str = "moderate") -> list[str]:
    """활성 불변량 이름. 기본적으로 `expensive` 는 제외한다 —
    포함하려면 `max_cost="expensive"`."""
    limit = COST_ORDER[max_cost]
    return sorted(k for k, v in REGISTRY.items()
                  if v.status == "active"
                  and COST_ORDER.get(v.cost, 0) <= limit
                  and (kinds is None or v.value_kind in kinds))


# ═══════════════════════ 재배향 궤도 마스크 (핵심 확장) ═══════════════════════
def _cyclic_reorientation_mask(ch: Chirotope) -> int:
    """circuit 이 하나라도 '전부 같은 부호'가 되는 재배향 전체의 bitmask.

    reorientation_cover 와 같은 국소 공식을 쓴다: 재배향 후 circuit 부호는
    원래 부호에 원소별 ρ 를 곱한 것(전역 부호는 균형에 무관)이므로, support 위의
    2^|S| 패턴만 조사한 뒤 subcube 로 확장하면 된다.

    이 마스크의 여집합 = **acyclic 이 되는 재배향 = tope**(전역반전 몫)."""
    mask = 0
    for S in combinations(range(ch.n), ch.r + 1):
        S = tuple(S)
        base = ch.circuit(S)
        flippable = [s for s in S if s >= 1]
        for bits in product((1, -1), repeat=len(flippable)):
            rho = dict(zip(flippable, bits))
            pos = sum(1 for s in S if base[s] * rho.get(s, 1) > 0)
            if min(pos, len(S) - pos) == 0:          # 전부 + 또는 전부 −
                fixed = {s - 1: (1 if rho[s] == -1 else 0) for s in flippable}
                mask |= _subcube_mask(ch.n - 1, fixed)
    return mask


def _nonconvex_reorientation_mask(ch: Chirotope) -> int:
    """convex position 이 깨지는 재배향 전체 (reorientation_cover 의 coverage)."""
    mask = 0
    for S in combinations(range(ch.n), ch.r + 1):
        mask |= bad_reorientation_mask(ch, S)
    return mask


class _OrbitCache:
    """한 chirotope 에 대해 두 마스크를 한 번만 계산해 여러 불변량이 공유."""

    def __init__(self):
        self._key = None
        self._data: dict = {}

    def get(self, ch: Chirotope) -> dict:
        key = (ch.n, ch.r, id(ch), tuple(sorted(ch.signs.items())))
        if key != self._key:
            total = 1 << (ch.n - 1)
            all_mask = (1 << total) - 1
            cyc = _cyclic_reorientation_mask(ch) & all_mask
            noncvx = _nonconvex_reorientation_mask(ch) & all_mask
            self._key = key
            self._data = {
                "total": total,
                "topes": total - cyc.bit_count(),               # acyclic 재배향 수
                "convex": total - noncvx.bit_count(),           # convex 재배향 수
            }
        return self._data


_ORBIT = _OrbitCache()


# ═══════════════════════════ 내장 불변량 ═══════════════════════════
class _StructuralCache:
    """한 후보의 회로·코회로 통계를 한 번의 순회로 묶어 재사용한다."""

    def __init__(self):
        self._key = None
        self._data: dict = {}

    def get(self, ch: Chirotope) -> dict:
        key = (ch.n, ch.r, id(ch), tuple(sorted(ch.signs.items())))
        if key == self._key:
            return self._data

        circuit_balances = []
        singleton_degree: Counter = Counter({e: 0 for e in range(ch.n)})
        for support in combinations(range(ch.n), ch.r + 1):
            circuit = ch.circuit(support)
            pos = [e for e, value in circuit.items() if value > 0]
            neg = [e for e, value in circuit.items() if value < 0]
            circuit_balances.append(min(len(pos), len(neg)))
            if len(pos) == 1:
                singleton_degree[pos[0]] += 1
            elif len(neg) == 1:
                singleton_degree[neg[0]] += 1

        cocircuit_balances = []
        for hyperplane in combinations(range(ch.n), ch.r - 1):
            cocircuit = ch.cocircuit(hyperplane)
            pos = sum(1 for value in cocircuit.values() if value > 0)
            cocircuit_balances.append(min(pos, len(cocircuit) - pos))

        self._key = key
        self._data = {
            "circuit_balances": tuple(circuit_balances),
            "cocircuit_balances": tuple(cocircuit_balances),
            "singleton_degree": singleton_degree,
        }
        return self._data


_STRUCTURE = _StructuralCache()


def _circuit_balances(ch: Chirotope) -> list[int]:
    return _STRUCTURE.get(ch)["circuit_balances"]


def _cocircuit_balances(ch: Chirotope) -> list[int]:
    return _STRUCTURE.get(ch)["cocircuit_balances"]


def _singleton_degree(ch: Chirotope) -> Counter:
    """원소 e 가 '혼자 한쪽'인 circuit 의 개수 (= e 가 나머지의 볼록껍질에 갇힌 횟수)."""
    return _STRUCTURE.get(ch)["singleton_degree"]


def _hist(values) -> tuple:
    """값 리스트 → 정렬된 (값, 개수) 튜플. 원소 이름에 의존하지 않는 형태."""
    return tuple(sorted(Counter(values).items()))


def _install_builtins() -> None:
    B = lambda name, fn, kind, desc, **kw: register(          # noqa: E731
        name, fn, value_kind=kind, description=desc, source="builtin", **kw)

    # ── 라벨 (frozen — om_core 가 유일한 권위) ──
    B(LABEL_NAME, lambda ch: _ORBIT.get(ch)["convex"] == 0, "bool",
      "어떤 재배향으로도 convex position 이 되지 않음 (McMullen 상한 witness). "
      "om_core.is_reorientable_to_convex 와 동치이며 reorientation_cover 와 같은 공식",
      frozen=True, relabel_invariant=True, reorient_invariant=True)

    # ── 크기/기본 파라미터 ──
    B("n", lambda ch: ch.n, "int", "원소 수",
      relabel_invariant=True, reorient_invariant=True)
    B("rank", lambda ch: ch.r, "int", "rank r = d+1",
      relabel_invariant=True, reorient_invariant=True)
    B("corank", lambda ch: ch.n - ch.r, "int",
      "쌍대 rank n−r. n=2d+2 목표점에서는 rank 와 같아진다(자기쌍대 rank)",
      relabel_invariant=True, reorient_invariant=True)

    # ── 재배향 궤도 전체를 보는 양 (이번 확장의 핵심) ──
    B("num_tope_pairs", lambda ch: _ORBIT.get(ch)["topes"], "int",
      "acyclic 이 되는 재배향의 수 (전역반전 몫) = tope 쌍의 수. "
      "실현가능한 경우 '사영변환으로 얻을 수 있는 점배치'의 가짓수",
      relabel_invariant=True, reorient_invariant=True)
    B("num_convex_reorientations", lambda ch: _ORBIT.get(ch)["convex"], "int",
      "convex position 이 되는 재배향의 수 (전역반전 몫). witness ⟺ 이 값이 0",
      relabel_invariant=True, reorient_invariant=True, defines_label=True)
    B("convex_tope_ratio",
      lambda ch: (_ORBIT.get(ch)["convex"] / _ORBIT.get(ch)["topes"]
                  if _ORBIT.get(ch)["topes"] else 0.0), "ratio",
      "convex 재배향 / tope 수 — 0 에 얼마나 가까운지로 '근접 실패'를 잰다",
      relabel_invariant=True, reorient_invariant=True, defines_label=True)
    B("tope_fraction",
      lambda ch: _ORBIT.get(ch)["topes"] / _ORBIT.get(ch)["total"], "ratio",
      "tope 수 / 2^(n−1) — 재배향 중 acyclic 인 비율",
      relabel_invariant=True, reorient_invariant=True)

    # ── 아래는 전부 **이 대표원소(=이 부호배정)에 대한** 양이다.
    #    재배향하면 값이 바뀌므로 reorient_invariant=False 로 선언한다.
    #    (선언이 아니라 실측과 일치하는지는 자체 테스트가 매번 확인한다.)
    REP = dict(relabel_invariant=True, reorient_invariant=False)

    B("acyclic", lambda ch: ch.is_acyclic(), "bool", "양의 회로가 없음", **REP)
    B("totally_cyclic", lambda ch: ch.is_totally_cyclic(), "bool",
      "양의 코회로가 없음 (acyclic 의 쌍대; convex 와 무관)", **REP)
    B("convex_position", lambda ch: ch.is_convex_position(), "bool",
      "모든 Radon 분할이 균형 (= 이 대표원소 자체가 convex)", **REP)

    # ── circuit(Radon 분할) 구조 ──
    B("min_circuit_balance", lambda ch: min(_circuit_balances(ch)), "int",
      "가장 치우친 Radon 분할의 작은 쪽 크기", **REP)
    # max_circuit_balance 는 (6,3) 전 표본 × 전 재배향에서 값이 변하지 않는 것으로
    # 실측됐지만, 그것이 일반 (n,r) 에서도 성립한다는 근거는 없다(작은 케이스의
    # 우연일 수 있음). 그래서 재배향 불변성을 **선언하지 않는다**(None) —
    # 미확인은 conjecture.py 에서 자동으로 하위 등급으로 강등된다.
    B("max_circuit_balance", lambda ch: max(_circuit_balances(ch)), "int",
      "가장 균형잡힌 Radon 분할의 작은 쪽 크기 "
      "(재배향 불변성 미확인 — 작은 n 에서는 상수처럼 보이나 일반 근거 없음)",
      relabel_invariant=True)
    B("num_singleton_circuits",
      lambda ch: sum(1 for b in _circuit_balances(ch) if b == 1), "int",
      "한쪽이 정확히 1인 Radon 분할 수 (= 볼록껍질 내부에 갇힌 사례 수)", **REP)
    B("num_positive_circuits",
      lambda ch: sum(1 for b in _circuit_balances(ch) if b == 0), "int",
      "한쪽이 비어 있는 회로 수 (acyclic ⟺ 이 값이 0)", **REP)
    B("circuit_balance_profile", lambda ch: _hist(_circuit_balances(ch)), "tuple",
      "Radon 분할 균형의 히스토그램 — 원소 이름과 무관한 구조 지문", **REP)

    # ── cocircuit(초평면) 구조 ──
    B("min_cocircuit_balance", lambda ch: min(_cocircuit_balances(ch)), "int",
      "가장 치우친 초평면의 작은 쪽 크기", **REP)
    B("cocircuit_balance_profile", lambda ch: _hist(_cocircuit_balances(ch)), "tuple",
      "초평면 분할 균형 히스토그램 — Gale/쌍대 쪽 구조 지문", **REP)
    B("num_halving_cocircuits",
      lambda ch: sum(1 for b in _cocircuit_balances(ch)
                     if b == (ch.n - ch.r + 1) // 2), "int",
      "양쪽을 가장 고르게 나누는 초평면(halving)의 수", **REP)

    # ── 원소별 구조 (정렬해 원소 이름 비의존으로) ──
    B("num_extreme_elements",
      lambda ch: sum(1 for v in _singleton_degree(ch).values() if v == 0), "int",
      "어떤 Radon 분할에서도 혼자 갇히지 않는 원소 수 (= 이 대표원소의 볼록껍질 꼭짓점 수)",
      **REP)
    B("singleton_degree_profile",
      lambda ch: _hist(_singleton_degree(ch).values()), "tuple",
      "원소별 '혼자 갇힌 횟수'의 히스토그램", **REP)

    # ── 대칭 ──
    B("reorientation_symmetry_order", _reorientation_symmetry_order, "int",
      "χ 를 그대로 두는 순수 재배향의 수 (전역반전 포함 안 함). uniform이고 "
      "1≤r<n이면 항상 항등 하나뿐이라 닫힌 형태로 계산",
      relabel_invariant=True, reorient_invariant=True, cost="cheap")
    B("automorphism_order", _automorphism_order, "int",
      "(Z2)^n⋊S_n 안에서 χ 를 고정하는 부분군의 크기 (n<=6 에서만; 그 외 None). "
      "비용 등급 expensive — 기본 어휘에서 제외, 명시적으로 켜야 함",
      relabel_invariant=True, reorient_invariant=True, cost="expensive")


def _reorientation_symmetry_order(ch: Chirotope):
    """원소 0 고정 gauge에서 χ를 그대로 두는 재배향 수.

    uniform이고 1≤r<n이면 모든 r-부분집합 B에 |F∩B|가 짝수여야 한다. 한 원소만
    바꾼 두 basis를 비교하면 모든 원소의 flip 지시자가 같고, 0을 고정했으므로
    F=∅뿐이다. r=n이면 유일한 basis와 짝수 번 교차하는 flip이 전부 가능하다.
    """
    if 1 <= ch.r < ch.n:
        return 1
    if ch.r == ch.n:
        return 1 if ch.n <= 1 else 1 << (ch.n - 2)
    return None


def _automorphism_order(ch: Chirotope):
    # n! × 2^n 전수 탐색이라 비용이 급격히 는다 (n=7 이면 645k, n=8 이면 10M).
    # 코퍼스 구축에 쓰이므로 실용 상한을 6 으로 둔다 — 그 위에서는 None(미계산)이라
    # 채굴에서 자동 제외되고, 필요하면 개별 대상에 직접 호출하면 된다.
    if ch.n > 6:
        return None
    return automorphism_count(ch)


_install_builtins()


# ═══════════════════════════ 평가 ═══════════════════════════
def evaluate(ch: Chirotope, names: list[str] | None = None,
             *, skip_errors: bool = True) -> dict:
    """chirotope 하나에 대해 활성 불변량 값을 전부 계산.
    값이 None 이면 '이 크기에서는 계산하지 않음'(예: 비용 상한)이라는 뜻이다."""
    names = names if names is not None else active_names()
    out: dict = {}
    for nm in names:
        inv = REGISTRY.get(nm)
        if inv is None or inv.status != "active":
            continue
        try:
            out[nm] = inv.fn(ch)
        except Exception as e:              # noqa: BLE001 — 어휘 오류가 루프를 끊지 않게
            if not skip_errors:
                raise
            out[nm] = None
            inv.description += ""           # 값 없음으로만 기록
            _EVAL_ERRORS.append((nm, repr(e)))
    return out


_EVAL_ERRORS: list[tuple[str, str]] = []


def label(ch: Chirotope) -> bool:
    """유일한 라벨. om_core 와 동치인 궤도 계산으로 판정."""
    return _ORBIT.get(ch)["convex"] == 0


# ═══════════════════════════ vetting (LLM 어휘 심사) ═══════════════════════════
@dataclass
class VetReport:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    relabel_invariant: Optional[bool] = None
    reorient_invariant: Optional[bool] = None
    relabel_samples_passed: int = 0
    reorient_samples_passed: int = 0
    value_kind: str = ""
    distinct_values: int = 0
    max_cost_ms: float = 0.0
    sample_values: list = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


def _classify_kind(values: list) -> str:
    if all(isinstance(v, bool) for v in values):
        return "bool"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        return "int"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return "ratio"
    if all(isinstance(v, tuple) for v in values):
        return "tuple"
    return ""


def vet_invariant(fn: Callable, corpus: list[Chirotope], *,
                  max_cost_ms: float = 400.0,
                  invariance_samples: int = 12,
                  seed: int = 20260809) -> VetReport:
    """새 불변량이 어휘에 들어갈 자격이 있는지 결정론적으로 심사한다.

    검사 항목 (하나라도 실패하면 거부):
      1. 전역성(totality)  — corpus 전체에서 예외 없이 값을 낸다
      2. 결정성            — 같은 입력에 두 번 같은 값
      3. 해시가능/비교가능  — 추측 채굴이 값을 집합·정렬로 다룰 수 있어야 함
      4. 타입 일관성        — bool/int/ratio/tuple 중 하나로 일관
      5. 비상수            — corpus 에서 최소 2개의 값을 가진다 (상수는 정보가 0)
      6. 비용              — 표본당 max_cost_ms 이내

    그리고 **거부하지는 않지만 반드시 기록하는** 분류:
      · relabel_invariant  — 원소 이름 바꾸기에 불변인가 (정리로서 의미가 있는가)
      · reorient_invariant — 재배향에 불변인가 (witness 와 동치가 될 수 있는가)

    ⚠ 이 두 값의 논리적 지위: 표본 검사는 불변성을 **반증**할 수만 있다.
    `False` 는 실제 반례를 찾았다는 뜻이고, 반례가 없으면 `None`(미확인)으로 남긴다.
    통과 표본 수는 별도 필드에 기록한다. 내장 불변량처럼 수학적으로 정당화된 경우만
    레지스트리에 명시적인 `True`를 가질 수 있다.
    """
    rng = random.Random(seed)
    reasons: list[str] = []
    if not corpus:
        return VetReport(False, ["corpus 가 비어 있음 — 심사 불가"])

    values = []
    worst_ms = 0.0
    for ch in corpus:
        t0 = time.perf_counter()
        try:
            v = fn(ch)
        except Exception as e:              # noqa: BLE001
            return VetReport(False, [f"전역성 실패: n={ch.n} 표본에서 예외 {e!r}"])
        dt = (time.perf_counter() - t0) * 1000
        worst_ms = max(worst_ms, dt)
        try:
            hash(v)
        except TypeError:
            return VetReport(False, [f"해시 불가능한 값 {type(v).__name__} 반환"])
        values.append(v)

    if worst_ms > max_cost_ms:
        reasons.append(f"비용 초과: 표본당 최대 {worst_ms:.0f}ms > {max_cost_ms:.0f}ms")

    # 결정성
    for ch, v in zip(corpus[:8], values[:8]):
        if fn(ch) != v:
            return VetReport(False, ["결정성 실패: 같은 입력에 다른 값"])

    kind = _classify_kind(values)
    if not kind:
        reasons.append(f"타입 불일치: {sorted({type(v).__name__ for v in values})}")

    distinct = len({v for v in values})
    if distinct < 2:
        reasons.append(f"상수 불변량 (corpus 전체에서 값이 {values[0]!r} 하나뿐) — 정보 없음")

    # 불변성 실측
    relabel_status: Optional[bool] = None
    relabel_passed = 0
    for ch in corpus[:invariance_samples]:
        perm = list(range(ch.n))
        rng.shuffle(perm)
        try:
            if fn(relabel(ch, tuple(perm))) != fn(ch):
                relabel_status = False
                break
            relabel_passed += 1
        except Exception:                    # noqa: BLE001
            relabel_status = False
            break

    reorient_status: Optional[bool] = None
    reorient_passed = 0
    for ch in corpus[:invariance_samples]:
        flip = {e for e in range(1, ch.n) if rng.random() < 0.5}
        try:
            if fn(ch.reorient(flip)) != fn(ch):
                reorient_status = False
                break
            reorient_passed += 1
        except Exception:                    # noqa: BLE001
            reorient_status = False
            break

    return VetReport(
        ok=not reasons, reasons=reasons,
        relabel_invariant=relabel_status, reorient_invariant=reorient_status,
        relabel_samples_passed=relabel_passed,
        reorient_samples_passed=reorient_passed,
        value_kind=kind, distinct_values=distinct, max_cost_ms=worst_ms,
        sample_values=[v for v in values[:6]])


def register_llm_invariant(name: str, source: str, description: str,
                           corpus: list[Chirotope], *, origin: str = "",
                           persist: bool = True) -> tuple[Optional[Invariant], VetReport]:
    """LLM 이 제안한 불변량을 컴파일 → 심사 → 어휘 등록. 실패하면 (None, 사유)."""
    if name in REGISTRY and REGISTRY[name].frozen:
        return None, VetReport(False, [f"'{name}' 은 frozen 내장 불변량"])
    if not name.isidentifier() or name.startswith("_"):
        return None, VetReport(False, [f"부적절한 이름 '{name}'"])
    try:
        fn = compile_invariant(source)
    except SandboxError as e:
        return None, VetReport(False, [f"샌드박스 거부: {e.reason}"])

    rep = vet_invariant(fn, corpus)
    if not rep.ok:
        return None, rep
    cost = ("expensive" if rep.max_cost_ms > 50 else
            "moderate" if rep.max_cost_ms > 5 else "cheap")
    inv = register(name, fn, value_kind=rep.value_kind, description=description,
                   source="llm", relabel_invariant=rep.relabel_invariant,
                   reorient_invariant=rep.reorient_invariant,
                   origin=origin, sandbox_source=source,
                   max_cost_ms=rep.max_cost_ms, cost=cost)
    if persist:
        _save_llm_invariant(inv)
    return inv, rep


def _save_llm_invariant(inv: Invariant) -> str:
    os.makedirs(VOCAB_DIR, exist_ok=True)
    path = os.path.join(VOCAB_DIR, f"{inv.name}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(inv.meta(), f, ensure_ascii=False, indent=2)
    return path


def load_vocabulary(corpus: list[Chirotope] | None = None,
                    directory: str = VOCAB_DIR, *, revet: bool = True) -> dict:
    """저장된 LLM 어휘를 다시 읽어 등록. corpus 를 주면 재심사(revet)한다.
    재심사를 켜는 이유: 코드가 그대로여도 om_core 가 바뀌면 결과가 달라질 수 있고,
    그때는 조용히 쓰이는 대신 명시적으로 실패해야 한다."""
    out = {"loaded": [], "skipped": [], "deprecated": []}
    if not os.path.isdir(directory):
        out["deprecated"] = apply_status_ledger()
        return out
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".json") or fname.startswith("_"):
            continue
        with open(os.path.join(directory, fname), encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("status") != "active":
            out["skipped"].append((meta.get("name"), "deprecated"))
            continue
        try:
            fn = compile_invariant(meta["sandbox_source"])
        except SandboxError as e:
            out["skipped"].append((meta.get("name"), f"샌드박스 거부: {e.reason}"))
            continue
        if revet and corpus:
            rep = vet_invariant(fn, corpus)
            if not rep.ok:
                out["skipped"].append((meta["name"], "; ".join(rep.reasons)))
                continue
            meta["relabel_invariant"] = rep.relabel_invariant
            meta["reorient_invariant"] = rep.reorient_invariant
            meta["value_kind"] = rep.value_kind
        # 구버전이 표본 통과를 True로 저장했더라도 LLM 메타데이터만으로는 증명이 아니다.
        if meta.get("relabel_invariant") is True:
            meta["relabel_invariant"] = None
        if meta.get("reorient_invariant") is True:
            meta["reorient_invariant"] = None
        try:
            register(meta["name"], fn, value_kind=meta.get("value_kind", "int"),
                     description=meta.get("description", ""), source="llm",
                     relabel_invariant=meta.get("relabel_invariant"),
                     reorient_invariant=meta.get("reorient_invariant"),
                     origin=meta.get("origin", ""),
                     sandbox_source=meta["sandbox_source"],
                     max_cost_ms=meta.get("max_cost_ms"),
                     cost=meta.get("cost", "cheap"))
            out["loaded"].append(meta["name"])
        except VocabularyError as e:
            out["skipped"].append((meta["name"], str(e)))
    out["deprecated"] = apply_status_ledger()
    return out


def vocabulary_summary() -> list[dict]:
    """프롬프트/보고서에 넣기 위한 어휘 목록."""
    rows = []
    for nm in sorted(REGISTRY):
        inv = REGISTRY[nm]
        rows.append({
            "name": nm, "kind": inv.value_kind, "source": inv.source,
            "status": inv.status, "description": inv.description,
            "relabel_invariant": inv.relabel_invariant,
            "reorient_invariant": inv.reorient_invariant,
            "cost": inv.cost,
        })
    return rows


if __name__ == "__main__":
    from console import enable_utf8_stdout
    from om_core import mcmullen_evaluate
    from generator import generate_backtracking

    enable_utf8_stdout()

    # (1) 라벨이 om_core 와 완전히 일치하는가 — 어휘 계층이 판정을 바꾸지 않음을 고정.
    corpus = list(generate_backtracking(6, 3, dedup=False, max_candidates=120,
                                        max_nodes=400_000))
    assert len(corpus) >= 20
    for ch in corpus:
        assert label(ch) == mcmullen_evaluate(ch)["witness"], "라벨이 om_core 와 불일치"
    print(f"라벨 <-> om_core 일치 OK ({len(corpus)}개 표본, (6,3))")

    # (2) tope/convex 재배향 수의 의미 확인
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    assert REGISTRY["num_convex_reorientations"].fn(quad) >= 1     # 이미 convex
    assert REGISTRY["num_convex_reorientations"].fn(tri) >= 1      # 재배향으로 convex 가능
    assert label(quad) is False and label(tri) is False
    # tope 수는 acyclic 재배향 수와 정확히 같아야 한다 (전수 대조)
    for ch in (quad, tri, corpus[0], corpus[1]):
        brute = sum(1 for bits in product((0, 1), repeat=ch.n - 1)
                    if ch.reorient({i + 1 for i, b in enumerate(bits) if b}).is_acyclic())
        assert REGISTRY["num_tope_pairs"].fn(ch) == brute, (brute,)
        brute_cvx = sum(1 for bits in product((0, 1), repeat=ch.n - 1)
                        if ch.reorient({i + 1 for i, b in enumerate(bits) if b})
                        .is_convex_position())
        assert REGISTRY["num_convex_reorientations"].fn(ch) == brute_cvx
    print("num_tope_pairs / num_convex_reorientations 전수 대조 OK")

    # (3) 내장 어휘 전체가 corpus 에서 예외 없이 값을 낸다
    vals = evaluate(corpus[0], skip_errors=False)
    assert LABEL_NAME in vals and len(vals) >= 20
    print(f"내장 어휘 {len(vals)}개 평가 OK")

    # (4) frozen 보호: 라벨은 덮어쓸 수도 폐기할 수도 없다
    for bad in (lambda: register(LABEL_NAME, lambda ch: True),
                lambda: deprecate(LABEL_NAME, "테스트")):
        try:
            bad(); raise AssertionError("frozen 보호가 작동하지 않음")
        except VocabularyError:
            pass
    print("frozen 라벨 보호 OK")

    # (5) LLM 어휘 등록 경로: 좋은 것은 통과, 상수/위반은 거부
    good = ("def f(ch):\n"
            "    trapped = set()\n"
            "    for S in combinations(range(ch.n), ch.r + 1):\n"
            "        C = ch.circuit(S)\n"
            "        pos = [e for e in C if C[e] > 0]\n"
            "        neg = [e for e in C if C[e] < 0]\n"
            "        if len(pos) == 1:\n"
            "            trapped.add(pos[0])\n"
            "        if len(neg) == 1:\n"
            "            trapped.add(neg[0])\n"
            "    return len(trapped)\n")
    inv, rep = register_llm_invariant("num_trapped_elements", good,
                                      "어떤 Radon 분할에서 혼자 갇히는 원소의 수",
                                      corpus[:24], origin="selftest", persist=False)
    assert inv is not None, rep.reasons
    assert rep.value_kind == "int"
    assert rep.relabel_invariant is None and rep.relabel_samples_passed > 0
    assert inv.relabel_invariant is None, "표본 통과가 증명된 불변성으로 승격됨"
    print(f"LLM 어휘 등록 OK — relabel_inv={rep.relabel_invariant} "
          f"reorient_inv={rep.reorient_invariant} 값종류={rep.distinct_values}")

    const_src = "def f(ch):\n    return 7\n"
    inv2, rep2 = register_llm_invariant("always_seven", const_src, "상수",
                                        corpus[:24], persist=False)
    assert inv2 is None and any("상수" in r for r in rep2.reasons)
    inv3, rep3 = register_llm_invariant("evil", "import os\ndef f(ch):\n    return 1\n",
                                        "위반", corpus[:24], persist=False)
    assert inv3 is None and any("샌드박스" in r for r in rep3.reasons)
    print("상수/샌드박스 위반 거부 OK")

    # (6) 내장 불변량의 '선언된' 불변성이 실측과 일치하는가.
    #     여기가 틀리면 conjecture.py 가 대표원소 의존 성질을 궤도 불변으로 오인해
    #     'witness 의 특징짓기'로 잘못 승격시킨다 — 가장 위험한 거짓 결론이므로
    #     선언만 믿지 않고 매번 표본으로 검증한다.
    #     실측의 논리적 지위에 주의: 표본 검사는 불변성을 **반증**할 수만 있고
    #     **확증**할 수는 없다. 따라서 실패로 볼 것은 '선언=True 인데 반례 발견'
    #     한 방향뿐이다. 반대 방향(선언=False 인데 표본에서 안 변함)은 표본이
    #     약하다는 뜻일 뿐이라 경고만 남긴다.
    sample = corpus[:16]
    contradictions, weak = [], []
    for nm in sorted(REGISTRY):
        inv = REGISTRY[nm]
        if inv.fn is None or inv.fn(sample[0]) is None:
            continue
        got = vet_invariant(inv.fn, sample, invariance_samples=8)
        for attr, measured in (("relabel_invariant", got.relabel_invariant),
                               ("reorient_invariant", got.reorient_invariant)):
            declared = getattr(inv, attr)
            if declared is True and measured is False:
                contradictions.append((nm, f"{attr}: 선언=True 인데 반례 발견"))
            elif declared is False and measured is True:
                weak.append(f"{nm}.{attr}")
    assert not contradictions, f"선언/실측 모순: {contradictions}"
    assert REGISTRY["acyclic"].reorient_invariant is False
    assert REGISTRY[LABEL_NAME].reorient_invariant is True
    assert REGISTRY["max_circuit_balance"].reorient_invariant is None   # 미확인 유지
    print(f"내장 불변량 선언 <-> 실측 무모순 OK ({len(REGISTRY)}개 검사"
          + (f", 표본이 약해 미확인인 것 {len(weak)}개" if weak else "") + ")")

    print("invariants core-contract assertions OK")
