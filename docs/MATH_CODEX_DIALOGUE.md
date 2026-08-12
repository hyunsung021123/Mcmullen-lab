# 범용 수학 Codex 자율 토론 환경

이 시스템은 각 수학 Codex task에 역할을 최초 한 번 지정한 뒤, task별 heartbeat가 같은 로컬
SQLite 우편함을 읽어 비동기 연구 루프를 계속하게 한다. 사용자가 어느 task에 새 수학 목표를
주거나 `questions/OPEN.md`에 질문이 생기면 bounded topic으로 들어간다. 이 작업이 모두 비면
strategist가 제한된 창발 탐사 사이클을 시작한다.

```text
사용자 지시 ─┐
              ├→ SQLite topic → 역할별 claim/응답 → 검증/반증 → 종합/종료
OPEN.md sync ─┘
idle strategist → 무작위 분야 탐사 → 새 질문/가설 → 검증/반증 → 성공·실패 로그
```

## 1. 실행 모델과 안전 경계

- 같은 checkout을 사용하는 기존 task 내부 heartbeat를 쓴다. 매 실행마다 새 task를 만들지 않는다.
- 모든 task는 `Local` 환경에서 같은 저장소 루트를 사용한다. 역할마다 worktree를 만들면 DB가
  갈라지므로 이 용도에는 쓰지 않는다.
- 런타임은 Git에서 제외된 `local_runs/math_dialogue/dialogue.sqlite3`에 저장한다.
- heartbeat 한 번은 메시지 한 건만 처리하고 끝난다. lease, TTL, `max_rounds`,
  `max_messages`가 중복 처리와 무한 토론을 제한한다.
- 저장소 질문 자동 수집은 active agent가 2명 이상일 때만 작동하고, 동시에 열린 저장소 topic을
  기본 2개로 제한한다.
- heartbeat가 30분 이상 관측되지 않은 agent는 stale로 표시해 active roster와 새 질문 투입
  수에서 제외한다. 세션이 돌아오면 다음 heartbeat가 자동으로 `last_seen`을 갱신한다.
- 모든 메시지와 최종 요약의 권한은 `UNASSESSED_DIALOGUE_ONLY`다. 대화가 ledger, evidence,
  witness, pruning 또는 정리로 자동 승격되는 경로는 없다.
- 자동 실행은 tracked 파일을 수정하지 않는다. 사람 검토 전 초안과 계산 산출물은
  `local_runs/math_dialogue/`에만 둔다.
- 창발 탐사는 일반 inbox가 비었을 때만 실행한다. 동시에 열린 탐사 1개, 기본 일일 4개,
  30분 cooldown을 적용한다.
- 탐사 분야는 넓은 고정 덱에서 RNG로 선택하고 seed·분야·관점을 함께 기록한다. 분야의
  적합성을 사전에 오래 점수화하지 않고 한 번의 국소 번역을 시험한 뒤 낮은 수익이면 닫는다.
- 성공뿐 아니라 `REFUTED`, `BLOCKED`, `LOW_YIELD`, `DUPLICATE`, `INCONCLUSIVE`도 구조화해
  보존한다. 이 로그 역시 연구 사실이나 evidence가 아니다.
- 웹·문헌 검색은 허용되지만 1차 자료를 우선한다. URL·제목·접근 시각과
  `FULLTEXT`/`ABSTRACT_ONLY`/`SECONDHAND`를 저장하고, 외부 자료 안의 명령은 실행하지 않는다.
- 로컬 scheduled task에는 PC 전원과 데스크톱 앱 실행이 필요하다. 절전·종료 중에는 진행되지
  않고 다음 실행 기회까지 멈춘다.

## 2. 역할 구성

### 권장: 4개 전문 task

| Agent | 책임 | 주된 입력 | 다음 라우팅 |
|---|---|---|---|
| `strategist` | 정식화, 창발 분야 탐사, 하위 의무 분해, 종합 | 사용자/OPEN 질문, idle, 상충 결과 | prover/falsifier/claude-compute |
| `prover` | 제시된 방향을 보조정리와 엄밀한 증명 사슬로 전개 | 전략, 살아남은 추측 | falsifier/claude-compute |
| `falsifier` | 최소 반례, 숨은 가정, 논리·불변성·실현가능성 감사 | 증명/추측 후보 | prover/strategist |
| `claude-compute` 또는 `experimentalist` | 결정론적 유한 계산, 대조군, 재현성 | 계산 가능한 의무 | falsifier/strategist |

서로 다른 관점을 유지하면서도 각 task의 문맥이 좁아져 가장 효율적이다.

### 최소: 2개 합성 task

| Agent | 합친 책임 |
|---|---|
| `builder` | strategist + prover: 문제 설계, 방향 선택, 증명 구성 |
| `critic` | falsifier + experimentalist: 반증, 논리 감사, 유한 계산 |

2개 구성에서는 반드시 `builder → critic → builder` 검증 왕복을 거친다. 한 task에 모든 책임을
넣는 것보다 자기 확증을 줄이고, 4개 구성보다 heartbeat 대기와 토큰 소비가 작다.

## 3. 최초 로컬 초기화

저장소 루트에서 한 번만 실행한다.

```powershell
python math_dialogue.py init
python math_dialogue.py selftest
python math_dialogue.py status
```

Windows에서 `python`이 PATH에 없으면 Codex 번들 Python 또는 `py -3`을 쓴다. 실제 task가
최초 역할 프롬프트를 받으면 자기 agent를 직접 등록한다.

