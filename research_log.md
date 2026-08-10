# research_log.md — 연구 기록 (append-only)

실험 한 줄 = 한 라운드. 실패한 시도도 반드시 남긴다 (같은 막다른 길을 다시 걷지 않기 위해).

- `run_0001` n=6 r=3 class=uniform 실현가능성=UNKNOWN | 후보 1500 (witness 1258) | 추측 40 → 반증 1, 전수확인 11 | commit d1b1c78f
- `probe` d=5 착수 실측: 후보당 비용 (12,6)=172ms | 무작위 witness 밀도 d=2 75.5% → d=3 1.6% → d=4 0/153,379 (95% UB 0.002%) | 기하급수 외삽 **반증**
- `sweep_d4_calib` (10,5) 무작위 153,379개 → witness 0건. 최선 근접실패 convex/tope = 4/256. **무작위 탐색 경로 폐기 결정**
- `climb_d4_calib` (10,5) 국소탐색 116,476 평가 5분 → f=1 도달 (무작위 최선 f=4). 방법 유효성 확인
- `climb_d5` (12,6) 국소탐색 개시 — 7워커, coord {3,4,5,6,8,10,14}, stall 3000, temp 0.5, seed 51201, 최대 6시간
- `climb_d4` (10,5) 보정 탐색 개시 — 4워커, coord {4,5,7,9}, stall 3000, temp 0.5, seed 41001, 최대 6시간 (답이 존재하는 범위에서 방법을 검증)
- `mutation_diag` **진단 전환**: d=4 f=1 에서 기저 부호 하나로 f=0 을 만드는 뒤집기가 252개 중 125개나 있으나 **전부 GP 위반**. 적법 23개 중 f 하강 0개. d=5 f=18 도 동일(813/924 하강, 적법 0). 벽은 목적함수 평탄면이 아니라 **OM 공리 경계**
- `mutation_depth` d=4 f=1 에서 적법 돌연변이만 따라 반경 4 전수(2,875 노드/305s) — f<1 없음. 엄격한 국소최소이므로 이동집합이 아니라 **출발점**이 문제
- `fasteval` circuit 균형이 ρ|_S 에만 의존한다는 항등식으로 f 재평가 172ms → **0.1ms** (om_core 와 완전 일치). witness ⟺ γ_S 반경-1 해밍 실린더의 하이퍼큐브 덮개
- `resp_0001` 외부 응답 수신·독립 검증 — f=17 정수배치의 VERIFIED 주장 7건이 om_core 로 **100% 재현**(924 비영, min|det| 457,533,801, acyclic 1024, survivor 17개 인덱스, GP 돌연변이 60개 {17:33,18:26,19:1}). 종전 최선 f=18 → **f=17**. witness 아님 → 상한 미증명. `responses/0001-d5project.md`
- `mutation_lab` 응답의 목적함수 3종 구현 + selftest 전항목 통과. f=17 상태는 z₁=17/17·Σκ₁=0 — 어떤 단일 적법 돌연변이도 survivor 를 죽이지 못함
- `envelope d5_f17` beam 8 로는 D_1^0=D_2^0=D_3^0=17 (반례 후보처럼 보였음) — **beam 이 원인이었다**. 전수(beam 없음) depth-2 에서 **D_2^0 = 16**, N_2=1, 경로 [(1,4,6,8,9,10),(1,3,6,8,9,10)], 두 중간 단계 모두 `is_valid()` 참. 교훈: envelope 의 beam 가지치기는 f 로 정렬하는데 하강 경로의 첫 수가 f 를 안 낮추므로 순위가 무의미하다 → **깊이별 전수가 기본이어야 한다**
- `d5_f16_abstract` f=16 추상 OM 확보 (`nearmiss_d5_f16_abstract.json`). **realizability=UNKNOWN — 정수 좌표 실현 전에는 ν(5) 상한에 대해 아무것도 증명하지 않는다.** 다음 단계는 응답의 determinant 실현(move_proposals #1·#3) 구현
- `cegis_calib` 덮개-CEGIS 캘리브레이션 — **(5,3) UNSAT** (하한 ν(2) ≥ 5 와 일치: "없다"를 말하는 능력 검증), (6,3) SAT 1라운드, (8,4) SAT 2라운드/0.1s. 인코딩 버그 1건 수정(재배향 인덱스 k → 원소 마스크 k<<1 누락 시 절이 무효)
- `cegis_d4_n10` **(10,5) SAT — d=4 보정 통과.** 38라운드/278절/750s, 게이지 2^10 축소. 독립 3경로 검증: om_core 전수 512개(acyclic 256, convex **0**) · mcmullen_evaluate(witness=True, implied_upper_bound=9) · reorientation_cover.evaluate_coverage(512/512 덮임). snapshot_id `10f2fae852f83720`, 기록 `cegis_witness_d4_n10.json`. **추상 OM 이므로 realizability 미확인 — ν(4) ≤ 9 를 증명하지 않는다.** 좌표탐색이 190만 회로 못 한 것을 완전 탐색이 12분에 해냈다는 것이 요점
- `cegis_d4_n9` (9,5) UNSAT 확인 시도 — 예산 초과로 결론 미도출(중단). 본 보정은 (10,5) SAT 로 달성됐으므로 후순위로 밀었다
- `HI-0001 감사` extended Lawrence rank-2 union class 반증 시험 — union GP 적법 328표본 위반 0, 재배향 교환 90회 불일치 0(둘 다 반증 안 됨). 그러나 **자명한 쌓기 실현이 union chirotope 를 12/12 재현 실패** → "layer 가 realizable 이므로 union 도 realizable" 에 즉각적 구성 근거 없음. `realizability` 를 `CLAIMED_UNVERIFIED` 로 강등, ledger HI-0001 을 INTEGRATED→TESTING·PROVEN→CONJECTURE. **채택은 함** — d=3 (8,4) 에서 후보 400개 중 witness 17개(4.25%, 무작위 실현가능 표집 1.6%보다 높음). 단 rank=d+1 이 짝수여야 하므로 **홀수 d 전용**(d=4 보정 불가) (DECISIONS 0034)
- `HI-0004` **Lawrence union 명시적 실현** — 층별 상수배는 Laplace 전개상 모든 항에 ∏c_i² 가 똑같이 붙어 원리상 무력(대조군 0/10). 원소별·블록별 계수 t^(i·λ_j) 를 쓰면 연속 짝짓기 항이 유일하게 압도 → **55/55 실현 성공**((7,4)~(12,6), λ=j+1, t∈{11,101}). 새 class `extended_lawrence_r2_realized` 는 후보마다 정수 좌표 증명서를 om_core 로 대조하고 성공분만 방출(fail-closed). (8,4) 200개 중 **realizable witness 8개**, (12,6) 60개 최선 f=40. 등급: 일반 명제는 NUMERICAL, 개별 후보는 증명서로 확정 (DECISIONS 0035)
- `layer_space` **layer 공간에 기울기가 있다** — (12,6) family f=40 에서 단일 이동 69개(인접전치 33 + 부호뒤집기 36) 전수: **7개가 하강, 최선 40→23 (한 수)**. 좌표공간(chamber 내부 f 상수, 기울기 없음)·OM 돌연변이 공간(하강 방향 전부 GP 위반)과 달리 **모든 상태가 실현 증명서를 유지**한다. 이 프로젝트에서 처음으로 쓸 수 있는 탐색 공간
- `bound_window` 기존 상한 U=2d+⌊(1+d)/2⌋ 기준 **개선 구간**: d=5 → n∈{12,13}, d=7 → {16,17,18}, d=9 → {20..23}, d=11 → {24..28}. **n=13 witness 만으로 ν(5) ≤ 12 로 개선**된다(Larman 목표 n=12 가 아니어도). witness 는 n 에 단조(부분집합이 convex position 을 물려받으므로)라 n=13 이 엄격히 쉽다 — family 무작위 표집 실측도 n=13 최선 f=17(16표본) vs n=12 f=40(60표본). **지금까지 n=12 만 본 것이 설계 오류**
- `cegis_d5_n12` (12,6) 덮개-CEGIS 중단 — 4라운드 f=66→56→45, 라운드당 11s→124s→1000s 로 8배씩 폭증. 6시간 예산 내 결론 불가로 판단. snapshot_id `d4f35548399c371d`. 방향을 layer 공간(상한 개선)으로 전환하며 보류. 재개하려면 대칭 파괴 절 + per-round 증대가 선행되어야 함
