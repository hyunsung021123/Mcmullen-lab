"""
dashboard.py — 로컬 UI (Streamlit). 연구 실험실 UI.

화면은 세 영역으로 나뉜다:
  1. 실험 설계 — 설정을 고르고, 실행 전 "실험 문장"으로 확인한 뒤 실행한다.
  2. 실행 현황 — 지금 도는 실험의 상태·현재 최선 결과·제어(일시정지/중단).
  3. 결과와 가설 — 검증된 결과, Discovery 패턴, AI 가설/채택된 탐색 규칙을 신뢰
     수준별로 구분해서 보여준다.

표시 문구/검증/뷰모델 변환의 순수 로직은 ui_helpers.py 에 있다 — 이 파일은 Streamlit
위젯 배치만 담당한다. 판정/생성 로직(om_core/criteria/generator/search/progress/store)은
그대로 재사용하며 수정하지 않는다.

실행:  streamlit run dashboard.py   (또는 scripts/run_dashboard.bat 더블클릭)
"""
from __future__ import annotations
import json, os, time
from collections import Counter
import streamlit as st
import pandas as pd

from om_classes import CLASS_REGISTRY
from search import SearchConfig
from progress import SearchRunner
from store import ResultsStore
from evidence_db import EvidenceDB
from research_ir import STEP_KINDS
from autonomous_ui import (AutonomousRunConfig, AutonomousResearchRunner,
                           audit_rows, validate_config as validate_autonomous_config)
import ui_helpers as uh

st.set_page_config(page_title="McMullen-OM Lab", layout="wide")

# 실행 결과 저장 위치 — 시스템 임시 폴더 대신 저장소 안의 전용 폴더를 쓴다. 이 폴더는
# .gitignore(local_runs/)로 완전히 무시되므로 git pull/커밋과 무관하게 영구 보존되고,
# 시스템이 임시 폴더를 정리해도 사라지지 않는다.
LOCAL_RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_runs")

# ───────────────────────────── 탐색 목표(고정) ─────────────────────────────
# 이 도구는 항상 McMullen 상한 witness(어떤 재배향으로도 convex position이 되지 않는
# OM) 하나만 찾는다. acyclic/totally_cyclic 등 다른 조건을 화면에서 토글하게 두는 건
# 실효성이 없었다 — acyclic(M) ⟹ ¬totally_cyclic(M)이 항상 성립해 totally_cyclic은
# 중복이고, witness 판정(재배향 궤도 전체 탐색)은 애초에 시작 후보가 acyclic일 필요도
# 없다(docs/DECISIONS.md 0010). REGISTRY의 다른 조건들(circuit_balance_at_least 등)도
# 지금은 UI에서 뺐다 — 필요해지면 CLI(config.yaml)에서는 여전히 쓸 수 있다.
FIXED_CRITERIA = [{"name": "not_reorientable_to_convex", "mode": "target"}]


# ───────────────────────────── 세션 상태 ─────────────────────────────
st.session_state.setdefault("runner", None)
st.session_state.setdefault("out_path", None)
st.session_state.setdefault("running_cfg_snapshot", None)
st.session_state.setdefault("pending_cfg", None)
st.session_state.setdefault("uploaded_data", None)
st.session_state.setdefault("autonomous_runner", None)
st.session_state.setdefault("autonomous_cfg_snapshot", None)


def _build_search_config(pending: dict) -> SearchConfig:
    return SearchConfig(
        d=int(pending["d"]), om_class=pending["om_class"],
        n_min=int(pending["n_min"]), n_max=int(pending["n_max"]),
        rounds=int(pending["rounds"]),
        backend=None if pending["backend"] == "(자동)" else pending["backend"],
        dedup=bool(pending["dedup"]), criteria=FIXED_CRITERIA,
        max_candidates_per_round=int(pending["max_cand"]),
        seed=None if int(pending["seed"]) == 0 else int(pending["seed"]),
        discovery_enabled=bool(pending["discovery_on"]),
        memory_path=(pending["memory_path"].strip() or None),
        debate_rounds=int(pending["debate_rounds"]),
        llm_enabled=bool(pending["llm_on"]), llm_model=pending["llm_model"],
        llm_personas=pending.get("llm_personas", {}))


