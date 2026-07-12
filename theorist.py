"""
theorist.py — 다중 전문가 '토론' + 결정론적 반례 사냥/증명 검사. 리뷰 지적 ①②③ 반영.

구조(요청하신 '다분야 전문가 토론', 단일 통합모델 아님):
  제안자(LLM, 서로 다른 역할):
     geometer · combinatorialist · om_expert · graph_expert · sat_expert
  적대자(결정론적 코드 — 여기가 핵심):
     counterexample_hunter : 제안된 편향이 '이미 검증된 witness'를 버리게 되는지 실제로 확인
     proof_checker         : 기계적 검증 가능성 + 공허성 + 장기기억(과거 실패) 게이트

여러 라운드로 진행하며, 각 라운드의 '기각 사유(critique)'가 다음 라운드 제안자에게 전달돼
제안이 수정된다(단발 제안이 아니라 상호작용). LLM 은 방향만 제안하고, 채택 여부는 코드가 정한다.

의존성: requests(Ollama). 미설치/미가동이어도 import 안전. LLM 없이도 vet_biases()는 동작
        (Discovery Engine 의 제안 편향을 게이트/반례로 걸러 학습 루프에 쓰인다).
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass
from typing import Callable, Optional

try:
    import requests
except ImportError:
    requests = None

from om_core import Chirotope
from criteria import REGISTRY
from generator import generate_backtracking

OLLAMA_URL = "http://localhost:11434/api/chat"

PROPOSER_ROLES = {
    "geometer": "당신은 이산기하 전문가다. Radon/Tverberg, 사영변환 불변량, 일반위치 직관으로 "
                "'어떤 구조가 재배향으로도 convex 가 안 되게 하는가'를 제안하라.",
    "combinatorialist": "당신은 조합론 전문가다. 부분구조 개수·대칭·극단조합 관점에서 "
                        "탐색을 좁힐 성질을 제안하라.",
    "om_expert": "당신은 유향 매트로이드 전문가다. circuit/cocircuit 부호, 재배향류, "
                 "Lawrence 구성 관점의 성질을 제안하라.",
    "graph_expert": "당신은 그래프 이론 전문가다. tope/cocircuit 그래프의 구조로 "
                    "구별 성질을 제안하라.",
    "sat_expert": "당신은 SAT/SMT 인코딩 전문가다. 탐색 공간을 줄일 대칭 파괴/고정 제약을 "
                  "기준 형태로 제안하라.",
}

PROPOSAL_SCHEMA = """반드시 이 JSON 으로만 답하라(자유서술 금지):
{
 "conjecture": "검증 가능한 한 문장",
 "rationale": "간결한 근거",
 "search_bias": {
    "type": "element_count | require_property | forbid_property",
    "spec": {}
 },
 "confidence": 0.0
}
spec 형식: element_count -> {"n":int} / *_property -> {"name":"<REGISTRY 기준>","args":[..]}"""


@dataclass
class Proposal:
    role: str
    conjecture: str = ""
    bias: Optional[dict] = None
    rationale: str = ""
    confidence: float = 0.0
    status: str = "unverified"
    critique: str = ""

    def as_dict(self):
        return {"role": self.role, "conjecture": self.conjecture, "bias": self.bias,
                "confidence": self.confidence, "status": self.status,
                "critique": self.critique}


def ollama_chat(model: str, system: str, user: str) -> str:
    if requests is None:
        raise RuntimeError("requests 미설치. pip install requests 후 Ollama 사용.")
    payload = {"model": model, "stream": False, "format": "json",
               "options": {"temperature": 0.7},
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}]}
    r = requests.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"]


def parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group()) if m else {}


# ───────────────────────── 결정론적 적대자 ─────────────────────────
def _criterion_holds(name: str, args: list, ch: Chirotope) -> bool:
    crit = REGISTRY[name](*args) if args else REGISTRY[name]()
    return crit.holds(ch)


def proof_checker(bias: dict, d: int, r: int, memory=None,
                  fail_threshold: int = 5) -> tuple[bool, str]:
    """기계적 검증 가능성 + 공허성 + 장기기억(반복 실패) 게이트."""
    if not isinstance(bias, dict):
        return False, "bias 형식 아님"
    btype = bias.get("type"); spec = bias.get("spec", {})
    if btype == "element_count":
        n = spec.get("n")
        if not isinstance(n, int) or not (r + 1 <= n <= 2 * d + 4):
            return False, f"n 범위 밖: {n}"
        return True, f"element_count n={n}"
    if btype in ("require_property", "forbid_property"):
        name = spec.get("name"); args = spec.get("args", [])
        if name not in REGISTRY:
            return False, f"미등록 기준 '{name}'"
        if memory is not None and memory.bias_failed_count(bias) >= fail_threshold:
            return False, f"장기기억: {memory.bias_failed_count(bias)}회 실패한 편향"
        mode = "require" if btype == "require_property" else "forbid"
        try:
            from criteria import CriteriaSet
            cs = CriteriaSet.from_config([{"name": "valid"},
                                          {"name": name, "mode": mode, "args": args}])
            ref_n = min(2 * d + 2, r + 2)
            ok = next(generate_backtracking(ref_n, r,
                                            accept=lambda ch: cs.evaluate(ch).accepted,
                                            dedup=False, max_candidates=1,
                                            max_nodes=200_000), None)
            if ok is None:
                return False, f"공허: n={ref_n} 에서 통과 후보 없음"
        except Exception as e:
            return False, f"검증 오류: {e}"
        return True, f"{btype}:{name}{args or ''}"
    return False, f"알 수 없는 type '{btype}'"


def counterexample_hunter(bias: dict, known_witnesses: list) -> Optional[str]:
    """편향이 '이미 검증된 witness'를 배제하게 되는지 실제 확인. 그러면 그 witness 가 반례."""
    if not isinstance(bias, dict) or not known_witnesses:
        return None
    btype = bias.get("type"); spec = bias.get("spec", {})
    if btype not in ("require_property", "forbid_property"):
        return None
    name = spec.get("name"); args = spec.get("args", [])
    if name not in REGISTRY:
        return None
    for w in known_witnesses:
        holds = _criterion_holds(name, args, w)
        if btype == "require_property" and not holds:
            return f"witness(n={w.n}) 는 '{name}' 불만족 → require 시 실제 witness 배제"
        if btype == "forbid_property" and holds:
            return f"witness(n={w.n}) 는 '{name}' 만족 → forbid 시 실제 witness 배제"
    return None


# ───────────────────────── 편향 심사(게이트+반례) ─────────────────────────
def vet_biases(biases: list, d: int, r: int, *, memory=None,
               known_witnesses: list | None = None) -> dict:
    """후보 편향들을 게이트+반례로 심사, 통과분만 승격. (LLM 유무 무관; Discovery 제안에도 사용)"""
    promoted, criteria_add, rejected = [], [], []
    next_n = None; seen = set()
    for bias in biases:
        if not bias:
            continue
        sig = (bias.get("type"), str(bias.get("spec")))
        if sig in seen:
            continue
        seen.add(sig)
        ok, reason = proof_checker(bias, d, r, memory)
        if not ok:
            rejected.append({"bias": bias, "reason": reason})
            if memory is not None:
                memory.record_bias(bias, promoted=False, reason=reason)
            continue
        cx = counterexample_hunter(bias, known_witnesses or [])
        if cx:
            rejected.append({"bias": bias, "reason": cx})
            if memory is not None:
                memory.record_bias(bias, promoted=False, reason=cx)
            continue
        promoted.append({"bias": bias, "gate_reason": reason})
        if memory is not None:
            memory.record_bias(bias, promoted=True, reason=reason)
        btype = bias["type"]; spec = bias.get("spec", {})
        if btype == "element_count":
            next_n = spec["n"]
        elif btype == "require_property":
            criteria_add.append({"name": spec["name"], "mode": "require",
                                 "args": spec.get("args", [])})
        elif btype == "forbid_property":
            criteria_add.append({"name": spec["name"], "mode": "forbid",
                                 "args": spec.get("args", [])})
    return {"promoted": promoted, "criteria_add": criteria_add,
            "next_n_override": next_n, "rejected": rejected}


# ───────────────────────────── 다중 라운드 토론 ─────────────────────────────
def run_debate(d: int, r: int, *, verified_facts: list, findings: list,
               memory=None, known_witnesses: list | None = None,
               model: str = "qwen2.5", rounds: int = 2,
               llm_fn: Callable[[str, str, str], str] = ollama_chat) -> dict:
    """제안자 LLM 들이 여러 라운드로 제안·수정하고, 결정론적 적대자가 매 라운드 반박."""
    mem_lines = memory.summary_for_committee() if memory else []
    find_lines = [f"{f['invariant']}={f['value']} ({f['kind']}, {f['support']})"
                  for f in findings]
    base_ctx = (f"문제: d={d}, rank={r}. 목표는 '어떤 재배향으로도 convex 가 안 되는' "
                f"uniform OM 을 최소 n 으로.\n"
                f"검증된 사실: {verified_facts or '없음'}\n"
                f"Discovery(검증 데이터 기반): {find_lines or '없음'}\n"
                f"장기기억: {mem_lines or '없음'}\n")

    transcript = []; critiques: list = []; survived: list = []
    for rd in range(rounds):
        ctx = base_ctx
        if critiques:
            ctx += ("\n지난 라운드 기각 사유(피해서 수정 제안):\n- " +
                    "\n- ".join(critiques[-8:]) + "\n")
        ctx += "\n" + PROPOSAL_SCHEMA

        proposals: list[Proposal] = []
        for role, persona in PROPOSER_ROLES.items():
            try:
                out = parse_json(llm_fn(model, persona, ctx))
                p = Proposal(role=role, conjecture=out.get("conjecture", ""),
                             bias=out.get("search_bias"),
                             rationale=out.get("rationale", ""),
                             confidence=float(out.get("confidence", 0.0)))
            except Exception as e:
                p = Proposal(role=role, conjecture=f"(호출 실패: {e})")
            proposals.append(p)

        critiques = []
        for p in proposals:
            if not p.bias:
                p.status = "rejected"; p.critique = "편향 없음"; continue
            ok, reason = proof_checker(p.bias, d, r, memory)
            if not ok:
                p.status = "rejected"; p.critique = f"proof_checker: {reason}"
                critiques.append(f"[{p.role}] {p.critique}")
                if memory is not None:
                    memory.record_bias(p.bias, promoted=False, reason=reason)
                continue
            cx = counterexample_hunter(p.bias, known_witnesses or [])
            if cx:
                p.status = "rejected"; p.critique = f"counterexample_hunter: {cx}"
                critiques.append(f"[{p.role}] {p.critique}")
                if memory is not None:
                    memory.record_bias(p.bias, promoted=False, reason=cx)
                continue
            p.status = "survived"; survived.append(p.bias)

        transcript.append({"round": rd, "proposals": [p.as_dict() for p in proposals]})

    result = vet_biases(survived, d, r, memory=memory, known_witnesses=known_witnesses)
    result["transcript"] = transcript
    return result


if __name__ == "__main__":
    import random
    from om_core import mcmullen_evaluate
    random.seed(3); wit = None
    while wit is None:
        pts = [tuple(random.randint(-9, 9) for _ in range(3)) for _ in range(8)]
        try:
            ch = Chirotope.from_points(pts)
        except ValueError:
            continue
        if mcmullen_evaluate(ch)["witness"]:
            wit = ch
    canned = {
        "geometer": {"conjecture": "acyclic 필요", "confidence": 0.8,
                     "search_bias": {"type": "require_property", "spec": {"name": "acyclic"}}},
        "combinatorialist": {"conjecture": "convex 여야", "confidence": 0.6,
                             "search_bias": {"type": "require_property",
                                             "spec": {"name": "convex_position"}}},
        "om_expert": {"conjecture": "n=8 시도", "confidence": 0.7,
                      "search_bias": {"type": "element_count", "spec": {"n": 8}}},
        "graph_expert": {"conjecture": "엉터리", "confidence": 0.3,
                         "search_bias": {"type": "require_property", "spec": {"name": "nonexistent"}}},
        "sat_expert": {"conjecture": "valid 금지", "confidence": 0.2,
                       "search_bias": {"type": "forbid_property", "spec": {"name": "valid"}}},
    }
    def mock_llm(model, system, user):
        role = next(k for k, v in PROPOSER_ROLES.items() if v == system)
        return json.dumps(canned[role])
    res = run_debate(3, 4, verified_facts=["n=8 witness 존재"], findings=[],
                     known_witnesses=[wit], rounds=2, llm_fn=mock_llm)
    print(f"라운드 {len(res['transcript'])}회, 승격 {len(res['promoted'])}개")
    for p in res["transcript"][0]["proposals"]:
        print(f"  [{p['role']:16}] {p['status']:9} {p['critique']}")
    print("promoted:", [b["bias"] for b in res["promoted"]])
    print("criteria_add:", res["criteria_add"], "| next_n:", res["next_n_override"])

    # core-contract: 결정론적 적대자가 매 라운드 동일 입력에 동일 판정을 내리는지 고정.
    # (ChatGPT 리뷰 0006 반영 — 이전엔 출력만 하고 어느 것도 assert하지 않았다.)
    status_by_role = {p["role"]: p["status"] for p in res["transcript"][0]["proposals"]}
    assert status_by_role["geometer"] == "survived"        # acyclic require: witness가 만족
    assert status_by_role["combinatorialist"] == "rejected"  # counterexample_hunter가 배제
    assert status_by_role["om_expert"] == "survived"       # element_count 범위 안
    assert status_by_role["graph_expert"] == "rejected"    # 미등록 REGISTRY 이름
    assert status_by_role["sat_expert"] == "rejected"      # forbid(valid) → 공허
    assert len(res["promoted"]) == 2
    assert res["criteria_add"] == [{"name": "acyclic", "mode": "require", "args": []}]
    assert res["next_n_override"] == 8
    print("core-contract assertions OK (결정론적 적대자 판정 고정)")
