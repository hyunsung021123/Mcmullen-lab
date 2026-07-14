"""
discovery.py — Discovery Engine (결정론적 패턴 발견). 리뷰 지적 ⑤ 반영.

검증된 witness 들(그리고 채택됐지만 witness 가 아닌 것들)에 대해 구조적 불변량을 계산하고,
  · witness 들이 공통으로 갖는 성질(common)
  · witness 를 non-witness 와 구별하는 성질(distinguishing)
을 자동으로 찾는다. 발견이 REGISTRY 기준으로 표현되면 '제안 편향'으로 내보내며,
이 제안은 이후 검증 게이트 + 반례 사냥을 통과해야만 실제 탐색에 반영된다.

핵심: 여기서 나오는 '발견'은 검증된 OM 들에 대한 사실(fact)이지 LLM 의 주장이 아니다.
"""
from __future__ import annotations
from collections import Counter
from itertools import combinations, product
from dataclasses import dataclass, field
from typing import Optional

from om_core import Chirotope


# ───────────────────────────── 불변량 ─────────────────────────────
def _circuit_balance_hist(ch: Chirotope) -> Counter:
    c = Counter()
    for S in combinations(range(ch.n), ch.r + 1):
        C = ch.circuit(S); pos = sum(1 for v in C.values() if v > 0)
        c[min(pos, len(C) - pos)] += 1
    return c


def _cocircuit_balance_hist(ch: Chirotope) -> Counter:
    c = Counter()
    for H in combinations(range(ch.n), ch.r - 1):
        D = ch.cocircuit(H); pos = sum(1 for v in D.values() if v > 0)
        c[min(pos, len(D) - pos)] += 1
    return c


def _symmetry_order(ch: Chirotope, cap_n: int = 11) -> Optional[int]:
    if ch.n > cap_n:
        return None                      # 2^(n-1) 폭발 방지
    subs = sorted(ch.signs); base = tuple(ch.signs[s] for s in subs)
    others = list(range(1, ch.n)); cnt = 0
    for bits in product((0, 1), repeat=len(others)):
        flip = {others[i] for i, b in enumerate(bits) if b}
        if tuple(ch.reorient(flip).signs[s] for s in subs) == base:
            cnt += 1
    return cnt


def invariants(ch: Chirotope) -> dict:
    cb = _circuit_balance_hist(ch)
    sym = _symmetry_order(ch)
    return {
        "acyclic": ch.is_acyclic(),
        "totally_cyclic": ch.is_totally_cyclic(),
        "min_circuit_balance": min(cb),                 # 가장 치우친 Radon 분할
        "has_balanced_circuit": int(max(cb) >= 2) if cb else 0,
        "symmetry_order": sym,
    }


@dataclass
class Finding:
    invariant: str
    value: object
    kind: str                 # "common" | "distinguishing"
    support: str              # "k/n"
    suggested_bias: Optional[dict] = None
    note: str = ""
    # provenance (#50): 이 finding 을 지지한 witness 표본의 ResultRecord id 들.
    # id 를 모르는 호출 경로에서는 빈 리스트 (하위호환).
    supporting_ids: list = field(default_factory=list)

    def as_dict(self):
        return {"invariant": self.invariant, "value": self.value, "kind": self.kind,
                "support": self.support, "suggested_bias": self.suggested_bias,
                "note": self.note, "supporting_ids": list(self.supporting_ids)}


# invariant → REGISTRY 기준 매핑(가능한 것만; 나머지는 관찰만)
def _suggest_bias(inv: str, value) -> Optional[dict]:
    if inv == "symmetry_order" and isinstance(value, int) and value >= 2:
        return {"type": "require_property",
                "spec": {"name": "min_symmetry_order", "args": [value]}}
    if inv == "totally_cyclic":
        mode = "require_property" if value else "forbid_property"
        return {"type": mode, "spec": {"name": "totally_cyclic"}}
    if inv == "acyclic" and value:
        return {"type": "require_property", "spec": {"name": "acyclic"}}
    return None


