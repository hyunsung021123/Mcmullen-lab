# McMullen 연구 루프 — 구조 분석 및 다음 방향 요청

## 문제

McMullen 문제. ν(d) = "일반위치의 어떤 ν(d)개 점도 적당한 사영변환으로 convex
position 으로 보낼 수 있는" 최대 수. 하한 ν(d) ≥ 2d+1 은 **이미 알려져 있다**.
따라서 계산의 목표는 반례 찾기가 아니라, **n = 2d+2 개의 나쁜 배치(obstruction)**
를 찾아 상한 ν(d) ≤ 2d+1 을 닫는 것이다.

### 이 저장소의 정식화 (정확히 이 뜻으로만 쓸 것)

- R^d 일반위치 n점 → 동차화 → rank r = d+1 uniform chirotope χ.
- 사영변환 ↔ 재배향(원소별 부호반전). 전역반전은 무해하므로 재배향 공간은
  (Z/2)^(n-1), 크기 2^(n-1).
- convex position ⟺ 모든 circuit(= 최소 Radon 분할, uniform 이므로 (r+1)-부분집합)
  이 **균형**: 양·음 양쪽 크기가 모두 ≥ 2.
- **witness** ⟺ 2^(n-1) 개 재배향 중 convex 가 되는 것이 하나도 없음.
  n 에서 witness 를 찾으면 상한이 n−1 로 내려간다. 목표는 n = 2d+2.
- 이 동치의 근거: convex ⟹ acyclic 이고, acyclic 재배향 = tope = 선형범함수로
  재정규화 가능한 배치이므로, 전체 재배향을 훑는 것과 모든 사영상을 훑는 것이
  (실현가능한 경우) 같다.

### 현재 상태

- d=2 (r=3, n=6), d=3 (r=4, n=8) 에서 witness 가 확인됨.
- (5,3), (6,4) 에는 witness 가 없음이 전수로 확인됨.
- **d=5 (rank 6, n=12) 가 미해결 본 목표.** 전수 열거는 2^924 라 불가능하다.


## 이 프로젝트의 신뢰 규약 (반드시 지킬 것)

당신의 답변은 사람이 아니라 **결정론적 검사기**가 받는다. 다음을 지키지 않으면
제안은 자동으로 기각된다.

1. 다음 다섯 등급을 절대 섞지 말 것. 각 주장마다 등급을 명시하라.
   - `PROVEN`      : 당신이 완전한 증명을 제시한 것
   - `VERIFIED`    : 이 보고서에 계산으로 확인됐다고 적힌 유한 사례
   - `NUMERICAL`   : 수치적 증거일 뿐
   - `CONJECTURE`  : 반증 가능하지만 아직 미증명
   - `SPECULATION` : 직관/유추
2. 보조정리를 제안하면, **먼저 반례를 찾으려고 시도한 흔적**을 보여라.
   반례 탐색을 하지 않은 보조정리는 낮게 취급된다.
3. 추상 유향 매트로이드(OM)는 자동으로 **실현가능하지 않다**. n=2d+2 에서
   비실현 witness 를 찾는 것은 ν(d) 상한에 대해 아무것도 증명하지 않는다.
   실현가능성이 필요한 주장이면 그 사실을 명시하라.
4. 추측은 **계산으로 반증 가능한 형태**로 제시하라. 아래 원자(atom) 형식을 쓰면
   이 저장소가 즉시 대규모로 공격한다.
5. "그럴듯해 보인다"는 검증이 아니다. 반례가 없다는 것은 증명이 아니다.


## 이번 라운드의 계산 결과

코퍼스: `{"total": 1500, "witness": 1258, "nonwitness": 242, "scope": {"backend": "backtracking", "exhaustive": false, "realizability": "UNKNOWN", "how": "generate_backtracking(n=6,r=3,max=1500)", "generator_stats": {"nodes": 9573, "emitted": 1500, "hit_candidate_cap": true, "hit_node_cap": false, "exhausted": false}, "realizability_note": "GP 공리만 만족하는 추상 OM 이라 실현가능성은 알 수 없다. 비실현 witness 는 OM 판본의 상한만 말할 뿐 ν(d) 에 대해서는 아무것도 증명하지 않는다.", "n": 6, "r": 3, "d": 2, "om_class": "uniform", "seed": 20260809}, "features": 21, "realizability": "UNKNOWN", "realizability_note": "GP 공리만 만족하는 추상 OM 이라 실현가능성은 알 수 없다. 비실현 witness 는 OM 판본의 상한만 말할 뿐 ν(d) 에 대해서는 아무것도 증명하지 않는다."}`

### 현재 불변량 어휘

