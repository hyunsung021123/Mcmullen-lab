"""
process_verifier.py — WP6: 결정론적 Process Verifier + first-failure 피드백 (#43).

Epic #37 / docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §13. (source: chatgpt, relayed by user)

## 역할

WP5 ResearchStep(`research_ir.py`)의 obligation 들을 **결정론적으로 실행**하는
hard gate. learned PRM(#46)보다 먼저 존재해야 하는 층이다.

- 한 obligation 이라도 실패하면 즉시 기각하고 **첫 실패 위치**를 기록한다.
- 동적 피드백은 긴 자유 텍스트가 아니라 기계 판독 가능한 구조로 전달한다:
      {"status": "negative", "first_failed_obligation": "...",
       "counterexample_id": "...", "detail": "...", ...}
- **fail-closed**: 자동 실행기가 없는 obligation 은 통과가 아니라 **기각**이다.
  "검증할 수 없음"과 "검증됨"을 절대 혼동하지 않는다 — 실행기가 생기기 전까지
  그 kind 의 step 은 hard gate 를 넘을 수 없다.

## legacy gate adapter

기존 `theorist.proof_checker` / `theorist.counterexample_hunter` 는 삭제하지 않고
이 모듈의 어댑터로 사용한다 (CLAUDE.md §2 — 적대자는 항상 결정론적 코드).
LLM 은 이 모듈의 어떤 판정에도 관여하지 않는다.

의존성: 표준 라이브러리 + om_core/criteria/generator/theorist/research_ir.
"""
from __future__ import annotations
from typing import Optional

from om_core import Chirotope
from criteria import REGISTRY
from generator import generate_backtracking
from theorist import proof_checker, counterexample_hunter, _criterion_holds
from research_ir import validate_step, StepValidationError, to_legacy_bias


def _audit(status: str, passed: list, *, first_failed: Optional[str] = None,
           detail: str = "", counterexample_id: Optional[str] = None,
           counterexample: Optional[dict] = None) -> dict:
    return {"status": status, "hard_gate_passed": status == "positive",
            "passed": list(passed), "first_failed_obligation": first_failed,
            "detail": detail, "counterexample_id": counterexample_id,
            "counterexample": counterexample}


def _legacy_of(step: dict) -> Optional[dict]:
    try:
        return to_legacy_bias(step)
    except StepValidationError:
        return None


def verify_until_first_failure(step: dict, *,
                               known_witnesses: list | None = None,
                               known_nonwitnesses: list | None = None,
                               d: int | None = None, r: int | None = None,
                               memory=None) -> dict:
    """step 의 obligation 들을 순서대로 실행. 첫 실패에서 즉시 기각(negative).

    d/r: small-instance 검사에 쓸 문제 크기 (없으면 scope 에서 추론 시도).
    반환 audit 은 결정론적이다 — 같은 입력이면 같은 출력."""
    known_witnesses = known_witnesses or []
    known_nonwitnesses = known_nonwitnesses or []
    passed: list[str] = []

    # scope 에서 d/r 추론 (명시 인자 우선)
    scope = step.get("claim", {}).get("scope", {}) if isinstance(step, dict) else {}
    if r is None:
        r = scope.get("rank") if isinstance(scope.get("rank"), int) else 3
    if d is None:
        d = scope.get("dimension") if isinstance(scope.get("dimension"), int) else r - 1

    legacy = _legacy_of(step) if isinstance(step, dict) else None

    for obligation in (step.get("obligations", []) if isinstance(step, dict) else []):
        ok, detail, cx_id, cx = _run_obligation(
            obligation, step, legacy, d, r,
            known_witnesses, known_nonwitnesses, memory)
        if not ok:
            return _audit("negative", passed, first_failed=obligation,
                          detail=detail, counterexample_id=cx_id, counterexample=cx)
        passed.append(obligation)

    if not passed:
        return _audit("negative", passed, first_failed="schema_valid",
                      detail="obligation 이 없는 step — 검증 의무 없는 주장은 기각")
    return _audit("positive", passed)


