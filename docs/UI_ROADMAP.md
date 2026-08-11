# docs/UI_ROADMAP.md — 대시보드 UI 로드맵

> ## ⚠ 이 문서는 폐기되었습니다 (0029)
>
> 여기 기술된 Streamlit 대시보드(`dashboard.py`, `ui_helpers.py`, `autonomous_ui.py`)는
> 2026-08-09 에 제거되었습니다. 사용자가 루프 실행과 현황 확인을 대화창(코딩 CLI
> 에이전트)에서 하기로 했기 때문입니다 — `docs/DECISIONS.md` 0029 참조.
>
> **설계 기록으로만 남겨 둡니다.** 여기 적힌 UI 원칙(수학 용어는 순화하지 않는다,
> 신뢰 등급을 표시에서 섞지 않는다, 예상 소요 시간을 약속하지 않는다)은 여전히
> 유효하며, 지금은 `research_cycle.py` 의 보고서/프롬프트와 `conjecture.py` 의
> 등급 체계가 그 역할을 이어받았습니다.


이 문서는 `dashboard.py`(Streamlit) UI가 어떤 사용자를 위해, 어떤 원칙으로 설계됐고,
지금 어디까지 구현됐으며, 앞으로 무엇을 할 계획인지 기록한다. 사람이 ChatGPT와 함께
작성한 상세 계획(Issue #23)을 기반으로 한다.

## 1. 사용자 persona

- **수학적 개념은 잘 안다**: dimension/rank, oriented matroid, realizability,
  circuit/cocircuit, acyclic/totally cyclic, convex position, reorientation,
  witness, McMullen number/upper bound.
- **프로그램 내부 구조는 모른다**: backend override, thread, cache, JSON 내부
  필드명(`criteria_satisfied`, `reward` 등), Python 모듈 구조, 임시 파일 경로.

→ UI는 수학 용어를 순화하지 않는다. 대신 프로그램 내부 개념만 화면에서 숨긴다.

## 2. UI의 핵심 원칙

1. **수학적 정확성** — "가능한 모든 배치"처럼 부정확한 표현을 쓰지 않는다. 각 탐색
   클래스가 실제로 무엇을 생성하는지(전수/표본, 실현가능/비실현 포함 여부)를 정확히
   설명한다.
2. **검증 수준 구분** — 결정론적으로 검증된 결과(A), 검증된 표본에서 관찰된 경험적
   패턴(B), 미검증 AI 가설(C), 게이트를 통과해 채택된 탐색 규칙(D)을 절대 섞지 않는다.
3. **내부 구현 세부 숨김** — thread/cache/JSON 필드명 같은 프로그램 내부 개념은 기본
   화면에 노출하지 않는다. 다만 이걸 위해 핵심 판별/탐색 로직을 재구현하거나 우회하지
   않는다 — 이미 계산된 값을 정확히 라벨링해서 보여줄 뿐이다.
4. **결과의 provenance 유지** — "이번 실험에서 검사해 만족한 조건"과 "이 chirotope가
   가질 수 있는 모든 수학적 성질"을 혼동하지 않는다. raw chirotope/JSON은 항상 고급
   expander 안에만 둔다.

## 3. Phase 1에서 실제 구현한 항목

- 화면을 **실험 설계 / 실행 현황 / 결과와 가설** 3개 탭으로 재편(`st.tabs`).
- 실험 설계를 `st.form` 기반으로 구성 — 폼 제출은 "미리보기/검증"만 하고, 실제 실행은
  별도 버튼으로 분리. 실행 중에는 이 버튼이 비활성화되고 안내 문구가 뜬다(기존 실행을
  조용히 자동 중단하지 않음).
- 실행 시점의 설정을 `st.session_state`에 스냅샷으로 저장해 실행 현황 탭에 고정
  표시(화면에서 그 사이 바꾼 값은 다음 실험에만 적용됨을 명시).
- `ui_helpers.py`(신규, 순수 함수 모듈): 클래스 표시 문구, 실험 문장 생성(criteria.py
  REGISTRY의 공식 설명을 그대로 재사용), 설정 검증, 현실성 경고(정성적 문구만, 정확한
  소요 시간 약속 안 함), 종료 사유 라벨링, ν(d)≤n−1 headline 생성.
- `om_classes.py`에 read-only 헬퍼 `has_generator(name)` 추가 — `lawrence`처럼 소켓에
  생성기가 연결되지 않은 클래스는 **실행 전에 버튼을 막는다**(예외를 던진 뒤 오류
  화면으로 보내지 않음).
- 탐색 클래스별 정확한 설명/경고: `uniform`(전수 아님, 비실현 포함 가능),
  `realizable_uniform`(실현가능 **표본**, 전체 열거 아님), `rank2_uniform`(literal
  rank-2로 해석하면 안 됨 — CLAUDE.md §5 경고), `cyclic`(기준선/시드, witness 탐색
  클래스 아님), `lawrence`(생성기 미연결로 실행 불가).
- 설정 검증: `n_min ≤ n_max`, `n_min ≥ rank+1`(회로가 존재하려면 필요), 실행 불가능한
  custom 클래스, `reorientable_to_convex`/`not_reorientable_to_convex` 동시 require(논리적
  부정 관계라 불가능) 검출. 오류가 있으면 실행 버튼이 비활성화된다.
- 실행 현황: `Progress.candidates`가 실제로 "사용자 조건을 통과해 witness 판정까지
  받은 후보 수"임을 코드로 확인한 뒤 그 의미로 라벨링(전체 생성 시도 수라고 주장하지
  않음). 종료 사유는 `best_upper_bound == 2d+1` 여부로만 "목표 달성"을 판단하고, 그
  외엔 "설정된 탐색이 끝나 종료"로만 표현 — 추측하지 않는다.
