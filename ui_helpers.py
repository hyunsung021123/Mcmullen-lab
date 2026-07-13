"""
ui_helpers.py — dashboard.py 를 위한 순수 로직 모듈 (표시 문자열/검증/뷰모델 변환).

원칙:
  * Streamlit 을 import 하지 않는다 — 여기 있는 함수는 CLI/테스트에서도 그대로 쓸 수
    있어야 한다.
  * 여기서 하는 일은 전부 "이미 결정된 사실을 정확하게 표현"하는 것뿐이다. 판정/생성
    로직(om_core.py, criteria.py 의 판정 의미, generator.py, search.py, progress.py,
    store.py)은 절대 재구현하거나 우회하지 않는다 — 필요한 값은 그 모듈들이 이미
    계산해 둔 것을 그대로 가져다 쓴다.
  * 사용자(수학자)는 OM/circuit/acyclic/witness/McMullen 상한 같은 수학 개념은 잘
    안다. 여기서 숨기는 건 프로그램 내부 개념(backend override, thread, JSON 필드명
    등)뿐이다 — 수학 용어를 임의로 순화하지 않는다.
"""
from __future__ import annotations
from typing import Optional

from criteria import CriteriaSet
from om_classes import CLASS_REGISTRY, has_generator


# ───────────────────────── 신뢰 수준 표시(섹션 9 A/B/C/D) ─────────────────────────
TRUST_DETERMINISTIC = "결정론적 검증 완료"
TRUST_EMPIRICAL = "검증된 표본에서 관찰된 경험적 패턴 (정리 아님)"
TRUST_AI_HYPOTHESIS = "미검증 AI 가설"
TRUST_ADOPTED_RULE = "결정론적 게이트를 통과해 탐색 규칙으로 채택됨 (증명된 정리 아님)"
TRUST_REJECTED = "결정론적 반박으로 기각됨"

PROPOSAL_STATUS_LABELS = {
    "survived": TRUST_ADOPTED_RULE,
    "rejected": TRUST_REJECTED,
    "unverified": "검증 전",
}

# search.py 의 Progress.candidates / RoundRecord.num_candidates 는
# "이번 실행에서 사용자 조건(require/forbid)을 통과해 실제로 witness 판정까지 받은
# 후보 수"다 — 백트래킹이 가지치기한 노드 수나 전체 시도 수가 아니다. 확인 근거:
# search.py 의 for-loop 는 class_generator(...) 가 이미 accept 콜백으로 필터링해
# yield 한 chirotope 에 대해서만 mcmullen_evaluate 를 부르고 candidates 를 늘린다.
CANDIDATE_COUNTER_LABEL = "사용자 조건을 통과해 witness 판정까지 받은 후보 수"

STATE_LABELS = {
    "idle": "대기",
    "running": "실행 중",
    "paused": "일시정지",
    "stopping": "중단 처리 중",
    "stopped": "사용자가 중단함",
    "done": "종료됨",
    "error": "오류로 종료됨",
}


def finish_reason_label(state: str, run: dict, summary: dict) -> str:
    """종료 상태를 정확히 아는 범위 안에서만 설명한다. 추측하지 않는다 —
    search.py 의 유일한 자동 종료 조건은 '목표 상한(2d+1) 달성'뿐이므로, 그 조건이
    저장된 결과로 실제로 확인될 때만 '목표 달성'이라고 말한다. 그 외 'done' 은
    설정된 반복 횟수가 모두 끝나 종료된 것으로만 설명한다."""
    if state == "error":
        return STATE_LABELS["error"]
    if state == "stopped":
        return STATE_LABELS["stopped"]
    if state == "done":
        d = run.get("d")
        best = summary.get("best_upper_bound")
        if d is not None and best is not None and best == 2 * d + 1:
            return "목표 상한(2d+1) 달성으로 종료"
        return "설정된 탐색(반복 횟수 등)이 모두 끝나 종료 — 목표 상한 미달성"
    return STATE_LABELS.get(state, state)


