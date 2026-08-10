# docs/STATE.md — 세션 재시작용 단일 진입점

> **새 세션이면 이 파일만 읽으면 된다.** 5분 안에 맥락이 복원되도록 만든 문서다.
> 아래 §6 은 `python scripts/session_bootstrap.py` 로 자동 재생성된다 — 손으로 고치지 말 것.
> §1~§5 는 사람/에이전트가 갱신한다. 상세는 각 절이 가리키는 파일로.

읽는 순서: **이 파일 → `research_log.md`(실험 한 줄 = 한 라운드) → 필요한 모듈의 docstring.**
`CLAUDE.md` 는 규칙, 이 문서는 상태다. 둘을 섞지 않는다.

---

## 1. 지금 무엇을 풀고 있나

McMullen 문제. ν(d) = "임의의 n 점을 사영변환으로 볼록위치에 놓을 수 있는" 최대 n.
**witness**(어떤 재배향으로도 convex 가 되지 않는 구성)를 n 점에서 찾으면 ν(d) ≤ n−1.

**현재 주력은 Larman 목표(n=2d+2)가 아니라 상한 개선이다.** 알려진 상한
U(d) = 2d+⌊(1+d)/2⌋ 기준으로 **n ≤ U(d) 인 witness 는 무엇이든 개선**이다.

| d | 하한 2d+1 | 기존 U(d) | 개선되는 n | Larman 목표 n |
|---|---|---|---|---|
| 5 | 11 | 13 | **12, 13** | 12 |
| 7 | 15 | 18 | 16~18 | 16 |
| 9 | 19 | 23 | 20~23 | 20 |

witness 는 n 에 **단조**다(볼록위치는 부분집합에 유전 → n 점 witness 에 점을 더해도 witness).
그래서 n 이 클수록 엄격히 쉽고, **U(d) 부터 아래로 훑는다.**

⚠ U(d) 의 출처가 미확인이다 (`questions/OPEN.md` QQ-0001 최우선). 이 값이 바뀌면 위 표가 바뀐다.

## 1-B. 상시 제약 — layer OM 은 고전 Lawrence 를 포함한다 (사용자 지시)

rank-2 layer family 는 고전 Lawrence OM 을 **진부분집합으로 포함**한다. 따라서

> **이 class 가 기존 상한을 못 넘는 일은 원리상 없다.** n_L(m) ≤ (고전 구성의 n) = 5m−2.

**모든 설계·해석은 이 전제 위에서 한다.** 실측이 이보다 나쁘게 나오면 그것은 family 의
한계가 아니라 **우리 탐색의 결함**으로 읽어야 한다. 되짚을 곳은 탐색이지 class 가 아니다.

**매장(embedding)은 확인됐다** — 짝수 rank Lawrence OM 의 rank-1 층을 **2개씩 묶으면**
각 조각이 rank-2 OM 이 된다:

    ψ_c(a,b) := s_{2c}(a)·s_{2c+1}(b)   (a<b)

  · ψ 는 **항상** 유효한 rank-2 chirotope 다 (증명: GP 3항에서 s₂ = s₃ = s_a s_b s'_c s'_d 이
    항등적으로 성립하므로, 금지 패턴 "s₁=s₃ ∧ s₂=−s₁" 은 s₂=−s₂ 를 요구해 모순. 표본 1000/1000)
  · 모든 uniform rank-2 OM 은 realizable 이고 (order, signs) 로 표현된다 (240/240 확인)
  · rank-1 Lawrence union == 2개씩 묶은 rank-2 union (80/80 완전 일치)
  · **proper**: 곱형은 진부분집합 — n=4: 32<48, n=5: 128<384, n=6: 512<3840

⚠ 종전에 적었던 "항등 order 장애"는 **범위를 잘못 잡은 것**이었다(항등 order 만 고려했음).
철회한다. 일반 order 를 허용하면 매장이 성립한다.

**귀결 1 — (3,13) witness 는 반드시 존재한다** (고전 구성 n = 5m−2 = 13). 우리 최선은
n_L(3) ≤ 15 이고 n=14 는 f=2 에서 반복 정체다. 상시 제약대로 이는 **탐색의 결함**이다.

**귀결 2 — 결함의 정체를 특정했다.** 곱형 rank-2 OM 은 전체의

    2^(2n−3) / ((n−1)!·2^(n−1)) = 2^(n−2)/(n−1)!     ← n=13 이면 약 1/233,888

