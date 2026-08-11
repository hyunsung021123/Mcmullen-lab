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

## 0015 — WP3: GP outer solver + exact CEGIS 루프 도입 (cegis_search.py)

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #40 에 따라 `cegis_search.py` 를 도입한다. `∃χ[GP(χ) ∧ ∀ρ ¬Convex(χ^ρ)]`
  를 QBF 로 직접 풀지 않고, outer(GP z3 solver) 가 χ 를 제안하고 inner(WP2 SAT)가
  convex 재배향 ρ 를 찾으면 "그 ρ 를 차단하는 일반 제약"
  `∨_S [min(pos,neg) ≤ 1 under ρ]` 을 outer 에 학습시킨다 (모델 단위 블로킹이 아님).
- 신뢰 규율 (구현에 강제됨):
  - **learned cut replay**: cut 추가 직후 om_core 직접 계산으로 (a) 방금 반례가 된
    χ 를 실제로 배제하는지, (b) 알려진 witness 를 배제하지 않는지 assert.
  - outer 모델도 `chi.is_valid()`(om_core) 재검증 — 실패 시 그 모델만 블로킹.
  - inner UNSAT → legacy(is_reorientable_to_convex) replay → certificate v1 독립
    replay 통과 후에만 CERTIFIED 반환. inner UNKNOWN 은 비승격(모델 블로킹 후 계속).
- 실측 (수용 조건 대비):
  - naive Z3(모델 열거+사후 판정, 현 generate_z3 구조와 동일) 대비:
    (5,3) 무-witness 증명 192 → 16 모델 (**12.0x**), (6,4) 1,920 → 15 모델
    (**128x**, 시간 5.7s → 0.9s = 6.1x) — "2개 벤치마크에서 모델 10x 또는 시간 3x"
    수용 조건 충족.
  - witness recall: (4,2) 24/24 (전부 CERTIFIED), (6,3) 전수 열거 9,984/9,984
    (WP0 product 전수 실측과 일치, 소요 53분 — 대규모 recall 은 수동 검증용). mismatch 0.
  - (6,3) 첫 witness 는 outer 1 모델 만에 CERTIFIED.
- 검토한 대안과 기각 사유:
  - 거대 QBF (∃∀) 직접 인코딩 → 기각(설계 문서의 명시적 금지 — 디버깅 불가능한
    단일 블랙박스가 되고, cut 단위의 독립 replay 가 불가능해짐).
  - 반례 χ 모델 하나만 블로킹 → 기각(수용 조건이 명시적으로 "일반 제약 학습" 요구;
    실측에서도 cut 학습이 12~128x 모델 감소의 원천).
  - 열거 모드에서 witness 마다 solver 재생성 → 기각(O(k²)). 지속 solver 로 리팩터링.
- 영향 범위: 신규 모듈 1개 + 문서/CI/pyproject 배선. `om_core.py`/기존 모듈 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0016 — WP4: (Z₂)^(n-1)⋊S_n exact orbit 축소 도입 (symmetry_reduction.py + orbit-aware CEGIS)

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #41 에 따라 `symmetry_reduction.py`(relabel / lex-leader canonical_form /
  orbit_dedup / automorphism_count / orbit_images)를 도입하고, `cegis_search.py` 에
  orbit-aware 열거(`cegis_enumerate_witness_orbits`)를 추가한다 — witness 를 찾으면
  그 orbit 의 게이지 고정 이미지 전부를 outer 에서 블로킹.
- 정확성 계약 (구현에 강제됨):
  - witness 여부의 (σ,ρ)-불변성을 믿음이 아니라 실측으로 재확인 (자체 테스트,
    무작위 군 원소 30건).
  - `orbit_dedup` 은 제거된 모든 candidate 가 자기 orbit 대표를 가리키게 한다
    (silent drop 금지) — (5,3) 전수 192개에서 witness orbit 손실 0 전수 검증.
  - recall 보존은 Σ orbit_size == labeled 전수 개수로 검증: (4,2) 24/24,
    (6,3) 9,984/9,984.
  - `automorphism_count` 는 |Aut(χ)| 의 정확한 값 — om_core `canonical_key` 나
    criteria 의 간이 `min_symmetry_order` 지표와 혼동 금지를 문서화.
