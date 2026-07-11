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