# ───────────────────────── 탐색 클래스 표시(섹션 3) ─────────────────────────
# 수학적으로 정확한 설명 + (해당하면) 눈에 띄는 경고. om_classes.py 의 OMClass.note 는
# CLI 사용자도 보는 짧은 문구라 그대로 두고, UI 전용으로 더 자세히 설명한다.
CLASS_DISPLAY: dict[str, dict] = {
    "uniform": {
        "label": "Uniform OM (전수 백트래킹 기반)",
        "math_name": "uniform OM",
        "detail": (
            "uniform OM 후보를 탐색합니다. 작은 n·rank 범위에서는 백트래킹이 전수적으로 "
            "동작할 수 있지만, 범위가 커지면 후보 수 제한과 계산량 때문에 전체 열거를 "
            "보장하지 않습니다. 실현 불가능(non-realizable)한 OM도 포함될 수 있습니다."
        ),
        "warning": None,
    },
    "realizable_uniform": {
        "label": "Realizable uniform OM 표본 (무작위 점배치)",
        "math_name": "실현 가능한(realizable) uniform OM 표본",
        "detail": (
            "실현 가능한 uniform OM만 생성합니다. 무작위 점배치에서 얻은 **표본**이며, "
            "실현 가능한 모든 OM을 열거하는 것이 아닙니다. 실현 불가능한 OM은 이 클래스로는 "
            "찾을 수 없습니다."
        ),
        "warning": None,
    },
    "rank2_uniform": {
        "label": "Rank-2 uniform OM (REOM 실험용 인코딩)",
        "math_name": "rank-2 uniform OM",
        "detail": "rank=2 로 고정된 원형 부호열 OM을 탐색합니다. REOM(상위 rank 인코딩) 실험 기반입니다.",
        "warning": (
            "이걸 문자 그대로 'rank-2 McMullen 탐색'으로 해석하면 안 됩니다 — rank-2에서는 "
            "회로가 3원소뿐이라 convex position 조건이 자명하게 퇴화합니다(CLAUDE.md §5의 "
            "알려진 특이 케이스). 현재는 상위 rank 문제(REOM 인코딩)를 위한 실험 모드이며, "
            "일반 rank-(d+1) 탐색과 같은 의미로 해석해서는 안 됩니다."
        ),
    },
    "cyclic": {
        "label": "Cyclic / alternating OM (기준선)",
        "math_name": "cyclic(alternating) OM",
        "detail": "순환다면체(cyclic polytope) 계열의 OM입니다.",
        "warning": "이 클래스는 기준선(baseline)·구조적 seed 용도입니다 — 일반적인 witness 탐색 클래스가 아닙니다.",
    },
    "lawrence": {
        "label": "Lawrence OM (소켓 — 아직 실행 불가)",
        "math_name": "Lawrence OM",
        "detail": "일반 Lawrence 구성은 non-uniform이라 현재 코어(uniform 전용) 확장이 필요합니다.",
        "warning": "Lawrence 계열은 현재 수학적 생성기/인코딩이 연결되지 않아 실행할 수 없습니다.",
    },
}


def class_display(name: str) -> dict:
    """등록되지 않은/향후 추가된 클래스(예: 사용자가 register_class 로 붙인 reom)는
    om_classes.py 의 description/note 를 그대로 fallback 으로 쓴다 — 새 계열을 UI가
    미리 안다고 가짜로 꾸미지 않는다."""
    if name in CLASS_DISPLAY:
        return CLASS_DISPLAY[name]
    oc = CLASS_REGISTRY.get(name)
    if oc is None:
        return {"label": name, "math_name": name, "detail": "", "warning": None}
    return {"label": name, "math_name": name, "detail": oc.description,
            "warning": (oc.note or None)}


