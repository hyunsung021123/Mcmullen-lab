# 인간 수학 insight 공동 처리 프로토콜

이 문서는 인간과의 수학 대화에서 나온 아이디어를 Claude와 Codex가 같은 의미로 읽고,
검증 가능한 탐색 개선으로 전환하는 절차를 정의한다. 권위 있는 원문은
`knowledge/insights/ledger.jsonl`이며, `insight_ledger.py`만 append한다.

## 1. 해결하려는 문제

채팅 맥락은 공유 상태가 아니다. 한 에이전트가 들은 아이디어를 저장소에 남기지 않으면
다른 에이전트는 알 수 없고, 세션이 바뀌면 가정·반례·기각 이유가 유실된다. 반대로 검증 전
아이디어를 곧바로 generator/pruning 규칙에 넣으면 recall을 잃거나 비실현 OM의 관찰을
`ν(d)` 결론으로 오해할 수 있다.

따라서 다음 세 층을 분리한다.

1. **Insight ledger**: 인간/에이전트가 제안한 공개 아이디어와 상태. 참을 보장하지 않는다.
2. **ResearchStep/evidence**: 기계가 실행할 검증 의무와 그 결과. 기존 `research_ir.py`,
   `process_verifier.py`, `evidence_db.py`, `falsify.py`가 담당한다.
3. **구현**: 검증을 통과한 opt-in generator, invariant, objective, pruning 등. witness 판정은
   여전히 `om_core.py`만 담당한다.

## 2. 언제 기록하는가

- 사용자가 `기록`, `검증`, `반영`, `탐색에 적용`을 요청한 구체적 아이디어는 등록한다.
- 구현 작업 중 발견한 새로운 수학적 가정도 등록한다.
- 단순 질문, 자유 토론, 이미 알려진 정의의 재진술은 자동 등록하지 않는다.
- 판단이 애매하면 코드를 바꾸지 말고 `PROPOSED / UNASSESSED`로만 기록하거나 사용자에게
  기록 여부를 묻는다.

대화만으로 `SUPPORTED`나 `INTEGRATED` 상태를 만들지 않는다. LLM의 동의는 evidence가 아니다.

## 3. 공통 수명주기

`PROPOSED → FORMALIZED → TESTING → SUPPORTED → INTEGRATED`

- `PROPOSED`: 원문을 짧은 공개 명제로 보존했다. 아직 모호할 수 있다.
- `FORMALIZED`: 범위, 가정, 실현가능성, 불변성, 반증 계획과 적용 지점이 명시됐다.
- `TESTING`: 결정론적 반증 또는 benchmark가 실행 중이다.
- `SUPPORTED`: 재현 가능한 evidence가 있다. 증명과 동일하지 않다.
- `REFUTED`: 반례 또는 실패 benchmark가 있다. 삭제하지 않는다.
- `INTEGRATED`: evidence와 구현 참조가 모두 있고 실제 탐색 경로에 반영됐다.
- `RETIRED`: 현재 사용하지 않는다. 과거 기록은 남는다.

`SUPPORTED`, `REFUTED`에는 evidence 참조가 필요하고, `INTEGRATED`에는 evidence와 구현
참조가 모두 필요하도록 CLI가 강제한다.

## 4. 에이전트가 반드시 채울 의미 필드

- `grade`: `PROVEN | VERIFIED | NUMERICAL | CONJECTURE | SPECULATION | UNASSESSED`
- `scope`: 최소한 관련 `n`, `r`, OM class와 exhaustive 여부를 구분할 수 있어야 한다.
- `realizability`: 원래 `ν(d)` 결론에 필요하면 `REQUIRED`; 추상 OM이면 `UNKNOWN`을 숨기지 않는다.
- `invariance.relabel`, `invariance.reorient`: 표본 통과만으로 `PROVEN`으로 올리지 않는다.
- `targets`: 아이디어가 영향을 줄 수 있는 계층. 여러 개 가능하다.
- `falsification_plan`: 구현 전에 먼저 시도할 가장 싼 반례 공격.
- `source_refs`: 채팅 task, 논문, Issue, 응답 파일 등 출처.
- `parent_ids`: 기존 insight의 변형·반박·일반화라면 연결한다.

긴 숨은 추론 과정은 저장하지 않는다. 재현 가능한 공개 명제, 짧은 근거, 반증 절차만 남긴다.

## 5. 구현 전 결정 순서

에이전트는 insight를 다음 순서로 분류한다.

1. 정의 또는 이미 증명된 동어반복인가?
2. 원소 재명명/재배향에 의존하는가?
3. 실현가능성이 필요한 결론인가?
4. 기존 어휘로 표현 가능한가, 새 invariant가 필요한가?
5. generator restriction이면 known witness recall을 잃지 않는가?
6. 작은 전수 범위 또는 기존 corpus에서 먼저 반증할 수 있는가?
7. 개선 효과를 동일 seed·예산·검증기로 비교할 benchmark가 있는가?

Pruning은 가장 위험하다. `SUPPORTED`만으로 pruning을 기본 활성화하지 않는다. 작은 범위의
recall preservation과 기존 witness retention을 통과하고, 별도 결정 기록이 있어야 한다.

## 6. CLI

제안 JSON 템플릿:

```bash
python insight_ledger.py template
```

JSON 파일로 등록:

```bash
python insight_ledger.py add --from-json path/to/proposal.json
```

상태 전이:

```bash
python insight_ledger.py status HI-0001 --actor codex --to FORMALIZED \
  --note "재배향 불변 정수로 형식화"

python insight_ledger.py status HI-0001 --actor claude --to SUPPORTED \
  --note "(6,3) 전수에서 반례 없음" --grade VERIFIED \
  --evidence experiments/run_0001/falsification.json
```

조회와 무결성 검사:

```bash
python insight_ledger.py list
python insight_ledger.py show HI-0001
python insight_ledger.py verify
```

ledger는 직접 편집하지 않는다. 같은 checkout에서 동시 append할 때 OS 파일 잠금이 순서를
직렬화하고, 각 event의 hash chain이 중간 개찬을 탐지한다. 서로 다른 clone의 Git 병합 충돌은
`docs/AI_WORKFLOW.md`의 일반 충돌 절차를 따른다. JSONL 줄을 수동 병합하지 말고 한쪽 event를
정상 CLI로 다시 append한다.

## 7. Claude ↔ Codex 인수인계

Issue/PR/HANDOFF에는 관련 `HI-NNNN`을 적는다. 다음 에이전트는 작업 시작 시 해당 insight를
`show`하고 연결 evidence를 재생한다. 인수인계에는 최소한 다음을 포함한다.

- insight ID와 현재 상태
- 이번 작업에서 추가한 evidence/implementation 참조
- 실패한 반증과 아직 실행하지 않은 반증
- 신뢰 모델 영향: witness 판정, realizability, invariance, pruning recall
- 다음 상태로 올리기 위해 남은 조건

에이전트 이름은 권위 등급이 아니다. `human`, `claude`, `codex`, `chatgpt` 모두 같은 상태 전이와
evidence 요건을 따른다.

