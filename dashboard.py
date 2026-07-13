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
import json, tempfile, os, time
from collections import Counter
import streamlit as st
import pandas as pd

from om_classes import CLASS_REGISTRY
from search import SearchConfig
from progress import SearchRunner
from store import ResultsStore
import ui_helpers as uh

st.set_page_config(page_title="McMullen-OM Lab", layout="wide")

# ───────────────────────────── 조건(criteria) 표시 ─────────────────────────────
# REGISTRY 이름은 절대 바꾸지 않는다 — 화면 라벨/도움말 문구만 여기서 정한다.
TOGGLEABLE = {
    "acyclic": {
        "label": "Acyclic — 양의 회로가 없음",
        "help": "criteria.py REGISTRY: acyclic. 점 배치로 실현할 때 '뒤집힘'이 없는 경우.",
    },
    "totally_cyclic": {
        "label": "Totally cyclic — 양의 코회로가 없음 (acyclic 의 쌍대)",
        "help": "criteria.py REGISTRY: totally_cyclic. acyclic 과는 다른 개념이며 convex "
                "position 과도 무관하다(CLAUDE.md §3 참고).",
    },
    "convex_position": {
        "label": "Convex position — 모든 회로의 Radon 분할이 균형",
        "help": "criteria.py REGISTRY: convex_position. 모든 원소가 convex hull 의 꼭짓점.",
    },
    "reorientable_to_convex": {
        "label": "재배향으로 convex position 이 가능한가",
        "help": "criteria.py REGISTRY: reorientable_to_convex.",
    },
    "not_reorientable_to_convex": {
        "label": "★ 어떤 재배향으로도 convex position 이 되지 않는가 (McMullen 상한 witness)",
        "help": "criteria.py REGISTRY: not_reorientable_to_convex. 이 성질을 만족하는 후보를 "
                "찾으면 upper bound 를 n−1 로 낮추는 witness 가 된다.",
    },
    "circuit_balance_at_least": {
        "label": "회로 균형 ≥ k — 모든 Radon 분할의 작은 쪽이 k 이상",
        "help": "criteria.py REGISTRY: circuit_balance_at_least(k). convex_position 은 이 "
                "조건의 k=2 특수 경우에 해당한다.",
    },
    "min_symmetry_order": {
        "label": "대칭(부호 보존 재배향) 수 ≥ k",
        "help": "criteria.py REGISTRY: min_symmetry_order(k). 부호를 보존하는 재배향의 개수.",
    },
}
PARAM_CRITERIA = {"circuit_balance_at_least", "min_symmetry_order"}
MODES = ["off", "require", "forbid", "target"]
MODE_LABELS = {
    "off": "미사용",
    "require": "require — 반드시 만족",
    "forbid": "forbid — 만족하면 제외",
    "target": "target — 성공(witness) 판정 조건",
}


# ───────────────────────────── 세션 상태 ─────────────────────────────
st.session_state.setdefault("runner", None)
st.session_state.setdefault("out_path", None)
st.session_state.setdefault("running_cfg_snapshot", None)
st.session_state.setdefault("pending_cfg", None)
st.session_state.setdefault("uploaded_data", None)


def _collect_criteria_from_widgets() -> list[dict]:
    items = []
    for name, info in TOGGLEABLE.items():
        mode = st.session_state.get(f"m_{name}", "off")
        if mode == "off":
            continue
        args = [int(st.session_state[f"k_{name}"])] if name in PARAM_CRITERIA else []
        items.append({"name": name, "mode": mode, "args": args})
    return items


