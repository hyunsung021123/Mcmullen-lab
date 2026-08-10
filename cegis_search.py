"""
cegis_search.py — WP3: GP outer solver + exact CEGIS 루프 (#40).

Epic #37 / docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §12. (source: chatgpt, relayed by user)

## 목표

    ∃χ [ GP(χ) ∧ ∀ρ ¬Convex(χ^ρ) ]

를 거대한 QBF 로 직접 풀지 않고 CEGIS(Counter-Example Guided Inductive Synthesis)로
분해한다:

    outer(GP solver)가 χ 제안
    inner(reorientation_sat, WP2)가 convex 재배향 ρ 탐색
      SAT   → ρ 는 정확한 반례 (WP2 가 om_core replay 를 이미 강제).
              outer 에 "다음 χ 는 ρ 아래 unbalanced circuit 을 가져야 함" cut 추가:
                  ∨_S [ min(|C⁺_{χ^ρ,S}|, |C⁻_{χ^ρ,S}|) ≤ 1 ]
              — 모델 하나 블로킹이 아니라 그 재배향을 차단하는 **일반 제약 학습**.
      UNSAT → candidate witness. legacy(om_core.is_reorientable_to_convex) replay →
              certificate v1 생성 → 독립 검증 통과 후에만 CERTIFIED 반환.

## 신뢰 규율

- 모든 learned cut 은 independent code 로 replay 된다: cut 추가 직후, 그 cut 이
  "방금 그 χ 를 실제로 배제하는지"와 "이미 알려진 witness 를 배제하지 않는지"를
  om_core 직접 계산으로 확인한다 (`_replay_cut`).
- outer 모델은 반드시 `chi.is_valid()`(om_core) 를 통과해야 하며, 실패하면 그
  모델만 블로킹하고 계속한다 (인코딩 불신 원칙 — pseudocode 그대로).
- inner UNKNOWN(타임아웃)은 witness 로 승격하지 않고 그 모델을 블로킹 후 계속한다.
- 반환되는 witness 는 legacy replay + certificate 독립 replay 를 모두 통과한
  CERTIFIED 등급뿐이다.

z3 는 선택적 의존성 (미설치 시 자체 테스트 SKIP).
"""
from __future__ import annotations
import sys
import time
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

from om_core import Chirotope
from reorientation_sat import find_convex_reorientation_sat
from reorientation_cover import flip_set_from_index  # cut replay 보조 (독립성 제약 없음)

try:
    import z3
except ImportError:
    z3 = None


@dataclass(frozen=True)
class CegisOutcome:
    # "CERTIFIED_WITNESS" | "EXHAUSTED"(unknown 0건일 때만 — 무-witness 증명)
    # | "INCONCLUSIVE_WITH_UNKNOWN"(타임아웃 후보가 있어 완전성 주장 불가)
    # | "BUDGET_EXCEEDED"
    status: str
    chirotope: Optional[Chirotope]
    certificate: Optional[dict]
    stats: dict = field(default_factory=dict)


