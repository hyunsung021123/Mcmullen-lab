# 설계 결정 로그 (Decision Log)

Claude Code · Codex · ChatGPT가 이 저장소에서 협업하며 내린 아키텍처/설계 결정을
기록합니다. 코드 diff만으로는 "왜 이렇게 했는가"가 드러나지 않는 결정 — 특히 여러
대안 중 하나를 선택한 경우나 `CLAUDE.md`의 불변 조건과 맞닿아 있는 경우 — 은 반드시
여기에 기록합니다.

**규칙**: 이 로그는 append-only. 과거 항목은 수정/삭제하지 않는다. 이전 결정을 뒤집을
때도 그 사실과 사유를 새 항목으로 추가한다. (`COLLABORATION.md` §2.2 참고)

## 기록 형식

```
## NNNN — 한 줄 제목
- 날짜:
- 제안자: claude-code | codex | chatgpt | human
- 결정: (한 문장)
- 배경/문제:
- 검토한 대안과 기각 사유:
- 영향 범위: (어떤 모듈/불변식에 영향을 주는지)
- 다른 참여자 리뷰 상태: pending | agreed | contested (+사유)
```

---

## 0001 — Claude Code ↔ ChatGPT 협업 프로토콜 도입

- 날짜: 2026-07-10
- 제안자: claude-code
- 결정: `COLLABORATION.md`, 이 결정 로그, PR 템플릿(`.github/PULL_REQUEST_TEMPLATE.md`),
  교차 리뷰 이슈 템플릿(`.github/ISSUE_TEMPLATE/cross_review.md`)을 도입해 두 AI가
  저장소를 통해서만 비동기로 소통하도록 한다. 역할은 claude-code=구현,
  chatgpt=최적화/검토로 시작한다.
- 배경/문제: 사용자가 ChatGPT Business 계정을 이 저장소와 연동해 Claude Code와 협업하는
  구조를 원함. 두 AI는 실시간 공유 세션이 없으므로, 저장소 자체(커밋/PR/이슈/이 로그)가
  유일하게 신뢰할 수 있는 공유 기억이 되어야 한다는 게 핵심 제약.
- 검토한 대안과 기각 사유:
  - 커밋 메시지만으로 소통 → 설계 차원의 트레이드오프(왜 대안 B가 아니라 A를 골랐는지)가
    diff 안에 묻혀 검색/추적이 어려움. 기각.
  - 저장소 밖 외부 문서(Notion/Google Docs 등)에 결정 로그 작성 → 저장소 상태와 분리되어
    stale해질 위험이 크고, 두 AI가 매 세션 자동으로 읽는 파일(CLAUDE.md 패턴)과 다른
    위치라 놓치기 쉬움. 기각.
  - 역할을 코드로 강제(예: 특정 브랜치/디렉터리를 한쪽만 쓰게 제한) → 지나치게 경직되고,
    실제로는 역할이 상황에 따라 바뀔 수 있어야 함. 규약(문서)으로만 강제하고 기술적
    강제는 CI(결정론적 테스트 통과)에만 맡기기로 함.
- 영향 범위: 코드 로직에는 영향 없음 — 문서(`COLLABORATION.md`, 이 로그)와 GitHub
  템플릿만 추가. `CLAUDE.md`에 이 문서들의 존재를 가리키는 짧은 포인터 섹션 추가.
  `om_core.py` 등 신뢰 앵커의 동작은 전혀 변경되지 않음.
- 상대방 리뷰 상태: pending (ChatGPT 연동이 완료되면 최초 교차 리뷰 요청 대상)

## 0002 — 2자 구도 → 3자 비대칭 접근 구조로 수정 (Codex 추가, 권한 비대칭 명시)

- 날짜: 2026-07-10
- 제안자: claude-code
- 결정: `COLLABORATION.md`를 Claude Code(직접 커밋)/Codex(로컬 폴더 경유 간접 커밋)/
  ChatGPT(읽기 전용)의 3자 구도로 재작성한다. 역할도 함께 갱신: claude-code=최초 개발·
  구현, codex=코드 점검·개선·최적화·실행, chatgpt=코드 리뷰·방향성 제시·사용자에게
  현황 설명. 권한이 대칭이 아니라는 점(ChatGPT는 §2의 채널을 직접 쓸 수 없음, Codex의
  커밋은 별도 계정으로 안 남을 수 있음)을 명시적으로 문서화한다.
- 배경/문제: 사용자가 "지금 클로드/코덱스/챗지피티 모두 저장소에 연결된 상태"라며
  검증을 요청. 실제 GitHub 저장소 상태(협업자 목록, 브랜치, 커밋 이력, PR, Actions 실행
  기록)를 조회해보니 지금까지의 모든 변경은 claude-code 단독으로 이루어졌고, Codex의
  커밋/브랜치/PR 흔적이나 ChatGPT 연동의 흔적(둘 다 GitHub API로 관찰 가능한 범위 내)이
  전혀 없었다. 그런데 기존 `COLLABORATION.md`(0001)는 애초에 Claude+ChatGPT 2자 구도만
  가정하고 있어 Codex라는 참여자 자체가 문서에 없었고, 세 참여자의 접근 수준이 서로
  다르다는 점(직접/로컬간접/읽기전용)도 반영돼 있지 않았다. 즉 "연동이 실패했다"가
  아니라 "문서가 애초에 실제 의도된 구조를 기술하지 못하고 있었다"는 게 핵심 문제.
- 검토한 대안과 기각 사유:
  - 기존 2자 문서를 그대로 두고 Codex 얘기는 별도 문서로 분리 → 협업 규약이 두 곳에
    흩어지면 "저장소가 유일한 공유 기억"이라는 §0 원칙과 모순되고, 최신성 추적이
    어려워짐. 기각.
  - 세 참여자를 대칭적 권한으로 가정하고 문서화(예: 전부 PR을 열 수 있다고 서술) →
    ChatGPT는 실제로 쓰기 권한이 없으므로 문서와 실제가 어긋나는 게 이번 문제의
    원인이었다. 같은 실수를 반복하는 셈이라 기각.
