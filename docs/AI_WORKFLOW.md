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

## 2. 브랜치 모델 — 2단계 (통합 브랜치 + 안전 저장소)

루프(개발→리팩터링→리뷰→개발...)가 **매번 사람 승인 없이** 돌 수 있도록, 병합 대상을
두 단계로 나눈다. "사람 승인이 매번 필요한가"는 AI가 몇 명이냐의 문제가 아니라 병합
대상이 몇 단계냐의 문제였고, 이 2단계 모델이 그 해결책이다(`docs/DECISIONS.md` 0004).

```
main                              ← 안전 저장소. 사람이 간헐적으로 승인해 승격.
  ↑ (develop → main PR, 사람 승인 필수 — 드물게, 의도적으로)
develop                           ← 통합 브랜치. claude↔codex↔chatgpt 루프가 도는 곳.
  ↑ (PR + CI 통과, 사람 승인 불필요 — 루프가 돌 때마다 자동)
├── claude/<issue>-<slug>         ← Claude Code 소유
├── codex/<issue>-<slug>          ← Codex 소유
└── human/<issue>-<slug>          ← 사람 소유
```

예: `claude/12-optimize-reorientation`, `codex/12-profile-reorientation`

규칙:
- **하나의 브랜치는 한 에이전트만 소유**한다. Claude와 Codex가 같은 브랜치를 동시에
  수정하지 않는다.
- 에이전트 브랜치는 **`develop`에서 분기**하고, **`develop`로 PR**을 연다(`main`이 아님).
- `main`·`develop` 모두 **직접 push 금지.** 모든 변경은 PR을 통해 병합한다.
- **`develop` 병합에는 사람 승인이 필요 없다** — PR + CI(결정론적 테스트) 통과만 있으면
  된다. 병합 자체는 Claude Code가 "자동 병합 코디네이터" 역할로 수행한다(§6-1).
- **`main` 병합(승격)에는 항상 사람 승인이 필요하다.** 루프를 몇 번을 돌든 `main`은
  사람이 "이제 됐다"고 판단할 때만, 그리고 그때만 움직인다.
- 병렬 대안(같은 이슈에 대한 서로 다른 접근)을 비교할 때는 **서로 다른 브랜치**를 쓴다
  (위 예시처럼 같은 이슈 번호, 다른 slug/소유자).
- 다른 AI 소유 브랜치를 수정해야 한다면, 그 브랜치에서 **새 브랜치를 분기**하거나
  Issue/PR에 **명시적 인수인계(HANDOFF)** 를 기록한 뒤에만 한다. 남의 브랜치를 임의로
  덮어쓰지 않는다.

> **현재 상태(0006 갱신)**: `criteria.py`/`om_core.py`/`theorist.py` 같은 신뢰 모델
> 핵심 파일도 `develop`에서 CI만 통과하면 자동 병합된다 — CODEOWNERS 같은 파일 단위
> 사람 승인 게이트는 걸지 않는다. 대신 `docs/DECISIONS.md` 0006(ChatGPT 첫 리뷰,
> 0004 `contested`)을 반영해 **CI 자체를 semantic하게 강화**했다: `om_core.py`/
> `criteria.py`/`theorist.py`의 자체 테스트가 이제 실측 기대값을 실제로 `assert`한다
> (이전엔 `print`만 하고 값 자체는 검증하지 않아, 판별 로직이 반대로 뒤집혀도 CI가
> 통과할 수 있었다). CI-only 병합이 안전한 건 "CI가 결정론적이라서"가 아니라
> "CI가 이제 수학적 의미를 실제로 검증해서"다 — 이 둘은 다른 명제였다.

> branch protection(“main/develop 직접 push 금지”, “머지 전 CI 필수”, “develop은 승인
> 불필요·main은 승인 필수”)의 **기술적 강제**는 GitHub 저장소 설정이며 **사람(관리자)만**
> 켤 수 있다. 이 문서의 규칙은 그 설정이 켜지기 전까지는 규약(약속)으로만 강제된다.

## 3. 작업 단위 = GitHub Issue

작업은 반드시 Issue 하나로 시작한다(`.github/ISSUE_TEMPLATE/ai_task.md`). 이슈 번호가
브랜치·PR을 잇는 식별자다. 이슈에는 목표·범위·담당·기준 브랜치/커밋·수용 조건·필수
테스트·신뢰 모델 영향·상태를 적는다.

