# 자율 토론 루프 연구 기록 — 2026-08-12

> **권한: `UNASSESSED_DIALOGUE_ONLY`.** 이 문서는 `math_dialogue.py` 우편함에 쌓인 대화 계층의
> 기록을 기계적으로 옮긴 것이다. **아무것도 증명되지 않았고 승격되지 않았다.**
> 각 항목의 등급(`ADVANCED`/`REFUTED`/`BLOCKED`/`LOW_YIELD`, `EXHAUSTED_ON_SCOPE` 등)은
> 원문 그대로이며, `om_core`·`falsify`·evidence DB 를 거친 것이 아니다.
> 검증된 실험 이력은 `research_log.md`, 승격된 근거는 evidence DB 를 보라.
>
> 내보내기 근거: `scripts/export_dialogue_research.py` (읽기 전용).
> 원본 DB `local_runs/math_dialogue/dialogue.sqlite3` SHA-256 `b77731774e7b14f4ed30d51b62c5e239c141aed1072da1eeabb39b94020f3c04`.
> 원문 응답 JSON 은 `local_runs/math_dialogue/responses/` 에 있고 gitignore 대상이다 —
> 이 문서가 저장소에 남는 유일한 기록이므로 원본 백업을 따로 보관할 것.

## 규모

- agent 6명 · topic 15개 · 메시지 57건
- 연구 사이클 10개 · research_event 37건 · 개념 증류 3건
- 메시지 종류: DIRECTION 14, CONJECTURE 12, COMPUTATIONAL_CLAIM 8, PROOF_SKETCH 6, CRITIQUE 6, QUESTION 3, COUNTEREXAMPLE_CANDIDATE 3, COMPUTATION_RESULT 3, EXPERIMENT_PLAN 1, COMPUTATION_REQUEST 1

| agent | 역할 | 마지막 관측 |
|---|---|---|
| `claude-compute` | 결정론적 계산 실험 설계·실행 | 2026-08-12T01:42:09+00:00 |
| `codex-prover` | 증명 구성·계산 의무 발행 | 2026-08-12T01:42:50+00:00 |
| `experimentalist` | 결정론적 계산·유한 검증·재현성 | 2026-08-12T06:56:12+00:00 |
| `falsifier` | 최소 반례 탐색·숨은 가정·논리 감사 | 2026-08-12T06:56:14+00:00 |
| `prover` | 제시된 방향을 엄밀한 보조정리와 증명 사슬로 구성 | 2026-08-12T01:31:34+00:00 |
| `strategist` | 정식화·창발 분야 탐사·라우팅·종합 | 2026-08-12T06:50:54+00:00 |

## 연구 사이클 — 가설에서 종합까지

각 사이클은 `창발 탐사` 한 바퀴다. event 의 `outcome` 은 대화 계층의 자체 분류다.

### `ER-20260812-022948-187f4e` — SAT·CSP·모델검사

- **HYPOTHESIS / ADVANCED** — strategist
  - 요약: rank-6, n=12 witness 탐색을 8개 circuit obstruction kernel의 exact-cover 존재 문제로 축소했다.
  - 접근: 각 7-support circuit이 2048개 재배향 중 정확히 256개를 막는다는 균일 용량을 이용해, 8개 최소 덮개를 pairwise-disjoint exact cover로 SAT 인코딩하고 이후 GP extension SAT를 분리한다.
  - 재사용 가능한 단서:
    - 모든 rank-6 n=12 circuit bad mask의 크기는 256이다.
    - 8-circuit cover는 용량상 정확분할이어야 하며 support 쌍의 교집합 크기가 5 이하이면 불가능하다.
    - support당 circuit sign class 하나만 허용해야 Hamming-code형 가짜 exact cover를 배제할 수 있다.
  - 다음 질문:
    - support 중복 금지를 포함한 Stage A exact-cover SAT는 UNSAT인가?
    - Stage A 해가 존재하면 선택 circuit sign 제약이 GP chirotope로 확장 가능한가?
    - 알려진 작은 witness의 최소 circuit-cover 수는 얼마인가?
- **COMPUTATION / ADVANCED** — experimentalist
  - 요약: 8개 circuit mask의 Stage A exact cover가 존재함을 찾았고 overlap 판정을 유한 전수로 확인했다.
  - 접근: n=12의 모든 support/sign class mask를 직접 구성하고 overlap 보조정리를 대조한 뒤, 8-support star 두 gauge 대표에서 결정론적 exact-cover DFS를 수행했다.
  - 재사용 가능한 단서:
    - 8개 7-support의 pairwise intersection>=6 조건은 8원소 집합의 7-subset star를 허용한다.
    - support-level exact cover SAT은 GP-적법 OM extension을 의미하지 않는다.
    - 두 circuit masks의 disjointness는 overlap antipodal distance가 3 이상인지로 판정할 수 있다.
  - 다음 질문:
    - 명시한 Stage A sign 해가 rank-6 GP 제약으로 확장되는가?
    - 8-clique support family를 두 gauge star 대표로 줄이는 symmetry가 완전한가?
    - GP 확장이 SAT이면 완성 OM의 최소 circuit cover가 정확히 8인가?
- **CRITIQUE / ADVANCED** — falsifier
  - 요약: 첫 8-mask exact cover는 circuit별 antipodal gauge를 보정하면 28 basis signs를 강제하지만, 그 n=8 rank-6 restriction이 GP 위반이라 확장 불가능하다.
  - 접근: 공유 basis의 sign 일관성을 circuit orientation 변수 z_S에 대한 부호 방정식으로 풀고, 유도된 완전한 C(8,6) sign table을 om_core Chirotope.is_valid로 검사했다.
  - 재사용 가능한 단서:
    - antipodal circuit sign class를 chirotope literal로 옮길 때 support별 전역부호 변수를 반드시 둔다
    - 7-subset의 크기 8 pairwise-intersection-6 clique는 star가 아니라 고정 8-set의 top이다
    - 전역 n=12 GP 전에 top 내부 n=8 restriction GP가 값싼 완전 필터다
  - 다음 질문:
    - 한 top의 모든 exact-cover sign 해가 local rank-6 GP에서 탈락하는가
    - local GP를 통과하는 Stage A 해가 있다면 n=12 uniform OM으로 확장되는가
- **COMPUTATION / ADVANCED** — experimentalist
  - 요약: canonical 8-support top의 Stage A 해 240개를 완전 열거했고 모두 local rank-6 GP에서 탈락했다.
  - 접근: 첫 circuit mask를 cube translation으로 고정하고 exact-cover DFS를 완주한 뒤 support orientation gauge를 복원하여 n=8,r=6 Chirotope.is_valid로 전수 필터링했다.
  - 재사용 가능한 단서:
    - circuit antipodal class를 basis literals로 옮길 때 support별 orientation gauge z_S가 필수다.
    - global n=12 GP보다 8원소 restriction의 local GP 검사가 훨씬 싼 완전 필터다.
    - support-level exact partitions 240개가 모두 local GP 위반이었다.
  - 다음 질문:
    - 8개의 7-subset pairwise-6-intersecting family가 반드시 top임을 짧게 증명할 수 있는가?
    - 첫 mask canonical 고정이 chirotope orientation gauge까지 누락 없이 모든 해를 대표하는가?
    - 240개 GP 실패를 압축하는 소수의 공통 GP obstruction orbit가 있는가?
- **SYNTHESIS / ADVANCED** — falsifier
  - 요약: 8-support family의 top 분류, relabel/cube-translation canonicalization, gamma convention을 증명하고 240해 전수를 독립 재현해 모두 local GP 위반임을 확인했다.
  - 접근: 용량과 Johnson-clique 분류를 손증명하고, gauge action을 추적한 뒤 mask DFS와 circuit-orientation 복원 및 n=8 rank-6 GP 검사를 독립 재구현했다.
  - 재사용 가능한 단서:
    - 동일 크기 cylinder 8개가 cube를 덮으면 반드시 exact partition이므로 support Johnson clique로 축약된다
    - 크기 8의 7-subset pairwise-6 clique는 star가 아니라 8-set top이다
    - circuit별 antipodal orientation을 복원한 뒤 작은 ground-set restriction GP를 먼저 검사하면 전역 extension을 피할 수 있다
  - 다음 질문:
    - 240개 local GP 실패를 소수의 obstruction orbit로 압축할 수 있는가
    - 최소 circuit cover 9를 달성하는 GP-적법 rank-6 OM이 존재하는가
    - 재현 가능한 certificate와 독립 verifier의 최소 형식은 무엇인가
- **SYNTHESIS / ADVANCED** — strategist
  - 요약: rank-6, n=12 uniform OM의 circuit obstruction cover에는 적어도 9개 circuit이 필요한다는 bounded-kernel 하한을 조합 환원과 240개 canonical case 전수검사로 종합했다.
  - 접근: 8개 mask가 exact partition이어야 함을 보이고 support family를 하나의 8-set top으로 분류·정규화한 뒤, 240개 canonical exact cover가 모두 local rank-6 GP를 위반한다는 두 독립 열거를 결합했다.
  - 재사용 가능한 단서:
    - 8-circuit cover는 균일 mask 용량 때문에 exact partition 문제로 축소된다.
    - pairwise intersection>=6인 8개의 7-support는 n=12에서 하나의 8-set top으로 환원된다.
    - canonical exact cover 240개는 shared-basis sign에는 일관되지만 모두 8원소 rank-6 GP restriction에서 탈락한다.
    - 결과의 프로젝트 승격에는 후보별 첫 GP 위반을 담은 영속 certificate가 남아 있다.
  - 다음 질문:
    - 240개 GP 실패를 소수의 obstruction orbit로 압축할 수 있는가?
    - 독립 replay certificate를 만들면 8-cover 불가능성을 짧은 보조정리로 승격할 수 있는가?
    - 9개의 circuit obstruction mask는 Stage A exact cover 또는 GP-consistent cover를 만들 수 있는가?

### `ER-20260812-031941-f5510e` — 군 작용·표현론

- **HYPOTHESIS / ADVANCED** — strategist
  - 요약: 240개 canonical 8-circuit exact partitions를 하나의 S_8 orbit이자 labeled F_2^3 구조 240개로 해석하는 대칭 압축 가설을 세웠다.
  - 접근: 240=8!/168과 |GL(3,2)|=168의 일치에서 출발해, relabel 후 first-mask translation-normalization을 포함한 induced S_8 action, Coxeter relation, orbit 및 stabilizer 검사를 설계했다.
  - 재사용 가능한 단서:
    - 240=8*30은 zero 선택 8개와 7 nonzero points의 Fano-plane labeling 30개로 해석될 수 있다.
    - gauge-fixed slice의 대칭은 relabeling 뒤 retranslation을 포함해야 하며 generator relations로 합성 폐쇄성을 감사해야 한다.
    - 단일 orbit이면 GP 부적법성 certificate를 한 대표와 orbit transport로 압축할 수 있다.
    - bad-mask subsets에 먼저 작용하면 sorted-support gamma parity convention을 추측할 필요가 없다.
  - 다음 질문:
    - 240개 해의 normalized S_8 orbit size multiset은 정말 [240]인가?
    - 대표 stabilizer는 order 168이고 Fano plane을 보존하는 GL(3,2)인가?
    - 한 대표의 GP 위반을 전체 orbit에 운반해 240개 부적법성을 완전히 인증할 수 있는가?
- **CRITIQUE / REFUTED** — experimentalist
  - 요약: canonical first mask normalization에 residual Z2 ambiguity가 있어 제안된 S8 action이 well-defined하지 않음을 반증했다.
  - 접근: 2048 cube translations를 전수해 기준 mask stabilizer를 구하고, canonical Stage A 해에 대한 distinct normalized images를 비교했다.
  - 재사용 가능한 단서:
    - bad mask는 support 밖 translation뿐 아니라 support 전체 antipodal translation에도 불변이다.
    - gauge slice의 대표 선택이 유일하지 않으면 identity조차 다가함수가 되어 군 작용이 아니다.
    - residual Z2를 quotient한 뒤에만 Coxeter relation을 검사해야 한다.
  - 다음 질문:
    - residual antipodal translation은 240해에서 fixed-point-free involution인가?
    - 120쌍 quotient 위 relabeling action은 well-defined한가?
    - 수정된 action의 orbit와 stabilizer는 무엇인가?
- **CRITIQUE / ADVANCED** — falsifier
  - 요약: normalization의 residual Z2가 240해를 fixed-point-free 120쌍으로 만들며, quotient에서만 S8 action이 정준적이고 GP 실패가 보존됨을 확인했다.
  - 접근: first-mask translation stabilizer를 outside-R kernel과 a=127로 분해하고, 240 solution lookup에서 a의 cycle 구조를 전수한 뒤 ground reorientation의 GP 불변성을 직접 추적했다.
  - 재사용 가능한 단서:
    - support별 circuit antipodal gauge와 전 ground-set reorientation은 구분해야 한다
    - 비유일 normalization은 stabilizer가 자명 kernel과 자유로운 residual action으로 분해되면 quotient에서 정준화할 수 있다
    - reorientation은 GP validity와 invalidity를 모두 보존하므로 failure certificate orbit 축소에 안전하다
  - 다음 질문:
    - 120 quotient 위 S8 orbit sizes와 stabilizer orders는 무엇인가
    - quotient stabilizer가 알려진 336차 부분군과 동형인가
    - 120 대표 GP 위반을 더 적은 obstruction orbit로 압축할 수 있는가
- **PIVOT / ADVANCED** — strategist
  - 요약: 비정당화된 240-set S_8 action을 폐기하고 residual reorientation involution으로 나눈 120 quotient의 well-defined S_8 action으로 탐사를 수정했다.
  - 접근: 120 quotient에서 adjacent transposition의 Coxeter relations, orbit decomposition, stabilizer를 계산하고 single orbit이면 order-336 sharply 3-transitive PGL(2,7) 후보를 판별하도록 단계화했다.
  - 재사용 가능한 단서:
    - gauge-fixed slice의 normalization 모호성은 자유 residual reorientation으로 quotient해야 제거된다.
    - 120이 단일 S_8 orbit이면 stabilizer order는 336이며 8점 위 PGL(2,7) 작용이 구체적 판별 후보다.
    - GP certificate는 quotient orbit마다 하나의 위반과 transporter words, residual reorientation으로 압축할 수 있다.
    - 240-set의 GL(3,2) stabilizer-168 가설은 폐기됐다.
  - 다음 질문:
    - 120 quotient의 S_8 orbit size multiset은 무엇인가?
    - single orbit이면 stabilizer는 sharply 3-transitive하며 PGL(2,7)에 conjugate한가?
    - orbit transporter와 a-reorientation만으로 240개 GP 실패를 독립 replay할 수 있는가?
