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
    "acyclic": {
        "label": "뒤집힌 부분이 없어야 함",
        "help": "점 배치를 어느 방향에서 봐도 '반대로 뒤집힌' 부분이 없는, 자연스러운 배치만 "
                "인정합니다. (전문 용어: acyclic — 양의 회로 없음)",
    },
    "totally_cyclic": {
        "label": "원점이 도형 안쪽에 있어야 함",
        "help": "배치의 중심(원점)이 도형 바깥이 아니라 안쪽에 있는 경우입니다. 아래 '볼록 배치'와는 "
                "다른 개념이니 혼동하지 마세요. (전문 용어: totally cyclic — acyclic 의 쌍대)",
    },
    "convex_position": {
        "label": "모든 점이 볼록하게(오목한 부분 없이) 배치돼야 함",
        "help": "다각형/다면체처럼 모든 점이 겉면에 있고 안쪽으로 파인 부분이 없는 배치입니다. "
                "(전문 용어: convex position — 모든 Radon 분할 균형)",
    },
    "reorientable_to_convex": {
        "label": "방향을 바꾸면 볼록하게 만들 수 있어야 함",
        "help": "지금 배치 자체는 볼록하지 않아도, 일부를 뒤집으면(재배향) 볼록하게 바꿀 수 있는 "
                "경우입니다.",
    },
    "not_reorientable_to_convex": {
        "label": "★ 어떻게 방향을 바꿔도 볼록하게 안 돼야 함 (이게 목표!)",
        "help": "이 조건을 만족하는 배치를 찾으면, 그게 곧 McMullen 문제의 '상한을 낮추는 증거'입니다. "
                "이 프로그램이 찾으려는 핵심 목표입니다.",
    },
    "circuit_balance_at_least": {
        "label": "구조의 균형도가 일정 수준 이상이어야 함 (고급)",
        "help": "점들 사이 관계가 얼마나 '균형 잡혀' 있는지를 나타내는 값입니다. 값(k)이 클수록 "
                "더 엄격한 균형을 요구합니다. 잘 모르면 꺼두셔도 됩니다.",
    },
    "min_symmetry_order": {
        "label": "이 배치를 그대로 유지하는 대칭이 일정 개수 이상이어야 함 (고급)",
        "help": "배치를 회전/반사해도 똑같아 보이는 '대칭'이 최소 몇 개 있어야 하는지를 정합니다. "
                "잘 모르면 꺼두셔도 됩니다.",
    },
}
PARAM_CRITERIA = {"circuit_balance_at_least", "min_symmetry_order"}
MODES = ["off", "require", "forbid", "target"]
MODE_LABELS = {
    "off": "사용 안 함",
    "require": "✅ 반드시 있어야 함",
    "forbid": "🚫 있으면 안 됨",
    "target": "🎯 이게 목표(찾으면 성공)",
}
CLASS_LABELS = {
    "uniform": "① 기본 탐색 — 가능한 모든 배치 (가장 정확하지만 느림)",
    "realizable_uniform": "② 무작위 점 배치 — 빠르게 여러 후보를 찔러봄 (추천, 점 8개 이상)",
    "rank2_uniform": "③ 특수 실험용 배치 (고급)",
    "cyclic": "④ 비교 기준용 배치 (그 자체가 목표는 아님)",
    "lawrence": "⑤ 준비 중 — 아직 사용할 수 없음",
}
STATUS_LABELS = {"survived": "✅ 채택됨", "rejected": "❌ 기각됨", "unverified": "검증 전"}
STATE_BADGE = {"idle": "⏸ 대기", "running": "▶ 실행 중", "paused": "⏸ 일시정지",
               "stopping": "⏹ 중단 중", "stopped": "⏹ 중단됨", "done": "✅ 완료",
               "error": "⚠ 오류"}


# ───────────────────────────── 사이드바: 설정 ─────────────────────────────
st.sidebar.title("McMullen-OM Lab")
st.sidebar.caption("점 배치를 탐색해서 수학 난제(McMullen 문제)의 답에 다가가는 도구")

