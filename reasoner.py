"""
reasoner.py — LLM 공급자에 독립적인 추론 인터페이스 + 연구 프롬프트 생성기.

## 왜 필요한가

지금까지 이 저장소가 LLM 을 부르는 유일한 경로는 로컬 Ollama HTTP 였다. 그런데
저장소 자신의 실측 기록(docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §1)이 말하듯,
작은 로컬 모델은 근거 없는 n-추정으로 수렴했다. 고급 모델을 쓰려면 API 키가 필요한데
그건 이 프로젝트의 제약 밖이다.

해결: **수학 파이프라인이 "추론 텍스트가 어디서 왔는지" 전혀 신경 쓰지 않게 한다.**

    FileReasoner    prompts/0004-analyze.md 를 쓴다
                    → 사람이 그 파일을 고급 모델 대화창에 붙여넣는다
                    → 답을 responses/0004-analyze.md 로 저장한다
                    → 다음 실행에서 파이프라인이 그대로 이어간다
    OllamaReasoner  기존 로컬 경로 (보존)
    ScriptedReasoner 테스트용 (LLM 없이 전체 루프 검사)

API 키는 어떤 경로에서도 요구되지 않는다.

## 이 모듈이 하지 않는 일

수학적 판정을 하지 않는다. 프롬프트를 만들고 응답 텍스트를 돌려줄 뿐이며,
응답 안의 주장은 전부 `invariants.vet_invariant` / `falsify.falsify` /
`process_verifier` 가 결정론적으로 심사한다.

의존성: 표준 라이브러리. (Ollama 경로만 theorist 를 늦게 import)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from itertools import combinations
from typing import Optional, Protocol

from om_core import Chirotope

STAGES = ("explore", "construct", "critique", "analyze")


# ═══════════════════════ chirotope 의 사람/LLM 친화 표현 ═══════════════════════
def encode_chirotope(ch: Chirotope) -> dict:
    """부호를 사전식 r-부분집합 순서의 +/- 문자열 하나로 압축.
    (12,6) 이면 924자 — dict 로 쓰면 수만 자가 되는 것을 피한다."""
    subs = sorted(combinations(range(ch.n), ch.r))
    return {"n": ch.n, "r": ch.r,
            "order": "lexicographic r-subsets of {0..n-1}",
            "signs": "".join("+" if ch.signs[s] > 0 else "-" for s in subs)}


def decode_chirotope(d: dict) -> Chirotope:
    """encode_chirotope 의 역. LLM 이 구체적 후보를 제안하면 이 형식으로 받는다."""
    n, r, s = int(d["n"]), int(d["r"]), d["signs"].strip()
    subs = sorted(combinations(range(n), r))
    if len(s) != len(subs):
        raise ValueError(f"부호 길이 {len(s)} != C({n},{r})={len(subs)}")
    if set(s) - {"+", "-"}:
        raise ValueError("부호는 '+' 와 '-' 만 허용")
    return Chirotope(n, r, {sub: (1 if c == "+" else -1) for sub, c in zip(subs, s)})


# ═══════════════════════════ 추론자 인터페이스 ═══════════════════════════
class ResearchReasoner(Protocol):
    """수학 파이프라인이 보는 유일한 추론 표면.

    ask() 는 응답 텍스트를 돌려주거나, 아직 사람이 답을 넣지 않았으면 None 을
    돌려준다. None 은 오류가 아니라 '대기'다 — 파이프라인은 여기서 멈추고
    사람에게 무엇을 하면 되는지 알려준 뒤, 다음 실행에서 이어간다."""

    name: str

    def ask(self, stage: str, prompt: str, *, meta: dict | None = None) -> Optional[str]:
        ...


@dataclass
class PendingPrompt:
    """FileReasoner 가 응답을 기다리는 상태."""
    stage: str
    prompt_path: str
    response_path: str

    def instruction(self) -> str:
        return (f"[대기] 다음 파일을 고급 모델 대화창에 그대로 붙여넣으세요:\n"
                f"    {self.prompt_path}\n"
                f"  모델의 답변 전체를 아래 경로에 저장한 뒤 같은 명령을 다시 실행하세요:\n"
                f"    {self.response_path}")


class FileReasoner:
    """프롬프트를 파일로 쓰고 응답을 파일에서 읽는다 — human-in-the-loop 경로.

    이 방식의 장점은 신뢰가 아니라 **선택의 자유**다: 어떤 모델을 쓰든, 몇 번을
    다시 묻든, 대화 맥락을 얼마나 길게 유지하든 파이프라인은 영향받지 않는다."""

    name = "file"

    def __init__(self, root: str, *, prompts_dir: str = "prompts",
                 responses_dir: str = "responses"):
        self.root = root
        self.prompts_dir = os.path.join(root, prompts_dir)
        self.responses_dir = os.path.join(root, responses_dir)
        os.makedirs(self.prompts_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
        self.pending: list[PendingPrompt] = []

    def _paths(self, stage: str, seq: int) -> tuple[str, str]:
        base = f"{seq:04d}-{stage}.md"
        return (os.path.join(self.prompts_dir, base),
                os.path.join(self.responses_dir, base))

    def ask(self, stage: str, prompt: str, *, meta: dict | None = None) -> Optional[str]:
        seq = int((meta or {}).get("seq", self._next_seq(stage)))
        ppath, rpath = self._paths(stage, seq)
        if not os.path.exists(ppath):
            with open(ppath, "w", encoding="utf-8", newline="\n") as f:
                f.write(prompt)
        if os.path.exists(rpath):
            with open(rpath, encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                return text
        self.pending.append(PendingPrompt(stage, ppath, rpath))
        return None

    def _next_seq(self, stage: str) -> int:
        used = [int(m.group(1)) for fn in os.listdir(self.prompts_dir)
                if (m := re.match(r"(\d{4})-", fn))]
        return (max(used) + 1) if used else 1


class OllamaReasoner:
    """기존 로컬 경로 보존 — 작은 모델용. 품질 한계는 저장소에 기록돼 있다."""

    name = "ollama"

    def __init__(self, model: str = "qwen2.5", system: str = ""):
        self.model = model
        self.system = system or ("당신은 이산기하·유향 매트로이드 연구자다. "
                                 "지정된 JSON 형식으로만 답하라.")

    def ask(self, stage: str, prompt: str, *, meta: dict | None = None) -> Optional[str]:
        from theorist import ollama_chat
        try:
            return ollama_chat(self.model, self.system, prompt)
        except Exception as e:                # noqa: BLE001
            return None if "Connection" in repr(e) else f"(호출 실패: {e})"


class ScriptedReasoner:
    """테스트/재현용 — stage 별 고정 응답. LLM 없이 전체 루프를 돌릴 수 있다."""

    name = "scripted"

    def __init__(self, answers: dict):
        self.answers = dict(answers)
        self.seen: list[tuple[str, str]] = []

    def ask(self, stage: str, prompt: str, *, meta: dict | None = None) -> Optional[str]:
        self.seen.append((stage, prompt))
        return self.answers.get(stage)


# ═══════════════════════════ 응답 파싱 ═══════════════════════════
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


def _brace_spans(text: str) -> list[tuple[int, int]]:
    """문자열 리터럴을 존중하며 균형 잡힌 중괄호 구간을 전부 찾는다(중첩 포함).
    LLM 응답에는 설명·깨진 펜스·여러 판본이 섞이므로, 후보를 넓게 모은 뒤
    실제로 파싱되는 것만 고른다."""
    spans: list[tuple[int, int]] = []
    stack: list[int] = []
    in_str = False
    esc = False
    quote = ""
    for i, c in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                in_str = False
        elif c in ('"', "'"):
            in_str = True
            quote = c
        elif c == "{":
            stack.append(i)
        elif c == "}" and stack:
            spans.append((stack.pop(), i + 1))
    return spans


def extract_json(text: str) -> dict:
    """응답에서 JSON 객체를 뽑는다. 사람이 대화창에서 복사해 붙인 텍스트에는
    설명·여러 판본·깨진 펜스가 섞여 있는 게 정상이므로 단계적으로 폴백한다:
      1) ```json 펜스 중 마지막(=최종안)으로 파싱되는 것
      2) 균형 잡힌 중괄호 구간 중 '키가 가장 많고 가장 나중'인 것
    실패하면 빈 dict — 호출자는 이걸 '응답 형식 위반'으로 처리해야 한다."""
    if not text:
        return {}
    for b in reversed(_JSON_BLOCK.findall(text)):
        try:
            obj = json.loads(b)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    best: tuple[int, int, dict] | None = None
    for start, end in _brace_spans(text):
        try:
            obj = json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        key = (len(obj), start)
        if best is None or key > (best[0], best[1]):
            best = (len(obj), start, obj)
    return best[2] if best else {}


# ═══════════════════════════ 프롬프트 생성 ═══════════════════════════
_TRUST_PREAMBLE = """\
## 이 프로젝트의 신뢰 규약 (반드시 지킬 것)

당신의 답변은 사람이 아니라 **결정론적 검사기**가 받는다. 다음을 지키지 않으면
제안은 자동으로 기각된다.

1. 다음 다섯 등급을 절대 섞지 말 것. 각 주장마다 등급을 명시하라.
   - `PROVEN`      : 당신이 완전한 증명을 제시한 것
   - `VERIFIED`    : 이 보고서에 계산으로 확인됐다고 적힌 유한 사례
   - `NUMERICAL`   : 수치적 증거일 뿐
   - `CONJECTURE`  : 반증 가능하지만 아직 미증명
   - `SPECULATION` : 직관/유추
2. 보조정리를 제안하면, **먼저 반례를 찾으려고 시도한 흔적**을 보여라.
   반례 탐색을 하지 않은 보조정리는 낮게 취급된다.
3. 추상 유향 매트로이드(OM)는 자동으로 **실현가능하지 않다**. n=2d+2 에서
   비실현 witness 를 찾는 것은 ν(d) 상한에 대해 아무것도 증명하지 않는다.
   실현가능성이 필요한 주장이면 그 사실을 명시하라.
4. 추측은 **계산으로 반증 가능한 형태**로 제시하라. 아래 원자(atom) 형식을 쓰면
   이 저장소가 즉시 대규모로 공격한다.
5. "그럴듯해 보인다"는 검증이 아니다. 반례가 없다는 것은 증명이 아니다.
"""

_PROBLEM_BRIEF = """\
## 문제

McMullen 문제. ν(d) = "일반위치의 어떤 ν(d)개 점도 적당한 사영변환으로 convex
position 으로 보낼 수 있는" 최대 수. 하한 ν(d) ≥ 2d+1 은 **이미 알려져 있다**.
따라서 계산의 목표는 반례 찾기가 아니라, **n = 2d+2 개의 나쁜 배치(obstruction)**
를 찾아 상한 ν(d) ≤ 2d+1 을 닫는 것이다.

### 이 저장소의 정식화 (정확히 이 뜻으로만 쓸 것)

- R^d 일반위치 n점 → 동차화 → rank r = d+1 uniform chirotope χ.
- 사영변환 ↔ 재배향(원소별 부호반전). 전역반전은 무해하므로 재배향 공간은
  (Z/2)^(n-1), 크기 2^(n-1).
- convex position ⟺ 모든 circuit(= 최소 Radon 분할, uniform 이므로 (r+1)-부분집합)
  이 **균형**: 양·음 양쪽 크기가 모두 ≥ 2.
- **witness** ⟺ 2^(n-1) 개 재배향 중 convex 가 되는 것이 하나도 없음.
  n 에서 witness 를 찾으면 상한이 n−1 로 내려간다. 목표는 n = 2d+2.
- 이 동치의 근거: convex ⟹ acyclic 이고, acyclic 재배향 = tope = 선형범함수로
  재정규화 가능한 배치이므로, 전체 재배향을 훑는 것과 모든 사영상을 훑는 것이
  (실현가능한 경우) 같다.

### 현재 상태

- d=2 (r=3, n=6), d=3 (r=4, n=8) 에서 witness 가 확인됨.
- (5,3), (6,4) 에는 witness 가 없음이 전수로 확인됨.
- **d=5 (rank 6, n=12) 가 미해결 본 목표.** 전수 열거는 2^924 라 불가능하다.
"""

_ATOM_SPEC = """\
### 원자(atom)와 추측(conjecture) 형식

    atom       = {"inv": "<불변량 이름>", "op": "==|!=|<=|>=|<|>", "value": <값>}
    conjecture = {"antecedent": [atom, ...],   // 논리곱. 빈 리스트면 항상
                  "consequent": atom,
                  "scope": {"n": <int>, "r": <int>},
                  "statement": "<한 문장>",
                  "grade": "CONJECTURE|PROVEN|...",
                  "rationale": "<왜 참일 것 같은가 / 어떤 반례를 시도했는가>"}

`witness` 는 예약된 불변량 이름이며 값은 true/false 다.
"""

_INVARIANT_SPEC = """\
### 새 불변량 제출 형식

기존 어휘로 표현할 수 없는 성질이 필요하면 **직접 코드로 제출하라.** 어휘가
좁으면 정리도 좁아진다 — 새 어휘를 만드는 것이 이 단계에서 가장 가치 있는 일이다.

    {"name": "<식별자>", "description": "<한 줄>",
     "code": "def f(ch):\\n    ...\\n    return <값>",
     "why": "<이 양이 왜 McMullen 문제와 관련 있는가>"}

제한 문법 (위반하면 컴파일 단계에서 거부):
  - `import`, `while`, `try`, `class`, `lambda 외 함수정의`, `_` 로 시작하는 이름,
    화이트리스트 밖 전역 이름은 금지. 반복은 `for` + 유한 이터러블만.
  - 사용 가능한 전역: len min max sum sorted abs any all range enumerate zip
    tuple list set frozenset dict int bool str float map filter reversed
    divmod pow round combinations permutations product Counter gcd
  - `ch` 에서 쓸 수 있는 것: ch.n, ch.r, ch.signs, ch.chi(tuple),
    ch.circuit(S) -> {원소: ±1}, ch.cocircuit(H) -> {원소: ±1}, ch.reorient(flip),
    ch.is_valid(), ch.is_acyclic(), ch.is_totally_cyclic(), ch.is_convex_position()
  - 반환값은 bool / int / float / tuple 중 하나 (해시 가능해야 함).

자동 심사 항목: 전역성(예외 없음) · 결정성 · 비상수 · 비용 · 그리고
**원소 재명명 불변성**과 **재배향 불변성**을 실측해 기록한다. 재명명에 의존하는
양은 정리 후보에서 자동 강등되므로, 값을 만들 때 원소 이름에 의존하지 말 것
(예: 원소별 값은 반드시 정렬하거나 히스토그램으로 만들 것).
"""

_RESPONSE_SCHEMA = """\
## 응답 형식 (반드시 지킬 것)

자유롭게 분석한 뒤, **마지막에** 아래 JSON 을 ```json 펜스로 감싸 딱 하나만 넣어라.
분석 산문은 JSON 밖에 쓰면 된다 — 파이프라인은 JSON 만 읽는다.

