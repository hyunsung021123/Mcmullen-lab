"""
d5_project.py — d=5, n=12 witness 프로젝트 전용 프롬프트 생성 + 응답 흡수.

## 왜 별도 진입점인가

`research_cycle.py` 의 루프는 **코퍼스에서 명제를 채굴**하는 것이 목적이다. 이 프로젝트의
질문은 다르다:

    "국소탐색이 f=1 (d=4) / f=20 (d=5) 에서 막혔다. 이 평탄면을 어떻게 깨는가?"

이건 코퍼스 통계가 아니라 **구체적 구성 하나의 구조**에 대한 질문이라, 넣어야 할
데이터도(근접 실패 도시에) 물어야 할 것도(목적함수·이동연산·구성족) 다르다.

## 핵심 설계: 모델의 답을 '검사 가능한 것'으로 받는다

우리에겐 정확한 검증기가 있으므로, 모델에게 **명시적 정수 좌표**를 요구한다.
좌표 12×5 = 60개 정수는 모델이 쓰기에 자연스럽고, 우리는 밀리초 안에 판정한다.
그리고 정수 점배치에서 출발하므로 **실현가능성이 자동으로 보장**된다 —
비실현 OM 을 받아 아무것도 증명하지 못하는 함정을 원천적으로 피한다.

    모델이 준 좌표  →  om_core.mcmullen_evaluate  →  witness? 예/아니오

부호열(chirotope)도 계속 받지만(`candidate_chirotopes`), n=12 면 924자라 오류가
나기 쉬워 좌표 쪽(`candidate_points`)을 권장 형식으로 둔다.

## 명령

    python d5_project.py prompt                  # 도시에 조립 → prompts/NNNN-d5project.md
    python d5_project.py ingest --seq 0002       # responses/ 읽어 좌표 즉시 판정

의존성: 표준 라이브러리 + om_core + reasoner + nearmiss.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from console import enable_utf8_stdout
from om_core import Chirotope, mcmullen_evaluate
import reasoner as RS

ROOT = os.path.dirname(os.path.abspath(__file__))


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _load_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: str, text: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ═══════════════════════════ 도시에(dossier) 조립 ═══════════════════════════
def climb_summary(out_dir: str) -> dict | None:
    if not os.path.isdir(out_dir):
        return None
    import climb
    try:
        return climb.aggregate(out_dir)
    except Exception:                        # noqa: BLE001
        return None


def _fmt_nearmiss(rep: dict) -> str:
    if not rep:
        return "(아직 분석되지 않음)"
    L = []
    n, r, d = rep["n"], rep["r"], rep["d"]
    total = 1 << (n - 1)
    L.append(f"- 차원 d={d} (n={n}, rank r={r}). 재배향 공간 크기 2^(n−1) = {total}, "
             f"그중 acyclic(=사영변환으로 도달 가능한 점배치) **{rep['num_tope_pairs']}개**")
    L.append(f"- **f = convex 재배향 수 = {rep['num_convex_reorientations']}** "
             f"(0 이면 witness). om_core 판정: witness={rep['om_core_evaluate'].get('witness')}")
    L.append(f"- 점 좌표 (Z^{d} 정수):")
    L.append("")
    L.append("```")
    for i, p in enumerate(rep["points"]):
        L.append(f"p{i} = {p}")
    L.append("```")
    f_val = rep["num_convex_reorientations"]
    n_surv = len(rep.get("survivors", []))
    if n_surv and n_surv < f_val:
        L.append("")
        L.append(f"  (살아남은 재배향 {f_val}개 중 앞의 {n_surv}개만 아래에 싣는다.)")
    for s in rep.get("survivors", []):
        L.append("")
        L.append(f"- **살아남은 재배향**: 원소 {s['flip_set']} 를 뒤집은 것 "
                 f"(hypercube index {s['reorientation_index']}, 원소 0 은 고정)")
        L.append(f"  - 그 재배향에서 circuit(Radon 분할) 균형 min(|+|,|−|) 의 분포: "
                 f"`{s['circuit_balance_histogram']}`")
        # f=1 일 때만 '하나 깨면 witness'가 참이다. f>1 이면 이 재배향 하나가
        # 죽을 뿐 f 가 1 줄어들 뿐이다 — 이 구분을 흐리면 모델을 오도한다.
        consequence = ("이 중 하나만 무너뜨리면(한쪽을 크기 ≤1 로 만들면) 이 재배향은 "
                       "convex 가 아니게 되고, f 가 0 이 되어 **witness 가 된다**."
                       if f_val == 1 else
                       f"이 중 하나를 무너뜨리면 이 재배향 하나가 죽어 f 가 "
                       f"{f_val} → {f_val - 1} 로 줄어든다 (witness 가 되려면 "
                       f"{f_val}개 재배향을 **모두** 죽여야 한다).")
        L.append(f"  - 그중 **min-side = 2 인 '깨지기 쉬운' circuit 이 "
                 f"{s['num_fragile_circuits']}개**. {consequence}")
        L.append(f"  - fragile circuit 예시(원소 첨자): "
                 f"`{s['fragile_circuits_sample'][:6]}`")
        L.append(f"  - 원소별 취약도(= 그 원소가 fragile circuit 에 등장한 횟수): "
                 f"`{s['element_fragility_degree']}`")
    return "\n".join(L)


def _fmt_landscape(agg: dict | None, label: str) -> str:
    if not agg:
        return f"- {label}: (데이터 없음)"
    hist = agg.get("f_histogram") or {}
    return (f"- {label}: 평가 {agg['evals']:,}회, 재시작 {agg['restarts']}회, "
            f"최선 f = **{agg['best_f']}** / tope {agg['best_topes']}\n"
            f"  - 도달한 f 값의 빈도(작은 쪽부터): `{hist}`")


PROBLEM_KEY_FACTS = """\
## 이 프로젝트가 계산하는 것 (정의 — 이 뜻으로만 쓸 것)