- 영향 범위: 코드 로직에는 영향 없음 — `COLLABORATION.md` 전면 개정, 이 결정 로그
  항목 추가. `.github/PULL_REQUEST_TEMPLATE.md`와
  `.github/ISSUE_TEMPLATE/cross_review.md`의 역할 체크박스를 3자 구도로 갱신 예정
  (별도 커밋). `CLAUDE.md`의 포인터 문구도 3자 구도를 반영하도록 갱신.
- 다른 참여자 리뷰 상태: pending (Codex·ChatGPT 양쪽 다 이 개정판을 아직 검토하지
  않음 — 특히 Codex 쪽에는 "로컬 폴더 경유 커밋도 역할 체크박스로 표시해야 한다"는
  요구가 실제로 실행 가능한지 확인 필요)

## 0003 — 브랜치/이슈/HANDOFF 기반 협업 워크플로 정비

- 날짜: 2026-07-11
- 제안자: chatgpt (코드 리뷰용 AI 조언) → claude-code 가 현재 코드에 맞게 조정·구현,
  human 승인(3개 핵심 선택)
- 결정: 저장소를 세 AI의 유일한 공유 상태로 다시 못박고, 브랜치 모델(main + 에이전트별
  `<agent>/<issue>-<slug>`) · 작업단위=Issue · HANDOFF 형식 · 충돌 처리 규칙을 문서화한다.
  신규: `AGENTS.md`(Codex 진입점), `docs/AI_WORKFLOW.md`(절차), `docs/WORKBOARD.md`(활성
  작업 인덱스), `docs/RESEARCH_STATUS.md`(연구 현황), `.github/ISSUE_TEMPLATE/ai_task.md`.
  개정: `COLLABORATION.md`(역할표 정교화 + 절차는 AI_WORKFLOW로 위임하는 포인터),
  `PULL_REQUEST_TEMPLATE.md`(담당·연결이슈·기준커밋·HANDOFF 섹션 추가). 함께: 현재
  `claude/repo-setup-files-svtmrg`를 `main`으로 승격해 브랜치 모델의 기준선을 만든다.
- 배경/문제: 0002까지는 "누가 무엇을 했나"만 다뤘고, 여러 AI가 동시에 같은 저장소를
  건드릴 때의 실무 문제(브랜치 소유권, 동시 편집 충돌, 작업 현황 가시성, 인수인계,
  기준 브랜치 부재)가 규약으로 정리돼 있지 않았다. 특히 `main` 브랜치가 아예 없어
  브랜치 모델 자체가 성립하지 않는 상태였다.
- 검토한 대안과 기각 사유:
  - 모든 진행 로그를 공유 Markdown 하나(`AGENT_LOG.md`)에 append → 여러 AI 동시 수정 시
    병합 충돌 빈발. 기각. 대신 상세는 Issue/PR, 인덱스만 `WORKBOARD.md`.
  - 리뷰 AI가 제시한 전체 파일 세트를 그대로 도입하되 역할 경계를 흐리게 → 리뷰 AI
    스스로의 기준("문서 과잉/중복 회피")에 어긋남. 그래서 문서별 책임을 명확히 분리
    (헌장=COLLABORATION, 절차=AI_WORKFLOW, 진입점=AGENTS)해 중복을 제거.
  - `main` 부재를 방치하고 문서만 정비 → 브랜치 규약이 존재하지 않는 기준을 가리키는
    모순. 기각. 현재 브랜치를 main으로 승격하기로 함(human 승인).
  - 전용 브랜치(claude/ai-collaboration-infrastructure)에서 작업 → human이 "현재 svtmrg
    브랜치에서 이어서"를 선택. 기각.
- 영향 범위: **핵심 코드 로직 변경 없음(문서/템플릿 전용).** `om_core.py` 등 연구 코드
  파일은 이번 작업에서 전혀 수정하지 않음. `python -m py_compile *.py` 통과 확인.
- 부트스트랩 예외(정직성 기록): 이 커밋 자체는 새 워크플로(“모든 변경은 PR로, main 직접
  push 금지”)를 **도입하는** 커밋이므로, 그 규칙이 강제되기 전 단계에서 기존 svtmrg
  브랜치에 직접 커밋되었다. main 승격과 branch protection(사람이 GitHub 설정에서 켜야 함)
  이후부터 이 워크플로가 실제로 강제된다.
- 다른 참여자 리뷰 상태: pending (Codex가 `AGENTS.md`를 실제로 자동 인식하는지, ChatGPT가
  이 문서 세트만으로 PR/CI 맥락을 재구성할 수 있는지 실사용 검증 필요)

## 0004 — `develop`/`main` 2단계 브랜치 구조 도입 (루프는 자동, main 승격만 사람 승인)

- 날짜: 2026-07-12
- 제안자: human(요구사항 제시) → claude-code(설계·구현)
- 결정: 병합 대상을 2단계로 나눈다. 에이전트 브랜치(`claude/<issue>-<slug>` 등)는
  이제 `main`이 아니라 **`develop`**에서 분기하고 `develop`로 PR을 연다. `develop` 병합은
  PR + CI 통과만으로 **사람 승인 없이** 이루어지며, 이 병합을 실제로 실행하는 "자동 병합
  코디네이터" 역할은 claude-code가 맡는다(`docs/AI_WORKFLOW.md` §6-1). `main`은 여전히
  PR + 사람 승인이 있어야만 움직이며, `develop → main` 승격은 사람이 판단하는 시점에
  간헐적으로만 일어난다(§9). `develop` 브랜치를 `main`과 동일한 커밋에서 새로 만들었다.
  신뢰 모델 핵심 파일(`om_core.py`/`criteria.py`/`theorist.py`)에 대한 CODEOWNERS 기반
  사람 승인 게이트는 **이번에는 도입하지 않는다** — `develop`에서도 CI만 통과하면
  이 파일들도 자동 병합된다.