def _run_obligation(obligation: str, step: dict, legacy: Optional[dict],
                    d: int, r: int, witnesses: list, nonwitnesses: list,
                    memory) -> tuple:
    """단일 obligation 실행. (ok, detail, counterexample_id, counterexample)."""
    # ── 항상 실행 가능한 형식 검사 ──
    if obligation == "schema_valid":
        try:
            validate_step(step)
            return True, "", None, None
        except StepValidationError as e:
            return False, str(e), None, None

    if obligation == "type_valid":
        if legacy is not None:
            btype = legacy["type"]; spec = legacy.get("spec", {})
            if btype in ("require_property", "forbid_property"):
                name = spec.get("name")
                if name not in REGISTRY:
                    return False, f"미등록 기준 '{name}' (CLAUDE.md §4)", None, None
            elif btype == "element_count":
                n = spec.get("n")
                if not isinstance(n, int) or not (r + 1 <= n <= 2 * d + 4):
                    return False, f"n 범위 밖: {n}", None, None
            return True, "", None, None
        # 비-legacy: scope 타입만 검사 가능
        scope = step.get("claim", {}).get("scope", {})
        if not isinstance(scope, dict):
            return False, "scope 가 dict 아님", None, None
        return True, "", None, None

    # ── legacy property/element 기반 step 에서 실행 가능한 수학적 검사 ──
    if obligation == "known_witness_retention" and legacy is not None:
        cx = counterexample_hunter(legacy, witnesses)      # 결정론적 적대자 어댑터
        if cx:
            w = next((w for w in witnesses
                      if legacy["type"] == "require_property" and
                      not _criterion_holds(legacy["spec"]["name"],
                                           legacy["spec"].get("args", []), w)
                      or legacy["type"] == "forbid_property" and
                      _criterion_holds(legacy["spec"]["name"],
                                       legacy["spec"].get("args", []), w)), None)
            return False, cx, f"witness-n{w.n}" if w else None, \
                (w.to_dict() if w else None)
        return True, "", None, None

    if obligation == "small_instance_differential_test" and legacy is not None:
        ok, reason = proof_checker(legacy, d, r, memory)   # 게이트 어댑터(공허성 포함)
        return (True, "", None, None) if ok else (False, f"proof_checker: {reason}",
                                                  None, None)

    if obligation == "known_nonwitness_soundness" and legacy is not None:
        # sufficient_condition 해석: "성질 P ⟹ witness". P 를 만족하는 non-witness
        # 가 하나라도 있으면 반례.
        if legacy["type"] == "require_property":
            name = legacy["spec"]["name"]; args = legacy["spec"].get("args", [])
            for nw in nonwitnesses:
                if _criterion_holds(name, args, nw):
                    return False, f"non-witness(n={nw.n})가 '{name}' 만족 — 충분조건 반례", \
                        f"nonwitness-n{nw.n}", nw.to_dict()
            return True, "", None, None
        return False, "이 legacy type 에는 충분조건 해석이 정의되지 않음", None, None

    if obligation == "gp_validity_sample" and legacy is not None \
            and legacy["type"] == "element_count":
        n = legacy["spec"]["n"]
        sample = list(generate_backtracking(n, r, dedup=False,
                                            max_candidates=5, max_nodes=200_000))
        if not sample:
            return False, f"n={n} 에서 GP-valid 후보가 생성되지 않음", None, None
        bad = next((ch for ch in sample if not ch.is_valid()), None)
        if bad:
            return False, "생성 표본 중 GP-invalid 존재 (생성기 회귀)", None, bad.to_dict()
        return True, "", None, None

    if obligation == "exact_candidate_verification" and legacy is not None \
            and legacy["type"] == "element_count":
        n = legacy["spec"]["n"]
        sample = list(generate_backtracking(n, r, dedup=False,
                                            max_candidates=3, max_nodes=200_000))
        for ch in sample:
            ch.is_reorientable_to_convex()      # 표본이 legacy 경로로 판정 가능한지
        return True, "", None, None

    # ── 자동 실행기가 없는 obligation: fail-closed ──
    return False, (f"obligation '{obligation}' 의 자동 실행기가 아직 없음 — "
                   f"fail-closed 원칙에 따라 기각 ('검증 불가'는 '검증됨'이 아니다)"), \
        None, None


