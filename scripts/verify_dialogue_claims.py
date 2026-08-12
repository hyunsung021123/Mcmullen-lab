"""scripts/verify_dialogue_claims.py — 자율 토론 루프 주장 중 **값싸게 재현되는 것**만 검증한다.

`knowledge/dialogue_research/` 의 기록은 전부 `UNASSESSED_DIALOGUE_ONLY` 다. 그 안에서
일부 주장은 몇 초 안에 결정론적으로 재현되고, 일부는 큰 계산이나 별도 구현이 필요하다.
이 스크립트는 **전자만** 다룬다 — 그리고 무엇을 검증하지 **않았는지** 명시적으로 출력한다.
"검증했다"와 "검증 안 했다"를 섞는 것이 이 프로젝트에서 가장 위험한 실패이기 때문이다.

판정은 전부 `om_core` 와 `reorientation_cover` 가 한다. 이 스크립트는 세고 비교만 한다.

    python scripts/verify_dialogue_claims.py

실패하면 종료 코드 1. CI 에 넣어도 되지만 주장 A 는 792 x 2^11 규모라 수십 초 걸린다.
"""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from om_core import Chirotope                                  # noqa: E402
from reorientation_cover import bad_reorientation_mask         # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                              # noqa: BLE001
    pass

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def claim_a_mask_capacity() -> None:
    """주장 A — rank-6, n=12 의 모든 circuit bad mask 크기가 정확히 256.

    이것이 '8-cover 는 반드시 exact partition' 이라는 용량 강성의 근거이고, 거기서
    'circuit obstruction cover 에는 최소 9개가 필요' 라는 하한 논증이 출발한다.
    """
    n, r = 12, 6
    print("\n주장 A — 모든 circuit bad mask 크기 = 256, 그리고 2^(n-1) = 8 x 256")
    chi = Chirotope.from_vectors([[t ** k for k in range(r)] for t in range(n)])
    check("기저 chirotope 가 유효한 uniform OM", chi.is_valid() is True,
          f"모멘트 곡선 n={n}, r={r}")

    supports = list(combinations(range(n), r + 1))
    sizes: dict[int, int] = {}
    for S in supports:
        sizes[bin(bad_reorientation_mask(chi, S)).count("1")] = \
            sizes.get(bin(bad_reorientation_mask(chi, S)).count("1"), 0) + 1
    check("mask 크기가 전부 256", set(sizes) == {256},
          f"C({n},{r + 1})={len(supports)}개 support, 크기 분포={sizes}")

    cube = 1 << (n - 1)
    check("gauge-fixed cube = 2048", cube == 2048)
    check("2048 = 8 x 256 (여유 0 → 8-cover 는 exact partition 강제)",
          cube == 8 * 256, f"{cube} / 256 = {cube // 256}")
    # STATE.md §2 의 '용량비 99배' 와 대조 — 총 용량은 남아도는데 최소 개수는 8이 안 된다.
    ratio = len(supports) * 256 / cube
    check("총 용량비 = 99.0배 (STATE.md §2 와 일치)", abs(ratio - 99.0) < 1e-9,
          f"{len(supports)} x 256 / {cube} = {ratio}")


def claim_b_bound_parity() -> None:
    """주장 B — 옛 식 2d+floor((1+d)/2) 는 홀수 d 에서 상한이 아니라 witness 크기다."""
    print("\n주장 B — U(d)=floor(5d/2) vs M(d)=U+1, 옛식 - U = d mod 2  (0042 로 정정됨)")
    rows = []
    ok = True
    for d in range(1, 12):
        old = 2 * d + (1 + d) // 2
        U = (5 * d) // 2
        ok &= (old - U == d % 2)
        rows.append((d, old, U, U + 1, old - U))
    check("d=1..11 전 범위에서 옛식 - U(d) = d mod 2", ok)
    print("      d  옛식  U(d)  M(d)  차이")
    for d, old, U, M, diff in rows:
        star = "  <- 어긋남" if diff else ""
        print(f"      {d:>2} {old:>5} {U:>5} {M:>5} {diff:>5}{star}")
    # reward = (U+1) - n 이므로 n = M(d) 는 개선이 아니다.
    check("n = M(d) 에서 reward 0 (고전 구성은 개선이 아니다)",
          all((5 * d) // 2 + 1 - ((5 * d) // 2 + 1) == 0 for d in range(1, 12)))
    check("개선 구간은 2d+2 <= U(d), 즉 d>=4 에서만 열린다",
          [d for d in range(2, 12) if 2 * d + 2 <= (5 * d) // 2] == list(range(4, 12)),
          "d=2,3 은 하한 2d+1 = U(d) 로 tight")


NOT_VERIFIED = [
    ("240개 canonical Stage A 해의 전수 열거와 전원 GP 탈락",
     "코덱스의 두 독립 구현이 일치했다는 것이 현재 근거. 재현에는 exact-cover DFS 구현이 필요"),
    ("240 해 ↔ P^1(F_7) Paley tournament 궤도 동일성 (120 keys, class 당 금지 quadruple 28개)",
     "dual pair signing + normalized triple signature 구현과 8! 궤도 비교가 필요"),
    ("QQ-0002 의 rank-2 layer union 실현 정리와 명시적 t 하한",
     "증명 사슬은 문서 감사 대상. 저장소 구현은 여전히 후보별 om_core certificate 경로를 쓴다"),
    ("QQ-0003 의 혼합 rank 조성 properness (n=4,5,6 전수)와 reversal 보조정리",
     "조성별 정규화 chirotope 열거 구현이 필요"),
    ("접합 귀납의 조건부 정리 T0--T7 과 2,2,2,3 slope",
     "조건부 진술이며 전제(one-step operator G)가 아직 구현되지 않았다"),
]


def main() -> int:
    print("=" * 74)
    print("자율 토론 루프 주장 검증 — knowledge/dialogue_research/ 의 일부만 다룬다")
    print("=" * 74)
    claim_a_mask_capacity()
    claim_b_bound_parity()

    print("\n" + "=" * 74)
    print("이 스크립트가 검증하지 **않은** 주장 (근거 등급을 올리지 말 것)")
    print("=" * 74)
    for claim, why in NOT_VERIFIED:
        print(f"  · {claim}\n      왜: {why}")

    print("\n" + "=" * 74)
    if failures:
        print(f"실패 {len(failures)}건: {failures}")
        return 1
    print("검증한 주장 전부 통과 (A: mask 용량 강성, B: U/M parity)")
    print("나머지는 위 목록대로 미검증 — 승격에는 영속 replay artifact 가 필요하다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
