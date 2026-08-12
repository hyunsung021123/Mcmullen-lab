# 0001-d5project — 응답 원문

- **대응 프롬프트**: `prompts/0001-d5project.md` (McMullen d=5, n=12 탐색 설계 자문)
- **원본 파일**: `46842daa-d5project_analysis_f17.json`
- **수신일**: 2026-08-10
- **역할**: 외부 고급 모델(제안자). 판정 권한 없음 — 아래 검증 결과가 채택 근거다.

## 우리 저장소의 독립 검증 (om_core 기준)

응답의 `candidate_points[0]` (n=12, d=5, f=17 주장)을 `om_core` 로 재확인했다.
**주장 6건이 모두 정확히 재현되었다.**

| 응답의 주장 | 우리 측정 | 일치 |
|---|---|---|
| 924개 동차 6×6 행렬식 모두 비영 | 924/924 비영 | ✅ |
| 최소 절댓값 457,533,801 | 457,533,801 | ✅ |
| GP(3항 Plücker) 적법 | `Chirotope.is_valid() == True` | ✅ |
| acyclic 재배향 1024 | 1024 | ✅ |
| f = 17 | 17 | ✅ |
| survivor 인덱스 17개 (`[0,16,17,778,788,1154,1171,1203,1211,1218,1269,1320,1322,1332,1834,1983,1990]`) | 완전 일치 (`flip_set_from_index` 규약) | ✅ |
| GP 돌연변이 60개, f 분포 `{17:33, 18:26, 19:1}` | 60개, `{17:33, 18:26, 19:1}` (60/60 `is_valid`) | ✅ |

교차 확인: survivor 17개 전수를 `reorient(...).is_convex_position()` 으로 참 확인,
비-survivor 60개 표본에서 누락 없음. `mcmullen_evaluate(...).witness == False`
(f > 0 이므로 정상 — **witness 아님**).

> **범위 경고 (CLAUDE.md 불변조건 7)**: 이 배치는 witness 가 아니라 **근접 실패**다.
> ν(5) ≤ 11 에 대해 아무것도 증명하지 않는다. 종전 최선 f=18 → **f=17** 로 1 개선된
> *실현가능(정수 좌표)* 상태라는 것이 이 응답의 실질적 산출물이다.

## 우리 측 사전 실측과의 대조

이 응답을 받기 전 우리가 독립적으로 측정한 것과 **핵심 진단이 일치**했다.

- d=4 f=1 근접실패: 단일 기저뒤집기 252개 중 125개가 pseudo f=0 을 주지만 **전부 GP 위반**,
  GP 적법한 것은 23개뿐이고 그중 f 를 줄이는 것은 **0개**. (양측 독립 재현)