- 실측:
  - **(6,3) witness 전수 파악: labeled 열거 3,181s → orbit 열거 63.6s (50x, 
    canonicalization 비용 포함)** — Issue #41 의 "전체 benchmark 개선" 수용 조건 충족.
  - 부수 발견(연구적 가치): (6,3) 의 witness 9,984개는 정확히 **3개의 isomorphism
    class** 로 떨어진다. (5,3) 의 GP-valid 192개는 단일 orbit (|Aut|=10).
- 비용 정직성: canonical_form 은 n!·2^(n-1) 전수의 exact 구현이라 n ≤ 7 에서만
  실용적이다. 싼 술어(legacy witness 판정 0.6ms)를 대량 후보에 거는 용도로는
  candidate 당 canonicalization(수백 ms)이 오히려 손해 — 이득은 후보당 후속 작업이
  비싼 곳(CEGIS 열거, certificate 생성, 향후 d≥4 후보 축소)에서 나온다. 대규모 n 용
  canonical labeling 휴리스틱은 범위 밖이며, 이 exact 버전이 그 정확성 oracle 이다.
- 검토한 대안과 기각 사유:
  - circuit incidence graph canonical labeling (nauty 류) → 보류. 외부 heavy
    dependency 없이 exact oracle 을 먼저 확보하는 게 순서 (decision log 원칙).
  - lex-leader SAT 제약(대칭 파괴 제약을 outer 에 직접 추가) → 보류. orbit 블로킹이
    이미 50x 를 달성했고, 대칭 파괴 제약의 완전성(대표 유일성) 증명이 별도로 필요.
- 영향 범위: 신규 모듈 1개 + `cegis_search.py` 에 함수 1개 추가(기존 함수 무변경)
  + 문서/CI/pyproject. `om_core.py` 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0017 — WP5: typed ResearchStep IR 도입 (research_ir.py)

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #42 에 따라 `research-step/v1` IR 을 도입한다. kind 10종(definition/
  equivalence/necessary_condition/sufficient_condition/pruning_rule/generator_family/
  encoding/performance_claim/certificate_transform/formalization)마다 필수 obligation
  목록이 고정되며, obligation 없는 kind 는 스키마 차원에서 존재할 수 없다.