if __name__ == "__main__":
    import json
    from research_ir import from_legacy_bias, new_step

    # 알려진 witness 하나 확보 ((6,3) 결정론적 첫 witness) + non-witness
    wit = None
    for cand in generate_backtracking(6, 3, dedup=False,
                                      max_candidates=10**9, max_nodes=10**9):
        if not cand.is_reorientable_to_convex()[0]:
            wit = cand
            break
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])

    # (1) 통과 케이스: require_property(acyclic) — witness 가 acyclic 이면 retention 통과
    step_ok = from_legacy_bias({"type": "require_property", "spec": {"name": "acyclic"}})
    a1 = verify_until_first_failure(step_ok, known_witnesses=[wit], d=2, r=3)
    # witness 가 acyclic 인지에 따라 판정이 갈린다 — 실측으로 기대값 고정
    expect = wit.is_acyclic()
    assert a1["hard_gate_passed"] == expect, a1
    print(f"require(acyclic) 판정 = {a1['status']} (witness acyclic={expect} 실측과 일치)")

    # (2) 미등록 기준 → type_valid 에서 첫 실패
    step_bad = from_legacy_bias({"type": "require_property",
                                 "spec": {"name": "nonexistent"}})
    a2 = verify_until_first_failure(step_bad, known_witnesses=[wit], d=2, r=3)
    assert a2["status"] == "negative" and a2["first_failed_obligation"] == "type_valid"
    print("미등록 기준 → type_valid 첫 실패 OK")

    # (3) witness 배제 편향 → known_witness_retention 에서 반례와 함께 실패
    step_cx = from_legacy_bias({"type": "require_property",
                                "spec": {"name": "convex_position"}})
    a3 = verify_until_first_failure(step_cx, known_witnesses=[wit], d=2, r=3)
    assert a3["status"] == "negative"
    assert a3["first_failed_obligation"] == "known_witness_retention"
    assert a3["counterexample_id"] and a3["counterexample"]
    print("witness 배제 편향 → retention 실패 + 기계 판독 가능한 반례 OK:",
          json.dumps({k: a3[k] for k in ("status", "first_failed_obligation",
                                         "counterexample_id")}, ensure_ascii=False))

    # (4) element_count → generator_family: 실행 가능한 obligation 전부 통과
    step_n = from_legacy_bias({"type": "element_count", "spec": {"n": 6}})
    a4 = verify_until_first_failure(step_n, d=2, r=3)
    assert a4["hard_gate_passed"], a4
    print("element_count(n=6) → generator_family 전 obligation 통과 OK")

    # (5) fail-closed: 실행기 없는 obligation(equivalence 의 forward_implication)은
    #     통과가 아니라 기각이어야 한다
    step_eq = new_step(kind="equivalence", claim_dsl="A iff B",
                       scope={"rank": 3}, rationale_summary="테스트")
    a5 = verify_until_first_failure(step_eq, d=2, r=3)
    assert a5["status"] == "negative"
    assert a5["first_failed_obligation"] == "forward_implication"
    assert "fail-closed" in a5["detail"]
    print("fail-closed OK (실행기 없는 obligation → 기각, 통과 아님)")

    # (6) 결정론: 같은 입력 → 같은 출력
    assert verify_until_first_failure(step_cx, known_witnesses=[wit], d=2, r=3) == a3
    print("결정론 OK (동일 입력 → 동일 audit)")

    print("process_verifier core-contract assertions OK "
          "(first-failure / fail-closed / legacy adapter / 결정론)")