## 4. 작업 시작 절차 — 아래 `fetch`/`pull`은 필수, 생략 금지(0007)

```bash
git fetch origin
git switch develop && git pull --ff-only origin develop   # 기준 최신화 (main이 아님)
git switch -c <agent>/<issue>-<slug> develop                # develop에서 분기
git status --short --branch                                  # 깨끗한 작업 트리 확인
```

이 두 줄(`fetch`/`pull`)은 권장이 아니라 **모든 작업의 필수 첫 단계**다(0007). 특히
Codex 로컬 모드처럼 사람의 로컬 클론을 통해 간접적으로 작업하는 경우, 그 클론은
Claude Code(클라우드)가 GitHub에 병합한 변경과 **자동으로 동기화되지 않는다** — 로컬
클론과 GitHub 사이의 유일한 연결은 사람 또는 에이전트가 명시적으로 실행하는
`git fetch`/`pull`/`push`뿐이다. 이 단계를 건너뛰고 오래된 기준에서 시작한 작업은
**무효로 간주하고, 최신 `develop` 기준으로 다시 시작한다.**

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
4. PR 생성 — **대상 브랜치는 `develop`** (`.github/PULL_REQUEST_TEMPLATE.md` 형식).
5. PR을 Issue와 연결(`Closes #<issue>` 등).
6. 필요 시 HANDOFF 또는 교차 리뷰 요청 작성.
7. CI가 통과하면 §6-1에 따라 **사람 개입 없이** `develop`에 병합된다.

(`docs/WORKBOARD.md`는 매 작업마다 갱신하지 않는다 — §11 참고. 활성 작업 현황이
궁금하면 GitHub Issues의 `ai-task` 라벨을 검색하는 게 항상 최신이다.)

## 6-1. `develop` 자동 병합 코디네이터 (Claude Code)

`develop`을 향한 PR은 사람이 승인하지 않는다 — 대신 **Claude Code가 병합 코디네이터
역할**을 맡는다. Claude Code(또는 향후 동등한 접근권을 가진 에이전트)는 다음을 확인한
뒤 병합한다:

1. CI(`ci.yml`)가 녹색인가.
2. PR 템플릿이 채워져 있는가(특히 "영향 범위"·"신뢰 모델 점검").
3. 다른 진행 중인 PR과 파일 충돌이 없는가(있으면 §8에 따라 병합하지 않고 보고).

위 세 가지가 확인되면 **사람에게 묻지 않고 병합한다.** Codex가 연 PR도 동일 기준으로
Claude Code가 병합할 수 있다(Codex 자체에 병합 권한이 있다면 스스로 해도 무방 — 둘 다
같은 기준을 따른다). 이 자동 병합은 신뢰 모델 핵심 파일도 예외 없이 포함한다 — 단,
위 §2의 "현재 상태"대로 이제 CI가 그 파일들의 실측 기대값을 실제로 검증하기 때문에
안전하다(0006). CODEOWNERS 도입 여부는 재검토 대상으로 남아 있다.

## 6-2. GitHub 자체 auto-merge 사용 (0008)

§6-1의 "병합 코디네이터" 역할은 지금까지 CI 완료를 사람이 알려주거나 에이전트가
수동으로 폴링해서 확인한 뒤 병합하는 방식으로 수행되어 왔다. 이제부터는 **PR을 열자마자
GitHub의 네이티브 auto-merge를 그 PR에 걸어둔다** — `develop` 브랜치 보호 규칙이 이미
"PR 필수 + CI 필수 + 승인 0"으로 설정되어 있으므로(§2), GitHub가 CI green을 확인하는
즉시 스스로 병합을 완료한다.

- PR을 여는 에이전트는 PR 생성 직후 auto-merge를 활성화한다(squash 방식, 이 저장소의
  기본 병합 방식과 동일하게 맞춘다).