밖에 안 된다. 그런데 `layer_search.random_layers` 는 (order, signs) 를 **균등 표집**한다.
즉 **답이 보장된 영역을 표본이 사실상 한 번도 방문하지 않았다.** n_L(3) 이 13 이 아니라
15 에서 멈춘 이유가 이것이다.

**따라서 다음 수**: (3,13) 을 문헌에서 번역해오기 전에 **순수 rank-1 Lawrence 부호공간에서
직접 탐색한다.** 상태는 부호벡터 2m 개, 이동은 단일 부호 뒤집기 2m·n = 78개, order 순열이
없어 공간이 훨씬 순하다. 성공하면 n_L(3) ≤ 13 · gadget 의 홀수 base cap · 탐색기 보정이
한 번에 나온다. 그다음 곱형 → 일반 layer 로 점진 확장한다(곱형이 진부분집합이므로 일반
layer 에 더 좋은 것이 있을 수 있고, 그것이 4m 을 향한 길이다).

## 2. 확정된 사실 (전부 실측 — 재유도 금지)

- **덮개 재정식화.** circuit S 의 Radon 균형은 재배향 ρ 의 **S 로의 제한**에만 의존한다
  (C^ρ_S(sᵢ) = G·ρ_{sᵢ}·C_S(sᵢ), G 는 전역 상수). 따라서
  **witness ⟺ circuit 부호벡터 γ_S 의 반경-1 해밍 실린더가 하이퍼큐브를 전부 덮는다.**
  f 재평가 172ms → 0.1ms. (`mutation_lab.py`)
- **덮개 용량은 남아돈다.** 용량비 = C(n,r+1)(r+2)/2^r — d=5 에서 **99배**, 실측 평균 중복도도 99.0.
  그런데 중복도가 **0 아니면 5 이상**이다(1~4 가 없다). 즉 "조금만 안쪽으로" 가 불가능하다.
  → simplicial depth / Bárány 선택보조정리와 이어지는 지점.
- **tope 수 불변.** uniform OM 의 acyclic 재배향 수 = Σ_{i<r} C(n−1,i). 마이크로초 적법성 프록시.
- **kill-birth 항등식.** f(χ^B) = f(χ) − |K_B| + |R_B| (정확).

## 3. 죽은 길 — 다시 걷지 말 것 (근거 포함)

| 접근 | 왜 죽었나 |
|---|---|
| 무작위 정수 box 표집 (`sweep.py`) | (10,5) 153,379 표본 witness 0. 기하급수 감쇠 모형 반증 |
| 좌표공간 국소탐색 (`climb.py`) | **realization chamber 내부에서 f 가 상수** — 원리상 gradient 없음(PROVEN). 190만 평가/0건이 이걸로 설명됨 |
| f 의 2차 목적함수(fragile circuit 수 등) | 평탄면 문제가 아니었다. f 를 낮추는 단일 돌연변이는 **전부 GP 위반**(d=4 125/125, d=5 813/813) |
| d=4 근접실패에서 돌연변이 반경 넓히기 | 반경 4 전수(2,875 노드)에도 f<1 없음. 이동집합이 아니라 **출발점**이 문제 |
| envelope 의 f-정렬 beam 가지치기 | 하강 경로의 **첫 수가 f 를 안 낮춘다** → 순위가 무의미. beam 8 로는 못 찾고 전수는 찾음 |
| 층별 상수배로 Lawrence union 실현 | Laplace 전개의 모든 항에 ∏cᵢ² 가 똑같이 붙어 원리상 무력(0/10) |

## 4. 쓰는 도구 (무엇을 언제)

| 목적 | 도구 |
|---|---|
| **상한 개선 주력** | `layer_search.py` — layer 공간 탐색. 상태가 항상 실현가능, 실측 기울기 있음(7/69 하강) |
| 실현 증명서 붙은 후보 생성 | `om_classes.extended_lawrence_r2_realized` (`extended_lawrence.py`) |
| 존재/부재의 **완전** 판정 | `covering_cegis.py` — UNSAT 이면 "없다". 단 추상 OM 만 준다 |
| 근접실패 구조 분석 | `mutation_lab.py` (kill-birth, κ₁, depth-h envelope), `nearmiss.py` |
| 판정 (유일한 권한) | `om_core.py` — 다른 어떤 모듈도 witness 를 결정하지 못한다 |

