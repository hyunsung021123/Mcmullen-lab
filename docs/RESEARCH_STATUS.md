# docs/RESEARCH_STATUS.md — 현재 연구 상태

이 프로젝트의 **수학적 목표·현재 진행·막힌 지점**을 저장소 안에서 추적하기 위한
문서입니다. 협업 인프라(브랜치/절차)와 분리해, "지금 무엇을 풀고 있는가"를 세 AI와
사람이 공유하기 위함입니다. 실험 결과가 바뀌면 갱신합니다.

> 배경 이론과 트랙터빌리티 상세는 `README.md`(특히 §1, §10)를 참고. 이 문서는 그 위에서
> "현재 어디까지 왔고 다음에 뭘 할지"만 요약합니다.

## 1. 큰 목표

McMullen 문제(Larman 추측 f(5)=11)를 유향 매트로이드(OM)로 재구성해, **어떤 재배향으로도
convex position이 되지 않는 uniform OM**을 최소 원소 수 n으로 찾는다. n에서 찾으면
OM-McMullen 상한이 n−1로 내려간다. d=5의 구체 목표: rank-6, n=12 witness → ν(5) ≤ 11.

## 1-1. 검증·구성 인프라 (Epic #37 — 2026-07-14 상태)

coverage/SAT/CEGIS/대칭 축소/certificate 파이프라인이 병합됨 (도구 상세는
`docs/AUTONOMOUS_VERIFICATION_PIPELINE.md`). 연구 관점의 핵심 실측:

- **(6,3)의 labeled witness 9,984개는 정확히 3개의 isomorphism class** 로 떨어진다
  (orbit-aware CEGIS 열거, recall 손실 0 — 문헌 대조는 미완, ChatGPT 교차 리뷰 요청 중).
- (5,3)/(6,4)에는 witness 가 없음이 CEGIS EXHAUSTED(unknown 0건)로 확인됨.
- witness certificate 는 저장소 비의존 replay.py 로 제3자가 재검증 가능 (CERTIFIED 등급).

## 2. 현재 상태 (검증된 것만)

| d | rank | 목표 상한 2d+1 | 현재 상태 |
|---|---|---|---|
| 2 | 3 | 5 | 이미 tight(U=2d+1). 데모에서 witness 다수 확인. reward 0(개선 여지 없음). |
| 3 | 4 | 7 | `realizable_uniform`(무작위 점배치) 데모에서 n=8 witness 발견 사례 있음(상한 7 도달). |
| 5 | 6 | 11 | **미해결(본 목표).** 개별 후보 검증은 빠르나, 전수 생성이 비현실적. |

> 위 d=2/d=3 결과는 각 모듈의 데모 실행(`search.py`/`manager.py`)에서 관찰된 것으로,
> `om_core.mcmullen_evaluate()`를 통과한 witness다. 아직 저장소에 커밋된 대규모 결과
> 아티팩트(results*.json)는 없다(그리고 그것들은 `.gitignore` 대상이다).

## 3. 막힌 지점 / 트랙터빌리티

- **전수 백트래킹은 d≥4, n~12에서 비현실적**(이중지수). `generator.py`의 backtracking은
  작은 n 데모용.
- 개별 후보 검증(재배향 2^(n-1) × convex 판정)은 d=5, n=12에서도 빠름 → **구조적 후보를
  직접 공급하면** 코어가 즉시 판정 가능.

## 4. 다음 후보 방향 (검증 가능한 것 우선)

1. **rank-2 extended Lawrence class 사용**: `extended_lawrence_r2`가 signed-permutation
   rank-2 layer들의 Lawrence–Weinberg union을 rank-6 realizable chirotope로 직접 공급한다
   (d=5에서는 layer 3개). 최종 판정은 기존 exact evaluator가 담당한다.
2. **타깃 SAT/Z3**(`backend: z3`)로 GP + 편향을 인코딩해 대규모/구조적 탐색.
3. **minimum interval map 성질 측정**: `interval_maps.py`의 단일-layer beta_0/beta_1은
   exact 분석량이다. layer composition과 final rank-6 obstruction 사이의 관계는 아직
   heuristic이므로 opt-in ranking과 benchmark에만 사용한다(HI-0002/HI-0003).
4. 위원회(theorist)는 "어떤 부분구조를 고정/금지할지" 같은 **검증 가능한 편향**만 제안하고,
   결정론적 게이트(proof_checker/counterexample_hunter)를 통과한 것만 반영.

## 5. 열린 질문 (교차 리뷰 환영)

- layer-map composition score가 exact McMullen coverage 품질과 실제로 양의 상관을 갖는가?
  동일 seed·예산의 heuristic on/off benchmark가 필요하다.
- signed-permutation tuple의 relabel/layer-order 대칭을 recall 손실 없이 얼마나 더 줄일 수 있는가?
- d=3에서 비실현(non-realizable) witness가 실현가능 witness보다 더 작은 n을 줄 수 있는가?
  (현재 `random` 백엔드는 실현가능만 생성 → 비실현 탐색은 `uniform`/`z3` 필요)