| 이름 | 종류 | 출처 | 재명명불변 | 재배향불변 | 설명 |
|---|---|---|---|---|---|
| `acyclic` | bool | builtin | O | X | 양의 회로가 없음 |
| `automorphism_order` | int | builtin | O | O | (Z2)^n⋊S_n 안에서 χ 를 고정하는 부분군의 크기 (n<=6 에서만; 그 외 None). 비용 등급 expensive — 기본 어휘에서 제외, 명시적으로 켜야 함 |
| `circuit_balance_profile` | tuple | builtin | O | X | Radon 분할 균형의 히스토그램 — 원소 이름과 무관한 구조 지문 |
| `cocircuit_balance_profile` | tuple | builtin | O | X | 초평면 분할 균형 히스토그램 — Gale/쌍대 쪽 구조 지문 |
| `convex_position` | bool | builtin | O | X | 모든 Radon 분할이 균형 (= 이 대표원소 자체가 convex) |
| `convex_tope_ratio` | ratio | builtin | O | O | convex 재배향 / tope 수 — 0 에 얼마나 가까운지로 '근접 실패'를 잰다 |
| `corank` | int | builtin | O | O | 쌍대 rank n−r. n=2d+2 목표점에서는 rank 와 같아진다(자기쌍대 rank) |
| `max_circuit_balance` | int | builtin | O | ? | 가장 균형잡힌 Radon 분할의 작은 쪽 크기 (재배향 불변성 미확인 — 작은 n 에서는 상수처럼 보이나 일반 근거 없음) |
| `min_circuit_balance` | int | builtin | O | X | 가장 치우친 Radon 분할의 작은 쪽 크기 |
| `min_cocircuit_balance` | int | builtin | O | X | 가장 치우친 초평면의 작은 쪽 크기 |
| `n` | int | builtin | O | O | 원소 수 |
| `num_convex_reorientations` | int | builtin | O | O | convex position 이 되는 재배향의 수 (전역반전 몫). witness ⟺ 이 값이 0 |
| `num_extreme_elements` | int | builtin | O | X | 어떤 Radon 분할에서도 혼자 갇히지 않는 원소 수 (= 이 대표원소의 볼록껍질 꼭짓점 수) |
| `num_halving_cocircuits` | int | builtin | O | X | 양쪽을 가장 고르게 나누는 초평면(halving)의 수 |
| `num_positive_circuits` | int | builtin | O | X | 한쪽이 비어 있는 회로 수 (acyclic ⟺ 이 값이 0) |
| `num_singleton_circuits` | int | builtin | O | X | 한쪽이 정확히 1인 Radon 분할 수 (= 볼록껍질 내부에 갇힌 사례 수) |
| `num_tope_pairs` | int | builtin | O | O | acyclic 이 되는 재배향의 수 (전역반전 몫) = tope 쌍의 수. 실현가능한 경우 '사영변환으로 얻을 수 있는 점배치'의 가짓수 |
| `rank` | int | builtin | O | O | rank r = d+1 |
| `reorientation_symmetry_order` | int | builtin | O | O | χ 를 그대로 두는 재배향의 수 (전역반전 포함 안 함) |
| `singleton_degree_profile` | tuple | builtin | O | X | 원소별 '혼자 갇힌 횟수'의 히스토그램 |
| `tope_fraction` | ratio | builtin | O | O | tope 수 / 2^(n−1) — 재배향 중 acyclic 인 비율 |
| `totally_cyclic` | bool | builtin | O | X | 양의 코회로가 없음 (acyclic 의 쌍대; convex 와 무관) |
| `witness` | bool | builtin | O | O | 어떤 재배향으로도 convex position 이 되지 않음 (McMullen 상한 witness). om_core.is_reorientable_to_convex 와 동치이며 reorientation_cover 와 같은 공식 |

# 추측 채굴 보고

- 범위(scope): `{"backend": "backtracking", "exhaustive": false, "realizability": "UNKNOWN", "how": "generate_backtracking(n=6,r=3,max=1500)", "generator_stats": {"nodes": 9573, "emitted": 1500, "hit_candidate_cap": true, "hit_node_cap": false, "exhausted": false}, "realizability_note": "GP 공리만 만족하는 추상 OM 이라 실현가능성은 알 수 없다. 비실현 witness 는 OM 판본의 상한만 말할 뿐 ν(d) 에 대해서는 아무것도 증명하지 않는다.", "n": 6, "r": 3, "d": 2, "om_class": "uniform", "seed": 20260809}`
- 표본: 전체 1500 (witness 1258 / non-witness 242)
- 사용한 불변량 21개

> 아래는 전부 **관찰(MINED)** 이며 증명이 아니다. `falsify.py` 를 통과하기 전에는 어떤 것도 정리로 인용하지 말 것.

## witness 의 필요조건 (1건)