- 최선 결과를 `ν(d) ≤ n−1` 형태로 표시(`reward`는 기본 화면에서 제거, witness 상세의
  고급 expander 안에서만 참고용으로 노출).
- witness 상세를 기본 수학적 요약 / 검사된 조건(만족·불만족) / 원본 chirotope(고급
  expander, JSON 다운로드 포함) 순으로 재구성.
- 결과를 A(결정론적 검증)/B(Discovery 경험적 패턴)/C(AI 가설)/D(채택된 탐색 규칙) 4개
  절로 명확히 분리해 표시. Discovery 제안이 실제로 D로 채택됐는지도 대조해서 보여준다.
- 결과 JSON 업로드/다운로드, 실험 설정 JSON 다운로드 추가(기존 "로컬 경로 직접 입력"은
  고급 옵션으로 유지). 기존 결과 JSON과 완전히 하위 호환(스키마 무변경).
- 실행 편의성: `scripts/run_dashboard.bat` — 바탕화면에서 더블클릭 한 번으로 대시보드가
  브라우저에 뜨도록 하는 실행 스크립트(`docs/AI_WORKFLOW.md` §13 참고).

## 4. Phase 2~4로 미룬 항목과 이유

### Phase 2 — 영구 실험 관리
실험 ID/영구 저장(DB), 재시작 후 다시 열기, 중단된 실험 재개, 여러 실험 목록/비교,
병렬 큐, 임시 디렉터리 의존 제거.
**왜 지금 안 하는가**: 현재 `SearchRunner`는 단일 실행을 스레드 하나로 돌리고 결과를
`tempfile`에 쓰는 구조다(`progress.py`, `dashboard.py`). 영구 관리를 하려면 실행
식별자·저장소 스키마·재개 가능한 체크포인트 형식을 먼저 설계해야 하는데, 이건 UI
문제가 아니라 `progress.py`/`store.py` 수준의 아키텍처 결정이라 이번 PR의 "핵심 로직
무변경" 원칙과 직접 충돌한다.

### Phase 2 — 정확한 파이프라인 통계
전체 생성 시도 수, GP 적법성 통과 수, 중복 제외 수, require/forbid 필터 통과 수,
witness 검사 수, 단계별 처리 속도, 명확한 종료 이유(정확한 단계별 카운터).
**왜 지금 안 하는가**: 이런 세분화된 카운터는 `generator.py`/`search.py`의 루프 내부에
계측 지점을 추가해야 나온다. 이번 PR은 "현재 존재하는 카운터(`Progress.candidates`)의
실제 의미를 정확히 라벨링"하는 데 그쳤다 — 없는 값을 화면에서 지어내지 않는다.

### Phase 3 — 증거와 witness cohort 탐색기
각 발견(Finding)을 지지한 witness ID 목록, 반례 witness 목록, 비교한 non-witness
목록, witness cohort 저장, round별 발견 이력, circuit/cocircuit 분포 시각화, 재배향류/
대칭 상세 시각화.
**왜 지금 안 하는가**: `discovery.py`의 `Finding` 데이터클래스에는 그 발견을 뒷받침한
구체적인 witness ID가 저장되지 않는다(`invariant/value/kind/support/suggested_bias/note`
뿐). 이번 PR은 이 사실을 숨기지 않고, 있는 그대로("이번 실험에서 검사한 조건"까지만)
표시했다. 근거 witness를 추적하려면 `discovery.py`의 `Finding`에 witness id 리스트를
추가해야 하는데, 이는 이번 PR의 "핵심 로직 무변경" 대상에는 없지만 `discovery.py` 역시
검증 파이프라인의 일부라 신중한 별도 검토가 필요해 미룬다.

