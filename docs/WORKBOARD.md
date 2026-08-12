# docs/WORKBOARD.md — 활성 작업 인덱스 (비권위 스냅샷)

> **source of truth는 GitHub Issues의 `ai-task` 라벨 검색입니다.** 이 파일은 매 PR마다
> 갱신되지 않는 **비권위(non-authoritative) 스냅샷**이며, `develop → main` 승격 시점
> (`docs/AI_WORKFLOW.md` §9)에만 동기화됩니다. 지금 당장 활성 작업을 정확히 보려면
> Issues를 `ai-task` 라벨로 검색하세요. (0006 — 매번 갱신 의무가 실제로 지켜지지 않아
> Issues와 이 파일이 어긋난 사례가 있었던 것을 반영해 정책을 낮췄습니다.)

지금 누가 무슨 작업을 하고 있는지 **한눈에 보는 인덱스**입니다. 상세 로그가 아닙니다 —
작업의 세부 진행/논의는 해당 **Issue와 PR**에, 설계 결정은 `docs/DECISIONS.md`에 둡니다.

## 활성 작업

| Issue | 작업 | 담당 | 브랜치 | 상태 | 마지막 갱신 |
|---|---|---|---|---|---|
| #16 | GP 관계 테이블 컴파일 캐싱 | codex | codex/16-cache-compile-relations | review | 2026-07-12 |
| #69 | 수학 task 자율 토론 우편함 | codex | codex/69-math-dialogue-mailbox (PR #70) | review | 2026-08-12 |
| — | 계산 의무 전달 계층 (request/result v1) | claude | claude/71-computation-relay | review | 2026-08-12 |

> ⚠ `claude/71-computation-relay` 는 **PR #70 위에 쌓은 후속 브랜치**입니다. `math_dialogue.py`
> 를 확장하므로 PR #70 이 먼저 병합돼야 하고, PR #70 의 브랜치는 codex 소유이므로 직접
> 수정하지 않았습니다. HANDOFF 는 해당 PR 본문에 있습니다.

<!-- 예시 행(실제 작업이 생기면 이 형식으로 추가):
| #12 | 재배향 프로파일링 | codex | codex/12-profile-reorientation | active | 2026-07-12 |
| #13 | 캐시 설계 검토 | claude | claude/13-cache-design | review | 2026-07-12 |
-->

상태 값: `planned` | `active` | `blocked` | `review` | `done`

## 완료 (최근)

| Issue | 작업 | 담당 | 병합 PR | 완료일 |
|---|---|---|---|---|
| — | 협업 인프라 정비(문서·템플릿) | claude | (svtmrg 브랜치 직접) | 2026-07-11 |
| #5 | store.py 정리 — ResultsStore.to_dict() 죽은 코드 제거 | codex | #6 | 2026-07-12 |
| #7 | semantic core-contract CI + 협업 문서 정합성 (ChatGPT 리뷰 0006 반영) | claude | #8 | 2026-07-12 |
