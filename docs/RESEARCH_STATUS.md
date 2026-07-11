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

1. **구조적 시드에서 출발**: 순환다면체 / Lawrence / 사용자의 rank-2 REOM 인코딩.
2. **타깃 SAT/Z3**(`backend: z3`)로 GP + 편향을 인코딩해 대규모/구조적 탐색.
3. **REOM 소켓 연결**: `om_classes.py`의 `lawrence` 소켓(또는 신규 `reom` 클래스)에
   `(n, r, *, accept, **kw) -> Iterator[Chirotope]` 시그니처의 생성기를 연결. 인코딩(또는
   Z3 제약)이 확정되면 통합 — 코어 검증은 그대로 재사용.
4. 위원회(theorist)는 "어떤 부분구조를 고정/금지할지" 같은 **검증 가능한 편향**만 제안하고,
   결정론적 게이트(proof_checker/counterexample_hunter)를 통과한 것만 반영.

## 5. 열린 질문 (교차 리뷰 환영)

- rank-2 REOM 인코딩을 어떤 형식으로 코어에 넘길 것인가(signed-permutation-tuple /
  ABA-패턴 → chirotope)?
- d=3에서 비실현(non-realizable) witness가 실현가능 witness보다 더 작은 n을 줄 수 있는가?
  (현재 `random` 백엔드는 실현가능만 생성 → 비실현 탐색은 `uniform`/`z3` 필요)
