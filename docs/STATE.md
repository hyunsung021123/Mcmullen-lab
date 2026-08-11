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
U(d) = 2d + ⌈(d+1)/2⌉ − 1 기준으로 **witness at n ⟹ ν(d) ≤ n−1** 이므로
**n ≤ U(d) 인 witness 가 개선**이다.

| d | 하한 2d+1 | U(d) | 고전 구성 n=5m−2 | 개선되는 n | Larman 목표 n |
|---|---|---|---|---|---|
| 5 | 11 | 12 | 13 | **12 뿐** (= Larman) | 12 |
| 7 | 15 | 17 | 18 | 16, 17 | 16 |
| 9 | 19 | 22 | 23 | 20~22 | 20 |
| 11 | 23 | 27 | 28 | 24~27 | 24 |

witness 는 n 에 **단조**다(볼록위치는 부분집합에 유전 → n 점 witness 에 점을 더해도 witness).
그래서 n 이 클수록 엄격히 쉽고, **U(d) 부터 아래로 훑는다.** 개선 구간 크기는 m−2 다.

**U(d) 의 출처는 우리 코드 안에서 확인됐다 (QQ-0001 자체 해결, 2026-08-11).** 고전 Lawrence
구성이 n = 5m−2 에서 witness 를 주고 그것이 곧 ν(d) ≤ 5m−3 = (5d−1)/2 = U(d) 다. d=3,5,7,9,11
에서 5m−3 == U(d) 대조 전항목 일치(`lawrence_signs.selftest` [6]), 그리고 **(5,13) 에서
실제 witness 를 실현 증명서까지 붙여 재현**했다. 즉 개선이란 곧 **고전 구성보다 n 을 하나
더 줄이는 것**이다. ⚠ 남은 미확인: d=5 에 한정된 더 나은 문헌 값이 있는지 (QQ-0001 4번).

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

**→ 실행 완료 (2026-08-11, `lawrence_signs.py`, snapshot `ad6e4b6ce141cc27`).** 진단이 맞았다.

  · **매장의 명시적 형태 확보** — QQ-0003 의 "항등 order 장애"는 항등 order 를 고집한 탓이다.
    σ=s_{2c}, τ=s_{2c+1}, g(b)=σ(b)τ(b) 로 두고 order 를 **deque 구성**(g(b)=+ 면 오른쪽,
    − 면 왼쪽), signs=σ 로 하면 chi(a,b)=σ(a)σ(b)g(b)=σ(a)τ(b) 가 a<b 에서 항등적으로
    성립한다. 240/240 일치. 그래서 rank-1 상태가 실현 증명서를 그대로 물려받는다.
  · **(5,13) witness 를 151평가·2.9초에** 찾았다. 같은 지점에서 layer 공간은 934평가·488초를
    쓰고 f=1 에서 막혔다. **n_L(3) ≤ 13 = 5m−2 (고전 구성 크기 도달).**
  · 게이지는 (A) 장 전역반전 s_p→−s_p (χ→−χ, 같은 OM) 과 (B) 원소 e 에서 **모든 장 동시반전**
    (= e 의 재배향) 두 개다. s_0 ≡ + 와 s_p(0)=+ 를 고정하면 자유 비트가 (2m−1)(n−1) 이고
    모든 궤도가 대표원소를 가지므로 **전수는 완전하다**(UNSAT 을 말할 수 있다).
  · 전수 실측: (3,7) 2^18 전부 witness 아님(최선 f=4, layer 공간 전수와 독립 일치) ·
    (3,8) 2^21 중 witness **2^17 = 정확히 1/16**(layer 공간 2.500% 대비 2.5배 조밀).