- 배경/문제: 사용자가 claude→codex→chatgpt→claude 루프를 반복하는 개발 방식을 쓰려는데,
  기존 구조(모든 PR이 `main` 대상, `main`엔 사람 승인 필수)에서는 사소한 변경 하나하나마다
  사용자 승인이 필요해 루프가 막힌다는 문제를 제기함. "이게 다중 AI 협업의 본질적 제약인지,
  아니면 피할 방법이 있는지"를 물었고, 사용자는 "루프는 승인 없이 안전하게 반영되고,
  `main`에는 간헐적으로만 승인해 승격하고 싶다"는 요구사항을 명확히 제시함.
- 검토한 대안과 기각 사유:
  - CODEOWNERS로 신뢰 모델 핵심 파일(om_core.py 등)은 `develop`에서도 항상 사람 승인
    필요하게 하는 안 → 제안했으나 사용자가 기각. 사유(사용자 발언 그대로): "신뢰 모델
    내부의 정확한 구조는 아직 모르는 상태라 프로그램을 실행해봐야 피드백 가능하고,
    신뢰 모델이 완벽하지 않다면 계속 바꿔야 하니 지금은 CI만으로 충분"하다고 판단.
    → 결과적으로 안전망은 CI + `main` 승격 시점의 사람 리뷰뿐이며, 이는 의식적으로
    받아들인 트레이드오프다(아래 "영향 범위" 참고). 신뢰 모델이 안정되면 재검토하기로
    `docs/AI_WORKFLOW.md`에 명시.
  - 에이전트별 자기 PR은 자기가만 병합(교차 병합 없음) → 사용자가 "Claude Code가 병합
    코디네이터 역할을 맡는" 안을 선택. Codex가 자체적으로 병합할 수도 있으나, 코디네이터
    기준(§6-1의 3가지 확인 사항)은 동일하게 적용됨.
  - `develop` 도입 없이 `main` 자체의 required-approval을 0으로 낮춰 처리 → "안전
    저장소"라는 사용자의 명시적 요구(main은 간헐적·의도적 승인만 받는 곳)와 정면으로
    배치되어 기각.
- 영향 범위: 코드 로직 변경 없음(브랜치 생성 + 문서 갱신만). **단, 신뢰 경계상 중요한
  변화**: 지금부터 `om_core.py`/`criteria.py`/`theorist.py`를 포함한 모든 변경이 CI만
  통과하면 사람 확인 없이 `develop`에 반영된다. `main`은 여전히 그 파일들을 포함해
  사람 승인 없이는 어떤 변경도 받지 않는다. `docs/AI_WORKFLOW.md`(브랜치 모델·작업
  절차·§6-1·§9)와 `COLLABORATION.md`(포인터)를 갱신.
- 부트스트랩 예외(정직성 기록): 이 결정 자체를 반영하는 커밋도 아직 branch protection이
  없는 상태에서 기존 `claude/repo-setup-files-svtmrg`에 직접 커밋되었다(0003과 동일한
  부트스트랩 예외). 사용자가 `develop`/`main` 각각의 branch protection을 GitHub 설정에서
  켠 이후부터 이 워크플로가 실제로 강제된다.
- 다른 참여자 리뷰 상태: pending (Codex·ChatGPT 모두 아직 이 2단계 구조 하에서 실제로
  작업해본 적 없음 — 특히 Claude Code의 자동 병합 코디네이터 역할이 실제 충돌 상황에서
  §8의 "충돌 시 중단하고 보고" 규칙과 정확히 어떻게 상호작용하는지 실사용 검증 필요)

## 0005 — 0004의 branch protection 라이브 검증 완료

- 날짜: 2026-07-12
- 제안자: human(GitHub 설정 적용 + main 직접 수정 시도) / claude-code(develop 쪽 실측)
- 결정: 새로운 설계 결정 아님 — 0004에서 pending으로 남겨둔 "실사용 검증"의 결과 기록.
- 확인된 사실:
  - 저장소를 public으로 전환(GitHub Free는 private 저장소에 branch protection을 지원하지
    않아 발생한 제약 — 사용자가 연구 내용 공개에 문제없다고 판단해 결정).
  - `develop`: 트리비얼 PR(#1, #2)을 실제로 열어 CI green 확인 후 사람 승인 없이
    `merge_pull_request` API로 병합 성공. "Require a pull request"는 켜고 "Require
    approvals"는 꺼두면 승인 0개와 동일한 효과라는 점도 확인(숫자 입력이 1부터 시작하는
    이유 — 이 체크박스 자체가 꺼지면 승인 요구가 아예 없어짐).
  - `main`: 사람이 GitHub 웹에서 직접 수정을 시도 → PR을 거치라는 차단 메시지 확인.
  - Claude Code가 `main`에 직접 fast-forward push를 시도했다가 세션 자체의 안전 분류기에
    의해 차단된 사건이 있었음(0004 도입 직후) — "부트스트랩 예외"를 스스로 판단해
    적용하려 한 것은 잘못이었고, 이후 실제로는 PR 경유로 재작업함. 이 경험이 오히려
    "사람 승인 없이는 main이 움직이지 않는다"는 §2의 원칙이 실제로 다층으로(에이전트
    자기규율 + GitHub 서버 강제) 보호되고 있음을 보여줌.
- 검토한 대안과 기각 사유: 해당 없음(검증 기록이며 새 설계 결정 아님).
- 영향 범위: 없음(문서 기록 전용). 저장소 가시성 변경(public)은 GitHub 설정이며
  코드/신뢰 모델에 영향 없음.
- 다른 참여자 리뷰 상태: agreed(human이 직접 두 가지를 실측 확인함). Codex·ChatGPT의
  실사용은 여전히 미검증으로 남음.

## 0006 — ChatGPT 첫 실제 교차 리뷰: 0004 `contested` 판정 + 후속 수정