# ───────────────────────────── 탭 1: 실험 설계 ─────────────────────────────
def render_design_tab(is_running: bool):
    if is_running:
        st.info("다른 실험이 실행 중입니다. 아래에서 다음 실험을 미리 구성해둘 수 있지만, "
                "**시작하려면 먼저 '📡 실행 현황' 탭에서 현재 실험을 중단**해야 합니다.")

    with st.form("experiment_form"):
        st.subheader("탐색 공간")
        c1, c2 = st.columns(2)
        class_names = list(CLASS_REGISTRY.keys())
        om_class = c1.selectbox("탐색 클래스", class_names,
                                index=class_names.index("uniform"),
                                format_func=lambda c: uh.class_display(c)["label"])
        d = c2.number_input("dimension d", 1, 10, 2)

        oc = CLASS_REGISTRY[om_class]
        r_preview = oc.resolve_rank(int(d))
        if oc.rank is not None:
            st.caption(f"이 클래스는 rank={oc.rank} 로 고정되어 있어 dimension 입력은 "
                       f"무시됩니다. 실제 사용되는 rank = **{r_preview}**.")
        else:
            st.caption(f"실제 사용되는 rank = **{r_preview}** (= d+1).")

        info = uh.class_display(om_class)
        st.caption(info["detail"])
        if info["warning"]:
            st.warning(info["warning"])

        c3, c4, c5 = st.columns(3)
        n_min = c3.number_input("n_min", 3, 40, 6)
        n_max = c4.number_input("n_max", 3, 40, 6)
        rounds = c5.number_input("반복 횟수", 1, 100, 1)

        st.caption("찾는 조건은 고정되어 있습니다: **valid**(적법한 uniform OM) 이면서 "
                   "**어떤 재배향으로도 convex position이 되지 않는 OM**(McMullen 상한 "
                   "witness). 다른 조건(acyclic 등)은 판정에 불필요함이 확인되어 "
                   "제거했습니다(docs/DECISIONS.md 0010).")

        st.subheader("연구 루프")
        discovery_on = st.checkbox("Discovery Engine (검증된 표본에서 패턴 자동 탐지)",
                                   value=True)
        llm_on = st.checkbox("Theorist 위원회 (로컬 LLM 다중 전문가 토론, Ollama 필요)",
                             value=False)

        with st.expander("고급 설정"):
            backend_override = st.selectbox("백엔드 override (generic 클래스만)",
                                            ["(자동)", "backtracking", "random", "z3", "cegis"])
            dedup = st.checkbox("재배향-동치 중복 제거", value=True)
            max_cand = st.number_input("라운드당 최대 후보", 10, 10_000_000, 300)
            seed = st.number_input("random 시드 (0 = 무작위)", 0, 10**9, 0)
            memory_path = st.text_input("장기기억 파일 경로 (비우면 미사용)", "memory.json")
            llm_model = st.text_input("Ollama 모델 이름", "qwen2.5", disabled=not llm_on)
            debate_rounds = st.number_input("토론 라운드 수", 1, 6, 2, disabled=not llm_on)

            st.caption("아래는 각 전문가 역할에게 주는 system prompt다. 바꿔도 채택 여부를 "
                      "정하는 결정론적 게이트(proof_checker/counterexample_hunter)는 "
                      "전혀 영향받지 않는다 — 제안자의 프롬프트만 바뀐다.")
            llm_personas = {}
            for role, default_prompt in uh.PROPOSER_ROLE_DEFAULTS.items():
                llm_personas[role] = st.text_area(
                    f"{role} 프롬프트", value=default_prompt, height=80,
                    disabled=not llm_on, key=f"persona_{role}")

        preview_clicked = st.form_submit_button("실험 문장 미리보기 / 검증")

    if preview_clicked:
        st.session_state.pending_cfg = {
            "d": int(d), "om_class": om_class, "n_min": int(n_min), "n_max": int(n_max),
            "rounds": int(rounds),
            "backend": backend_override, "dedup": bool(dedup),
            "max_cand": int(max_cand), "seed": int(seed),
            "discovery_on": bool(discovery_on), "memory_path": memory_path,
            "llm_on": bool(llm_on), "llm_model": llm_model,
            "debate_rounds": int(debate_rounds), "llm_personas": llm_personas,
        }

    pending = st.session_state.get("pending_cfg")
    if not pending:
        return

    st.divider()
    r = CLASS_REGISTRY[pending["om_class"]].resolve_rank(pending["d"])
    summary = uh.criteria_summary_from_items(FIXED_CRITERIA)
    sentence = uh.experiment_sentence(pending["d"], r, pending["om_class"],
                                      pending["n_min"], pending["n_max"], summary)
    st.markdown(f"**실험 문장**\n\n> {sentence}")

    errors = uh.validate_experiment(d=pending["d"], r=r, om_class=pending["om_class"],
                                    n_min=pending["n_min"], n_max=pending["n_max"],
                                    criteria_items=FIXED_CRITERIA)
    backend_eff = pending["backend"] if pending["backend"] != "(자동)" else \
        CLASS_REGISTRY[pending["om_class"]].backend
    warnings = uh.feasibility_warnings(d_eff=r - 1, backend_effective=backend_eff,
                                       n_max=pending["n_max"])
    for w in warnings:
        st.warning(w)
    for e in errors:
        st.error(e)

    start_disabled = bool(errors) or is_running
    if st.button("▶ 이 설정으로 탐색 실행", type="primary",
                disabled=start_disabled, use_container_width=True):
        cfg = _build_search_config(pending)
        os.makedirs(LOCAL_RUNS_DIR, exist_ok=True)
        out = os.path.join(LOCAL_RUNS_DIR, f"results_{int(time.time())}.json")
        runner = SearchRunner(cfg, out_path=out)
        runner.start()
        st.session_state.runner = runner
        st.session_state.out_path = out
        st.session_state.running_cfg_snapshot = dict(pending)
        st.session_state.pending_cfg = None
        st.rerun()
    if errors:
        st.caption("위 오류를 해결해야 실행할 수 있습니다.")
    elif is_running:
        st.caption("다른 실험이 실행 중이라 시작할 수 없습니다 — 먼저 중단하세요.")

    st.download_button("현재 실험 설정 JSON 다운로드",
                       data=json.dumps(pending, ensure_ascii=False, indent=2),
                       file_name="experiment_config.json", mime="application/json")