- **cj-987083fe** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6992)
  - (witness 이다) ⟹ (convex_position = 거짓)
  - 지지: `{"witness": 1258, "nonwitness": 242, "nonwitness_also_satisfying": 218, "discrimination": 0.0992}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5

## witness 의 충분조건 (12건)

- **cj-1efce1c1** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 2.1671)
  - (num_singleton_circuits == 7) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 388, "coverage": 0.3084}`
  - 반증 시도: `{"conjecture_id": "cj-1efce1c1", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 4.887, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 3.265, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
- **cj-7d869b8e** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 2.1656)
  - (circuit_balance_profile == ((1, 7), (2, 8))) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 387, "coverage": 0.3076}`
  - 반증 시도: `{"conjecture_id": "cj-7d869b8e", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 4.967, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 3.072, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
- **cj-78a0f4dd** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.9874)
  - (num_extreme_elements == 5) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 265, "coverage": 0.2107}`
  - 반증 시도: `{"conjecture_id": "cj-78a0f4dd", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 4.942, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 3.105, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
- **cj-d81b3b42** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.9186)
  - (num_singleton_circuits == 11) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 218, "coverage": 0.1733}`
  - 반증 시도: `{"conjecture_id": "cj-d81b3b42", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 4.946, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 3.059, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
- **cj-29b6208b** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.812)
  - (singleton_degree_profile == ((0, 3), (3, 1), (4, 2))) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 145, "coverage": 0.1153}`
  - 반증 시도: `{"conjecture_id": "cj-29b6208b", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 5.023, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 3.102, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
- **cj-6241fe2d** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.7769)
  - (num_singleton_circuits == 3) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 121, "coverage": 0.0962}`
- **cj-2bde97ab** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.7754)
  - (num_singleton_circuits == 4) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 120, "coverage": 0.0954}`
- **cj-1bfcb7a5** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.7418)
  - (singleton_degree_profile == ((0, 4), (3, 1), (5, 1))) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 97, "coverage": 0.0771}`
- **cj-20d92134** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.7067)
  - (singleton_degree_profile == ((0, 3), (3, 2), (5, 1))) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 73, "coverage": 0.058}`
- **cj-4932ebfd** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6351)
  - (num_halving_cocircuits == 6) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 24, "coverage": 0.0191}`