R^d 일반위치 n 점 → 동차화 → rank r = d+1 uniform chirotope χ.

- **재배향** ρ ∈ {±1}^E: χ^ρ(B) = χ(B)·∏_{e∈B} ρ_e. 전역반전은 무해하므로 원소 0 을
  고정해 재배향 공간을 (Z/2)^(n−1) 로 본다.
- **사영변환 ↔ 재배향**: 허용 가능한 사영변환으로 얻는 점배치들은 정확히
  **acyclic 이 되는 재배향(=tope)** 에 대응한다 (Farkas/Gale 쌍대).
- **circuit**: uniform rank r 에서 circuit 은 (r+1)-부분집합 S={s_0<…<s_r} 이고
  부호는 C_S(s_i) = (−1)^i χ(S∖{s_i}). 그 양/음 부분이 S 의 Radon 분할이다.
- **convex position ⟺ 모든 circuit 에서 min(|양|,|음|) ≥ 2.**
  (근거: 점 p 가 나머지의 볼록껍질에 속함 ⟺ Carathéodory 로 한쪽이 {p} 인 Radon
  분할 존재 ⟺ 어떤 circuit 의 작은 쪽 크기가 1. 작은 쪽이 0 이면 acyclic 이 아님.)
- **f(점배치) := #{convex position 이 되는 재배향}**, **witness ⟺ f = 0.**
  n 에서 witness 를 찾으면 ν(d) ≤ n−1.

도달 가능한 사영 이미지의 총 수는 배치와 무관한 상수다:
Σ_{i=0}^{r−1} C(n−1, i) — d=4 (10,5) 이면 256, d=5 (12,6) 이면 1024.
(우리 계산값과 정확히 일치함을 확인했다.)

## 목표

**하한 ν(d) ≥ 2d+1 은 이미 알려져 있다.** 따라서 반례를 찾는 것이 목표가 아니라,
n = 2d+2 에서 witness 를 하나 제시해 상한을 닫는 것이 목표다.

- d=4: n=10 에서 witness → ν(4) ≤ 9. **문헌상 존재한다고 알려져 있다**
  (Forge–Las Vergnas–Schuchert, 10 points in dimension four…, 2001).
  ※ 이 출처는 우리가 원문 확인을 아직 못 했다.
- **d=5: n=12 에서 witness → ν(5) ≤ 11. 미해결. 이것이 본 목표다.**