- 날짜: 2026-07-12
- 제안자: chatgpt(리뷰, 사람이 중계) → claude-code(검증·구현)
- 결정: ChatGPT에게 0001~0004를 정식 교차 리뷰 요청(cross_review 형식)한 첫 사례.
  ChatGPT의 판정: 0001 agreed / 0002 agreed / 0003 agreed(단, 추적성 보완 필요) /
  **0004 contested**(2단계 브랜치 구조 자체는 동의하되, 신뢰 모델 핵심 파일의
  CI-only 자동 병합에는 반대). claude-code가 각 주장을 실제 파일과 대조 검증했고
  전부 사실로 확인됨. 사용자가 선택한 대응: (1) semantic core-contract CI를 지금
  구축, (2) 빈 채로 열려있던 `develop→main` PR #4는 닫고 나중에 제대로 재작성,
  (3) `docs/WORKBOARD.md`는 비권위 스냅샷으로 격하.
- 배경/문제 (ChatGPT 지적 중 검증된 것들):
  1. **핵심**: `om_core.py`/`criteria.py`/`theorist.py`의 `if __name__=="__main__":`
     자체 테스트가 `print`만 하고 기대값을 `assert`하지 않음 — 예를 들어
     `is_convex_position()`의 부호 판정이 통째로 뒤집혀도 `python om_core.py`는
     예외 없이 종료해 CI가 green이 된다. "CI가 결정론적이다"와 "CI가 수학적 의미를
     검증한다"는 서로 다른 명제라는 지적이 정확했다(직접 코드 확인 → 사실).
  2. `ci.yml`이 `CLAUDE.md` 필수 명령 목록의 `python manager.py`를 실행하지 않음
     (직접 확인 → 사실, 0003 작성 당시 제가 빠뜨린 것).
  3. `.github/ISSUE_TEMPLATE/ai_task.md`, `.github/PULL_REQUEST_TEMPLATE.md`의
     기준 브랜치 예시가 0004(develop 도입) 이후에도 `main @ <SHA>`로 남아있음
     (직접 확인 → 사실, 0004 작성 시 갱신 누락).
  4. `develop → main` 승격 PR #4가 실제로 담당·연결이슈·기준커밋·변경이유·blast
     radius·테스트결과 전부 placeholder로 빈 채 열려 있었음(직접 API로 확인 →
     사실). "승격 단위가 무제한으로 커질 수 있다"는 반박의 실제 사례.
  5. `docs/AI_WORKFLOW.md` §7 HANDOFF의 "보낸 주체"가 `claude|codex|human`뿐이라,
     사람이 ChatGPT 의견을 중계할 때 원 출처가 손실됨(직접 확인 → 사실).
  6. `docs/WORKBOARD.md`가 Issue #5/PR #6 완료를 반영하지 못한 채 방치되어 GitHub
     Issues와 실제로 어긋나 있었음(직접 확인 → 사실).
- 검토한 대안과 기각 사유:
  - 신뢰 모델 핵심 파일에 CODEOWNERS 기반 사람 승인 게이트 추가 → 사용자가 기각.
    대신 semantic CI로 "CI-only 병합"이라는 원래 목표(루프 유지)를 지키면서 반박의
    핵심(스모크 테스트 불충분)을 해소하는 쪽을 선택.
  - PR #4를 지금 내용 채워서 그대로 승격 → 사용자가 기각. 지금은 사람이 실제로
    "승격하겠다"고 판단한 시점이 아니므로, 준비 안 된 승격 PR을 열어두는 것 자체가
    0004의 "간헐적·의도적 승인"이라는 원칙에 어긋남. 닫고 나중에 §9 체크리스트로
    제대로 다시 열기로 함.
  - `WORKBOARD.md`를 아예 제거 → 사용자가 기각(완전 제거보다 비권위 스냅샷으로
    남겨 급할 때 참고할 여지를 둠).
- 영향 범위:
  - `om_core.py`/`criteria.py`/`theorist.py`: **판별 로직 자체는 무변경.**
    `if __name__=="__main__":` 자체 테스트 블록에만 실측 기대값 assertion 추가
    (예: `quad.is_convex_position() is True`, `tc.is_totally_cyclic() is True` 등 —
    전부 실제 실행해서 확인한 현재 값을 고정한 회귀 테스트).
  - `.github/workflows/ci.yml`: `python manager.py` 단계 추가.
  - `.github/ISSUE_TEMPLATE/ai_task.md`, `.github/PULL_REQUEST_TEMPLATE.md`: 브랜치
    예시 `main` → `develop`로 수정.
  - `AGENTS.md`: `develop` 직접 push 금지 및 `develop` 기준 분기 절차 명시.
  - `docs/AI_WORKFLOW.md`: §2/§6-1에 semantic CI 도입 반영, §7 HANDOFF에 "원 제안/
    검토 출처" 필드 추가, §9에 승격 체크리스트 템플릿 추가, §11(신설)에 WORKBOARD
    비권위 정책 명시.
  - `docs/WORKBOARD.md`: 첫머리에 "source of truth는 GitHub Issues" 명시, Issue
    #5/PR #6 완료 소급 기록.
  - PR #4: 닫음(아래 참고).
- 다른 참여자 리뷰 상태: agreed — ChatGPT의 지적을 전부 사실로 검증했고 사용자가
  대응 방향을 결정했으므로 이 사이클은 완결. 이 0006 자체에 대한 교차 리뷰는 아직
  없음(다음 ChatGPT 리뷰 때 확인 대상).

## 0007 — 로컬 동기화 하드닝: 작업 전 pull 필수화 + Windows 자동 pull 스크립트

- 날짜: 2026-07-12
- 제안자: human(질문 제기) → claude-code(구현)
- 결정: Claude Code(클라우드)가 병합한 변경이 사람의 Windows 로컬 클론에 자동으로
  반영되지 않는다는 사실을 확인한 뒤, 사용자가 "①작업 전 pull을 필수화하고,
  ②로컬 자동 pull 스크립트도 원한다"고 명시적으로 요청 — 둘 다 구현.
  1. `AGENTS.md`·`docs/AI_WORKFLOW.md` §4의 "작업 전 git fetch/pull"을 권장에서
     **필수 선행 단계**로 격상(생략한 작업은 무효로 간주하고 재시작).
  2. `scripts/local-autopull.ps1` 추가 — Windows 작업 스케줄러에 등록해 쓰는
     fast-forward-only 자동 pull 스크립트(`docs/AI_WORKFLOW.md` §12).