- **cj-502dbfe2** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6351)
  - (num_singleton_circuits == 5) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 24, "coverage": 0.0191}`
- **cj-cb47e71c** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6351)
  - (num_singleton_circuits == 9) ⟹ (witness 이다)
  - 지지: `{"witness": 1258, "nonwitness": 242, "antecedent_true": 24, "coverage": 0.0191}`

## 구조 함의 (보조정리 후보) (27건)

- **cj-d0c7255c** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.9833)
  - (min_circuit_balance == 1) ⟹ (acyclic = 참)
  - 지지: `{"antecedent_true": 1475, "consequent_true": 1499, "total": 1500}`
  - 반증 시도: `{"conjecture_id": "cj-d0c7255c", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 0.852, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 0.581, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: totally_cyclic = 거짓, min_circuit_balance >= 1, min_cocircuit_balance <= 0, min_cocircuit_balance == 0
- **cj-edec4bfa** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.9833)
  - (min_circuit_balance == 1) ⟹ (convex_position = 거짓)
  - 지지: `{"antecedent_true": 1475, "consequent_true": 1476, "total": 1500}`
  - 반증 시도: `{"conjecture_id": "cj-edec4bfa", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 0.617, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 0.36, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5
- **cj-fd3c718d** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.9033)
  - (num_singleton_circuits >= 4) ⟹ (convex_position = 거짓)
  - 지지: `{"antecedent_true": 1355, "consequent_true": 1476, "total": 1500}`
  - 반증 시도: `{"conjecture_id": "cj-fd3c718d", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 0.625, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 0.36, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5
- **cj-cc4d623f** `[REPRESENTATIVE_DEPENDENT]` `REFUTED` (score 1.8387)
  - (num_singleton_circuits <= 10) ⟹ (num_halving_cocircuits <= 5)
  - 지지: `{"antecedent_true": 1258, "consequent_true": 1476, "total": 1500}`
  - 반증 시도: `{"conjecture_id": "cj-cc4d623f", "verdict": "REFUTED", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "REFUTED", "tested": 1503, "exhausted": false, "elapsed_s": 0.131, "counterexample": {"chirotope": {"n": 6, "r": 3, "signs": {"0,1,2": 1, "0,1,3": 1, "0,1,4": 1, "0,1,5": -1, "0,2,3": 1, "0,2,4": 1, "0,2,5": 1, "0,3,4": 1, "0,3,5": 1, "0,4,5": 1, "1,2,3": 1, "1,2,4": 1, "1,2,5": -1, "1,3,4": 1, "1,3,5": -1, "1,4,5": 1, "2,3,4": 1, "2,3,5": -1, "2,4,5": -1, "3,4,5": -1}}, "features": {"num_halving_cocircuits": 7, "num_singleton_circuits": 6}, "failed_atom": "num_halving_cocircuits <= 5"}, "note": "전건은 성립하는데 후건이 깨지는 대상을 찾았다"}, "extensions": []}`
- **cj-a8f103ec** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.8073)
  - (num_extreme_elements <= 4) ⟹ (convex_position = 거짓)
  - 지지: `{"antecedent_true": 1211, "consequent_true": 1476, "total": 1500}`
  - 반증 시도: `{"conjecture_id": "cj-a8f103ec", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 0.64, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 0.362, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5
- **cj-6a8089d0** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.8073)
  - (num_extreme_elements <= 4) ⟹ (num_singleton_circuits >= 4)
  - 지지: `{"antecedent_true": 1211, "consequent_true": 1355, "total": 1500}`
  - 반증 시도: `{"conjecture_id": "cj-6a8089d0", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 1.045, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "EXTENDS", "tested": 3000, "exhausted": false, "elapsed_s": 0.604, "counterexample": null, "note": "예산 3000개 안에서 반례 없음 — 전수가 아니므로 증거로 약함"}]}`
- **cj-def73549** `[REPRESENTATIVE_DEPENDENT]` `EXHAUSTED_ON_SCOPE` (score 1.79)
  - (num_halving_cocircuits >= 4) ⟹ (convex_position = 거짓)
  - 지지: `{"antecedent_true": 1185, "consequent_true": 1476, "total": 1500}`
  - 반증 시도: `{"conjecture_id": "cj-def73549", "verdict": "EXHAUSTED_ON_SCOPE", "in_scope": {"scope": {"n": 6, "r": 3, "backend": "backtracking", "budget": 20000}, "status": "EXHAUSTED_ON_SCOPE", "tested": 11904, "exhausted": true, "elapsed_s": 0.603, "counterexample": null, "note": "이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"}, "extensions": [{"scope": {"n": 7, "r": 3, "backend": "backtracking", "budget": 3000}, "status": "FAILS_TO_EXTEND", "tested": 1, "exhausted": false, "elapsed_s": 0.0, "counterexample": {"chirotope": {"n": 7, "r": 3, "signs": {"0,1,2": 1, "0,1,3": 1, "0,1,4": 1, "0,1,5": 1, "0,1,6": 1, "0,2,3": 1, "0,2,4": 1, "0,2,5": 1, "0,2,6": 1, "0,3,4": 1, "0,3,5": 1, "0,3,6": 1, "0,4,5": 1, "0,4,6": 1, "0,5,6": 1, "1,2,3": 1, "1,2,4": 1, "1,2,5": 1, "1,2,6": 1, "1,3,4": 1, "1,3,5": 1, "1,3,6": 1, "1,4,5": 1, "1,4,6": 1, "1,5,6": 1, "2,3,4": 1, "2,3,5": 1, "2,3,6": 1, "2,4,5": 1, "2,4,6": 1, "2,5,6": 1, "3,4,5": 1, "3,4,6": 1, "3,5,6": 1, "4,5,6": 1}}, "features": {"convex_position": true, "num_halving_cocircuits": 7}, "failed_atom": "convex_position = 거짓"}, "note": "전건은 성립하는데 후건이 깨지는 대상을 찾았다"}]}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5
- **cj-a9381f78** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.79)
  - (num_halving_cocircuits >= 4) ⟹ (num_singleton_circuits >= 4)
  - 지지: `{"antecedent_true": 1185, "consequent_true": 1355, "total": 1500}`
- **cj-67bb8367** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.694)
  - (num_halving_cocircuits <= 4) ⟹ (num_singleton_circuits <= 10)
  - 지지: `{"antecedent_true": 1041, "consequent_true": 1258, "total": 1500}`
- **cj-784991af** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6773)
  - (num_singleton_circuits <= 8) ⟹ (num_halving_cocircuits <= 5)
  - 지지: `{"antecedent_true": 1016, "consequent_true": 1476, "total": 1500}`
