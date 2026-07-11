# docs/AI_WORKFLOW.md — 실제 작업 절차 (브랜치 · 커밋 · PR · 인수인계)

`COLLABORATION.md`가 "원칙(왜)"이라면, 이 문서는 "절차(어떻게)"입니다. 세 AI와 사람이
같은 저장소에서 안전하게 비동기 협업하기 위한 구체적 순서를 정의합니다.

> 이 문서는 절차만 담습니다. 역할·신뢰 모델·반박 형식 같은 원칙은 `COLLABORATION.md`와
> `CLAUDE.md`를 보세요. 중복 서술을 피하기 위함입니다.

## 1. 공유 상태로 인정되는 것 (그 외는 없는 것과 같다)

```
커밋된 파일 · 원격 브랜치 · Pull Request · GitHub Issue · CI 결과 · docs/DECISIONS.md
```

로컬 미커밋 파일, 채팅에서만 오간 합의, 특정 AI의 세션 안에만 있는 맥락은 **공유 상태가
아니다.** 다른 참여자가 저장소만 보고 재구성할 수 없는 것은 존재하지 않는 것으로 간주한다.

## 2. 브랜치 모델

```
main                              ← 트렁크. 직접 push 금지. PR로만 병합.
├── claude/<issue>-<slug>         ← Claude Code 소유
├── codex/<issue>-<slug>          ← Codex 소유
└── human/<issue>-<slug>          ← 사람 소유
```

예: `claude/12-optimize-reorientation`, `codex/12-profile-reorientation`

규칙:
- **하나의 브랜치는 한 에이전트만 소유**한다. Claude와 Codex가 같은 브랜치를 동시에
  수정하지 않는다.
- `main` **직접 push 금지.** 모든 변경은 PR을 통해 병합한다.
- 병렬 대안(같은 이슈에 대한 서로 다른 접근)을 비교할 때는 **서로 다른 브랜치**를 쓴다
  (위 예시처럼 같은 이슈 번호, 다른 slug/소유자).
- 다른 AI 소유 브랜치를 수정해야 한다면, 그 브랜치에서 **새 브랜치를 분기**하거나
  Issue/PR에 **명시적 인수인계(HANDOFF)** 를 기록한 뒤에만 한다. 남의 브랜치를 임의로
  덮어쓰지 않는다.

> branch protection(“main 직접 push 금지”, “머지 전 CI 필수”)의 **기술적 강제**는 GitHub
> 저장소 설정이며 **사람(관리자)만** 켤 수 있다. 이 문서의 규칙은 그 설정이 켜지기 전까지는
> 규약(약속)으로만 강제된다.

## 3. 작업 단위 = GitHub Issue

작업은 반드시 Issue 하나로 시작한다(`.github/ISSUE_TEMPLATE/ai_task.md`). 이슈 번호가
브랜치·PR을 잇는 식별자다. 이슈에는 목표·범위·담당·기준 브랜치/커밋·수용 조건·필수
테스트·신뢰 모델 영향·상태를 적는다.

## 4. 작업 시작 절차

```bash
git fetch origin
git switch main && git pull --ff-only origin main   # 기준 최신화
git switch -c <agent>/<issue>-<slug> main            # 기준 브랜치에서 분기
git status --short --branch                           # 깨끗한 작업 트리 확인
```

- Issue를 생성/확인하고, 담당 AI와 브랜치 이름, **기준 커밋 SHA**를 이슈에 기록한다.
- 기존 미커밋 변경을 임의로 포함하지 않는다(내 작업이 아니면 건드리지 않는다).

## 5. 작업 중

- 주요 진행 상황은 **Issue 코멘트**에 남긴다(상세 로그를 공유 Markdown 파일 하나에 계속
  append하지 않는다 — 동시 수정 충돌의 원인).
- 이슈에 적은 **범위를 벗어난 변경 금지.** 범위를 넓혀야 하면 이슈를 갱신하거나 새
  이슈를 연다.
- 다른 AI 소유 브랜치를 직접 수정하지 않는다.

## 6. 작업 완료 절차

```bash
python -m py_compile *.py        # 항상
python om_core.py                # 검증 앵커
# 변경한 모듈의 자체 테스트 (예: python criteria.py)
```

1. 결정론적 테스트 실행(위) — 통과 확인.
2. 커밋(메시지에 담당 에이전트·이유·blast radius 포함).
3. 원격 브랜치 push (`git push -u origin <agent>/<issue>-<slug>`).
4. PR 생성(`.github/PULL_REQUEST_TEMPLATE.md` 형식).
5. PR을 Issue와 연결(`Closes #<issue>` 등).
6. 필요 시 HANDOFF 또는 교차 리뷰 요청 작성.
7. `docs/WORKBOARD.md`의 해당 행 상태를 갱신(인덱스만).

## 7. 인수인계(HANDOFF) 형식

작업을 다른 참여자에게 넘길 때 Issue 또는 PR에 아래를 남긴다. 이러면 채팅 없이 저장소만
보고 이어갈 수 있다.

```markdown
## HANDOFF
- 보낸 주체: claude | codex | human
- 받을 주체: claude | codex | chatgpt(리뷰) | human
- 기준 커밋: <SHA>
- 현재 상태:
- 완료한 내용:
- 남은 내용:
- 확인된 위험:
- 실행한 테스트 / 결과:
- 실패한 테스트:
- 수정하면 안 되는 부분:
- 요청하는 검토/작업:
```

ChatGPT는 읽기 전용이므로, ChatGPT에게 리뷰를 넘길 때는 사람이 PR/이슈 링크와 CI 결과를
전달하고, ChatGPT의 회신을 사람이 다시 이슈/PR 코멘트로 옮긴다(출처 명시).

## 8. 충돌 / 오래된 기준 브랜치 발견 시

- **force push 금지. 다른 AI의 변경을 임의로 삭제/덮어쓰기 금지.**
- 자동 병합(auto-merge)이나 `main` 자동 병합을 시도하지 않는다.
- 충돌 내용과 가능한 대안을 Issue/PR에 기록하고 **작업을 멈춘 뒤 사람에게 선택을
  요청**한다.
- 기준 브랜치가 오래됐으면(예: 분기 후 main이 크게 앞서감) 임의 rebase/merge로 밀어붙이지
  말고, 상황을 보고하고 사람의 지시를 받는다.

## 9. 운영 예시 (병렬 대안 비교)

```
사람이 Issue #12 생성
  → Codex에 프로파일링 배정: codex/12-profile-reorientation
  → Claude에 독립 최적화 배정: claude/12-optimize-reorientation
  → 각자 별도 PR
  → ChatGPT가 두 PR + CI를 비교 리뷰(사람이 중계)
  → 사람이 대안 선택 → 선택한 PR 병합
  → docs/DECISIONS.md에 선택 이유 기록
```