- 이렇게 하면 §6-1의 3개 확인 기준 중 "CI green"은 GitHub 자신이 강제하고, "PR 템플릿
  작성"·"다른 PR과 충돌 없음"은 여전히 PR을 여는 에이전트가 병합 전에 스스로 점검한다
  (auto-merge는 그 두 가지를 대신 판단해주지 않는다 — 형식적으로 CI만 통과하면
  병합되므로, 템플릿 미기입이나 충돌 위험이 있는 PR에는 auto-merge를 걸지 않는다).

### Codex(또는 다른 에이전트)가 여는 PR (0009)

PR #17(Codex 작성)이 CI green이었는데도 auto-merge가 걸려 있지 않아 사람이 직접
"왜 자동 병합 안 하냐"고 물어야 했던 사례가 있었다 — auto-merge는 **PR마다 개별
활성화**해야 하는 기능이라, 지금까지는 Claude Code가 여는 PR에만 실제로 적용되고
있었다. 이제부터:

- **Claude Code는 Codex(또는 다른 에이전트)가 연 `develop` PR을 인지하는 즉시**
  (CI 완료를 기다리지 않고) auto-merge를 건다 — diff를 먼저 전부 읽고 판단한 뒤에
  거는 게 아니라, §6-1의 "PR 템플릿 작성"·"충돌 없음" 두 가지만 빠르게 확인되면
  바로 건다. "CI가 이제 semantic해서 CI-only 병합이 안전하다"는 0004/0006의 원칙을
  Claude Code가 여는 PR과 동일하게 Codex PR에도 적용하는 것.
- 다만 이건 **의무적인 심층 코드 리뷰를 없앤다는 뜻은 아니다** — PR이 신뢰 모델
  핵심 파일이 아닌 곳(예: `generator.py`)을 건드리더라도 다른 모듈이 그 반환값에
  의존하는 방식이라 안전성이 자명하지 않다면(예: 캐싱 도입 시 반환값이 호출부에서
  mutate되는지), Claude Code는 auto-merge를 걸기 **전에** 그 부분만 빠르게 diff로
  확인한다. 이건 CI가 커버하지 못하는 "코드가 주장한 대로 안전한지"에 대한 확인이며,
  PR #17에서 실제로 이 확인을 거쳐 안전함을 검증한 뒤 병합했다.
- Codex 자신이 `gh` CLI 등으로 GitHub에 직접 접근할 수 있다면, PR을 연 직후
  `gh pr merge --auto --squash <PR번호>`를 스스로 실행하는 것도 권장한다(백업 경로 —
  Claude Code가 그 PR의 존재를 늦게 알아차리는 경우를 대비).
- `main`으로 향하는 승격 PR(§9)에는 이 자동화를 쓰지 않는다 — `main`은 사람 승인이
  branch protection으로 강제되어 있어 auto-merge를 걸어도 사람이 승인하기 전까지는
  움직이지 않지만, 혼동을 피하기 위해 애초에 승격 PR에는 auto-merge를 걸지 않는다.

## 7. 인수인계(HANDOFF) 형식

작업을 다른 참여자에게 넘길 때 Issue 또는 PR에 아래를 남긴다. 이러면 채팅 없이 저장소만
보고 이어갈 수 있다.

