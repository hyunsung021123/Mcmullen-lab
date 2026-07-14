"""
research_manager.py — opt-in 자율 연구 오케스트레이터 (0026).

(source: chatgpt, relayed by user — "새 부품들을 연결하는 자율 오케스트레이터")

기존 `search.py`/`manager.py`/UI 는 **무변경**이다 — 이 모듈은 새 부품들을 실제로
연결하는 별도 진입점(opt-in)이며, 기존 탐색 경로를 대체하지 않는다.

## 한 라운드의 흐름 (전부 결정론적 게이트, LLM 은 제안만)

    제안  : theorist.run_debate_ir  (LLM/mock → ResearchStep 정규화)
    게이트: process_verifier        (positive / refuted / unverified)
    기록  : evidence_db             (trust 자동 도출, append-only)
    순서  : step_ranker             (positive 만, 실행 순서만 결정)
    실행  : kind 별 결정론적 실행기
              generator_family → cegis_find_witness (CERTIFIED 만 채택)
              necessary_condition → EMPIRICAL 규칙로 다음 라운드 사실에 반영
    unverified 는 버리지 않고 backlog 로 반환한다 (실행기가 생기면 재평가).

witness 는 legacy + certificate 이중 replay 를 통과한 CERTIFIED 등급만 채택된다
(CLAUDE.md §1 — om_core 를 통과하지 않은 것은 witness 가 아니다).

의존성: 위 모듈들 + z3(옵셔널 — 없으면 generator_family 실행기가 비활성).
"""
from __future__ import annotations
import os
import time
from typing import Callable, Optional

from theorist import run_debate_ir, ollama_chat
from step_ranker import rank
from evidence_db import EvidenceDB
from research_ir import to_legacy_bias, StepValidationError

try:
    import z3
except ImportError:
    z3 = None


def run_autonomous_research(d: int, r: int | None = None, *,
                            rounds: int = 2,
                            max_witnesses: int = 1,
                            evidence_path: Optional[str] = None,
                            model: str = "qwen2.5",
                            personas: dict | None = None,
                            llm_fn: Callable = ollama_chat,
                            verbose: bool = True) -> dict:
    """opt-in 자율 연구 루프. 반환 report:
        {"witnesses": [Chirotope...], "certificates": [dict...],
         "backlog": [(step, audit)...],          # unverified — 재평가 대상
         "facts": [str...], "rounds": [...], "evidence_path": str|None}"""
    r = r if r is not None else d + 1
    db = EvidenceDB(evidence_path) if evidence_path else None

    witnesses: list = []
    certificates: list = []
    backlog: list = []
    facts: list[str] = []
    adopted_rules: list[str] = []
    round_reports: list[dict] = []

    def log(msg):
        if verbose:
            print(msg)

    for rd in range(rounds):
        if len(witnesses) >= max_witnesses:
            break
        log(f"[round {rd}] 제안 요청 (사실 {len(facts)}개, 규칙 {len(adopted_rules)}개)")
        debate = run_debate_ir(
            d, r, verified_facts=facts + adopted_rules, findings=[],
            known_witnesses=witnesses, model=model, personas=personas,
            llm_fn=llm_fn)

        # 기록 (trust 는 audit 에서 자동 도출 — 사칭 경로 없음)
        if db is not None:
            for step, audit in (debate["positive"] + debate["unverified"]
                                + debate["refuted"]):
                db.append(step=step, audit=audit, config={"d": d, "r": r, "round": rd})
        backlog.extend(debate["unverified"])

        executed = []
        for step, audit in rank(debate["positive"]):
            kind = step["kind"]
            if kind == "generator_family" and len(witnesses) < max_witnesses:
                if z3 is None:
                    executed.append((step["id"], "skipped: z3 미설치"))
                    continue
                try:
                    n = to_legacy_bias(step)["spec"]["n"]
                except (StepValidationError, KeyError):
                    executed.append((step["id"], "skipped: n 추출 불가"))
                    continue
                from cegis_search import cegis_find_witness
                t0 = time.perf_counter()
                out = cegis_find_witness(n, r, known_witnesses=witnesses)
                dt = time.perf_counter() - t0
                executed.append((step["id"], f"cegis(n={n}) → {out.status} ({dt:.1f}s)"))
                if out.status == "CERTIFIED_WITNESS":
                    witnesses.append(out.chirotope)
                    certificates.append(out.certificate)
                    facts.append(f"n={n} 에서 CERTIFIED witness 발견 (상한 {n - 1})")
                    if db is not None:
                        db.append(step=step, audit=audit, certificate_verified=True,
                                  config={"d": d, "r": r, "round": rd, "n": n},
                                  runtime_s=dt)
                elif out.status == "EXHAUSTED":
                    facts.append(f"n={n} 에는 witness 없음 (CEGIS 소진 증명, unknown 0)")
                elif out.status == "INCONCLUSIVE_WITH_UNKNOWN":
                    facts.append(f"n={n} 판정 불능 (solver unknown 존재 — 결론 금지)")
            elif kind == "necessary_condition":
                # positive = 소규모 witness pool 검사 통과 (EMPIRICAL) — 다음 라운드
                # 제안 맥락에 반영하되 hard pruning 으로는 쓰지 않는다 (translations
                # 의 heuristic 규율과 동일 원칙).
                rule = f"EMPIRICAL 규칙: {step['claim']['dsl']}"
                if rule not in adopted_rules:
                    adopted_rules.append(rule)
                executed.append((step["id"], "EMPIRICAL 규칙로 채택 (pruning 아님)"))
            else:
                executed.append((step["id"], f"실행기 없음(kind={kind}) — backlog"))
                backlog.append((step, audit))
        round_reports.append({
            "round": rd, "executed": executed,
            "counts": {k: len(debate[k]) for k in
                       ("positive", "unverified", "refuted", "malformed")}})
        log(f"[round {rd}] 실행 {len(executed)}건, witness 누계 {len(witnesses)}")

    return {"witnesses": witnesses, "certificates": certificates,
            "backlog": backlog, "facts": facts, "adopted_rules": adopted_rules,
            "rounds": round_reports,
            "evidence_path": evidence_path}