**두 축이 상보적이다**: CEGIS 는 공간이 넓지만 추상 OM 만 주고(→ ν 결론 불가),
layer family 는 실현가능성이 보장되지만 공간이 좁다. 그래서 **layer 공간 안에서 탐색**한다.

## 5. 다음 수

1. d=5 **n=13** layer 공간 탐색 → 성공 시 ν(5) ≤ 12 (증명서 동반)
2. 혼합 rank layer 구현 → 짝수 d 개방 + 고전 Lawrence 를 특수경우로 포함 (QQ-0003)
3. n_L(m) 수열을 모아 **닫힌 형식 추적** → 일반 정리 후보
4. 실현 증명서(rank-2m 벡터) → R^d **정수 점배치** 추출 3단계 구현 (DECISIONS 0035 말미)

---

## 6. 자동 생성 부록

<!-- BOOTSTRAP:BEGIN -->

_2026-08-11 02:20:07 자동 생성 (`scripts/session_bootstrap.py`)._

**저장소**: `claude/0036-bound-improvement-infra` @ `2d7a4bc` · 미커밋 변경 있음

### 실험 워크스페이스 (exec)

- 마지막 동기화: `5d20bf2ca5dd14d1` (2026-08-11 01:00:00, 파일 95개)
- **실험 진행 중**: n_L(3) 측정: m=3 하강 스윕 n=16→12 (rank-2 layer family 자체의 상한) (시작 2026-08-11 01:00:00, snapshot `5d20bf2ca5dd14d1`)
  → 이 실험이 끝나기 전에는 `sync_exec.py sync` 가 거부된다(규약 3)

### 최근 연구 기록 (research_log.md 끝 8줄)

- `n_L 측정 개시` 목표를 n_L(m)=이 family 가 witness 를 담는 최소 n 의 **증가율 α** 측정으로 정식화. n_L(m)=αm+c 이면 문헌 개선 조건은 4m+c ≤ 5m−3 ⟺ **m ≥ c+3** — 즉 상수 초과는 큰 m 이 흡수한다. α<5 면 충분히 큰 m 에서 반드시 개선. 평가비용은 ≈2^(6m−1)/(2m+2) 로 **m=4 가능·m=5 경계·m≥6 불가**(재배향 2^(n−1) 이 병목)
- `n_L(3) ≤ 15` m=3 하강 스윕(snapshot 5d20bf2ca5dd14d1): **n=16 witness(19평가/126s)**, **n=15 witness(136평가/462s)** — 둘 다 om_core 확인 + 실현 증명서 보유. 이 프로젝트 최초의 m=3 witness. n=14 는 f=2 에서 정체 중
- `m=2 전수 완료` (8,4) 게이지 고정 2,580,480개 전수 / 839s (3,077개/초 — `lawrence_union_chirotope` 의 is_valid 게이트를 우회하고 χ(a<b<c<d)=χ₁(c,d) 로 직접 구성해 6.5배 가속). **witness 64,512개 = 정확히 2.500%**. layer1 음부호 개수 분포가 1:5:10:10:5:1 (=C(5,k)) 로 정확히 이항
- `m=2 구조` witness 중 **layer1 의 order 도 항등인 것이 16개**. 이때 union 은 χ(a<b<c<d)=s_c s_d 로 부호벡터 하나가 전부를 결정하고, 조건이 완전히 factorize 된다: **s_2..s_5 가 교대(2가지) × s_1 자유(2) × s_6,s_7 자유(4) = 16**. 즉 "가운데 블록 교대 + 양 끝 2개씩 자유". n=7 에는 witness 가 없으므로 이 조건이 일반 n 으로 그대로 확장되지는 않는다 — 확장형은 반증 대상(다음 라운드)
- `상시제약` **layer OM 은 고전 Lawrence 를 proper 포함**(사용자 지시) → n_L(m) ≤ 5m−2 가 원리상 보장되므로 **이 class 가 기존 상한을 못 넘는 일은 없다.** 실측이 그보다 나쁘면 family 가 아니라 **탐색의 결함**으로 읽는다(`docs/STATE.md` §1-B). 귀결: **(3,13) 에 witness 가 반드시 존재** — 탐색 대상이 아니라 고전 구성을 layer 로 옮겨 적을 대상이며, 그것이 gadget 귀납의 홀수 base cap 을 공짜로 준다. 소박한 매장의 장애(항등 order 인 rank-2 는 부호벡터가 같은 rank-1 두 장만 재현)는 QQ-0003 로 상향
- `gadget 제안 검토` `knowledge/finite_gadget_induction.md` (Codex+사용자) 읽음. §2 가 우리 삼중항 분해와 독립 일치. 핵심 가치는 **무한 문제를 유한 판정으로 환원**하는 것. 최소화 대상은 (k,q) 가 아니라 **q/k** 하나이고(계수 = q/2k: 현재 5→2.5, 목표 4.5→2.25, Larman 4→2), §10 대로 signature 그래프의 **최소 평균 사이클**(Karp)로 데이터에서 추출해야 한다. 위험 3: (PG) 는 멱집합 전수가 아니라 **고정점 계산**·확장규칙은 "ground order 끝에 붙이기"로 구체화 가능(제한 보존 확인됨)·무한 family 실현가능성이 최약 고리
- `포함 검증` **짝수 rank Lawrence ⊂ rank-2 layer family 확인.** rank-1 층을 2개씩 묶어 ψ_c(a,b)=s_{2c}(a)s_{2c+1}(b) 로 두면 (i) ψ 는 **항상** 유효한 rank-2 chirotope (증명: GP 3항에서 s₂=s₃ 가 항등적이라 금지패턴이 모순; 표본 1000/1000), (ii) (order,signs) 로 표현 가능(240/240), (iii) rank-1 union == 묶은 rank-2 union (80/80 완전일치), (iv) **proper** (n=4·5·6 에서 32<48, 128<384, 512<3840). 종전에 적은 "항등 order 장애"는 범위 오류로 **철회**
- `탐색 결함 특정` 곱형 rank-2 OM 의 비율 = 2^(n−2)/(n−1)! — **n=13 에서 1/233,888**. `random_layers` 는 (order,signs) 균등 표집이므로 **답이 보장된 영역을 사실상 방문한 적이 없다.** n_L(3) 이 13 이 아니라 15 에서 멈춘 원인. 다음 수: **순수 rank-1 Lawrence 부호공간 탐색**(상태=부호벡터 2m장, 이동=단일 뒤집기 2m·n=78개, order 순열 없음) → 성공 시 n_L(3) ≤ 13 · gadget 홀수 base cap · 탐색기 보정을 동시 확보