- **COMPUTATION / ADVANCED** — experimentalist
  - 요약: 120-class quotient에서 S8 작용이 well-defined하고 transitive이며 stabilizer 336이 sharply 3-transitive임을 완전 계산했다.
  - 접근: 240 exact-cover 해를 residual involution으로 quotient하고 adjacent transposition 작용의 closure·Coxeter relations·orbit·stabilizer를 전수했다.
  - 재사용 가능한 단서:
    - residual Z2 quotient가 normalization의 다가성을 제거한다.
    - Q의 S8 orbit은 하나이고 stabilizer order는 336이다.
    - stabilizer의 8점 작용은 sharply 3-transitive다.
  - 다음 질문:
    - stabilizer는 표준 PGL(2,7)과 S8-conjugate인가?
    - 단일 GP 위반을 군 작용으로 240해 전부에 replay할 수 있는가?
- **CRITIQUE / ADVANCED** — falsifier
  - 요약: quotient-level S8 결과는 논리 감사를 통과했지만 단일 GP 위반의 240-lift 운반에는 state-dependent reorientation cocycle가 추가로 필요하다.
  - 접근: Coxeter presentation과 orbit-stabilizer의 충분성을 분리해 확인하고, quotient action에서 실제 sign-vector lift로 올라갈 때 잃는 gauge 및 residual 정보를 추적했다.
  - 재사용 가능한 단서:
    - permutation/action pair BFS의 크기는 action faithfulness 자체를 보이지 않는다.
    - sharp 3-transitivity는 336개의 서로 다른 ordered-triple image로 직접 인증된다.
    - quotient certificate를 representative certificate로 올리려면 reorientation cocycle와 residual bit가 필요하다.
  - 다음 질문:
    - stabilizer와 표준 PGL(2,7) 사이의 명시적 conjugating bijection은 무엇인가?
    - 120×7 lift cocycle가 Coxeter loop들에서 trivial holonomy를 갖는가?
    - 운반된 단일 GP 위반이 240개 저장 sign vector 모두와 직접 일치하는가?

### `ER-20260812-041939-213de3` — 정보이론·부호이론

- **HYPOTHESIS / ADVANCED** — strategist
  - 요약: 120 exact-cover quotient를 P^1(F_7)의 Paley tournament switching class orbit로 식별하고, dual triple invariant로 240개 GP 실패를 cocycle 없이 압축하는 가설을 세웠다.
  - 접근: rank-6,n=8 signs를 dual rank-2 pair signs와 switching-invariant triple signs로 바꾸고, 표준 Paley 모델의 8! stabilizer 및 모든 4-subset GP pattern을 직접 열거했다.
  - 재사용 가능한 단서:
    - dual triple product τ_ijk=p_ij p_ik p_jk는 ground reorientation을 global sign 하나로만 기억한다.
    - 표준 Paley switching class의 projective stabilizer는 336이고 labeled orbit size는 120이다.
    - rank-2 GP 위반은 한 4-set의 triple pattern (+,-,+,-) 또는 그 음수와 동치다.
    - Paley 대표에는 그런 forbidden quadruple이 정확히 28개 있어 잠재적 단일-orbit certificate가 된다.
  - 다음 질문:
    - exact-cover root의 normalized dual triple signature가 Paley signature와 relabel-equivalent한가?
    - 240 candidates 모두 forbidden quadruple 수가 정확히 28인가?
    - switching invariant만으로 원 rank-6 GP failure certificate를 완전히 replay할 수 있는가?
- **COMPUTATION / ADVANCED** — experimentalist
  - 요약: 240 exact-partition lifts의 dual triple signatures가 8점 Paley switching class의 120 labeled copies와 정확히 일치함을 전수 확인했다.
  - 접근: Stage A 240개를 재생해 28 basis signs, dual pair signs, normalized triple keys를 복원하고 Paley signature의 8! projective orbit과 set equality 및 quadruple obstruction histogram을 비교했다.
  - 재사용 가능한 단서:
    - 240 lift가 120 triple keys에 정확히 multiplicity 2로 압축된다.
    - Paley orbit과 candidate orbit의 exact key equality가 성립한다.
    - 모든 candidate에는 정확히 28개의 dual GP forbidden quadruple이 있다.
  - 다음 질문:
    - dual parity convention과 primal rank-6 GP 대응을 독립 감사할 수 있는가?
    - Paley root와 한 forbidden quadruple만으로 최소 영속 replay certificate를 만들 수 있는가?
- **CRITIQUE / ADVANCED** — falsifier
  - 요약: normalized triangle signature가 switching/projective class의 완전 불변량임을 보여 Paley root GP 위반이 240 lifts 전체에 충분하며 lift cocycle가 불필요함을 확인했다.
  - 접근: dual parity를 inversion count로 유도하고, primal reorientation의 tau 변환식과 triangle signatures의 switching-completeness를 증명한 뒤 rank-6 GP 세 항과 dual pair products를 직접 대조했다.
  - 재사용 가능한 단서:
    - primal reorientation은 tau를 R=product rho만큼 global flip하므로 projective normalization 뒤 불변이다.
    - complete graph의 모든 triangle products는 edge switching class를 완전히 결정한다.
    - switching-invariant 결론 운반에는 representative-level cocycle가 필요 없다.
  - 다음 질문:
    - 120 candidate keys와 Paley orbit의 persistent set-equality certificate를 어떤 최소 형식으로 저장할 것인가?
    - Paley edge 하나를 flip한 음성 대조에서 orbit 및 obstruction histogram은 어떻게 변하는가?
- **SYNTHESIS / ADVANCED** — strategist
  - 요약: 8-circuit exact-partition의 240 lifts를 Paley tournament switching class의 120 labeled copies로 식별하고 한 projective orbit의 forbidden quadruple로 GP 부적법성을 압축했다.
  - 접근: rank-6 signs를 dual rank-2 pair signs와 switching-invariant triple signatures로 변환해 Paley 8! orbit과 exact set equality를 확인하고, alternating four-triple pattern을 rank-6 GP 위반으로 대수적으로 되돌렸다.
  - 재사용 가능한 단서:
    - dual normalized triple signature는 reorientation/projective switching class의 완전 불변량이다.
    - canonical 240 solutions는 Paley orbit의 120 keys에 정확히 multiplicity 2로 놓인다.
    - Paley class의 각 lift는 정확히 28개의 forbidden quadruples를 갖는다.
    - GP invalidity-only certificate에는 lift cocycle가 필요 없고 Paley root와 orbit equality면 충분하다.
  - 다음 질문:
    - Paley root와 orbit equality를 독립 replay하는 최소 영속 artifact를 만들 수 있는가?
    - 이 switching-invariant 압축이 9-circuit near-cover kernel에도 유사한 코드 구조를 드러내는가?
    - Paley obstruction을 유한 열거 없이 직접 exact-partition 분류에서 유도할 수 있는가?

### `ER-20260812-045004-508dbc` — 극값 조합론

- **HYPOTHESIS / ADVANCED** — strategist
  - 요약: 9-circuit cover를 projective radius-one balls의 극값 덮개로 바꾸고, 두 bad sets의 완전한 교집합 표와 pair-budget 항등식을 유도했다.
  - 접근: 7-support 두 개의 overlap에서 bad restriction을 중심 부호와 최대 한 예외 좌표로 유일 표현해 compatible marker를 세고, cover multiplicity의 1차·2차 모멘트를 비교했다.
  - 재사용 가능한 단서:
    - 두 circuit bad sets의 교집합 크기는 (support overlap t, projective center distance h)만으로 결정된다.
    - 9-cover의 pair budget은 P=256+sum binom(m-1,2)이며 최소 256이다.
    - P=256 stratum은 triple collision이 전혀 없는 cover와 정확히 동치여서 가장 싼 첫 탐색층이다.
    - pair intersection이 모두 8의 배수라 최소층 실패 뒤 다음 가능한 budget은 264다.
  - 다음 질문:
    - P=256인 9-mask exact cover가 존재하는가?
    - 존재하지 않으면 9-cover의 최소 pair-intersection budget은 얼마인가?
    - 최소-budget Stage A cover 중 shared-basis sign consistency와 GP를 통과하는 것이 있는가?
- **FAILURE / REFUTED** — experimentalist
  - 요약: P=256인 9-cover가 없다는 H_ext를 canonical 8-partition에 ninth mask를 추가한 명시 구성으로 반박했다.
  - 접근: 기존 8-mask exact partition을 n=12 cube에 lift하고 새로운 support의 all-plus mask를 추가해 mask sizes, union, 모든 pair/triple intersections를 직접 계산했다.
  - 재사용 가능한 단서:
    - P=256 stratum에는 exact 8-partition의 redundant augmentation이 자동으로 존재한다.
    - 수정 탐색에는 각 mask의 private point가 하나 이상이라는 제약이 필요하다.
    - 명시 반례의 ninth pair intersections는 48,48,48,48,16,16,32,0이다.
  - 다음 질문:
    - inclusion-minimal 9-cover에서도 P=256이 가능한가?
    - shared-basis sign consistency를 동시에 강제하면 P=256 후보가 남는가?
- **PIVOT / ADVANCED** — strategist
  - 요약: trivial ninth-mask augmentation이 H_ext를 반박함을 수용하고, inclusion-minimal P=256 cover로 명제를 수정했다.
  - 접근: P=256에서 triple intersections가 없다는 항등을 mask별로 국소화해 private-point 수를 weighted degree로 표현하고, positive pair 최소값 16에서 Johnson-edge 밀도 조건을 도출했다.
  - 재사용 가능한 단서:
    - P=256에서는 mask i의 private-point 수가 정확히 256에서 pair-intersection weighted degree를 뺀 값이다.
    - inclusion-minimal 조건은 모든 weighted degree가 248 이하라는 정수 조건과 동치다.
    - P=256인 9-family는 적어도 20개의 disjoint-mask pair를 가지므로 supports가 J(12,7)에서 최소 20 edges를 유도한다.
    - 8-partition에 redundant mask를 더하는 반례는 새 vertex weighted degree 256으로 정확히 제거된다.
  - 다음 질문:
    - inclusion-minimal P=256 9-cover가 존재하는가?
    - J(12,7)에서 9 vertices와 최소 20 edges를 갖는 support orbit은 몇 개인가?
    - 그 support orbits 중 h=3 zero-edge constraints와 center signs가 양립하는 것은 무엇인가?
- **COMPUTATION / REFUTED** — experimentalist
  - 요약: 서로 다른 supports를 가진 inclusion-minimal P=256의 9-mask Stage A cover를 찾아 H_min을 반박했다.
  - 접근: canonical 8-partition에서 한 mask를 제거하고, 제거 mask와 160점 교차하는 adjacent-support 후보 56개 중 두 개로 대체하여 exact union, pair/triple budget, private counts를 검사했다.
  - 재사용 가능한 단서:
    - 명시 새 supports는 (2,3,4,5,6,7,8)과 (1,3,4,5,6,7,8)이다.
    - private counts는 240,240,224,224,224,224,224,96,96이다.
    - H_min 반례는 zero support-adjacency pairs 23개와 P=256을 동시에 만족한다.
  - 다음 질문:
    - 이 9-family의 shared-basis sign equations는 일관적인가?
    - 일관적이면 partial rank-6 signs를 GP-valid chirotope로 완성할 수 있는가?
- **SYNTHESIS / ADVANCED** — strategist
  - 요약: 두 극값 부재 가설을 반례로 폐기했지만, inclusion-minimal 9-cover 반례가 일곱 canonical top circuits만으로 이미 Paley GP 위반을 강제함을 확인했다.
  - 접근: pair-budget과 private-point 조건을 종합하고, 명시 9-family의 support-gauge equations를 풀어 고정된 partial basis signs에서 직접 GP 위반을 추출했다.
  - 재사용 가능한 단서:
    - 8원소 top의 8 circuits 중 임의의 7개가 그 restriction의 모든 rank-6 basis signs를 결정한다.
    - 8-partition cell splitting은 Stage A minimal cover를 만들지만 inherited seven-top Paley core 때문에 GP를 통과하지 못한다.
    - 9-cover의 pair budget과 mask별 private count는 weighted intersection graph의 1차·2차 모멘트로 정확히 읽힌다.
    - 다음 탐색은 shared-basis consistency 뒤가 아니라 partial GP relation이 완전히 지정되는 순간 online pruning해야 한다.
  - 다음 질문:
    - Paley seven-top core를 피하는 inclusion-minimal 9-mask Stage A cover가 존재하는가?
    - online partial-GP pruning을 넣으면 9-mask support/center 탐색이 전수 가능한 크기로 줄어드는가?
    - 그 필터를 통과한 partial signs가 full rank-6 OM 및 realizable OM으로 완성되는가?

### `ER-20260812-052023-95ed6c` — 가환대수

- **SYNTHESIS / ADVANCED** — strategist
  - 요약: 8-cover 용량 환원을 Boolean coordinate algebra의 trace-rigid 직교 idempotent 분해로, 240개 GP 실패를 cover ideal과 GP ideal의 빈 교차로 번역했다.
  - 접근: bad-mask characteristic functions를 Boolean ring의 idempotents로 보고 trace를 사용했으며, GP forbidden pattern의 polynomial indicator를 명시해 유한점 ideal과 Nullstellensatz certificate 관점으로 옮겼다.
  - 재사용 가능한 단서:
    - 동일 크기 obstruction masks가 용량 하한을 정확히 달성하면 단위원의 직교 idempotent 분해가 된다.
    - 유한 cover 후보 전수는 zero-dimensional Boolean quotient의 length로 읽을 수 있다.
    - 모든 finite candidates의 GP 탈락은 cover ideal과 GP ideal의 합이 unit ideal이라는 certificate 목표로 압축할 수 있다.
    - signed Hamming balls는 simplicial complex가 아니므로 Stanley--Reisner 번역에는 affine complementary-literal relations가 필요하다.
  - 다음 질문:
    - I_cover+I_GP=(1)의 낮은 차수 Nullstellensatz certificate가 존재하는가?
    - cover quotient의 Gröbner standard monomials가 canonical 240 solutions와 직접 대응하는가?
    - polarized squarefree model의 Betti 자료가 support top과 GP obstruction을 분리해 보여 주는가?

### `ER-20260812-053029-eaae43` — SAT·CSP·모델검사

