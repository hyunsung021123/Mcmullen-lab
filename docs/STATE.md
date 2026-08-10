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

_2026-08-10 22:44:24 자동 생성 (`scripts/session_bootstrap.py`)._

**저장소**: `develop` @ `d1b1c78` · 미커밋 변경 있음

### 실험 워크스페이스 (exec)

- 마지막 동기화: `3dd257a75c913a94` (2026-08-10 22:38:53, 파일 88개)
- **실험 진행 중**: d=5 상한 개선: layer 공간 n 스윕 (n=13 → ν(5)≤12 개선 구간) (시작 2026-08-10 22:38:54, snapshot `3dd257a75c913a94`)
  → 이 실험이 끝나기 전에는 `sync_exec.py sync` 가 거부된다(규약 3)

### 최근 연구 기록 (research_log.md 끝 8줄)

- `cegis_calib` 덮개-CEGIS 캘리브레이션 — **(5,3) UNSAT** (하한 ν(2) ≥ 5 와 일치: "없다"를 말하는 능력 검증), (6,3) SAT 1라운드, (8,4) SAT 2라운드/0.1s. 인코딩 버그 1건 수정(재배향 인덱스 k → 원소 마스크 k<<1 누락 시 절이 무효)
- `cegis_d4_n10` **(10,5) SAT — d=4 보정 통과.** 38라운드/278절/750s, 게이지 2^10 축소. 독립 3경로 검증: om_core 전수 512개(acyclic 256, convex **0**) · mcmullen_evaluate(witness=True, implied_upper_bound=9) · reorientation_cover.evaluate_coverage(512/512 덮임). snapshot_id `10f2fae852f83720`, 기록 `cegis_witness_d4_n10.json`. **추상 OM 이므로 realizability 미확인 — ν(4) ≤ 9 를 증명하지 않는다.** 좌표탐색이 190만 회로 못 한 것을 완전 탐색이 12분에 해냈다는 것이 요점
- `cegis_d4_n9` (9,5) UNSAT 확인 시도 — 예산 초과로 결론 미도출(중단). 본 보정은 (10,5) SAT 로 달성됐으므로 후순위로 밀었다
- `HI-0001 감사` extended Lawrence rank-2 union class 반증 시험 — union GP 적법 328표본 위반 0, 재배향 교환 90회 불일치 0(둘 다 반증 안 됨). 그러나 **자명한 쌓기 실현이 union chirotope 를 12/12 재현 실패** → "layer 가 realizable 이므로 union 도 realizable" 에 즉각적 구성 근거 없음. `realizability` 를 `CLAIMED_UNVERIFIED` 로 강등, ledger HI-0001 을 INTEGRATED→TESTING·PROVEN→CONJECTURE. **채택은 함** — d=3 (8,4) 에서 후보 400개 중 witness 17개(4.25%, 무작위 실현가능 표집 1.6%보다 높음). 단 rank=d+1 이 짝수여야 하므로 **홀수 d 전용**(d=4 보정 불가) (DECISIONS 0034)
- `HI-0004` **Lawrence union 명시적 실현** — 층별 상수배는 Laplace 전개상 모든 항에 ∏c_i² 가 똑같이 붙어 원리상 무력(대조군 0/10). 원소별·블록별 계수 t^(i·λ_j) 를 쓰면 연속 짝짓기 항이 유일하게 압도 → **55/55 실현 성공**((7,4)~(12,6), λ=j+1, t∈{11,101}). 새 class `extended_lawrence_r2_realized` 는 후보마다 정수 좌표 증명서를 om_core 로 대조하고 성공분만 방출(fail-closed). (8,4) 200개 중 **realizable witness 8개**, (12,6) 60개 최선 f=40. 등급: 일반 명제는 NUMERICAL, 개별 후보는 증명서로 확정 (DECISIONS 0035)
- `layer_space` **layer 공간에 기울기가 있다** — (12,6) family f=40 에서 단일 이동 69개(인접전치 33 + 부호뒤집기 36) 전수: **7개가 하강, 최선 40→23 (한 수)**. 좌표공간(chamber 내부 f 상수, 기울기 없음)·OM 돌연변이 공간(하강 방향 전부 GP 위반)과 달리 **모든 상태가 실현 증명서를 유지**한다. 이 프로젝트에서 처음으로 쓸 수 있는 탐색 공간
- `bound_window` 기존 상한 U=2d+⌊(1+d)/2⌋ 기준 **개선 구간**: d=5 → n∈{12,13}, d=7 → {16,17,18}, d=9 → {20..23}, d=11 → {24..28}. **n=13 witness 만으로 ν(5) ≤ 12 로 개선**된다(Larman 목표 n=12 가 아니어도). witness 는 n 에 단조(부분집합이 convex position 을 물려받으므로)라 n=13 이 엄격히 쉽다 — family 무작위 표집 실측도 n=13 최선 f=17(16표본) vs n=12 f=40(60표본). **지금까지 n=12 만 본 것이 설계 오류**
- `cegis_d5_n12` (12,6) 덮개-CEGIS 중단 — 4라운드 f=66→56→45, 라운드당 11s→124s→1000s 로 8배씩 폭증. 6시간 예산 내 결론 불가로 판단. snapshot_id `d4f35548399c371d`. 방향을 layer 공간(상한 개선)으로 전환하며 보류. 재개하려면 대칭 파괴 절 + per-round 증대가 선행되어야 함

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

### 열린 자문 질문 (questions/OPEN.md)

- QQ-0001 — 기존 상한 U(d) 의 정확한 출처와 값 · 상태 `OPEN` · 우선순위 **최상**
- QQ-0002 — rank-2 layer union 의 실현 정리 · 상태 `OPEN` · 우선순위 상
- QQ-0003 — 혼합 rank layer 로의 확장 · 상태 `OPEN` · 우선순위 중
- QQ-0004 — n=2d+2 에서 convex position 의 Gale 쌍대 특성화 · 상태 `OPEN` · 우선순위 중
- QQ-0005 — d=4 witness 의 명시 좌표 · 상태 `OPEN` · 우선순위 중

<!-- BOOTSTRAP:END -->