# ───────────────────────────── 탭 2: 실행 현황 ─────────────────────────────
def render_status_tab():
    runner: SearchRunner | None = st.session_state.get("runner")
    if runner is None:
        st.info("아직 실행한 실험이 없습니다. '🧪 실험 설계' 탭에서 설정을 확인하고 "
               "실행하세요.")
        return

    snap = runner.snapshot()
    st.subheader(f"상태: {uh.STATE_LABELS.get(snap.state, snap.state)}")
    if snap.state == "error":
        st.error(f"오류: {snap.message}")

    snap_cfg = st.session_state.get("running_cfg_snapshot")
    if snap_cfg:
        r = CLASS_REGISTRY[snap_cfg["om_class"]].resolve_rank(snap_cfg["d"])
        summary = uh.criteria_summary_from_items(FIXED_CRITERIA)
        sentence = uh.experiment_sentence(snap_cfg["d"], r, snap_cfg["om_class"],
                                          snap_cfg["n_min"], snap_cfg["n_max"], summary)
        st.info("현재 실행은 아래 설정으로 고정되어 있습니다. 화면에서 수정한 값은 "
               f"다음 실험에만 적용됩니다.\n\n> {sentence}")

    cols = st.columns(4)
    cols[0].metric("현재 n / round", f"{snap.n} / {snap.round}")
    cols[1].metric("검사된 후보 수", snap.candidates, help=uh.CANDIDATE_COUNTER_LABEL)
    cols[2].metric("발견된 witness 수", snap.witnesses)
    cols[3].metric("경과 시간(초)", f"{snap.elapsed:.1f}")

    if snap.best_config:
        bc = snap.best_config
        d_ = snap_cfg["d"] if snap_cfg else bc["n"] - bc["implied_upper_bound"]
        st.success(f"**현재까지 검증된 최선 결과**\n\n"
                   f"ν({d_}) ≤ {bc['implied_upper_bound']}  ·  witness n={bc['n']}  ·  "
                   f"id `{bc['id']}`  ·  {uh.TRUST_DETERMINISTIC}")
    else:
        st.info("아직 witness 미발견.")

    b1, b2, b3 = st.columns(3)
    if runner.is_alive():
        if snap.state == "paused":
            if b1.button("▶ 재개", use_container_width=True):
                runner.resume(); st.rerun()
        else:
            if b1.button("⏸ 일시정지", use_container_width=True):
                runner.pause(); st.rerun()
        if b2.button("⏹ 중단", use_container_width=True):
            runner.stop(); st.rerun()
    else:
        data = _load_current_results()
        if data:
            reason = uh.finish_reason_label(snap.state, data["run"], data["summary"])
            st.write(f"**종료 사유**: {reason}")
    b3.button("🔄 새로고침", use_container_width=True, on_click=lambda: None)

    with st.expander("실행 로그", expanded=runner.is_alive()):
        st.code("\n".join(snap.log[-40:]) or "(아직 로그 없음)")

    if runner.is_alive():
        time.sleep(0.7)
        st.rerun()


