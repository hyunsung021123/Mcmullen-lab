"""
research_ir.py — WP5: typed ResearchStep IR + 제안 정규화 (#42).

Epic #37 / docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §13. (source: chatgpt, relayed by user)

## 왜 필요한가

기존 Theorist 의 행동 공간(`element_count` / `require_property` / `forbid_property`)
으로는 수학적 동치, 새로운 encoding, generator family, pruning theorem,
certificate transform, performance claim 을 표현할 수 없다 — LLM 이 근거 없는
n-추정으로 수렴하는 구조적 원인 중 하나 (실측, DECISIONS 0013 배경).

이 모듈은 모든 제안을 `research-step/v1` 로 정규화한다. **kind 마다 요구되는
obligation(검증 의무) 목록이 고정**되어 있고, obligation 이 없는 kind 는 존재할 수
없다. 실제 obligation 의 '실행'은 WP6 Process Verifier(#43)의 몫이다 — 이 모듈은
스키마/타입/정규화/하위호환만 담당하며 어떤 것도 참으로 판정하지 않는다.

## 신뢰 경계

- `rationale_summary` 는 짧고 공개 가능한 근거만 담는다 (길이 상한 강제).
  private hidden chain of thought 는 저장 금지 — 스키마 차원에서 긴 텍스트를 거부.
- 기존 3개 bias type 은 IR 로 **무손실** 표현된다 (`from_legacy_bias`/`to_legacy_bias`
  왕복이 항등). 기존 theorist 게이트는 교체하지 않는다 (legacy adapter 는 WP6).

의존성: 표준 라이브러리만.
"""
from __future__ import annotations
import uuid

SCHEMA_ID = "research-step/v1"
RATIONALE_MAX_CHARS = 500          # 공개 가능한 짧은 근거만 — hidden CoT 저장 금지

# kind → 반드시 요구되는 obligation 목록. obligation 없는 kind 는 추가 금지 (#42).
STEP_KINDS: dict[str, list[str]] = {
    "definition": [
        "schema_valid", "type_valid"],
    "equivalence": [
        "schema_valid", "type_valid", "forward_implication",
        "backward_implication", "small_instance_differential_test",
        "independent_replay"],
    "necessary_condition": [
        "schema_valid", "type_valid", "known_witness_retention",
        "small_instance_differential_test"],
    "sufficient_condition": [
        "schema_valid", "type_valid", "known_nonwitness_soundness",
        "small_instance_differential_test"],
    "pruning_rule": [
        "schema_valid", "type_valid", "known_witness_retention",
        "recall_preservation"],
    "generator_family": [
        "schema_valid", "type_valid", "gp_validity_sample",
        "exact_candidate_verification"],
    "encoding": [
        "schema_valid", "type_valid", "small_instance_differential_test",
        "independent_replay"],
    "performance_claim": [
        "schema_valid", "type_valid", "fixed_benchmark", "reproducibility"],
    "certificate_transform": [
        "schema_valid", "type_valid", "certificate_replay", "hash_integrity"],
    "formalization": [
        "schema_valid", "type_valid", "kernel_acceptance"],
}

VALID_STATUS = ("pending", "verified", "rejected")


