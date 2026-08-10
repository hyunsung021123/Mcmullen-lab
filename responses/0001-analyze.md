# 0001 분석 응답

## 결론

이번 표본에서 가장 중요한 사실은 개별 회로가 덮는 재배향 수가 아니라, 회로들이 만드는 나쁜 재배향 집합들의 **겹침 구조**가 witness 여부를 결정한다는 점이다. uniform rank `r`에서 각 circuit support의 크기는 `r+1`이고, 한 circuit이 convexity를 깨뜨리는 상대 부호 패턴은 전부 같은 부호인 1개와 singleton인 `r+1`개, 합계 `r+2`개다. 따라서 각 circuit은 정확히 `(r+2)·2^(n-r-1)`개의 재배향을 덮는다. 이 값과 전체 incidence 합은 같은 `(n,r)`의 모든 OM에서 동일하다.

특히 목표 `(n,r)=(12,6)`에서는 재배향이 `2^11=2048`개, circuit이 `C(12,7)=792`개이며, 각 circuit은 정확히 `8·2^5=256`개 상태를 덮는다. 전체 obstruction incidence는 `792·256=202752`, 상태당 평균 obstruction multiplicity는 정확히 `99`다. 따라서 `num_singleton_circuits` 같은 한 대표원소의 주변 통계보다, 792개 고정 크기 부분집합이 2048개 상태를 얼마나 균등하게 덮는지와 그 교집합 구조가 본질적이다.

## 구조적 설명

`num_tope_pairs=16`은 `(6,3)` 표본의 우연한 공통점이 아니다. uniform OM의 tope 수는 underlying uniform matroid에 의해 정해지고, tope 쌍의 수는

`sum_{i=0}^{r-1} C(n-1,i)`

이다. 삭제-축약 recurrence와 경계값에 대한 귀납으로 이 식을 얻으며, `(6,3)`에서는 `1+5+10=16`이다. 그러므로 witness와 near-miss가 모두 16인 것은 분류 신호가 아니다. `convex_tope_ratio=1/16=0.0625`도 near-miss에서 `num_convex_reorientations=1`이므로 생기는 정의적 결과다.

`min_circuit_balance==1 -> acyclic`과 `min_circuit_balance==1 -> not convex`는 `(6,3)`에서만 전수 확인된 경험칙이 아니라 정의에서 바로 나오는 전역 명제다. uniform OM에서는 `acyclic`이 정확히 모든 circuit balance가 1 이상이라는 뜻이고, `convex_position`은 정확히 모든 circuit balance가 2 이상이라는 뜻이다. 따라서 이 항목들을 `EXHAUSTED_ON_SCOPE`로만 표현하면 오히려 논리적 지위를 낮춰 보이게 한다.

마찬가지로 witness이면 현재 대표원소가 convex일 수 없다는 필요조건은 빈 재배향도 허용된다는 사실의 즉각적인 귀결이다. 이는 올바르지만 witness의 새로운 구조를 설명하지 않는다. `num_halving_cocircuits>=4 -> not convex`는 `(7,3)` 첫 확장 대상에서 이미 깨졌으므로 일반화 후보에서 제외해야 한다. 자기쌍대 rank인 `n=2r`도 dual의 convexity 조건을 별도로 증명하지 않는 한 witness의 쌍대 대칭을 뜻하지 않는다.

## 새 상관량과 추가 반증 실험

두 circuit의 support가 정확히 두 원소에서 만날 때, 공통 원소 두 곳에서 circuit 부호가 한 곳에서는 같고 다른 한 곳에서는 다른지를 센 `two_overlap_circuit_disagreement_count`를 제안한다. circuit 전체 부호를 뒤집으면 `같음 0회`와 `같음 2회`만 교환되고 `같음 1회`는 그대로다. 재배향은 공통 원소에서 두 circuit 부호에 같은 인자를 곱하므로 같음/다름 관계를 보존한다. 재명명은 회로쌍을 순열할 뿐이다. 따라서 이 양은 재명명 및 재배향 불변이다.

샌드박스 심사에서 300개 표본 전체에 대해 예외 없이 결정적으로 계산됐고, 값이 3종류로 비상수였으며, 최대 실측 비용은 약 0.15 ms였다. 재명명과 재배향 각각 12개 표본 검사에서도 반례가 없었다.

