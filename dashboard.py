"""
dashboard.py — 로컬 UI (Streamlit). 진행 현황과 결과를 모두 화면에 표시(요구사항 #3).

실행:  streamlit run dashboard.py
  · 왼쪽: 클래스(탐색공간) 선택 + 파라미터 + 성질 토글(require/forbid/target) → "탐색 실행"
  · 실행 중: 실시간 현황(현재 최선 구성 · 현재 최소 상한 · 카운터 · 로그) + 일시정지/재개/중단
  · 완료/중단: 결과 요약 · 성질 분포 · 결과표 · witness 근거 상세
탐색은 백그라운드 스레드에서 돌며, 화면은 주기적으로 현황을 폴링한다.
"""
from __future__ import annotations
import json, tempfile, os, time
from collections import Counter
import streamlit as st
import pandas as pd

from om_classes import CLASS_REGISTRY, list_classes
from search import SearchConfig
from progress import SearchRunner
from store import ResultsStore

st.set_page_config(page_title="McMullen-OM Lab", layout="wide")

TOGGLEABLE = {
    "acyclic": "acyclic (양의 회로 없음)",
    "totally_cyclic": "totally cyclic (원점 내부 / acyclic 의 쌍대)",
    "convex_position": "convex independent (모든 Radon 분할 균형)",
    "reorientable_to_convex": "재배향으로 convex 가능",
    "not_reorientable_to_convex": "재배향으로도 convex 불가  ← 상한 witness",
    "circuit_balance_at_least": "회로 균형 ≥ k",
    "min_symmetry_order": "대칭(부호보존 재배향) ≥ k",
}
PARAM_CRITERIA = {"circuit_balance_at_least", "min_symmetry_order"}
MODES = ["off", "require", "forbid", "target"]
STATE_BADGE = {"idle": "⏸ 대기", "running": "▶ 실행 중", "paused": "⏸ 일시정지",
               "stopping": "⏹ 중단 중", "stopped": "⏹ 중단됨", "done": "✅ 완료",
               "error": "⚠ 오류"}


# ───────────────────────────── 사이드바: 설정 ─────────────────────────────
st.sidebar.title("McMullen-OM Lab")
st.sidebar.caption("유향 매트로이드 재구성으로 McMullen 상한을 탐색")

with st.sidebar:
    st.subheader("클래스 (탐색 공간)")
    class_names = list(CLASS_REGISTRY.keys())
    om_class = st.selectbox("OM 클래스", class_names,
                            index=class_names.index("uniform"))
    oc = CLASS_REGISTRY[om_class]
    st.caption(oc.description + (f"\n\n⚠ {oc.note}" if oc.note else ""))

    st.subheader("문제 / 범위")
    d = st.number_input("차원 d (rank = d+1, 클래스가 rank 고정 시 무시)", 1, 6, 2)
    c1, c2 = st.columns(2)
    n_min = c1.number_input("n_min", 3, 30, 6)
    n_max = c2.number_input("n_max", 3, 30, 6)
    rounds = st.number_input("라운드 수", 1, 50, 1)
    backend_override = st.selectbox("백엔드 override(generic 클래스만)",
                                    ["(클래스 기본)", "backtracking", "random", "z3"])
    dedup = st.checkbox("재배향 중복 제거", value=True)
    max_cand = st.number_input("라운드당 최대 후보", 10, 10_000_000, 300)
    seed = st.number_input("seed(random 재현, 0=무작위)", 0, 10**9, 0)

    st.divider()
    st.subheader("탐색 기준")
    st.caption("valid(적법 GP uniform OM)은 항상 적용됩니다.")
    crit_items: list[dict] = []
    for name, label in TOGGLEABLE.items():
        cols = st.columns([3, 2] if name in PARAM_CRITERIA else [1])
        default = ("target" if name == "not_reorientable_to_convex"
                   else "require" if name == "acyclic"
                   else "forbid" if name == "totally_cyclic" else "off")
        mode = cols[0].selectbox(label, MODES, index=MODES.index(default), key=f"m_{name}")
        args = []
        if name in PARAM_CRITERIA:
            k = cols[1].number_input("k", 1, 10, 2, key=f"k_{name}")
            args = [int(k)]
        if mode != "off":
            crit_items.append({"name": name, "mode": mode, "args": args})

    st.divider()
    st.subheader("연구 루프")
    discovery_on = st.checkbox("Discovery Engine (자동 패턴 발견)", value=True)
    memory_path = st.text_input("장기기억 파일(비우면 미사용)", "memory.json")

    st.divider()
    st.subheader("Theorist 토론 (로컬 LLM)")
    llm_on = st.checkbox("다중 전문가 토론 켜기 (Ollama 필요)", value=False)
    llm_model = st.text_input("모델", "qwen2.5", disabled=not llm_on)
    debate_rounds = st.number_input("토론 라운드", 1, 6, 2, disabled=not llm_on)

    start_clicked = st.button("탐색 실행", type="primary", use_container_width=True)