# ─────────────────────────── outer: GP solver ───────────────────────────
class GPOuterSolver:
    """GP-적법 uniform chirotope 공간 위의 z3 solver + cut 관리.

    부호 변수 x_B ∈ {1,-1} (첫 r-부분집합은 +1 고정 — generator 와 동일한 전역 부호 몫).
    GP 제약은 om_core.is_valid 와 같은 금지 패턴 (s1==s3 ∧ s2==-s1) 차단."""

    def __init__(self, n: int, r: int):
        if z3 is None:
            raise RuntimeError("z3-solver 미설치")
        self.n, self.r = n, r
        self.subs = sorted(combinations(range(n), r))
        self.x = {s: z3.Int(f"x_{'_'.join(map(str, s))}") for s in self.subs}
        self.solver = z3.Solver()
        for s in self.subs:
            self.solver.add(z3.Or(self.x[s] == 1, self.x[s] == -1))
        self.solver.add(self.x[self.subs[0]] == 1)

        E = range(n)
        for Y in combinations(E, r - 2):
            rest = [e for e in E if e not in Y]
            for a, b, c, d in combinations(rest, 4):
                s1 = self._chi_expr(Y + (a, b)) * self._chi_expr(Y + (c, d))
                s2 = self._chi_expr(Y + (a, c)) * self._chi_expr(Y + (b, d))
                s3 = self._chi_expr(Y + (a, d)) * self._chi_expr(Y + (b, c))
                self.solver.add(z3.Not(z3.And(s1 == s3, s2 == -s1)))

    def _chi_expr(self, t):
        arr = list(t); swaps = 0; m = len(arr)
        for i in range(m):
            for j in range(m - 1 - i):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]; swaps += 1
        e = self.x[tuple(arr)]
        return e if swaps % 2 == 0 else -e

    def next_candidate(self) -> Optional[Chirotope]:
        if self.solver.check() != z3.sat:
            return None
        m = self.solver.model()
        signs = {s: (1 if m.evaluate(self.x[s]).as_long() == 1 else -1)
                 for s in self.subs}
        return Chirotope(self.n, self.r, signs)

    def block_exact_candidate(self, ch: Chirotope):
        self.solver.add(z3.Or([self.x[s] != ch.signs[s] for s in self.subs]))

    def add_reorientation_obstruction_cut(self, flip: frozenset):
        r"""재배향 ρ(=flip 집합)를 차단하는 일반 cut:
        ∨_S [ npos_S(x, ρ) ≤ 1 ∨ npos_S(x, ρ) ≥ |S|-1 ].

        S 가 정렬돼 있으면 S\{s_i} 도 정렬돼 있으므로 χ(S\{s_i}) = x[S\{s_i}] 그대로이고,
        재배향 후 상대 부호는 (-1)^i · x[B_i] · ρ_{s_i} (WP1 에서 검증된 공식)."""
        disj = []
        for S in combinations(range(self.n), self.r + 1):
            pos_flags = []
            for i, s in enumerate(S):
                B = S[:i] + S[i + 1:]
                coeff = (-1) ** i * (-1 if s in flip else 1)
                pos_flags.append(z3.If(self.x[B] == coeff, 1, 0))
            npos = z3.Sum(pos_flags)
            k = len(S)
            disj.append(z3.Or(npos <= 1, npos >= k - 1))
        self.solver.add(z3.Or(disj))


def _unbalanced_under(ch: Chirotope, flip: frozenset) -> bool:
    """cut replay 용 독립 계산: χ 가 재배향 flip 아래 unbalanced circuit 을 갖는가.
    (= cut 이 참인가) — om_core 의 reorient/circuit 를 직접 사용한다."""
    rch = ch.reorient(flip)
    for S in combinations(range(ch.n), ch.r + 1):
        C = rch.circuit(S)
        pos = sum(1 for v in C.values() if v > 0)
        if min(pos, len(C) - pos) <= 1:
            return True
    return False


