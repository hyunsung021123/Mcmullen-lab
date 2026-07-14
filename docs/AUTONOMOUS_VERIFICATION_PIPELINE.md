# docs/AUTONOMOUS_VERIFICATION_PIPELINE.md — 자율 반례 탐색·검증 파이프라인

Epic #37 / 첫 구현 Task #38. (source: chatgpt, relayed by user)

이 문서는 전체 아키텍처의 source of truth 다. 구현은 단계별(Work Package)로 진행하며,
**선행 단계가 정확성·성능 게이트를 통과하기 전에 다음 단계를 구현하지 않는다.**

## 1. 현재 문제와 병목

- LLM 위원회는 여러 역할로 나뉘어 있지만 실질 행동 공간이 `element_count` /
  등록된 성질의 `require`/`forbid` 로 제한된다. 실측 결과, 구조적 가설 대신
  근거 없는 n-추정만 반복하는 저품질 제안으로 수렴했다.
- `proof_checker` 는 수학적 증명기가 아니라 형식·공허성·기존 witness 보존을
  검사하는 게이트다.
- Z3 생성기는 GP-valid chirotope 를 목표와 무관하게 열거한 뒤 Python 에서
  witness 를 판정한다 — **witness 조건이 생성기·검증 과정 바깥에 있다.**

따라서 새 구조의 핵심은 LLM 프롬프트를 늘리는 것이 아니라 **witness 조건을
생성기와 검증 과정 안으로 옮기는 것**이다.

## 2. O2026 참고에 대한 사실성 경계

O2026 단위거리 반증 사례에서 참고하는 것은 공개적으로 확인된 교훈뿐이다:

1. 원래 기하 문제를 다른 수학적 도메인으로 **정확히** 번역한다.
2. 텍스트 추측보다 **계산 가능한 구조**를 사용한다.
3. 사람이 독립 검증할 수 있는 **명시적 증거**를 출력한다.

공개 근거가 확인되지 않은 다음 내용은 사실처럼 문서화하지 않는다: 특정 PRM 사용,
특정 크기의 hidden chain of thought, Python sandbox, Lean/LRAT certificate pipeline.
이 프로젝트의 PRM·과정 검증·certificate 는 **새로 설계해 도입하는 것**이지 O2026
구현의 복제가 아니다. Private hidden chain of thought 는 저장소에 기록하지 않는다 —
저장하는 것은 형식화된 주장 / 짧은 rationale summary / 가정 / 검증 의무 / 실행한
검사 / 반례 / 계산 증명서 / 첫 실패 위치뿐이다.

## 3. 핵심 번역: Boolean hypercube coverage (WP1에서 구현·검증됨)

Ground set \(E=\{0,\ldots,n-1\}\), uniform rank-\(r\) chirotope
\(\chi:\binom{E}{r}\to\{-1,+1\}\). Affine McMullen 문제에서는 현재 코드 관례대로
\(r=d+1\).

\(S=\{s_0<\cdots<s_r\}\in\binom{E}{r+1}\) 의 signed circuit:

\[ C_{\chi,S}(s_i) = (-1)^i\,\chi(S\setminus\{s_i\}) \]

재배향 \(\rho\in\{\pm1\}^E\) 에 대해 \(\chi^\rho(B)=\chi(B)\prod_{e\in B}\rho_e\) 이므로

\[ C_{\chi^\rho,S}(s_i) = (-1)^i \chi(S\setminus\{s_i\}) \prod_{e\in S\setminus\{s_i\}}\rho_e
   = C_{\chi,S}(s_i)\cdot\Big(\prod_{e\in S}\rho_e\Big)\cdot\rho_{s_i}. \]

\(\prod_{e\in S}\rho_e\) 는 support 전체에 공통인 부호라 circuit 의 양·음 분할에 영향을
주지 않는다. 즉 **재배향 후 circuit 의 상대 부호 = 원래 circuit 부호 × 각 원소의
\(\rho_{s_i}\)**.

