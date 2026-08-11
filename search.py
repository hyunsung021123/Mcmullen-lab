"""
search.py — Discovery Loop 오케스트레이션 (연구 루프). 리뷰 지적 ①~⑤ 반영.

한 라운드:
  generate(클래스 탐색공간, 현재 n, 활성 기준으로 조기필터)
    → 각 후보 결정론적 검증 + 기준 리포트 → witness/채택분 기록 (+ 탈락 사유 집계)
  Discovery Engine 이 검증된 witness/non-witness 구조를 분석 → 발견 + 제안 편향
  제안 편향(및 LLM 토론 편향) → 게이트+반례 심사 → 통과분만 기준/ n 반영  (학습 루프)
  장기기억 갱신(제너레이터/기준/조합/실패). 상한 2d+1 도달 시 조기 종료.

신뢰 경계 불변: '발견'은 om_core 검증 통과분만. LLM/Discovery 는 검증 게이트+반례를 통과한
편향만 탐색에 반영. 적대자(반례 사냥/증명 검사)는 결정론적 코드.
"""
from __future__ import annotations
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional, Callable

from om_core import Chirotope, mcmullen_evaluate
from criteria import CriteriaSet
from om_classes import CLASS_REGISTRY, class_generator
from store import ResultsStore, RoundRecord
from progress import Progress, Control
from discovery import DiscoveryEngine
from theorist import vet_biases
from memory import Memory


@dataclass
class SearchConfig:
    d: int
    om_class: str = "uniform"
    n_min: int | None = None
    n_max: int | None = None
    U: int | None = None
    backend: str | None = None
    criteria: list[dict] = field(default_factory=list)
    dedup: bool = True
    max_candidates_per_round: int = 200
    record_accepted: bool = True
    accepted_cap: int = 50
    rounds: int = 6
    seed: int | None = None
    # custom class 전용 옵션. accept/max_candidates/dedup/seed는 오케스트레이터가 소유한다.
    class_options: dict = field(default_factory=dict)
    # 연구 루프
    discovery_enabled: bool = True
    memory_path: str | None = None       # 설정 시 장기기억 로드/갱신/저장
    bias_fail_threshold: int = 5
    # LLM 토론
    llm_enabled: bool = False
    llm_model: str = "qwen2.5"
    debate_rounds: int = 2
    llm_personas: dict[str, str] = field(default_factory=dict)  # role -> 커스텀 system prompt

    def resolve(self):
        if self.om_class not in CLASS_REGISTRY:
            raise KeyError(f"알 수 없는 클래스 '{self.om_class}'. 사용 가능: {sorted(CLASS_REGISTRY)}")
        if not isinstance(self.class_options, dict):
            raise TypeError("class_options는 mapping이어야 함")
        reserved = {"accept", "max_candidates", "dedup", "seed"}
        overlap = reserved.intersection(self.class_options)
        if overlap:
            raise ValueError(f"class_options가 예약된 생성기 옵션을 덮어씀: {sorted(overlap)}")
        oc = CLASS_REGISTRY[self.om_class]
        if self.class_options and oc.backend != "custom":
            raise ValueError("class_options는 custom 탐색 class에서만 사용할 수 있음")
        if self.backend is not None and oc.backend == "custom":
            raise ValueError("custom 탐색 class에는 generic backend override를 사용할 수 없음")
        r = oc.resolve_rank(self.d)
        d_eff = r - 1
        self._r = r; self._d_eff = d_eff
        U_loose = 2 * d_eff + (1 + d_eff) // 2
        if self.U is None:
            self.U = U_loose
        if self.n_min is None:
            self.n_min = max(r + 1, 2 * d_eff + 2)
        if self.n_max is None:
            self.n_max = self.U + 1
        merged = list(oc.base_criteria) + list(self.criteria)
        if not any(c.get("name") == "valid" for c in merged):
            merged = [{"name": "valid", "mode": "require"}] + merged
        self.criteria = merged
        return r


def _witness_chirotopes(store: ResultsStore, cap: int = 25) -> list[Chirotope]:
    out = []
    for rec in store.results:
        if rec.is_witness:
            out.append(Chirotope.from_dict(rec.chirotope))
            if len(out) >= cap:
                break
    return out


def _nonwitness_chirotopes(store: ResultsStore, cap: int = 25) -> list[Chirotope]:
    out = []
    for rec in store.results:
        if not rec.is_witness:
            out.append(Chirotope.from_dict(rec.chirotope))
            if len(out) >= cap:
                break
    return out