- **HYPOTHESIS / ADVANCED** — strategist
  - 요약: 9-circuit GP-consistent cover의 존재를 full chirotope signs와 support selectors 위의 exact bounded CEGIS로 정식화했다.
  - 접근: circuit center를 별도 열거하지 않고 global basis signs에서 유도하며, GP 위반 relation과 uncovered reorientation만 lazy clause로 추가하는 이중 counterexample loop를 설계했다.
  - 재사용 가능한 단서:
    - support selector와 global chirotope signs를 직접 연결하면 shared-basis consistency가 자동으로 강제된다.
    - 한 reorientation의 cover 의무는 선택 support와 7-literal unbalanced cardinality predicate의 OR 하나다.
    - 선택 circuit 하나를 fixed support/all-positive signs로 정규화하는 relabel+reorientation symmetry가 있다.
    - k=8 Stage A SAT/GP UNSAT 쌍은 k=9 solver의 강한 양성·음성 대조군이다.
  - 다음 질문:
    - GP-valid rank-6,n=12 chirotope에 9-circuit cover가 존재하는가?
    - SAT이면 해당 abstract witness는 realizable한가?
    - UNSAT이면 proof artifact를 작은 forbidden partial-GP cores로 압축할 수 있는가?
- **COMPUTATION / BLOCKED** — experimentalist
  - 요약: exact-nine CEGIS 정식화를 감사하고, 명시 9-mask candidate가 28개의 완전 지정 GP 위반으로 즉시 제거됨을 확인했다.
  - 접근: 변수·관계 수와 reorientation 식을 점검한 뒤 shared-basis gauge equations를 풀고 fixed partial signs에서 평가 가능한 GP relations를 직접 열거했다.
  - 재사용 가능한 단서:
    - 직전 9-family는 39 basis signs를 일관되게 고정하지만 GP 위반 28개를 이미 포함한다.
    - 첫 위반은 Y=(0,1,2,5), quadruple=(3,4,6,7), products=(+,-,+)이다.
    - selector-level shared-basis/partial-GP propagation은 큰 CEGIS 전에 적용 가능하다.
  - 다음 질문:
    - z3 환경에서 k=8 양·음성 controls가 모두 통과하는가?
    - k=9 exact model은 SAT인가 UNSAT인가?
- **PIVOT / ADVANCED** — strategist
  - 요약: z3 부재로 full k=9 판정이 멈춘 사이, P=256 cover가 항상 8-partition의 seven-mask subcore를 포함하는지 묻는 dependency-free split-completion 가설을 세웠다.
  - 접근: 명시 cell-split cover의 구조를 추출해 9-family당 36개 seven-subfamily complement lookup으로 반증 가능한 정규형 명제로 바꿨다.
  - 재사용 가능한 단서:
    - P=256 9-cover가 seven-mask exact-partition core를 포함하면 그 일곱 circuit만으로 Paley GP 위반이 이미 강제된다.
    - split-completion 여부는 9-family당 36개 bitset complement와 50,688-mask lookup만으로 판정된다.
    - H_split 반례는 full GP solver가 없어도 얻을 수 있는 비-Paley Stage A seed다.
    - P=256 층이 제거될 경우 pair-intersection quantization 때문에 다음 탐색 budget은 264다.
  - 다음 질문:
    - inclusion-minimal P=256 9-cover 중 split completion이 없는 것이 존재하는가?
    - 두-mask replacement 56-candidate family에서는 H_split이 전수 성립하는가?
    - H_split이 참이라면 이를 support/center intersection table만으로 증명할 수 있는가?
- **COMPUTATION / ADVANCED** — falsifier
  - 요약: 56개 adjacent replacement 후보의 1,540쌍을 전수해 196개 inclusion-minimal P=256 cover 모두가 정확히 하나의 split completion을 가짐을 확인했다.
  - 접근: canonical 8-partition과 50,688 circuit masks를 exact 2048-bit integers로 재생하고 union, pair budget, private counts 및 36개 seven-subfamily complement lookup을 전수했다.
  - 재사용 가능한 단서:
    - 28 adjacent supports마다 removed mask와 160점 교차하는 projective center가 정확히 2개다.
    - 제한 construction의 196 valid covers는 split completion multiplicity가 모두 정확히 1이다.
    - non-split 반례는 positive-intersection graph의 vertex-cover number가 3 이상이면 즉시 인증된다.
  - 다음 질문:
    - 일반 inclusion-minimal P=256 cover 중 intersection graph의 maximum independent set이 6 이하인 예가 존재하는가?
    - vertex cover가 2인 P=256 cover에서 seven-mask complement가 circuit mask가 아닌 예가 존재하는가?
- **ATTEMPT / ADVANCED** — strategist
  - 요약: 제한 replacement family의 H_split 196/196 결과를 보존하고, 일반 non-split P=256 cover 탐색을 pair-weight·triple-conflict 조건으로 축약했다.
  - 접근: triple-free 포함배제와 mask별 weighted degree를 이용해 union/private 조건을 제거하고, positive-intersection graph의 vertex-cover number에 따라 반례 탐색을 두 strata로 분리했다.
  - 재사용 가능한 단서:
    - 9개 size-256 masks가 triple-free이고 pair budget 256이면 union=2048은 자동이다.
    - 같은 조건에서 private count는 정확히 256-weighted degree다.
    - positive-intersection graph의 vertex-cover number가 3 이상이면 H_split의 즉시 반례다.
    - 일반 non-split 탐색은 z3 없이 exact bitset DFS로 수행할 수 있다.
  - 다음 질문:
    - τ(G_+)≥3인 inclusion-minimal P=256 9-cover가 존재하는가?
    - 그런 cover가 없으면 τ≤2이지만 complement mask가 없는 stratum-B 반례가 존재하는가?
    - non-split Stage A cover가 shared-basis consistency와 partial GP를 통과하는가?
- **COMPUTATION / ADVANCED** — experimentalist
  - 요약: canonical exact partition의 임의 세 cells 안에 포함되는 universe masks는 그 원래 세 masks뿐임을 전수 확인해 3-cell/4-mask K4 replacement를 배제했다.
  - 접근: 50,688 exact masks를 생성하고 세 removed cells의 56 choices마다 retained five-cell union과 disjoint한 masks를 필터링했다.
  - 재사용 가능한 단서:
    - 모든 56 removed triples에서 contained mask count는 정확히 3이다.
    - canonical partition의 3-cell union은 다른 circuit mask를 포함하지 않는다.
    - stratum-A 반례는 canonical partition의 단순 3-to-4 local deformation 밖에서 찾아야 한다.
  - 다음 질문:
    - fixed all-positive mask 아래 global stratum-A DFS가 SAT인가?
    - canonical partition의 k-cell union rigidity가 다른 k에도 성립하는가?

### `ER-20260812-060053-64dc53` — 범주론·함자적 관점

- **SYNTHESIS / ADVANCED** — strategist
  - 요약: 120 quotient의 S8 대칭과 240 representative certificate 사이의 간극을 principal gauge set의 equivariant descent datum 및 1-cocycle holonomy로 해석했다.
  - 접근: free residual Z2 quotient를 principal set으로 보고 section을 선택해 transporter를 state-dependent gauge cocycle로 표현했으며 Coxeter relation 검사를 base closure와 fiber holonomy로 분리했다.
  - 재사용 가능한 단서:
    - quotient action은 representative action의 존재나 유일성을 자동으로 주지 않는다.
    - section에 상대적인 lift transporter는 비가환 1-cocycle이고 presentation loop의 누적값은 holonomy다.
    - base orbit--stabilizer 자료는 stabilizer가 fiber에 어떻게 작용하는지 잊는다.
    - exact-lift certificate와 quotient-invariant-only certificate는 서로 다른 증명 의무다.
  - 다음 질문:
    - 120×7 transporter cocycle가 모든 Coxeter 및 stabilizer loop에서 trivial holonomy를 갖는가?
    - 이 cocycle의 cohomology class는 section 변경과 무관하게 trivial한가?
    - GP invalidity certificate가 representative bundle을 거치지 않고 quotient invariant로 factor되는가?

### `ER-20260812-061100-b3a1f0` — 범주론·함자적 관점

- **HYPOTHESIS / ADVANCED** — strategist
  - 요약: 유한 gadget 접합 귀납을 finite boundary-state category의 productive endomorphism과 observational congruence로 정식화했다.
  - 접근: gadget 반복을 morphism powers와 additive cost로 증명하고, 경계정보 완전성을 모든 suffix에 대한 Myhill--Nerode형 동치로 정의해 separating-suffix 반증 시험을 만들었다.
  - 재사용 가능한 단서:
    - 반복 가능한 gadget은 같은 완전한 boundary state로 돌아오는 endomorphism이어야 한다.
    - productive cycle cost (p,q)는 귀납 상한의 주계수 q/p를 직접 준다.
    - 같은 interface state의 두 prefixes를 분리하는 suffix는 접합 정리의 최소 반례다.
    - finite-state 안정화 뒤에는 weighted transition graph의 minimum-mean cycle이 최적 periodic run 후보를 준다.
  - 다음 질문:
    - rank-2 layer OM에 대해 finite-index observational congruence가 존재하는가?
    - 어떤 최소 boundary data가 GP, coverage, realizability continuation을 모두 보존하는가?
    - transition category에 cost sequence 2,2,2,3인 productive endomorphism이 존재하는가?
- **ATTEMPT / BLOCKED** — experimentalist
  - 요약: Lawrence gluing API 부재를 확인하고 observational-equivalence harness의 최소 schema와 fixed-window signature 반증 의무를 정식화했다.
  - 접근: repository generator capabilities를 검사하고 standalone rank-2 outputs를 재생한 뒤 GP/circuit의 cut-crossing dependency로 필요한 boundary fields를 도출했다.
  - 재사용 가능한 단서:
    - rank-6 future GP는 prefix의 C(N,4)개 Y query를 잠재적으로 구분한다.
    - 고정 최근-window signature는 별도 locality theorem 없이는 완전하지 않다.
    - 안전한 첫 schema는 pending GP queries, coverage profile, realization interface를 모두 보존해야 한다.
  - 다음 질문:
    - rank-2 layer family에는 과거 GP query를 유한하게 압축하는 특별한 항등이 있는가?
    - prefix length가 증가할 때 bounded observational class count가 안정되는가?
- **PIVOT / ADVANCED** — strategist
  - 요약: 특정 gadget 반복 증명에는 local sound interface만 필요하고 global observational completeness는 전수검색·최적성 주장에만 필요하다는 핵심 구분을 정식화했다.
  - 접근: one-step extension lemma의 귀납 증명과 Myhill--Nerode형 search completeness를 분리하고, cross-boundary GP obligations를 contractions M/Y의 future queries로 재해석했다.
  - 재사용 가능한 단서:
    - 한 productive loop의 증명은 전체 state space의 finite complete quotient를 요구하지 않는다.
    - gadget 부재나 minimum-mean optimality를 주장하려면 observational completeness가 필요하다.
    - rank-6 cross-boundary GP memory는 과거 4-set contractions의 future rank-2 query family로 표현된다.
    - abstract OM closure, realizability closure, witness preservation은 서로 독립된 one-step obligations다.
  - 다음 질문:
    - rank-2 layer candidate 하나에 대해 T1--T6를 모두 만족하는 local interface contract를 쓸 수 있는가?
    - cross-boundary contraction queries가 structured layer product에서 bounded factorization을 갖는가?
    - 2,2,2,3 후보 loop가 k=2,3 direct composition에서 interface recurrence를 유지하는가?
- **CRITIQUE / ADVANCED** — falsifier
  - 요약: local productive-loop 귀납은 충분하지만 semantic inductive invariant T0과 McMullen parameter accounting T7이 누락됐고, k≤3 검사는 누적 defect를 배제하지 못한다.
  - 접근: 귀납 명제의 양화 범위를 명시하고 T1--T6의 논리적 독립성을 abstract validity, realizability, coverage의 기존 반례군과 누적 counter 모델로 공격했다.
  - 재사용 가능한 단서:
    - fixed right recursion에는 associativity가 필요 없지만 semantic closure의 보편 양화는 필요하다.
    - k=1,2,3 성공은 숨은 누적 counter가 k=4에서 실패하는 경우를 배제하지 못한다.
    - OM validity, realizability, witness coverage는 서로 독립된 보존 의무다.
    - cost additivity와 ν(d) 해석 사이에는 rank=d+1 및 실제 ground cardinality 회계가 필요하다.
  - 다음 질문:
    - 실제 σ의 각 field는 arbitrary-k one-step proof의 어느 항에서 사용되는가?
    - realizability lemma는 존재 보존인가, 주어진 좌표의 compatible extension인가?
    - candidate에 k=4 이후 처음 나타나는 cross-boundary GP 또는 coverage defect가 있는가?
- **SYNTHESIS / ADVANCED** — strategist
  - 요약: 접합 gadget 반복을 T0--T7의 uniform one-step lemma로 정리하고, finite-state completeness가 반복 증명에는 불필요하지만 전수검색·최적성에는 필요함을 확정했다.
  - 접근: fixed right recursion에 대한 직접 귀납, exact dimension/ground-size 회계, realizability와 witness preservation의 독립성을 결합하고 k≤3 성공을 깨는 누적-defect 반례를 제시했다.
  - 재사용 가능한 단서:
    - semantic one-step invariant가 있으면 전체 observational quotient 없이도 gadget 반복 상한을 증명할 수 있다.
    - fixed right recursion에는 associativity가 필수가 아니며 arbitrary placement를 주장할 때만 필요하다.
    - bounded k tests는 누적 defect를 발견할 수 있지만 uniform closure를 증명하지 못한다.
    - T0--T7 중 abstract OM validity, realizability, witness preservation, McMullen accounting은 독립 의무다.
  - 다음 질문:
    - 실제 rank-2 layer encoding에서 T0--T7을 만족하는 one-step operator G를 정의할 수 있는가?
    - 2,2,2,3 후보 run이 동일 semantic σ로 복귀하는가?
    - cross-boundary contraction queries M/Y가 layer formula에서 bounded factorization을 갖는가?

### `ER-20260812-064048-4d4884` — 확률론적 방법

- **SYNTHESIS / ADVANCED** — strategist
  - 요약: Paley orbit의 28/70 local obstruction 밀도에서 평균 2.5회 randomized tester와 전체 120 classes를 때리는 크기≤10 universal hitting set의 존재를 유도했다.
  - 접근: 한 class의 miss probability를 계산하고 120 classes에 union bound를 적용했으며 S8 transitivity로 column incidence 48과 hitting-set lower bound 3을 계산했다.
  - 재사용 가능한 단서:
    - 조밀한 local obstruction orbit은 one-sided randomized tester로 빠르게 검출할 수 있다.
    - union bound는 orbit 전체를 적중하는 작은 deterministic local-test set의 존재를 준다.
    - row/column regular incidence는 exact set-cover certificate의 강한 checksum이다.
    - randomized discovery와 deterministic proof replay를 구분해야 한다.
  - 다음 질문:
    - 120×70 incidence hypergraph의 transversal number는 정확히 얼마인가?
    - 최소 hitting set은 PGL(2,7) 또는 다른 작은 subgroup orbit으로 설명되는가?
    - 같은 probabilistic compression이 9-circuit partial-GP candidates에도 적용되는가?