# ─────────────────────────── CEGIS 루프 ───────────────────────────
def cegis_find_witness(n: int, r: int, *,
                       max_outer_models: int = 100_000,
                       inner_timeout_ms: Optional[int] = None,
                       known_witnesses: list | None = None,
                       _blocked: list | None = None) -> CegisOutcome:
    """CEGIS 로 (n,r) witness 하나를 찾아 CERTIFIED 등급으로 반환.

    known_witnesses: learned cut replay 시 '이 witness 들을 배제하지 않는지' 확인용.
    _blocked: (열거 모드용) 시작 전에 정확 블로킹할 chirotope 들."""
    from certificate import build_certificate
    from certificate_verify import verify_certificate

    outer = GPOuterSolver(n, r)
    for ch in (_blocked or []):
        outer.block_exact_candidate(ch)

    stats = {"outer_models": 0, "cuts": 0, "inner_sat": 0, "inner_unsat": 0,
             "inner_unknown": 0, "invalid_models": 0}
    t0 = time.perf_counter()

    while stats["outer_models"] < max_outer_models:
        chi = outer.next_candidate()
        if chi is None:
            stats["wall_s"] = time.perf_counter() - t0
            # UNKNOWN(타임아웃) 후보를 블로킹한 적이 있으면 "witness 없음"을 주장할 수
            # 없다 — 그 후보가 실제 witness 였을 수 있다 (0023). EXHAUSTED 는
            # inner_unknown == 0 일 때만.
            if stats["inner_unknown"] > 0:
                return CegisOutcome("INCONCLUSIVE_WITH_UNKNOWN", None, None, stats)
            return CegisOutcome("EXHAUSTED", None, None, stats)
        stats["outer_models"] += 1

        # 인코딩 불신: outer 가 내놓은 모델도 om_core 로 재검증
        if not chi.is_valid():
            stats["invalid_models"] += 1
            outer.block_exact_candidate(chi)
            continue

        inner = find_convex_reorientation_sat(chi, timeout_ms=inner_timeout_ms)

        if inner.status == "SAT":
            stats["inner_sat"] += 1
            rho = inner.flip_set                     # WP2 가 om_core replay 를 이미 강제
            outer.add_reorientation_obstruction_cut(rho)
            stats["cuts"] += 1
            # learned cut replay (독립 계산):
            #  (a) 방금 그 χ 는 ρ 아래 균형 → cut 이 χ 를 실제로 배제해야 한다.
            assert not _unbalanced_under(chi, rho), \
                "cut replay 실패(a): 반례 재배향이 실제로는 unbalanced"
            #  (b) 알려진 witness 는 모든 재배향에서 unbalanced → cut 을 만족해야 한다.
            for w in (known_witnesses or []):
                if w.n == n and w.r == r:
                    assert _unbalanced_under(w, rho), \
                        "cut replay 실패(b): learned cut 이 알려진 witness 를 배제"
            continue

        if inner.status == "UNSAT":
            stats["inner_unsat"] += 1
            # legacy replay — solver 를 진실 판정자로 쓰지 않는다
            reorientable, _ = chi.is_reorientable_to_convex()
            if reorientable:
                raise AssertionError("inner UNSAT 인데 legacy 는 재배향 가능 — 인코딩 버그")
            cert = build_certificate(chi, generator="cegis",
                                     config={"n": n, "r": r})
            verify_certificate(cert)                 # 독립 replay (실패 시 예외)
            stats["wall_s"] = time.perf_counter() - t0
            return CegisOutcome("CERTIFIED_WITNESS", chi, cert, stats)

        # UNKNOWN: witness 로 승격 금지 — 그 모델만 블로킹하고 계속
        stats["inner_unknown"] += 1
        outer.block_exact_candidate(chi)

    stats["wall_s"] = time.perf_counter() - t0
    return CegisOutcome("BUDGET_EXCEEDED", None, None, stats)