```markdown
## HANDOFF
- 전달 주체: claude | codex | human            (실제로 이 HANDOFF를 기록/전달한 주체)
- 원 제안/검토 출처: claude | codex | chatgpt | human   (의견 자체가 누구에게서 나왔나)
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

`전달 주체`와 `원 제안/검토 출처`를 분리한 이유(0006): 사람이 ChatGPT의 검토 의견을
대신 옮기는 경우 "전달 주체=human, 원 출처=chatgpt"로 남겨야, 나중에 "사람이 직접
판단한 내용"과 "ChatGPT 의견을 사람이 중계한 내용"이 뒤섞이지 않는다.

ChatGPT는 읽기 전용이므로, ChatGPT에게 리뷰를 넘길 때는 사람이 PR/이슈 링크와 CI 결과를
전달하고, ChatGPT의 회신을 사람이 다시 이슈/PR 코멘트로 옮긴다(출처 명시).

## 8. 충돌 / 오래된 기준 브랜치 발견 시

- **force push 금지. 다른 AI의 변경을 임의로 삭제/덮어쓰기 금지.**
- 자동 병합(auto-merge)이나 `main` 자동 병합을 시도하지 않는다.
- 충돌 내용과 가능한 대안을 Issue/PR에 기록하고 **작업을 멈춘 뒤 사람에게 선택을
  요청**한다.
- 기준 브랜치가 오래됐으면(예: 분기 후 main이 크게 앞서감) 임의 rebase/merge로 밀어붙이지
  말고, 상황을 보고하고 사람의 지시를 받는다.

## 9. `develop → main` 승격 (사람이 간헐적으로 승인)

`main`은 "안전 저장소"다 — 루프가 몇 번을 돌든 사람이 승인하기 전까지는 움직이지 않는다.

승격 PR은 **비어있는 채로 열어두지 않는다**(0006 — 실제로 그런 사례(#4)가 있었다:
`develop→main` PR이 담당·기준 커밋·변경 이유·blast radius·테스트 결과가 전부
placeholder로 빈 채 방치됨). 승격을 시작하는 시점에 아래 체크리스트를 그 PR 본문에
채운다:

```markdown
## 승격 체크리스트 (develop → main)
- 기준 main SHA: <SHA>
- 승격할 develop SHA: <SHA>
- 포함되는 Issue/PR 목록: #.. #.. #..
- 신뢰 모델 핵심 파일(om_core.py/criteria.py/theorist.py) 변경 여부와 목록:
- 아직 pending/contested인 교차 리뷰가 있는가:
- 이 head SHA에서 실행된 CI 결과(링크):
- 알려진 위험 / 롤백 시 되돌릴 단위:
- 승격 후 다시 실행해 확인할 연구 검증(있다면):
```

절차:
1. 사람이 "이 정도면 됐다"고 판단하는 시점에(정해진 주기 없음, 전적으로 사람의 재량),
   `develop`에서 `main`으로 PR을 열고 위 체크리스트를 채운다. **채우지 않은 채로 방치된
   승격 PR은 열어두지 않는다** — 지금 승격할 준비가 안 됐으면 닫고, 준비됐을 때 다시 연다.
2. 리뷰 시 개별 커밋보다는 `docs/DECISIONS.md`에 쌓인 결정 항목들과 CI 결과를 함께 본다.
3. 사람이 diff를 검토하고 승인해야만 병합된다(branch protection이 `main`에 이를
   강제한다 — §2 참고).
4. 병합 후 `docs/WORKBOARD.md`를 최신 상태로 동기화한다(§11 참고 — WORKBOARD는
   비권위 스냅샷이라 이 시점에만 동기화하면 된다).

## 10. 운영 예시 (병렬 대안 비교 + 2단계 승격)

```
사람이 Issue #12 생성
  → Codex에 프로파일링 배정: codex/12-profile-reorientation
  → Claude에 독립 최적화 배정: claude/12-optimize-reorientation
  → 각자 develop 대상 PR
  → CI 통과 → Claude Code(코디네이터)가 사람 개입 없이 develop에 병합
  → ChatGPT가 develop의 결과 + CI를 비교 리뷰(사람이 중계)
  → 사람이 대안 선택(이미 develop엔 둘 다 반영돼 있을 수 있음 — 필요하면 후속 커밋으로 정리)
  → docs/DECISIONS.md에 선택 이유 기록
  → (루프 여러 번 반복) ...
  → 사람이 "이제 됐다" 판단 → develop → main PR → 사람이 승인 → main 승격