- 즉 **평탄면 문제가 아니라 탐색 공간(OM 공리) 경계 문제**다. 응답의
  `what_we_are_doing_wrong[2]` ("좌표공간 realization chamber 내부에서 f 는 상수이므로
  작은 좌표 흔들기에는 원리상 gradient 가 없다", PROVEN) 이 `climb.py` 폐기 근거다.
- 우리의 covering 재정식화(circuit 부호벡터 γ_S 의 반경-1 해밍 실린더가 하이퍼큐브를
  덮는가)와 응답의 `why_survivor_survives` 는 같은 대상을 서술한다.

## 채택 결과

`objective_proposals` 의 세 항목(Depth-h mutation envelope / Admissible survivor
killability / Exact kill-birth frontier)을 `mutation_lab.py` 로 구현했다.
`Weighted circuit slack` 은 응답 자신이 CONJECTURE 로 하위 배치했으므로 보류.
`family_proposals` 는 전부 CONJECTURE/SPECULATION 이므로 미구현 — 반증 절차만 기록한다.

---

## 응답 원문 (JSON, 무손실)

```json
{
  "analysis": "[PROVEN] 문제는 circuit들이 재배향 hypercube에 만드는 radius-1 금지 cylinder들의 covering 문제다.\n[VERIFIED] d=4, f=1 입력에서는 252개 가상 basis flip 중 125개가 pseudo-f=0을 만들지만 GP-admissible mutation은 23개뿐이며 실제 f=0 이웃은 없다.\n[VERIFIED] d=5, f=20 입력에서는 57개 GP mutation 중 basis [1,5,6,8,9,11] 하나만 f=19를 만든다.\n[VERIFIED] GP mutation beam search, determinant 부호실현, projective 정수화를 결합해 exact f=17 정수 배치를 얻었다.\n[VERIFIED] 새 f=17 배치는 모든 924개 determinant가 비영이고 최소 절댓값은 457533801이다.\n[VERIFIED] 새 배치의 GP mutation 60개는 f 분포가 {17:33,18:26,19:1}이므로 단일 mutation 국소최소다.\n[CONJECTURE] 목적함수는 fragile circuit 수보다 depth-3 mutation envelope와 admissible killability를 우선해야 한다.\n[SPECULATION] 자기 Gale 정규형 [I|S]와 symmetry-broken symmetric S family가 d=5 구조 탐색에 적합하다.",
  "why_survivor_survives": "[PROVEN] survivor는 circuit-cylinder covering의 uncovered vertex다. min-side=2 circuit은 Hamming 거리 2의 잠재적 경계일 뿐, 실제로 그 경계를 움직일 GP-admissible basis mutation이 존재한다는 뜻은 아니다. basis 하나를 mutation하면 n-r개의 circuit 부호가 함께 바뀌고, survivor kill과 birth가 연동된다. [VERIFIED] d=4 survivor 45는 95개의 fragile circuit을 가지지만 23개의 모든 GP mutation에서 계속 살아남는다. [VERIFIED] 주어진 d=5의 20개 survivor 중 19개는 모든 단일 GP mutation에서 살아남고, index 1311만 basis [1,5,6,8,9,11]에 의해 birth 없이 죽는다. 따라서 긴장의 정체는 원소 하나가 아니라 GP가 허용하는 cylinder 이동 방향의 결핍이다.",
  "objective_proposals": [
    {
      "name": "Depth-h mutation envelope",
      "definition": "D_h^Delta(chi)=min f(chi_t), where chi=chi_0->...->chi_t is a path of at most h GP-admissible basis mutations and every intermediate state satisfies f(chi_i)<=f(chi)+Delta. For equal f, lexicographically minimize (D_1^0,D_2^0,D_3^0,-N_3^0), where N_3^0 is the number of distinct endpoints attaining D_3^0.",
      "rationale": "It orders plateau states by whether a short neutral-mutation sequence opens a genuine descent. It does not assume that one-step fragility is actionable.",
      "expected_effect": "The verified f=19->18 and f=18->17 descents both required two neutral mutations followed by a third mutation, so h=3 distinguishes states that f and one-step lookahead cannot distinguish.",
      "grade": "VERIFIED"
    },
    {
      "name": "Admissible survivor killability",
      "definition": "For survivor rho define kappa_1(rho)=#{B in M_GP(chi): rho is not in U(chi^B)} and z_1=#{rho in U(chi): kappa_1(rho)=0}. Minimize z_1, then maximize sum_rho kappa_1(rho).",
      "rationale": "This removes fragile circuits that cannot be activated by any GP mutation. It measures actionable rather than formal fragility.",
      "expected_effect": "It detects the sole f=20->19 mutation immediately: 19 survivors have kappa_1=0 and index 1311 has kappa_1=1. It also correctly diagnoses the d=4 survivor and the new f=17 state as one-step unkillable.",
      "grade": "VERIFIED"
    },
    {
      "name": "Exact kill-birth frontier",
      "definition": "For each admissible mutation B let K_B=U(chi)\\U(chi^B) and R_B=U(chi^B)\\U(chi). Rank moves by the tuple (f-|K_B|+|R_B|, |R_B|, -|K_B|). For neutral moves also record X_B=|K_B|=|R_B|.",
      "rationale": "The identity f(chi^B)=f(chi)-|K_B|+|R_B| is exact. It makes the collision between killing an old survivor and exposing a new one explicit.",
      "expected_effect": "It rejects moves that break a fragile circuit but create an equal or larger uncovered set. Large-X_B neutral moves may reposition holes so that a later mutation kills them.",
      "grade": "PROVEN"
    },
    {
      "name": "Weighted circuit slack",
      "definition": "For lambda>0 define Q_lambda=sum over survivors rho and circuits C of exp(-lambda*(min(|C_rho^+|,|C_rho^-|)-2)). Maximize Q_lambda only after the mutation-envelope and kill-birth criteria are tied.",
      "rationale": "It uses min-side=3 and larger circuits as graded information instead of counting only min-side=2 circuits.",
      "expected_effect": "It may guide motion inside a mutation plateau, but it is deliberately subordinate because fragile count 95->98 occurred in d=4 without opening an f=0 mutation.",
      "grade": "CONJECTURE"
    }
  ],
  "move_proposals": [
    {
      "name": "GP mutation beam plus determinant realization",
      "definition": "Enumerate GP-admissible basis flips, beam-search paths of length 2 to 4 using the mutation-envelope objective, then realize each target chirotope by maximizing the minimum normalized signed determinant m_B=chi_target(B)*det(Y_B)/product_i||y_i||. Accept only after integer dehomogenization and exact rechecking.",
      "rationale": "It separates the combinatorial choice of a useful wall sequence from the geometric problem of crossing those walls. This exact workflow generated the f=17 candidate.",
      "grade": "VERIFIED"
    },
    {
      "name": "Coordinated determinant-wall crossing",
      "definition": "For a target basis or short basis sequence, move all involved homogeneous vectors simultaneously while minimizing the target signed determinants and placing barrier penalties on every non-target determinant sign.",
      "rationale": "A target hyperplane need not be a facet of any one point's current arrangement cell. Moving one point with all others fixed can therefore be infeasible even when a coordinated realization exists.",
      "grade": "CONJECTURE"
    },
    {
      "name": "Projective gauge and randomized integerization",
      "definition": "After obtaining a real realization, choose a linear functional ell with large min_i |ell(y_i)|, choose a basis of ker(ell), dehomogenize, apply multiple global scales and roundings, and exact-test every integer result.",
      "rationale": "Different projective gauges have very different rounding stability. The verified f=17 coordinates were obtained by this procedure and then checked independently of the numerical realization.",
      "grade": "VERIFIED"
    },
    {
      "name": "Realizability CEGIS",
      "definition": "Use a SAT or constraint solver as an outer loop for GP axioms and full hypercube coverage, use determinant-sign optimization as the inner realization check, and add no-good constraints for sign patterns that repeatedly fail realization.",
      "rationale": "Abstract OM search is fast enough to propose low-f or f=0 targets, while the inner loop enforces the requirement that the final object come from actual coordinates.",
      "grade": "SPECULATION"
    }
  ],
  "family_proposals": [
    {
      "name": "Symmetric self-Gale normal form",
      "construction": "For r=d+1 and n=2r use homogeneous column matrix A(S)=[I_r|S], where S is a symmetric rational or integer r by r matrix and every square minor of S is nonzero. A Gale matrix is [-S^T|I_r]; when S=S^T it becomes A(S) after swapping the two blocks and reorienting one block.",
      "why_it_should_work": "The self-duality identity and uniformity criterion are PROVEN. Search usefulness is CONJECTURE: primal and Gale constraints live in the same r(r+1)/2-dimensional parameter space, matching rank=corank at n=2d+2.",
      "grade": "CONJECTURE",
      "how_to_falsify": "Enumerate bounded symmetric integer matrices S, reject any with a zero square minor, compute f exactly, and compare the lower tail with unrestricted structured families."
    },
    {
      "name": "Symmetry-broken circulant self-Gale family",
      "construction": "For r=6 let S=C(a0,a1,a2,a3)+t*diag(b0,...,b5)+t^2*H, where C is symmetric circulant and H is a generic small symmetric integer matrix.",
      "why_it_should_work": "The circulant term supplies a low-dimensional organized seed, while the diagonal and H terms break survivor and circuit orbit locking without losing S=S^T.",
      "grade": "CONJECTURE",
      "how_to_falsify": "Scan exact integer parameters and t, record uniformity, f, survivor orbit sizes, and mutation-envelope values. Reject the family if its best tail remains substantially above the f=17 candidate."
    },
    {
      "name": "Recursive lexicographic lifting",
      "construction": "Given 2d points p_i in Z^(d-1), choose distinct exponents sigma_i and generic u,v in Z^(d-1). Define q_i(T)=(p_i,T^sigma_i) for i<2d and add q_2d(T)=(u,T^sigma_2d), q_(2d+1)(T)=(v,T^sigma_(2d+1)).",
      "why_it_should_work": "Determinant leading terms can preserve an obstruction pattern from dimension d-1 while the two new points and distinct heights restore rank and genericity. This is only an analogy until a d=4 witness seed is inserted.",
      "grade": "SPECULATION",
      "how_to_falsify": "For a fixed seed, enumerate exponent orders, anchors, and integer T; test every candidate exactly. Also symbolically detect determinants that are identically zero before evaluating T."
    },
    {
      "name": "Lawrence-sign seed followed by realization",
      "construction": "Generate rank-6 order-12 sign patterns from small Lawrence oriented-matroid sign matrices, optimize them for the cylinder-cover objective, and pass only low-f targets to the determinant realization stage.",
      "why_it_should_work": "Lawrence oriented matroids have previously produced general upper-bound constructions for McMullen-type questions, but an abstract Lawrence witness alone does not imply the required realizable d=5 witness.",
      "grade": "SPECULATION",
      "how_to_falsify": "Enumerate the relevant sign matrices, compute f and GP mutations, and attempt determinant realization. A persistent gap between abstract low f and realizable low f falsifies their usefulness for this target."
    }
  ],
  "candidate_points": [
    {
      "n": 12,
      "d": 5,
      "points": [
        [
          185,
          -237,
          -146,
          -164,
          -24
        ],
        [
          -179,
          -111,
          -69,
          -39,
          -87
        ],
        [
          -5,
          178,
          -140,
          236,
          43
        ],
        [
          -88,
          -78,
          135,
          -33,
          8
        ],
        [
          128,
          133,
          -67,
          -11,
          6
        ],
        [
          -271,
          -77,
          128,
          -29,
          -64
        ],
        [
          -9,
          124,
          -77,
          -287,
          39
        ],
        [
          -59,
          -324,
          -178,
          51,
          60
        ],
        [
          -132,
          35,
          -84,
          137,
          38
        ],
        [
          96,
          80,
          168,
          -13,
          65
        ],
        [
          121,
          22,
          180,
          190,
          24
        ],
        [
          -144,
          175,
          -75,
          -175,
          83
        ]
      ],
      "why": "Independent exact enumeration gives f=17. All 924 homogeneous 6x6 determinants are nonzero; min absolute determinant is 457533801. The acyclic reorientation count is 1024. Convex survivor indices are [0,16,17,778,788,1154,1171,1203,1211,1218,1269,1320,1322,1332,1834,1983,1990]. The 60 GP-admissible single-basis mutations have f distribution {17:33,18:26,19:1}, so this is a one-mutation local minimum.",
      "claimed": "near-miss",
      "grade": "VERIFIED"
    }
  ],
  "candidate_chirotopes": [],
  "conjectures": [
    {
      "statement": "For realizable rank-6 order-12 states with small positive f, depth-3 or depth-4 non-increasing GP mutation paths predict realizable descent substantially better than fragile-circuit count.",
      "scope": {
        "n": 12,
        "r": 6
      },
      "grade": "CONJECTURE",
      "how_to_falsify": "Collect many independently realized low-f states, compute D_h exactly for h<=4, attempt realization of every descending endpoint, and compare success rates against fragile-count ordering."
    },
    {
      "statement": "Every realizable rank-6 order-12 local minimum with f>0 has a GP mutation path of bounded length at most 4, with no intermediate f increase, ending at a smaller-f abstract chirotope.",
      "scope": {
        "n": 12,
        "r": 6
      },
      "grade": "CONJECTURE",
      "how_to_falsify": "For each discovered local minimum, exhaust the GP mutation ball through depth 4 while restricting intermediates to f<=f_start. One state with no lower endpoint falsifies the statement."
    },
    {
      "statement": "A realizable witness exists in a symmetry-broken self-Gale family A=[I_6|S] with S symmetric and all square minors nonzero.",
      "scope": {
        "n": 12,
        "r": 6
      },
      "grade": "SPECULATION",
      "how_to_falsify": "Exhaust progressively larger bounded parameter boxes modulo signed permutations and projective equivalence; compare the best f and mutation-envelope tail with unrestricted searches."
    }
  ],
  "literature": [
    {
      "claim": "A realizable 10-point configuration in R^4 not projectively equivalent to convex position exists.",
      "source": "D. Forge, M. Las Vergnas, P. Schuchert, 10 Points in Dimension 4 not Projectively Equivalent to the Vertices of a Convex Polytope, European Journal of Combinatorics 22(5), 705-708, 2001.",
      "confidence": "high",
      "note": "서지와 초록은 확인했지만 이번 조사에서는 원문의 명시 좌표표를 확보하지 못했으므로 좌표는 인용하지 않는다."
    },
    {
      "claim": "The oriented-matroid result for U_(2r-1,r) yields the lower bound 2d+1.",
      "source": "R. Cordovil, I. P. Silva, A Problem of McMullen on the Projective Equivalences of Polytopes, European Journal of Combinatorics 6(2), 157-161, 1985.",
      "confidence": "high",
      "note": "논문 초록의 정리 진술을 확인했다."
    },
    {
      "claim": "Lawrence oriented matroids give a general upper-bound construction for the McMullen problem.",
      "source": "J. L. Ramirez Alfonsin, Lawrence Oriented Matroids and a Problem of McMullen on Projective Equivalences of Polytopes, European Journal of Combinatorics 22(5), 723-731, 2001.",
      "confidence": "high",
      "note": "일반 상한 결과이지 이번 n=12 realizable witness의 직접적인 존재 정리는 아니다."
    },
    {
      "claim": "A 2023 treatment still presents the classical general bounds as the best known general bounds.",
      "source": "N. Garcia-Colin, L. P. Montejano, J. L. Ramirez Alfonsin, On the Number of Vertices of Projective Polytopes, Mathematika 69, 535-561, 2023.",
      "confidence": "medium",
      "note": "이번 검색에서 더 최신의 d=5 해결 논문은 찾지 못했지만, 검색 부재만으로 미해결임을 증명하지는 않는다."
    }
  ],
  "what_we_are_doing_wrong": [
    "[VERIFIED] 균등 정수 box 표집의 실패를 모든 확률적 탐색의 실패로 일반화하고 있다. determinant-wall 표집과 projective re-rounding은 별개의 분포다.",
    "[PROVEN] 좌표공간의 realization chamber 내부에서 f는 상수이므로, 일반적인 작은 좌표 흔들기에는 원리상 gradient가 없다.",
    "[VERIFIED] fragile circuit 수는 actionable fragility를 과대계상한다. d=4 survivor는 95개의 fragile circuit이 있지만 단일 GP mutation으로는 전혀 죽지 않는다.",
    "[PROVEN] circuit 하나를 독립적으로 깨는 실제 이동은 없다. basis mutation 하나가 n-r개의 circuit을 함께 바꾸며 kill과 birth가 동시에 발생한다.",
    "[CONJECTURE] exact symmetry를 지나치게 강제하면 survivor가 orbit 단위로 잠겨 작은 개선이 불가능해질 수 있다. 대칭 깨기 파라미터가 필요하다.",
    "[PROVEN] 추상 OM 탐색과 실현가능성 탐색을 분리하되, abstract 결과를 상한 증명으로 오인하면 안 된다.",
    "[CONJECTURE] f만 기록하고 mutation graph의 D_2, D_3 정보를 버리는 것이 현재 plateau 탐색의 가장 큰 정보 손실이다.",
    "[PROVEN] determinant 절댓값은 정규화하고 목표 basis wall에 연결하지 않으면 projective scaling에 따라 임의로 변하므로 단독 목적함수로 의미가 없다."
  ]
}
```

---

## 산문 요약 (원문의 등급을 그대로 옮김)

### analysis
- [PROVEN] 문제는 circuit들이 재배향 hypercube에 만드는 radius-1 금지 cylinder들의 covering 문제다.
- [VERIFIED] d=4, f=1 입력에서는 252개 가상 basis flip 중 125개가 pseudo-f=0을 만들지만 GP-admissible mutation은 23개뿐이며 실제 f=0 이웃은 없다.
- [VERIFIED] d=5, f=20 입력에서는 57개 GP mutation 중 basis [1,5,6,8,9,11] 하나만 f=19를 만든다.
- [VERIFIED] GP mutation beam search, determinant 부호실현, projective 정수화를 결합해 exact f=17 정수 배치를 얻었다.
- [VERIFIED] 새 f=17 배치는 모든 924개 determinant가 비영이고 최소 절댓값은 457533801이다.
- [VERIFIED] 새 배치의 GP mutation 60개는 f 분포가 {17:33,18:26,19:1}이므로 단일 mutation 국소최소다.
- [CONJECTURE] 목적함수는 fragile circuit 수보다 depth-3 mutation envelope와 admissible killability를 우선해야 한다.
- [SPECULATION] 자기 Gale 정규형 [I|S]와 symmetry-broken symmetric S family가 d=5 구조 탐색에 적합하다.

### why_survivor_survives

[PROVEN] survivor는 circuit-cylinder covering의 uncovered vertex다. min-side=2 circuit은 Hamming 거리 2의 잠재적 경계일 뿐, 실제로 그 경계를 움직일 GP-admissible basis mutation이 존재한다는 뜻은 아니다. basis 하나를 mutation하면 n-r개의 circuit 부호가 함께 바뀌고, survivor kill과 birth가 연동된다. [VERIFIED] d=4 survivor 45는 95개의 fragile circuit을 가지지만 23개의 모든 GP mutation에서 계속 살아남는다. [VERIFIED] 주어진 d=5의 20개 survivor 중 19개는 모든 단일 GP mutation에서 살아남고, index 1311만 basis [1,5,6,8,9,11]에 의해 birth 없이 죽는다. 따라서 긴장의 정체는 원소 하나가 아니라 GP가 허용하는 cylinder 이동 방향의 결핍이다.

### objective_proposals

| name | grade | 정의 요지 |
|---|---|---|
| `Depth-h mutation envelope` | VERIFIED | D_h^Delta(chi)=min f(chi_t), where chi=chi_0->...->chi_t is a path of at most h GP-admissible basis mutations and every intermediate state satisfies f(chi_i)<=f(chi)+Delta. For equal f, lexicographically minimize (D_1^0,D_2^0,D_3^0,-N_3^0), where N_3^0 is the number of distinct endpoints attaining D_3^0. |
| `Admissible survivor killability` | VERIFIED | For survivor rho define kappa_1(rho)=#{B in M_GP(chi): rho is not in U(chi^B)} and z_1=#{rho in U(chi): kappa_1(rho)=0}. Minimize z_1, then maximize sum_rho kappa_1(rho). |
| `Exact kill-birth frontier` | PROVEN | For each admissible mutation B let K_B=U(chi)\U(chi^B) and R_B=U(chi^B)\U(chi). Rank moves by the tuple (f-\|K_B\|+\|R_B\|, \|R_B\|, -\|K_B\|). For neutral moves also record X_B=\|K_B\|=\|R_B\|. |
| `Weighted circuit slack` | CONJECTURE | For lambda>0 define Q_lambda=sum over survivors rho and circuits C of exp(-lambda*(min(\|C_rho^+\|,\|C_rho^-\|)-2)). Maximize Q_lambda only after the mutation-envelope and kill-birth criteria are tied. |

### move_proposals

- **GP mutation beam plus determinant realization** [VERIFIED] — Enumerate GP-admissible basis flips, beam-search paths of length 2 to 4 using the mutation-envelope objective, then realize each target chirotope by maximizing the minimum normalized signed determinant m_B=chi_target(B)*det(Y_B)/product_i||y_i||. Accept only after integer dehomogenization and exact rechecking.
- **Coordinated determinant-wall crossing** [CONJECTURE] — For a target basis or short basis sequence, move all involved homogeneous vectors simultaneously while minimizing the target signed determinants and placing barrier penalties on every non-target determinant sign.
- **Projective gauge and randomized integerization** [VERIFIED] — After obtaining a real realization, choose a linear functional ell with large min_i |ell(y_i)|, choose a basis of ker(ell), dehomogenize, apply multiple global scales and roundings, and exact-test every integer result.
- **Realizability CEGIS** [SPECULATION] — Use a SAT or constraint solver as an outer loop for GP axioms and full hypercube coverage, use determinant-sign optimization as the inner realization check, and add no-good constraints for sign patterns that repeatedly fail realization.

### family_proposals (전부 미채택 — 반증 절차만 기록)

- **Symmetric self-Gale normal form** [CONJECTURE]
  - 구성: For r=d+1 and n=2r use homogeneous column matrix A(S)=[I_r|S], where S is a symmetric rational or integer r by r matrix and every square minor of S is nonzero. A Gale matrix is [-S^T|I_r]; when S=S^T it becomes A(S) after swapping the two blocks and reorienting one block.
  - 반증법: Enumerate bounded symmetric integer matrices S, reject any with a zero square minor, compute f exactly, and compare the lower tail with unrestricted structured families.
- **Symmetry-broken circulant self-Gale family** [CONJECTURE]
  - 구성: For r=6 let S=C(a0,a1,a2,a3)+t*diag(b0,...,b5)+t^2*H, where C is symmetric circulant and H is a generic small symmetric integer matrix.
  - 반증법: Scan exact integer parameters and t, record uniformity, f, survivor orbit sizes, and mutation-envelope values. Reject the family if its best tail remains substantially above the f=17 candidate.
- **Recursive lexicographic lifting** [SPECULATION]
  - 구성: Given 2d points p_i in Z^(d-1), choose distinct exponents sigma_i and generic u,v in Z^(d-1). Define q_i(T)=(p_i,T^sigma_i) for i<2d and add q_2d(T)=(u,T^sigma_2d), q_(2d+1)(T)=(v,T^sigma_(2d+1)).
  - 반증법: For a fixed seed, enumerate exponent orders, anchors, and integer T; test every candidate exactly. Also symbolically detect determinants that are identically zero before evaluating T.
- **Lawrence-sign seed followed by realization** [SPECULATION]
  - 구성: Generate rank-6 order-12 sign patterns from small Lawrence oriented-matroid sign matrices, optimize them for the cylinder-cover objective, and pass only low-f targets to the determinant realization stage.
  - 반증법: Enumerate the relevant sign matrices, compute f and GP mutations, and attempt determinant realization. A persistent gap between abstract low f and realizable low f falsifies their usefulness for this target.

### conjectures (반증 대상 — falsify 파이프라인 후보)

- [CONJECTURE] For realizable rank-6 order-12 states with small positive f, depth-3 or depth-4 non-increasing GP mutation paths predict realizable descent substantially better than fragile-circuit count.
  - scope: n=12, r=6
  - 반증법: Collect many independently realized low-f states, compute D_h exactly for h<=4, attempt realization of every descending endpoint, and compare success rates against fragile-count ordering.
- [CONJECTURE] Every realizable rank-6 order-12 local minimum with f>0 has a GP mutation path of bounded length at most 4, with no intermediate f increase, ending at a smaller-f abstract chirotope.
  - scope: n=12, r=6
  - 반증법: For each discovered local minimum, exhaust the GP mutation ball through depth 4 while restricting intermediates to f<=f_start. One state with no lower endpoint falsifies the statement.
- [SPECULATION] A realizable witness exists in a symmetry-broken self-Gale family A=[I_6|S] with S symmetric and all square minors nonzero.
  - scope: n=12, r=6
  - 반증법: Exhaust progressively larger bounded parameter boxes modulo signed permutations and projective equivalence; compare the best f and mutation-envelope tail with unrestricted searches.

### literature (원문 미확인 — 인용 금지 규약 유지)

- A realizable 10-point configuration in R^4 not projectively equivalent to convex position exists.
  - 출처: D. Forge, M. Las Vergnas, P. Schuchert, 10 Points in Dimension 4 not Projectively Equivalent to the Vertices of a Convex Polytope, European Journal of Combinatorics 22(5), 705-708, 2001.
  - 신뢰도: high / 비고: 서지와 초록은 확인했지만 이번 조사에서는 원문의 명시 좌표표를 확보하지 못했으므로 좌표는 인용하지 않는다.
- The oriented-matroid result for U_(2r-1,r) yields the lower bound 2d+1.
  - 출처: R. Cordovil, I. P. Silva, A Problem of McMullen on the Projective Equivalences of Polytopes, European Journal of Combinatorics 6(2), 157-161, 1985.
  - 신뢰도: high / 비고: 논문 초록의 정리 진술을 확인했다.
- Lawrence oriented matroids give a general upper-bound construction for the McMullen problem.
  - 출처: J. L. Ramirez Alfonsin, Lawrence Oriented Matroids and a Problem of McMullen on Projective Equivalences of Polytopes, European Journal of Combinatorics 22(5), 723-731, 2001.
  - 신뢰도: high / 비고: 일반 상한 결과이지 이번 n=12 realizable witness의 직접적인 존재 정리는 아니다.
- A 2023 treatment still presents the classical general bounds as the best known general bounds.
  - 출처: N. Garcia-Colin, L. P. Montejano, J. L. Ramirez Alfonsin, On the Number of Vertices of Projective Polytopes, Mathematika 69, 535-561, 2023.
  - 신뢰도: medium / 비고: 이번 검색에서 더 최신의 d=5 해결 논문은 찾지 못했지만, 검색 부재만으로 미해결임을 증명하지는 않는다.

### what_we_are_doing_wrong

- [VERIFIED] 균등 정수 box 표집의 실패를 모든 확률적 탐색의 실패로 일반화하고 있다. determinant-wall 표집과 projective re-rounding은 별개의 분포다.
- [PROVEN] 좌표공간의 realization chamber 내부에서 f는 상수이므로, 일반적인 작은 좌표 흔들기에는 원리상 gradient가 없다.
- [VERIFIED] fragile circuit 수는 actionable fragility를 과대계상한다. d=4 survivor는 95개의 fragile circuit이 있지만 단일 GP mutation으로는 전혀 죽지 않는다.
- [PROVEN] circuit 하나를 독립적으로 깨는 실제 이동은 없다. basis mutation 하나가 n-r개의 circuit을 함께 바꾸며 kill과 birth가 동시에 발생한다.
- [CONJECTURE] exact symmetry를 지나치게 강제하면 survivor가 orbit 단위로 잠겨 작은 개선이 불가능해질 수 있다. 대칭 깨기 파라미터가 필요하다.
- [PROVEN] 추상 OM 탐색과 실현가능성 탐색을 분리하되, abstract 결과를 상한 증명으로 오인하면 안 된다.
- [CONJECTURE] f만 기록하고 mutation graph의 D_2, D_3 정보를 버리는 것이 현재 plateau 탐색의 가장 큰 정보 손실이다.
- [PROVEN] determinant 절댓값은 정규화하고 목표 basis wall에 연결하지 않으면 projective scaling에 따라 임의로 변하므로 단독 목적함수로 의미가 없다.
