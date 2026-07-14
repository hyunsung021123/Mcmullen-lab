"""
translations.py — WP7c: Cross-Domain Translation Registry (#48).

Epic #37. (source: chatgpt, relayed by user)

## 왜 필요한가

prompt persona 추가는 교차 도메인 전환이 아니다. 정식 translation 은 encode/decode
와 **exactness 등급**을 가진 계약이어야 하고, 등급에 따라 탐색에서 쓸 수 있는
권한이 다르다:

    equivalence : 양방향 동치 검증됨 → hard search constraint 가능
    sound_only  : 한 방향만 증명됨 → 증명된 방향으로만 hard constraint 가능
    heuristic   : 보존 정리 없음 → ranking 에만 사용, 후보 제거 절대 금지

이 규칙은 문서가 아니라 **코드로 강제**된다: `assert_usable_for_pruning()` 이
heuristic translation 에 대해 예외를 던지므로, heuristic 으로 후보를 제거하는
코드 경로는 이 레지스트리를 통과할 수 없다.

## 초기 등록

  om-reorientation → boolean-hypercube-coverage (exactness=equivalence)
  — WP1(#38)에서 검증된 동치. encode = evaluate_coverage,
    decode = certificate 독립 검증(통과 시에만 claim 반환).

의존성: 표준 라이브러리 + om_core/reorientation_cover/certificate_verify.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional

EXACTNESS = ("equivalence", "sound_only", "heuristic")


@dataclass(frozen=True)
class Translation:
    name: str
    source_domain: str
    target_domain: str
    exactness: str                       # EXACTNESS 중 하나
    encode: Callable                     # source 객체 → target 표현
    decode: Callable                     # target certificate/결과 → 검증된 source 주장
    obligations: tuple                   # 이 translation 의 검증 의무 (기록용)
    sound_direction: Optional[str] = None  # sound_only 일 때: "encode" 또는 "decode"
    note: str = ""

    def __post_init__(self):
        if self.exactness not in EXACTNESS:
            raise ValueError(f"exactness 는 {EXACTNESS} 중 하나여야 함: {self.exactness}")
        if self.exactness == "sound_only" and self.sound_direction not in ("encode", "decode"):
            raise ValueError("sound_only translation 은 sound_direction 필수")


REGISTRY: dict[str, Translation] = {}


def register(t: Translation) -> Translation:
    if t.name in REGISTRY:
        raise ValueError(f"이미 등록된 translation '{t.name}'")
    REGISTRY[t.name] = t
    return t


def can_hard_constrain(t: Translation, *, direction: str = "encode") -> bool:
    """이 translation 을 hard search constraint(후보 제거)에 써도 되는가.
    equivalence → 항상 가능 / sound_only → 증명된 방향만 / heuristic → 불가."""
    if t.exactness == "equivalence":
        return True
    if t.exactness == "sound_only":
        return direction == t.sound_direction
    return False


def assert_usable_for_pruning(t: Translation, *, direction: str = "encode"):
    """후보 제거 코드 경로의 강제 게이트. heuristic(또는 증명 안 된 방향의
    sound_only)이면 예외 — 조용한 recall 손실을 원천 차단한다."""
    if not can_hard_constrain(t, direction=direction):
        raise PermissionError(
            f"translation '{t.name}' (exactness={t.exactness}"
            f"{', 방향=' + direction if t.exactness == 'sound_only' else ''}) 은 "
            f"후보 제거에 사용할 수 없다 — ranking 전용. 보존 정리를 검증한 뒤 "
            f"exactness 를 승격할 것 (새 DECISIONS 항목 필요).")


# ───────────────────── 초기 등록: coverage 동치 (WP1 검증됨) ─────────────────────
def _encode_coverage(ch):
    from reorientation_cover import evaluate_coverage
    return evaluate_coverage(ch)


def _decode_certificate(cert: dict) -> dict:
    """certificate → 독립 검증 통과 시에만 검증된 주장 반환 (실패 시 예외 전파)."""
    from certificate_verify import verify_certificate
    verify_certificate(cert)
    c = cert["claim"]
    return {"statement": f"nu_OM({c['dimension']}) <= {c['implied_upper_bound']}",
            "trust": "CERTIFIED", "n": c["n"], "rank": c["rank"]}


register(Translation(
    name="om-reorientation->boolean-hypercube-coverage",
    source_domain="oriented-matroid reorientation",
    target_domain="boolean hypercube covering",
    exactness="equivalence",
    encode=_encode_coverage,
    decode=_decode_certificate,
    obligations=("forward_implication", "backward_implication",
                 "small_instance_differential_test", "independent_replay"),
    note="WP1(#38)에서 검증: exhaustive+sampled 14,439건 mismatch 0, "
         "certificate 독립 replay. docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §3.",
))

# 후속 후보 (등록하지 않음 — 수학적 계약 확정 전):
#   om-witness -> SAT/CEGIS            : #39/#40 구현됨, equivalence 승격은 교차 리뷰 후
#   realizable-om -> integer matrix    : realizable 한정 scope
#   reom/lawrence -> rank-2 encoding   : 사용자의 인코딩 형식 확정 대기 (RESEARCH_STATUS §5)
#   minor/tope-graph features          : 보존 정리 없는 동안 heuristic 전용


if __name__ == "__main__":
    from om_core import Chirotope
    from generator import generate_backtracking
    from certificate import build_certificate

    # (1) 초기 translation 등록 확인 + encode 가 legacy 와 일치 (witness/non-witness)
    t = REGISTRY["om-reorientation->boolean-hypercube-coverage"]
    assert t.exactness == "equivalence" and can_hard_constrain(t)
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    assert t.encode(quad).is_witness is False
    wit = next(ch for ch in generate_backtracking(6, 3, dedup=False,
                                                  max_candidates=10**9, max_nodes=10**9)
               if not ch.is_reorientable_to_convex()[0])
    assert t.encode(wit).is_witness is True
    print("coverage translation encode ⟷ legacy 일치 OK")

    # (2) decode: certificate 독립 검증 통과 시에만 주장 반환, 조작 시 예외
    cert = build_certificate(wit, generator="translations-selftest")
    claim = t.decode(cert)
    assert claim == {"statement": "nu_OM(2) <= 5", "trust": "CERTIFIED",
                     "n": 6, "rank": 3}
    import copy
    bad = copy.deepcopy(cert); bad["claim"]["implied_upper_bound"] = 4
    try:
        t.decode(bad); raise AssertionError("조작된 certificate 가 decode 됨")
    except Exception:
        pass
    print("decode = 독립 검증 게이트 OK (조작 certificate 거부)")

    # (3) heuristic 은 후보 제거 불가 — 코드로 강제
    h = Translation(name="tope-graph-degree-heuristic", source_domain="om",
                    target_domain="graph features", exactness="heuristic",
                    encode=lambda ch: None, decode=lambda x: None,
                    obligations=())
    assert not can_hard_constrain(h)
    try:
        assert_usable_for_pruning(h)
        raise AssertionError("heuristic 이 pruning 게이트를 통과")
    except PermissionError as e:
        assert "ranking 전용" in str(e)
    print("heuristic pruning 금지 강제 OK")

    # (4) sound_only 는 증명된 방향만
    s = Translation(name="demo-sound-only", source_domain="a", target_domain="b",
                    exactness="sound_only", encode=lambda x: x, decode=lambda x: x,
                    obligations=(), sound_direction="encode")
    assert can_hard_constrain(s, direction="encode")
    assert not can_hard_constrain(s, direction="decode")
    try:
        assert_usable_for_pruning(s, direction="decode")
        raise AssertionError("sound_only 미증명 방향이 통과")
    except PermissionError:
        pass
    print("sound_only 방향 제한 OK")

    # (5) exactness 어휘/중복 등록 방어
    try:
        Translation(name="x", source_domain="a", target_domain="b",
                    exactness="magic", encode=lambda x: x, decode=lambda x: x,
                    obligations=())
        raise AssertionError("잘못된 exactness 가 통과")
    except ValueError:
        pass
    try:
        register(t); raise AssertionError("중복 등록이 통과")
    except ValueError:
        pass
    print("exactness 어휘 + 중복 등록 방어 OK")

    print("translations core-contract assertions OK "
          "(equivalence/sound_only/heuristic 권한 분리를 코드로 강제)")