- **cj-25c70de1** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6767)
  - (num_extreme_elements >= 4) ⟹ (acyclic = 참)
  - 지지: `{"antecedent_true": 1015, "consequent_true": 1499, "total": 1500}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: totally_cyclic = 거짓, min_circuit_balance >= 1, min_cocircuit_balance <= 0, min_cocircuit_balance == 0
- **cj-9af1c76e** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6767)
  - (num_extreme_elements >= 4) ⟹ (num_halving_cocircuits <= 5)
  - 지지: `{"antecedent_true": 1015, "consequent_true": 1476, "total": 1500}`
- **cj-bf12b465** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6767)
  - (num_extreme_elements >= 4) ⟹ (num_singleton_circuits <= 10)
  - 지지: `{"antecedent_true": 1015, "consequent_true": 1258, "total": 1500}`
- **cj-ae0bdecb** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.6767)
  - (num_extreme_elements >= 4) ⟹ (num_singleton_circuits <= 8)
  - 지지: `{"antecedent_true": 1015, "consequent_true": 1016, "total": 1500}`
- **cj-9f77f76f** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_extreme_elements == 4) ⟹ (acyclic = 참)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1499, "total": 1500}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: totally_cyclic = 거짓, min_circuit_balance >= 1, min_cocircuit_balance <= 0, min_cocircuit_balance == 0
- **cj-bc470499** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_extreme_elements == 4) ⟹ (convex_position = 거짓)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1476, "total": 1500}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5
- **cj-5931208b** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_extreme_elements == 4) ⟹ (min_circuit_balance == 1)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1475, "total": 1500}`
- **cj-010e3f28** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_extreme_elements == 4) ⟹ (num_halving_cocircuits <= 5)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1476, "total": 1500}`
- **cj-7d657e03** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_extreme_elements == 4) ⟹ (num_singleton_circuits <= 10)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1258, "total": 1500}`
- **cj-4c057cd9** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_extreme_elements == 4) ⟹ (num_singleton_circuits <= 8)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1016, "total": 1500}`
- **cj-24ea8bde** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_extreme_elements == 4) ⟹ (num_singleton_circuits >= 4)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1355, "total": 1500}`
- **cj-15da3a39** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_halving_cocircuits == 4) ⟹ (convex_position = 거짓)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1476, "total": 1500}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5
- **cj-59d1c244** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_halving_cocircuits == 4) ⟹ (num_singleton_circuits <= 10)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1258, "total": 1500}`
- **cj-f2df2251** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.484)
  - (num_halving_cocircuits == 4) ⟹ (num_singleton_circuits >= 4)
  - 지지: `{"antecedent_true": 726, "consequent_true": 1355, "total": 1500}`
- **cj-175bafe4** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.4513)
  - (num_singleton_circuits >= 8) ⟹ (acyclic = 참)
  - 지지: `{"antecedent_true": 677, "consequent_true": 1499, "total": 1500}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: totally_cyclic = 거짓, min_circuit_balance >= 1, min_cocircuit_balance <= 0, min_cocircuit_balance == 0
- **cj-20ec8178** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.4513)
  - (num_singleton_circuits >= 8) ⟹ (convex_position = 거짓)
  - 지지: `{"antecedent_true": 677, "consequent_true": 1476, "total": 1500}`
  - 비고: 코퍼스에서 후건과 진리값이 같은 다른 표현: min_circuit_balance <= 1, num_extreme_elements <= 5
- **cj-e8fa575f** `[REPRESENTATIVE_DEPENDENT]` `MINED` (score 1.4513)
  - (num_singleton_circuits >= 8) ⟹ (min_circuit_balance == 1)
  - 지지: `{"antecedent_true": 677, "consequent_true": 1475, "total": 1500}`


# 반증 시도 결과

- 공격한 명제 12건 → 반증 1 / 범위내 전수확인 11 / 미해결 0

> `EXHAUSTED_ON_SCOPE` 는 **그 유한 범위에서만** 확인된 것이다. 정리가 아니다.
> 확장 시험의 `FAILS_TO_EXTEND` 는 원 명제의 반증이 아니라 '더 큰 범위로는
> 넘어가지 않는다'는 별개의 사실이다.

## cj-1efce1c1 — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 2.1671)

- 명제: (num_singleton_circuits == 7) ⟹ (witness 이다)
- 형식: `forall chi in scope: (num_singleton_circuits == 7) -> (witness == True)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 4.887s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-7d869b8e — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 2.1656)

- 명제: (circuit_balance_profile == ((1, 7), (2, 8))) ⟹ (witness 이다)
- 형식: `forall chi in scope: (circuit_balance_profile == ((1, 7), (2, 8))) -> (witness == True)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 4.967s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-78a0f4dd — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.9874)

- 명제: (num_extreme_elements == 5) ⟹ (witness 이다)
- 형식: `forall chi in scope: (num_extreme_elements == 5) -> (witness == True)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 4.942s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-d0c7255c — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.9833)

- 명제: (min_circuit_balance == 1) ⟹ (acyclic = 참)
- 형식: `forall chi in scope: (min_circuit_balance == 1) -> (acyclic == True)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 0.852s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-edec4bfa — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.9833)

- 명제: (min_circuit_balance == 1) ⟹ (convex_position = 거짓)
- 형식: `forall chi in scope: (min_circuit_balance == 1) -> (convex_position == False)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 0.617s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-d81b3b42 — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.9186)

- 명제: (num_singleton_circuits == 11) ⟹ (witness 이다)
- 형식: `forall chi in scope: (num_singleton_circuits == 11) -> (witness == True)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 4.946s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-fd3c718d — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.9033)