### Phase 3 — witness별 발견 round 표시 (추가로 발견된 격차)
계획 원문의 섹션 8은 witness 상세에 "발견 round"를 포함하라고 했으나, `store.py`의
`ResultRecord`에는 `round` 필드가 없다(어떤 라운드에서 발견됐는지 기록되지 않음).
**왜 지금 안 하는가**: 추가하려면 `store.py`(`ResultRecord`)와 `search.py`(`add_result`
호출부)를 수정해야 하는데, 이 두 파일은 이번 PR에서 명시적으로 "건드리지 않는다"고
정한 핵심 로직 파일이다. 순수 추가·하위 호환 필드([Optional] 이라 기존 JSON도 그대로
열림)라 위험은 작지만, 그래도 명시된 제외 범위를 넘어서는 변경이라 이번 PR에서는
보류하고 다음 단계에서 사용자 승인을 받아 진행한다.

### Phase 3 — `관찰만 함`(observe) 조건
필터에는 안 쓰지만 모든 후보에서 측정만 하는 `observe` mode.
**왜 지금 안 하는가**: `criteria.py`의 `mode`는 `require/forbid/target` 3가지로 고정돼
있고(`CriterionReport`도 이 3가지만 집계), `observe`를 추가하려면 `CriteriaSet.evaluate()`
의 집계 로직과 저장 스키마(관찰값 분포)를 함께 바꿔야 한다 — criteria.py의 판정 의미
변경이라 이번 PR 범위 밖.

### Phase 4 — 복합 클래스 작성기
AND/OR/NOT 조건식, 매개변수형 조건 조합, 저장 가능한 preset, 클래스와 backend의 독립
선택, realizability/rank/구조적 family를 별도 축으로 분리.
**왜 지금 안 하는가**: 현재 `om_classes.py`의 `OMClass`는 수학적 클래스(무엇을 탐색할
지)와 생성 방법(backend)을 하나로 묶고 있다. 이걸 독립된 두 축으로 재설계하는 건
`om_classes.py`의 데이터 모델 자체를 바꾸는 일이라 이번 PR의 "전면 재설계 안 함"
원칙과 직접 충돌한다.

### Phase 4 — 자연어 연구 질문
"acyclic이고 symmetry order가 4 이상이며 totally cyclic이 아닌 rank-6 OM을 조사하라"
같은 자연어 입력.
**왜 지금 안 하는가**: 반드시 (1)자연어 입력 → (2)등록된 조건식으로 변환 → (3)해석
결과를 사용자에게 표시 → (4)사용자 확인 → (5)실행 의 5단계를 거쳐야 안전하다(LLM이
등록되지 않은 성질을 임의 코드로 만들어 바로 실행하면 신뢰 모델이 깨진다 — CLAUDE.md
§1). 이 변환 계층 자체가 새로운 서브시스템이라 이번 PR 범위가 아니다.

### Phase 4 — 새로운 수학적 계열(REOM, 일반 Lawrence, matching field, non-uniform 등)
**왜 지금 안 하는가**: 이건 UI 기능이 아니라 수학적 표현과 생성기 구현이 먼저 필요한
문제다. 생성기와 검증 의미가 준비되기 전에는 UI에 실행 가능한 기능처럼 표시하지
않는다(실제로 `lawrence`는 이번 PR에서 실행 버튼을 막았다).

## 5. 다음 구현의 권장 순서

1. **Phase 3 — witness별 발견 round**: `store.py`에 `Optional[int] = None` 필드 하나만
   추가하는 가장 작은 변경. 사용자 승인 후 우선 진행 권장.
2. **Phase 2 — 정확한 파이프라인 통계**: `generator.py`/`search.py`에 계측 지점을
   추가해 "왜 탈락했는지"를 더 세밀하게 보여줄 수 있다. Discovery/학습 루프의 신호도
   더 풍부해진다.
3. **Phase 3 — witness cohort 탐색기**: 2번과 함께 `discovery.py`의 `Finding`에 근거
   witness id를 추가하면 자연스럽게 이어진다.
4. **Phase 2 — 영구 실험 관리**: 연구가 길어질수록 필요해지지만, 저장소/재개 형식
   설계가 선행돼야 하므로 뒤로 미룬다.
5. **Phase 4 — 복합 클래스 작성기 / 자연어 질문**: 가장 큰 재설계가 필요하므로 마지막.