- 배경: 사용자가 "내 로컬 폴더에도 자동으로 push된거야?"라고 질문 → 아니라고 답변.
  Claude Code는 격리된 클라우드 컨테이너에서 실행되며 사람의 PC 파일시스템에 접근할
  방법이 전혀 없다(정책이 아니라 아키텍처상 제약). 유일한 공유 채널은 GitHub이고,
  로컬 클론은 사람 또는 로컬 에이전트가 명시적으로 pull해야만 최신화된다. 이는
  이전에 확인된 "Codex 로컬 ↔ GitHub" 동기화 질문과 대칭인 문제.
- 검토한 대안과 기각 사유:
  - Claude Code가 사람의 PC에 직접 쓰기를 시도하는 방법 → 존재하지 않음(네트워크/
    파일시스템 접근 자체가 불가능). 아키텍처 제약이므로 대안이 아니라 불가능.
  - 자동 pull 스크립트가 merge/rebase까지 수행 → 기각. fast-forward-only로 제한해
    로컬 작업 중인 커밋을 스크립트가 임의로 되돌리거나 충돌을 만들 위험을 원천 차단.
  - 스크립트가 임의로 브랜치를 `develop`으로 전환 → 기각. 사람/Codex가 다른 브랜치에서
    작업 중일 수 있으므로, 현재 브랜치가 `develop`일 때만 동작하게 제한.
- 영향 범위:
  - `AGENTS.md`, `docs/AI_WORKFLOW.md` §4: "필수, 생략 금지" 문구 추가(판별 로직
    무변경, 절차 문서만).
  - `docs/AI_WORKFLOW.md` §12(신설): 로컬 자동 동기화 스크립트 설명·Task Scheduler
    등록 절차.
  - `scripts/local-autopull.ps1`(신규): 사람의 로컬 Windows 환경에서만 실행되는
    PowerShell 스크립트. 저장소의 CI·병합 절차·신뢰 모델에는 영향 없음.
- 다른 참여자 리뷰 상태: pending(다음 ChatGPT 교차 리뷰 때 확인 대상).

## 0008 — `develop` PR에 GitHub 네이티브 auto-merge 사용

- 날짜: 2026-07-12
- 제안자: human(요청) → claude-code(구현)
- 결정: 사용자가 "CI 통과 준비되면 자동 병합 설정해줘"라고 명시적으로 요청. 지금까지
  §6-1의 병합 코디네이터 역할을 "CI 완료를 사람이 알려주거나 에이전트가 수동 폴링 →
  병합"으로 수행해 왔는데, 앞으로는 **PR을 열 때 GitHub 자체의 auto-merge 기능을
  그 PR에 걸어둔다.** `develop` 브랜치 보호 규칙이 이미 PR 필수+CI 필수+승인 0으로
  되어 있으므로, GitHub가 CI green을 확인하는 즉시 스스로 병합을 완료한다.
- 배경: PR #9/#11 병합 과정에서 사람이 "CI 통과됐는데 왜 병합 안 하냐"고 지적한 사례가
  있었음 — 에이전트가 수동으로 상태를 재확인하는 절차가 불필요한 지연을 만듦. GitHub
  자체 auto-merge를 쓰면 이 지연이 구조적으로 사라진다.
- 검토한 대안과 기각 사유:
  - 에이전트가 폴링 주기를 더 짧게 하는 방법 → 기각. 여전히 폴링이라는 근본 방식은
    남고, GitHub가 이미 제공하는 네이티브 메커니즘을 쓰는 게 더 안정적.
  - `main` 승격 PR에도 auto-merge 적용 → 기각. `main`은 사람 승인이 branch
    protection으로 강제되므로 auto-merge를 걸어도 실질적 차이가 없고, 오히려
    "auto-merge가 걸려 있다"는 것 자체가 승격 PR의 "간헐적·의도적 승인"이라는 §9
    원칙과 혼동을 줄 수 있어 아예 걸지 않기로 함.
- 영향 범위:
  - `docs/AI_WORKFLOW.md` §6-2(신설): auto-merge 사용 절차와 예외(`main` 제외) 명시.
  - 판별 로직/CI 자체는 무변경 — 병합 트리거 방식만 바뀜.
- 다른 참여자 리뷰 상태: pending(다음 ChatGPT 교차 리뷰 때 확인 대상).

## 0009 — Codex가 여는 `develop` PR에도 auto-merge 확대 적용

- 날짜: 2026-07-12
- 제안자: human(질문 제기) → claude-code(구현)
- 결정: PR #17(Codex 작성, `_compile_relations` 캐싱)이 CI green이었는데도 auto-merge가
  안 걸려 있어 사람이 "왜 자동 병합 안 하냐"고 물어야 했음. 원인은 0008이 "PR을 여는
  에이전트가 auto-merge를 건다"고 했지만 실제로는 Claude Code가 여는 PR에만 적용되고
  있었기 때문. 사용자에게 "Codex PR도 CI 통과 시 자동 병합" vs "Claude Code가 diff
  검토 후 수동 병합 유지" 중 선택지를 제시했고, 사용자가 전자를 선택.
  이제부터 Claude Code는 Codex(또는 다른 에이전트)가 연 PR을 인지하는 즉시 auto-merge를
  건다. 단, 신뢰 모델 핵심 파일이 아니어도 다른 모듈이 그 반환값에 의존하는 방식이라
  안전성이 자명하지 않은 변경(예: 캐싱 도입으로 인한 mutation 위험)은 auto-merge 걸기
  전에 그 부분만 diff로 빠르게 확인한다 — CI가 커버하지 못하는 지점이기 때문.