- 명제: (num_singleton_circuits >= 4) ⟹ (convex_position = 거짓)
- 형식: `forall chi in scope: (num_singleton_circuits >= 4) -> (convex_position == False)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 0.625s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-29b6208b — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.812)

- 명제: (singleton_degree_profile == ((0, 3), (3, 1), (4, 2))) ⟹ (witness 이다)
- 형식: `forall chi in scope: (singleton_degree_profile == ((0, 3), (3, 1), (4, 2))) -> (witness == True)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 5.023s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-a8f103ec — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.8073)

- 명제: (num_extreme_elements <= 4) ⟹ (convex_position = 거짓)
- 형식: `forall chi in scope: (num_extreme_elements <= 4) -> (convex_position == False)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 0.64s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-6a8089d0 — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.8073)

- 명제: (num_extreme_elements <= 4) ⟹ (num_singleton_circuits >= 4)
- 형식: `forall chi in scope: (num_extreme_elements <= 4) -> (num_singleton_circuits >= 4)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 1.045s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): EXTENDS — 3000개 검사, 전수=False

## cj-def73549 — `EXHAUSTED_ON_SCOPE` `[REPRESENTATIVE_DEPENDENT]` (score 1.79)

- 명제: (num_halving_cocircuits >= 4) ⟹ (convex_position = 거짓)
- 형식: `forall chi in scope: (num_halving_cocircuits >= 4) -> (convex_position == False)`
- 범위내: EXHAUSTED_ON_SCOPE — 11904개 검사, 전수=True, 0.603s (이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계))
- 확장 (n=7, r=3): FAILS_TO_EXTEND — 1개 검사, 전수=False
  - **확장 반례**: 깨진 부분 = convex_position = 거짓
  - chirotope: `{"0,1,2": 1, "0,1,3": 1, "0,1,4": 1, "0,1,5": 1, "0,1,6": 1, "0,2,3": 1, "0,2,4": 1, "0,2,5": 1, "0,2,6": 1, "0,3,4": 1, "0,3,5": 1, "0,3,6": 1, "0,4,5": 1, "0,4,6": 1, "0,5,6": 1, "1,2,3": 1, "1,2,4": 1, "1,2,5": 1, "1,2,6": 1, "1,3,4": 1, "1,3,5": 1, "1,3,6": 1, "1,4,5": 1, "1,4,6": 1, "1,5,6": 1, "2,3,4": 1, "2,3,5": 1, "2,3,6": 1, "2,4,5": 1, "2,4,6": 1, "2,5,6": 1, "3,4,5": 1, "3,4,6": 1, "3,5,6": 1, "4,5,6": 1}`

## cj-cc4d623f — `REFUTED` `[REPRESENTATIVE_DEPENDENT]` (score 1.8387)

- 명제: (num_singleton_circuits <= 10) ⟹ (num_halving_cocircuits <= 5)
- 형식: `forall chi in scope: (num_singleton_circuits <= 10) -> (num_halving_cocircuits <= 5)`
- 범위내: REFUTED — 1503개 검사, 전수=False, 0.131s (전건은 성립하는데 후건이 깨지는 대상을 찾았다)
  - **반례**: n=6 r=3, 깨진 부분 = num_halving_cocircuits <= 5
  - 반례 chirotope: `{"0,1,2": 1, "0,1,3": 1, "0,1,4": 1, "0,1,5": -1, "0,2,3": 1, "0,2,4": 1, "0,2,5": 1, "0,3,4": 1, "0,3,5": 1, "0,4,5": 1, "1,2,3": 1, "1,2,4": 1, "1,2,5": -1, "1,3,4": 1, "1,3,5": -1, "1,4,5": 1, "2,3,4": 1, "2,3,5": -1, "2,4,5": -1, "3,4,5": -1}`


### witness 표본 (6개 / 전체 6개)

- `c00001` n=6 r=3
  - signs: `+++++++++++++++++++-`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 3], [2, 12]], "cocircuit_balance_profile": [[0, 5], [1, 7], [2, 3]], "convex_position": false, "convex_tope_ratio": 0.0, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 0, "num_extreme_elements": 5, "num_halving_cocircuits": 3, "num_positive_circuits": 0, "num_singleton_circuits": 3, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 5], [3, 1]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": true}`
- `c00002` n=6 r=3
  - signs: `++++++++++++++++++--`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 4], [2, 11]], "cocircuit_balance_profile": [[0, 5], [1, 6], [2, 4]], "convex_position": false, "convex_tope_ratio": 0.0, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 0, "num_extreme_elements": 5, "num_halving_cocircuits": 4, "num_positive_circuits": 0, "num_singleton_circuits": 4, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 5], [4, 1]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": true}`