if __name__ == "__main__":
    import json
    import tempfile

    if z3 is None:
        print("SKIP: z3 미설치 — 오케스트레이터 자체 테스트를 건너뜀")
        raise SystemExit(0)

    # mock LLM: 역할별로 서로 다른 종류의 제안 (Ollama 불필요 — 결정론)
    canned = {
        "geometer": {"legacy_bias": {"type": "element_count", "spec": {"n": 6}},
                     "rationale_summary": "d=2 목표상한+1 지점"},
        "om_expert": {"legacy_bias": {"type": "require_property",
                                      "spec": {"name": "acyclic"}},
                      "rationale_summary": "witness 는 acyclic 대표를 갖는다는 가설"},
        "sat_expert": {"kind": "equivalence",
                       "claim_dsl": "witness(chi) iff covers_hypercube(chi)",
                       "scope": {"rank": 3}, "rationale_summary": "coverage 동치"},
        "graph_expert": {"legacy_bias": {"type": "require_property",
                                         "spec": {"name": "tope_graph_regular"}},
                         "rationale_summary": "미등록 성질 제안"},
        "combinatorialist": "이건 JSON 이 아님",   # 정규화 실패 케이스
    }

    def mock_llm(model, system, user):
        from theorist import PROPOSER_ROLES
        role = next(k for k, v in PROPOSER_ROLES.items() if v == system)
        out = canned[role]
        return out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)

    with tempfile.TemporaryDirectory() as tmp:
        ev_path = os.path.join(tmp, "evidence.jsonl")
        report = run_autonomous_research(2, 3, rounds=1, max_witnesses=1,
                                         evidence_path=ev_path, llm_fn=mock_llm,
                                         verbose=True)

        # (1) 자율 루프가 CERTIFIED witness 를 실제로 만들었는가
        assert len(report["witnesses"]) == 1
        assert report["certificates"][0]["claim"]["implied_upper_bound"] == 5
        # (2) equivalence(실행기 없음)와 미등록 성질은 폐기가 아니라 backlog
        kinds = [s["kind"] for s, _ in report["backlog"]]
        assert "equivalence" in kinds and "necessary_condition" in kinds
        # (3) 정규화 실패는 malformed 로 격리 (루프 중단 없음)
        assert report["rounds"][0]["counts"]["malformed"] == 1
        # (4) EMPIRICAL 규칙 채택 (acyclic 필요조건 — pool 검사 통과 시)
        #     hard pruning 이 아님을 report 가 명시
        # (5) evidence: trust 자동 도출로 기록됨 + 개찬 없음
        db = EvidenceDB(ev_path)
        recs = list(db.iter_records())
        assert db.verify_chain() == len(recs) >= 5
        trusts = {rec["trust_status"] for rec in recs}
        assert "UNVERIFIED" in trusts and "CERTIFIED" in trusts
        print(f"evidence {len(recs)}건 (trust: {sorted(trusts)})")

    print("research_manager core-contract assertions OK "
          "(자율 루프 end-to-end: 제안→게이트→기록→순위→CEGIS→CERTIFIED)")