전역 부호반전은 convexity 를 보존하므로 원소 0 을 고정한다:
\(G=\{\pm1\}^{E}/\{\pm\mathbf 1\}\cong(\mathbb Z/2\mathbb Z)^{n-1}\), \(|G|=2^{n-1}\).

현재 코어 정의(convex ⟺ 모든 circuit 이 min(pos,neg)≥2)에 따라, 각 circuit support
\(S\) 가 convexity 를 파괴하는 재배향 집합을

\[ B_S=\Big\{\rho\in G:\ \min\big(|C^{+}_{\chi^\rho,S}|,\,|C^{-}_{\chi^\rho,S}|\big)\le1\Big\} \]

로 정의하면:

\[ \boxed{\ \chi\text{ 가 witness } \iff G=\bigcup_{S\in\binom{E}{r+1}}B_S\ } \]

**양방향 논증.**
(⇐) 모든 재배향 \(\rho\) 가 어떤 \(B_S\) 에 속하면, 모든 \(\rho\) 에 대해 \(\chi^\rho\) 는
unbalanced circuit 을 가진다 → 어느 재배향도 convex position 이 아니다 → witness.
(⇒) witness 면 모든 재배향이 non-convex 인데, non-convex 의 정의가 곧
"min(pos,neg)≤1 인 circuit 존재"이므로 그 \(\rho\) 는 그 circuit 의 \(B_S\) 에 속한다.
즉 두 방향 모두 convex position 의 **정의를 전개한 것**이며, 유일한 비자명한 내용은
위의 재배향-후-circuit 부호 공식이다.