def cegis_enumerate_witnesses(n: int, r: int, *,
                              max_witnesses: int = 10 ** 9,
                              inner_timeout_ms: Optional[int] = None,
                              certify_each: bool = True,
                              cut_replay_sample: int = 50):
    """(n,r) 의 witness 들을 하나씩 방출 (recall 검증용 열거 모드).

    outer solver 를 하나만 유지한 채 witness 를 찾을 때마다 정확 블로킹하고 계속
    (매번 solver 를 재생성하면 O(k^2) 라 대규모 recall 검증이 비현실적).
    certify_each=False 면 legacy replay 까지만 하고 certificate 생성은 생략
    (수천 개 전수 recall 측정용 — witness 판정 자체는 여전히 legacy 가 확정).
    learned cut replay 는 앞 cut_replay_sample 개 cut 에 대해서만 수행한다."""
    from certificate import build_certificate
    from certificate_verify import verify_certificate

    outer = GPOuterSolver(n, r)
    found: list[Chirotope] = []
    n_cuts = 0
    n_unknown = 0
    while len(found) < max_witnesses:
        chi = outer.next_candidate()
        if chi is None:
            # UNKNOWN 후보를 버린 적이 있으면 열거가 완전하다고 주장할 수 없다 —
            # 종료 전에 INCONCLUSIVE 신호를 방출한다 (recall 주장하는 소비자는
            # 이 신호를 반드시 확인해야 함).
            if n_unknown > 0:
                yield CegisOutcome("INCONCLUSIVE_WITH_UNKNOWN", None, None,
                                   {"inner_unknown": n_unknown, "found": len(found)})
            return
        if not chi.is_valid():
            outer.block_exact_candidate(chi)
            continue
        inner = find_convex_reorientation_sat(chi, timeout_ms=inner_timeout_ms)
        if inner.status == "SAT":
            rho = inner.flip_set
            outer.add_reorientation_obstruction_cut(rho)
            n_cuts += 1
            if n_cuts <= cut_replay_sample:
                assert not _unbalanced_under(chi, rho)
                for w in found[:20]:
                    assert _unbalanced_under(w, rho)
            continue
        if inner.status == "UNSAT":
            reorientable, _ = chi.is_reorientable_to_convex()
            if reorientable:
                raise AssertionError("inner UNSAT 인데 legacy 는 재배향 가능 — 인코딩 버그")
            cert = None
            if certify_each:
                cert = build_certificate(chi, generator="cegis-enumerate",
                                         config={"n": n, "r": r})
                verify_certificate(cert)
            found.append(chi)
            outer.block_exact_candidate(chi)
            yield CegisOutcome("CERTIFIED_WITNESS" if certify_each else "VERIFIED_WITNESS",
                               chi, cert, {"cuts": n_cuts, "found": len(found)})
            continue
        outer.block_exact_candidate(chi)            # UNKNOWN: 비승격
        n_unknown += 1


def cegis_enumerate_witness_orbits(n: int, r: int, *,
                                   inner_timeout_ms: Optional[int] = None,
                                   certify_each: bool = True):
    """WP4(#41) orbit-aware 열거: witness 를 찾을 때마다 그 (Z₂)^(n-1)⋊S_n orbit 의
    게이지 고정 이미지 **전부**를 outer 에서 블로킹하고 계속한다.

    labeled 열거(cegis_enumerate_witnesses)가 orbit 크기만큼 반복하던 것을 orbit 당
    1회로 줄인다. 방출: CegisOutcome (stats 에 orbit_size 포함). recall 보존은
    Σ orbit_size 가 labeled 전수 개수와 일치하는지로 검증한다 (자체 테스트)."""
    from certificate import build_certificate
    from certificate_verify import verify_certificate
    from symmetry_reduction import orbit_images

    outer = GPOuterSolver(n, r)
    n_cuts = 0
    n_unknown = 0
    while True:
        chi = outer.next_candidate()
        if chi is None:
            if n_unknown > 0:
                yield CegisOutcome("INCONCLUSIVE_WITH_UNKNOWN", None, None,
                                   {"inner_unknown": n_unknown})
            return
        if not chi.is_valid():
            outer.block_exact_candidate(chi)
            continue
        inner = find_convex_reorientation_sat(chi, timeout_ms=inner_timeout_ms)
        if inner.status == "SAT":
            outer.add_reorientation_obstruction_cut(inner.flip_set)
            n_cuts += 1
            assert not _unbalanced_under(chi, inner.flip_set)
            continue
        if inner.status == "UNSAT":
            reorientable, _ = chi.is_reorientable_to_convex()
            if reorientable:
                raise AssertionError("inner UNSAT 인데 legacy 는 재배향 가능 — 인코딩 버그")
            cert = None
            if certify_each:
                cert = build_certificate(chi, generator="cegis-orbit-enumerate",
                                         config={"n": n, "r": r})
                verify_certificate(cert)
            images = orbit_images(chi)               # 게이지 고정 orbit 전체
            for signs in images:
                outer.solver.add(z3.Or([outer.x[s] != v for s, v in signs.items()]))
            yield CegisOutcome(
                "CERTIFIED_WITNESS" if certify_each else "VERIFIED_WITNESS",
                chi, cert, {"cuts": n_cuts, "orbit_size": len(images)})
            continue
        outer.block_exact_candidate(chi)            # UNKNOWN: 비승격
        n_unknown += 1