추가로 `(6,3)`의 전역 부호 고정 대표계 11,904개를 `dedup=False`로 다시 전수 열거했다. 값별 `(nonwitness, witness)`는 다음과 같았다.

- 15: `(0, 384)`
- 18: `(1920, 3840)`
- 19: `(0, 5760)`

따라서 `(6,3)`에서 값이 18이 아니면 witness라는 명제는 이 유한 범위에서 `VERIFIED`다. 값 18은 필요조건일 뿐 충분조건은 아니다.

`(7,3)`의 DFS 앞 3,000개를 별도로 공격했을 때 값은 122, 126, 128, 130, 132였고, 39개의 nonwitness는 모두 126에서만 나왔다. 그러나 이 표본은 전수가 아니며 DFS 순서 편향도 있으므로, `값 != 126 -> witness`는 `CONJECTURE`로만 제출한다.

## d=5 탐색 전략

첫째, 실제 `ν(5)` 상한을 위해서는 처음부터 `realizable_uniform`만 주 탐색 대상으로 삼아야 한다. 추상 OM witness는 별도의 조합론적 결과일 뿐 원래 문제를 닫지 못한다.

둘째, 12개의 RP5 점 가운데 일반위치의 7점을 projective frame으로 고정해 PGL(6) 자유도를 제거한다. 예를 들어 여섯 좌표점과 `[1:1:1:1:1:1]`을 고정하고 나머지 다섯 점만 유리수 또는 작은 정수 동차좌표로 움직인다. 각 후보는 정수 determinant로 chirotope를 만들면 실현가능성과 부호의 정확성이 동시에 보장된다. 점별 projective scaling도 정규화하면 실제 탐색 변수 수를 더 줄일 수 있다.

셋째, fitness는 대표원소의 singleton 수가 아니라 exact coverage에 둔다. 1차 목적은 `num_convex_reorientations` 최소화, 2차 목적은 obstruction multiplicity의 하위 분위수와 최솟값 최대화, 3차 목적은 pair-overlap energy `sum_x C(m(x),2)` 최소화로 잡는 것이 자연스럽다. 총 incidence와 평균 99는 상수이므로, 낮은 multiplicity 또는 0인 상태를 없애려면 불필요한 중첩을 줄여야 한다. 현재 bitmask coverage 엔진은 2048개 상태를 직접 다룰 수 있으므로 이 평가는 chirotope 생성보다 훨씬 싸다.

넷째, 좌표의 한 항목을 작게 바꾸는 local move, 좌표 교환, 부호 반전과 작은 정수 mutation을 사용한 다중 시작 탐색을 수행한다. 각 단계에서 uniformity를 exact determinant로 확인하고, canonical key 또는 재배향 불변 signature로 중복을 제거한다. near-miss를 발견하면 유일한 uncovered 재배향을 깨는 방향으로 좌표 변이를 집중하는 CEGIS식 피드백을 적용한다.

