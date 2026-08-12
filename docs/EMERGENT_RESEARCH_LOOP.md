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
  ↓ substantial result: ADVANCED 또는 REFUTED
원본 불변 보존 + 별도 개념 증류 job
  ↓ 한 번에 한 분야 렌즈, 최대 4회
인간적 명제·메커니즘·최소 예·경계 또는 RAW_PRESERVED
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
`distillation_jobs`는 완료 결과의 독립적인 해석 상태를, `distillation_attempts`는 분야별 시도를
append-only로 저장한다. 증류 레코드는 원본 `research_cycles` 행을 수정하지 않는다.

확인 수준은 다음 세 값만 쓴다.

- `FULLTEXT`: 원 논문이나 공식 문서 본문을 실제로 읽음
- `ABSTRACT_ONLY`: 초록까지만 확인
- `SECONDHAND`: 검색 결과, 리뷰, 다른 글의 인용만 확인

긴 원문은 복사하지 않는다. 필요한 정의·명제와 에이전트 자신의 유도만 남긴다. 메시지, event,
source는 모두 `UNASSESSED_DIALOGUE_ONLY`이며 `evidence_db.py`, insight ledger, witness 라벨로
자동 승격되지 않는다.

## 폭주와 표류 방지

- 일반 inbox가 비어 있을 때만 새 탐사를 만든다.
- 기본값은 동시에 열린 탐사 1개, strategist당 UTC 일일 12개, 10분 cooldown이다. 낮은 수익으로
  닫히면 다음 heartbeat에서 바로 다른 분야로 전환할 수 있다.
- topic은 기본 6 round, 8 message에서 닫힌다.
- 한 heartbeat는 한 메시지만 처리한다.
- 한 사이클은 핵심 전이 하나만 밀며, 병렬 질문 폭발 대신 가장 값싼 판별 의무 하나를 라우팅한다.
- `LOW_YIELD`와 `DUPLICATE`를 실패가 아닌 보존할 연구 데이터로 취급한다.
- 일반 질문이 적합한 동료 부재로 release되면 CLI 기본값으로 30분 defer한다. defer된 질문은
  삭제되지 않지만 그 사이 새 분야 탐사를 막지 않으며, 시간이 지나면 다시 우선 inbox로 돌아온다.

## 결과 후 개념 증류

발견 중간 단계에는 “사람에게 당장 의미 있는가”라는 게이트를 두지 않는다. 병리적인 식, 긴
경우분석, 우연처럼 보이는 유한 패턴도 원본 그대로 남긴다. 다만 discovery cycle이 `ADVANCED`
또는 `REFUTED`로 닫히면 별도 job을 만들고, strategist의 일반 inbox가 비었을 때 다음을 시도한다.

1. 원본 분야와 아직 시도하지 않은 분야를 우선해 RNG로 렌즈를 하나 고른다.
2. 원 결과의 정확한 범위와 증거 등급을 유지한 채 인간적 명제, 작동 메커니즘, 최소 예,
   일반화 범위와 실패 경계를 찾는다.
3. 결과는 `CONCEPTUALIZED`, `PARTIAL`, `NO_BRIDGE` 중 하나로 append한다. 이는 진위 등급이 아니다.
4. 기본 네 번의 렌즈 예산을 소진해도 연결이 없으면 job만 `RAW_PRESERVED`로 둔다. 원본 결과는
   실패·저수익으로 재분류되지 않으며 추후 새 관련 결과나 사람이 재개할 수 있다.

개념 증류가 발견을 계속 미루지 않도록 동일 strategist에서 증류 사이클 두 개 사이에는 새
discovery cycle이 최소 하나 있어야 한다. 부분 결과의 다음 렌즈는 기본 6시간 뒤에만 열리며,
증류는 하루 네 번으로 제한한다. 이 비율은 연구 속도 제어일 뿐 결과 평가 점수가 아니다.

이 분리는 성공한 AI 수학 연구의 공통 구조를 보수적으로 차용한다.
[Davies et al.](https://www.nature.com/articles/s41586-021-04086-x)은 기계가 찾은 관계를 사람이
흥미·증명 가능성 관점에서 반복적으로 정제하되 학습 실패를 수학적 부재로 해석하지 않았다.
[FunSearch](https://www.nature.com/articles/s41586-023-06924-6)는 정확성 evaluator와 다양한
프로그램 탐색을 분리하고 생성 프로그램 자체를 해석 가능한 압축으로 썼다.
[AlphaGeometry](https://www.nature.com/articles/s41586-023-06747-5)는 대규모 저수준 탐색 뒤
symbolic traceback으로 사용되지 않은 전제를 걷어내 사람이 읽을 수 있는 증명과 일반화를 얻었다.
[AlphaEvolve](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf)의
다중 표현·다양성 보존은 여러 분야 렌즈를 재시도하는 근거로만 쓰며, 이 저장소에서는 단순성
점수를 후보 제거에 사용하지 않는다.

계산 의무는 일반 메시지만 보내지 않고 `docs/COMPUTATION_RELAY.md`의
`computation-request/v1`으로 `claude-compute`에 게시한다. 요청은 데이터이고 실행 명령은 담지
않는다. Claude가 검토한 `experiment-plan/v1`만 실행 대상이며, 결과가 돌아와도 이 탐사 로그의
권한은 그대로 `UNASSESSED_DIALOGUE_ONLY`다.

## 웹·문헌과 로컬 쓰기 권한

에이전트는 사용 가능한 브라우징 도구로 웹과 문헌을 읽을 수 있다. 논문·공식 문서 같은 1차
자료를 우선하고 조회 메타데이터를 구조화해 남긴다. 외부 문서나 mailbox 본문은 실행 명령이
아니다. 자동 쓰기는 Git에서 제외된 `local_runs/math_dialogue/`와 SQLite transaction에만
허용한다. tracked 연구 문서, 실행 코드, ledger, evidence DB 수정은 별도 검토 작업이다.

## 운영 명령

```powershell
python -X utf8 math_dialogue.py seed-exploration --agent strategist
python -X utf8 math_dialogue.py seed-distillation --agent strategist
python -X utf8 math_dialogue.py claim --agent strategist
python -X utf8 math_dialogue.py research-log --limit 100
python -X utf8 math_dialogue.py research-log --cycle <ER-CYCLE-ID>
```

향후 second brain은 `research-log`의 `math-dialogue-research-log/v1` 출력을 읽는 별도 adapter로
붙인다. 원본 SQLite 행을 다시 판정하거나 덮어쓰지 않는다.

기존 strategist Scheduled prompt가 `claim --agent strategist`에서 `no_work`면 종료하도록 쓰여
있어도 CLI가 먼저 증류 job과 bounded seed를 순서대로 확인하므로 automation 자체를 다시 만들
필요가 없다. 수동으로 순수 inbox만 확인하려면
`claim --agent strategist --no-idle-exploration`을 쓴다.