def run_search(cfg: SearchConfig, out_path: str = "results.json", verbose: bool = True,
               reporter: Optional[Callable[[Progress], None]] = None,
               control: Optional[Control] = None,
               memory: Optional[Memory] = None) -> ResultsStore:
    r = cfg.resolve()
    d_eff = cfg._d_eff
    oc = CLASS_REGISTRY[cfg.om_class]

    if memory is None and cfg.memory_path:
        memory = Memory(cfg.memory_path)
    disco = DiscoveryEngine() if cfg.discovery_enabled else None

    store = ResultsStore({
        "d": d_eff, "requested_d": cfg.d, "r": r, "U": cfg.U,
        "om_class": cfg.om_class, "om_class_note": oc.note,
        "om_class_realizable": oc.realizable,
        "n_min": cfg.n_min, "n_max": cfg.n_max,
        "backend": cfg.backend or oc.backend,
        "seed": cfg.seed, "class_options": dict(cfg.class_options),
        "llm_enabled": cfg.llm_enabled, "llm_model": cfg.llm_model,
        "debate_rounds": cfg.debate_rounds, "discovery_enabled": cfg.discovery_enabled,
        "rounds": cfg.rounds, "criteria_active": cfg.criteria,
        "memory_summary": memory.summary_for_committee() if memory else [],
    })

    target_bound = 2 * d_eff + 1
    promoted_biases: list[dict] = []
    current_criteria = list(cfg.criteria)
    n = cfg.n_min

    prog = Progress(); prog.state = "running"
    start = time.time(); last_report = [0.0]

    def push(force=False, msg=None):
        prog.elapsed = time.time() - start
        if msg:
            prog.message = msg; prog.log.append(f"[{prog.elapsed:6.1f}s] {msg}")
            del prog.log[:-200]
        now = time.time()
        if reporter and (force or now - last_report[0] > 0.15):
            last_report[0] = now; reporter(prog)
        if verbose and msg:
            print(msg)

    llm_debate = None
    if cfg.llm_enabled:
        from theorist import run_debate
        llm_debate = run_debate

    push(force=True, msg=f"시작: class={cfg.om_class} rank={r} (d_eff={d_eff}) "
                         f"목표상한={target_bound} 토론={'on' if llm_debate else 'off'} "
                         f"discovery={'on' if disco else 'off'}")

    # 트랙터빌리티 경고 (0029 — ui_helpers.feasibility_warnings 에서 이관).
    # 정성적 경고만 한다: 예상 소요 시간을 약속하지 않는다.
    backend_effective = cfg.backend or oc.backend
    if backend_effective == "backtracking" and d_eff >= 4 and cfg.n_max >= 10:
        push(force=True, msg=(
            f"  ⚠ rank {r}, n={cfg.n_max} 까지의 모든 uniform OM 을 백트래킹으로 전수 "
            f"생성하는 것은 현실적이지 않습니다 (README §10). 구조적 seed(cyclic) 또는 "
            f"z3/cegis 백엔드를 검토하세요."))

    stopped = False
    for rnd in range(cfg.rounds):
        # 기준 중복 제거(학습 루프가 같은 기준을 다시 추가할 수 있음)
        _seen, _dd = set(), []
        for c in current_criteria:
            k = (c["name"], c.get("mode", "require"), tuple(c.get("args", [])))
            if k not in _seen:
                _seen.add(k); _dd.append(c)
        current_criteria = _dd
        cs = CriteriaSet.from_config(current_criteria)
        store.run["criteria_active"] = cs.active_summary()
        fail_counter: Counter = Counter()

        def accept(ch):
            rep = cs.evaluate(ch)
            if not rep.accepted:
                fail_counter[rep.failed[0] if rep.failed else "?"] += 1
            return rep.accepted

        prog.round = rnd; prog.n = n
        push(force=True, msg=f"round {rnd}: n={n} 탐색 시작 (기준 {len(current_criteria)}개)")

        pre = len(store.results)
        round_results = []
        accepted_recorded = 0
        gen_kw = dict(accept=accept, dedup=cfg.dedup,
                      max_candidates=cfg.max_candidates_per_round)
        if cfg.seed is not None:
            gen_kw["seed"] = cfg.seed
        gen_kw.update(cfg.class_options)

        for ch in class_generator(cfg.om_class, n, r,
                                  backend_override=cfg.backend, **gen_kw):
            if control is not None and not control.checkpoint():
                stopped = True
                push(force=True, msg="중단 요청 — 부분 결과 저장 중")
                break
            ev = mcmullen_evaluate(ch, U=cfg.U)
            rep = cs.evaluate(ch)
            round_results.append({"witness": ev["witness"], "n": ch.n})
            prog.candidates += 1; prog.accepted += 1
            if ev["witness"] or (cfg.record_accepted and accepted_recorded < cfg.accepted_cap):
                rec = store.add_result(ch, ev, rep, promoted_biases=list(promoted_biases))
                if not ev["witness"]:
                    accepted_recorded += 1
                if ev["witness"]:
                    prog.witnesses += 1
                    ub = ev["implied_upper_bound"]
                    if prog.best_upper_bound is None or ub < prog.best_upper_bound:
                        prog.best_upper_bound = ub
                        prog.best_config = {"id": rec.id, "n": rec.n,
                                            "implied_upper_bound": ub,
                                            "criteria_satisfied": rec.criteria_satisfied,
                                            "reward": rec.reward}
                        push(force=True, msg=f"  ★ 새 최선: n={rec.n} → 상한 {ub}")
            push()

        # ---------- 라운드 후: 발견 · 실패분석 · 학습 · 토론 · 기억 ----------
        new_recs = store.results[pre:]
        num_wit_round = sum(1 for x in round_results if x["witness"])
        best = store.best_witness()

        witnesses_ch = _witness_chirotopes(store)
        nonwit_ch = _nonwitness_chirotopes(store)
        witness_ids = [rec.id for rec in store.results if rec.is_witness][:len(witnesses_ch)]
        findings = (disco.analyze(witnesses_ch, nonwit_ch, witness_ids=witness_ids)
                    if disco else [])
        finding_dicts = [f.as_dict() for f in findings]
        failures = dict(fail_counter.most_common(5))
        if failures:
            push(force=True, msg="  · 탈락 사유: " +
                 ", ".join(f"{k}×{v}" for k, v in failures.items()))
        if finding_dicts:
            push(force=True, msg="  · 발견: " +
                 "; ".join(f"{f['invariant']}={f['value']}({f['kind']})"
                           for f in finding_dicts[:4]))

        # 학습 루프(LLM 무관): Discovery 제안 편향을 게이트+반례로 심사 후 반영
        suggested = [f["suggested_bias"] for f in finding_dicts if f.get("suggested_bias")]
        vet = vet_biases(suggested, d_eff, r, memory=memory, known_witnesses=witnesses_ch)
        current_criteria += vet["criteria_add"]
        promoted_biases.extend(vet["promoted"])

        # LLM 토론(선택)
        debate_transcript = None
        next_n = min(n + 1, cfg.n_max)
        if llm_debate is not None:
            facts = ([f"n={best.n} witness → 상한 ≤ {best.implied_upper_bound}"] if best else []) + \
                    ([f"탈락 사유 {failures}"] if failures else [])
            res = llm_debate(d_eff, r, verified_facts=facts, findings=finding_dicts,
                             memory=memory, known_witnesses=witnesses_ch,
                             model=cfg.llm_model, rounds=cfg.debate_rounds,
                             personas=cfg.llm_personas or None)
            debate_transcript = res["transcript"]
            current_criteria += res["criteria_add"]
            promoted_biases.extend(res["promoted"])
            if res["next_n_override"] is not None:
                next_n = res["next_n_override"]
            if res["promoted"]:
                push(force=True, msg=f"  · 토론 승격 {len(res['promoted'])}개 → next_n={next_n}")

        store.add_round(RoundRecord(
            round=rnd, num_candidates=len(round_results),
            num_accepted=len(round_results), num_witness=num_wit_round,
            best_upper_bound=best.implied_upper_bound if best else None,
            promoted_biases=list(promoted_biases),
            findings=finding_dicts, failures=failures, debate=debate_transcript))

        # 장기기억 갱신
        if memory is not None:
            memory.record_generator(cfg.om_class, attempts=len(round_results),
                                    witnesses=num_wit_round,
                                    best_bound=best.implied_upper_bound if best else None)
            for rec in new_recs:
                for name in rec.criteria_satisfied:
                    memory.record_criterion(name, in_witness=rec.is_witness)
            memory.record_combo([c["name"] for c in current_criteria], num_wit_round)
            for f in finding_dicts:
                memory.add_finding(f)
            memory.save()
            store.run["memory_summary"] = memory.summary_for_committee()

        push(force=True, msg=f"round {rnd} 종료: 후보 {len(round_results)} "
                             f"witness {num_wit_round} 최선상한 "
                             f"{best.implied_upper_bound if best else '—'}")

        if stopped:
            break
        if best and best.implied_upper_bound == target_bound:
            push(force=True, msg=f"목표 달성: n={best.n} → 상한 {best.implied_upper_bound} (=2d+1)")
            break
        n = next_n

    store.save(out_path)
    prog.state = "stopped" if stopped else "done"
    push(force=True, msg=f"{'중단됨' if stopped else '완료'} — 저장: {out_path} | "
                         f"요약 {store.to_dict()['summary']}")
    return store


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        cfg = SearchConfig(
            d=2, om_class="uniform", n_min=6, n_max=6, rounds=1,
            criteria=[{"name": "acyclic", "mode": "require"},
                      {"name": "totally_cyclic", "mode": "forbid"},
                      {"name": "not_reorientable_to_convex", "mode": "target"}],
            max_candidates_per_round=300, accepted_cap=20,
            memory_path=str(Path(tmp) / "mem_demo.json"), llm_enabled=False)
        run_search(cfg, out_path=str(Path(tmp) / "demo_results.json"))