- `c00003` n=6 r=3
  - signs: `+++++++++++++++++---`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 7], [2, 8]], "cocircuit_balance_profile": [[0, 4], [1, 7], [2, 4]], "convex_position": false, "convex_tope_ratio": 0.0, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 0, "num_extreme_elements": 4, "num_halving_cocircuits": 4, "num_positive_circuits": 0, "num_singleton_circuits": 7, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 4], [3, 1], [4, 1]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": true}`
- `c00004` n=6 r=3
  - signs: `++++++++++++++++-+++`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 3], [2, 12]], "cocircuit_balance_profile": [[0, 5], [1, 7], [2, 3]], "convex_position": false, "convex_tope_ratio": 0.0, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 0, "num_extreme_elements": 5, "num_halving_cocircuits": 3, "num_positive_circuits": 0, "num_singleton_circuits": 3, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 5], [3, 1]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": true}`
- `c00005` n=6 r=3
  - signs: `++++++++++++++++--++`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 4], [2, 11]], "cocircuit_balance_profile": [[0, 5], [1, 6], [2, 4]], "convex_position": false, "convex_tope_ratio": 0.0, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 0, "num_extreme_elements": 5, "num_halving_cocircuits": 4, "num_positive_circuits": 0, "num_singleton_circuits": 4, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 5], [4, 1]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": true}`
- `c00006` n=6 r=3
  - signs: `++++++++++++++++---+`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 7], [2, 8]], "cocircuit_balance_profile": [[0, 4], [1, 7], [2, 4]], "convex_position": false, "convex_tope_ratio": 0.0, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 0, "num_extreme_elements": 4, "num_halving_cocircuits": 4, "num_positive_circuits": 0, "num_singleton_circuits": 7, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 4], [3, 1], [4, 1]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": true}`

### 근접 실패 표본 (convex 재배향이 가장 적은 non-witness) (6개 / 전체 6개)

- `c00000` n=6 r=3
  - signs: `++++++++++++++++++++`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[2, 15]], "cocircuit_balance_profile": [[0, 6], [1, 6], [2, 3]], "convex_position": true, "convex_tope_ratio": 0.0625, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 2, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 1, "num_extreme_elements": 6, "num_halving_cocircuits": 3, "num_positive_circuits": 0, "num_singleton_circuits": 0, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 6]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": false}`
- `c00007` n=6 r=3
  - signs: `++++++++++++++++----`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 8], [2, 7]], "cocircuit_balance_profile": [[0, 4], [1, 6], [2, 5]], "convex_position": false, "convex_tope_ratio": 0.0625, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 1, "num_extreme_elements": 4, "num_halving_cocircuits": 5, "num_positive_circuits": 0, "num_singleton_circuits": 8, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 4], [4, 2]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": false}`
- `c00018` n=6 r=3
  - signs: `+++++++++++++------+`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 8], [2, 7]], "cocircuit_balance_profile": [[0, 4], [1, 6], [2, 5]], "convex_position": false, "convex_tope_ratio": 0.0625, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 1, "num_extreme_elements": 4, "num_halving_cocircuits": 5, "num_positive_circuits": 0, "num_singleton_circuits": 8, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 4], [4, 2]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": false}`
- `c00020` n=6 r=3
  - signs: `++++++++++++-+--+---`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 10], [2, 5]], "cocircuit_balance_profile": [[0, 3], [1, 8], [2, 4]], "convex_position": false, "convex_tope_ratio": 0.0625, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 1, "num_extreme_elements": 3, "num_halving_cocircuits": 4, "num_positive_circuits": 0, "num_singleton_circuits": 10, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 3], [3, 2], [4, 1]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": false}`
- `c00027` n=6 r=3
  - signs: `+++++++++++----+--++`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 8], [2, 7]], "cocircuit_balance_profile": [[0, 4], [1, 6], [2, 5]], "convex_position": false, "convex_tope_ratio": 0.0625, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 1, "num_extreme_elements": 4, "num_halving_cocircuits": 5, "num_positive_circuits": 0, "num_singleton_circuits": 8, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 4], [4, 2]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": false}`
- `c00034` n=6 r=3
  - signs: `++++++++++-++++-++--`
  - 불변량: `{"acyclic": true, "circuit_balance_profile": [[1, 6], [2, 9]], "cocircuit_balance_profile": [[0, 4], [1, 8], [2, 3]], "convex_position": false, "convex_tope_ratio": 0.0625, "corank": 3, "max_circuit_balance": 2, "min_circuit_balance": 1, "min_cocircuit_balance": 0, "n": 6, "num_convex_reorientations": 1, "num_extreme_elements": 4, "num_halving_cocircuits": 3, "num_positive_circuits": 0, "num_singleton_circuits": 6, "num_tope_pairs": 16, "rank": 3, "reorientation_symmetry_order": 1, "singleton_degree_profile": [[0, 4], [3, 2]], "tope_fraction": 0.5, "totally_cyclic": false, "witness": false}`