### `ER-20260812-065054-7185c2` — 가환대수

- **HYPOTHESIS / ADVANCED** — strategist
  - 요약: shared-basis sign consistency를 signed support-overlap graph의 balance 및 quadratic binomial ideal의 properness와 동치화했다.
  - 접근: circuit orientation gauges를 F2 vertex variables로 바꾸고 shared-basis equations를 labeled graph edges로 표현하여 cycle-space obstruction과 parity union-find 검사를 유도했다.
  - 재사용 가능한 단서:
    - shared-basis consistency는 GP보다 약하며 negative cycle이 정확한 최소형 obstruction이다.
    - connected overlap graph에서 consistent projective gauge는 유일하다.
    - fundamental cycle basis만 검사하면 모든 shared-basis equations의 consistency를 판정할 수 있다.
    - negative cycle은 binomial ideal의 짧은 unit-ideal certificate로 저장할 수 있다.
  - 다음 질문:
    - restricted 196 minimal nine-covers 중 negative-cycle filter가 몇 개를 제거하는가?
    - 일반 P=256 nine-cover stream에서 shortest negative cycle의 분포는 무엇인가?
    - balanced graph에서 canonical gauge로 복원한 partial basis signs를 가장 싸게 GP 검사하는 순서는 무엇인가?
- **COMPUTATION / LOW_YIELD** — experimentalist
  - 요약: signed-graph consistency를 canonical 240 covers와 restricted replacement family에 적용해 모두 balanced임을 확인하고, reported 196 중 28개가 duplicate-support masks임을 발견했다.
  - 접근: support/gamma에서 epsilon edges를 직접 계산하고 spanning-forest parity propagation을 수행했으며, replacement pairs에는 support uniqueness를 별도 검사했다.
  - 재사용 가능한 단서:
    - canonical 240 covers는 모두 connected K8 balanced이며 projective gauge가 유일하다.
    - restricted 196 mask covers 중 28은 duplicate-support pair이고 circuit family에서 제외해야 한다.
    - 남은 168 distinct-support nine-covers는 모두 connected 24-edge balanced graphs다.
  - 다음 질문:
    - 일반 P=256 nine-cover stream에서는 negative-cycle reject fraction이 얼마인가?
    - support uniqueness 이후 fully-fixed GP filter가 몇 후보를 제거하는가?

## topic 최종 종합 (원문 전문)

종합문은 `CLAIM / ASSUMPTIONS / WORK / STATUS / NEXT_TEST / ROUTE` 구조다.
**`STATUS` 절이 무엇이 확정이고 무엇이 미확인인지 구분한다 — 반드시 함께 읽을 것.**

### QQ-0001 — 기존 상한 U(d) 의 정확한 출처와 값

- topic `T-20260812-001938-01a044` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `requirements_1_to_3_synthesized_requirement_4_split` · 종료 시각 2026-08-12T01:20:27+00:00
- source_key: `questions/OPEN.md::QQ-0001`
- evidence_refs:
  - `research_log.md#L51`
  - `research_log.md#L54`
  - `knowledge/lawrence_f_additivity.md#3-상한-구성-a-논문-definition-32-재현하고-검증했다`
  - `questions/OPEN.md#QQ-0001`
  - `layer_search.py::known_upper_bound`
  - `lawrence_travel.py::star_n`
  - `lawrence_travel.py::selftest[6]`
  - `om_core.py::mcmullen_evaluate`
  - `local_runs/math_dialogue/responses/strategist-7.json`

CLAIM: QQ-0001의 일반 상한과 구성 색인은 다음과 같이 종합된다. 2001 A*의 witness 크기는 M(d)=2d+ceil((d+1)/2)=floor(5d/2)+1이고, 따라서 McMullen 수의 일반 상한은 nu(d)<=U(d):=M(d)-1=floor(5d/2)이다. 질문이 요구한 d=3,5,7,9,11의 U는 7,12,17,22,27이다. 원 출처는 Ramirez Alfonsin (2001) Theorem 1.1이고 A*는 Definition 3.2이며, 2023 서론 식 (2)는 같은 결론 nu(d)<M(d)의 재인용이다.

ASSUMPTIONS: witness at n이면 nu(d)<=n-1이다. 2001의 f(d)는 프로젝트 내부의 Lawrence-family 임계함수 f_L(d)가 아니라 McMullen 수 nu(d)다. 문헌 확인 수준은 저장소가 확보한 2001/2023 FULLTEXT 기록을 따른다. 계산은 문헌 정리를 증명하지 않고 색인·구현 정합성만 검사한다.

WORK: d=2k이면 (M,U)=(5k+1,5k), d=2k+1이면 (M,U)=(5k+3,5k+2)다. 홀수 표기 d=2m-1에서는 A* witness n=5m-2와 U=5m-3이 된다. 오래된 코드 기준식 U_old=2d+floor((d+1)/2)은 even d에서 U와 같고 odd d에서 M=U+1과 같으므로, odd 차원에서 upper bound와 witness size를 혼동했다. experimentalist의 결정론적 대조는 d=2..11 전 범위에서 M=floor(5d/2)+1, U=M-1, U_old-U=d mod 2를 모두 확인했다. 또한 d=2,3,4,5의 A* n=6,8,11,13은 GP 적법성, travel witness, om_core witness, 정수 realization certificate를 모두 통과했다.

STATUS: 확정된 문헌 범위는 일반식, Theorem 1.1, Definition 3.2 및 요구 1--3이다. 계산 범위는 산술·코드 대조 d=2..11의 EXHAUSTED_ON_SCOPE와 A* replay d=2..5다. 반박된 것은 U_old를 모든 parity의 상한으로 읽는 해석이다. 추측하거나 미확인인 것은 d=5 전용으로 일반식보다 강한 nu(5)<=11 문헌이 존재하는지 여부다. 문헌 부재는 결론 내리지 않는다. 우편함 전체 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: 요구 4는 별도 문헌 의무로 유지한다. 2023 survey의 저차원 표와 전후방 참고문헌에서 d=5 또는 nu(5)를 검색하고, 발견한 주장은 FULLTEXT/ABSTRACT_ONLY/SECONDHAND로 분리한다. 저장소 회귀 검사는 d=2..11의 세 항등과 d=2..5 A* replay를 양성 대조군으로 유지하면 된다.

ROUTE: 요구 1--3의 토론은 종결한다. 요구 4는 외부 문헌 검색 범위를 명시한 별도 topic으로만 재개하며, 현재 topic에서 근거 없이 반복하지 않는다.

### QQ-0002 — rank-2 layer union 의 실현 정리

- topic `T-20260812-002939-02dcd5` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `realizability_theorem_synthesized_literature_scope_split` · 종료 시각 2026-08-12T01:30:42+00:00
- source_key: `questions/OPEN.md::QQ-0002`
- evidence_refs:
  - `questions/OPEN.md#QQ-0002`
  - `extended_lawrence.py::lawrence_union_chirotope`
  - `extended_lawrence.py::layer_vectors`
  - `extended_lawrence.py::stack_vectors`
  - `extended_lawrence.py::realize_union`
  - `om_core.py::Chirotope.from_vectors`
  - `knowledge/insights/ledger.jsonl#HI-0004`
  - `local_runs/math_dialogue/responses/strategist-3.json`

CLAIM: 같은 labeled ground set [n] 위의 uniform realizable rank-2 layers L_0,...,L_{m-1}의 ordered product chirotope chi(j_1<...<j_{2m})=product_i chi_i(j_{2i+1},j_{2i+2})는 항상 realizable이다. 각 layer의 정수 실현을 v_j^(i)라 하고 엄격 증가 정수열 lambda_0<...<lambda_{n-1}를 택하면, w_j(t)=(t^{i lambda_j}v_j^(i))_{i=0}^{m-1}가 충분히 큰 양의 정수 t에서 이 product를 실현한다. 특히 lambda_j=j 또는 j+1이면 충분하며, 질문의 'lambda=j 최대항 동점' 우려는 비최대항끼리의 동점일 뿐이다.

ASSUMPTIONS: 모든 layer는 uniform rank-2이고 정수 벡터로 실현된다. basis 행은 ground-set 증가순, 좌표 열은 layer block 순서다. g=min_j(lambda_{j+1}-lambda_j)>0, H는 모든 layer 2x2 minor 절댓값의 상계, C_min은 모든 basis의 연속쌍 최고계수 절댓값 최솟값이다. uniform integer realization이므로 C_min>=1이다.

WORK: 고정 basis의 generalized Laplace 전개는 크기 2의 labeled ordered partitions S=(S_0,...,S_{m-1})를 합하며 항 수는 N=(2m)!/(2!)^m, 지수는 E(S)=sum_i i sum_{j in S_i}lambda_j다. 비최대 배정에는 weight inversion이 있고 교환하면 E가 적어도 g 증가한다. 따라서 유일 최고 partition은 연속쌍 S_i*={j_{2i+1},j_{2i+2}}다. 이 partition의 row shuffle은 항등이라 부호가 +1이고 최고계수 부호는 정확히 product union chirotope다. 나머지 항 절댓값의 합은 (N-1)H^m t^{E*-g} 이하이므로 모든 basis에 공통으로 t^g>(N-1)H^m/C_min이면 최고항이 지배한다. 현재 `layer_vectors`에서는 H<=n-1이어서 보수적으로 t^g>(N-1)(n-1)^m이면 충분하다. lambda에 상수를 더하면 모든 maximal minor에 basis-independent 양의 인자만 생기므로 lambda_0>=0으로 정규화해 정수 좌표를 얻는다.

STATUS: 내부 증명 사슬은 ordered-partition Laplace 전개, inversion 유일성, shuffle sign, 공통 t bound까지 완성됐다. 계산 범위는 m=2의 지정 6개 partition 전수, m=3의 seed 고정 12 tuples x 7 bases x 90 partitions, symbolic/direct determinant 168회 및 bound 초과 t에서 12/12 tuple 전체 basis 일치다(EXHAUSTED_ON_SCOPE/VERIFIED ON SCOPE). 반박된 주장은 lambda=j가 최고항 동점을 만든다는 것이다. 기존 t=11,101의 55/55 성공은 일반 근거가 아니라 작은 후보별 certificate일 뿐이다. Lawrence--Weinberg 1981이 union 적법성만 증명했는지 realizability까지 증명했는지의 정확한 theorem 번호·문면은 여전히 별도 문헌 의무다. 본 내부 증명은 그 더 강한 문헌 진술을 가정하지 않는다. 전체 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: 저장소에 반영하기 전 prover의 수식을 독립적으로 문서 감사하고, m=4 작은 사례를 선택적 회귀검사로 추가할 수 있다. 구현에서 고정 스킴 t=11,101을 일반 정리의 t 하한으로 오인하지 말고, per-object `om_core` certificate 경로는 명시적 bound 구현 전까지 유지한다. Lawrence--Weinberg 원문 질문은 FULLTEXT를 확보한 별도 topic에서만 재개한다.

ROUTE: QQ-0002의 수학적 실현성 핵심과 요구 2--3은 종결한다. 요구 1의 역사적 원문 진술은 별도 문헌 의무로 분리하며, 근거 없이 추정하지 않는다.

### QQ-0003 — 혼합 rank layer 로의 확장

- topic `T-20260812-012939-32606c` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `mixed_rank_realizability_classical_embedding_and_priority_synthesized` · 종료 시각 2026-08-12T04:10:42+00:00
- source_key: `questions/OPEN.md::QQ-0003`
- evidence_refs:
  - `git:c4aa224:questions/OPEN.md#QQ-0003`
  - `git:c4aa224:docs/STATE.md#1-B`
  - `git:c4aa224:extended_lawrence.py::stack_vectors`
  - `git:c4aa224:lawrence_signs.py::fast_chirotope`
  - `local_runs/math_dialogue/responses/strategist-13.json`
  - `local_runs/math_dialogue/responses/strategist-27.json`
  - `local_runs/math_dialogue/responses/experimentalist-30.json`
  - `om_core.py::Chirotope.is_valid`
  - `om_core.py::Chirotope.from_vectors`
  - `symmetry_reduction.py::relabel`

CLAIM: QQ-0003의 세 요구는 다음처럼 종합된다. (1) positive composition r_0+...+r_{k-1}=R<=n과 같은 labeled ground set 위의 uniform realizable rank-r_i layers가 주어지면, 정렬 basis j_0<...<j_{R-1}를 조성 크기의 연속 blocks로 잘라 layer chirotope들을 곱한 ordered product는 항상 uniform realizable rank-R chirotope다. (2) 모든 r_i=1이면 chi(j_0<...<j_{R-1})=product_i s_i(j_i)로, 저장소의 고전 Lawrence sign-matrix formula와 정확히 같다. 더 강하게 임의의 조성 family가 고전 Lawrence family를 포함한다. (3) 탐색 우선순위는 홀수 d에서 pure rank-2, 짝수 d에서 한 rank-1과 나머지 rank-2인 최소 혼합 조성이다.

ASSUMPTIONS: 각 layer는 추상 OM이 아니라 uniform realizable OM이다. layer ranks는 양수이고 block order는 고정한다. 실현가능성이 미확인인 abstract rank>=3 layer까지 정리를 확대하지 않는다. 결과 권한은 UNASSESSED_DIALOGUE_ONLY이며 문헌의 역사적 정리 범위는 별도다.

WORK: layer i의 실현 vectors를 v_j^(i), 엄격 증가 비음수 정수열 a_i와 lambda_j를 택하고 w_j(t)=direct_sum_i t^(a_i lambda_j)v_j^(i)로 둔다. generalized Laplace 전개의 ordered partition S_i, |S_i|=r_i 항은 exponent E(S)=sum_i a_i sum_{j in S_i}lambda_j를 갖는다. inversion 교환에 의해 유일 최대 block-set assignment는 basis를 r_0,r_1,... 크기의 연속 구간으로 자른 target이다. block 내부 순열은 이미 layer determinant에 합쳐지고 target row shuffle sign은 +1이다. target coefficient는 uniformity로 nonzero다. N=R!/product_i r_i!, H_i=max layer-i maximal-minor absolute value, C_min=target coefficient absolute-value minimum, delta=min_i(a_{i+1}-a_i) min_j(lambda_{j+1}-lambda_j)라 하면 t^delta>(N-1)product_i H_i/C_min은 모든 bases에 공통인 충분조건이다. 음수 exponent weight가 있으면 a와 lambda에 상수를 더해 비음수화하며 이는 각 determinant에 양의 공통인자만 준다. layer realization cell의 모든 maximal-minor signs를 보존하는 rational approximation 후 denominator를 없애면 정수 realization도 얻는다. 이 사슬은 unequal blocks, repeated weights, shuffle sign, common t에 대한 falsifier 감사를 통과했다.

