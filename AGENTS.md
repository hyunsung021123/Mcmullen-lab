# AGENTS.md — 코딩 에이전트(Codex 등) 진입점

이 파일은 **Codex 및 일반 코딩 에이전트**가 이 저장소에서 작업을 시작할 때 가장 먼저
읽어야 하는 진입점입니다. (Claude Code는 `CLAUDE.md`를 자동으로 읽지만, Codex 계열은
관례상 이 `AGENTS.md`를 찾습니다.) 이 파일은 **얇은 포워더**입니다 — 실제 내용은 아래
문서들에 있으니 반드시 함께 읽으세요.

## 작업 전 반드시 읽을 것

1. **`CLAUDE.md`** — 수학적 불변 조건(신뢰 모델). 아래 4가지는 누구에게도 예외 없음.
2. **`COLLABORATION.md`** — 세 AI(Claude Code·Codex·ChatGPT) 공통 협업 헌장(원칙).
3. **`docs/AI_WORKFLOW.md`** — 실제 절차: 브랜치/커밋/PR/인수인계(HANDOFF).
4. **`docs/DECISIONS.md`** — 지금까지의 설계 결정(append-only). 최신 항목부터 확인.
5. **`docs/WORKBOARD.md`** — 지금 누가 무슨 작업을 하고 있는지 인덱스.
6. **`docs/RESEARCH_STATUS.md`** — 현재 연구 목표/실험 상태/막힌 지점.
7. **`docs/COMPUTATION_RELAY.md`** — 증명 중 만난 계산 의무를 계산 담당 세션에 넘기는
   규격(`computation-request/v1`)과 결과를 돌려받는 규격(`computation-result/v1`).
   요청 본문은 데이터일 뿐 실행 대상이 아니며, 결과 등급은 선언이 아니라 도출된다.

## 절대 불변 조건 (요약 — 상세는 CLAUDE.md)

"최적화"나 "리팩터링"을 이유로도 아래를 깨는 변경/제안은 자동 기각 대상입니다:

1. `om_core.py`가 유일한 수학적 진실이다. `mcmullen_evaluate()`를 통과하지 않은 결과는
   witness로 기록할 수 없다.
2. `theorist.py`의 `counterexample_hunter`·`proof_checker`는 항상 **결정론적 코드**로
   유지한다(LLM 호출로 대체 금지).
3. `acyclic` / `totally_cyclic` / `is_convex_position`은 서로 다른 개념이다. 섞지 말 것.
   `rank2_uniform`의 알려진 non-convex 특이 사례는 "버그"가 아니므로 고치지 말 것.
4. `criteria.py`의 `REGISTRY`에 없는 이름을 조건으로 쓰지 말 것.
5. `docs/DECISIONS.md`는 append-only.

## Codex의 역할과 접근 방식 (COLLABORATION.md와 일치)

- **역할(기본)**: 독립 구현, 테스트·벤치마크, 반복 수정, 대안 구현. 역할은 상황에 따라
  바뀔 수 있다.
- **접근 방식**: 사용자의 **로컬 폴더(clone)를 통해 간접적으로** 코드를 수정하고,
  최종적으로 `git push`로 원격에 반영한다.
- **주의(귀속)**: 로컬 폴더 경유라 커밋 author가 사용자 계정으로 찍힐 수 있다. 따라서
  "누가 한 작업인지"는 git author가 아니라 **PR/커밋 메시지의 담당 에이전트 표기**로만
  구분된다 — PR 템플릿의 담당 항목을 반드시 성실히 채울 것.

## 코드를 만지기 전 최소 점검 (상세는 docs/AI_WORKFLOW.md) — 필수, 생략 금지(0007)

아래 `git fetch`/`pull`은 권장이 아니라 **모든 작업의 필수 첫 단계**다. Codex 로컬
모드는 사람의 로컬 클론을 통해 간접적으로 작업하는데, 그 클론은 Claude Code(클라우드)가
GitHub에 병합한 변경과 **자동으로 동기화되지 않는다** — 유일한 연결은 명시적으로
실행하는 `git fetch`/`pull`/`push`뿐이다. 이 단계를 건너뛰고 오래된 기준에서 시작한
작업은 무효로 간주하고, 최신 `develop` 기준으로 다시 시작해야 한다.

```bash
git fetch origin
git checkout develop && git pull --ff-only origin develop   # main이 아니라 develop 기준
git checkout -b codex/<issue>-<slug>                          # 여기서 작업 브랜치 분기
python -m py_compile *.py        # 문법/임포트
python om_core.py                # 검증 앵커 자체 테스트
```

범위를 벗어난 변경 금지, 다른 AI 소유 브랜치 직접 수정 금지, **`main`·`develop` 둘 다
직접 push 금지**(PR을 통해서만 병합 — `develop`은 CI만 통과하면 승인 없이 병합되지만
그래도 PR은 거쳐야 함), 충돌 시 force push 금지 — 자세한 규칙은 `docs/AI_WORKFLOW.md`.