### 확보된 산출물

| 파일 | 요약 |
|---|---|
| `cegis_witness_d4_n10.json` | status=SAT, n=10, r=5, best_f=0, realizability=UNKNOWN — 추상 OM. 정수 좌표 실 |
| `nearmiss_d4.json` | n=10, r=5, d=4, num_convex_reorientations=1 |
| `nearmiss_d5.json` | n=12, r=6, d=5, num_convex_reorientations=18 |
| `nearmiss_d5_f16_abstract.json` | n=12, r=6, d=5, num_convex_reorientations=16, realizability=UNKNOWN — 추상 OM 이다. 정수 좌 |

### 인간 insight 상태 (knowledge/insights/ledger.jsonl)

| ID | 상태 | 등급 | 제목 |
|---|---|---|---|
| `HI-0001` | TESTING | CONJECTURE | rank-2 extended Lawrence oriented-matroid 탐색 |
| `HI-0002` | INTEGRATED | PROVEN | minimum interval map과 circuit-defect lower e |
| `HI-0003` | TESTING | CONJECTURE | layer minimum interval map composition 휴리스틱 |
| `HI-0004` | SUPPORTED | NUMERICAL | 블록·원소별 계수로 Lawrence union을 명시적으로 실현 |
| `HI-0005` | FORMALIZED | CONJECTURE | rank-2 Lawrence의 유한 boundary-state gadget 귀납 |

### 열린 자문 질문 (questions/OPEN.md)

- QQ-0001 — 기존 상한 U(d) 의 정확한 출처와 값 · 상태 `OPEN` · 우선순위 **최상**
- QQ-0002 — rank-2 layer union 의 실현 정리 · 상태 `OPEN` · 우선순위 상
- QQ-0003 — 혼합 rank layer 로의 확장 · 상태 `OPEN` · 우선순위 중
- QQ-0004 — n=2d+2 에서 convex position 의 Gale 쌍대 특성화 · 상태 `OPEN` · 우선순위 중
- QQ-0005 — d=4 witness 의 명시 좌표 · 상태 `OPEN` · 우선순위 중

<!-- BOOTSTRAP:END -->
