"""
step_ranker.py — WP7a: rule-based step ranker (#45).

Epic #37. (source: chatgpt, relayed by user)

## Hard gate 와 soft score 의 엄격한 분리

- **Hard gate** (process_verifier, WP6): step 이 큐에 들어갈 수 있는지를 정한다.
  전부 통과해야 함. 이 모듈은 절대 관여하지 않는다.
- **Soft score** (이 모듈): hard gate 를 **이미 통과한** step 들의 실행 순서만 정한다.
  점수는 진실 여부를 결정하지 않는다 — 낮은 점수는 "나중에"일 뿐 "거짓"이 아니고,
  높은 점수는 "먼저"일 뿐 "참"이 아니다.

score 형태 (설계 문서 §WP9):
    S(s) = α·Δcoverage_proxy + β·space_reduction_proxy + γ·novelty
           − δ·runtime_proxy − η·risk

모든 항은 step/audit 구조에서 결정론적으로 계산된다 (LLM/난수 없음).
learned PRM(#46)은 이 ranker 를 이길 때만(top-k hard-gate 통과율 +20%) 기본 경로에
들어올 수 있다 — 그 비교를 위한 평가 지표(top_k_pass_rate)를 여기서 고정한다.

의존성: 표준 라이브러리만.
"""
from __future__ import annotations

# 결정론적 가중치 (변경은 새 DECISIONS 항목으로만)
WEIGHTS = {"alpha": 3.0, "beta": 2.0, "gamma": 1.0, "delta": 0.5, "eta": 1.0}

# kind 별 탐색 기여 proxy — "witness 발견에 얼마나 직접적인가"의 고정 순서
KIND_COVERAGE_PROXY = {
    "generator_family": 1.0,       # 후보를 직접 공급
    "pruning_rule": 0.9,           # 공간을 직접 줄임
    "encoding": 0.8,               # 새 탐색 경로
    "equivalence": 0.7,
    "necessary_condition": 0.6,
    "sufficient_condition": 0.6,
    "certificate_transform": 0.4,
    "performance_claim": 0.3,
    "formalization": 0.2,
    "definition": 0.1,
}


def score(step: dict, audit: dict, *, seen_claims: set | None = None) -> float:
    """hard gate 를 통과한 step 의 실행 우선순위 점수 (결정론).
    통과하지 못한 step 에 대해 호출하면 ValueError — 게이트 우회 방지."""
    if not audit.get("hard_gate_passed"):
        raise ValueError("hard gate 를 통과하지 않은 step 은 순위 대상이 아님 "
                         "(score 는 진실/채택 여부를 결정하지 않는다)")
    kind = step.get("kind", "definition")
    coverage = KIND_COVERAGE_PROXY.get(kind, 0.1)

    # 공간 축소 proxy: scope 가 구체적일수록(제약이 많을수록) 높게
    scope = step.get("claim", {}).get("scope", {})
    space_reduction = min(1.0, 0.2 * len([k for k in scope if k != "legacy"])
                          + (0.5 if "legacy" in scope else 0.0))

    novelty = 0.0 if (seen_claims and step.get("claim", {}).get("dsl") in seen_claims) \
        else 1.0

    # 실행 비용 proxy: obligation 수 (실측 runtime 이 audit 에 있으면 그것 우선)
    runtime_proxy = audit.get("runtime_s") or 0.1 * len(step.get("obligations", []))

    risk = 0.2 * len(step.get("assumptions", []))

    w = WEIGHTS
    return (w["alpha"] * coverage + w["beta"] * space_reduction
            + w["gamma"] * novelty - w["delta"] * runtime_proxy - w["eta"] * risk)