st.sidebar.divider()
loaded_path = st.sidebar.text_input("기존 결과 불러오기 (results.json 경로)", "")


# ───────────────────────────── 실행 제어 ─────────────────────────────
def build_cfg() -> SearchConfig:
    return SearchConfig(
        d=int(d), om_class=om_class,
        n_min=int(n_min), n_max=int(n_max), rounds=int(rounds),
        backend=None if backend_override == "(클래스 기본)" else backend_override,
        dedup=bool(dedup), criteria=crit_items,
        max_candidates_per_round=int(max_cand),
        seed=None if int(seed) == 0 else int(seed),
        discovery_enabled=bool(discovery_on),
        memory_path=(memory_path.strip() or None),
        debate_rounds=int(debate_rounds),
        llm_enabled=bool(llm_on), llm_model=llm_model)

if start_clicked:
    old = st.session_state.get("runner")
    if old and old.is_alive():
        old.stop()
    out = os.path.join(tempfile.gettempdir(),
                       f"mcmullen_{int(time.time())}.json")
    runner = SearchRunner(build_cfg(), out_path=out)
    runner.start()
    st.session_state["runner"] = runner
    st.session_state["out_path"] = out
    st.rerun()

runner: SearchRunner | None = st.session_state.get("runner")


# ───────────────────────────── 결과 렌더 ─────────────────────────────
def render_results(data: dict):
    run = data["run"]; summ = data["summary"]; results = data["results"]; rounds_log = data["rounds"]
    d_ = run["d"]; target = 2 * d_ + 1; loose_U = run.get("U")
    best_ub = summ.get("best_upper_bound")

    m = st.columns(4)
    m[0].metric("발견된 최소 상한", best_ub if best_ub is not None else "—")
    m[1].metric("목표 상한 (2d+1)", target)
    m[2].metric("느슨한 상한 U", loose_U)
    m[3].metric("witness 수", summ.get("num_witness", 0))

    if best_ub is not None and best_ub <= target:
        st.success(f"d={d_}: n={best_ub+1} witness 로 상한 **{best_ub} = 2d+1** 달성.")
    elif best_ub is not None and loose_U is not None and best_ub < loose_U:
        st.success(f"d={d_}: 느슨한 상한 {loose_U} → **{best_ub}** 로 개선.")
    elif best_ub is not None:
        st.warning(f"witness 발견(상한 {best_ub})이나 느슨한 상한 이하로는 아직.")
    else:
        st.warning("witness 미발견. 기준/n 범위/클래스를 조정해 보세요.")

    st.caption("클래스: " + run.get("om_class", "?") +
               "  ·  활성 기준: " + ", ".join(f"{c['name']}={c['mode']}"
                                           for c in run["criteria_active"]))

    wit = [r for r in results if r["is_witness"]]
    if wit:
        cnt = Counter()
        for rr in wit:
            cnt.update(rr["criteria_satisfied"])
        left, right = st.columns(2)
        with left:
            st.subheader("witness 가 사용한 성질")
            st.bar_chart(pd.DataFrame({"건수": dict(cnt)}))
        with right:
            st.subheader("라운드별 최고 상한")
            rl = pd.DataFrame([{"round": rr["round"],
                                "best_upper_bound": rr["best_upper_bound"]}
                               for rr in rounds_log])
            if not rl.empty:
                st.line_chart(rl.set_index("round"))

    st.subheader("결과 목록")
    rows = [{
        "id": rr["id"], "witness": "✓" if rr["is_witness"] else "",
        "n": rr["n"], "상한(n-1)": rr.get("implied_upper_bound"),
        "reward": rr["reward"],
        "만족 성질": ", ".join(rr["criteria_satisfied"]),
        "불만족": ", ".join(rr["criteria_failed"]),
    } for rr in sorted(results, key=lambda x: (not x["is_witness"], x["n"]))]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("witness 상세 (구성 · 상한 개선 · 사용한 성질)")
    for rr in sorted(wit, key=lambda x: x["n"])[:20]:
        with st.expander(f"witness {rr['id']}  ·  n={rr['n']}  →  상한 {rr.get('implied_upper_bound')}"
                         f"{'  (= 2d+1)' if rr.get('solves_conjecture') else ''}"):
            st.write(f"**상한 개선**: n={rr['n']} 비-재배향-convex OM → 상한 ≤ "
                     f"{rr.get('implied_upper_bound')} (목표 {rr.get('target_bound')}), reward={rr['reward']}")
            st.write("**사용한 성질(만족)**: " + ", ".join(rr["criteria_satisfied"]))
            st.write("**불만족 성질**: " + (", ".join(rr["criteria_failed"]) or "—"))
            if rr.get("promoted_biases"):
                st.write("**이 시점 승격된 LLM 편향**:")
                st.json(rr["promoted_biases"])
            st.write("**chirotope (정렬 r-튜플 → ±1)**:")
            st.json(rr["chirotope"]["signs"])

    with st.expander("라운드 로그"):
        st.dataframe(pd.DataFrame(rounds_log), use_container_width=True, hide_index=True)

    # ---- 연구 루프 산출물 (발견 · 실패분석 · 토론 · 기억) ----
    latest = rounds_log[-1] if rounds_log else {}
    findings = latest.get("findings") or []
    if findings:
        st.subheader("Discovery — 검증된 데이터에서 찾은 구조")
        st.dataframe(pd.DataFrame([{
            "불변량": f["invariant"], "값": f["value"], "종류": f["kind"],
            "지지도": f["support"], "제안 편향": (f["suggested_bias"] or {}).get("spec", {}).get("name", ""),
            "비고": f.get("note", ""),
        } for f in findings]), use_container_width=True, hide_index=True)

    failures = latest.get("failures") or {}
    if failures:
        st.subheader("실패 분석 — 후보 탈락 사유(마지막 라운드)")
        st.bar_chart(pd.DataFrame({"탈락 수": failures}))

    debates = [(rr["round"], rr.get("debate")) for rr in rounds_log if rr.get("debate")]
    if debates:
        st.subheader("전문가 토론 (제안 → 결정론적 반박)")
        for rnum, transcript in debates:
            for rd in transcript:
                with st.expander(f"round {rnum} · 토론 라운드 {rd['round']}"):
                    st.dataframe(pd.DataFrame([{
                        "전문가": p["role"], "상태": p["status"],
                        "추측": p["conjecture"],
                        "편향": (p["bias"] or {}).get("spec", {}),
                        "기각 사유": p["critique"],
                    } for p in rd["proposals"]]), use_container_width=True, hide_index=True)

    mem = run.get("memory_summary") or []
    if mem:
        st.subheader("장기기억 요약")
        for line in mem:
            st.write("· " + line)