with st.sidebar:
    st.subheader("1. 탐색 방식")
    class_names = list(CLASS_REGISTRY.keys())
    om_class = st.selectbox("어떤 방식으로 후보를 만들까요?", class_names,
                            index=class_names.index("uniform"),
                            format_func=lambda c: CLASS_LABELS.get(c, c),
                            help="후보가 될 점 배치를 컴퓨터가 만들어내는 방법입니다. 잘 모르겠으면 "
                                 "'② 무작위 점 배치'를 추천합니다.")
    oc = CLASS_REGISTRY[om_class]
    if oc.note:
        st.warning(oc.note)
    else:
        st.caption(oc.description)

    st.subheader("2. 문제 범위")
    d = st.number_input("차원 (공간의 차원 — 2=평면, 3=입체, ...)", 1, 6, 2,
                        help="이 문제를 몇 차원 공간에서 풀지 정합니다. 탐색 방식이 차원을 고정하는 "
                             "경우엔 이 값이 무시됩니다.")
    c1, c2 = st.columns(2)
    n_min = c1.number_input("점 개수 — 최소", 3, 30, 6)
    n_max = c2.number_input("점 개수 — 최대", 3, 30, 6,
                            help="이 범위 안에서 점 개수를 늘려가며 찾습니다.")
    rounds = st.number_input("반복 횟수", 1, 50, 1,
                             help="같은 설정으로 몇 번 반복해서 시도할지 정합니다. 목표를 "
                                  "달성하면 도중에 자동으로 멈춥니다.")
    with st.expander("고급 설정 (보통 안 건드려도 됩니다)"):
        backend_override = st.selectbox("생성 방식 세부 옵션",
                                        ["(자동)", "backtracking", "random", "z3"])
        dedup = st.checkbox("같은 모양(뒤집기만 다른) 중복 제거", value=True)
        max_cand = st.number_input("한 번에 검토할 후보 최대 개수", 10, 10_000_000, 300)
        seed = st.number_input("무작위 시드 (같은 값을 넣으면 같은 결과 재현, 0=매번 다르게)",
                               0, 10**9, 0)

    st.divider()
    st.subheader("3. 찾고 싶은 조건")
    st.caption("아래와 무관하게, 수학적으로 말이 되는 배치만 후보로 삼습니다(항상 켜져 있음). "
               "조건마다 '사용 안 함 / 반드시 있어야 함 / 있으면 안 됨 / 이게 목표'를 고를 수 있어요.")
    crit_items: list[dict] = []
    for name, info in TOGGLEABLE.items():
        cols = st.columns([3, 2] if name in PARAM_CRITERIA else [1])
        default = ("target" if name == "not_reorientable_to_convex"
                   else "require" if name == "acyclic"
                   else "forbid" if name == "totally_cyclic" else "off")
        mode = cols[0].selectbox(info["label"], MODES, index=MODES.index(default),
                                 format_func=lambda m: MODE_LABELS[m],
                                 help=info["help"], key=f"m_{name}")
        args = []
        if name in PARAM_CRITERIA:
            k = cols[1].number_input("기준값", 1, 10, 2, key=f"k_{name}")
            args = [int(k)]
        if mode != "off":
            crit_items.append({"name": name, "mode": mode, "args": args})

    st.divider()
    st.subheader("4. 자동 학습 (선택)")
    discovery_on = st.checkbox("찾은 결과들의 공통점 자동 분석하기", value=True,
                               help="지금까지 찾은 결과들 사이의 패턴을 자동으로 찾아서, "
                                    "다음 탐색에 힌트로 반영합니다.")
    memory_path = st.text_input("기록 파일 이름 (실행마다 결과가 여기 누적됩니다, 비우면 저장 안 함)",
                                "memory.json")

    st.divider()
    st.subheader("5. AI 전문가 토론 (선택)")
    llm_on = st.checkbox("AI 여러 명이 토론해서 힌트 주기", value=False,
                         help="이 컴퓨터에 Ollama가 설치·실행 중이어야 동작합니다. 켜지 않아도 "
                              "탐색 자체는 정상적으로 됩니다.")
    llm_model = st.text_input("사용할 AI 모델 이름", "qwen2.5", disabled=not llm_on)
    debate_rounds = st.number_input("토론을 몇 번 주고받을지", 1, 6, 2, disabled=not llm_on)

    start_clicked = st.button("▶ 탐색 실행", type="primary", use_container_width=True)

st.sidebar.divider()
loaded_path = st.sidebar.text_input("이전에 저장한 결과 파일 불러오기 (경로)", "")