class DiscoveryEngine:
    def __init__(self, min_support: float = 0.8, min_samples: int = 3):
        self.min_support = min_support
        self.min_samples = min_samples

    def analyze(self, witnesses: list[Chirotope],
                nonwitnesses: list[Chirotope] | None = None,
                witness_ids: list | None = None) -> list[Finding]:
        """witness_ids (#50): witnesses[i] 의 provenance id (ResultRecord.id 등).
        주어지면 각 finding 에 '그 값을 실제로 만족한 표본들의 id'가 기록된다 —
        나중에 finding 이 틀렸거나 표본이 편향됐을 때 역추적 가능."""
        findings: list[Finding] = []
        if len(witnesses) < self.min_samples:
            return findings
        if witness_ids is not None and len(witness_ids) != len(witnesses):
            raise ValueError("witness_ids 길이가 witnesses 와 다름")
        w_inv = [invariants(ch) for ch in witnesses]
        nw_inv = [invariants(ch) for ch in (nonwitnesses or [])]
        keys = ["acyclic", "totally_cyclic", "min_circuit_balance",
                "has_balanced_circuit", "symmetry_order"]
        for k in keys:
            w_vals = [d[k] for d in w_inv if d[k] is not None]
            if len(w_vals) < self.min_samples:
                continue
            common = Counter(w_vals).most_common(1)[0]
            val, cnt = common
            frac = cnt / len(w_vals)
            if frac < self.min_support:
                continue
            # non-witness 에서 같은 값의 비율
            nw_vals = [d[k] for d in nw_inv if d[k] is not None]
            nw_frac = (sum(1 for v in nw_vals if v == val) / len(nw_vals)
                       if nw_vals else None)
            kind = "common"
            note = ""
            if nw_frac is not None and nw_frac <= 0.4:
                kind = "distinguishing"
                note = f"non-witness 에선 {nw_frac:.0%} 만 해당 → 구별 특징"
            sup_ids = ([witness_ids[i] for i, dv in enumerate(w_inv)
                        if dv[k] == val] if witness_ids is not None else [])
            findings.append(Finding(
                invariant=k, value=val, kind=kind,
                support=f"{cnt}/{len(w_vals)}",
                suggested_bias=_suggest_bias(k, val), note=note,
                supporting_ids=sup_ids))
        return findings


if __name__ == "__main__":
    import random
    from om_core import mcmullen_evaluate
    random.seed(1)
    wits, nonwits = [], []
    while len(wits) < 6 or len(nonwits) < 6:
        pts = [tuple(random.randint(-9, 9) for _ in range(3)) for _ in range(8)]
        try:
            ch = Chirotope.from_points(pts)
        except ValueError:
            continue
        (wits if mcmullen_evaluate(ch)["witness"] else nonwits).append(ch)
    ids = [f"w{i}" for i in range(6)]
    findings = DiscoveryEngine().analyze(wits[:6], nonwits[:6], witness_ids=ids)
    # provenance (#50): 각 finding 의 supporting_ids 는 실제로 그 값을 만족한
    # 표본들의 id 여야 하고, as_dict 왕복에도 포함돼야 한다.
    from discovery import invariants as _inv
    for f in findings:
        expect = [ids[i] for i, ch in enumerate(wits[:6])
                  if _inv(ch)[f.invariant] == f.value]
        assert f.supporting_ids == expect, (f.invariant, f.supporting_ids, expect)
        assert f.as_dict()["supporting_ids"] == expect
    legacy = DiscoveryEngine().analyze(wits[:6], nonwits[:6])   # id 없는 하위호환 경로
    assert all(f.supporting_ids == [] for f in legacy)
    print("provenance(supporting_ids) assertion OK (#50) + 하위호환 빈 리스트 OK")
    print(f"witness {len(wits)}개 / non {len(nonwits)}개 분석 → 발견 {len(findings)}개")
    for f in findings:
        print(f"  [{f.kind:13}] {f.invariant}={f.value} ({f.support}) "
              f"bias={f.suggested_bias} {f.note}")