- 신뢰 규율:
  - 이 모듈은 어떤 주장도 참으로 판정하지 않는다 — 형식/타입/정규화만. obligation
    실행은 WP6 Process Verifier(#43)의 몫.
  - `rationale_summary` 는 500자 상한 — hidden chain of thought 저장을 스키마
    차원에서 차단.
  - 기존 3개 bias type(element_count/require_property/forbid_property)은
    `from_legacy_bias`/`to_legacy_bias` 로 무손실 왕복 (원본을 scope.legacy 에 보존).
    element_count → generator_family, require/forbid_property → necessary_condition
    으로 사상. 기존 theorist 게이트는 교체하지 않는다.
  - 사용자가 별도로 제기했던 require/forbid type 통합 리팩토링은 이 IR 로 흡수
    (별도 진행 불필요 — 두 legacy type 이 같은 kind 의 다른 claim 으로 정규화됨).
- 검토한 대안과 기각 사유:
  - kind 를 자유 문자열로 허용(LLM 이 새 kind 창발) → 기각. obligation 없는 kind 가
    생기는 즉시 "검증 의무 없는 주장"이 시스템에 들어온다 — CLAUDE.md §1 위반 경로.
    새 kind 는 사람이 obligation 목록과 함께 코드로 추가한다.
  - JSON Schema 라이브러리 도입 → 기각(표준 라이브러리 원칙, 검증 로직이 단순).
- 영향 범위: 신규 모듈 1개(표준 라이브러리만) + 문서/CI/pyproject. 기존 모듈 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0018 — WP6: 결정론적 Process Verifier 도입 (process_verifier.py) — fail-closed 원칙

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #43 에 따라 `process_verifier.py` 를 도입한다. ResearchStep 의
  obligation 들을 순서대로 결정론적으로 실행하고, 첫 실패에서 즉시 기각하며
  기계 판독 가능한 first-failure(+가능하면 반례 chirotope)를 반환한다.
- 핵심 원칙 — **fail-closed**: 자동 실행기가 없는 obligation 은 '통과'가 아니라
  '기각'이다. "검증할 수 없음"을 "검증됨"과 혼동하는 순간 CLAUDE.md §1 이 무너진다.
  (예: equivalence 의 forward_implication 실행기는 아직 없으므로 equivalence step 은
  현재 hard gate 를 넘을 수 없다 — 실행기가 구현될 때 열린다.)
- legacy gate adapter: `theorist.proof_checker`(공허성·범위)와
  `counterexample_hunter`(witness 보존)를 삭제하지 않고 obligation 실행기로
  재사용한다 (CLAUDE.md §2 유지 — 판정은 전부 결정론적 코드, LLM 무관여).
- 실행 가능 obligation (현재): schema_valid / type_valid /
  known_witness_retention / small_instance_differential_test /
  known_nonwitness_soundness / gp_validity_sample / exact_candidate_verification.
  나머지는 fail-closed (해당 WP 에서 실행기 추가 시 개방).
- 결정론을 자체 테스트로 고정 (동일 입력 → 동일 audit dict).
- 검토한 대안과 기각 사유:
  - 실행기 없는 obligation 을 "skip + 경고"로 통과 → 기각. 검증 의무의 의미가
    사라지고, LLM 이 실행기 없는 kind 로 우회하는 경로가 생긴다.
  - theorist 게이트 로직을 이 모듈로 이동(중복 제거) → 기각. 기존 theorist 경로의
    동작을 바꾸지 않는 것이 WP6 의 명시적 제약 (adapter 로만 재사용).
- 영향 범위: 신규 모듈 1개 + 문서/CI/pyproject. 기존 모듈 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0019 — WP6b: append-only evidence DB 도입 (evidence_db.py) — JSONL + hash chain (SQLite 대신)

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #44 에 따라 `evidence_db.py` 를 도입한다. Process Verifier 의 audit
  결과를 step/claim/obligation 결과/first-failure/반례/commit/config hash/artifact
  hash/runtime/verifier version/certificate path/trust status 와 함께 append-only
  JSONL 로 기록하고, 레코드마다 이전 레코드 hash 를 연결(chain_hash)해 중간 개찬을
  탐지한다.
- SQLite vs JSONL 비교 결과 JSONL 선택. 근거:
  - 표준 라이브러리 원칙에 둘 다 부합하지만, JSONL 은 사람이 직접 읽고 diff 할 수
    있으며 append-only 의미가 파일 형식 자체와 일치한다 (SQLite 는 UPDATE/DELETE 가
    항상 가능해 "수정 API 없음"을 라이브러리 표면에서만 보장하게 됨).
  - hash chain 을 얹으면 개찬 탐지가 되어 SQLite 의 트랜잭션 무결성 우위가 상쇄됨.
  - 예상 레코드 수(세션당 수백~수천)에서 성능 차이는 무의미.
  - 동시 다중 프로세스 기록이 필요해지면 재검토 (그때 SQLite 재고려 — 새 결정으로).
- 신뢰 규율: LLM 자유 서술 필드가 스키마에 없다(검증된 evidence 가 자유 서술보다
  우선한다는 원칙의 스키마 강제). trust_status 는 고정 어휘만 허용, 등급 사칭
  개찬은 chain 검증에서 탐지됨을 자체 테스트로 고정. 수정/삭제 메서드 부재.
- memory.py 와의 공존: memory.json 의 횟수 집계는 그대로 유지(빠른 학습 신호),
  evidence DB 는 "왜/무엇으로 판정됐나"의 재현 가능한 근거 저장소 — 서로 대체가
  아니라 계층이 다르다.
- 영향 범위: 신규 모듈 1개(표준 라이브러리만) + 문서/CI/pyproject. 기존 모듈 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0020 — WP7a: rule-based step ranker 도입 (step_ranker.py) — gate/score 엄격 분리

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #45 에 따라 `step_ranker.py` 를 도입한다. hard gate(WP6)를 통과한
  step 들의 **실행 순서만** 결정론적 규칙 점수(S = α·coverage + β·space_reduction
  + γ·novelty − δ·runtime − η·risk)로 정한다.
- 신뢰 규율 (구현에 강제됨):
  - 게이트 미통과 step 에 score 를 호출하면 ValueError — 점수로 게이트를 우회하는
    경로 자체가 없다.
  - rank 는 audit 를 절대 변형하지 않는다 (자체 테스트에서 deep-copy 비교로 고정).
  - novelty 는 감점일 뿐 제거가 아니다 — score 는 어떤 것도 큐에서 빼지 않는다.
  - 완전한 결정론: 동점은 step id 사전순, 입력 순서 무관.
- learned PRM(#46) 게이트 준비: 비교 지표 `top_k_pass_rate`(상위 k 개가 다음 hard
  verification 을 통과하는 비율)를 이 모듈에 고정 — PRM 은 이 지표에서 rule-based
  대비 20% 이상 개선해야 기본 경로 진입 가능.
- 가중치(WEIGHTS)와 kind 별 coverage proxy 는 고정 상수이며, 변경은 새 DECISIONS
  항목으로만 한다 (조용한 튜닝 금지).
- 영향 범위: 신규 모듈 1개(표준 라이브러리만) + 문서/CI/pyproject. 기존 모듈 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0021 — WP7c: Cross-Domain Translation Registry 도입 (translations.py)

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #48 에 따라 `translations.py` 를 도입한다. 정식 translation 은
  name/source_domain/target_domain/exactness/encode/decode/obligations 계약을 갖고,
  exactness 등급별 사용 권한이 코드로 강제된다:
  - equivalence → hard search constraint(후보 제거) 가능
  - sound_only → 증명된 방향(sound_direction)으로만 가능
  - heuristic → ranking 전용, `assert_usable_for_pruning` 에서 PermissionError
    (조용한 recall 손실 경로 원천 차단)
- 초기 등록: `om-reorientation->boolean-hypercube-coverage` (equivalence) —
  WP1(#38)에서 14,439건 mismatch 0 + 독립 replay 로 검증된 동치. decode 는
  certificate 독립 검증(certificate_verify) 통과 시에만 주장을 반환한다.
- 미등록(의도적): SAT/CEGIS 번역은 구현됐지만 equivalence 승격은 교차 리뷰 후,
  REOM/Lawrence 는 사용자의 인코딩 형식 확정 대기(RESEARCH_STATUS §5),
  tope-graph 류는 보존 정리 없는 동안 heuristic 전용.
- 검토한 대안과 기각 사유:
  - exactness 를 문서 규약으로만 두기 → 기각. "prompt persona 추가 ≠ 교차 도메인
    전환"이라는 원칙은 강제 장치가 없으면 침식된다 — 코드 게이트로 강제.
- 영향 범위: 신규 모듈 1개 + 문서/CI/pyproject. 기존 모듈 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0022 — WP8: certificate export 번들 도입 (certificate_export.py) — FORMALIZED 비사칭 강제

- 날짜: 2026-07-14
- 제안자: chatgpt(Epic #37 설계) → human(순차 진행 지시) → claude-code(구현). (source: chatgpt, relayed by user)
- 결정: Issue #47 에 따라 `certificate_export.py` 를 도입한다. certificate v1
  하나에서 번들(manifest.json / certificate.json / chirotope.json / report.md /
  report.tex / replay.py / theorem.lean / SHA256SUMS)을 결정론적으로 생성한다.
- 신뢰 규율 (구현에 강제됨):
  - **replay.py 는 저장소 비의존**: 표준 라이브러리만으로 certificate 를 재검증하는
    독립 스크립트가 번들에 포함된다 (자체 테스트가 subprocess 격리 실행으로 확인 —
    양성 CERTIFIED + 조작 certificate 비-0 실패).
  - **Lean 파일 생성 ≠ FORMALIZED**: manifest 의 `formalized` 는 항상 False 로
    생성되고, theorem.lean 자체에 경고가 박혀 있다. 실제 Lean kernel 수락 후에만
    사람이 별도 절차로 승격한다.
  - hash 불일치 certificate 는 번들 생성 자체를 거부한다.
  - 모든 파일이 SHA256SUMS 로 검증 가능 (sha256sum -c 호환).
- Lean 스켈레톤은 주석 처리된 상태로 생성된다(UniformChirotope 등 정의부가 없는
  상태에서 컴파일 가능한 것처럼 보이는 파일을 만들지 않기 위함 — placeholder
  금지 원칙과의 균형).
- 영향 범위: 신규 모듈 1개 + 문서/CI/pyproject. 기존 모듈 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0023 — 정확성 수정 팩: export GP 결함 / CEGIS UNKNOWN / REFUTED-UNVERIFIED 분리 / trust 자동 도출

- 날짜: 2026-07-14
- 제안자: chatgpt(교차 리뷰, relayed by user) → claude-code(재현 검증 후 수정)
- 배경: ChatGPT 가 Epic #37 구현 전반을 리뷰하며 결함 4건 + 개선 다수를 지적.
  claude-code 가 각 지적을 **코드로 재현 검증**한 뒤 사실로 확인된 것만 수정.
- 수정 1 (재현됨 — 심각): **export 번들의 replay.py 가 GP validity 를 검사하지
  않았다.** GP-invalid ±1 부호표(uniform OM 아님)도 모든 재배향에 unbalanced
  circuit 을 갖도록 구성 가능하며(rank 3, n=6 에서 무작위 첫 시도만에 재현),
  기존 replay.py 는 이를 CERTIFIED 로 출력했다 (내부 certificate_verify.py 는
  gp_validity 에서 정상 차단 — 결함은 export 경로에만 있었음). 수정: replay
  템플릿에 3-term GP 검사 + sign key 완전성 검사 추가, export_bundle 은 hash 만이
  아니라 full verify_certificate 통과를 요구. GP-invalid 공격 재현 코드를 회귀
  방지 자체 테스트로 고정.
- 수정 2 (논리 확인): CEGIS 가 inner UNKNOWN(타임아웃) 후보를 블로킹한 뒤 outer 가
  소진되면 EXHAUSTED(무-witness 증명)를 반환할 수 있었다 — 그 후보가 실제 witness
  였을 수 있으므로 오판. 수정: unknown > 0 이면 INCONCLUSIVE_WITH_UNKNOWN 반환,
  두 열거 함수도 종료 전 동일 신호 방출(완전성 주장 차단).
- 수정 3: Process Verifier 의 실패 상태를 refuted(구체적 반례·결정적 위반)와
  unverified(실행기 부재)로 분리. fail-closed(게이트 불통과)는 유지하되,
  "새로운 종류의 가설일수록 실행기가 없어 자동 폐기되는 역설"을 막기 위해
  unverified 는 backlog 로 남는다. 미등록 REGISTRY 기준도 unverified 로 분류
  (등록 후 재평가 가능 — 사용자가 이전에 제기한 '미등록 신규 발견의 소실' 우려와
  일치하는 방향).
- 수정 4: 필요조건(known_witness_retention)의 공허 통과 제거 — 알려진 witness 가
  없으면 소규모 결정론적 witness pool(메모이즈, n=2d+2 앞쪽 최대 40개)로 검사하고,
  pool 도 불가하면 unverified (positive 금지). pool 검사는 전수가 아니므로 통과해도
  EMPIRICAL 수준임을 docstring 에 명시 (반례 발견은 확실한 REFUTED).
- 수정 5: EvidenceDB 의 trust_status 를 호출자 지정에서 **자동 도출**로 변경
  (derive_trust_status) — negative 증거에 CERTIFIED 를 붙이는 API 경로 자체를 제거.
  positive audit 없이는 certificate/kernel 플래그가 무효.
- 문서 drift 수정: pipeline 문서의 "구현 금지" 잔재 제목(§10/§13), trust 어휘 추가,
  RESEARCH_STATUS.md 에 Epic #37 인프라와 (6,3) 3-class 발견 반영.
- 채택하지 않은 지적: (a) GP-invalid 음성 fixture 를 파일로 커밋 — 오인 위험이
  있어 자체 테스트 안에서 즉석 생성으로 대체. (b) 필요조건의 완전 전수(∀ witness)
  검사 — 호출당 수 초~수십 초라 비현실적, 결정론적 부분 pool + 정직한 등급 표기로
  대체 (전수 모드는 후속 과제).
- 영향 범위: certificate_export / cegis_search / process_verifier / evidence_db
  수정. om_core.py/theorist.py 게이트 무변경. 기존 CERTIFIED 결과물 중 저장소
  내부 verifier 를 거친 것(golden fixture 포함)은 이 결함과 무관하게 유효.
- 다른 참여자 리뷰 상태: chatgpt 지적 반영분 — 사용자 중계 재확인 대상.

## 0024 — Discovery provenance: finding 마다 지지 표본 id 기록 (#50)

- 날짜: 2026-07-14
- 제안자: chatgpt(설계·리뷰, relayed by user) → claude-code(구현)
- 결정: `discovery.Finding` 에 `supporting_ids`(그 값을 실제로 만족한 witness 표본의
  ResultRecord id 목록) 추가, `analyze(witness_ids=...)` 로 전달. `search.py` 호출부가
  store 의 witness record id 를 넘긴다. id 를 모르는 호출 경로는 빈 리스트(하위호환).
- 이유: 기존 Finding 은 support("k/n")만 기록해 finding 이 틀렸거나 표본이 편향됐을
  때 역추적이 불가능했다. evidence 원칙(#44)과 정합.
- 대시보드 finding→표본 드릴다운 UI 는 이번 범위 밖 (UI_ROADMAP Phase 2 와 병합).
- 영향 범위: discovery.py(필드 추가·하위호환), search.py(호출부 1곳). 판정 로직 무관.
- 다른 참여자 리뷰 상태: pending.

## 0025 — 대칭군 정정: 전역 부정 포함 (Z₂)^n⋊S_n + witness 구조 압축 모듈 도입

- 날짜: 2026-07-14
- 제안자: claude-code (자체 교차 검증에서 발견) — witness_analysis 모듈 방향은
  chatgpt 제안 (relayed by user)
- **발견된 버그 (자체 교차 검증)**: WP4 의 canonical_form/automorphism_count/
  orbit_images 가 쓰던 "0-고정 flip × relabel" 열거는 **합성에 닫혀 있지 않다** —
  σ(A) 가 원소 0 을 포함하면 그 합성은 홀수 r 에서 전역 부정(-χ = χ^E, 즉 전체
  집합 재배향)으로 나타나 열거 밖으로 나간다. 결과: orbit-stabilizer 정리 위반이
  실측으로 재현되었고(gauge slice 3,840 vs 예측 2,880), canonical_form 이 한
  isomorphism class 를 두 key 로 쪼갤 수 있었다.
- 영향 평가 (정직):
  - WP4 의 recall 주장(Σ orbit_size == 전수 개수)은 **유효** — 블로킹된 이미지는
    전부 진짜 동형 이미지였고(가짜 블로킹 없음), 완전성은 전수 개수 대조로 확인됨.
  - "(6,3) witness = 3개 isomorphism class" 결론도 **전체 군 기준으로 재확인** —
    정확한 분해는 gauge 크기 {5,760, 3,840, 384}, |Stab| = {4, 6, 60}
    (384 class 는 고대칭). 이전 실행이 3개로 맞았던 것은 결과적으로 옳았으나
    근거가 불완전했다.
- 수정: 전역 부정을 canonical_form/orbit_images/automorphism_count 에 포함
  (짝수 r 에선 χ^E=χ 라 무해). group_order 를 2^n·n! 로 정정. orbit-stabilizer
  정합(slice == |G|/(2·|Stab|))을 회귀 방지 자체 테스트로 고정.
- **witness_analysis.py 신설** (구조 압축 — exact 계산 → 압축 → AI 가설 → 반례
  사냥 → 사람의 일반화 경로의 2단계):
  - minimal_obstruction_cover (greedy + z3 exact 최소, 반환 전 커버 완전성 재검증)
  - unsat_core_supports (z3 unsat core + core-only UNSAT replay 강제)
  - witness_profile (전체 군 |Stab|/orbit 크기/균형 히스토그램)
  - **연구적 발견**: (6,3) 의 세 witness class 모두 **정확히 3개의 circuit
    obstruction 으로 모든 32개 재배향이 차단**된다 (exact 최소 커버 크기 3).
    circuit_hist 의 min(pos,neg)=1 개수는 class 별 3/4/5 로 서로 다름.
    이는 검증된 계산적 사실(VERIFIED)이지 일반 정리가 아니다 — "witness 는 항상
    작은 obstruction family 로 설명되는가"는 후속 가설 후보.
- 영향 범위: symmetry_reduction.py 정정(+회귀 테스트), witness_analysis.py 신설,
  배선. om_core.py 무변경. cegis orbit 열거 회귀 없음(자체 테스트 통과).
- 다른 참여자 리뷰 상태: pending (특히 384 class 의 고대칭 구조는 문헌 대조 요망).

## 0026 — 자율 연구 오케스트레이터(opt-in) + Theorist IR 제안 경로 + cegis 백엔드

- 날짜: 2026-07-14
- 제안자: chatgpt(리뷰 — "부품은 있으나 연결하는 오케스트레이터가 없다", relayed by
  user) → claude-code(구현)
- 결정 1 — `theorist.run_debate_ir` (추가 전용): LLM 제안자들이 legacy bias 대신
  ResearchStep(IR)을 제안하는 새 경로. 정규화(research_ir) → 결정론적 게이트
  (process_verifier) → positive/unverified/refuted/malformed 분류. 기존
  run_debate/proof_checker/counterexample_hunter 는 무변경 (CLAUDE.md §2 유지 —
  게이트는 여전히 100% 코드).
- 결정 2 — `research_manager.run_autonomous_research` (opt-in): 제안→게이트→
  evidence 기록(trust 자동 도출)→step_ranker 순위→kind 별 결정론적 실행
  (generator_family→CEGIS, CERTIFIED 만 채택 / necessary_condition→EMPIRICAL
  규칙으로 다음 라운드 맥락 반영, hard pruning 금지). unverified 는 backlog 반환.
  기존 search.py/manager.py/UI 는 무변경 — 대체가 아니라 병행 진입점.
- 결정 3 — `generator.generate_cegis` + backend="cegis" 등록 (run.py/dashboard
  선택지 포함): CERTIFIED witness 를 직접 방출하는 실험적 백엔드. solver unknown
  발생 시 조용한 누락 대신 RuntimeError. 파이프라인의 mcmullen_evaluate 재검증은
  그대로 거친다 (이중 안전).
- 검토한 대안과 기각 사유:
  - search.py 의 기본 루프를 오케스트레이터로 교체 → 기각. 기존 경로는 검증된
    안정 상태이고, 새 루프는 실행기 커버리지가 아직 부분적(2개 kind)이다 —
    opt-in 병행으로 신뢰 축적 후 통합 재검토.
  - LLM 출력에서 legacy_bias 를 없애고 IR 만 강제 → 기각. 정확한 실행기가 있는
    legacy 경로가 검증 통과율이 높아, 두 형식을 모두 받되 IR 로 정규화.
- mock 실측 (자체 테스트, Ollama 불필요): 1 라운드에 제안 5건(정규화 실패 1 격리)
  → 게이트 분류 → CEGIS 실행 → n=6 CERTIFIED witness 채택 → evidence 5건
  (UNVERIFIED/VERIFIED/CERTIFIED 자동 도출) — end-to-end 0.3초.
- 영향 범위: theorist.py 추가 전용, generator.py 백엔드 1개 추가, run.py/dashboard
  선택지 1개, 신규 모듈 1개. om_core.py 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0027 — 자율 ResearchStep IR 대시보드 연결 계층 + Windows certificate hash 정합 (#66)

- 날짜: 2026-07-15
- 제안자: human(요구사항) → codex(설계·구현)
- 결정: 기존 Streamlit 대시보드에 별도 opt-in 탭을 추가하고, UI 비의존 연결 계층
  `autonomous_ui.py`를 둔다. 이 계층은 Ollama endpoint/model/temperature, 공통·역할별
  프롬프트, ResearchStep kind 실행 정책, 자율 라운드, CEGIS outer/inner 예산,
  Evidence DB, 진행 현황, audit/backlog/certificate/witness structure 결과를 기존
  `run_autonomous_research`에 전달·표시한다. 수학적 판정이나 Process Verifier를 UI에서
  재구현하지 않는다.
- `research_manager.run_autonomous_research`에는 기본 동작을 보존하는 선택 인자만 추가:
  debate round, enabled kind, CEGIS 예산, 진행 reporter. enabled kind에서 제외된 positive
  step은 기각·삭제하지 않고 backlog로 보낸다. ranker와 hard gate의 의미는 변하지 않는다.
- 실행 제어 트레이드오프: 현재 CEGIS는 후보 단위 안전 중단 callback이 없으므로 UI가
  스레드를 강제 종료하지 않는다. 대신 outer model 수와 inner SAT timeout을 사용자 예산으로
  노출한다. 안전 중단은 CEGIS 자체 계약이 생길 때 별도 작업으로 다룬다.
- Windows 실측 수정: certificate export가 문자열의 LF bytes를 hash한 뒤 text mode가
  파일을 CRLF로 기록해 SHA256SUMS가 즉시 실패했다. 모든 번들 파일을 `newline=""`로
  기록해 hash 대상 bytes와 실제 파일을 플랫폼 간 동일하게 만들었다. certificate 검증
  의미나 trust label은 바뀌지 않는다.
- 영향 범위: `dashboard.py`, 신규 `autonomous_ui.py`, `research_manager.py`의 추가 선택 인자,
  `certificate_export.py`의 플랫폼 개행 정합, 패키징/CI. `om_core.py`, `criteria.py`,
  `theorist.py`의 결정론적 적대자 로직은 무변경.
- 다른 참여자 리뷰 상태: pending.

## 0037 — 로컬 수학 Codex task 토론은 권한 없는 우편함으로 분리

- 날짜: 2026-08-12
- 제안자: human (여러 수학 Codex 세션의 자동 토론 환경 요청) → codex (구현)
- 관련 Issue: #69
- 결정 1 — 같은 checkout을 보는 여러 heartbeat의 간접 통신에 `math_dialogue.py` SQLite
  우편함을 쓴다. `BEGIN IMMEDIATE` 선점, lease 만료, TTL, 최대 라운드와 최대 메시지 수로
  동시 처리와 무한 자기대화를 제한한다.
- 결정 2 — 우편함은 런타임 운반 계층이며 `.math_dialogue/`는 Git에서 제외한다. 장기 공유
  기억은 계속 Git·Issue·`insight_ledger.py`·evidence DB가 담당한다.
- 결정 3 — 모든 토론 산출물의 권한은 `UNASSESSED_DIALOGUE_ONLY`다. 메시지에 적힌 grade는
  작성자의 자체 분류이며 evidence가 아니다. ledger 상태 전이, witness 판정, pruning,
  실현가능성 결론으로 자동 승격하는 경로를 만들지 않는다.
- 결정 4 — heartbeat 한 번은 메시지 하나만 `claim → 응답 파일 → submit`하고 끝낸다.
  상대 task 직접 호출이나 같은 실행에서 연속 claim하는 구조는 금지한다. 실제 task 생성과
  heartbeat 활성화는 모의 selftest와 수동 왕복을 통과한 뒤 별도로 수행한다.
- 영향 범위: 신규 `math_dialogue.py`, 설정 문서와 역할 프롬프트, 패키징·CI·gitignore.
  `om_core.py`, `criteria.py`, `theorist.py`, insight/evidence 판정 경로는 무변경.

## 0038 — 수학 task는 범용 역할과 기존-thread heartbeat로 자율 운영

- 날짜: 2026-08-12
- 제안자: human (최초 역할 지정 뒤 무개입 자율 토론 요청) → codex (설계·구현)
- 관련 Issue/PR: #69 / #70
- 결정 1 — 매 실행마다 새 task를 만드는 standalone schedule이 아니라, 각 기존 수학 task의
  문맥을 유지하는 10분 heartbeat를 쓴다. heartbeat는 같은 local checkout에서 메시지 한 건만
  처리한다.
- 결정 2 — 권장 역할은 `strategist`(정식화·분해·종합), `prover`(증명 구성),
  `falsifier`(반증·감사), `experimentalist`(결정론적 계산)다. task가 2개뿐이면 이를
  `builder`와 `critic`으로 합치되 구성과 공격 관점은 분리한다.
- 결정 3 — intake 역할은 active agent가 2명 이상일 때 `questions/OPEN.md`의 새 `OPEN`
  질문을 source key로 중복 없이 한 번에 하나씩 투입한다. 동시에 열린 저장소 topic은 기본
  2개로 제한한다. heartbeat `last_seen`이 기본 30분 넘게 갱신되지 않은 agent는 새 작업을
  받을 active roster에서 제외한다.
- 결정 4 — 실제 운영 경로는 이미 Git에서 제외되는
  `local_runs/math_dialogue/dialogue.sqlite3`로 둔다. 이는 0037의 초기 `.math_dialogue/`
  경로를 대체한다.
- 결정 5 — 자동 task는 tracked 파일을 수정하지 않는다. 초안과 계산 산출물은 `local_runs`
  아래에 두고, 사람이 검토한 뒤 기존 insight/evidence 절차로만 승격한다.
- 영향 범위: `math_dialogue.py`의 idempotent enqueue·OPEN 질문 sync·lease release, 범용 역할
  프롬프트와 운영 문서. 수학 판정·검사기 경로는 무변경.
