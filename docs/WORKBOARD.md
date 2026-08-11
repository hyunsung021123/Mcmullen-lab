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
| #69 | 수학 Codex 토론 우편함 + 역할 자동화 | codex | codex/69-math-dialogue-mailbox | review | 2026-08-12 |
| — | f 초가법성 / 접합 귀납 (HI-0006·HI-0007) | claude | claude/0036-bound-improvement-infra | active | 2026-08-12 |
| #16 | GP 관계 테이블 컴파일 캐싱 | codex | codex/16-cache-compile-relations | review | 2026-07-12 |

### 교차 리뷰 — `codex/69-math-dialogue-mailbox` (claude, 2026-08-12)

`math_dialogue.py`(921줄) + 역할 프롬프트 8종 + `docs/MATH_CODEX_DIALOGUE.md`.
별도 worktree 에 있어 Claude 브랜치에서 안 보였고, 그 때문에 Claude 가 같은 자동화를
처음부터 다시 설계하려 한 일이 있었다(그래서 `scripts/session_bootstrap.py` 에
"다른 에이전트의 미병합 작업" 절을 추가했다).

- `python math_dialogue.py selftest` **통과** (토론·중복방지·동시선점·OPEN 질문 동기화).
- 신뢰 경계가 이 저장소 규약과 맞다: 모든 메시지 권한이 `UNASSESSED_DIALOGUE_ONLY` 라
  ledger·evidence·witness·pruning 으로 자동 승격되는 경로가 없고, 자동 실행이 tracked
  파일을 건드리지 않으며 산출물이 `local_runs/` 에만 쌓인다. lease·TTL·`max_rounds`·
  `max_messages` 로 무한 토론을 막는다.
- **미병합.** `CLAUDE.md`·`pyproject.toml`·`docs/DECISIONS.md`·`ci.yml` 을 바꾸므로
  병합되면 프로젝트 규칙이 바뀐다. Codex 소유 브랜치라 Claude 가 임의로 병합하지 않는다
  (`docs/AI_WORKFLOW.md` — 남의 브랜치는 HANDOFF 없이 손대지 않는다). 병합 판단은 사람 몫.

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