고전 포함은 rank-1 rows를 조성에 따라 연속 묶어 각 묶음의 내부 ordered product를 하나의 realizable rank-r_i layer로 만들면 바깥 product가 원래 product_i s_i(j_i)를 그대로 복원한다는 grouping으로 증명된다. 포함이 실제로 proper한지는 최소 유한 범위에서 확인됐다. total rank 3에서 C=(1,1,1), M12=(1,2), M21=(2,1)의 normalized labeled chirotope 수는 n=4에서 모두 8, n=5에서 |C|=64, |M12|=|M21|=96, C=M12 intersection M21, n=6에서 512,1536,1536이고 다시 C가 정확한 교집합이다. 따라서 mixed family는 n=5부터 고전을 proper하게 포함한다(EXHAUSTED_ON_SCOPE for n=4,5,6). 최소 proper representatives는 `is_valid`와 명시 정수 좌표의 모든 maximal-minor sign replay를 통과했다.

composition reversal lemma도 성립한다. ground order reversal과 layer order reversal은 c=(r_0,...,r_{k-1}) family를 reverse(c) family로 옮기며 생기는 parity는 basis-independent global sign이다. 계산에서도 M12와 M21은 n=4,5,6에서 labeled sets로는 n>=5부터 다르지만 reversal 전단사 후 exact equality였다. 따라서 odd R=2m+1에서 singleton slot p와 m-p는 동치지만, 다른 slots는 증명 없이 합치지 않는다. d=4,R=5에서는 edge (1,2,2)~(2,2,1)와 middle (2,1,2)의 두 유형을 모두 유지한다.

STATUS: 확정된 내부 증명은 임의 조성 ordered product의 실현가능성, all-rank-1=classical, 모든 조성의 classical 포함, reversal equivalence다. 계산 범위는 mixed properness와 rank-3 reversal equality의 n=4,5,6 완전 열거다. C=M12 intersection M21의 일반 n 명제는 관찰일 뿐 본 질문에 필요한 결론이 아니므로 열린 별도 추측으로 남긴다. 유망 조성 순위는 탐색 비용에 근거한 전략이지 상한 개선 보장이 아니다.

NEXT_TEST: 구현한다면 odd d/even R에는 기존 (2,...,2)를 유지한다. even d/odd R에는 (1,2,...,2)의 singleton slots를 reversal orbit별로 하나씩 구현하고, 고전 grouping을 양성 대조로 넣는다. generic rank-3 layer는 생성·실현가능성 문제가 다시 어려워지므로, rank-1/2 family가 실패하고 구조적 rank-3 subclass가 있을 때만 (3,2,...,2)를 연다. 한-block 조성 (R)은 모든 realizable rank-R OM을 layer 하나로 다시 부르는 tautology라 탐색 축소가 없다. 구현이 explicit t bound를 직접 쓰기 전에는 candidate별 `om_core.Chirotope.from_vectors` 좌표 replay를 유지한다.

ROUTE: QQ-0003은 여기서 닫는다. 일반 교집합 C=M12 intersection M21이나 조성별 orbit 수는 본 정리·구현 우선순위와 분리된 후속 연구로만 재개한다.

### 창발 탐사 — SAT·CSP·모델검사

- topic `T-20260812-022948-c57d4f` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `bounded_kernel_lower_bound_synthesized` · 종료 시각 2026-08-12T03:11:25+00:00
- source_key: `emergent-research::ER-20260812-022948-187f4e`
- evidence_refs:
  - `local_runs/math_dialogue/responses/strategist-16.json`
  - `local_runs/math_dialogue/responses/experimentalist-17.json`
  - `local_runs/math_dialogue/responses/experimentalist-19.json`
  - `om_core.py::Chirotope.circuit`
  - `om_core.py::Chirotope.is_valid`
  - `reorientation_cover.py::bad_reorientation_mask`
  - `reorientation_cover.py::is_unbalanced_circuit_after_reorientation`

CLAIM: rank 6, n=12의 임의의 uniform oriented matroid에 대해 gauge-fixed 재배향 2^11개를 circuit obstruction mask들로 덮을 수 있다면 그 덮개의 circuit 수는 적어도 9다. 동치로, 서로 다른 8개 circuit obstruction mask가 재배향 cube 전체를 덮는 경우는 없다. 이는 9개 circuit으로 덮을 수 있다는 존재 명제가 아니며, McMullen witness나 realizable witness의 존재도 주장하지 않는다.

ASSUMPTIONS: 각 circuit support는 7-subset이고, support S={s_0<...<s_6}의 signed circuit은 C_S(s_i)=(-1)^i chi(S\{s_i}) convention을 따른다. 원소 0의 재배향을 gauge-fix한 11-cube를 사용한다. 원래 OM은 uniform rank 6이므로 선택된 8원소 집합에 대한 restriction도 uniform rank 6 chirotope여야 한다.

WORK: (1) 각 circuit bad mask의 크기는 256이므로 2048점을 8개로 덮으면 중복 없는 exact partition이어야 한다. (2) 두 bad mask가 disjoint하려면 두 7-support의 교집합 크기가 적어도 6이어야 한다. (3) 8개의 서로 다른 7-subset이 pairwise intersection>=6을 만족하면, n=12에서는 어떤 8-set R에 대해 정확히 {R\{x}:x in R}인 top이다. 고정 6-set을 공유하는 star는 최대 6개뿐이며, falsifier의 독립 감사가 혼합형까지 배제했다. (4) S_12 relabeling으로 R={0,...,7}을, cube translation과 전역 sign gauge로 첫 circuit mask center를 +------로 고정할 수 있다. (5) 남은 유한 문제를 두 구현이 독립 열거했다. support별 64 antipodal gamma class에 대한 pairwise-disjoint DFS는 1,341개 노드와 240개 canonical exact cover를 산출했다. 240개 모두 28개 shared-basis sign 방정식에는 일관됐지만, 그로부터 복원한 n=8,r=6 chirotope는 전부 Grassmann--Pluecker 검사를 실패했다. experimentalist와 falsifier의 수, convention, 대칭 quotient 결과가 정확히 일치했다. 따라서 전역 uniform rank-6 OM에서 나올 수 있는 canonical exact partition은 없다.

STATUS: mask 용량, exact-partition 환원, support 교집합 조건, top 분류 및 대칭 환원은 수학적/조합적 환원으로 독립 감사되었다. canonical kernel 240개에 대한 부재는 EXHAUSTED_ON_SCOPE이며 독립 계산이 재현했다. 그러나 각 후보의 첫 GP 위반을 담은 영속 certificate와 독립 replay script가 아직 없으므로 저장소의 PROVEN 정리나 witness evidence로 승격하지 않는다. 이 종합의 권한은 UNASSESSED_DIALOGUE_ONLY다. realizability는 이 추상 OM 필요조건에는 필요하지 않지만, 향후 실제 McMullen 상한에는 다시 필수다.

NEXT_TEST: 240개 canonical cover 각각에 대해 support gamma, orientation gauge z, 28 basis signs, 첫 GP 위반 relation을 압축 JSONL로 저장하고, `om_core.Chirotope.is_valid`와 별도의 직접 3항 GP evaluator가 같은 240개를 거부하는 replay를 만든다. 이 certificate가 재현된 뒤에만 보조정리 통합을 검토한다. 다음 독립 연구 질문은 9-circuit cover의 Stage A/GP extension 존재 여부이며, 이번 결과만으로 9-cover 존재를 추론하지 않는다.

ROUTE: 이 bounded-kernel cycle은 여기서 닫는다. 후속 계산 작업은 experimentalist에게 persistent certificate/replay 생성을, 그 감사 후 prover에게 짧은 '8-cover 불가능' 보조정리 작성을 별도 topic으로 넘기는 것이 적절하다.

### 창발 탐사 — 군 작용·표현론

- topic `T-20260812-031941-13c2cd` · 작성 `falsifier` · 종류 `CRITIQUE` · 등급 `UNASSESSED`
- 종료 사유: `max_rounds` · 종료 시각 2026-08-12T04:05:49+00:00
- source_key: `emergent-research::ER-20260812-031941-f5510e`
- evidence_refs:
  - `local_runs/math_dialogue/responses/experimentalist-28.json`
  - `local_runs/math_dialogue/responses/experimentalist-23.json`
  - `reorientation_cover.py::bad_reorientation_mask`
  - `om_core.py::Chirotope.reorient`

CLAIM: Q 위 S_8 작용, 단일 orbit, stabilizer H의 order 336 및 sharply 3-transitive 결론은 보고된 전수 항목으로부터 논리적으로 따라온다. 그러나 ‘대표 GP 위반 하나+generator word+a=127’만으로 240개 certificate를 replay한다는 축약은 아직 충분하지 않다. quotient 작용을 실제 240개 lift에 올리는 state-dependent reorientation cocycle를 함께 보존해야 한다.

ASSUMPTIONS: q(s)=min(s,a.s)는 240개 해의 residual involution a에 대한 quotient다. 각 adjacent generator g와 class q에서 32개 renormalization이 같은 quotient image를 주지만, 실제 representative sign vector 또는 chirotope lift는 서로 residual a 및 gauge reorientation만큼 다를 수 있다. GP 적법성은 ground relabeling과 reorientation 아래 불변이다.

WORK: 첫째, 7개 generator가 involution·distant commutation·braid relations를 Q의 모든 점에서 만족하므로 Coxeter presentation을 통해 S_8→Sym(Q) homomorphism이 정의된다. 120점 단일 orbit이면 추상 S_8에서 root stabilizer 크기는 40320/120=336이다. 이때 stabilizer 원소가 ordered triple (0,1,2)에 보내는 336개 image가 모두 다르다는 계산은 가능한 서로 다른 ordered triple의 총수 8·7·6=336과 같으므로 H의 8점 작용이 free이자 transitive, 즉 sharply 3-transitive라는 결론에 충분하다. 단, permutation/action pair BFS가 40320개라는 사실만으로 Q-action의 faithfulness를 주장해서는 안 된다. pair의 ground permutation 좌표가 kernel을 가릴 수 있다. 현재 결론에는 faithfulness가 필요하지 않다.

둘째, PGL(2,7) 식별은 order나 sharp 3-transitivity라는 수치 일치만으로 선언하지 말아야 한다. 계산 certificate는 Ω={0,…,7}과 P^1(F_7) 사이 bijection c를 하나 제시하고, 336개 H 원소에 대해 cHc^{-1}가 336개 Möbius permutation 집합과 정확히 같음을 set equality로 검사하면 충분하다. 임의의 표준 labeling에서 equality만 검사하면 conjugate subgroup을 거짓 음성으로 놓칠 수 있다.

셋째, GP transporter에는 각 상태 q와 generator g마다 실제 선택된 lift를 q의 canonical lift에서 gq의 canonical lift로 보내는 reorientation mask r(q,g)와 residual bit ε(q,g)∈{0,1}가 필요하다. word g_k…g_1을 따라 r을 relabeling과 함께 누적하는 semidirect-product 규칙을 replay해야 한다. quotient image만 저장하면 서로 다른 32 normalization이 같은 q'를 준다는 사실은 알지만, 어느 basis sign이 어떤 multiplier를 받는지는 복원되지 않는다. root의 위반 GP relation (I;a,b,c,d)을 σ로 운반할 때 index 재정렬 parity와 각 basis의 reorientation factor도 직접 적용해야 한다. 그 뒤 각 target의 28 basis signs와 대조하면 120 canonical lifts가 인증되고, residual a를 한 번 더 적용해 나머지 120 lifts가 인증된다.

STATUS: 작용·orbit·stabilizer·sharp 3-transitivity는 EXHAUSTED_ON_SCOPE 보고를 전제로 논리 감사를 통과했다. PGL conjugacy와 240-solution GP transporter는 OPEN이다. 특히 quotient-level word만으로 lift-level certificate가 된다는 암묵적 가정은 반박됐다. 모든 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: experimentalist가 (1) conjugating bijection c와 두 336-element permutation sets의 canonical hash, (2) 120×7개의 r(q,g), ε(q,g), (3) spanning-tree word별 누적 lift가 저장된 target 28-sign vector와 일치하는지, (4) 운반된 첫 GP relation이 실제로 실패하는지를 출력하라. Coxeter loop를 따라 누적 cocycle이 canonical lift에서 identity가 되는지도 검사하면 word-choice 독립성의 가장 싼 반증 시험이다.

ROUTE: strategist가 현재 확정 범위와 미완 certificate를 분리해 종합한다. 추가 계산 라운드를 열 경우 experimentalist에게 quotient action 재계산이 아니라 lift cocycle 및 conjugating bijection만 요구한다.

### 창발 탐사 — 정보이론·부호이론

- topic `T-20260812-041939-994efd` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `paley_switching_certificate_synthesized` · 종료 시각 2026-08-12T04:41:05+00:00
- source_key: `emergent-research::ER-20260812-041939-213de3`
- evidence_refs:
  - `local_runs/math_dialogue/responses/strategist-32.json`
  - `local_runs/math_dialogue/responses/experimentalist-33.json`
  - `local_runs/math_dialogue/responses/falsifier-35.json`
  - `local_runs/math_dialogue/responses/experimentalist-19.json`
  - `local_runs/math_dialogue/responses/strategist-21.json`
  - `om_core.py::Chirotope.is_valid`
  - `om_core.py::Chirotope.reorient`

CLAIM: rank-6,n=12의 8-circuit exact-partition kernel에서 생기는 canonical Stage A 해는 GP 검사 앞에서 임의적인 240개 예외가 아니다. orientation-consistent signs를 8원소 restriction의 dual rank-2 pair signing으로 바꾸고 vertex switching 및 global sign을 quotient하면, 정확히 P^1(F_7)의 Paley tournament가 만드는 하나의 120-element labeled switching/projective orbit가 된다. 이 Paley class의 모든 원소는 정확히 28개의 rank-2 GP forbidden quadruples를 가지므로 rank-6 chirotope restriction으로 확장될 수 없다. 따라서 앞서 얻은 '8개 circuit obstruction mask로 cover 불가능, 최소 cover 수>=9'의 유한 GP kernel은 Paley 대표 하나와 orbit equality로 압축된다. 이는 9-cover의 존재를 주장하지 않는다.

ASSUMPTIONS: canonical support top은 R={0,...,7}, supports S_x=R\{x}이고 첫 circuit mask가 정규화돼 있다. orientation-consistent 28 signs χ(R\{i,j})를 복원한다. i<j에서 dual pair sign은 p_ij=(-1)^(i+j-1)χ(R\{i,j})이며 p_ji=-p_ij다. triple signature는 τ_ijk=p_ij p_ik p_jk이고 모든 τ의 동시 global sign을 quotient한다.

