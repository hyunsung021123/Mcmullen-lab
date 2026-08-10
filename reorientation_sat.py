"""
reorientation_sat.py — WP2: 고정 chirotope 의 convex-reorientation SAT 검증기 (#39).

Epic #37 / docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §11. (source: chatgpt, relayed by user)

## 인코딩

고정된 uniform chirotope χ 에 대해 재배향 Bool 변수 z_1..z_{n-1} 을 둔다 (원소 0 은
전역 부호 몫 고정 — reorientation_cover 와 동일한 convention). 재배향 후 circuit 의
상대 부호는 원래 부호 × 원소별 ρ 이므로 (WP1 에서 검증된 공식), support S 의 원소 s 가
재배향 후 양(+)이 될 조건은:

    base[s] = +1  →  ¬z_s        base[s] = -1  →  z_s        (z_0 ≡ False)

convexity 는 모든 circuit 이 균형(min(pos,neg) ≥ 2)일 조건이므로:

    Convex(χ^z)  ⟺  ∧_S ( 2 ≤ N_S^+(z) ≤ |S|-2 )

- SAT   → model 이 실제 convex 재배향. **반드시 om_core 로 replay 후에만 반환**
          (replay 실패는 인코딩 버그이므로 예외).
- UNSAT → candidate witness. 상태는 `VERIFIED_BY_SOLVER` 일 뿐이며, certificate v1
          독립 replay 를 통과해야 `CERTIFIED` 다 (solver 를 진실 판정자로 쓰지 않는다).
- 타임아웃/불능 → `UNKNOWN` 으로 구분한다 (UNSAT 과 절대 혼동하지 않는다).

## 신뢰 경계

이 모듈은 om_core 를 대체하지 않는다. z3 는 무거운 선택적 의존성이므로 try/except 로
감싸며, 미설치 시 자체 테스트는 SKIP 으로 안전 종료한다 (코어 검증기는 여전히 표준
라이브러리만으로 동작).
"""
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

from om_core import Chirotope

try:
    import z3
except ImportError:
    z3 = None

# trust label (docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §6)
TRUST_SAT_REPLAYED = "VERIFIED"            # SAT model 을 om_core 로 replay 완료
TRUST_UNSAT_SOLVER = "VERIFIED_BY_SOLVER"  # UNSAT — certificate 통과 전까지는 이 등급
TRUST_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SatResult:
    status: str                        # "SAT" | "UNSAT" | "UNKNOWN"
    is_witness: Optional[bool]         # SAT→False, UNSAT→True, UNKNOWN→None
    flip_set: Optional[frozenset]      # SAT 일 때 convex 재배향 (replay 통과분)
    trust: str
    stats: dict = field(default_factory=dict)


def status_from_z3(check_result) -> str:
    """z3 CheckSatResult → 이 모듈의 status 문자열. 타임아웃(unknown)은 UNKNOWN —
    UNSAT 으로 절대 승격하지 않는다."""
    if z3 is None:
        raise RuntimeError("z3 미설치")
    if check_result == z3.sat:
        return "SAT"
    if check_result == z3.unsat:
        return "UNSAT"
    return "UNKNOWN"


def build_convexity_solver(ch: Chirotope):
    """χ 고정 convexity 인코딩을 담은 z3 Solver 와 변수 dict 를 반환."""
    if z3 is None:
        raise RuntimeError("z3-solver 미설치. pip install z3-solver 후 사용.")
    zvar = {e: z3.Bool(f"z_{e}") for e in range(1, ch.n)}
    solver = z3.Solver()
    n_constraints = 0
    for S in combinations(range(ch.n), ch.r + 1):
        base = ch.circuit(S)
        pos_lits = []
        for s in S:
            if s == 0:
                # z_0 ≡ False: base 부호 그대로
                pos_lits.append(z3.BoolVal(base[s] > 0))
            elif base[s] > 0:
                pos_lits.append(z3.Not(zvar[s]))
            else:
                pos_lits.append(zvar[s])
        npos = z3.Sum([z3.If(b, 1, 0) for b in pos_lits])
        solver.add(npos >= 2, npos <= len(S) - 2)
        n_constraints += 1
    return solver, zvar, n_constraints


