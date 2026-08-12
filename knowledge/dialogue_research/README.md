# knowledge/dialogue_research/ — 자율 토론 루프의 연구 기록

## 이 디렉터리가 왜 있나

`math_dialogue.py` 의 자율 토론 루프는 **설계상 tracked 파일을 절대 수정하지 않는다**
(0038 결정 5). 안전상 옳은 규칙이지만, 결과적으로 연구 기록 전체가 `.gitignore` 된
`local_runs/math_dialogue/dialogue.sqlite3` 안에만 쌓인다. 즉 **영속성으로 가는 유일한
다리가 사람**이다.

2026-08-12 에 그 다리가 끊겼다. Codex 4-agent 루프가 6시간 반 동안 연구 사이클 10개를
돌린 뒤 **토큰 소진으로 중단**됐고, 사람이 검토·승격하기 전이었다. 그 시점에 저장소에
남은 기록은 0건이었다 — `questions/OPEN.md` 는 이미 답이 나온 질문 셋을 여전히
`상태 OPEN` 으로 표시하고 있었고, `research_log.md` 에는 아무 언급이 없었다.

이 디렉터리는 그 간극을 메운다. **연구 이력의 보관소이며 근거의 승격소가 아니다.**

## 권한 — 반드시 먼저 읽을 것

| 파일 | 권한 | 뜻 |
|---|---|---|
| `2026-08-12-emergent-loop.md` | `UNASSESSED_DIALOGUE_ONLY` | 대화 계층 원문의 기계적 사본. **아무것도 증명되지 않았다** |
| `research_log.md` (저장소 루트) | 검증된 실험 이력 | `om_core` 를 통과한 실측 |
| evidence DB | 승격된 근거 | `process_verifier` 감사를 통과한 것 |

내보낸 문서의 등급 표기(`ADVANCED` / `REFUTED` / `BLOCKED` / `LOW_YIELD`,
`EXHAUSTED_ON_SCOPE` 등)는 **대화 계층의 자체 분류**다. `om_core`·`falsify`·evidence DB 를
거친 것이 아니다. 각 종합문의 `STATUS` 절이 무엇이 확정이고 무엇이 미확인인지 스스로
구분해 두었으니 **반드시 함께 읽을 것** — 요약만 인용하면 등급이 사라진다.

## 독립 검증 현황

`python scripts/verify_dialogue_claims.py` 로 재현된다(약 0.5초). 그 스크립트는 검증한
것과 **검증하지 않은 것을 함께 출력한다** — 섞이면 안 되기 때문이다.

### 검증됨 (Claude Code, 2026-08-13)

| 주장 | 결과 |
|---|---|
| rank-6, n=12 의 모든 circuit bad mask 크기가 정확히 256 | C(12,7)=792개 전부 256. 원소 0 포함 여부 무관 |
| `2^11 = 2048 = 8 × 256` (여유 0) | 성립 → **8-cover 는 exact partition 이 강제된다** |
| 총 용량비 99.0배 | `docs/STATE.md §2` 의 실측과 일치 |
| 옛 U 식 − `U(d)` = `d mod 2` | d=1..11 전 범위 일치 → **0042 로 코드 정정** |

첫 두 항목이 중요하다. "circuit obstruction cover 에는 최소 9개가 필요하다"는 하한 논증의
**출발점인 용량 강성이 재현됐다**는 뜻이다.

### 검증 안 됨 — 등급을 올리지 말 것

- **240개 canonical Stage A 해의 전수 열거와 전원 GP 탈락.** 현재 근거는 코덱스의
  experimentalist·falsifier 두 독립 구현이 개수·convention·대칭 몫까지 일치했다는 것뿐이다.
- **240 해 ↔ P¹(F₇) Paley tournament 궤도 동일성** (120 keys, class 당 금지 quadruple 28개,
  명시 순열 `(0,1,2,7,6,5,4,3)`).
- **QQ-0002 의 rank-2 layer union 실현 정리**와 명시적 t 하한 `t^g > (N−1)Hᵐ/C_min`.
- **QQ-0003 의 혼합 rank 조성 properness** (n=4,5,6 전수)와 composition reversal 보조정리.
- **접합 귀납 조건부 정리 T0–T7** 과 `2,2,2,3 ⟹ ν(d) ≤ (9/4)d + O(1)`. 전제인 one-step
  operator G 가 아직 구현되지 않은 **조건부** 진술이다.

각 종합문이 스스로 "persistent replay artifact 가 없으므로 승격하지 않는다"고 적어 두었다.
그 판단을 존중한다.

## 읽는 순서

1. **`2026-08-12-emergent-loop.md` §규모** — 무엇이 얼마나 돌았는지.
2. **§연구 사이클** — 사이클별 `HYPOTHESIS → COMPUTATION → CRITIQUE → PIVOT → SYNTHESIS`
   흐름. `REFUTED` event 를 특히 볼 것. 적대자가 실제로 무엇을 죽였는지가 여기 있다
   (예: 240-set S₈ 작용이 residual Z₂ 때문에 well-defined 가 아니라는 반증 → 120 quotient 로
   선회 → 이후 Paley 통찰이 그 부채 자체를 불필요하게 만듦).
3. **§topic 최종 종합** — QQ-0001/0002/0003 과 창발 탐사 사이클의 전문. 가장 밀도 높다.
4. **§개념 증류** — 같은 결과를 가환대수·범주론·확률론적 방법 언어로 다시 쓴 것.
   **재표현이므로 원 결과의 증명 등급을 바꾸지 않는다.**

## 다시 만들기

```bash
python scripts/export_dialogue_research.py \
    --db local_runs/math_dialogue/dialogue.sqlite3 \
    --out knowledge/dialogue_research/<날짜>-<슬러그>.md
python scripts/verify_dialogue_claims.py
```

내보내기는 DB 를 `mode=ro` 로만 열고 아무것도 쓰지 않는다. 문서 머리말에 원본 DB 의
SHA-256 이 박히므로 어느 스냅샷에서 나왔는지 추적된다.

> ⚠ **원본 DB 를 따로 백업할 것.** 이 문서는 사람이 읽는 사본이고 원문 응답 JSON
> (`local_runs/math_dialogue/responses/`, 54개)은 gitignore 대상이라 저장소에 없다.
> 종합문의 `evidence_refs` 가 그 파일들을 가리키므로, DB 를 잃으면 근거 추적이 끊긴다.
> WAL 때문에 파일 복사만으로는 부족하다 — sqlite backup API 를 쓸 것.

## 승격 경로

이 디렉터리의 내용이 연구 사실이 되려면 기존 절차를 밟는다. 지름길은 없다.

1. 명제를 `insight_ledger.py` 로 `PROPOSED / UNASSESSED` 등록 (`HI-NNNN`).
2. `falsify.py` 또는 전용 결정론적 검사기로 **먼저 반증을 시도**.
3. 재현 가능한 evidence 와 구현 참조가 있을 때만 상태 전이.
4. 큰 계산이 필요하면 `docs/COMPUTATION_RELAY.md` 의 `computation-request/v1` 로 발행한다.
   240-case 재현은 이 계층의 정확한 사용 사례다 — 전수 기대치 240, 양성 대조군은
   "Paley edge 하나를 뒤집으면 궤도 동일성 또는 28-count 히스토그램이 깨진다".

`EXHAUSTED_ON_SCOPE` 는 **정리가 아니다.** 그 유한 범위의 전수 확인일 뿐이다
(`AGENTS.md` 연구 규율 2).