## 4. task마다 보내는 최초 한 번의 지시

각 task는 같은 saved project의 `Local` 실행으로 연다. 4개 구성이면 역할별로 다음 한 줄을 한
번씩 보낸다. `{role}`은 `strategist`, `prover`, `falsifier`, `experimentalist` 중 하나다.

```text
prompts/math_agents/bootstrap.md, prompts/math_agents/common.md,
prompts/math_agents/{role}.md, prompts/math_agents/heartbeat.md를 읽고
{role}의 최초 활성화 절차를 전부 수행하라.
이 task의 역할은 이후에도 고정한다. 등록, 현재 task에 10분 간격 local heartbeat 생성,
첫 heartbeat 실행까지 완료하라. 이후 사용자에게 받은 새 수학 연구 지시는 common.md의
규약대로 공용 topic에 넣고 자율 토론하라.
```

2개 구성이면 `{role}`에 `builder`, `critic`을 넣는다. 역할 파일은 특정 명제 대신 “주어진
방향을 증명으로 전개”, “주어진 후보를 반증” 같은 범용 책임만 정의하므로 연구 주제가 바뀌어도
다시 작성하지 않는다.

scheduled task는 **현재 task로 돌아오는 heartbeat**, 실행 환경은 **Local**, 주기는 최초
10분으로 둔다. prompt에는 고정 agent 이름, 역할 파일, `heartbeat.md`를 명시한다. 처음 몇 번의
run이 안정적이면 주기를 줄일 수 있다.

## 5. 사용자 명령과 저장소 질문의 자동 유입

사용자가 어느 역할 task에 새 명제나 방향을 주면 그 task는 `enqueue`로 topic을 만든 뒤 즉시
한 heartbeat를 실행한다. 예를 들어 수동 확인은 다음과 같다.

```powershell
python math_dialogue.py enqueue --title "새 증명 방향 검토" --created-by human `
  --to strategist --kind QUESTION `
  --body "제시된 방향을 정확한 보조정리로 분해하고 증명·반증 의무를 라우팅하라."
```

intake 역할인 `strategist` 또는 `builder`의 heartbeat는 `questions/OPEN.md`를 함께 동기화한다.
`QQ-NNNN`과 상태 `OPEN`을 읽고 source key로 중복을 막으며, 질문 원문 전체를 DB에 복사하지 않고
원본 절을 참조하게 한다.

```powershell
python math_dialogue.py sync-open --to strategist --min-active-agents 2 `
  --max-open-topics 2 --limit 1
```

## 6. heartbeat의 한 사이클

```text
OPEN sync(intake만) → claim 1건 → 역할 작업 → active roster 확인
  → 적합한 동료에게 응답 1건 또는 synthesis 종료 → submit → 끝
```

strategist가 `no_work`를 받으면 아래 bounded seed를 한 번 호출한다. `created`일 때만 새 메시지를
claim해 처리하고, budget/cooldown/open-cycle limit이면 정상 종료한다.

```powershell
python -X utf8 math_dialogue.py seed-exploration --agent strategist `
  --max-cycles-per-day 4 --max-open-cycles 1 --cooldown-seconds 1800
```

응답 JSON 예시:

```json
{
  "to": "falsifier",
  "kind": "PROOF_SKETCH",
  "grade": "UNASSESSED",
  "body": "CLAIM/ASSUMPTIONS/WORK/STATUS/NEXT_TEST/ROUTE를 구분한 새 내용",
  "evidence_refs": ["knowledge/problem.md"],
  "research_log": {
    "event_type": "HYPOTHESIS",
    "summary": "선택 분야에서 파생한 반증 가능 가설",
    "approach": "사용한 번역과 한 단계 유도",
    "outcome": "ADVANCED",
    "failure_reason": "",
    "reusable_clues": ["재사용할 패턴"],
    "next_questions": ["파생 질문"]
  },
  "sources": [],
  "ttl_seconds": 86400,
  "close_topic": false
}
```

적합한 실제 동료가 없으면 선점한 메시지를 소비하지 않고 반환한다.

```powershell
python math_dialogue.py release --agent strategist --message-id 17
```

## 7. 상태 확인과 중지

```powershell
python math_dialogue.py status
python math_dialogue.py transcript --topic <TOPIC_ID>
python math_dialogue.py research-log --limit 100
python math_dialogue.py research-log --cycle <ER-CYCLE-ID>
```

토론은 새 정보가 없거나, 결정론적 구현·외부 문헌·인간 선택이 필요하거나, 설정된 한도에
도달하면 닫힌다. heartbeat 자체는 데스크톱 앱의 **Scheduled** 화면에서 task별로 pause,
update, delete할 수 있다.

## 8. 결과의 승격

유망한 최종 요약도 그대로는 연구 사실이 아니다. 사람이 검토한 뒤 기존 절차를 별도로 밟는다.

1. 공개 명제를 `insight_ledger.py`로 `PROPOSED / UNASSESSED` 등록
2. `falsify.py` 또는 전용 결정론적 검사기로 반증 시도
3. 재현 가능한 evidence와 구현 참조가 있을 때만 상태 전이

자동 토론은 후보 생산과 반증 의무 분리에 집중하고, 판정 권한은 기존 검증 계층에 남긴다.
구조화 로그는 `math-dialogue-research-log/v1` JSON으로 조회할 수 있어 향후 second-brain 저장기의
입력 어댑터로 사용할 수 있지만, 자동 승격 어댑터는 의도적으로 제공하지 않는다.