```json
{
  "analysis": "핵심 관찰 3~6줄 요약",
  "new_invariants": [ {"name":"", "description":"", "code":"", "why":""} ],
  "deprecate_invariants": [ {"name":"", "reason":""} ],
  "conjectures": [ {"antecedent":[], "consequent":{}, "scope":{}, "statement":"",
                    "grade":"", "rationale":""} ],
  "candidate_chirotopes": [ {"n":0, "r":0, "signs":"+-+...", "why":""} ],
  "next_experiment": {"n":0, "r":0, "om_class":"", "why":""},
  "assessment": {"proven":[], "verified":[], "conjecture":[], "speculation":[]},
  "open_questions": []
}
```

비어 있어도 되는 항목은 빈 배열로 두라. `candidate_chirotopes` 의 `signs` 는
`{0..n-1}` 의 r-부분집합을 **사전식**으로 나열했을 때의 부호 문자열이다
(길이 = C(n,r)). 구체적 구성을 제안할 자신이 있을 때만 채우면 된다.
"""


def _fmt_vocabulary(rows: list[dict]) -> str:
    lines = ["| 이름 | 종류 | 출처 | 재명명불변 | 재배향불변 | 설명 |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        if r["status"] != "active":
            continue
        lines.append(f"| `{r['name']}` | {r['kind']} | {r['source']} | "
                     f"{_yn(r['relabel_invariant'])} | {_yn(r['reorient_invariant'])} | "
                     f"{r['description']} |")
    return "\n".join(lines)


def _yn(v):
    return "?" if v is None else ("O" if v else "X")


def _fmt_examples(items: list[dict], title: str, limit: int = 6) -> str:
    if not items:
        return ""
    out = [f"### {title} ({min(len(items), limit)}개 / 전체 {len(items)}개)", ""]
    for it in items[:limit]:
        enc = it.get("encoded") or {}
        out.append(f"- `{it['id']}` n={enc.get('n')} r={enc.get('r')}")
        out.append(f"  - signs: `{enc.get('signs','')}`")
        feats = {k: v for k, v in (it.get("features") or {}).items()
                 if not isinstance(v, (list, dict))}
        out.append(f"  - 불변량: `{json.dumps(feats, ensure_ascii=False, default=str)}`")
    out.append("")
    return "\n".join(out)


def build_analyze_prompt(*, corpus_summary: dict, vocabulary: list[dict],
                         conjecture_report: str, falsify_report: str,
                         witness_examples: list[dict],
                         nearmiss_examples: list[dict],
                         history: str = "", extra: str = "") -> str:
    """루프 한 바퀴의 결과를 고급 모델에게 넘기는 주 프롬프트."""
    parts = [
        "# McMullen 연구 루프 — 구조 분석 및 다음 방향 요청",
        "",
        _PROBLEM_BRIEF, "",
        _TRUST_PREAMBLE, "",
        "## 이번 라운드의 계산 결과",
        "",
        f"코퍼스: `{json.dumps(corpus_summary, ensure_ascii=False)}`",
        "",
        "### 현재 불변량 어휘", "",
        _fmt_vocabulary(vocabulary), "",
        conjecture_report, "",
        falsify_report, "",
        _fmt_examples(witness_examples, "witness 표본"),
        _fmt_examples(nearmiss_examples,
                      "근접 실패 표본 (convex 재배향이 가장 적은 non-witness)"),
    ]
    if history:
        parts += ["## 지금까지의 연구 기록 (같은 실패를 반복하지 말 것)", "", history, ""]
    parts += [
        "## 당신에게 요청하는 것", "",
        "1. 위 결과에서 **구조적 설명**을 찾아라. 어떤 양이 왜 그런 값을 갖는가?",
        "2. 현재 어휘로 표현할 수 없는 성질이 보이면 **새 불변량을 코드로 제출하라.**",
        "3. **반증 가능한 추측**을 제시하라. 특히 n 이나 rank 에 대해 확장되는 형태를.",
        "4. d=5 (r=6, n=12) 로 가는 **탐색 전략**을 제안하라. 전수 열거는 불가능하므로,",
        "   구조적 후보족(파라미터화된 구성) 또는 대칭/쌍대성을 이용한 축소가 필요하다.",
        "5. 위 결과 중 **틀렸거나 오해를 부르는 것**이 있으면 지적하라.",
        "",
        _ATOM_SPEC, "",
        _INVARIANT_SPEC, "",
        _RESPONSE_SCHEMA,
    ]
    if extra:
        parts += ["", "## 추가 지시", "", extra]
    return "\n".join(parts)


def build_stage_prompt(stage: str, *, context: str, question: str = "") -> str:
    """Explore / Construct / Critique 3단계 프롬프트 (Huang 식 최소 파이프라인)."""
    heads = {
        "explore": ("# Stage 1 — 탐색 (연구 노트)",
                    "완성된 증명이 아니라 **연구 노트**를 써라. 유망한 접근을 조사하고, "
                    "단계별 계획을 세우고, 증명 가능한 중간 주장은 증명하고, **빈틈을 "
                    "명시적으로 지목하라.** 추측된 문장이나 중간 보조정리가 **거짓일 "
                    "가능성**을 적극적으로 고려하고, 반례를 실제로 찾아보라."),
        "construct": ("# Stage 2 — 구성",
                      "위 탐색 맥락을 받아, 엄밀한 증명 / 반례 / obstruction / 후보족 중 "
                      "하나를 **구성하라.** 모든 가정을 명시하라. 전략이 막히면 수리하거나 "
                      "포기하고 그 사실을 분명히 적어라."),
        "critique": ("# Stage 3 — 비판",
                     "당신은 회의적인 심사위원이다. 위 논증에서 **오류를 적극적으로 찾아라.** "
                     "숨은 가정을 시험하고, 중간 보조정리의 반례를 구성해 보라. 검증된 "
                     "문장과 그럴듯한 추측을 분리하라. 가능하면 수정된 논증을 제시하라."),
    }
    if stage not in heads:
        raise ValueError(f"알 수 없는 stage '{stage}'. 사용 가능: {sorted(heads)}")
    title, instruction = heads[stage]
    return "\n".join([title, "", _PROBLEM_BRIEF, "", _TRUST_PREAMBLE, "",
                      "## 지시", "", instruction, "",
                      "## 맥락", "", context, "",
                      ("## 질문\n\n" + question if question else ""), "",
                      _RESPONSE_SCHEMA])


if __name__ == "__main__":
    import tempfile
    from console import enable_utf8_stdout

    enable_utf8_stdout()

    # (1) chirotope 압축 표현 왕복
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    enc = encode_chirotope(quad)
    assert len(enc["signs"]) == 4 and decode_chirotope(enc).signs == quad.signs
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    assert decode_chirotope(encode_chirotope(tri)).signs == tri.signs
    try:
        decode_chirotope({"n": 4, "r": 3, "signs": "++"})
        raise AssertionError("길이 불일치가 통과")
    except ValueError as e:
        assert "부호 길이" in str(e)
    print("chirotope 압축 표현 왕복 OK")

    # (2) FileReasoner: 응답이 없으면 대기, 생기면 이어감 — API 키 없음
    with tempfile.TemporaryDirectory() as tmp:
        fr = FileReasoner(tmp)
        out = fr.ask("analyze", "프롬프트 본문", meta={"seq": 4})
        assert out is None and len(fr.pending) == 1
        p = fr.pending[0]
        assert os.path.exists(p.prompt_path) and p.prompt_path.endswith("0004-analyze.md")
        assert "붙여넣" in p.instruction()
        with open(p.response_path, "w", encoding="utf-8") as f:
            f.write("분석입니다.\n```json\n{\"analysis\": \"ok\"}\n```")
        fr2 = FileReasoner(tmp)
        out2 = fr2.ask("analyze", "프롬프트 본문", meta={"seq": 4})
        assert out2 is not None and extract_json(out2) == {"analysis": "ok"}
        # 프롬프트 파일을 덮어쓰지 않는다 (사람이 손댔을 수 있으므로)
        assert len(fr2.pending) == 0
    print("FileReasoner 대기→재개 OK (API 키 불필요)")

    # (3) JSON 추출: 산문 + 여러 블록 중 마지막(최종안)을 고른다
    txt = ("생각 중...\n```json\n{\"a\": 1}\n```\n다시 고쳤습니다.\n"
           "```json\n{\"a\": 2, \"conjectures\": []}\n```\n끝")
    assert extract_json(txt)["a"] == 2
    assert extract_json("펜스 없이 {\"b\": 3} 여기")["b"] == 3
    assert extract_json("JSON 이 전혀 없음") == {}
    assert extract_json("```json\n{망가진\n```\n{\"c\": 4}")["c"] == 4
    print("JSON 추출 OK (펜스/최종안/깨진블록 폴백)")

    # (4) 프롬프트에 신뢰 규약과 형식이 빠짐없이 들어가는가
    prompt = build_analyze_prompt(
        corpus_summary={"total": 200, "witness": 167},
        vocabulary=[{"name": "num_tope_pairs", "kind": "int", "source": "builtin",
                     "status": "active", "relabel_invariant": True,
                     "reorient_invariant": True, "description": "tope 쌍 수"}],
        conjecture_report="# 추측 채굴 보고\n(내용)",
        falsify_report="# 반증 시도 결과\n(내용)",
        witness_examples=[{"id": "c00001", "encoded": enc, "features": {"n": 4}}],
        nearmiss_examples=[])
    for must in ("PROVEN", "SPECULATION", "실현가능", "```json", "atom",
                 "num_tope_pairs", "d=5", "재배향 불변"):
        assert must in prompt, must
    assert len(prompt) > 3000
    print(f"analyze 프롬프트 생성 OK ({len(prompt)}자)")

    for st in ("explore", "construct", "critique"):
        p = build_stage_prompt(st, context="맥락", question="질문?")
        assert "신뢰 규약" in p and "```json" in p
    print("explore/construct/critique 프롬프트 생성 OK")

    # (5) ScriptedReasoner 로 LLM 없이 루프를 돌릴 수 있는가
    sr = ScriptedReasoner({"analyze": "```json\n{\"analysis\":\"테스트\"}\n```"})
    assert extract_json(sr.ask("analyze", "x"))["analysis"] == "테스트"
    assert sr.ask("explore", "y") is None
    print("ScriptedReasoner OK")
    print("reasoner core-contract assertions OK")