# ───────────────────────── 실험 문장(섹션 4) ─────────────────────────
def criteria_summary_from_items(criteria_items: list[dict]) -> list[dict]:
    """UI 폼에서 고른 {name, mode, args} 목록을 criteria.py 의 REGISTRY 를 통해
    {name, mode, description} 목록으로 바꾼다 — 설명 문구를 여기서 다시 만들지 않고
    criteria.py 가 이미 등록해 둔 공식 설명을 그대로 재사용한다."""
    return CriteriaSet.from_config(criteria_items).active_summary()


def experiment_sentence(d: int, r: int, om_class: str, n_min: int, n_max: int,
                        criteria_summary: list[dict]) -> str:
    """현재 설정을 수학적 자연어 한 문단으로 요약한다."""
    math_name = class_display(om_class)["math_name"]
    n_str = f"n={n_min}" if n_min == n_max else f"{n_min} ≤ n ≤ {n_max}"

    require = [c["description"] for c in criteria_summary
              if c["mode"] == "require" and c["name"] != "valid"]
    forbid = [c["description"] for c in criteria_summary if c["mode"] == "forbid"]
    target = [c["description"] for c in criteria_summary if c["mode"] == "target"]

    parts = [f"dimension {d}, rank {r}, {n_str}인 {math_name} 후보를 탐색합니다."]
    if require:
        parts.append("다음을 반드시 만족해야 합니다: " + "; ".join(require) + ".")
    if forbid:
        parts.append("다음을 만족하면 제외합니다: " + "; ".join(forbid) + ".")
    if target:
        parts.append("다음을 만족하는 경우를 성공(witness)으로 판정합니다: " +
                     "; ".join(target) + ".")
    else:
        parts.append("이번 설정에는 성공 조건(target)이 지정되어 있지 않습니다 — "
                     "witness 판정 없이 관찰/통계 목적으로만 탐색합니다.")
    return " ".join(parts)


# ───────────────────────── 설정 검증(섹션 5) ─────────────────────────
# 서로 논리적 부정 관계인 조건 쌍 — 둘 다 require 로 걸면 어떤 후보도 통과할 수 없다.
# (criteria.py: not_reorientable_to_convex 의 predicate 는 정확히
#  `not reorientable_to_convex 의 predicate` 이다.)
_NEGATION_PAIRS = [("reorientable_to_convex", "not_reorientable_to_convex")]


def validate_experiment(*, d: int, r: int, om_class: str, n_min: int, n_max: int,
                        criteria_items: list[dict]) -> list[str]:
    """실행을 막아야 하는 오류 목록(비어 있으면 실행 가능)."""
    errors = []
    if n_min > n_max:
        errors.append(f"n_min({n_min}) 이 n_max({n_max}) 보다 큽니다.")
    if n_min < r + 1:
        errors.append(
            f"n_min({n_min}) 이 rank+1({r + 1}) 보다 작습니다 — 이 범위에서는 회로"
            f"(Radon 분할)가 존재하지 않아 acyclic/convex 계열 조건이 의미를 갖지 않습니다.")
    if not has_generator(om_class):
        errors.append(class_display(om_class)["warning"] or
                     f"클래스 '{om_class}' 는 아직 생성기가 연결되지 않아 실행할 수 없습니다.")

    mode_by_name = {c["name"]: c["mode"] for c in criteria_items}
    for a, b in _NEGATION_PAIRS:
        if mode_by_name.get(a) == "require" and mode_by_name.get(b) == "require":
            errors.append(f"'{a}' 와 '{b}' 를 동시에 require 로 설정했습니다 — 이 둘은 "
                          f"논리적으로 정확히 반대 조건이라 어떤 후보도 둘 다 만족할 수 없습니다.")
    return errors


