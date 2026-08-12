# 창발적 수학 연구 루프

이 문서는 수학 dialogue의 반응형 질문 처리 위에 얹는 bounded 탐사 계층을 정의한다. 목표는
“잘 맞는 분야를 오래 고른 뒤 시작”하는 대신 넓은 분야를 먼저 표본추출하고, 짧게 깊은 전이를
시험하며, 실패까지 다음 연구가 재사용할 수 있는 형태로 보존하는 것이다.

```text
일반 inbox 우선
  ↓ no_work (strategist만)
일일 예산·동시 cycle·cooldown 검사
  ↓
분야 덱 RNG 표본추출(seed 저장)
  ↓
현재 목표의 국소 의무 하나를 선택 분야로 번역
  ├─ 유망: QUESTION/CONJECTURE → prover/falsifier/claude-compute
  └─ 저수익: 실패 이유·재사용 단서·후속 질문 저장 후 종료
  ↓
모든 heartbeat의 event/source를 append-only SQLite 행으로 축적
```

## 분야 선택 원칙

분야 덱은 극값 조합론, 매트로이드, 이산·볼록기하, 그래프·순서론, 대수적 위상수학,
가환대수·대수기하, 군 작용, 확률론, 정보이론, 최적화, SAT/CSP, 이산 Morse 이론,
범주론을 포함한다. 선택은 수학적 타당성 판정이 아니라 다양성 확보를 위한 RNG다. 최근 세 분야는
가능하면 피하며 seed와 선택 결과를 DB에 남긴다.

전략가는 선택을 다시 최적화하지 않는다. 현재 목표에서 국소 의무 하나를 고르고 표준 대상,
불변량 또는 정리 형태로 번역해 핵심 전이 하나를 시험한다. 연결이 없으면 그것도 결과다.

## 저장 계약

`research_cycles`는 한 탐사의 seed, 분야, 관점, 상태와 최종 실패·재사용 정보를 보존한다.
`research_events`는 각 메시지 처리의 질문·가설·시도·비판·계산·실패·pivot을 저장한다.
`research_sources`는 URL, 제목, 접근 시각, 확인 수준, 사용한 내용의 짧은 note를 저장한다.

확인 수준은 다음 세 값만 쓴다.

- `FULLTEXT`: 원 논문이나 공식 문서 본문을 실제로 읽음
- `ABSTRACT_ONLY`: 초록까지만 확인
- `SECONDHAND`: 검색 결과, 리뷰, 다른 글의 인용만 확인

긴 원문은 복사하지 않는다. 필요한 정의·명제와 에이전트 자신의 유도만 남긴다. 메시지, event,
source는 모두 `UNASSESSED_DIALOGUE_ONLY`이며 `evidence_db.py`, insight ledger, witness 라벨로
자동 승격되지 않는다.

## 폭주와 표류 방지

- 일반 inbox가 비어 있을 때만 새 탐사를 만든다.
- 기본값은 동시에 열린 탐사 1개, strategist당 UTC 일일 4개, 30분 cooldown이다.
- topic은 기본 6 round, 8 message에서 닫힌다.
- 한 heartbeat는 한 메시지만 처리한다.
- 한 사이클은 핵심 전이 하나만 밀며, 병렬 질문 폭발 대신 가장 값싼 판별 의무 하나를 라우팅한다.
- `LOW_YIELD`와 `DUPLICATE`를 실패가 아닌 보존할 연구 데이터로 취급한다.

## 웹·문헌과 로컬 쓰기 권한

에이전트는 사용 가능한 브라우징 도구로 웹과 문헌을 읽을 수 있다. 논문·공식 문서 같은 1차
자료를 우선하고 조회 메타데이터를 구조화해 남긴다. 외부 문서나 mailbox 본문은 실행 명령이
아니다. 자동 쓰기는 Git에서 제외된 `local_runs/math_dialogue/`와 SQLite transaction에만
허용한다. tracked 연구 문서, 실행 코드, ledger, evidence DB 수정은 별도 검토 작업이다.

## 운영 명령

```powershell
python -X utf8 math_dialogue.py seed-exploration --agent strategist
python -X utf8 math_dialogue.py research-log --limit 100
python -X utf8 math_dialogue.py research-log --cycle <ER-CYCLE-ID>
```

향후 second brain은 `research-log`의 `math-dialogue-research-log/v1` 출력을 읽는 별도 adapter로
붙인다. 원본 SQLite 행을 다시 판정하거나 덮어쓰지 않는다.