우리는 **정수 점배치에서 출발**하므로, witness 를 찾으면 실현가능성이 자동으로
보장되어 곧바로 ν(d) 상한이 된다 (추상 유향 매트로이드였다면 아무것도 증명 못 한다).
"""

RESPONSE_SCHEMA = """\
## 응답 형식

자유롭게 분석하되, **마지막에** 아래 JSON 을 ```json 펜스로 딱 하나 넣어라.
산문은 JSON 밖에 쓰면 된다.

```json
{
  "analysis": "핵심 관찰 요약 (5~10줄)",
  "why_survivor_survives": "살아남은 재배향이 왜 살아남는지에 대한 구조적 설명 + 등급",
  "objective_proposals": [
    {"name": "", "definition": "f 가 같을 때 순서를 매길 2차 기준의 정확한 정의",
     "rationale": "", "expected_effect": "", "grade": ""}
  ],
  "move_proposals": [
    {"name": "", "definition": "어떤 이동을 어떤 공간에서 하는가", "rationale": "", "grade": ""}
  ],
  "family_proposals": [
    {"name": "", "construction": "파라미터화된 구성의 정확한 정의 (d 에 대한 일반형)",
     "why_it_should_work": "", "grade": "", "how_to_falsify": ""}
  ],
  "candidate_points": [
    {"n": 12, "d": 5, "points": [[0,0,0,0,0]],
     "why": "", "claimed": "witness | near-miss | unknown", "grade": ""}
  ],
  "candidate_chirotopes": [
    {"n": 12, "r": 6, "signs": "+-+...", "why": ""}
  ],
  "conjectures": [
    {"statement": "", "scope": {"n": 0, "r": 0}, "grade": "",
     "how_to_falsify": "우리가 계산으로 어떻게 깨뜨려 볼 수 있는가"}
  ],
  "literature": [
    {"claim": "", "source": "", "confidence": "", "note": "우리는 원문 확인 전까지 인용하지 않는다"}
  ],
  "what_we_are_doing_wrong": ["우리 접근에서 틀렸거나 오해를 부르는 점"]
}
```

`candidate_points` 가 **가장 가치 있는 항목**이다: 정수 좌표만 주면 우리가 즉시
`om_core` 로 판정한다. 좌표 개수는 n 개, 각 점은 d 개 정수다 (d=5 면 12×5=60개).
확신이 없어도 좋다 — 틀린 후보는 밀리초 안에 걸러지고, 그 자체가 정보다.
"""

def _asks(agg4: dict | None, nm4: dict | None) -> str:
    """요청문. 수치를 **실측에서 직접 읽어** 넣는다 — 하드코딩하면 탐색이 진행될수록
    프롬프트가 조용히 거짓이 된다(실제로 그럴 뻔했다)."""
    hist = (agg4 or {}).get("f_histogram") or {}
    hits1 = hist.get(1) or hist.get("1") or 0
    hits2 = hist.get(2) or hist.get("2") or 0
    evals = (agg4 or {}).get("evals", 0)
    frag = ""
    if nm4 and nm4.get("survivors"):
        deg = nm4["survivors"][0]["element_fragility_degree"].values()
        frag = f"{min(deg)}~{max(deg)}"
    return f"""\
## 요청 (우선순위 순)

**1. 평탄면을 깨뜨릴 목적함수를 제안하라.** 이것이 가장 급하다.
   현재 목적함수 f = #{{convex 재배향}} 은 너무 거칠다. d=4 에서 총 {evals:,}회 평가 중
   **f=1 상태에 {hits1:,}번 도달했는데 단 한 번도 f=0 으로 내려가지 못했다**
   (f=2 에는 {hits2:,}번 도달). 만약 마지막 한 칸이 확률 문제였다면 {hits1:,}번 중
   몇 번은 성공했어야 한다 — 즉 이것은 거리가 아니라 **벽**으로 보인다.
   f 가 같은 상태들 사이에 순서가 없어서 기울기가 사라지는 것이 원인이라고 추정한다.
   f 가 같을 때 "witness 에 더 가까움"을 재는 **2차 기준**을 정확히 정의하라.
   (살아남은 재배향의 fragile circuit 수를 쓰는 것이 자연스러워 보이지만, 그것이 정말
   단조로운 방향을 주는지는 우리가 모른다. 더 나은 안이 있으면 그것이 좋다.)

**2. 살아남은 재배향이 왜 살아남는가를 설명하라.**
   d=4 근접 실패에서 원소별 취약도가 {frag or '거의 균일하'}로 고르다. 즉 "이 점 하나가
   문제"가 아니다. 하나의 fragile circuit 을 깨면 256개 중 다른 재배향이 새로 convex 가
   되는 충돌 구조로 보인다. 이 긴장의 정체가 무엇인가?

**3. d=5 를 위한 파라미터화된 구성족을 제안하라.**
   무작위 탐색은 실측으로 배제되었다(위 참조). 필요한 것은 구조다. 특히:
   - n = 2d+2 에서 rank = corank = d+1 이다(자기쌍대 rank). Gale 쌍대를 쓸 수 있는가?
   - 대칭을 강제한 구성(순환군 작용 등)이 도움이 되는가?
   - d=4 의 알려진 구성을 **명시적 정수 좌표로** 재현할 수 있는가? 그것이 있으면
     우리가 즉시 검증하고 d=5 일반화의 템플릿으로 쓸 수 있다.

**4. 우리가 틀린 곳을 지적하라.**
   정식화, 측정 해석, 탐색 설계 중 잘못됐거나 오해를 부르는 것이 있으면 말하라.
"""


def build_prompt() -> str:
    nm4 = (_load_json(os.path.join(ROOT, "nearmiss_d4.json")) or [None])[0]
    nm5 = (_load_json(os.path.join(ROOT, "nearmiss_d5.json")) or [None])[0]
    probe = _load_json(os.path.join(ROOT, "feasibility_probe.json"), {})
    agg4 = climb_summary(os.path.join(ROOT, "climb_d4"))
    agg5 = climb_summary(os.path.join(ROOT, "climb_d5"))

    dens = probe.get("density", [])
    cost = probe.get("cost", [])
    dens_rows = "\n".join(
        f"| d={rec['d']} | ({rec['n']},{rec['r']}) | {rec['sampled']:,} | "
        f"{rec['witness']} | "
        f"{('%.4f%%' % (100 * rec['witness_rate'])) if rec.get('witness_rate') is not None else '—'} |"
        for rec in dens)
    cost_rows = "\n".join(
        f"| d={rec['r']-1} | ({rec['n']},{rec['r']}) | {rec['total_ms']} ms | "
        f"{rec['per_hour']:,} |" for rec in cost if rec.get("samples"))

    parts = [
        "# McMullen 문제 d=5 (n=12) — 탐색 설계 자문 요청",
        "",
        "당신에게 묻는 것은 증명이 아니라 **탐색 설계**와 **구성 아이디어**다. "
        "우리에게는 정확한 결정론적 검증기가 있으므로, 당신이 구체적 좌표를 주면 "
        "즉시 참/거짓을 가린다. 추측해도 좋다 — 다만 등급을 반드시 밝혀라.",
        "",
        PROBLEM_KEY_FACTS, "",
        RS._TRUST_PREAMBLE, "",
        "---", "",
        "# 우리가 실제로 측정한 것",
        "",
        "## 1. 후보 1개당 판정 비용 (실측)", "",
        "| 차원 | (n,r) | 후보당 | 시간당(1코어) |", "|---|---|---|---|",
        cost_rows, "",
        "개별 판정은 d=5 에서도 실용적이다. 문제는 속도가 아니다.",
        "",
        "## 2. 무작위 표집의 witness 밀도 — **붕괴**", "",
        "| 차원 | (n,r) | 표본 | witness | 비율 |", "|---|---|---|---|---|",
        dens_rows, "",
        "추가로 d=4 (10,5) 에서 **153,379개를 더 뽑아 witness 0건**을 확인했다 "
        "(95% 신뢰 상한 0.002%). d=2→d=3 감쇠 배수 47 을 외삽하면 약 52건이 나와야 "
        "하는데 0건이다 — **기하급수 감쇠 모형은 반증되었다.**",
        "",
        "그런데 d=4 의 witness 는 존재한다고 알려져 있다. 따라서:",
        "",
        "> witness 는 존재하지만 정수 격자 위 균등 무작위 표집으로는 도달할 수 없다.",
        "> **무작위 탐색 경로는 실측으로 폐기했다.**",
        "",
        "(표집 범위: [-C,C]^d 정수 격자, C ∈ {3,5,9,15,30}. 다른 분포는 시험하지 않았다.)",
        "",
        "## 3. 국소탐색(hill-climbing)의 지형", "",
        "목적함수 f 를 내려가는 국소탐색(이동: 점 하나의 좌표를 흔들거나 재표집, "
        "수용: f 감소는 항상·동률은 항상·증가는 온도에 따라, 정체 시 재시작):",
        "",
        _fmt_landscape(agg4, "d=4 (10,5)"),
        _fmt_landscape(agg5, "d=5 (12,6)"),
        "",
        "**핵심 관찰**: d=4 에서 f=1 에 여러 번 도달했지만 f=0 은 한 번도 없다. "
        "f=2 에는 그보다 훨씬 자주 도달한다. 즉 마지막 한 칸이 통계적 요행의 문제가 "
        "아니라 **구조적 장벽**으로 보인다.",
        "",
        "## 4. 근접 실패의 구조 — d=4 (가장 중요한 데이터)", "",
        _fmt_nearmiss(nm4), "",
        "## 5. 근접 실패의 구조 — d=5 (현재 최선)", "",
        _fmt_nearmiss(nm5), "",
        "## 6. 그 밖의 실측", "",
        "- GP-적법 uniform chirotope 전수 개수(전역 부호 고정 대표계): "
        "(5,3)=192, (6,3)=11,904, (6,4)=1,920, (7,3)=1,743,360, (7,4)=1,743,360.",
        "- **(7,3) 과 (7,4) 의 개수가 정확히 같다** — rank 와 corank 의 쌍대 대응과 "
        "정합한다. n=2d+2 에서는 rank = corank = d+1 이므로 쌍대가 같은 rank 위의 "
        "대합이 된다. 다만 **convex 조건이 쌍대에서 무엇이 되는지 우리는 확정하지 "
        "않았다** — 추측해서 구현하지 않기로 했다.",
        "- (6,3) 에서는 witness 가 오히려 흔하다(전수 11,904개 중 약 84%).",
        "",
        "---", "",
        _asks(agg4, nm4), "",
        RESPONSE_SCHEMA,
    ]
    return "\n".join(parts)


# ═══════════════════════════ 응답 흡수 ═══════════════════════════
def ingest(seq: int) -> int:
    fr = RS.FileReasoner(ROOT)
    _, rpath = fr._paths("d5project", seq)
    if not os.path.exists(rpath):
        print(f"응답 파일이 없습니다: {rpath}")
        return 1
    data = RS.extract_json(_read(rpath))
    if not data:
        print("응답에서 JSON 블록을 찾지 못했습니다 (```json 펜스 필요).")
        return 1

    result = {"seq": seq, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
              "analysis": data.get("analysis", ""),
              "why_survivor_survives": data.get("why_survivor_survives", ""),
              "candidate_points": [], "candidate_chirotopes": [],
              "objective_proposals": data.get("objective_proposals", []),
              "move_proposals": data.get("move_proposals", []),
              "family_proposals": data.get("family_proposals", []),
              "conjectures": data.get("conjectures", []),
              "literature": data.get("literature", []),
              "what_we_are_doing_wrong": data.get("what_we_are_doing_wrong", [])}

    # ── 점 좌표 제안: om_core 로 즉시 판정 (이 프로젝트의 핵심 경로) ──
    for i, spec in enumerate(data.get("candidate_points") or []):
        entry = {"index": i, "why": spec.get("why", ""),
                 "claimed": spec.get("claimed", ""), "grade": spec.get("grade", "")}
        try:
            pts = [tuple(int(x) for x in p) for p in spec["points"]]
        except Exception as e:                # noqa: BLE001
            entry.update({"ok": False, "error": f"좌표 파싱 실패: {e}"})
            result["candidate_points"].append(entry)
            print(f"  좌표 후보 {i}: 파싱 실패 — {e}")
            continue
        dims = {len(p) for p in pts}
        if len(dims) != 1:
            entry.update({"ok": False, "error": f"점마다 차원이 다름: {sorted(dims)}"})
            result["candidate_points"].append(entry)
            print(f"  좌표 후보 {i}: 차원 불일치 {sorted(dims)}")
            continue
        d = dims.pop()
        try:
            ch = Chirotope.from_points(pts)   # 일반위치가 아니면 ValueError
        except ValueError as e:
            entry.update({"ok": False, "error": f"일반위치 아님(uniform 실패): {e}",
                          "n": len(pts), "d": d})
            result["candidate_points"].append(entry)
            print(f"  좌표 후보 {i}: n={len(pts)} d={d} — 일반위치가 아님")
            continue
        ev = mcmullen_evaluate(ch)
        entry.update({"ok": True, "n": ch.n, "r": ch.r, "d": d,
                      "points": [list(p) for p in pts],
                      "valid_gp": ch.is_valid(),
                      "om_core_evaluate": ev,
                      "realizability": "REALIZABLE",
                      "note": "정수 점배치에서 왔으므로 실현가능성은 구성상 보장된다."})
        result["candidate_points"].append(entry)
        if ev.get("witness"):
            print(f"  ★★★ 좌표 후보 {i}: **WITNESS** n={ch.n} d={d} "
                  f"→ ν({d}) ≤ {ev['implied_upper_bound']}")
            _write(os.path.join(ROOT, f"WITNESS_from_model_{seq:04d}_{i:02d}.json"),
                   json.dumps(entry, ensure_ascii=False, indent=1))
        else:
            import invariants as INV
            f_val = INV.REGISTRY["num_convex_reorientations"].fn(ch)
            topes = INV.REGISTRY["num_tope_pairs"].fn(ch)
            entry["f"] = f_val
            entry["topes"] = topes
            print(f"  좌표 후보 {i}: n={ch.n} d={d} — witness 아님 "
                  f"(f = {f_val} / tope {topes})")

    # ── 부호열 제안 ──
    for i, spec in enumerate(data.get("candidate_chirotopes") or []):
        try:
            ch = RS.decode_chirotope(spec)
        except Exception as e:                # noqa: BLE001
            result["candidate_chirotopes"].append({"index": i, "ok": False,
                                                   "error": str(e)})
            print(f"  부호열 후보 {i}: 해독 실패 — {e}")
            continue
        valid = ch.is_valid()
        ev = mcmullen_evaluate(ch) if valid else None
        result["candidate_chirotopes"].append({
            "index": i, "ok": True, "valid_gp": valid, "om_core_evaluate": ev,
            "realizability": "UNKNOWN",
            "note": ("GP 위반 — 유향 매트로이드가 아님" if not valid else
                     "실현가능성 미판정 — 비실현이면 ν(d) 상한을 증명하지 않는다.")})
        print(f"  부호열 후보 {i}: valid={valid}"
              + (f", witness={ev['witness']}" if ev else ""))

    for key, label in (("objective_proposals", "목적함수"),
                       ("move_proposals", "이동연산"),
                       ("family_proposals", "구성족"),
                       ("conjectures", "추측")):
        items = result[key]
        if items:
            print(f"  {label} 제안 {len(items)}건 기록 (d=4 보정으로 검증 예정)")

    out = os.path.join(ROOT, f"d5project_ingest_{seq:04d}.json")
    _write(out, json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n  흡수 완료 → {out}")
    return 0


def main(argv=None) -> int:
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(prog="d5_project")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prompt", help="도시에 조립 → prompts/NNNN-d5project.md")
    p.add_argument("--seq", type=int, default=None)
    p.set_defaults(cmd="prompt")
    p = sub.add_parser("ingest", help="응답 흡수 + 좌표 즉시 판정")
    p.add_argument("--seq", type=int, required=True)
    p.set_defaults(cmd="ingest")
    args = ap.parse_args(argv)

    if args.cmd == "ingest":
        return ingest(args.seq)

    text = build_prompt()
    fr = RS.FileReasoner(ROOT)
    seq = args.seq if args.seq is not None else fr._next_seq("d5project")
    ppath, rpath = fr._paths("d5project", seq)
    _write(ppath, text)
    print(f"프롬프트 생성: {ppath}  ({len(text):,}자)")
    print(f"응답 저장 위치: {rpath}")
    print(f"흡수 명령:      python d5_project.py ingest --seq {seq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