def feasibility_warnings(*, d_eff: int, backend_effective: str, n_max: int) -> list[str]:
    """정성적 경고만 제공한다 — 예상 소요 시간을 약속하지 않는다."""
    warnings = []
    if backend_effective == "backtracking" and d_eff >= 4 and n_max >= 10:
        warnings.append(
            f"rank {d_eff + 1}, n={n_max}까지의 모든 uniform OM을 백트래킹으로 전수 생성하는 "
            f"것은 현재 구조에서는 현실적이지 않습니다. 구조적 seed(cyclic) 또는 Z3 기반 "
            f"제한 탐색이 더 적절합니다.")
    return warnings


# ───────────────────────── 최선 결과 표시(섹션 7) ─────────────────────────
def best_result_headline(run: dict, summary: dict) -> Optional[str]:
    """ν(d) ≤ n−1 형태의 한 줄 headline. witness 가 없으면 None."""
    best = summary.get("best_upper_bound")
    if best is None:
        return None
    d = run.get("d")
    return f"ν({d}) ≤ {best}"


if __name__ == "__main__":
    # class_display / has_generator
    assert class_display("lawrence")["warning"]
    assert class_display("uniform")["warning"] is None
    assert class_display("이런-클래스-없음")["label"] == "이런-클래스-없음"

    # experiment_sentence — REGISTRY 설명을 그대로 재사용하는지 확인
    items = [{"name": "acyclic", "mode": "require"},
             {"name": "totally_cyclic", "mode": "forbid"},
             {"name": "not_reorientable_to_convex", "mode": "target"}]
    summ = criteria_summary_from_items(items)
    sent = experiment_sentence(d=3, r=4, om_class="realizable_uniform",
                              n_min=8, n_max=9, criteria_summary=summ)
    assert "dimension 3, rank 4" in sent
    assert "8 ≤ n ≤ 9" in sent
    assert "양의 회로가 없음" in sent          # acyclic 의 REGISTRY 설명
    assert "성공(witness)으로 판정" in sent
    print("experiment_sentence:", sent)

    # validate_experiment — 실제로 검증 로직을 태워서 확인
    errs = validate_experiment(d=3, r=4, om_class="realizable_uniform",
                               n_min=8, n_max=9, criteria_items=items)
    assert errs == []
    errs2 = validate_experiment(d=3, r=4, om_class="realizable_uniform",
                                n_min=2, n_max=1, criteria_items=items)
    assert len(errs2) >= 1
    errs3 = validate_experiment(d=3, r=4, om_class="lawrence",
                                n_min=8, n_max=9, criteria_items=items)
    assert any("생성기" in e or "연결되지" in e for e in errs3)
    contradiction = [{"name": "reorientable_to_convex", "mode": "require"},
                     {"name": "not_reorientable_to_convex", "mode": "require"}]
    errs4 = validate_experiment(d=3, r=4, om_class="uniform", n_min=8, n_max=9,
                                criteria_items=contradiction)
    assert any("논리적으로" in e for e in errs4)

    # feasibility_warnings — d_eff>=4 백트래킹만 경고, 그 외는 조용함
    assert feasibility_warnings(d_eff=5, backend_effective="backtracking", n_max=12)
    assert not feasibility_warnings(d_eff=2, backend_effective="backtracking", n_max=6)
    assert not feasibility_warnings(d_eff=5, backend_effective="random", n_max=12)

    # finish_reason_label — 목표 달성 여부를 실제 값으로만 판단
    assert finish_reason_label("done", {"d": 3}, {"best_upper_bound": 7}) == \
        "목표 상한(2d+1) 달성으로 종료"
    assert finish_reason_label("done", {"d": 3}, {"best_upper_bound": 9}) == \
        "설정된 탐색(반복 횟수 등)이 모두 끝나 종료 — 목표 상한 미달성"
    assert finish_reason_label("stopped", {}, {}) == "사용자가 중단함"

    assert best_result_headline({"d": 5}, {"best_upper_bound": 11}) == "ν(5) ≤ 11"
    assert best_result_headline({"d": 5}, {"best_upper_bound": None}) is None

    print("ui_helpers.py core-contract assertions OK")