def rank(steps_with_audits: list, *, seen_claims: set | None = None) -> list:
    """[(step, audit), ...] → hard gate 통과분만, 점수 내림차순(동점은 step id 사전순 —
    완전한 결정론)으로 정렬해 반환. 통과 못한 step 은 결과에 포함되지 않는다
    (그러나 그 step 의 audit 상태를 이 함수가 바꾸는 일은 없다)."""
    passed = [(s, a) for (s, a) in steps_with_audits if a.get("hard_gate_passed")]
    return sorted(passed,
                  key=lambda sa: (-score(sa[0], sa[1], seen_claims=seen_claims),
                                  str(sa[0].get("id"))))


def top_k_pass_rate(ranked: list, k: int, verify_fn) -> float:
    """#46(learned PRM) 비교용 고정 평가 지표: 순위 상위 k 개 step 이 '다음 hard
    verification'(verify_fn)을 통과하는 비율. PRM 은 이 지표에서 rule-based 대비
    20% 이상 개선해야 기본 경로에 들어올 수 있다."""
    top = ranked[:k]
    if not top:
        return 0.0
    return sum(1 for (s, _) in top if verify_fn(s)) / len(top)


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    from research_ir import from_legacy_bias
    from process_verifier import verify_until_first_failure

    # 실제 파이프라인 산출물로 테스트 (mock 아님)
    s_gen = from_legacy_bias({"type": "element_count", "spec": {"n": 6}})
    a_gen = verify_until_first_failure(s_gen, d=2, r=3)
    s_prop = from_legacy_bias({"type": "require_property", "spec": {"name": "acyclic"}})
    a_prop = verify_until_first_failure(s_prop, d=2, r=3)
    s_bad = from_legacy_bias({"type": "require_property", "spec": {"name": "nonexistent"}})
    a_bad = verify_until_first_failure(s_bad, d=2, r=3)

    assert a_gen["hard_gate_passed"] and a_prop["hard_gate_passed"]
    assert not a_bad["hard_gate_passed"]

    # (1) 게이트 우회 방지: 통과 못한 step 의 score 호출은 오류
    try:
        score(s_bad, a_bad)
        raise AssertionError("게이트 미통과 step 이 score 됨")
    except ValueError:
        pass
    print("게이트 우회 방지 OK (미통과 step 은 score 불가)")

    # (2) rank 는 통과분만 포함하고, audit 을 변형하지 않는다 (score ≠ 진실 판정)
    import copy
    a_bad_before = copy.deepcopy(a_bad)
    ranked = rank([(s_gen, a_gen), (s_prop, a_prop), (s_bad, a_bad)])
    assert len(ranked) == 2 and all(a["hard_gate_passed"] for _, a in ranked)
    assert a_bad == a_bad_before          # 순위 계산이 게이트 판정을 바꾸지 않음
    print("rank 통과분 한정 + audit 불변 OK")

    # (3) 결정론: 같은 입력 → 같은 순서 (두 번 실행 비교)
    ranked2 = rank([(s_prop, a_prop), (s_bad, a_bad), (s_gen, a_gen)])  # 입력 순서 뒤섞기
    assert [s["id"] for s, _ in ranked] == [s["id"] for s, _ in ranked2]
    print("결정론 OK (입력 순서와 무관하게 동일 순위)")

    # (4) novelty: 이미 본 claim 은 점수가 내려간다 (순서만 바뀔 뿐 제거되지 않는다)
    seen = {s_gen["claim"]["dsl"]}
    sc_new = score(s_gen, a_gen)
    sc_seen = score(s_gen, a_gen, seen_claims=seen)
    assert sc_seen < sc_new
    assert len(rank([(s_gen, a_gen)], seen_claims=seen)) == 1   # 여전히 큐에 있음
    print("novelty 감점 OK (제거가 아니라 순서 조정)")

    # (5) #46 비교용 평가 지표 고정
    rate = top_k_pass_rate(ranked, 2, lambda s: s["kind"] == "generator_family")
    assert rate == 0.5
    print(f"top_k_pass_rate 지표 OK (예시값 {rate})")

    print("step_ranker core-contract assertions OK "
          "(gate/score 분리 / audit 불변 / 결정론 / PRM 비교 지표 고정)")
