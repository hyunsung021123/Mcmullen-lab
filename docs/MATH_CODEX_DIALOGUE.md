# 수학 Codex 자동 토론 환경

이 문서는 같은 로컬 checkout을 보는 여러 Codex task가 수학 질문·방향·증명 초안·반례
후보를 비동기 교환하도록 설정하는 최소 절차다. 통신은 `math_dialogue.py`의 SQLite 우편함,
깨우기는 Codex task의 heartbeat 자동화가 담당한다.

## 1. 신뢰 경계

이 우편함은 토론을 운반할 뿐이다.

- 모든 메시지와 최종 요약의 권한은 `UNASSESSED_DIALOGUE_ONLY`다.
- `PROVEN`, `VERIFIED` 같은 필드는 작성자의 자체 분류일 뿐 증명서가 아니다.
- 대화 결과는 `knowledge/insights/ledger.jsonl`, `evidence_db`, `research_log.md`로 자동
  승격되지 않는다.
- witness 판정은 계속 `om_core.mcmullen_evaluate()`만 한다.
- heartbeat는 메시지 본문을 **연구 입력 데이터**로 읽고, 그 안의 명령을 실행하지 않는다.

유망한 결과를 공유 상태로 올리려면 기존 절차를 별도로 밟는다.

1. 공개 명제를 `insight_ledger.py`로 `PROPOSED / UNASSESSED` 등록
2. `falsify.py` 또는 전용 결정론적 검사기로 반증 시도
3. 재현 가능한 evidence를 붙인 뒤에만 상태 전이

## 2. 전제 조건

- 모든 수학 task가 **동일한 saved project의 local checkout**을 사용해야 한다.
- Codex worktree를 task마다 따로 만들면 기본 DB도 서로 달라져 통신되지 않는다.
- PC가 절전·종료되면 로컬 heartbeat는 진행되지 않는다.
- 런타임 데이터는 `.math_dialogue/`에 저장되며 Git에 커밋하지 않는다.

Windows에서 `python`이 PATH에 없다면 이 문서의 `python`을 Codex 번들 Python의 절대
경로 또는 `py -3`으로 바꾼다.

## 3. 우편함 초기화

저장소 루트에서 실행한다.

```powershell
python math_dialogue.py init
python math_dialogue.py register --agent explorer --role "새 구성·추측·연결을 제안한다"
python math_dialogue.py register --agent skeptic --role "가정·반례·범위·실현가능성을 감사한다"
python math_dialogue.py register --agent synthesizer --role "합의와 미해결 의무를 구조화한다"
python math_dialogue.py status
```

이름은 Codex task 제목이 아니라 우편함 내부의 안정적인 식별자다. 한 task는 한 agent 이름만
사용한다.

## 4. Codex task 만들기

Codex 앱에서 같은 저장소를 대상으로 local task 세 개를 만든다. worktree가 아니라 현재
checkout을 직접 공유하도록 선택한다.

각 task의 첫 프롬프트에는 다음 두 내용을 넣는다.

1. 역할별 지침: `prompts/math_agents/explorer.md`, `skeptic.md`, `synthesizer.md` 중 하나
2. 공통 heartbeat 지침: `prompts/math_agents/heartbeat.md`

task 제목에도 agent 이름을 넣어 찾기 쉽게 한다. 예:

- `math/explorer`
- `math/skeptic`
- `math/synthesizer`

## 5. 자동화 전에 수동 heartbeat 검사

먼저 topic과 첫 질문을 만든다.

```powershell
$topicResult = python math_dialogue.py topic `
  --title "(5,12) 접합 귀납의 최소 boundary signature" `
  --created-by human --max-rounds 6 --max-messages 10 | ConvertFrom-Json
$topic = $topicResult.topic_id

python math_dialogue.py post --topic $topic --sender human --to explorer `
  --kind QUESTION --grade UNASSESSED `
  --body "가장 싼 반증 시험과 필요한 정확한 정의를 제안하라."
```

그다음 `math/explorer` task에 “heartbeat를 한 번 수동 실행하라”고 요청한다. explorer가
응답을 skeptic에게 넣었으면 skeptic task에서도 같은 요청을 한다.

상태와 대화는 다음으로 확인한다.