# ───────────────────────────── 메인 영역 ─────────────────────────────
st.title("McMullen-OM Lab")

if runner is not None:
    snap = runner.snapshot()
    badge = STATE_BADGE.get(snap.state, snap.state)
    st.subheader(f"진행 현황 — {badge}")

    if snap.state == "error":
        st.error(f"오류: {snap.message}")

    cols = st.columns(5)
    cols[0].metric("현재 최소 상한", snap.best_upper_bound if snap.best_upper_bound is not None else "—")
    cols[1].metric("witness", snap.witnesses)
    cols[2].metric("처리 후보", snap.candidates)
    cols[3].metric("round / n", f"{snap.round} / {snap.n}")
    cols[4].metric("경과(초)", f"{snap.elapsed:.1f}")

    if snap.best_config:
        bc = snap.best_config
        st.success(f"**현재 최선 구성**: id `{bc['id']}`  ·  n={bc['n']}  →  상한 "
                   f"{bc['implied_upper_bound']}  ·  reward {bc.get('reward')}  ·  "
                   f"성질 [{', '.join(bc['criteria_satisfied'])}]")
    else:
        st.info("아직 witness 없음 — 탐색 진행 중. (현재 최선 구성이 여기에 표시됩니다)")

    # 제어 버튼
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
    b3.button("🔄 새로고침", use_container_width=True, on_click=lambda: None)

    with st.expander("실행 로그", expanded=runner.is_alive()):
        st.code("\n".join(snap.log[-40:]) or "(아직 로그 없음)")

    # 완료/중단되면 결과 표시
    out_path = st.session_state.get("out_path")
    if not runner.is_alive() and out_path and os.path.exists(out_path):
        st.divider()
        st.subheader("결과")
        try:
            render_results(ResultsStore.load(out_path))
        except Exception as e:
            st.error(f"결과 로드 실패: {e}")

    # 실행 중이면 자동 새로고침
    if runner.is_alive():
        time.sleep(0.7)
        st.rerun()

elif loaded_path:
    try:
        render_results(ResultsStore.load(loaded_path))
    except Exception as e:
        st.error(f"불러오기 실패: {e}")
else:
    st.info("왼쪽에서 **클래스**와 기준을 정하고 **탐색 실행**을 누르세요.\n\n"
            "목표: '어떤 재배향으로도 convex position 이 되지 않는' uniform OM 을 "
            "최소 원소 수 n 으로 찾으면 McMullen 상한이 n−1 로 내려갑니다.")