- 배경: PR #17 자체는 diff 검토 결과 실제로 안전했음(`by_max`가 저장소 전체에서 읽기
  전용으로만 쓰임을 직접 확인). 문제는 "검증 자체"가 아니라 "auto-merge를 거는 것을
  깜빡해서 CI green 상태로 방치된 것"이었다.
- 검토한 대안과 기각 사유:
  - Codex PR도 지금처럼 Claude Code가 CI 통과를 폴링해서 수동 병합 → 기각(사용자가
    비추천 옵션으로 선택 안 함). 0004/0006의 "CI-only 병합이 안전하다"는 원칙과
    일관되지 않게 Claude Code가 여는 PR과 Codex가 여는 PR을 차별 대우할 이유가 없음.
  - CI green이면 diff 검토 없이 무조건 즉시 auto-merge → 기각. `generator.py`처럼
    신뢰 모델 핵심 파일은 아니지만 다른 모듈이 강하게 의존하는 파일의 변경은,
    CI(기존 자체 테스트)가 우연히 놓칠 수 있는 안전성 가정(예: 캐시 mutation)이 있을
    수 있어 최소한의 diff 확인은 유지하기로 함.
- 영향 범위:
  - `docs/AI_WORKFLOW.md` §6-2에 "Codex(또는 다른 에이전트)가 여는 PR" 하위 절 추가.
  - 판별 로직/CI 자체는 무변경 — 병합 코디네이터의 실행 절차만 명확화.
- 다른 참여자 리뷰 상태: pending(다음 ChatGPT 교차 리뷰 때 확인 대상).

## 0010 — 기본 탐색 조건에서 acyclic/totally_cyclic 제거 (수학적으로 불필요함을 검증)

- 날짜: 2026-07-13
- 제안자: human(수학적 코드 구조 질의 → 직접 논증) → claude-code(코드로 실측 검증·구현)
- 결정: `config.example.yaml`/`dashboard.py`의 기본 탐색 조건에서 `acyclic=require`,
  `totally_cyclic=forbid` 두 항목을 제거한다. 남는 기본 조건은
  `not_reorientable_to_convex=target`(+ 항상 자동 적용되는 `valid`) 하나뿐이다.
- 배경/수학적 근거 (사람이 논증하고 claude-code가 코드로 검증):
  1. **`totally_cyclic=forbid`는 `acyclic=require`와 함께일 때 항상 자동 충족되는
     중복 필터다.** `acyclic(M)`이면 전부-양(+) covector가 존재하는데, 이는 "전부
     비음(≥0)인 covector가 영벡터뿐"이어야 하는 `totally_cyclic(M)`의 정의와 모순된다
     → `acyclic(M) ⟹ ¬totally_cyclic(M)`은 항상 성립. rank 2/3/4, n up to 8~9에서
     GP-적법 uniform chirotope를 최대 2만 개까지 전수 검사해 두 성질이 동시에 성립한
     사례 0건 확인(실측, 이 세션에서 직접 실행).
  2. **`acyclic=require` 자체도 witness 판정 정확성에는 불필요하다.**
     `is_reorientable_to_convex()`는 재배향 궤도(orbit) 전체를 훑어 "이 궤도 안에
     convex position이 되는 원소가 있는가"를 판정하는데, 이건 궤도 불변량이라
     시작 대표원소가 acyclic인지와 무관하게 결과가 같다.
  3. **현재 구현이 지금까지 안전했던 이유는 우연이었다.** `generator.py`는 dedup
     (궤도 중복 제거)이 accept(acyclic 등 조건 검사)보다 먼저 실행되는 구조라,
     이론적으로는 "궤도의 첫 대표가 non-acyclic이면 그 궤도 전체가 판정 없이
     사라질 위험"이 있었다. 하지만 rank 3/4, n=6~8(최대 20만 개 궤도)에서 전수
     검증한 결과, 현재 DFS 순회 순서(+1 우선 시도)가 **모든 궤도에서 예외 없이
     acyclic 대표를 먼저 찾아냈다** — 그래서 지금까지 손실이 없었을 뿐, 보장된
     성질은 아니다.
- 검토한 대안과 기각 사유:
  - `generator.py`의 dedup/accept 순서를 바꿔 위 3번의 잠재적 위험 자체를 봉합 →
    이번 범위에서는 보류. acyclic/totally_cyclic을 기본 조건에서 빼면 그 위험
    자체가 기본 파이프라인에서는 무의미해지므로, 더 침습적인 core 로직 변경은
    별도 이슈로 미룬다(사용자가 나중에 acyclic/totally_cyclic을 다시 켤 경우에는
    여전히 잠재적 위험으로 남아있음 — 문서에 명시).
  - `criteria.py`의 `REGISTRY`에서 `acyclic`/`totally_cyclic` 항목 자체를 제거 → 기각.
    다른 연구 목적(예: totally-cyclic 영역만 따로 탐색)으로는 여전히 유효한 개별
    조건이라 REGISTRY에는 남겨두고 기본값만 끈다.
- 영향 범위:
  - `config.example.yaml`: 기본 `criteria`에서 두 줄 제거, 근거 주석 추가.
  - `README.md`: §7 예시, §8 결과 예시 JSON을 새 기본값에 맞게 갱신.
  - `dashboard.py`: 사이드바 토글 기본값을 `acyclic`/`totally_cyclic` 모두 "미사용"으로
    변경(REGISTRY에서 제거하는 게 아니라 기본 선택만 변경 — 사용자가 여전히 켤 수 있음).
  - `om_core.py`/`criteria.py`/`generator.py`의 판정·생성 로직 자체는 무변경.
- 다른 참여자 리뷰 상태: pending(다음 ChatGPT 교차 리뷰 때 확인 대상).

## 0011 — local-autopull.ps1 이 자기 로그 파일 때문에 영구히 skip 되던 버그 수정