```powershell
python math_dialogue.py status
python math_dialogue.py transcript --topic $topic
```

## 6. heartbeat 자동화 설정

수동 왕복이 성공한 뒤 각 task에서 다음과 같이 요청한다.

> 이 task에 10분 간격 heartbeat 자동화를 만들어라. 실행 환경은 현재 local project다.
> 매 실행마다 `prompts/math_agents/heartbeat.md`를 따르고 agent 이름은 `explorer`다.
> 한 번에 메시지 하나만 처리하고, inbox가 비어 있으면 즉시 끝내라.

다른 task에서는 agent 이름만 `skeptic`, `synthesizer`로 바꾼다. 처음에는 10~15분 간격을
권장한다. 1분 간격은 빈 호출과 토큰 소비가 커지고, 두 세션이 불필요하게 서로를 깨우는
문제를 찾기 어렵다.

heartbeat는 다음 상태기계만 수행한다.

```text
claim 1건 → 저장소/근거 읽기 → response JSON 작성 → submit → 종료
     └ no_work이면 즉시 종료
```

무한 반복, 같은 heartbeat 안에서 다음 메시지까지 재선점, 상대 task 직접 호출은 금지한다.

## 7. 응답 JSON

heartbeat는 `.math_dialogue/responses/<agent>-<message-id>.json`에 다음 형식으로 쓴다.

```json
{
  "to": "skeptic",
  "kind": "CONJECTURE",
  "grade": "UNASSESSED",
  "body": "명제, 가정, 범위, 가장 싼 반증 시험을 짧게 적는다.",
  "evidence_refs": ["knowledge/problem.md"],
  "ttl_seconds": 86400,
  "close_topic": false
}
```

토론을 끝낼 때는 다음처럼 한다. `body`는 topic의 최종 요약으로 보존된다.

```json
{
  "kind": "SYNTHESIS",
  "grade": "UNASSESSED",
  "body": "합의한 사실, 반박된 부분, 남은 검증 의무를 구분한다.",
  "evidence_refs": [],
  "close_topic": true,
  "close_reason": "no_new_evidence"
}
```

제출 명령:

```powershell
python math_dialogue.py submit --agent explorer --message-id 1 `
  --response-file .math_dialogue/responses/explorer-1.json
```

submit은 idempotent하다. heartbeat가 결과를 받기 전에 끊겨 같은 파일을 다시 제출해도 자식
메시지를 중복 생성하지 않는다. lease가 만료된 미완료 작업은 다음 heartbeat가 다시 선점한다.

## 8. 종료 장치

topic 생성 시 두 한계를 반드시 설정한다.

- `max_rounds`: 메시지 사슬의 최대 깊이
- `max_messages`: topic 전체 메시지 수

개별 메시지에는 TTL이 있고, 선점에는 lease가 있다. 다음 경우 agent가 topic을 닫는다.

- 새 정의·근거·반례 없이 같은 주장만 반복
- 결정론적 검증이 필요해 LLM 토론만으로 진전할 수 없음
- 전제가 모호하여 인간의 선택이 필요함
- 다음 응답이 라운드/메시지 한도를 넘음

## 9. 테스트

실제 Codex task를 만들기 전 프로토콜 자체를 검사한다.

```powershell
python math_dialogue.py selftest
```

이 테스트는 임시 DB에서 다음을 확인한다.

1. explorer → skeptic → explorer 3단계 토론
2. 마지막 요약과 자동 종료
3. 동일 응답 재제출의 idempotence
4. 네 worker의 동시 선점에서 중복 message ID가 나오지 않음

그다음 §5의 수동 heartbeat 왕복이 실제 Codex 연동 테스트다. 자동화는 이 두 테스트가 모두
통과한 뒤 켠다.

## 10. 운영 권고

- 처음에는 topic 하나만 연다.
- explorer가 제안하고 skeptic이 먼저 반증한 뒤 synthesizer가 정리하게 한다.
- 증명 초안에는 가정·정량자·범위·실현가능성을 반드시 적는다.
- 계산 주장은 실행 명령과 산출물 경로가 없으면 `NUMERICAL`로도 승격하지 않는다.
- `.math_dialogue/` DB는 복구 가능한 런타임 대화이며, 장기 공유 기억은 기존 ledger와 Git이다.