# ───────────────────────────── 탭 3: 결과와 가설 ─────────────────────────────
def _load_current_results() -> dict | None:
    """이번 세션에 표시할 결과 데이터 하나를 고른다: 업로드한 파일 > 방금 실행한 결과."""
    if st.session_state.get("uploaded_data") is not None:
        return st.session_state["uploaded_data"]
    out_path = st.session_state.get("out_path")
    runner: SearchRunner | None = st.session_state.get("runner")
    if out_path and os.path.exists(out_path) and runner is not None and not runner.is_alive():
        return ResultsStore.load(out_path)
    return None


def render_results_tab():
    with st.expander("다른 결과 불러오기"):
        up = st.file_uploader("결과 JSON 업로드", type=["json"])
        if up is not None:
            try:
                st.session_state["uploaded_data"] = json.loads(up.read())
                st.success("불러왔습니다.")
            except Exception as e:
                st.error(f"불러오기 실패: {e}")
        legacy_path = st.text_input("고급: 로컬 파일 경로로 직접 불러오기", "")
        if legacy_path:
            try:
                st.session_state["uploaded_data"] = ResultsStore.load(legacy_path)
            except Exception as e:
                st.error(f"불러오기 실패: {e}")
        if st.session_state.get("uploaded_data") is not None:
            if st.button("업로드한 결과 지우고 방금 실행한 결과로 돌아가기"):
                st.session_state["uploaded_data"] = None
                st.rerun()

    data = _load_current_results()
    if not data:
        st.info("아직 표시할 결과가 없습니다. 실험을 실행하거나 결과 JSON을 불러오세요.")
        return

    run = data["run"]; summ = data["summary"]
    results = data["results"]; rounds_log = data["rounds"]
    d_ = run["d"]; target = 2 * d_ + 1

    st.download_button("현재 결과 JSON 다운로드",
                       data=json.dumps(data, ensure_ascii=False, indent=2),
                       file_name="results.json", mime="application/json")

    st.subheader("A. 결정론적으로 검증된 결과")
    st.caption(uh.TRUST_DETERMINISTIC + " — 아래는 모두 om_core.py 의 결정론적 판별을 "
              "통과한 항목입니다.")
    headline = uh.best_result_headline(run, summ)
    m = st.columns(4)
    m[0].metric("최선 결과", headline or "—")
    m[1].metric("목표 상한 (2d+1)", target)
    m[2].metric("시작 기준 상한 U", run.get("U"))
    m[3].metric("witness 수", summ.get("num_witness", 0))
    if headline:
        st.success(f"**{headline}**" +
                  (" — 목표 상한 달성" if summ.get("best_upper_bound") == target else ""))
    else:
        st.warning("아직 witness 미발견.")

    st.caption("탐색 클래스: " + uh.class_display(run.get("om_class", "?"))["label"] +
              "  ·  적용된 조건: " + ", ".join(f"{c['name']}={c['mode']}"
                                          for c in run["criteria_active"]))

    wit = [r for r in results if r["is_witness"]]
    if wit:
        cnt = Counter()
        for rr in wit:
            cnt.update(rr["criteria_satisfied"])
        left, right = st.columns(2)
        with left:
            st.write("**witness 들이 공통으로 만족한 조건**")
            st.bar_chart(pd.DataFrame({"건수": dict(cnt)}))
        with right:
            st.write("**반복(round)별 최선 upper bound**")
            rl = pd.DataFrame([{"round": rr["round"], "upper bound": rr["best_upper_bound"]}
                              for rr in rounds_log])
            if not rl.empty:
                st.line_chart(rl.set_index("round"))

    rows = [{
        "id": rr["id"], "witness": "✓" if rr["is_witness"] else "",
        "n": rr["n"], "upper bound": rr.get("implied_upper_bound"),
        "검사해 만족한 조건": ", ".join(rr["criteria_satisfied"]),
        "검사했으나 불만족한 조건": ", ".join(rr["criteria_failed"]),
    } for rr in sorted(results, key=lambda x: (not x["is_witness"], x["n"]))]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.write("**witness 상세**")
    for rr in sorted(wit, key=lambda x: x["n"])[:20]:
        title = f"witness `{rr['id']}` — n={rr['n']} → ν({d_}) ≤ {rr.get('implied_upper_bound')}"
        if rr.get("solves_conjecture"):
            title += "  (= 목표 상한 2d+1 달성)"
        with st.expander(title):
            st.write(f"**{uh.TRUST_DETERMINISTIC}**  ·  d={d_}, r={rr['r']}, n={rr['n']}  ·  "
                    f"목표 상한 {rr.get('target_bound')}")
            st.write("**이번 실험에서 검사해 만족한 조건**: " +
                    (", ".join(rr["criteria_satisfied"]) or "—"))
            st.write("**이번 실험에서 검사했으나 만족하지 않은 조건**: " +
                    (", ".join(rr["criteria_failed"]) or "—"))
            st.caption("주의: 위 목록은 '이번 실험에서 검사한 조건'이지, 이 chirotope가 "
                      "가질 수 있는 모든 수학적 성질의 전체 목록이 아닙니다.")
            if rr.get("promoted_biases"):
                st.write(f"**{uh.TRUST_ADOPTED_RULE}** (이 시점까지 채택된 탐색 규칙):")
                st.json(rr["promoted_biases"])
            with st.expander("기계 검증용 원본 데이터 (chirotope, 내부 점수)"):
                st.caption(f"내부 우선순위 점수(reward): {rr['reward']}")
                st.json(rr["chirotope"]["signs"])
                st.download_button("이 witness JSON 다운로드",
                                   data=json.dumps(rr, ensure_ascii=False, indent=2),
                                   file_name=f"witness_{rr['id']}.json",
                                   mime="application/json", key=f"dl_{rr['id']}")

    st.divider()
    st.subheader("B. 검증된 표본에서 관찰된 경험적 패턴")
    st.caption(uh.TRUST_EMPIRICAL)
    latest = rounds_log[-1] if rounds_log else {}
    findings = latest.get("findings") or []
    if findings:
        promoted_this_round = [p["bias"] for p in (latest.get("promoted_biases") or [])]
        st.dataframe(pd.DataFrame([{
            "불변량": f["invariant"], "값": f["value"], "종류": f["kind"],
            "지지도(support)": f["support"],
            "제안된 힌트": (f["suggested_bias"] or {}),
            "채택 여부": ("채택됨" if f.get("suggested_bias") in promoted_this_round
                       else "—"),
            "비고": f.get("note", ""),
        } for f in findings]), use_container_width=True, hide_index=True)
    else:
        st.caption("아직 발견된 패턴이 없습니다(표본이 충분하지 않거나 Discovery가 꺼져 있음).")

    st.divider()
    st.subheader("C. AI 가설  ·  D. 채택된 탐색 규칙")
    debates = [(rr["round"], rr.get("debate")) for rr in rounds_log if rr.get("debate")]
    if debates:
        st.caption(uh.TRUST_AI_HYPOTHESIS + " — 각 역할이 제안한 가설입니다. 실제로 검증된 "
                  "결과와 모순되면 결정론적 게이트가 자동으로 기각합니다.")
        for rnum, transcript in debates:
            for rd in transcript:
                with st.expander(f"round {rnum} · 토론 {rd['round']}회차"):
                    st.dataframe(pd.DataFrame([{
                        "역할": p["role"],
                        "제안한 가설": p["conjecture"],
                        "제안한 힌트": (p["bias"] or {}),
                        "결과": uh.PROPOSAL_STATUS_LABELS.get(p["status"], p["status"]),
                        "기각 이유": p["critique"],
                    } for p in rd["proposals"]]), use_container_width=True, hide_index=True)
    else:
        st.caption("이번 실행에서는 Theorist 위원회(LLM 토론)를 사용하지 않았습니다.")

    all_promoted = [(rr["round"], b) for rr in rounds_log
                    for b in (rr.get("promoted_biases") or [])]
    if all_promoted:
        st.write(f"**{uh.TRUST_ADOPTED_RULE}**")
        st.dataframe(pd.DataFrame([{
            "round": rnum, "탐색 규칙": b["bias"], "채택 근거(gate_reason)": b["gate_reason"],
        } for rnum, b in all_promoted]), use_container_width=True, hide_index=True)

    mem = run.get("memory_summary") or []
    if mem:
        st.divider()
        st.subheader("장기기억(memory) 요약")
        for line in mem:
            st.write("· " + line)