WORK: dual parity (-1)^(i+j-1)은 complement와 pair를 ground order로 옮기는 permutation parity와 일치한다. primal reorientation ρ 아래 p'_ij=Gρ_iρ_jp_ij, G=product_eρ_e이므로 τ'_ijk=Gτ_ijk다. 따라서 normalized τ는 ground reorientation, residual a=127 pair, circuit representative 선택을 잊는 정확한 switching/projective invariant다. 역으로 두 pair signings의 τ가 같으면 한 기준 vertex에서 switching signs를 복원할 수 있고, τ가 전부 반대이면 먼저 pair signing을 global negate하면 되므로 normalized τ는 이 quotient의 완전 불변량이다.

표준 Paley 모델은 vertices F_7 union {infinity}, finite x,y에서 y-x가 quadratic residue {1,2,4}이면 x→y, infinity→finite로 정의한다. 결정론적 전수는 canonical DFS의 240 solutions를 재생했고 GP-valid 수 0, normalized τ distinct 수 120, multiplicity 전부 2를 얻었다. Paley τ의 8! relabel/global-sign orbit도 120개였으며 두 key sets가 양방향 exact equality였다. 첫 candidate와 Paley 대표 사이 explicit permutation은 old→new=(0,1,2,7,6,5,4,3)이었다. 따라서 단순한 orbit-size 일치가 아니라 실제 orbit 식별이다.

GP obstruction은 국소적이다. i<j<k<l에서 세 dual products (p_ij p_kl,-p_ik p_jl,p_il p_jk)가 단색이면 rank-2 GP가 실패한다. 이는 네 triples (ijk,ijl,ikl,jkl)의 τ pattern이 (+,-,+,-) 또는 그 음수라는 것과 동치다. dual parity를 원 rank-6 relation으로 되돌리면 `om_core.is_valid`의 raw forbidden pattern (+,-,+)와 정확히 일치한다. Paley 대표에는 이런 quadruple이 정확히 28개이고, 전체 240 candidate histogram도 {28:240}이었다. 예시는 Paley Q=(0,1,2,4), 첫 candidate Q=(0,1,2,5), Y=(3,4,6,7)이다. switching, projective sign, relabeling은 이 obstruction을 보존하므로 invalidity-only certificate에는 이전에 제안된 state-dependent lift cocycle가 필요 없다. 그 cocycle는 각 28-sign lift 자체를 정확히 재구성하려는 더 강한 목적에만 필요하다.

STATUS: dual convention, reorientation invariant, invariant의 완전성, rank-2/rank-6 GP 대응은 falsifier의 독립 대수 감사를 통과했다. 계산 범위는 240 Stage A solutions, 120 normalized keys, Paley 8! orbit, solution당 70 quadruples의 EXHAUSTED_ON_SCOPE다. 그러나 persistent replay artifact가 없으므로 저장소의 PROVEN 보조정리나 certificate로 승격하지 않는다. 모든 권한은 UNASSESSED_DIALOGUE_ONLY다. 실현가능성은 이 추상 OM 필요조건의 부재 증명에는 관여하지 않는다.

NEXT_TEST: 영속화가 승인되는 별도 작업에서는 Paley root pair signs, normalized 56 triple signs, 28 forbidden quadruples, explicit candidate↔Paley permutation, candidate 120-key set과 Paley orbit의 canonical set-equality hash를 local replay artifact로 만든다. verifier는 root forbidden quadruple의 dual products와 대응 rank-6 raw GP products를 직접 계산해야 한다. 양성 반증 대조로 Paley edge 하나를 뒤집었을 때 orbit equality 또는 28-count histogram이 깨지는지도 포함한다. 이 artifact가 재현된 뒤에만 8-cover 불가능 보조정리의 프로젝트 승격을 검토한다.

ROUTE: 정보이론·부호이론 cycle은 여기서 닫는다. 후속은 새 수학 탐사가 아니라 experimentalist의 persistent replay 제작과 그 독립 감사로 분리한다.

### 창발 탐사 — 극값 조합론

- topic `T-20260812-045004-a73df4` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `stage_a_extremal_counterexamples_found_but_cell_split_family_gp_obstructed` · 종료 시각 2026-08-12T05:13:51+00:00
- source_key: `emergent-research::ER-20260812-045004-508dbc`
- evidence_refs:
  - `local_runs/math_dialogue/responses/strategist-36.json`
  - `local_runs/math_dialogue/responses/experimentalist-37.json`
  - `local_runs/math_dialogue/responses/strategist-38.json`
  - `local_runs/math_dialogue/responses/experimentalist-39.json`
  - `local_runs/math_dialogue/responses/experimentalist-19.json`
  - `local_runs/math_dialogue/responses/strategist-35.json`
  - `om_core.py::Chirotope.is_valid`
  - `reorientation_cover.py::bad_reorientation_mask`

CLAIM: H_ext와 H_min은 모두 Stage A에서 반박되지만, experimentalist의 inclusion-minimal 9-mask 반례는 rank-6 OM으로 확장될 수 없다. 이유는 새 A,B masks가 아니라 남겨 둔 canonical top의 일곱 circuits S_1,...,S_7만으로 R={0,...,7} 위 28개 rank-6 basis signs가 전부 결정되고, 그 restriction이 이미 Paley GP obstruction을 포함하기 때문이다. 따라서 `8-partition의 한 cell을 두 masks로 분할`하는 이 자연스러운 9-cover 생성법 전체는, 원래 일곱 top circuits의 signs를 유지하는 한 OM 후보가 될 수 없다.

ASSUMPTIONS: S_x=R\{x}. retained centers는 순서대로 S_1:+---+++, S_2:+--+--+, S_3:+-+--+-, S_4:+--++--, S_5:++++--+, S_6:+++-++-, S_7:++-++-+이다. 새 circuits는 A=(2,3,4,5,6,7,8):+++++++와 B=(1,3,4,5,6,7,8):+-----+이다. signed-circuit convention은 C_S(s_i)=(-1)^iχ(S\{s_i})이고 support별 projective gauge z_S를 허용한다.

WORK: 먼저 일반적인 결정성 관찰이 있다. R의 임의 6-basis R\{u,v}는 두 top circuits S_u,S_v에서 나타난다. S_0 하나만 제거하고 S_1,...,S_7을 모두 남기면 {S_u,S_v} 중 적어도 하나가 남으므로 모든 C(8,6)=28 basis signs가 이미 고정된다. 따라서 여덟 번째 top circuit은 chirotope restriction을 결정하는 데 필요하지 않다.

명시 centers의 shared-basis equations를 직접 풀면 z=(z_{S1},...,z_{S7},z_A,z_B)=(+,+,-,+,-,+,-,+,+)로 일관된다. 선택된 9 circuits의 63 basis occurrences는 24 shared-basis identifications 뒤 39 distinct signs를 고정하며 충돌은 0이다. 그러나 이 중 R 안의 28 signs에 대해 Y=(0,1,2,5), (a,b,c,d)=(3,4,6,7)의 GP raw products가 (+,-,+)다. 이는 `om_core.is_valid`가 금지하는 형태다. 독립 직접 열거로 완전히 고정된 GP relations 75개 중 28개가 금지형이었고, 첫 위반이 바로 위 relation이다. 따라서 미지의 나머지 885 basis signs를 어떻게 채워도 이 partial chirotope는 GP-valid completion을 갖지 않는다. 이 28개 수는 앞서 확인한 Paley representative의 forbidden-quadruple 수와도 일치한다.

극값 조합론 cycle의 확정된 유도는 다음과 같다. 각 mask 크기는 256이다. 두 masks의 교집합은 overlap t와 projective center distance h만으로 결정되고, t=2:[40,24], t=3:[56,24], t=4:[80,32,16], t=5:[112,48,16], t=6:[160,64,32,0]이다. 9-cover의 pair budget은 P=256+Σρ binom(m(ρ)-1,2)이다. P=256이면 private count는 |Q_i|=256-d_i이고 inclusion-minimal iff 모든 weighted degree d_i<256다. H_ext는 8-partition에 redundant ninth mask를 더한 예로, H_min은 private counts [240,240,224,224,224,224,224,96,96]인 명시 9-cover로 반박됐다. 그러나 후자는 위 seven-top GP core 때문에 OM 단계에서 탈락한다.

STATUS: pair table과 multiplicity/private-count 항등식은 유한 조합 유도다. H_ext 및 H_min 반례는 exact 2048-bit 계산으로 VERIFIED on scope다. 명시 9-family의 sign consistency와 GP 위반은 이번 heartbeat의 직접 유한 계산이며 persistent artifact는 없다. 이것은 9-circuit OM cover의 존재 또는 부재를 일반적으로 판정하지 않고, 특정 cell-splitting 구성 및 그와 동일한 inherited seven-top core만 제거한다. realizability에는 도달하지 않았다. 모든 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: 다음 독립 탐색에서는 Stage A 뒤에 shared-basis consistency만 거는 것으로 부족하다. partial signs가 완성되기를 기다리지 말고, 완전히 지정된 3-term GP relation이 생기는 즉시 가지치기해야 한다. 특히 어떤 8-set R에서도 canonical Paley exact-partition의 8 circuits 중 7개와 projectively 같은 signed subfamily를 포함하면 즉시 금지한다. 가장 작은 새 질문은 `그 forbidden seven-top core를 피하는 inclusion-minimal 9-cover가 존재하는가?`이다. 양성 후보가 나오면 fixed-basis GP filter, full abstract completion, realizability를 순서대로 적용한다.

ROUTE: 극값 조합론 cycle은 여기서 닫는다. 후속은 experimentalist의 새 Stage A+online-GP 탐색으로 별도 topic에서 시작해야 하며, 현재의 두 부재 가설을 다시 사용하지 않는다.

### 개념 증류 — ER-20260812-022948-187f4e × 가환대수

- topic `T-20260812-052023-4d6fa6` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `commutative_algebra_distillation_partial_boolean_idempotent_bridge` · 종료 시각 2026-08-12T05:22:32+00:00
- source_key: `conceptual-distillation::ER-20260812-022948-187f4e::ER-20260812-052023-95ed6c`
- evidence_refs:
  - `math-dialogue-research-log/v1::ER-20260812-022948-187f4e`
  - `local_runs/math_dialogue/responses/strategist-16.json`
  - `local_runs/math_dialogue/responses/experimentalist-19.json`
  - `local_runs/math_dialogue/responses/strategist-21.json`
  - `om_core.py::Chirotope.is_valid`
  - `reorientation_cover.py::bad_reorientation_mask`

CLAIM: 가환대수적으로 이 bounded-kernel 결과의 가장 자연스러운 문장은 `8-cover 문제는 Boolean coordinate algebra에서 단위원 1을 같은 trace의 직교 idempotent 8개로 분해할 수 있는가의 문제이고, cover-level 분해들은 존재하지만 GP ideal을 함께 부과하면 해당 zero-dimensional stratum이 사라진다`이다. Stanley--Reisner ideal 자체가 일차 대상이라기보다, 비동차 Boolean coordinate ring과 그 유한점 ideal이 정확한 대상이다. SR 언어는 complementary literals를 polarization한 뒤에만 보조적으로 나타난다.

ASSUMPTIONS: characteristic 0 또는 2가 아닌 체 k를 쓰고 A=k[x_1,...,x_11]/(x_i^2-x_i)≅k^{2^11}로 둔다. circuit bad mask B_C의 characteristic function을 idempotent e_C∈A로 본다. chirotope sign 변수도 s_B^2=1인 유한 Boolean algebra 안에 둔다. 이는 원 결과의 증명 등급을 바꾸지 않는 재표현이다.

WORK: e_C의 곱셈 연산 trace는 |B_C|=256이다. q개 masks가 cube를 덮으면 점별로 Σe_C≥1이고, q=8일 때 총 trace가 8·256=2048=dim_k A다. 따라서 모든 점에서 합이 정확히 1이어야 하며 e_i e_j=0 (i≠j), Σ_i e_i=1이다. 즉 용량 논증의 `8개면 exact partition`은 A의 단위원을 rank 256의 직교 idempotent 8개로 분해한다는 trace rigidity다. support-intersection 환원은 어떤 idempotent 쌍의 곱이 0일 수 있는지를 결정하는 incidence 조건이다.

canonical support와 gauge를 고정한 뒤 cover equations 및 shared-basis equations가 정하는 유한점 ideal을 I_cover라 하자. 보고된 240 solutions는 이 유한 Boolean 좌표계에서 A_cover≅k^{240}, 따라서 quotient length/Hilbert function의 최종 값 240으로 읽을 수 있다(단, 실제 Gröbner/Hilbert 계산을 한 것은 아니다). GP relation의 세 raw signs를 p_1,p_2,p_3∈{±1}라 하면 forbidden indicator는 b_GP=((1+p_1p_3)(1-p_1p_2))/4다. GP-validity는 모든 b_GP=0이다. 240/240 실패는 유한점 집합 위에서 V(I_cover+I_GP)=∅, 동치로 Boolean coordinate algebra 안에서 I_cover+I_GP=(1)이라는 말이다. 후보별 첫 위반 대신 1=Σ f_i g_i 꼴의 낮은 차수 Nullstellensatz certificate를 찾으면 전수 목록을 하나의 대수적 certificate로 압축할 가능성이 있다.

가장 작은 모형은 A_1=k[x]/(x^2-x)에서 e_0=1-x, e_1=x가 trace 1의 직교 idempotents이고 e_0+e_1=1인 경우다. 이는 두 complementary half-cubes의 exact partition이다. 실제 kernel에서는 같은 현상이 11-cube의 rank-256 idempotents 8개에 일어나며, 그 위에 chirotope GP ideal이 추가되어 cover stratum을 비운다.

STATUS: Boolean coordinate ring, trace rigidity, GP forbidden indicator의 번역은 직접적인 대수적 등가다. `quotient length 240`은 보고된 canonical finite enumeration을 유한점 algebra로 다시 읽은 것이지 독립 Gröbner 계산이 아니다. 낮은 차수 Nullstellensatz certificate, minimal free resolution, Betti table 또는 canonical Stanley--Reisner complex는 아직 얻지 못했다. 특히 signed Hamming balls는 flip-set 포함관계에 대해 simplicial complex가 아니므로 Stanley--Reisner 해석을 직접 적용하면 거짓이다. 전체 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: canonical finite model의 ±1 변수와 exact-cover/shared-basis/GP indicator polynomials를 생성하고, (1) cover quotient의 standard-monomial 수가 240인지, (2) GP generators 추가 후 Gröbner basis에 1이 나오는지, (3) 1-certificate의 최대 차수와 support가 Paley orbit 압축보다 작은지를 측정한다. polarization을 시험한다면 각 bit에 complementary literals u_i,v_i를 두되 u_iv_i=0뿐 아니라 u_i+v_i=1도 유지해야 한다. 후자의 affine relation을 버린 SR complex는 원 문제와 동치가 아니다.