def find_convex_reorientation_sat(ch: Chirotope, *,
                                  timeout_ms: Optional[int] = None) -> SatResult:
    """χ 에 convex 재배향이 존재하는지 SAT 로 판정.

    반환된 SAT 결과의 flip_set 은 이미 om_core 로 replay 검증된 것이다."""
    solver, zvar, n_constraints = build_convexity_solver(ch)
    if timeout_ms is not None:
        solver.set("timeout", int(timeout_ms))
    res = solver.check()
    status = status_from_z3(res)
    stats = {"n": ch.n, "r": ch.r, "constraints": n_constraints,
             "timeout_ms": timeout_ms}

    if status == "SAT":
        m = solver.model()
        flip = frozenset(e for e, v in zvar.items() if z3.is_true(m[v]))
        # 필수 replay: solver 를 신뢰하지 않는다. 실패는 인코딩 버그 → 예외.
        if not ch.reorient(flip).is_convex_position():
            raise AssertionError(
                f"SAT model replay 실패 (인코딩 버그): flip={sorted(flip)}")
        return SatResult("SAT", False, flip, TRUST_SAT_REPLAYED, stats)
    if status == "UNSAT":
        return SatResult("UNSAT", True, None, TRUST_UNSAT_SOLVER, stats)
    return SatResult("UNKNOWN", None, None, TRUST_UNKNOWN, stats)


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    if z3 is None:
        print("SKIP: z3-solver 미설치 — SAT verifier 자체 테스트를 건너뜀 "
              "(pip install z3-solver 또는 pip install -e '.[z3]')")
        sys.exit(0)

    import time
    from generator import generate_backtracking
    from certificate import build_certificate
    from certificate_verify import verify_certificate

    # (0) status 매핑 단위 테스트 — 타임아웃(unknown)을 UNSAT 으로 혼동하지 않는지
    assert status_from_z3(z3.sat) == "SAT"
    assert status_from_z3(z3.unsat) == "UNSAT"
    assert status_from_z3(z3.unknown) == "UNKNOWN"
    print("status 매핑 OK (unknown → UNKNOWN, UNSAT 아님)")

    # (1) 알려진 non-witness: convex 사각형 / 삼각형+내부점 → SAT + replay
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    for ch in (quad, tri, Chirotope.alternating(8, 4)):
        res = find_convex_reorientation_sat(ch)
        assert res.status == "SAT" and res.is_witness is False
        assert res.trust == TRUST_SAT_REPLAYED       # replay 는 함수 안에서 이미 강제됨
    print("non-witness → SAT + model replay OK")

    # (2) rank-2 특이 사례: 정의상 witness → UNSAT (등급은 VERIFIED_BY_SOLVER 까지만)
    r2 = Chirotope.from_vectors([(1, 0), (0, 1), (-1, -2), (-2, -1)])
    res = find_convex_reorientation_sat(r2)
    assert res.status == "UNSAT" and res.is_witness is True
    assert res.trust == TRUST_UNSAT_SOLVER
    print("rank-2 특이 사례 → UNSAT (VERIFIED_BY_SOLVER) OK")

    # (3) tiny exhaustive 차등 검증: (5,3) 전수 192개 + (6,3) 앞 200개 — legacy 100% 일치
    mism = 0; n_sat = n_unsat = 0
    corpus = list(generate_backtracking(5, 3, dedup=False,
                                        max_candidates=10**9, max_nodes=10**9))
    it63 = generate_backtracking(6, 3, dedup=False,
                                 max_candidates=200, max_nodes=10**9)
    corpus += list(it63)
    unsat_examples = []
    for ch in corpus:
        res = find_convex_reorientation_sat(ch)
        legacy_witness = not ch.is_reorientable_to_convex()[0]
        assert res.status in ("SAT", "UNSAT")        # 이 크기에서 UNKNOWN 이 나오면 안 됨
        if res.is_witness != legacy_witness:
            mism += 1
        if res.status == "SAT":
            n_sat += 1
        else:
            n_unsat += 1
            unsat_examples.append(ch)
    assert mism == 0, f"legacy 불일치 {mism}건"
    assert n_unsat > 0, "corpus 에 UNSAT(witness) 사례가 없음"
    print(f"차등 검증 OK: {len(corpus)}개 (SAT {n_sat} / UNSAT {n_unsat}) mismatch 0")

    # (4) UNSAT candidate → certificate v1 독립 replay → 그때에만 CERTIFIED
    for ch in unsat_examples[:3]:
        cert = build_certificate(ch, generator="sat-selftest")
        checks = verify_certificate(cert)
        assert checks[-1] == "hash"
    print(f"UNSAT candidate certificate 독립 replay OK ({min(3, len(unsat_examples))}건 CERTIFIED)")

    # (5) 참고용 타이밍 (assert 없음 — 정직 보고, 단일 실행이므로 과장 금지)
    wit = unsat_examples[0]
    t0 = time.perf_counter(); wit.is_reorientable_to_convex(); t_legacy = time.perf_counter() - t0
    t0 = time.perf_counter(); find_convex_reorientation_sat(wit); t_sat = time.perf_counter() - t0
    print(f"참고 타이밍 (witness 1건, 단일 실행): legacy {t_legacy*1e3:.2f}ms / SAT {t_sat*1e3:.2f}ms")

    print("reorientation_sat core-contract assertions OK "
          "(SAT replay 강제 / UNSAT≠CERTIFIED / unknown→UNKNOWN)")