**남은 것**: (5,12). 곧 이 family 가 고전 구성보다 하나 더 줄일 수 있는가 — 이것이 곧
d=5 Larman 이다. 그다음 곱형 → 일반 layer 로 점진 확장한다(곱형이 진부분집합이므로 일반
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

**사용자 지정 최우선 순위 (2026-08-12):**

1. `HI-0006`의 고전 Lawrence 접합 귀납을 exact boundary-state automaton과 Claude의
   완전 계산으로 증명 또는 반증한다. 첫 gate는 `(d,n)=(5,12)` CEGIS이고, 증명
   본체는 boundary signature의 right congruence와 reachable-set closure다.
2. 그 과정에서 검증한 powerset/orbit 엔진을 `HI-0005`의 rank-2 layer OM에 옮긴다.
   `(k,q)=(2,10)` 고전 임베딩을 양성 대조군으로 통과시킨 뒤 `(2,9)` 유한 gadget을
   탐색한다.

계산 조건과 인증서 규격은 `knowledge/gluing_induction_computational_spec.md`에 있다.
아래 기존 탐색 항목은 이 두 목표보다 후순위다.

1. ~~d=5 **n=13** 탐색~~ **완료** — `lawrence_signs` 로 151평가·2.9초, 증명서 동반 (§1-B)
2. **(3,8) 의 1/16 을 구조로 설명하라.** witness 비율이 정확히 2^(−4) 라는 것은 조건이
   **독립 이진 제약 4개로 factorize** 된다는 뜻이다. m=2 구조 라운드("가운데 블록 교대 +
   양 끝 2개씩 자유")와 이어붙이면 일반 n·m 으로 확장할 **닫힌 형식 후보**가 나온다.
   이것이 n_L(m) 을 탐색이 아니라 **계산**으로 얻는 가장 짧은 길이다
3. **(5,12)**: 이 family 가 고전 구성보다 하나 더 줄일 수 있는가 = d=5 Larman.
   전수는 2^60 이라 불가 — 2번의 구조식이 나오면 그것으로 판정하는 것이 정공법이다
4. **d=7 을 열려면 평가기부터**. (7,18) 은 현재 평가 1회도 분 단위다. 병목은 재배향
   2^(n−1) 이 아니라 `CoverageScanner.__init__` 의 circuit 구성 C(18,9)=48,620개다 —
   단일 비트 뒤집기에 대한 **증분 갱신**(뒤집힌 비트가 건드리는 basis 만 재계산)이 선행 조건.
   열리면 d=7 은 n∈{16,17} 로 개선 구간이 둘이라 d=5 보다 헐겁다
5. 혼합 rank layer 구현 → 짝수 d 개방 (QQ-0003 1·3번; 2번은 자체 해결됨)
6. 실현 증명서(rank-2m 벡터) → R^d **정수 점배치** 추출 3단계 구현 (DECISIONS 0035 말미).
   현재 증명서의 좌표는 t^(i·λ_j) 라 (5,13) 에서 max|coord| ≈ 1.3e52 — 축소도 함께 필요

---

## 6. 자동 생성 부록

<!-- BOOTSTRAP:BEGIN -->

_2026-08-12 03:47:58 자동 생성 (`scripts/session_bootstrap.py`)._

**저장소**: `claude/0036-bound-improvement-infra` @ `47c08e6` · 미커밋 변경 있음

### 실험 워크스페이스 (exec)

- 마지막 동기화: `ad6e4b6ce141cc27` (2026-08-11 08:46:59, 파일 97개)
- 실행 잠금 없음 (sync 가능)

### 최근 연구 기록 (research_log.md 끝 8줄)

- `A* 재현` 논문 Definition 3.2 의 극단 chessboard(행별 검정칸 **2,3,2,3,…** 계단, n=2(r−1)+⌈r/2⌉)를 복원해 d=2·3·4·5 에서 **witness 임을 travel·om_core 양 경로로 확인 + 실현 증명서**. Theorem 1.1 을 저장소가 독립 재현했다 → 모든 d 에서 f(d) ≤ ⌊5d/2⌋
- `f(4) ≥ 9 증명` (4,9) 밴드 축소 2²⁰ 전수 완주, **witness 0**, 최선 f=13 → 사용자의 검증식 (2,2) `f(2)+f(2)−1 = 9 ≤ f(4)` **확정**. (4,10) 전수는 목표식 (2,2) 를 결정한다
- `f(4) = 10 확정 · 목표식 (2,2) 증명` **(4,10) 밴드 축소 2²⁰ = 1,048,576 전수 완주 / 2,673s → witness 0, 최선 f=1.** f(4) ≥ 10 이고, (4,11) 의 실현 witness 로 f(4) ≤ 10 이므로 **f(4) = 10**. 따라서 사용자의 목표식 최초 비자명 사례 `f(2)+f(2) = 5+5 = 10 ≤ f(4) = 10` 이 **등호로 성립**한다(⌊5d/2⌋ 의 갭 구조가 예측한 대로 — a,b 둘 다 짝수면 갭 0). 측정 4점 f = 2·5·7·10 이 전부 ⌊5d/2⌋ = U(d). ⚠ 이 전수는 exec 가 아니라 main 작업트리에서 돌아 snapshot_id 가 없다 — 재현은 `python lawrence_signs.py exhaustive --d 4 --n 10`
- `HI-0006 축약 확인` 목표식은 **b=2 하나면 충분**하다 — 단계 +5 로 귀납하면 base f(2)=5, f(3)=7 에서 d=1..12 전부 ⌊5d/2⌋=U(d) 를 재현하므로 f(d) ≥ U(d) = 개선 불가. 반면 검증식(−1)은 단계 +4 라 U(d) 와 갭이 계속 벌어진다(d=12 에서 25 vs 30). 자문 문서 `knowledge/lawrence_f_additivity.md` + QQ-0006
- `Codex 답변 검증 — Lemma 2.1` Codex 가 준 직접 증명(TT 하강열 t_0<…<t_r 에서 C(t_k)/C(t_{k−1}) = −a_{k,t_{k−1}}/a_{k,t_k} = +1 이므로 양의 회로, t_r<n 은 안 쓰임)을 실측 확인. 4(b) 종료 표본 1,237건 중 **t_r = n 인 것이 461건(37%)** — 논문 문면 `1 ≤ s < n` 이 배제하던 경우인데 사슬 조건 위반 0, 양의 회로 아님 0, om_core 불일치 0. **코너 케이스가 아니라 실질적 누락**이며 2015 재수록본도 같은 문장을 복제하고 있다
- `lawrence_cegis 보정` 명세 C0 대로 **Lawrence 부호변수 전용** 덮개-CEGIS 구현(`lawrence_cegis.py`). 일반 OM CEGIS 와 달리 기저 변수 C(12,6)=924 개와 GP 제약이 **통째로 불필요** — χ(B) 부호가 primary bit 최대 R 개의 XOR 이라서다. (5,12) 는 변수 30개. 답을 아는 4점 보정 전부 통과: (3,7) UNSAT 0.1s · (3,8) SAT+om_core+증명서 0.3s · **(4,10) UNSAT 24.1s** (같은 결론에 전수는 2,673s — **111배**) · (4,11) SAT 8.4s. **(5,13) SAT_WITNESS 1,377.7s** (19라운드/311절, om_core=True·GP=True·실현 증명서 — A* 와 독립으로 자체 발견). **보정 5/5 완결.** (5,13) 대조군이 중요한 이유: 그것이 gate 인 (5,12) 보다 **큰** 규모(변수 35 vs 30, circuit 1716 vs 792)인데 23분에 풀렸으므로, (5,12) 가 몇 시간을 끌면 그것은 '이 규모에서 느림' 이 아니라 **어려운 UNSAT** 쪽 신호다
- `GATE C0 — (5,12) UNSAT` **45라운드/545절/5,266s(88분)에 UNSAT.** survivor 232→91→60→37→8→6 로 수렴 후 소진. ⟹ **f(5) ≥ 12**, A* 의 n=13 witness 로 f(5) ≤ 12 이므로 **f(5) = 12**. 사용자 목표식의 두 번째 사례 `f(2)+f(3) = 5+7 = 12 ≤ f(5) = 12` 가 **또 등호로** 성립(갭 구조 예측대로 — a,b 가 둘 다 홀수가 아니면 갭 0). 동시에 **Lawrence OM 은 d=5 에서 문헌 상한을 깨지 못한다**. ⚠ **등급은 PROVEN 이 아니다** — 명세 C0 대로 solver UNSAT 단독은 근거가 못 된다. 독립 전수는 2^30 × 14.9ms = **2,722시간**이라 불가(조기중단 9.1ms 로도 마찬가지 — 병목은 재배향이 아니라 상태당 `CoverageScanner.__init__` 의 circuit 792개 구성). 승격 경로는 두 가지: (a) 단일 비트 뒤집기 **증분 circuit 갱신** 으로 평가를 ~0.1ms 로 낮춰 Gray-code 전수(약 30시간), (b) DIMACS 내보내기 + 독립 solver 의 **DRAT proof** + 검사기
- `d=7 보류` (7,18) 평가가 10분 내 3회도 못 끝냄. 병목은 재배향 2^(n−1) 이 아니라 `CoverageScanner.__init__` 의 circuit 구성 C(18,9)=48,620개 × chi(8원소 버블정렬). 종전 추정("m=4 가능")은 재배향만 센 것이라 **낙관적이었다**. d=7 을 열려면 circuit 구성의 증분 갱신이 선행되어야 한다

### 확보된 산출물

| 파일 | 요약 |
|---|---|
| `cegis_d5_n12_lawrence.json` | status=UNSAT, n=12, r=6, d=5 |
| `cegis_d5_n13_control.json` | status=SAT_WITNESS, n=13, r=6, d=5, bound_gain=0, realizability=REALIZABLE |
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
| `HI-0006` | TESTING | NUMERICAL | f(d) 초가법성으로 Lawrence 상한 개선 가능성 판정 |
| `HI-0007` | FORMALIZED | CONJECTURE | 고전 Lawrence 접합 automaton의 rank-2 gadget 전이 |

### 열린 자문 질문 (questions/OPEN.md)

- QQ-0001 — 기존 상한 U(d) 의 정확한 출처와 값 · 상태 `OPEN` · 우선순위 **최상**
- QQ-0002 — rank-2 layer union 의 실현 정리 · 상태 `OPEN` · 우선순위 상
- QQ-0003 — 혼합 rank layer 로의 확장 · 상태 `OPEN` · 우선순위 중
- QQ-0004 — n=2d+2 에서 convex position 의 Gale 쌍대 특성화 · 상태 `OPEN` · 우선순위 중
- QQ-0005 — d=4 witness 의 명시 좌표 · 상태 `OPEN` · 우선순위 중
- QQ-0006 — Lawrence OM 상한의 최적성 (f 초가법성) · 상태 `OPEN` · 우선순위 **최상**

<!-- BOOTSTRAP:END -->
