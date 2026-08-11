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
7. **`docs/HUMAN_INSIGHT_PROTOCOL.md`** — 인간 수학 아이디어를 Claude·Codex 공통 상태로
   형식화하고 반증·구현으로 넘기는 절차.

## 세션·에이전트 공통 진입점 (여기부터)

| 무엇을 하려는가 | 어디를 보나 |
|---|---|
| 지금 상황 파악 (새 세션이면 **여기부터**) | `docs/STATE.md` — 목표·확정된 사실·**죽은 길**·진행 중 실험 |
| 실험 이력 | `research_log.md` (한 줄 = 한 라운드) |
| 수학 자문 질문·답변 | `questions/OPEN.md` · `questions/ANSWERED.md` |
| 사람 insight 상태 | `knowledge/insights/ledger.jsonl` (`python insight_ledger.py list`) |
| 정리·삭제 작업 | `docs/REFACTOR_BACKLOG.md` |
| 원문 PDF 반입 | `knowledge/papers/README.md` |

**웹 검색이 필요하면**: `WebSearch` 는 US 전용이라 이 환경에서 `unavailable` 이 뜬다.
대신 `WebFetch` 로 `https://html.duckduckgo.com/html/?q=<질의>` 를 열면 결과 목록이 그대로
나온다. 논문 본문은 arXiv 의 `ar5iv.labs.arxiv.org/html/<id>` 가 PDF 보다 훨씬 잘 읽힌다.
(QQ-0001 을 이 경로로 해결했다.)

**ChatGPT 는 `questions/OPEN.md` 를 읽고 각 항목의 `### 답변` 절을 채운다.** 답변에는
등급(PROVEN~SPECULATION)과 문헌 확인 수준(FULLTEXT/ABSTRACT_ONLY/SECONDHAND)을 반드시
붙인다 — 규약은 `questions/README.md`.

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
6. `invariants.py`의 불변량은 **판정 권한이 없다.** 라벨 `witness`(frozen)를 덮어쓰거나
   폐기하려는 변경, 어휘를 `criteria`의 `target` 모드로 승격시키는 변경은 자동 기각.
7. 불변성 등급(`conjecture._invariance_of`)이 미확인을 하위 등급으로 강등하는 동작을
   "보수적이라"는 이유로 완화하지 말 것 — 대표원소 성질이 궤도 성질로 승격되는 것이
   이 프로젝트에서 가장 위험한 거짓 결론이다.
8. 실현가능성을 결론에 반영할 것. 비실현 witness는 ν(d) 상한을 증명하지 않는다.

## 연구 규율 (정리 발굴 파이프라인 — 0028)

1. 계산으로 얻은 정리를 주장할 때는 **어떤 검사기가 그것을 뒷받침하는지** 반드시 밝힌다.
2. 다음을 절대 섞지 않는다: 증명된 사실 / 계산으로 확인된 유한 사례
   (`EXHAUSTED_ON_SCOPE`) / 수치적 증거 / 휴리스틱 / 추측 / LLM 발언.
3. 보조정리를 제안하면 **다듬기 전에 먼저 반증을 시도**한다 (`falsify.py`).
4. 후보를 제안하면 가능한 한 기계가독 형태로 바꾼다 (`reasoner.encode_chirotope`).
5. 실패한 아이디어도 기록한다 (`research_log.md`, 어휘는 삭제가 아니라 폐기).
6. 시험 중인 수학적 정의를 조용히 바꾸지 않는다.
7. 후보가 계속 실패한다는 이유로 검증기를 고치지 않는다.
8. 반증 가능하고 계산으로 시험 가능한 중간 추측을 우선한다.
9. 추상 OM을 쓸 때는 실현가능성을 항상 명시적으로 추적한다.
10. 실험을 나중에 재현할 수 있을 만큼의 provenance를 남긴다 (`experiments/run_*/manifest.json`).

## 인간 수학 insight 처리 (0031)

- 사용자가 아이디어의 `기록`·`검증`·`반영`·`탐색 적용`을 요청하면
  `insight_ledger.py`와 `docs/HUMAN_INSIGHT_PROTOCOL.md`를 사용한다.
- 대화 내용만으로 탐색 제약이나 pruning을 활성화하지 않는다. 먼저 `PROPOSED`로 기록하고
  형식화·반증·evidence 단계를 거친다.
- `SUPPORTED`/`REFUTED`에는 재현 가능한 evidence 참조가, `INTEGRATED`에는 evidence와
  구현 참조가 모두 필요하다. 에이전트의 동의나 이름은 evidence가 아니다.
- Issue·PR·HANDOFF에는 관련 `HI-NNNN`을 적어 Claude와 Codex가 같은 맥락을 재구성하게 한다.

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
