# run_0001 보고서

- 범위: `{"backend": "backtracking", "exhaustive": false, "realizability": "UNKNOWN", "how": "generate_backtracking(n=6,r=3,max=1500)", "generator_stats": {"nodes": 9573, "emitted": 1500, "hit_candidate_cap": true, "hit_node_cap": false, "exhausted": false}, "realizability_note": "GP 공리만 만족하는 추상 OM 이라 실현가능성은 알 수 없다. 비실현 witness 는 OM 판본의 상한만 말할 뿐 ν(d) 에 대해서는 아무것도 증명하지 않는다.", "n": 6, "r": 3, "d": 2, "om_class": "uniform", "seed": 20260809}`
- 실현가능성: **UNKNOWN** — GP 공리만 만족하는 추상 OM 이라 실현가능성은 알 수 없다. 비실현 witness 는 OM 판본의 상한만 말할 뿐 ν(d) 에 대해서는 아무것도 증명하지 않는다.

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