**검증 절차 (모두 통과 — Task #38 PR 참조).**
1. 위 수식의 양방향 논증 문서화 (이 문서).
2. tiny exhaustive corpus 에서 legacy verifier 와 100% 일치.
3. larger sampled corpus 에서 100% 일치.
4. positive witness 와 non-witness 모두 포함 (rank-2 특이 사례 포함).
5. 독립 certificate verifier replay.
6. semantic CI 통과.

## 4. Bit convention (certificate/Lean export 까지 동일 유지)

```text
k in [0, 2^(n-1))
k 의 bit i  ⟺  ground-set 원소 i+1 반전
원소 0 은 절대 반전하지 않음
```

## 5. 구현된 모듈 (WP0 + WP1)

| 모듈 | 역할 | 의존성 |
|---|---|---|
| `reorientation_cover.py` | exact bitset coverage verifier (`evaluate_coverage`) | 표준 라이브러리 + `om_core` |
| `certificate.py` | witness certificate v1 생성 + Markdown/KaTeX 보고서 + CLI | `om_core`, `reorientation_cover` |
| `certificate_verify.py` | **독립** certificate 검증기 (coverage 로직 미공유) + CLI | 표준 라이브러리 + `om_core` **만** |
| `benchmark_coverage.py` | WP0 baseline oracle/corpus/benchmark (B0 vs B1) | 위 모듈들 + `generator` |
| `reorientation_sat.py` | WP2 고정-χ convex-reorientation SAT 검증기 (SAT model replay 강제, UNSAT=`VERIFIED_BY_SOLVER`) | `om_core` + z3(옵셔널) |
| `cegis_search.py` | WP3 GP outer solver + exact CEGIS (재배향 obstruction cut 학습, cut replay 강제) + WP4 orbit-aware 열거 | `om_core`, `reorientation_sat` + z3(옵셔널) |
| `symmetry_reduction.py` | WP4 (Z₂)^(n-1)⋊S_n exact orbit 축소 (lex-leader canonical, orbit_dedup, automorphism_count) | 표준 라이브러리 + `om_core` |
| `research_ir.py` | WP5 typed ResearchStep IR (`research-step/v1`, kind 10종 × 필수 obligation, legacy bias 무손실 왕복) | 표준 라이브러리만 |
| `process_verifier.py` | WP6 결정론적 Process Verifier (first-failure, fail-closed, legacy 게이트 어댑터) | `om_core`/`criteria`/`generator`/`theorist`/`research_ir` |
| `evidence_db.py` | WP6b append-only 근거 저장소 (JSONL + hash chain, 수정/삭제 API 없음) | 표준 라이브러리만 |
| `fixtures/golden_certificate_d2_n6.json` | CI용 golden certificate (d=2, n=6, 32 obstructions) | — |

핵심 계약:

- witness 판정은 `covered_count == total_reorientations` 의 **exact 비교**로만 한다.
  float coverage ratio 는 UI/ranking용 파생값일 뿐 truth condition 이 아니다.
- `certificate_verify.py` 는 `reorientation_cover`/`search`/`generator`/`theorist`/
  `memory`/`manager`/UI 를 import 하지 않는다. 각 obstruction 을
  `om_core.Chirotope.reorient(flip).circuit(support)` 로 직접 순회 검사한다.
- 새 경로가 legacy(`is_reorientable_to_convex`)와 불일치하면 새 경로를 채택하지
  않는다. `om_core.py` 는 동결이다.
- 메모리는 사전 추정(`estimate_memory_bytes`) + 설정 가능한 한도로 보호하며, 한도
  초과 시 조용한 폭발 대신 명시적 오류를 낸다.

## 6. Trust labels

```text
CONJECTURAL   LLM 또는 사람이 제안했지만 검증 전
EMPIRICAL     유한 표본에서 관찰된 패턴
VERIFIED      현재 deterministic kernel(om_core)에서 직접 검증
CERTIFIED     독립 certificate verifier 가 재검증
FORMALIZED    Lean 같은 proof assistant kernel 이 수락
```

상위 등급을 사칭하지 않는다 — 특히 `CERTIFIED` 를 `FORMALIZED` 로, solver 의
UNSAT(`VERIFIED_BY_SOLVER`)를 `CERTIFIED` 로 표시하지 않는다.

## 7. Trusted computing base (TCB)

현재 TCB 는 다음뿐이다:

1. `om_core.py` — chirotope/GP/circuit/convex/reorient 판정 (동결).
2. `certificate_verify.py` — certificate replay (독립성 계약 유지).
3. Python 표준 라이브러리 / 인터프리터.

`reorientation_cover.py` 의 최적화된 bitset 경로는 TCB 가 **아니다** — 그 결과는
항상 legacy 차등 검증과 독립 replay 로 뒷받침되어야 한다. LLM·search loop·
Discovery·memory 는 어떤 의미에서도 TCB 에 들어오지 않는다.

## 8. dedup-before-accept 위험 (알려진 문제, #49)

`generate_backtracking` 은 orbit dedup 이 accept filter 보다 먼저 실행된다.
reorientation-invariant 하지 않은 조건을 hard pruning 으로 쓰면 orbit 전체가 판정
없이 사라질 수 있다 (0010 실측: 현재 DFS 순서에서는 손실 0이었으나 보장된 성질
아님). 이번 WP 에서는 generator 를 침습적으로 수정하지 않는다. 새 coverage
verifier 는 `accept` 에 의존하지 않는다. 향후 pruning rule 은 orbit-invariant 이거나
recall 보존 증명이 있을 때만 적용한다 (#41, #49).

## 9. 자동 자기수정 경계

자율 루프가 다음 파일을 자동 수정하게 하지 않는다: `om_core.py`, certificate
verifier, GP 정의, witness 정의, upper-bound bridge theorem. 자율 루프가 자동
생성할 수 있는 코드는 향후 별도 sandbox/plugin 영역으로 제한한다.

## 10. 후속 Work Package 로드맵 (구현 금지 — Issue로만 존재)

각 단계는 선행 게이트 통과 후에만 착수한다. 상세 수용 조건은 각 Issue 에 있다.

| WP | Issue | 내용 | 선행 조건 |
|---|---|---|---|
| WP2 | #39 | fixed-χ convex-reorientation SAT verifier (SAT model replay 필수, UNSAT 은 `VERIFIED_BY_SOLVER` 등급) | #38 게이트 통과 |
| WP3 | #40 | GP outer solver + exact CEGIS (반례 ρ 를 차단하는 일반 제약 학습, learned cut replay 필수) | #39 |
| WP4 | #41 | **구현됨** — `symmetry_reduction.py` + orbit-aware CEGIS 열거. (6,3) witness 전수 파악 3,181s→63.6s(50x), witness orbit 손실 0 전수 검증, witness isomorphism class 3개 발견 | 완료 |
| WP5 | #42 | **구현됨** — `research_ir.py`. kind 10종 전부 obligation 보유, legacy 3종 무손실 왕복, hidden-CoT 길이 상한 | 완료 |
| WP6 | #43 | **구현됨** — `process_verifier.py`. fail-closed(실행기 없는 obligation 은 기각), 기계 판독 가능한 first-failure + 반례, proof_checker/counterexample_hunter 를 legacy adapter 로 보존 | 완료 |
| WP6b | #44 | **구현됨** — `evidence_db.py`. JSONL + chain hash(개찬 탐지), trust label 검증, LLM 자유 서술 필드 없음 | 완료 |
| WP7a | #45 | rule-based step ranker (score 는 순서만, 진실 결정 금지) | #43, #44 |
| WP7b | #46 | learned PRM (선행 데이터 조건 + 20% 개선 go/no-go) | #45 |
| WP7c | #48 | Cross-domain translation registry (exactness 등급 강제) | #38 |
| WP8 | #47 | certificate Markdown/LaTeX/Lean export 번들 (`FORMALIZED` 는 Lean kernel 수락 후에만) | #38 |

독립 트랙: #49 (dedup-before-accept), #50 (Discovery evidence provenance).

## 11. WP2 (SAT) — 구현됨 (#39, `reorientation_sat.py`)

고정된 χ 에 대해 재배향 Bool 변수 \(z_1,\ldots,z_{n-1}\) 를 두고, 각 support \(S\) 의
재배향 후 positive count \(N_S^+(z)\) 에 대해

\[ \operatorname{Convex}(\chi^z) \iff \bigwedge_{S\in\binom E{r+1}}
   \big(2\le N_S^+(z)\le|S|-2\big). \]

SAT → model 이 실제 convex reorientation (반드시 `om_core` 로 replay — 함수 안에서 강제).
UNSAT → candidate witness, certificate v1 통과 후에만 `CERTIFIED`.
타임아웃/불능 → `UNKNOWN` (UNSAT 으로 승격 금지).

실측(#39 PR): (5,3) 전수 192 + (6,3) 표본 200 차등 검증 mismatch 0, SAT replay 100%,
UNSAT candidate certificate replay CERTIFIED. 작은 n 에서는 legacy 열거가 더 빠르며
(witness 1건 기준 0.8ms vs 12ms), SAT 의 가치는 속도가 아니라 (a) UNSAT 의 증명적
구조(WP3 CEGIS 의 cut 학습 기반), (b) 부분 제약과의 결합 가능성이다 — 정직 보고.

## 12. WP3 (CEGIS) — 구현됨 (#40, `cegis_search.py`)

\[ \exists\chi\ \big[\operatorname{GP}(\chi)\ \land\ \forall\rho\,
   \neg\operatorname{Convex}(\chi^\rho)\big] \]

outer(GP solver)가 χ 제안 → inner 가 convex 재배향 탐색 → SAT 이면 그 ρ 는 정확한
반례, outer 에 "다음 χ 는 ρ 아래 unbalanced circuit 을 가져야 함" 제약

\[ \bigvee_{S\in\binom E{r+1}}\Big[\min\big(|C^{+}_{\chi^\rho,S}|,|C^{-}_{\chi^\rho,S}|\big)\le1\Big] \]

을 추가(모델 하나 블로킹이 아니라 **재배향을 차단하는 일반 제약 학습**) →
UNSAT 이면 legacy replay + certificate + 독립 검증.

실측(#40 PR): (5,3) 무-witness 증명 naive 192 모델 vs CEGIS 16 모델(12.0x 감소),
(6,4) naive 1,920 모델/5.7s vs CEGIS 15 모델/0.9s(128x 모델·6.1x 시간) — 수용 조건
(2개 벤치마크에서 10x 모델 또는 3x 시간) 충족. recall: (4,2) 24/24, (6,3) 전수
9,984/9,984 (WP0 product 전수 실측과 일치, 소요 53분 — CI 밖 수동 검증). learned cut 은 추가 직후 om_core 직접
계산으로 replay 된다 — (a) 반례 χ 를 실제로 배제하는지, (b) 알려진 witness 를
배제하지 않는지.

## 13. WP5/6 (ResearchStep IR + Process Verifier) 개요 — 참고용, 구현 금지

모든 제안을 `research-step/v1` 로 정규화 (kind: definition / equivalence /
necessary_condition / sufficient_condition / pruning_rule / generator_family /
encoding / performance_claim / certificate_transform / formalization — kind 별로
요구 obligation 이 다르다). Hard gate 는 전부 결정론적이고 한 단계라도 실패하면
기각 + **첫 실패 위치** 기록. 동적 피드백은 자유 텍스트가 아니라 failed step ID /
first failed obligation / exact counterexample / scope / evidence ID 를 전달.
기존 `proof_checker`/`counterexample_hunter` 는 삭제하지 않고 legacy gate adapter 로
사용한다. learned PRM(#46)은 hard gate 를 **모두 통과한** step 의 실행 순서만 정하는
scheduler 이며 진실 판정자가 아니다.

## 14. 단계별 go/no-go (engineering threshold — 수학적 정리 아님)

- B1 을 search 기본 경로로 교체 검토: fixed corpus median speedup ≥ 3x, p95 치명적
  regression 없음, memory budget 준수, mismatch = 0. 미달이어도 certificate 기능은
  유지하되 optional verifier 로만 사용.
- CEGIS: 최소 두 benchmark 에서 outer model 수 10배 감소 또는 wall time 3배 감소.
- learned PRM: rule-based 대비 top-k hard-gate 통과율(또는 검증 예산당 유효 step)
  20% 이상 개선.

## 15. 최종 자율 루프 (문서용 pseudocode — 이번 구현 아님)

```python
def autonomous_research_loop(goal, budget):
    state = load_verified_evidence()
    queue = PriorityQueue()
    while budget.remaining():
        proposals = proposer_ensemble.propose(
            goal=goal, certified_facts=state.certified_facts,
            empirical_findings=state.empirical_findings,
            first_failures=state.first_failures,
            exact_counterexamples=state.counterexamples)
        for raw in proposals:
            step = research_ir.normalize(raw)
            audit = process_verifier.verify_until_first_failure(
                step, known_witnesses=state.witnesses,
                known_nonwitnesses=state.nonwitnesses,
                small_instance_oracle=legacy_oracle)
            evidence_db.append(step, audit)
            if audit.hard_gate_passed:
                queue.push(step, step_ranker.score(step, audit))
        task = queue.pop()
        # kind 별 결정론적 실행: encoding 차등검증 / generator_family 열거+정확 검증 /
        # pruning_rule recall 보존 검증 / performance_claim 고정 benchmark
        ...
        state = rebuild_state_from_verified_evidence()
    return NoCertifiedWitnessWithinBudget()
```

## 16. 성공 정의

LLM 이 좋은 가설을 내놓는지와 무관하게: 기존 witness 판정을 다른 수학적 표현으로
정확히 재현하고, 모든 재배향에 대한 obstruction 을 독립 검증 가능한 certificate 로
출력하며, 그 정확성과 성능을 객관적으로 측정할 수 있는 상태.