class StepValidationError(ValueError):
    """스키마/타입 위반. field 속성에 실패 지점을 담는다."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}")


def new_step(*, kind: str, claim_dsl: str, scope: dict,
             rationale_summary: str, parents: list | None = None,
             assumptions: list | None = None, step_id: str | None = None) -> dict:
    """새 ResearchStep 생성 (kind 의 필수 obligation 자동 부여)."""
    if kind not in STEP_KINDS:
        raise StepValidationError("kind", f"알 수 없는 kind '{kind}'. "
                                          f"사용 가능: {sorted(STEP_KINDS)}")
    step = {
        "schema": SCHEMA_ID,
        "id": step_id or f"step-{uuid.uuid4().hex[:8]}",
        "kind": kind,
        "claim": {"dsl": claim_dsl, "scope": dict(scope)},
        "parents": list(parents or []),
        "assumptions": list(assumptions or []),
        "obligations": list(STEP_KINDS[kind]),
        "rationale_summary": rationale_summary,
        "status": "pending",
    }
    validate_step(step)
    return step


def validate_step(step: dict) -> list[str]:
    """스키마 검증. 통과 시 검사 항목 목록 반환, 실패 시 StepValidationError.
    이 함수는 주장의 '참/거짓'을 판정하지 않는다 — 형식만 본다."""
    checked = []
    if not isinstance(step, dict):
        raise StepValidationError("root", "dict 가 아님")
    if step.get("schema") != SCHEMA_ID:
        raise StepValidationError("schema", f"{step.get('schema')!r} != {SCHEMA_ID}")
    checked.append("schema")
    if not isinstance(step.get("id"), str) or not step["id"]:
        raise StepValidationError("id", "비어있지 않은 문자열이어야 함")
    checked.append("id")
    kind = step.get("kind")
    if kind not in STEP_KINDS:
        raise StepValidationError("kind", f"알 수 없는 kind {kind!r}")
    checked.append("kind")
    claim = step.get("claim")
    if not isinstance(claim, dict) or not isinstance(claim.get("dsl"), str) \
            or not claim["dsl"] or not isinstance(claim.get("scope"), dict):
        raise StepValidationError("claim", "claim.dsl(문자열)/claim.scope(dict) 필요")
    checked.append("claim")
    for key in ("parents", "assumptions"):
        if not isinstance(step.get(key), list):
            raise StepValidationError(key, "list 여야 함")
    checked.append("parents/assumptions")
    obl = step.get("obligations")
    if not isinstance(obl, list):
        raise StepValidationError("obligations", "list 여야 함")
    missing = [o for o in STEP_KINDS[kind] if o not in obl]
    if missing:
        raise StepValidationError("obligations",
                                  f"kind '{kind}' 의 필수 obligation 누락: {missing}")
    checked.append("obligations")
    rs = step.get("rationale_summary")
    if not isinstance(rs, str) or not rs:
        raise StepValidationError("rationale_summary", "비어있지 않은 문자열이어야 함")
    if len(rs) > RATIONALE_MAX_CHARS:
        raise StepValidationError(
            "rationale_summary",
            f"{len(rs)}자 > 상한 {RATIONALE_MAX_CHARS}자 — 짧은 공개 근거만 저장"
            " (hidden chain of thought 저장 금지)")
    checked.append("rationale_summary")
    if step.get("status") not in VALID_STATUS:
        raise StepValidationError("status", f"{step.get('status')!r} not in {VALID_STATUS}")
    checked.append("status")
    return checked


# ───────────────────── 기존 bias type 하위호환 (무손실 왕복) ─────────────────────
def from_legacy_bias(bias: dict, *, rationale: str = "legacy bias 자동 변환") -> dict:
    """theorist 의 기존 search_bias 를 ResearchStep 으로 정규화.
    to_legacy_bias 와의 왕복이 항등이 되도록 원본을 scope 에 보존한다."""
    btype = bias.get("type")
    spec = dict(bias.get("spec", {}))
    if btype == "element_count":
        return new_step(kind="generator_family",
                        claim_dsl=f"generate(n={spec.get('n')})",
                        scope={"legacy": {"type": btype, "spec": spec}},
                        rationale_summary=rationale)
    if btype in ("require_property", "forbid_property"):
        name = spec.get("name")
        args = spec.get("args", [])
        neg = "" if btype == "require_property" else "not "
        return new_step(kind="necessary_condition",
                        claim_dsl=f"forall witness w: {neg}{name}({args or ''})",
                        scope={"legacy": {"type": btype, "spec": spec}},
                        rationale_summary=rationale)
    raise StepValidationError("legacy.type", f"알 수 없는 legacy type {btype!r}")


def to_legacy_bias(step: dict) -> dict:
    """ResearchStep → 기존 search_bias (무손실 역변환). legacy 출신이 아니면 오류."""
    legacy = step.get("claim", {}).get("scope", {}).get("legacy")
    if not isinstance(legacy, dict):
        raise StepValidationError("claim.scope.legacy",
                                  "legacy bias 출신 step 이 아님 — 역변환 불가")
    return {"type": legacy["type"], "spec": dict(legacy["spec"])}


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    import json

    # (1) 모든 kind 가 비어있지 않은 obligation 목록을 갖는지 (obligation 없는 kind 금지)
    for kind, obls in STEP_KINDS.items():
        assert obls and "schema_valid" in obls and "type_valid" in obls, kind
    print(f"kind {len(STEP_KINDS)}종 전부 obligation 보유 OK")

    # (2) 기존 3개 bias type 무손실 왕복 (theorist 자체 테스트의 canned bias 그대로)
    legacy_biases = [
        {"type": "element_count", "spec": {"n": 8}},
        {"type": "require_property", "spec": {"name": "acyclic"}},
        {"type": "forbid_property", "spec": {"name": "totally_cyclic", "args": []}},
    ]
    for b in legacy_biases:
        step = from_legacy_bias(b)
        validate_step(step)
        back = to_legacy_bias(step)
        assert back == {"type": b["type"], "spec": dict(b.get("spec", {}))}, (b, back)
    print("legacy bias 3종 무손실 왕복 OK (from_legacy_bias → to_legacy_bias 항등)")

    # (3) mock LLM 정규화/검증 왕복: JSON 문자열 제안 → 정규화 → 검증 → 직렬화 왕복
    mock_llm_output = json.dumps({
        "kind": "equivalence",
        "claim_dsl": "witness(chi) iff covers_reorientation_hypercube(chi)",
        "scope": {"uniform": True, "rank": 3, "n": 6},
        "rationale_summary": "모든 재배향이 어떤 circuit obstruction 에 커버되면 "
                             "convex 재배향이 존재하지 않는다.",
    })
    raw = json.loads(mock_llm_output)
    step = new_step(kind=raw["kind"], claim_dsl=raw["claim_dsl"],
                    scope=raw["scope"], rationale_summary=raw["rationale_summary"])
    assert step["obligations"] == STEP_KINDS["equivalence"]
    rt = json.loads(json.dumps(step, ensure_ascii=False))
    assert validate_step(rt)
    print("mock LLM 제안 정규화/검증/직렬화 왕복 OK")

    # (4) 거부 케이스: 알 수 없는 kind / obligation 누락 / 긴 rationale(hidden CoT 방지)
    import copy
    try:
        new_step(kind="miracle", claim_dsl="x", scope={}, rationale_summary="r")
        raise AssertionError("알 수 없는 kind 가 통과")
    except StepValidationError as e:
        assert e.field == "kind"
    bad = copy.deepcopy(step); bad["obligations"] = ["schema_valid"]
    try:
        validate_step(bad); raise AssertionError("obligation 누락이 통과")
    except StepValidationError as e:
        assert e.field == "obligations"
    try:
        new_step(kind="definition", claim_dsl="x", scope={},
                 rationale_summary="장문" * 1000)
        raise AssertionError("긴 rationale 이 통과")
    except StepValidationError as e:
        assert e.field == "rationale_summary"
    print("거부 케이스 OK (unknown kind / obligation 누락 / hidden-CoT 길이 상한)")

    print("research_ir core-contract assertions OK")
