---
name: AI 작업 (AI Task)
about: Claude Code / Codex / 사람에게 배정하는 작업 단위. 이슈 번호가 브랜치·PR을 잇는다.
title: "[Task] "
labels: ai-task
---

## 목표
<!-- 무엇을 해결하는가 (한두 문장) -->

## 배경
<!-- 왜 필요한가. 관련 이슈/PR/결정 로그 항목이 있으면 링크 -->

## 범위 (수정 가능한 파일)
<!-- 이 작업에서 만질 파일/모듈 -->

## 제외 범위 (건드리지 말 것)
<!-- 특히 핵심 코드(om_core.py 등) 및 CLAUDE.md 불변 조건 관련 -->

## 담당 에이전트
- [ ] claude-code (직접 커밋)
- [ ] codex (로컬 폴더 경유)
- [ ] human
<!-- ChatGPT는 읽기 전용이라 작업 담당이 될 수 없음(리뷰만). 리뷰 요청은 cross_review 템플릿 사용 -->

## 기준 브랜치 / 커밋
<!-- 예: develop @ <SHA>.  이 커밋에서 <agent>/<issue>-<slug> 브랜치를 분기 (main이 아님) -->

## 수용 조건 (Definition of Done)
<!-- 무엇이 충족되면 완료로 인정하는가 -->

## 필수 테스트 (결정론적)
- [ ] `python -m py_compile *.py`
- [ ] `python om_core.py`
- [ ] (변경 모듈의 자체 테스트, 예: `python criteria.py`)

## 신뢰 모델 영향
<!-- om_core 판별 / criteria REGISTRY / OM class 레지스트리 / public API 중 무엇을 건드리나.
     해당 없으면 "해당 없음". 건드린다면 CLAUDE.md의 어느 불변 조건과 관련되는지. -->

## 상태
`planned` | `active` | `blocked` | `review` | `done`

## HANDOFF 기록 (인수인계가 발생하면)
<!-- docs/AI_WORKFLOW.md §7의 HANDOFF 형식을 여기 또는 PR 코멘트에 남길 것 -->