# ───────────────────────────── 실행 제어 ─────────────────────────────
def build_cfg() -> SearchConfig:
    return SearchConfig(
        d=int(d), om_class=om_class,
        n_min=int(n_min), n_max=int(n_max), rounds=int(rounds),
        backend=None if backend_override == "(자동)" else backend_override,
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
    m[0].metric("지금까지 찾은 가장 좋은 값 (작을수록 좋음)", best_ub if best_ub is not None else "—")
    m[1].metric("이론상 목표값", target)
    m[2].metric("시작 시점 기준값", loose_U)
    m[3].metric("목표를 만족한 배치 개수", summ.get("num_witness", 0))

    if best_ub is not None and best_ub <= target:
        st.success(f"d={d_}: 점 {best_ub+1}개짜리 배치로 목표값 **{best_ub}(=2d+1)** 달성!")
    elif best_ub is not None and loose_U is not None and best_ub < loose_U:
        st.success(f"d={d_}: 시작 기준값 {loose_U} → **{best_ub}** 로 개선했습니다.")
    elif best_ub is not None:
        st.warning(f"조건을 만족하는 배치는 찾았지만(값 {best_ub}), 아직 목표만큼 좋지는 않습니다.")
    else:
        st.warning("아직 조건을 만족하는 배치를 못 찾았습니다. 조건/점 개수 범위/탐색 방식을 "
                   "조정해 보세요.")

    st.caption("탐색 방식: " + CLASS_LABELS.get(run.get("om_class", "?"), run.get("om_class", "?")) +
               "  ·  적용된 조건: " + ", ".join(f"{c['name']}={c['mode']}"
                                           for c in run["criteria_active"]))

    wit = [r for r in results if r["is_witness"]]
    if wit:
        cnt = Counter()
        for rr in wit:
            cnt.update(rr["criteria_satisfied"])
        left, right = st.columns(2)
        with left:
            st.subheader("목표를 만족한 배치들이 가진 공통 조건")
            st.bar_chart(pd.DataFrame({"건수": dict(cnt)}))
        with right:
            st.subheader("반복마다 가장 좋았던 값")
            rl = pd.DataFrame([{"반복": rr["round"],
                                "가장 좋은 값": rr["best_upper_bound"]}
                               for rr in rounds_log])
            if not rl.empty:
                st.line_chart(rl.set_index("반복"))

    st.subheader("결과 목록")
    rows = [{
        "번호": rr["id"], "목표 달성?": "✓" if rr["is_witness"] else "",
        "점 개수": rr["n"], "이 배치가 보여주는 값": rr.get("implied_upper_bound"),
        "점수": rr["reward"],
        "만족한 조건": ", ".join(rr["criteria_satisfied"]),
        "만족 못한 조건": ", ".join(rr["criteria_failed"]),
    } for rr in sorted(results, key=lambda x: (not x["is_witness"], x["n"]))]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("목표를 만족한 배치 자세히 보기")
    for rr in sorted(wit, key=lambda x: x["n"])[:20]:
        with st.expander(f"배치 {rr['id']}  ·  점 {rr['n']}개  →  값 {rr.get('implied_upper_bound')}"
                         f"{'  (= 이론상 목표값!)' if rr.get('solves_conjecture') else ''}"):
            st.write(f"**이 배치가 보여주는 것**: 점 {rr['n']}개짜리, 어떻게 방향을 바꿔도 볼록해지지 "
                     f"않는 배치 → 목표값 ≤ {rr.get('implied_upper_bound')} "
                     f"(이론상 목표 {rr.get('target_bound')}), 점수={rr['reward']}")
            st.write("**만족한 조건**: " + ", ".join(rr["criteria_satisfied"]))
            st.write("**만족 못한 조건**: " + (", ".join(rr["criteria_failed"]) or "—"))
            if rr.get("promoted_biases"):
                st.write("**이 시점 AI가 제안하고 채택된 힌트**:")
                st.json(rr["promoted_biases"])
            with st.expander("원본 수학 데이터 (참고용, 전문가용)"):
                st.json(rr["chirotope"]["signs"])

    with st.expander("실행 기록 로그 (참고용)"):
        st.dataframe(pd.DataFrame(rounds_log), use_container_width=True, hide_index=True)

    # ---- 연구 루프 산출물 (발견 · 실패분석 · 토론 · 기억) ----
    latest = rounds_log[-1] if rounds_log else {}
    findings = latest.get("findings") or []
    if findings:
        st.subheader("자동으로 발견된 패턴")
        st.caption("목표를 만족한 배치들 사이에서 공통적으로 나타난 특징입니다.")
        st.dataframe(pd.DataFrame([{
            "패턴 이름": f["invariant"], "값": f["value"], "얼마나 흔한가": f["kind"],
            "근거(지지도)": f["support"],
            "제안된 힌트": (f["suggested_bias"] or {}).get("spec", {}).get("name", ""),
            "비고": f.get("note", ""),
        } for f in findings]), use_container_width=True, hide_index=True)

    failures = latest.get("failures") or {}
    if failures:
        st.subheader("왜 탈락했나 (마지막 반복 기준)")
        st.bar_chart(pd.DataFrame({"탈락 수": failures}))

    debates = [(rr["round"], rr.get("debate")) for rr in rounds_log if rr.get("debate")]
    if debates:
        st.subheader("AI 전문가들의 토론 내용")
        st.caption("AI가 제안한 힌트라도, 실제로 검증된 결과와 모순되면 자동으로(코드가) 기각됩니다.")
        for rnum, transcript in debates:
            for rd in transcript:
                with st.expander(f"반복 {rnum} · 토론 {rd['round']}회차"):
                    st.dataframe(pd.DataFrame([{
                        "역할": p["role"],
                        "결과": STATUS_LABELS.get(p["status"], p["status"]),
                        "제안한 가설": p["conjecture"],
                        "제안한 힌트": (p["bias"] or {}).get("spec", {}),
                        "기각 이유": p["critique"],
                    } for p in rd["proposals"]]), use_container_width=True, hide_index=True)

    mem = run.get("memory_summary") or []
    if mem:
        st.subheader("지금까지 배운 것 요약")
        for line in mem:
            st.write("· " + line)


# ───────────────────────────── 메인 영역 ─────────────────────────────
st.title("McMullen-OM Lab")
st.caption("점들을 이리저리 배치해보면서, '어떻게 뒤집어도 볼록한 모양이 안 되는' 배치를 찾는 프로그램")

with st.expander("🔰 이 프로그램이 하는 일 (처음이시면 읽어보세요)"):
    st.markdown(
        "- 이 프로그램은 **McMullen 문제**라는 수학 난제를 컴퓨터로 탐색합니다.\n"
        "- 점 여러 개를 규칙에 맞게 배치해보고, 그중 **'아무리 뒤집어도(재배향해도) 볼록한 "
        "모양이 안 되는'** 배치를 찾으면, 그게 이 문제의 답의 상한(위쪽 한계)을 낮추는 "
        "증거가 됩니다.\n"
        "- 왼쪽에서 점 개수, 찾고 싶은 조건 등을 정하고 **'탐색 실행'**을 누르면 "
        "컴퓨터가 자동으로 여러 배치를 시도하고 결과를 보여줍니다.\n"
        "- 결과에 나오는 **값(상한)은 작을수록 더 좋은 결과**입니다."
    )

if runner is not None:
    snap = runner.snapshot()
    badge = STATE_BADGE.get(snap.state, snap.state)
    st.subheader(f"진행 현황 — {badge}")

    if snap.state == "error":
        st.error(f"오류: {snap.message}")

    cols = st.columns(5)
    cols[0].metric("지금까지 가장 좋은 값", snap.best_upper_bound if snap.best_upper_bound is not None else "—")
    cols[1].metric("목표 달성 배치 수", snap.witnesses)
    cols[2].metric("검토한 후보 수", snap.candidates)
    cols[3].metric("반복 / 점 개수", f"{snap.round} / {snap.n}")
    cols[4].metric("경과 시간(초)", f"{snap.elapsed:.1f}")

    if snap.best_config:
        bc = snap.best_config
        st.success(f"**현재까지 가장 좋은 배치**: 번호 `{bc['id']}`  ·  점 {bc['n']}개  →  값 "
                   f"{bc['implied_upper_bound']}  ·  점수 {bc.get('reward')}  ·  "
                   f"만족한 조건 [{', '.join(bc['criteria_satisfied'])}]")
    else:
        st.info("아직 목표를 만족한 배치 없음 — 계속 찾는 중입니다. (찾으면 여기에 표시됩니다)")

    # 제어 버튼
    b1, b2, b3 = st.columns(3)
    if runner.is_alive():
        if snap.state == "paused":
            if b1.button("▶ 다시 시작", use_container_width=True):
                runner.resume(); st.rerun()
        else:
            if b1.button("⏸ 잠깐 멈추기", use_container_width=True):
                runner.pause(); st.rerun()
        if b2.button("⏹ 그만하기", use_container_width=True):
            runner.stop(); st.rerun()
    b3.button("🔄 화면 새로고침", use_container_width=True, on_click=lambda: None)

    with st.expander("실행 로그 (참고용)", expanded=runner.is_alive()):
        st.code("\n".join(snap.log[-40:]) or "(아직 로그 없음)")

    # 완료/중단되면 결과 표시
    out_path = st.session_state.get("out_path")
    if not runner.is_alive() and out_path and os.path.exists(out_path):
        st.divider()
        st.subheader("결과")
        try:
            render_results(ResultsStore.load(out_path))
        except Exception as e:
            st.error(f"결과 불러오기 실패: {e}")

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
    st.info("왼쪽에서 **탐색 방식**과 **찾고 싶은 조건**을 정하고 **'▶ 탐색 실행'**을 누르세요.")