# ─────────────────────────── naive 기준선 ───────────────────────────
def naive_z3_find_witness(n: int, r: int, *, max_models: int = 100_000) -> dict:
    """비교 기준선: GP-적법 모델을 하나씩 열거하며 legacy 로 witness 판정
    (cut 학습 없음 — 현재 generate_z3 + 사후 판정 구조와 동일한 방식)."""
    outer = GPOuterSolver(n, r)
    models = 0
    t0 = time.perf_counter()
    while models < max_models:
        chi = outer.next_candidate()
        if chi is None:
            return {"status": "EXHAUSTED", "models": models,
                    "wall_s": time.perf_counter() - t0}
        models += 1
        if not chi.is_reorientable_to_convex()[0]:
            return {"status": "WITNESS", "models": models, "chirotope": chi,
                    "wall_s": time.perf_counter() - t0}
        outer.block_exact_candidate(chi)
    return {"status": "BUDGET_EXCEEDED", "models": models,
            "wall_s": time.perf_counter() - t0}


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    if z3 is None:
        print("SKIP: z3-solver 미설치 — CEGIS 자체 테스트를 건너뜀")
        sys.exit(0)

    # (1) witness 가 없는 (5,3): CEGIS 는 EXHAUSTED 로 끝나야 하고(무-witness 증명),
    #     naive 는 GP-적법 192개 전부를 열거해야 한다 → cut 의 모델 감소 효과 측정.
    out = cegis_find_witness(5, 3)
    nv = naive_z3_find_witness(5, 3)
    assert out.status == "EXHAUSTED" and nv["status"] == "EXHAUSTED"
    assert nv["models"] == 192                     # WP0 전수 교차검증과 일치해야 함
    ratio = nv["models"] / max(1, out.stats["outer_models"])
    print(f"(5,3) 무-witness: naive {nv['models']} 모델 vs CEGIS "
          f"{out.stats['outer_models']} 모델 (cut {out.stats['cuts']}개, {ratio:.1f}x 감소)")

    # (2) rank-2 (4,2): 전부 witness (24개, WP0 실측) — 열거 recall 100%
    wits = list(cegis_enumerate_witnesses(4, 2))
    assert len(wits) == 24, f"recall 실패: {len(wits)} != 24"
    assert all(w.status == "CERTIFIED_WITNESS" for w in wits)
    print(f"(4,2) 열거 recall OK: witness {len(wits)}/24 전부 CERTIFIED")

    # (3) (6,3) 첫 witness: CERTIFIED 등급으로 찾아져야 한다
    out63 = cegis_find_witness(6, 3)
    assert out63.status == "CERTIFIED_WITNESS"
    assert out63.certificate is not None
    ev_n = out63.chirotope.n
    print(f"(6,3) 첫 witness CERTIFIED OK (outer {out63.stats['outer_models']} 모델, "
          f"cut {out63.stats['cuts']}개) → nu_OM(2) <= {ev_n - 1}")

    # (4) WP4 orbit-aware 열거: (4,2) 의 labeled witness 24개(WP0 실측)가
    #     orbit 단위 열거에서도 Σ orbit_size 로 정확히 보존되는지 (recall 보존).
    orbits = list(cegis_enumerate_witness_orbits(4, 2))
    assert sum(o.stats["orbit_size"] for o in orbits) == 24
    assert all(o.status == "CERTIFIED_WITNESS" for o in orbits)
    print(f"(4,2) orbit-aware 열거 OK: orbit {len(orbits)}개, Σ orbit_size = 24 (recall 보존)")

    print("cegis_search core-contract assertions OK "
          "(cut replay 강제 / legacy+certificate 이중 replay / UNKNOWN 비승격)")