# ───────────────────────────── 탭 4: 자율 IR 연구 ─────────────────────────────
def _local_path(path: str) -> str:
    """상대 경로는 저장소 루트 기준으로 해석한다."""
    path = path.strip()
    return path if os.path.isabs(path) else os.path.join(os.path.dirname(__file__), path)


def _json_default(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(f"JSON으로 직렬화할 수 없는 값: {type(value).__name__}")


def render_autonomous_tab(other_run_active: bool):
    runner: AutonomousResearchRunner | None = st.session_state.get("autonomous_runner")
    auto_running = runner is not None and runner.is_alive()

    st.subheader("자율 ResearchStep IR 연구")
    st.caption("LLM은 ResearchStep을 제안만 합니다. Process Verifier의 결정론적 hard gate, "
               "rule-based ranker, CEGIS, certificate 독립 replay가 채택 여부를 결정합니다. "
               "기존 탐색 탭과 별개의 opt-in 경로입니다.")

    with st.form("autonomous_research_form"):
        c1, c2, c3 = st.columns(3)
        d = int(c1.number_input("dimension d", 1, 10, 2, key="auto_d"))
        r = d + 1
        c2.metric("rank r (=d+1)", r)
        rounds = int(c3.number_input("자율 연구 라운드", 1, 100, 2))

        c4, c5 = st.columns(2)
        debate_rounds = int(c4.number_input("라운드당 제안·반박 회수", 1, 6, 1))
        max_witnesses = int(c5.number_input("최대 CERTIFIED witness", 1, 100, 1))

        st.markdown("#### Ollama 및 프롬프트")
        o1, o2 = st.columns(2)
        ollama_url = o1.text_input("Ollama Chat API URL",
                                    "http://localhost:11434/api/chat")
        model = o2.text_input("Ollama 모델", "qwen2.5")
        o3, o4 = st.columns(2)
        temperature = float(o3.slider("제안 temperature", 0.0, 1.5, 0.7, 0.1))
        ollama_timeout_s = int(o4.number_input("Ollama 요청 timeout(초)", 10, 3600, 300))
        common_prompt = st.text_area(
            "모든 제안자에게 적용할 공통 프롬프트",
            "검증 가능한 주장만 제안하고, 근거는 500자 이내의 공개 가능한 요약으로 작성하라.",
            height=100)
        with st.expander("역할별 프롬프트", expanded=False):
            personas = {}
            for role, default_prompt in uh.PROPOSER_ROLE_DEFAULTS.items():
                personas[role] = st.text_area(
                    f"{role} 프롬프트", default_prompt, height=90,
                    key=f"auto_persona_{role}")

        st.markdown("#### ResearchStep 정책")
        enabled_kinds = st.multiselect(
            "이번 실행에서 실행을 허용할 kind (hard gate 통과 후에만 적용)",
            options=list(STEP_KINDS), default=list(STEP_KINDS),
            help="선택하지 않은 kind도 기각하지 않고 backlog에 보존합니다.")

        st.markdown("#### CEGIS 예산 및 증거")
        b1, b2 = st.columns(2)
        max_outer = int(b1.number_input("CEGIS 최대 outer model", 1, 10_000_000,
                                        100_000, step=1_000))
        inner_timeout = int(b2.number_input(
            "후보별 SAT timeout(ms, 0=제한 없음)", 0, 3_600_000, 0, step=100))
        save_evidence = st.checkbox("Evidence DB(JSONL hash chain) 저장", value=True)
        evidence_path = st.text_input("Evidence 파일 경로", "local_runs/evidence.jsonl",
                                      disabled=not save_evidence)
        a1, a2 = st.columns(2)
        analyze_witnesses = a1.checkbox("witness 구조 분석", value=True)
        export_certificates = a2.checkbox("certificate 독립 replay 번들 export", value=True)

        start = st.form_submit_button(
            "▶ 자율 IR 연구 실행", type="primary", use_container_width=True,
            disabled=auto_running or other_run_active)

    cfg = AutonomousRunConfig(
        d=d, r=r, rounds=rounds, debate_rounds=debate_rounds,
        max_witnesses=max_witnesses, enabled_kinds=tuple(enabled_kinds),
        cegis_max_outer_models=max_outer,
        cegis_inner_timeout_ms=(inner_timeout or None),
        evidence_path=(_local_path(evidence_path) if save_evidence else None),
        model=model, ollama_url=ollama_url, ollama_temperature=temperature,
        ollama_timeout_s=ollama_timeout_s, common_prompt=common_prompt,
        personas=personas, analyze_witnesses=analyze_witnesses,
        export_certificates=export_certificates)
    errors = validate_autonomous_config(cfg)
    for error in errors:
        st.error(error)
    if other_run_active:
        st.info("기존 탐색이 실행 중이라 자율 IR 연구를 동시에 시작할 수 없습니다.")
    if auto_running:
        st.info("자율 IR 연구가 실행 중입니다. 설정 변경은 다음 실행에 적용됩니다.")

    if start and not errors:
        run_dir = os.path.join(LOCAL_RUNS_DIR, f"autonomous_{int(time.time())}")
        os.makedirs(run_dir, exist_ok=True)
        cfg = AutonomousRunConfig(**{
            **cfg.__dict__,
            "artifact_dir": os.path.join(run_dir, "certificates")
                            if export_certificates else None,
        })
        runner = AutonomousResearchRunner(cfg)
        runner.start()
        st.session_state.autonomous_runner = runner
        st.session_state.autonomous_cfg_snapshot = cfg
        st.rerun()

    runner = st.session_state.get("autonomous_runner")
    if runner is None:
        return

    st.divider()
    snap = runner.snapshot()
    m1, m2, m3 = st.columns(3)
    m1.metric("상태", uh.STATE_LABELS.get(snap.state, snap.state))
    m2.metric("현재 round", "—" if snap.round < 0 else
              f"{snap.round + 1} / {snap.rounds_total}")
    m3.metric("CERTIFIED witness", snap.witnesses)
    if snap.state == "error":
        st.error(snap.message)
    else:
        st.info(snap.message or "실행 준비 중")
    with st.expander("자율 실행 로그", expanded=runner.is_alive()):
        st.code("\n".join(snap.log) or "(아직 로그 없음)")

    if runner.is_alive():
        st.caption("현재 CEGIS 호출은 후보 단위 안전 중단 API가 없어 이 화면에서 강제 중단하지 "
                   "않습니다. 설정한 outer model/timeout 예산으로 실행을 제한합니다.")
        time.sleep(0.7)
        st.rerun()
        return

    report = runner.report
    if not report:
        return

    st.markdown("#### 실행 결과")
    st.write("**검증된 사실**")
    for fact in report.get("facts", []):
        st.success(fact)
    if not report.get("facts"):
        st.caption("이번 실행에서 새로 채택된 검증 사실이 없습니다.")

    round_rows = []
    for rd in report.get("rounds", []):
        round_rows.append({"round": rd["round"], **rd["counts"],
                           "실행": "; ".join(f"{sid}: {msg}"
                                             for sid, msg in rd["executed"])})
    if round_rows:
        st.write("**라운드별 실행 현황**")
        st.dataframe(pd.DataFrame(round_rows), use_container_width=True, hide_index=True)

    st.write("**Process Verifier audit**")
    audits = audit_rows(report)
    if audits:
        st.dataframe(pd.DataFrame(audits), use_container_width=True, hide_index=True)
    else:
        st.caption("audit 결과가 없습니다.")

    st.write("**Backlog (반박이 아니라 실행기·정책 대기)**")
    backlog_rows = [{"step id": step["id"], "kind": step["kind"],
                     "주장": step["claim"]["dsl"],
                     "상태": audit.get("status"),
                     "첫 미통과": audit.get("first_failed_obligation")}
                    for step, audit in report.get("backlog", [])]
    if backlog_rows:
        st.dataframe(pd.DataFrame(backlog_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("backlog가 없습니다.")

    if report.get("evidence_path"):
        try:
            count = EvidenceDB(report["evidence_path"]).verify_chain()
            st.success(f"Evidence DB hash chain 검증 완료: {count}개 레코드 · "
                       f"`{report['evidence_path']}`")
        except Exception as exc:
            st.error(f"Evidence DB 검증 실패: {exc}")

    if report.get("certificates"):
        st.write("**Certificate 및 독립 replay 번들**")
        for idx, cert in enumerate(report["certificates"], start=1):
            with st.expander(f"certificate {idx}"):
                st.json(cert)
                st.download_button(
                    "certificate JSON 다운로드",
                    json.dumps(cert, ensure_ascii=False, indent=2),
                    file_name=f"certificate_{idx}.json", mime="application/json",
                    key=f"auto_cert_{idx}")
                bundles = report.get("certificate_bundles", [])
                if idx <= len(bundles):
                    st.caption("독립 replay.py 포함 번들: " + bundles[idx - 1]["directory"])

    if report.get("witness_analysis"):
        st.write("**Witness structure analysis**")
        for idx, analysis in enumerate(report["witness_analysis"], start=1):
            with st.expander(f"witness {idx}: n={analysis['n']}, r={analysis['r']}"):
                st.metric("obstruction cover 크기", analysis["obstruction_cover_size"])
                st.json(analysis)

    st.download_button(
        "자율 연구 report JSON 다운로드",
        json.dumps(report, ensure_ascii=False, indent=2, default=_json_default),
        file_name="autonomous_research_report.json", mime="application/json")


# ───────────────────────────── 메인 ─────────────────────────────
st.title("McMullen-OM Lab")
st.caption("Oriented matroid 재구성으로 McMullen 문제(Larman 추측)의 상한을 탐색하는 "
          "연구 실험실")

_runner = st.session_state.get("runner")
_is_running = _runner is not None and _runner.is_alive()
_auto_runner = st.session_state.get("autonomous_runner")
_auto_running = _auto_runner is not None and _auto_runner.is_alive()

tab_design, tab_status, tab_results, tab_autonomous = st.tabs(
    ["🧪 실험 설계", "📡 실행 현황", "📊 결과와 가설", "🧭 자율 IR 연구"])

with tab_design:
    render_design_tab(_is_running or _auto_running)
with tab_status:
    render_status_tab()
with tab_results:
    render_results_tab()
with tab_autonomous:
    render_autonomous_tab(_is_running)