def _build_search_config(pending: dict) -> SearchConfig:
    return SearchConfig(
        d=int(pending["d"]), om_class=pending["om_class"],
        n_min=int(pending["n_min"]), n_max=int(pending["n_max"]),
        rounds=int(pending["rounds"]),
        backend=None if pending["backend"] == "(자동)" else pending["backend"],
        dedup=bool(pending["dedup"]), criteria=pending["criteria"],
        max_candidates_per_round=int(pending["max_cand"]),
        seed=None if int(pending["seed"]) == 0 else int(pending["seed"]),
        discovery_enabled=bool(pending["discovery_on"]),
        memory_path=(pending["memory_path"].strip() or None),
        debate_rounds=int(pending["debate_rounds"]),
        llm_enabled=bool(pending["llm_on"]), llm_model=pending["llm_model"])


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

        st.subheader("조건")
        st.caption("valid(Grassmann–Plücker 공리를 만족하는 적법한 uniform OM)는 항상 "
                   "자동으로 적용됩니다.")
        for name, info_c in TOGGLEABLE.items():
            cols = st.columns([3, 2] if name in PARAM_CRITERIA else [1])
            default = ("target" if name == "not_reorientable_to_convex"
                       else "require" if name == "acyclic"
                       else "forbid" if name == "totally_cyclic" else "off")
            cols[0].selectbox(info_c["label"], MODES, index=MODES.index(default),
                              format_func=lambda m: MODE_LABELS[m],
                              help=info_c["help"], key=f"m_{name}")
            if name in PARAM_CRITERIA:
                cols[1].number_input("k", 1, 10, 2, key=f"k_{name}")

        st.subheader("연구 루프")
        discovery_on = st.checkbox("Discovery Engine (검증된 표본에서 패턴 자동 탐지)",
                                   value=True)
        llm_on = st.checkbox("Theorist 위원회 (로컬 LLM 다중 전문가 토론, Ollama 필요)",
                             value=False)

        with st.expander("고급 설정"):
            backend_override = st.selectbox("백엔드 override (generic 클래스만)",
                                            ["(자동)", "backtracking", "random", "z3"])
            dedup = st.checkbox("재배향-동치 중복 제거", value=True)
            max_cand = st.number_input("라운드당 최대 후보", 10, 10_000_000, 300)
            seed = st.number_input("random 시드 (0 = 무작위)", 0, 10**9, 0)
            memory_path = st.text_input("장기기억 파일 경로 (비우면 미사용)", "memory.json")
            llm_model = st.text_input("Ollama 모델 이름", "qwen2.5", disabled=not llm_on)
            debate_rounds = st.number_input("토론 라운드 수", 1, 6, 2, disabled=not llm_on)

        preview_clicked = st.form_submit_button("실험 문장 미리보기 / 검증")

    if preview_clicked:
        st.session_state.pending_cfg = {
            "d": int(d), "om_class": om_class, "n_min": int(n_min), "n_max": int(n_max),
            "rounds": int(rounds), "criteria": _collect_criteria_from_widgets(),
            "backend": backend_override, "dedup": bool(dedup),
            "max_cand": int(max_cand), "seed": int(seed),
            "discovery_on": bool(discovery_on), "memory_path": memory_path,
            "llm_on": bool(llm_on), "llm_model": llm_model,
            "debate_rounds": int(debate_rounds),
        }

    pending = st.session_state.get("pending_cfg")
    if not pending:
        return

    st.divider()
    r = CLASS_REGISTRY[pending["om_class"]].resolve_rank(pending["d"])
    summary = uh.criteria_summary_from_items(pending["criteria"])
    sentence = uh.experiment_sentence(pending["d"], r, pending["om_class"],
                                      pending["n_min"], pending["n_max"], summary)
    st.markdown(f"**실험 문장**\n\n> {sentence}")

    errors = uh.validate_experiment(d=pending["d"], r=r, om_class=pending["om_class"],
                                    n_min=pending["n_min"], n_max=pending["n_max"],
                                    criteria_items=pending["criteria"])
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
        out = os.path.join(tempfile.gettempdir(), f"mcmullen_{int(time.time())}.json")
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
        summary = uh.criteria_summary_from_items(snap_cfg["criteria"])
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


# ───────────────────────────── 메인 ─────────────────────────────
st.title("McMullen-OM Lab")
st.caption("Oriented matroid 재구성으로 McMullen 문제(Larman 추측)의 상한을 탐색하는 "
          "연구 실험실")

_runner = st.session_state.get("runner")
_is_running = _runner is not None and _runner.is_alive()

tab_design, tab_status, tab_results = st.tabs(
    ["🧪 실험 설계", "📡 실행 현황", "📊 결과와 가설"])

with tab_design:
    render_design_tab(_is_running)
with tab_status:
    render_status_tab()
with tab_results:
    render_results_tab()