## 당신에게 요청하는 것

1. 위 결과에서 **구조적 설명**을 찾아라. 어떤 양이 왜 그런 값을 갖는가?
2. 현재 어휘로 표현할 수 없는 성질이 보이면 **새 불변량을 코드로 제출하라.**
3. **반증 가능한 추측**을 제시하라. 특히 n 이나 rank 에 대해 확장되는 형태를.
4. d=5 (r=6, n=12) 로 가는 **탐색 전략**을 제안하라. 전수 열거는 불가능하므로,
   구조적 후보족(파라미터화된 구성) 또는 대칭/쌍대성을 이용한 축소가 필요하다.
5. 위 결과 중 **틀렸거나 오해를 부르는 것**이 있으면 지적하라.

### 원자(atom)와 추측(conjecture) 형식

    atom       = {"inv": "<불변량 이름>", "op": "==|!=|<=|>=|<|>", "value": <값>}
    conjecture = {"antecedent": [atom, ...],   // 논리곱. 빈 리스트면 항상
                  "consequent": atom,
                  "scope": {"n": <int>, "r": <int>},
                  "statement": "<한 문장>",
                  "grade": "CONJECTURE|PROVEN|...",
                  "rationale": "<왜 참일 것 같은가 / 어떤 반례를 시도했는가>"}

`witness` 는 예약된 불변량 이름이며 값은 true/false 다.


### 새 불변량 제출 형식

기존 어휘로 표현할 수 없는 성질이 필요하면 **직접 코드로 제출하라.** 어휘가
좁으면 정리도 좁아진다 — 새 어휘를 만드는 것이 이 단계에서 가장 가치 있는 일이다.

    {"name": "<식별자>", "description": "<한 줄>",
     "code": "def f(ch):\n    ...\n    return <값>",
     "why": "<이 양이 왜 McMullen 문제와 관련 있는가>"}

제한 문법 (위반하면 컴파일 단계에서 거부):
  - `import`, `while`, `try`, `class`, `lambda 외 함수정의`, `_` 로 시작하는 이름,
    화이트리스트 밖 전역 이름은 금지. 반복은 `for` + 유한 이터러블만.
  - 사용 가능한 전역: len min max sum sorted abs any all range enumerate zip
    tuple list set frozenset dict int bool str float map filter reversed
    divmod pow round combinations permutations product Counter gcd
  - `ch` 에서 쓸 수 있는 것: ch.n, ch.r, ch.signs, ch.chi(tuple),
    ch.circuit(S) -> {원소: ±1}, ch.cocircuit(H) -> {원소: ±1}, ch.reorient(flip),
    ch.is_valid(), ch.is_acyclic(), ch.is_totally_cyclic(), ch.is_convex_position()
  - 반환값은 bool / int / float / tuple 중 하나 (해시 가능해야 함).

자동 심사 항목: 전역성(예외 없음) · 결정성 · 비상수 · 비용 · 그리고
**원소 재명명 불변성**과 **재배향 불변성**을 실측해 기록한다. 재명명에 의존하는
양은 정리 후보에서 자동 강등되므로, 값을 만들 때 원소 이름에 의존하지 말 것
(예: 원소별 값은 반드시 정렬하거나 히스토그램으로 만들 것).


## 응답 형식 (반드시 지킬 것)

자유롭게 분석한 뒤, **마지막에** 아래 JSON 을 ```json 펜스로 감싸 딱 하나만 넣어라.
분석 산문은 JSON 밖에 쓰면 된다 — 파이프라인은 JSON 만 읽는다.

```json
{
  "analysis": "핵심 관찰 3~6줄 요약",
  "new_invariants": [ {"name":"", "description":"", "code":"", "why":""} ],
  "deprecate_invariants": [ {"name":"", "reason":""} ],
  "conjectures": [ {"antecedent":[], "consequent":{}, "scope":{}, "statement":"",
                    "grade":"", "rationale":""} ],
  "candidate_chirotopes": [ {"n":0, "r":0, "signs":"+-+...", "why":""} ],
  "next_experiment": {"n":0, "r":0, "om_class":"", "why":""},
  "assessment": {"proven":[], "verified":[], "conjecture":[], "speculation":[]},
  "open_questions": []
}
```

비어 있어도 되는 항목은 빈 배열로 두라. `candidate_chirotopes` 의 `signs` 는
`{0..n-1}` 의 r-부분집합을 **사전식**으로 나열했을 때의 부호 문자열이다
(길이 = C(n,r)). 구체적 구성을 제안할 자신이 있을 때만 채우면 된다.