ROUTE: 이 개념 증류는 여기서 닫는다. 별도 후속이 있다면 experimentalist가 240-case replay를 Nullstellensatz/Gröbner certificate로 압축할 때만 가환대수 렌즈를 재사용한다.

### 창발 탐사 — SAT·CSP·모델검사

- topic `T-20260812-053029-6c110f` · 작성 `experimentalist` · 종류 `COMPUTATION_RESULT` · 등급 `VERIFIED`
- 종료 사유: `max_rounds` · 종료 시각 2026-08-12T06:00:19+00:00
- source_key: `emergent-research::ER-20260812-053029-eaae43`
- evidence_refs:
  - `local_runs/math_dialogue/responses/experimentalist-19.json`
  - `local_runs/math_dialogue/responses/experimentalist-39.json`
  - `reorientation_cover.py::bad_reorientation_mask`
  - `local_runs/math_dialogue/responses/experimentalist-47.json`

CLAIM: general stratum-A search는 이번 cycle에서 완주하지 못했지만, 가장 자연스러운 다음 local construction인 `canonical 8-partition의 세 cells를 네 masks로 교체하여 positive graph K4를 만드는 방식`은 불가능함을 50,688-mask universe에서 전수 확인했다. 더 강하게, canonical partition의 임의 세 cells의 union 안에 완전히 포함되는 circuit mask는 원래 그 세 cell masks뿐이다.

ASSUMPTIONS: n=12 gauge-fixed 2048 cube, canonical top exact partition의 8 masks와 이전 gamma solution [63,7,9,18,12,57,54,45]를 사용했다. 세 원래 cells를 제거하고 남은 다섯 cells와 disjoint한 네 masks로 그 768점을 덮으면 전체 9-cover가 된다. 네 replacement masks의 positive graph가 K4이면 전체 positive graph는 isolated 5 vertices plus K4여서 alpha=6, tau=3인 stratum-A 반례가 된다.

WORK: 모든 792 supports와 support당 64 projective centers, 총 50,688 masks를 exact 2048-bit integers로 생성했다. canonical 8 masks는 union 2048, pair budget 0을 재현했다. 제거할 세 cells의 56 choices 각각에 대해, 남은 다섯 cells의 union과 disjoint한 universe masks를 필터링했다. 놀랍게도 매 choice에서 후보 수는 정확히 3이었고, 그 셋은 제거한 원래 세 masks 자체였다. 따라서 네 개의 서로 다른 replacement masks를 고를 수조차 없으며 K4 pair/triple/P 검사는 도달 전에 종료된다. 총 56 choices와 50,688 masks를 seed 없이 완전 열거했다.

STATUS: EXHAUSTED_ON_SCOPE for the three-cell/four-mask replacement family. 이는 general normalized stratum A의 UNSAT가 아니다. 후보가 retained union과 완전히 disjoint해야 한다는 조건은 이 local construction에서는 필수지만, 일반 triple-free P=256 cover의 masks는 모두 서로 양의 교차를 가질 수 있으므로 이 필터로 일반 문제를 축소할 수 없다. tracked artifact나 solver proof는 없고 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: 일반 stratum A에는 canonical partition 주변의 cell replacement 가정을 버리고, fixed all-positive mask와 양의 교차하는 후보 graph를 먼저 만든 뒤 exact-cover-style DFS를 해야 한다. 실용적 순서는 (1) support/center pair table로 P와 degree를 갱신, (2) 실제 bitset으로 triple conflict만 검사, (3) positive graph의 현재 alpha lower bound가 7이면 가지치기하는 것이다. 이번 결과는 1-cell→2-mask뿐 아니라 3-cell→4-mask local deformation도 막혀 있음을 양성 대조로 유지한다.

ROUTE: strategist가 이번 scoped rigidity를 기록하되 H_split의 일반 결론으로 확대하지 않는다. 다음 cycle을 열면 experimentalist에게 global fixed-mask DFS를 더 긴 계산 예산 또는 계산 relay와 함께 배정한다.

### 개념 증류 — ER-20260812-031941-f5510e × 범주론·함자적 관점

- topic `T-20260812-060053-247f05` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `category_theory_distillation_equivariant_descent_cocycle` · 종료 시각 2026-08-12T06:02:33+00:00
- source_key: `conceptual-distillation::ER-20260812-031941-f5510e::ER-20260812-060053-64dc53`
- evidence_refs:
  - `math-dialogue-research-log/v1::ER-20260812-031941-f5510e`
  - `local_runs/math_dialogue/responses/experimentalist-23.json`
  - `local_runs/math_dialogue/responses/falsifier-24.json`
  - `local_runs/math_dialogue/responses/experimentalist-28.json`
  - `local_runs/math_dialogue/responses/falsifier-29.json`
  - `om_core.py::Chirotope.reorient`

CLAIM: 이 cycle의 범주론적 핵심은 `quotient에서의 군 작용은 representative 위의 작용이 아니라, lift를 위한 descent datum의 바닥 자료일 뿐이다`라는 문장이다. 240 representatives에서 자유 residual Z2를 나눈 120-set Q의 S8 작용은 정당하지만, 특정 sign vector와 특정 GP 위반을 운반하려면 240→120 위의 equivariant lift가 추가로 필요하다. section을 하나 고르면 그 추가 자료가 state-dependent gauge 1-cocycle로 나타나며, Coxeter loop의 trivial holonomy가 합성 일관성이다.

ASSUMPTIONS: E는 240 canonical lifts, A≅Z2는 residual reorientation involution, Q=E/A는 120 quotient classes다. 실제 sign-vector 운반에는 A보다 큰 ground-reorientation gauge group K가 필요할 수 있다. S8은 Q에 작용한다. 이는 원 cycle의 계산·감사 범위를 바꾸지 않는 구조적 재표현이다.

WORK: 사영 π:E→Q는 자유 A-action을 갖는 principal A-set이다. quotient action은 각 σ∈S8에 대해 q↦σq만 정한다. 이를 E로 올린다는 것은 π∘tildeσ=σ∘π를 만족하고 gauge action과 양립하는 tildeσ를 일관되게 고르는 것이다. section s:Q→E를 택하면 lift는 tildeσ(s(q))=c(σ,q)·s(σq) 꼴이며 c(σ,q)∈K가 된다. 합성 tildeσtildeτ=tilde(στ)는 정확히 c(στ,q)=c(σ,τq)·σ[c(τ,q)]이라는 비가환 1-cocycle 조건을 준다(정확한 semidirect convention은 reorientation relabeling 작용에 맞춰야 한다). 따라서 adjacent transposition별 120×7 transporter와 residual bit는 임의 보조 데이터가 아니라 equivariant descent datum의 좌표 표현이다.

Coxeter 관계 s_i^2=1, s_is_j=s_js_i, s_is_{i+1}s_i=s_{i+1}s_is_{i+1}는 base Q에서만 확인하면 quotient functor의 well-definedness만 보인다. representative certificate에는 각 관계 loop를 따라 누적된 c가 identity gauge가 되는지도 확인해야 한다. 이것이 trivial holonomy다. base orbit 하나와 stabilizer 336은 Q의 action groupoid가 transitive임을 말하지만, stabilizer loop가 fiber에 비자명하게 작용하는지는 알려 주지 않는다. 따라서 orbit--stabilizer 수치만으로 한 root sign certificate가 모든 lifts에 자연스럽게 운반된다고 결론낼 수 없다.

최소 예는 Q={0,1}, A={±1}, E=Q×A이고 C2가 Q의 두 점을 바꾸는 경우다. quotient transposition은 하나지만 representative lift는 (q,a)↦(1-q,a)와 (q,a)↦(1-q,-a)처럼 여러 개다. section-level transporter를 방향마다 제멋대로 택하면 base에서는 transposition을 두 번 적용해 identity여도 fiber에서는 -1 holonomy가 남을 수 있다. 따라서 quotient path만 저장해서는 어느 representative에 도달했는지 복원할 수 없다.

STATUS: principal-set, equivariant lift, cocycle, holonomy 번역은 원 cycle의 논리적 결손을 정확히 설명한다. 120 quotient의 S8 action, transitivity, stabilizer 336, sharp 3-transitivity라는 계산 결과는 그대로 유지된다. 실제 K-valued cocycle, PGL(2,7) conjugacy, lift certificate는 계산되지 않았다. 또한 GP invalidity처럼 gauge-invariant한 `성질` 자체는 Q로 descend할 수 있으므로, 목적이 exact sign-vector transport가 아니라 invariant-only certificate라면 더 작은 quotient invariant가 cocycle를 우회할 수 있다. 이 cycle은 그러한 별도 invariant를 구축하지 않았다. 모든 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: representative-level certificate가 필요하면 (1) spanning tree의 edge마다 c(s_i,q)를 기록하고, (2) 모든 Coxeter 2-cell과 stabilizer generator loop에서 accumulated holonomy를 계산하며, (3) transported sign vector가 stored target lift와 일치하는지 확인한다. 반대로 invalidity-only 목적이면 먼저 GP obstruction이 Q 위의 자연한 invariant로 factor되는지 시험해 cocycle 의무 자체를 제거할 수 있는지 판별한다. 이 두 certificate 목표를 섞지 않는다.

ROUTE: 이 개념 증류는 여기서 닫는다. 후속 구현에서는 experimentalist가 exact-lift certificate를 택할 때만 cocycle/holonomy 표를 만들고, quotient-invariant certificate를 택하면 그 factorization을 falsifier가 별도로 감사한다.

### 창발 탐사 — 범주론·함자적 관점

- topic `T-20260812-061100-b26aa9` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `conditional_gluing_induction_theorem_T0_T7_synthesized_api_missing` · 종료 시각 2026-08-12T06:31:54+00:00
- source_key: `emergent-research::ER-20260812-061100-b3a1f0`
- evidence_refs:
  - `local_runs/math_dialogue/responses/strategist-49.json`
  - `local_runs/math_dialogue/responses/experimentalist-50.json`
  - `local_runs/math_dialogue/responses/strategist-51.json`
  - `local_runs/math_dialogue/responses/falsifier-52.json`
  - `om_classes.py::lawrence`
  - `om_classes.py::rank2_uniform`
  - `om_core.py::Chirotope.is_valid`
  - `om_core.py::mcmullen_evaluate`

CLAIM: 접합 귀납의 정확한 조건부 정리는 다음이다. uniform realizable OM constructions의 class C에 seed X_0와 fixed right-extension operator G가 있고, semantic predicate P(X)=σ(X)∧UniformOM(X)∧Realizable(X)∧Witness(X)를 두자. 어떤 p,q>0에 대해 (i) P(X_0), (ii) 모든 P-reachable X에 대해 P(X)⇒P(GX), (iii) d(GX)=d(X)+p, n(GX)=n(X)+q가 성립하면 X_k=G^kX_0가 모든 k≥0에서 존재하며 ν(d_0+kp)≤n_0+kq−1이다. 따라서 limsup 계수는 q/p다. residue classes별 seed/cap이 유한 개 있으면 모든 충분히 큰 d에 같은 주계수와 residue-dependent O(1)을 얻는다. 이 정리는 global finite observational quotient, associativity, 모든 parenthesization 비교를 요구하지 않는다.

ASSUMPTIONS: d(X)=rank(X)−1, n(X)=실제 distinct ground elements 수다. Witness는 `어떤 재배향도 convex position이 되지 않음`이며 `mcmullen_evaluate`와 같은 의미여야 한다. Realizable은 abstract GP validity와 분리한다. G는 매 단계 fresh labels와 지정 overlap을 사용한다. 고정 오른쪽 재귀 X_{k+1}=G(X_k)만 주장한다.

WORK: 증명은 보통 귀납이다. base P(X_0). step에서 P(X_k)⇒P(GX_k)=P(X_{k+1}). 회계식은 반복 대입으로 d_k=d_0+kp, n_k=n_0+kq. uniform realizable rank-(d_k+1) witness가 n_k개 ground elements에 있으므로 ν(d_k)≤n_k−1. 이 논증에서 σ가 다른 모든 prefixes를 완전히 분류할 필요는 없지만, `모든 reachable X`에 대한 semantic invariant여야 한다. 단지 g:σ→σ라는 그림 또는 k=1,2,3 계산은 이 보편 명제를 대신하지 않는다.

필수 의무는 최종적으로 T0--T7이다. T0: σ의 semantic inductive invariant와 quantifier domain. T1: fresh labels, overlap, 실제 ground-set 식별. T2: alternation, uniformity, 정확한 rank, 모든 GP. T3: `Real(X)⇒∃ realization of G(X)`; 기존 좌표를 고정한 compatible extension을 주장하려면 별도 강한 정리가 필요하다. T4: witness/coverage preservation. T5: σ recurrence. T6: actual dimension/element cost additivity. T7: r=d+1, distinct n, witness⇒ν(d)≤n−1의 McMullen 회계. fixed right recursion에는 associativity가 필요 없지만, cycle을 위치 독립 gadget으로 사용하거나 여러 parenthesization을 동일시할 때는 다시 필요하다.

가장 싼 누락 반례는 숨은 defect c다. σ가 c를 저장하지 않고 G가 c↦c+1, validity가 c≤3이면 k≤3은 모두 통과하고 k=4에서 실패한다. 따라서 bounded tests는 T0/T5를 반증할 수는 있어도 증명하지 못한다. rank 6에서 naive fixed-window signature가 위험한 이유도 임의 과거 4-set Y가 future 4-elements와 GP relation을 만들기 때문이다. 이는 contraction M/Y의 future rank-2 query로 읽을 수 있다. 하지만 structured layer formula가 모든 Y-query를 bounded factorization할 가능성은 남아 있으므로 finite interface 불가능성으로 단정하지 않는다.

2,2,2,3 run에 대한 정확한 현재 진술은 오직 조건부다. 네 번의 dimension extension에서 새 ground elements 수가 2+2+2+3=9이고 T0--T7을 만족해 같은 semantic interface로 복귀한다면 p=4,q=9여서 ν(d)≤(9/4)d+O(1)을 얻는다. cycle 존재, local closure, realizability, witness preservation은 현재 전혀 검증되지 않았다.

