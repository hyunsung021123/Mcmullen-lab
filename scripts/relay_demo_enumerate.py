"""scripts/relay_demo_enumerate.py — computation relay 의 end-to-end 예제 계산.

`computation_relay.py` 가 실제로 무엇을 실행하는지 보여주는 **작지만 진짜인** 전수 계산이다.
plan 은 인라인 코드 뭉치가 아니라 이렇게 **커밋된 스크립트**를 가리켜야 한다 — 그래야
명령이 리뷰 대상이 되고, `result.json` 의 commit 만으로 나중에 그대로 재현된다.

계산 내용: rank r=3 (즉 d=2), n=5 의 모든 부호배정 2^C(5,3) = 2^10 = 1024 개를 전수로
훑어 (a) GP 공리를 통과하는 chirotope 수와 (b) 그중 witness 수를 센다. d=2 는
ν(2) = 2d+1 = 5 로 tight 하므로 **n=5 에서 witness 는 하나도 없어야 한다** — 결과가
0 이 아니면 그건 검증기 쪽 사고다.

판정은 전적으로 `om_core` 가 한다. 이 스크립트는 세는 일만 한다.

산출물은 환경변수 ``MCMULLEN_RELAY_ARTIFACT_DIR`` 이 가리키는 디렉터리에 쓴다
(relay 가 run 디렉터리 안으로 지정한다). 없으면 현재 디렉터리에 쓴다.
"""
from __future__ import annotations

import json
import os
import sys
from itertools import combinations, product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from om_core import Chirotope, mcmullen_evaluate      # noqa: E402


N, R = 5, 3


def _artifact_dir() -> Path:
    path = Path(os.environ.get("MCMULLEN_RELAY_ARTIFACT_DIR", "."))
    path.mkdir(parents=True, exist_ok=True)
    return path


def enumerate_all() -> dict:
    """2^C(N,R) 부호배정 전수. 확인한 개수를 **실제로 센다**(공식으로 채우지 않는다)."""
    bases = list(combinations(range(N), R))
    checked = valid = witnesses = 0
    first_invalid: list[int] | None = None
    for assignment in product((1, -1), repeat=len(bases)):
        checked += 1
        chi = Chirotope(N, R, dict(zip(bases, assignment)))
        if not chi.is_valid():
            if first_invalid is None:
                first_invalid = list(assignment)
            continue
        valid += 1
        if mcmullen_evaluate(chi)["witness"]:
            witnesses += 1
    return {"checked_count": checked, "valid_count": valid,
            "witness_count": witnesses, "first_invalid_assignment": first_invalid,
            "bases": [list(base) for base in bases]}


def controls(first_invalid: list[int] | None) -> list[dict]:
    """oracle 자체에 대한 양성·음성 대조군. 둘 다 om_core 가 판정한다."""
    results = []

    # 양성: 모멘트 곡선 위의 5점은 일반위치이고 d=2 에서 convex 로 재배향 가능해야 한다.
    moment = Chirotope.from_vectors([[1, t, t * t] for t in range(N)])
    evaluated = mcmullen_evaluate(moment)
    results.append({
        "name": "모멘트 곡선 양성 대조",
        "expect": "valid=True, witness=False",
        "observed": f"valid={moment.is_valid()}, witness={evaluated['witness']}",
        "passed": bool(moment.is_valid()) and not evaluated["witness"],
    })

    # 음성: 전수에서 실제로 나온 GP 위반 배정은 반드시 is_valid()=False 여야 한다.
    bases = list(combinations(range(N), R))
    if first_invalid is None:
        results.append({"name": "GP 위반 음성 대조", "expect": "valid=False",
                        "observed": "전수에서 GP 위반 배정이 나오지 않음", "passed": False})
    else:
        broken = Chirotope(N, R, dict(zip(bases, first_invalid)))
        results.append({
            "name": "GP 위반 음성 대조",
            "expect": "valid=False",
            "observed": f"valid={broken.is_valid()}",
            "passed": not broken.is_valid(),
        })
    return results


def main() -> int:
    summary = enumerate_all()
    summary["control_results"] = controls(summary.pop("first_invalid_assignment"))
    summary["scope"] = {"n": N, "r": R, "d": R - 1, "enumeration": "exhaustive"}
    summary["expected_count"] = 2 ** len(summary.pop("bases"))
    out = _artifact_dir() / "enumeration.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "control_results"},
                     ensure_ascii=False, sort_keys=True))
    for control in summary["control_results"]:
        print(f"control {control['name']}: {control['observed']} -> passed={control['passed']}")
    print(f"artifact: {out}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                              # noqa: BLE001 — 표시 계층은 죽지 않는다
        pass
    raise SystemExit(main())