```

## 11. `docs/WORKBOARD.md` 정책 (0006 갱신)

**`docs/WORKBOARD.md`는 권위 있는 상태가 아니라 비권위(non-authoritative) 스냅샷이다.**
활성 작업의 살아있는 진실은 언제나 **GitHub Issues의 `ai-task` 라벨 검색**이다 — 매
PR마다 WORKBOARD를 갱신하는 의무를 없앤 이유는, 실제로 그 의무가 지켜지지 않아
(Issue #5/PR #6이 완료된 뒤에도 WORKBOARD엔 반영되지 않은 채 방치된 사례가 있었다)
GitHub Issues와 WORKBOARD 두 상태가 서로 어긋나는 위험이 이미 현실화됐기 때문이다.

- WORKBOARD는 **§9의 `develop → main` 승격 시점에만** 동기화한다.
- 문서 첫머리에 "source of truth는 GitHub Issues"임을 명시해 둔다.
- 급하게 지금 활성 작업을 보고 싶으면 Issues를 `ai-task` 라벨로 검색한다.

## 12. 로컬 자동 동기화 (선택, 사람 전용) (0007)

Claude Code(클라우드)는 사람의 로컬 PC에 **접근할 방법이 전혀 없다** — 유일한 공유
채널은 GitHub이며, 로컬 클론은 사람 또는 로컬 에이전트(Codex 로컬 모드 등)가 직접
`git pull`을 실행해야만 최신화된다. §4의 "작업 전 fetch/pull 필수"가 근본 대책이지만,
그 단계가 실제로는 누락되기 쉬우므로(사람이 깜빡하거나, Codex 세션이 그 단계를
생략하고 바로 작업을 시작하는 경우) 보조 수단으로 `scripts/local-autopull.ps1`을
제공한다.

- 이 스크립트는 **`develop`을 fast-forward-only로만 pull**한다 — merge/rebase/force
  없음.
- 현재 체크아웃된 브랜치가 `develop`이 아니거나, 커밋되지 않은 변경이 있거나,
  fast-forward가 불가능하면 **아무 것도 하지 않고 로그만 남긴다**(사람이 직접
  판단해야 하는 상황을 스크립트가 임의로 처리하지 않기 위함).
- Windows 작업 스케줄러(Task Scheduler)에 주기적 실행으로 등록해 사용한다:
  1. 작업 스케줄러 → "기본 작업 만들기"
  2. 트리거: 예) 15분마다 반복
  3. 동작: 프로그램 시작
     - 프로그램/스크립트: `powershell.exe`
     - 인수 추가: `-ExecutionPolicy Bypass -File "C:\경로\Mcmullen-lab\scripts\local-autopull.ps1" -RepoPath "C:\경로\Mcmullen-lab"`
  4. 실행 로그는 `RepoPath\autopull.log`에 쌓인다.
- 이 스크립트는 **사람의 로컬 환경에만 관여**하며 저장소의 신뢰 모델·CI·병합 절차에는
  영향을 주지 않는다. develop이 아닌 작업 브랜치에서 작업 중일 때는 스크립트가
  브랜치를 바꾸지 않으므로 안전하게 계속 실행해 둘 수 있다.

## 13. 대시보드 원클릭 실행 (선택, 사람 전용) (Issue #23)

`streamlit run dashboard.py`를 매번 터미널에서 직접 입력하지 않아도 되도록,
`scripts/run_dashboard.bat`를 제공한다.

- 이 스크립트가 하는 일은 저장소 루트로 이동해 `python -m streamlit run dashboard.py`를
  실행하는 것뿐이다 — Streamlit은 기본적으로(headless가 아니면) 실행 시 기본 브라우저를
  자동으로 띄운다. bare `streamlit` 대신 `python -m streamlit`을 쓰는 이유(0007과 같은
  종류의 실측 문제): pip이 설치한 `streamlit.exe`가 있는 Scripts 폴더가 PATH에 없는
  환경에서도, `python` 자체만 PATH에 있으면 동작한다.
- **바탕화면에 바로가기 만드는 법(Windows)**: `scripts\run_dashboard.bat` 파일을 우클릭
  → "바로 가기 만들기" → 만들어진 바로가기를 바탕화면으로 옮기기. 이후 그 바로가기를
  더블클릭하면 대시보드가 브라우저에 뜬다.
- 사전 준비: 저장소 폴더에서 `pip install -e .[ui]`(또는
  `python -m pip install streamlit pandas`)를 한 번 실행해 Streamlit이 설치돼 있어야
  한다.
- 이 `.bat` 파일은 UTF-8(BOM 없음)로 저장돼 있고 첫 줄에 `chcp 65001`로 콘솔
  코드페이지를 UTF-8로 전환한다 — `.bat` 파일에 BOM을 넣으면 cmd.exe가 첫 줄을 명령으로
  잘못 파싱해 오류가 나므로, `local-autopull.ps1`(PowerShell, BOM 방식)과는 다른
  방식으로 한글 깨짐을 해결했다(Issue #27, 실측 확인).
- 이 스크립트는 사람의 로컬 실행 편의만 다루며, 저장소의 신뢰 모델·CI·병합 절차와는
  무관하다.