STATUS: local one-step lemma의 충분성, global search completeness와의 분리, T0--T7 의무 및 조건부 slope 계산은 논리 종합을 마쳤다. repository audit상 `lawrence`는 generator 없는 socket이고 glue/boundary API가 없어 project-specific test는 NOT RUN이다. rank2_uniform n=4,5,6의 standalone validity는 접합 근거가 아니다. 모든 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: 실제 layer/glue candidate가 생기면 단계별 `(d,n,rank,uniform,is_valid,realization certificate,mcmullen_evaluate,σ fields)`를 k=0..4에서 기록하고 defect 누적을 공격한다. 동시에 T0--T7 dependency table에서 각 σ field가 arbitrary-k step proof의 어느 식에 쓰이는지 명시한다. bounded tests 통과 뒤에도 symbolic one-step lemma 없이는 상한으로 승격하지 않는다. gadget 탐색·최적성까지 원할 때만 suffix refinement와 finite observational quotient를 추가한다.

ROUTE: 이 범주론 cycle은 조건부 접합 귀납 정리와 명확한 구현 전제까지 도달했으므로 닫는다. 후속은 실제 rank-2 layer encoding과 Glue API가 제공된 별도 topic에서 experimentalist의 k=0..4 반증, falsifier의 T0--T7 감사, prover의 uniform one-step lemma 순으로 재개한다.

### 개념 증류 — ER-20260812-041939-213de3 × 확률론적 방법

- topic `T-20260812-064048-03338c` · 작성 `strategist` · 종류 `SYNTHESIS` · 등급 `UNASSESSED`
- 종료 사유: `probabilistic_distillation_paley_tester_and_hitting_set` · 종료 시각 2026-08-12T06:42:29+00:00
- source_key: `conceptual-distillation::ER-20260812-041939-213de3::ER-20260812-064048-4d4884`
- evidence_refs:
  - `math-dialogue-research-log/v1::ER-20260812-041939-213de3`
  - `local_runs/math_dialogue/responses/strategist-32.json`
  - `local_runs/math_dialogue/responses/experimentalist-33.json`
  - `local_runs/math_dialogue/responses/falsifier-35.json`
  - `om_core.py::Chirotope.is_valid`

CLAIM: 확률론적 방법으로 Paley switching-class obstruction은 두 가지 사람 친화적 문장으로 압축된다. (1) promise candidate 하나에서 균일 무작위 4-subset을 검사하면 GP 위반을 정확히 2/5 확률로 발견하므로 평균 5/2회 검사면 충분하다. (2) 120개 normalized labeled Paley classes 전체를 동시에 적중하는 4-subset들의 deterministic hitting set이 크기 10 이하로 존재한다. 따라서 exact orbit equality가 전제되면 70개 모든 quadruple이나 candidate별 28개 목록 대신 최대 10개의 공통 local tests로 전체 120 classes를 배제할 잠재적 certificate가 있다.

ASSUMPTIONS: 각 normalized class는 70=C(8,4) quadruples 중 정확히 28개 forbidden alternating patterns를 가진다. 120 classes는 S8의 하나의 labeled projective orbit이며 relabeling은 forbidden property를 보존한다. 이는 source cycle의 EXHAUSTED_ON_SCOPE 계산을 전제로 한 확률적 재해석이지 독립 재검증이 아니다.

WORK: 한 class C와 균일 Q∈C([8],4)에 대해 Pr[Q forbidden for C]=28/70=2/5. 독립 복원추출 t회에서 전부 놓칠 확률은 (3/5)^t이고, 첫 성공까지 기댓값은 1/(2/5)=5/2다. 따라서 95% 검출에는 t=6, 99%에는 t=10이면 충분하다. 동치로 하나의 고정 root quadruple을 두고 ground labels를 균일 무작위 permutation해도 image quadruple가 균일하므로 같은 확률이다.

전체 orbit hitting set은 첫 모멘트/union bound로 얻는다. m개의 quadruples를 독립 균일 선택하면 고정 class를 모두 놓칠 확률은 (3/5)^m. 120 classes 중 하나라도 놓칠 확률은 최대 120(3/5)^m이다. m=10에서 이 값은 약 0.7256<1이므로 모든 class를 적중하는 선택이 존재한다. 중복 선택을 제거하면 크기 ≤10인 실제 set을 얻는다. 더구나 S8이 4-subsets에 transitive하므로 총 incidence 120·28=3360은 70 quadruples에 균등 분포하고, 각 quadruple은 정확히 48 classes를 적중한다. 따라서 어떤 hitting set도 적어도 ceil(120/48)=3개가 필요해 최솟값은 현재 3과 10 사이에 있다. 70개의 subsets 대 120 classes의 작은 exact set-cover로 최솟값과 명시 hitting set을 계산할 수 있다.

비교를 위해 임의의 antisymmetric pair signing에서 고정 quadruple의 세 adjusted GP products는 서로 독립인 fair signs이므로 모두 같은 부호일 확률은 1/4이고 expected forbidden count는 70/4=17.5다. Paley class의 28은 이 통계에서 random mean보다 높다. 즉 여기서는 local lemma로 희귀한 bad events를 피하는 상황이 아니라, obstruction이 조밀해 randomized property testing과 hitting-set 압축이 효과적인 상황이다. 이 비교는 Paley를 일반적인 의미의 비랜덤 구조로 단정하지 않고 이 특정 GP statistic만 말한다.

STATUS: 28/70 tester, miss bound, expected stopping time, size≤10 hitting-set existence, 각 quadruple incidence 48, lower bound 3은 source counts를 전제로 한 정확한 확률/계수 유도다. 명시 최소 hitting set은 아직 계산되지 않았다. randomized tester는 one-sided지만 proof-grade zero-error certificate가 아니며, 저장된 hitting set과 120-class replay가 있어야 deterministic evidence가 된다. 전체 권한은 UNASSESSED_DIALOGUE_ONLY다.

NEXT_TEST: 120×70 incidence matrix를 재생해 exact minimum set cover를 풀고, 최소 quadruple list와 각 class의 첫 hit를 저장한다. 양성 대조로 모든 row sum=28, 모든 column sum=48, 총합=3360을 검사한다. 찾은 set을 candidate↔Paley orbit equality replay 뒤 적용해 120/120 hit인지 확인한다. 확률 tester를 실험 탐색에 쓰면 seed와 sampled quadruples를 기록하고, 최종 부재 주장은 deterministic full replay로만 한다.

ROUTE: 이 확률론적 개념 증류는 여기서 닫는다. 후속은 experimentalist가 작은 70-variable exact hitting-set 문제를 별도 artifact로 풀 때만 재개한다.

## 중단 시점에 열려 있던 topic

- `T-20260812-014209-d3f7b3` — [compute] d=2, n=5 전수에서 witness 부재 확인 (생성 2026-08-12T01:42:09+00:00)
- `T-20260812-014250-f77e2c` — [compute-result] d=2, n=5 전수에서 witness 부재 확인 (생성 2026-08-12T01:42:50+00:00)
- `T-20260812-065054-e2b979` — 창발 탐사 — 가환대수 (생성 2026-08-12T06:50:54+00:00)

## 개념 증류 — 다른 분야 언어로의 번역

한 사이클의 결과를 다른 수학 분야 렌즈로 다시 쓴 것이다. **재표현이므로 원 결과의
증명 등급을 바꾸지 않는다.**

### 가환대수 — `PARTIAL`

- 원 사이클 `ER-20260812-022948-187f4e` → 증류 `ER-20260812-052023-95ed6c`
- 렌즈: Stanley–Reisner ideal·syzygy·Hilbert 자료로 번역

**사람이 읽는 문장** — 8개의 circuit obstruction이 재배향 cube를 덮는다는 것은 Boolean 함수 대수에서 1을 같은 크기의 직교 idempotent 8개로 분해하는 것이며, 계산된 모든 분해는 Grassmann--Pluecker ideal과 양립하지 않는다.

**작동 원리** — 각 bad mask의 indicator는 trace 256인 idempotent다. 8개 trace의 합이 전체 대수 차원 2048과 같아 cover는 자동으로 exact partition이 된다. cover equations는 240개의 유한점을 남기지만 GP forbidden-indicator equations를 더하면 모든 점이 제거된다.

**최소 예** — A_1=k[x]/(x^2-x)에서 x와 1-x는 trace 1의 직교 idempotents이며 합이 1이다. 이는 1-cube의 두 점을 정확히 분할하는 최소 모형이고, 실제 11-cube에서는 rank 256 idempotents 8개가 같은 역할을 한다.

**전이 범위** — 유한 Boolean cube에서 모든 obstruction set의 크기가 같고 compatibility/extension 조건을 polynomial indicator로 쓸 수 있는 다른 exact-cover kernel에도 trace 하한, equality rigidity, unit-ideal certificate가 그대로 적용된다.

**표준 대상**
- Boolean coordinate ring / finite function algebra
- orthogonal idempotent decomposition and regular trace
- zero-dimensional radical ideal and quotient length
- Hilbert function / standard monomials
- Hilbert Nullstellensatz certificate
- polarization and Stanley--Reisner ideals (indirect only)
- cover ideals and Alexander duality (possible follow-up)

**한계 (반드시 함께 읽을 것)**
- 원 240-case 계산과 독립인 Gröbner 또는 Nullstellensatz certificate는 아직 없다.
- signed Hamming balls는 down-closed가 아니므로 원자료 자체는 Stanley--Reisner complex가 아니다.
- polarization은 u_i+v_i=1이라는 affine 관계까지 유지해야 하며, 순수 squarefree ideal만으로는 동치가 아니다.
- 이 번역은 abstract GP obstruction까지만 다루며 realizability나 McMullen witness 존재를 증명하지 않는다.

**문헌 검색어**
- Boolean coordinate ring orthogonal idempotents exact cover trace
- Nullstellensatz certificate exact cover Boolean cube
- polarization Boolean ideals Hamming balls Stanley Reisner
- cover ideals Alexander dual exact cover hypergraph
- oriented matroid Grassmann Plucker ideal sign constraints

### 범주론·함자적 관점 — `CONCEPTUALIZED`

- 원 사이클 `ER-20260812-031941-f5510e` → 증류 `ER-20260812-060053-64dc53`
- 렌즈: 보존되는 구조·자연성·보편 성질로 번역

**사람이 읽는 문장** — 대칭을 gauge quotient에서 확인한 것만으로는 실제 부호 대표를 운반할 수 없다. 대표 운반에는 각 대칭 단계의 gauge 보정과 모든 관계식 loop에서 보정이 되돌아온다는 cocycle 조건이 필요하다.

**작동 원리** — 240→120은 residual Z2 principal bundle처럼 작동한다. S8은 바닥 120 classes에 작용하지만 section을 통해 representatives로 올릴 때 state-dependent reorientation이 생기며, 그 보정은 합성에 대해 1-cocycle 법칙을 만족해야 한다. Coxeter loop의 누적 gauge가 비자명이면 quotient에서는 닫힌 경로가 representative에서는 닫히지 않는다.

**최소 예** — Q={0,1}, E=Q×{±1}에서 Q를 뒤집는 동일한 C2 action은 fiber sign을 보존하거나 뒤집는 서로 다른 lifts를 갖는다. base transposition만 기록하면 어느 lift인지 알 수 없고, 방향별 보정을 불일치하게 고르면 두 번 적용한 base loop 뒤 fiber sign -1이 남는다.

**전이 범위** — 재배향, 전역부호, 좌표 gauge 등으로 후보를 quotient한 뒤 군 대칭으로 certificate를 압축하는 모든 유한 탐색에 적용된다. quotient orbit에서 representative witness·부호표·좌표를 복원하려면 동일한 descent 의무가 생긴다.

**표준 대상**
- principal G-set / torsor
- action groupoid
- equivariant structure and descent datum
- nonabelian 1-cocycle
- group extension and semidirect product
- holonomy of presentation loops
- Grothendieck construction (organizational viewpoint)

**한계 (반드시 함께 읽을 것)**
- 실제 reorientation gauge group K와 semidirect convention을 명시해야 cocycle 식을 코드로 replay할 수 있다.
- 원 cycle은 cocycle 값을 계산하거나 cohomology class의 triviality를 보이지 않았다.
- gauge-invariant 성질만 인증한다면 representative lift가 불필요할 수 있으며, 별도 quotient invariant가 cocycle를 우회할 수 있다.
- PGL(2,7)라는 군 식별은 명시 conjugacy 없이는 이 개념화로부터 나오지 않는다.

**문헌 검색어**
- equivariant lift group action principal G-set nonabelian cocycle
- descent datum action groupoid section cocycle
- group extension lifting permutation action torsor
- Coxeter presentation cocycle holonomy
- oriented matroid reorientation group action quotient

### 확률론적 방법 — `CONCEPTUALIZED`

- 원 사이클 `ER-20260812-041939-213de3` → 증류 `ER-20260812-064048-4d4884`
- 렌즈: 무작위 구성·첫/둘째 모멘트·국소 보조정리로 번역

**사람이 읽는 문장** — Paley형 exact-cover 후보는 GP 위반이 70개 위치 중 28개에 조밀하게 퍼져 있어 무작위 한 위치만 봐도 40% 확률로 실패를 잡고, 공통된 최대 10개 위치만 골라도 120개 labeled 후보 전체를 반드시 잡는 선택이 존재한다.

**작동 원리** — 각 후보의 forbidden quadruple density가 2/5이므로 반복 sampling의 miss probability가 (3/5)^t로 지수 감소한다. 120개 후보에 union bound를 적용하면 10개의 무작위 위치 중 모든 후보를 하나 이상 때리는 선택이 양의 확률로 존재한다.

**최소 예** — 한 Paley class에서 70개 quadruples 중 28개가 bad다. 한 번 놓칠 확률은 3/5이고, 독립 10회 모두 놓칠 확률은 (3/5)^10≈0.00605다.

**전이 범위** — 유한 대칭 orbit의 모든 후보가 같은 수의 local obstructions를 갖는 다른 GP kernel에도 적용된다. 후보 수 N과 obstruction density δ라면 m개의 공통 random tests로 모두 적중할 충분조건은 N(1−δ)^m<1이다.

**표준 대상**
- one-sided randomized property testing
- first moment method and union bound
- set cover / transversal number of a regular hypergraph
- orbit incidence design
- geometric stopping time
- derandomization by conditional expectation (possible construction)

**한계 (반드시 함께 읽을 것)**
- 120-class exact orbit equality와 class당 28개 count가 먼저 deterministic하게 재현돼야 한다.
- 크기≤10 hitting set은 존재만 보였고 명시 set과 최소성은 아직 없다.
- random sampling만으로는 proof-grade 부재 certificate가 되지 않는다.
- 이 결과는 GP invalidity만 다루며 realizability나 McMullen witness 존재를 결론내리지 않는다.
- Local Lemma는 bad events가 조밀한 이 상황의 주 메커니즘이 아니다.

**문헌 검색어**
- orbit incidence hypergraph transversal number probabilistic method
- derandomization hitting set group action conditional expectation
- property testing tournament switching class forbidden quadruples
- Paley tournament four vertex patterns
- regular hypergraph set cover symmetric group orbit