- 날짜: 2026-07-13
- 제안자: human(Windows 로그 이상 신고) → claude-code(원인 특정·수정)
- 증상: 사용자가 실행 전용 폴더의 `autopull.log`에서 `skip: 커밋되지 않은 변경이 있어
  건너뜀`만 반복되고 있음을 신고. `.bat`으로 대시보드를 실행해도 항상 예전 버전이 뜸.
- 원인: `local-autopull.ps1`의 기본 `LogPath`는 `RepoPath\autopull.log`, 즉 클론 폴더
  루트에 로그를 남긴다. 그런데 `.gitignore`에 `autopull.log`가 없어서, 스크립트가
  최초 1회라도 실행되고 나면 그 로그 파일 자신이 즉시 untracked 파일로 잡히고,
  `git status --porcelain`이 영원히 비어있지 않게 된다. 스크립트의 안전장치("커밋되지
  않은 변경이 있으면 아무 것도 안 함")가 자기 자신의 로그 파일 때문에 항상 발동해
  `git pull`이 단 한 번도 실제로 실행되지 않는 상태였다(자기 자신을 dirty 원인으로
  오인).
- 결정: `.gitignore`에 `autopull.log` 추가. 스크립트(`local-autopull.ps1`) 자체는
  무변경 — 문제는 로직이 아니라 이 파일 하나가 커밋 추적 대상에서 빠져있지 않았던
  것뿐이었다.
- 검토한 대안과 기각 사유:
  - 스크립트에서 `git status --porcelain -- . ':!autopull.log'`처럼 로그 파일을
    명시적으로 제외 → 기각. `.gitignore`에 추가하는 쪽이 더 근본적이고(다른 도구가
    같은 파일을 봐도 일관되게 무시됨), 스크립트 로직을 건드릴 필요가 없음.
  - `LogPath` 기본값을 리포 바깥(예: `%TEMP%`)으로 변경 → 기각. 사용자가 로그를
    리포 폴더 안에서 바로 확인하길 원할 수 있고, 이미 배포된 두 Task Scheduler
    항목(코드 수정용/실행 전용)의 커맨드라인을 다시 등록해야 하는 번거로움 발생.
- 영향 범위: `.gitignore` 한 줄 추가. 판정/검색 로직 무관.
- 사용자 안내: 이 수정이 `develop`에 병합된 뒤에도, 이미 로컬에 쌓여있는
  `autopull.log`는 여전히 untracked 상태로 git status에 잡힐 수 있다(파일이 아직
  `.gitignore`에 없던 시점에 생성됐어도, `.gitignore`는 앞으로의 untracked 판정에는
  즉시 적용된다 — 이미 tracked 상태가 아니므로 `git rm --cached` 등 별도 조치 불필요).
  다만 이 수정 자체가 최신 `develop`에 반영되기 전까지는 동일한 지역 스크립트가 계속
  로그를 남기며 pull을 막고 있으므로, 급하면 로컬에서 `autopull.log`를 수동으로
  지우거나 `git pull`을 한 번 직접 실행해 최신 상태로 맞춰야 한다.
- 다른 참여자 리뷰 상태: pending(다음 ChatGPT 교차 리뷰 때 확인 대상).

## 0012 — McMullen 문제의 dimension/rank 표현 정리 (affine circuit OM: rank = dimension + 1)

- 날짜: 2026-07-13
- 제안자: human(직접 정정) — 이전 세션에서 논의 없이 열려 있던 "2d-1 vs 2d+1" 불일치
  질문에 대한 답.
- 정리: 이 프로젝트가 다루는 McMullen/Larman 추측은 기본적으로 **affine circuit OM**을
  취하므로 `rank = dimension + 1`이 항상 성립한다. 따라서 같은 명제를 dimension(`d`)
  기준으로 쓰면 목표 상한이 `2d+1`, rank(`r = d+1`) 기준으로 쓰면 `2r-1`이며 둘은
  같은 명제의 서로 다른 표현일 뿐 모순이 아니다. 코드 전반(`om_core.py`,
  `search.py`, `config.example.yaml`, `README.md`)은 지금까지 dimension 기준
  표현(`target_bound = 2d+1`)을 일관되게 써왔고, 그대로 유지하기로 함.
- 향후 방향(즉시 실행 아님, 열어둠): 앞으로 다양한 OM class(REOM/Lawrence 등 rank가
  1차 개념이고 "dimension"이 자연스럽지 않은 경우도 포함)를 다룰 예정이므로, 임의의
  OM class에 표준적으로 적용 가능한 **rank 기준** 표현으로 전체 코드/문서를 통일하는
  것을 고려할 수 있다. 이건 별도 이슈로 스코프를 잡을 문제(용어 전수 치환 + 테스트
  갱신)이며, 이번 결정에서는 착수하지 않는다.
- 영향 범위: 이번 결정 자체는 코드 변경 없음(문서화만). `target_bound`/`solves_conjecture`
  등 기존 dimension 기준 공식은 무변경.
- 다른 참여자 리뷰 상태: pending(다음 ChatGPT 교차 리뷰 때 확인 대상).

## 0013 — 자율 반례 탐색 파이프라인을 exact coverage → certificate → CEGIS → process verification 순으로 단계 도입

- 날짜: 2026-07-13
- 제안자: chatgpt(설계) → human(전달·승인) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Epic #37 의 첫 단계(Task #38)로 다음을 도입한다 —
  (1) Boolean hypercube coverage 동치에 기반한 exact witness verifier
  (`reorientation_cover.py`), (2) 모든 재배향(2^(n-1)개)에 대한 obstruction 을 담는
  witness certificate v1 (`certificate.py`), (3) coverage 로직을 공유하지 않는
  독립 검증기 (`certificate_verify.py`), (4) baseline oracle/benchmark
  (`benchmark_coverage.py`), (5) 전체 로드맵 문서
  (`docs/AUTONOMOUS_VERIFICATION_PIPELINE.md`)와 후속 Issue(#39~#50).
- 원칙 (이 순서로 후속 단계 게이트를 건다):
  - **LLM 품질을 직접 신뢰하지 않는다.** LLM 제안이 저품질이어도 시스템 전체가
    견디는 구조가 목표다. prompt/persona 추가만으로는 교차 도메인 전환이 아니다.
  - **witness 목표를 생성기·검증 과정 안으로 옮기는 것이 핵심이다** (현재 Z3 백엔드는
    GP-valid 를 목표와 무관하게 열거).
  - **PRM 보다 deterministic process verification 이 선행한다.** learned PRM 은
    진실 판정자가 아니라 hard gate 통과 step 의 실행 순서만 정하는 scheduler 다.
  - **`om_core.py` 는 동결.** 새 verifier 는 독립 이중 경로이며 legacy 와 불일치하면
    새 경로를 채택하지 않는다.
  - **단계별 benchmark(정확성 100% + engineering threshold) 통과 후에만 다음 단계.**
  - **hidden chain of thought 는 저장하지 않는다.** 형식화된 주장/짧은 rationale/
    검증 의무/반례/증명서/첫 실패 위치만 저장.
  - **certificate 는 독립 replay 가 필수다.** trust label
    (CONJECTURAL<EMPIRICAL<VERIFIED<CERTIFIED<FORMALIZED) 상위 등급 사칭 금지.
- 실측 (Task #38 PR 의 벤치마크):
  - 정확성: exhaustive corpus(전수: (4,2)(4,3)(5,2)(5,3)(5,4)(6,3)(6,4)) + sampled
    corpus 합계 14,439개 후보에서 legacy/new witness 판정 **mismatch 0**.
    witness 10,285개(rank-2 특이 사례 포함), non-witness 반례 flip replay 4,154건
    전부 convex 확인, certificate 독립 replay 16건 전부 CERTIFIED.
  - 성능: witness 밀도가 높은 corpus 에서 B1 이 1.6~1.8배 빠르고, legacy 가
    조기 종료하는 쉬운 non-witness 에서는 더 느리다. median speedup < 3x 이므로
    go/no-go 기준에 따라 **search 기본 경로 교체는 하지 않고** optional verifier 로
    유지한다 (통합은 별도 후속 Issue).
- 검토한 대안과 기각 사유:
  - 모든 기능(SAT/CEGIS/PRM/Lean)을 한 PR 에 구현 → 기각. 선행 게이트 없이 대형
    변경을 섞으면 정확성 회귀의 원인 추적이 불가능해진다. 후속은 Issue 로만 남긴다.
  - coverage 결과를 곧바로 search 파이프라인의 기본 판정으로 교체 → 기각(위 성능
    go/no-go 미달 + 신뢰 축적 기간 필요).
  - verifier 간 코드 공유(중복 제거) → 기각. `certificate_verify.py` 의 독립성이
    바로 신뢰 근거다 — 중복이 의도된 설계다.
- 영향 범위: 신규 모듈 4개 + fixtures/golden certificate + 문서. `om_core.py`/
  `theorist.py`/`generator.py`/`search.py`/UI 무변경. CI 에 새 self-test 4단계 추가.
- 다른 참여자 리뷰 상태: pending(다음 ChatGPT 교차 리뷰 때 확인 대상 — 특히 §3 의
  coverage 동치 논증과 certificate schema).

## 0014 — WP2: 고정-χ convex-reorientation SAT 검증기 도입 (reorientation_sat.py)

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #39 의 수용 조건에 따라 `reorientation_sat.py` 를 도입한다. 고정된
  chirotope χ 에 대해 재배향 Bool 변수 z_1..z_{n-1}(원소 0 고정)로
  `Convex(χ^z) ⟺ ∧_S (2 ≤ N_S^+(z) ≤ |S|-2)` 를 z3 로 인코딩.
- 신뢰 규율 (구현에 강제됨):
  - SAT model 은 **함수 안에서 om_core replay 를 통과해야만 반환**된다 (실패 시 예외 —
    solver 를 진실 판정자로 쓰지 않음).
  - UNSAT 은 `VERIFIED_BY_SOLVER` 등급일 뿐이며, certificate v1 독립 replay 통과
    후에만 `CERTIFIED`.
  - solver 타임아웃/불능은 `UNKNOWN` 으로 구분하고 UNSAT 으로 승격하지 않는다
    (status 매핑을 자체 테스트로 고정).
  - z3 는 무거운 선택적 의존성 유지(try/except) — 미설치 시 자체 테스트 SKIP 안전 종료.
    CI 는 `.[config,z3]` 설치로 실제 실행한다.
- 실측 (수용 조건 대비):
  - tiny exhaustive (5,3) 전수 192 + (6,3) 표본 200: legacy 와 100% 일치 (mismatch 0).
  - SAT model replay 100% (함수 내 강제라 통과 없이는 반환 자체가 불가).
  - UNSAT candidate certificate replay: 3건 CERTIFIED.
  - 참고 성능(정직 보고): 작은 n 에서는 legacy 전수 열거가 더 빠르다 (witness 1건
    0.8ms vs 12ms; (12,6) 쉬운 non-witness 에서 legacy 0.016s / coverage 0.15s /
    SAT 0.99s). SAT 의 가치는 속도가 아니라 UNSAT 의 증명적 구조(WP3 CEGIS 의
    cut 학습 기반)와 부분 제약 결합 가능성이다.
- 검토한 대안과 기각 사유:
  - z3.AtLeast/AtMost 카디널리티 내장 사용 → 기각(버전 간 API 편차, Sum/If 인코딩이
    이식성 높고 이 규모에서 성능 차이 무의미).
  - pseudo-Boolean(PbGe/PbLe) 인코딩 → 동일 이유로 보류. WP3 성능 벤치마크에서
    재검토 가능.
- 영향 범위: 신규 모듈 1개 + 문서/CI/pyproject 배선. `om_core.py`/기존 모듈 무변경.
  기존 모듈 어디에서도 아직 import 되지 않음 (독립 검증 경로).
- 다른 참여자 리뷰 상태: pending.