다섯째, 알려진 `(10,5)` 실현 witness에서 realizability-preserving lift 또는 suspension으로 `(12,6)` 후보를 만드는 계열은 보조 후보족으로 시험할 가치가 있다. 다만 이 연산이 no-convex-reorientation을 보존한다는 정리는 현재 없으므로 `SPECULATION`이다. 원 논문은 10점의 4차원 obstruction을 제공하지만, 일반 상계는 `d=5`의 목표 `ν(5)<=11`을 바로 주지 않는다: [Forge–Las Vergnas–Schuchert의 10점 구성](https://www.lri.fr/~forge/10point.pdf), [Ramírez Alfonsín의 Lawrence OM 상계](https://doi.org/10.1006/eujc.2000.0492).

## 불변량 폐기 제안

`reorientation_symmetry_order`는 목표 uniform 범위 `1<=r<n`에서 항상 1이다. 실제로 재배향 부호를 `rho_e`라 하면 모든 basis `B`에 대해 `product_{e in B} rho_e=1`이어야 한다. 임의의 `i,j`에 대해 둘과 겹치지 않는 같은 `(r-1)`-집합을 붙인 두 basis를 비교하면 `rho_i=rho_j`이고, 원소 0을 고정한 gauge에서 모든 `rho_e=1`이다. 계산을 O(1)로 최적화한 것은 맞지만 정보량도 0이므로 기본 어휘에서는 폐기하는 편이 낫다.

```json
{
  "analysis": "같은 (n,r)에서 각 circuit이 덮는 나쁜 재배향 수와 전체 obstruction incidence는 상수이므로 witness 여부는 circuit별 개수가 아니라 나쁜 재배향 집합들의 교집합 구조에 달려 있다. (6,3)의 num_tope_pairs=16도 uniform matroid의 tope 공식으로 강제되는 상수라 분류력이 없다. 목표 (12,6)에서는 792개 circuit이 각각 256/2048 상태를 덮고 평균 obstruction multiplicity가 정확히 99이므로, uncovered 상태와 낮은 multiplicity 꼬리를 직접 최적화해야 한다. 실현가능한 projective-frame 좌표족에서 exact determinant와 coverage bitmask를 결합하는 탐색이 ν(5)에 직접 유효하다. 추상 OM 또는 검증되지 않은 dual/lift 보존 주장은 원래 ν(5) 상한으로 승격하지 않는다.",
  "new_invariants": [
    {
      "name": "two_overlap_circuit_disagreement_count",
      "description": "support 교집합이 정확히 두 원소인 circuit 쌍 중 공통 두 원소에서 상대 부호가 한 번만 일치하는 쌍의 수",
      "code": "def f(ch):\n    circuits = []\n    for S in combinations(range(ch.n), ch.r + 1):\n        circuits.append((set(S), ch.circuit(S)))\n    count = 0\n    for A, B in combinations(circuits, 2):\n        I = A[0].intersection(B[0])\n        if len(I) == 2:\n            same = sum(1 for x in I if A[1][x] == B[1][x])\n            if same == 1:\n                count += 1\n    return count",
      "why": "재배향은 공통 원소에서 두 circuit 부호를 동시에 바꾸므로 상대 부호는 보존되고, circuit의 전역 부호 선택도 '정확히 한 번 일치' 여부를 바꾸지 않는다. 특히 n=2r에서 두 (r+1)-support가 두 원소에서 만나면 합집합이 전 원소이므로, 이 값은 국소 obstruction들이 전체 재배향 큐브에서 어떻게 겹치는지를 포착하는 저비용 궤도 불변량이다."
    }
  ],
  "deprecate_invariants": [
    {
      "name": "reorientation_symmetry_order",
      "reason": "uniform이고 1<=r<n인 모든 목표 범위에서 원소 0 고정 gauge의 stabilizer는 항등 하나뿐이어서 값이 항상 1이다. 계산은 싸지만 정보량이 0이다."
    }
  ],
  "conjectures": [
    {
      "antecedent": [
        {
          "inv": "two_overlap_circuit_disagreement_count",
          "op": "!=",
          "value": 18
        }
      ],
      "consequent": {
        "inv": "witness",
        "op": "==",
        "value": true
      },
      "scope": {
        "n": 6,
        "r": 3
      },
      "statement": "rank 3, n=6에서 two-overlap circuit disagreement 수가 18이 아니면 witness이다.",
      "grade": "VERIFIED",
      "rationale": "전역 부호 고정 대표계 11,904개를 dedup=False로 전수 재검사했다. 값 15에는 witness 384/nonwitness 0, 값 18에는 witness 3840/nonwitness 1920, 값 19에는 witness 5760/nonwitness 0이었고 generator stats는 exhausted=true였다. 이는 해당 유한 범위의 전수 확인이지 일반 정리가 아니다."
    },
    {
      "antecedent": [
        {
          "inv": "two_overlap_circuit_disagreement_count",
          "op": "!=",
          "value": 126
        }
      ],
      "consequent": {
        "inv": "witness",
        "op": "==",
        "value": true
      },
      "scope": {
        "n": 7,
        "r": 3
      },
      "statement": "rank 3, n=7에서 two-overlap circuit disagreement 수가 126이 아니면 witness이다.",
      "grade": "CONJECTURE",
      "rationale": "DFS 순서의 3,000개 비전수 표본을 공격했다. 값 122,128,130,132에서는 모두 witness였고 39개의 nonwitness는 전부 값 126에서 나왔다. 값 126에도 witness 281개가 있어 역방향은 거짓이다. 표본이 비무작위이고 hit_candidate_cap=true이므로 약한 수치 근거일 뿐이며 더 큰 예산의 반증 탐색이 필요하다."
    }
  ],
  "candidate_chirotopes": [],
  "next_experiment": {
    "n": 12,
    "r": 6,
    "om_class": "realizable_uniform",
    "why": "ν(5)에 직접 기여하려면 실현가능성을 생성 단계에서 보장해야 한다. projective frame으로 7점을 고정한 작은 정수 좌표족에서 다중 시작 local search를 수행하고, num_convex_reorientations를 1차 목적, obstruction multiplicity의 낮은 꼬리와 pair-overlap energy를 2차 목적으로 사용한다. 모든 후보는 exact determinant와 mcmullen_evaluate/coverage certificate로 재검증한다."
  },
  "assessment": {
    "proven": [
      "uniform (n,r) OM의 tope 쌍 수는 sum_{i=0}^{r-1} C(n-1,i)이다. 삭제-축약 recurrence와 경계값에 대한 귀납으로 얻으며, 따라서 (6,3)의 값 16은 상수다.",
      "각 (r+1)-circuit은 정확히 (r+2)*2^(n-r-1)개의 재배향에서 balance 0 또는 1이 된다. 따라서 같은 (n,r)에서 전체 obstruction incidence는 상수이고 차이는 교집합 구조뿐이다.",
      "uniform OM에서 acyclic iff min_circuit_balance>=1이고 convex_position iff min_circuit_balance>=2이다. 따라서 min_circuit_balance==1이 acyclic이고 non-convex라는 두 함의는 범위 제한 없는 정의적 귀결이다.",
      "uniform 1<=r<n에서 원소 0을 고정한 순수 재배향 stabilizer는 항등 하나뿐이므로 reorientation_symmetry_order=1이다.",
      "two_overlap_circuit_disagreement_count는 circuit 전체 부호 선택, 재배향, 원소 재명명에 불변이다."
    ],
    "verified": [
      "(6,3) 전역 부호 고정 대표계 11,904개 전수에서 two_overlap_circuit_disagreement_count는 15,18,19만 나타났고 nonwitness는 값 18에서만 나타났다.",
      "저장소 보고 범위에서 (5,3)과 (6,4)에는 witness가 없고, (6,3)에는 witness가 있다. 이 문장은 해당 유한 열거 범위에만 한정된다.",
      "제안 불변량은 300개 코퍼스에서 totality, determinism, hashability, non-constancy, 비용 검사를 통과했고 재명명/재배향 표본 검사에서 반례가 없었다."
    ],
    "conjecture": [
      "(7,3)에서 two_overlap_circuit_disagreement_count!=126이면 witness이다. 현재 근거는 비전수 DFS 3,000개뿐이다.",
      "d=5에서 낮은 pair-overlap energy와 높은 최소 obstruction multiplicity를 동시에 갖는 실현가능 좌표족이 num_convex_reorientations=0에 도달할 수 있다."
    ],
    "speculation": [
      "알려진 (10,5) 실현 witness의 realizability-preserving lift 또는 suspension을 (12,6) 후보족으로 만들 수 있을 수 있으나 witness 보존은 증명되지 않았다.",
      "n=2r의 최소 support 교집합 circuit 쌍이 전체 ground set을 덮는다는 사실이 d=5 witness의 작은 구조적 기술을 제공할 수 있다."
    ]
  },
  "open_questions": [
    "coverage bitmask에서 obstruction multiplicity histogram과 pair-overlap energy를 캐시해 n=12 좌표 local search의 증분 fitness로 계산할 수 있는가?",
    "(7,3)에서 disagreement count 126이 nonwitness의 필요조건이라는 추측은 전수 열거에서도 살아남는가?",
    "알려진 (10,5) 실현 witness에 대해 rank를 하나, 원소를 둘 늘리는 구체적 좌표 lift가 존재하며 no-convex-reorientation을 보존하는가?",
    "projective-frame 정규화 뒤 남은 다섯 점의 좌표 범위를 어떤 유한 정수 상자로 제한해야 기존 near-miss OM들을 충분히 재현하는가?",
    "자기쌍대 rank에서 convex 재배향 부재를 dual cocircuit 조건으로 정확히 옮기는 정리가 있는가?"
  ]
}
```
