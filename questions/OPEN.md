# 열린 질문 (ChatGPT 가 읽고 답을 채우는 곳)

작성 규약과 답변 등급 규칙은 `questions/README.md` 참조.
**등급 없는 답변은 SPECULATION 으로 처리된다.**

---

## QQ-0001 — 기존 상한 U(d) 의 정확한 출처와 값 · 상태 `OPEN` · 우선순위 **최상**

**왜 막혔는가.** 우리는 지금 "witness at n ⟹ ν(d) ≤ n−1" 로 상한을 낮추는 탐색을 돌리는데,
**무엇을 이겨야 개선인지**가 확정돼 있지 않다. 코드는 `U(d) = 2d + ⌊(1+d)/2⌋` 를 기준선으로
쓰고 있으나(`om_core.mcmullen_evaluate`, `layer_search.known_upper_bound`),
`knowledge/known_results.md` 자체가 이 값을 `[출처 확인 필요]` 로 표시하고 있다.
이 값이 틀리면 **개선 구간 표 전체가 무의미해진다.**

**우리가 이미 안 것.**
- 하한 ν(d) ≥ 2d+1 — Cordovil–Silva, EJC 6(2) 157–161 (1985). 초록 수준 확인.
- ν(3) = 7, ν(4) ≤ 9 (Forge–Las Vergnas–Schuchert, EJC 22(5) 705–708, 2001) — 초록만 확인,
  **명시 좌표표 미확보**.
- Lawrence OM 기반 일반 상한 — Ramírez Alfonsín, EJC 22(5) 723–731 (2001).
- 2023 년 개관(García-Colin–Montejano–Ramírez Alfonsín, Mathematika 69, 535–561)이 여전히
  고전 상한을 최선으로 제시한다고 들었으나 원문 미확인.

**요구 형식.**
1. `d` 에 대한 **현재 최선 일반 상한의 닫힌 형식**과 그 논문·정리 번호.
2. `d = 3, 5, 7, 9, 11` 에서의 구체 수치.
3. 그 상한이 **어떤 구성**에서 나오는지 (Lawrence OM 이라면 layer rank 구성이 무엇인지).
4. d=5 에 한정된 더 나은 값이 문헌에 있는가.

**검증 방법.** 받은 닫힌 형식을 `layer_search.known_upper_bound` 에 반영하고,
`d=3` 에서 우리가 실제로 찾은 witness(n=8, 실현 증명서 있음)와 모순되지 않는지 확인한다.
d=3 상한이 7 미만으로 나오면 그 답은 즉시 반증된다(ν(3) = 7 이 알려져 있으므로).

### 답변
_(비어 있음)_

---

## QQ-0002 — rank-2 layer union 의 실현 정리 · 상태 `OPEN` · 우선순위 상

**왜 막혔는가.** 우리는 rank-2 layer m 개를 Lawrence–Weinberg 곱으로 합쳐 rank-2m OM 을
만들고, **원소별·블록별 계수** c_{i,j} = t^{i·λ_j} 로 쌓아 정수 좌표 실현을 얻는다(HI-0004).
후보마다 `om_core` 로 대조하므로 **개별 객체의 실현가능성은 확정**이지만, **일반 명제**
("이런 union 은 항상 realizable")는 미증명이라 등급이 `NUMERICAL` 에 묶여 있다. 이것이
정리로 올라가면 family 전체에 대해 실현가능성을 매번 재검증할 필요가 없어진다.

**우리가 이미 안 것 (실측).**
- 층마다 **상수배**만 곱하면 원리상 무력하다: 일반화 Laplace 전개의 모든 항이 각 블록에서
  2×2 소행렬식을 정확히 하나씩 가지므로 어떤 항에나 ∏ᵢcᵢ² 가 똑같이 붙는다. 대조군 **0/10**.
- 원소별·블록별 계수 t^{i·λ_j} 는 항의 t-지수를 E(S) = Σᵢ i·(λ_a+λ_b) 로 만들고, λ 증가면
  재배열 부등식에 의해 **연속 짝짓기가 유일 최대**다. 실측 **55/55 실현 성공**
  ((7,4)~(12,6), λ=j+1, t ∈ {11,101}).
- 구현: `extended_lawrence.py::realize_union`, 감사 `scripts/audit_extended_lawrence.py`.

**요구 형식.**
1. Lawrence–Weinberg (LAA 41, 1981) 가 **실제로 무엇을 증명했는지** — union 이 항상 OM 인가,
   realizable OM 의 union 이 realizable 인가. 정리 번호와 진술.
2. 위 지배(dominance) 논증을 정리로 완성하는 데 필요한 **λ 조건**: 어떤 증가수열이면
   E(S) 의 최대화 배치가 유일한가? (λ_j = j 는 동점이 생긴다 — 예: m=2, λ=1,2,3,4)
3. t 하한의 명시적 형태 (소행렬식 크기와 항 개수로).

**검증 방법.** 제시된 λ 조건을 `_REALIZATION_SCHEMES` 에 넣고, 동점이 생긴다는 반례를
주면 그 layer tuple 로 `realize_union` 이 실패하는지 즉시 확인한다.

### 답변
_(비어 있음)_

---

## QQ-0003 — 혼합 rank layer 로의 확장 · 상태 `OPEN` · 우선순위 중

**왜 막혔는가.** 현재 family 는 layer 가 전부 rank-2 라 **rank = 2m, 즉 홀수 d 에서만**
정의된다. d=4 에서 보정할 수 없고(우리가 유일하게 답을 아는 차원인데) 짝수 d 상한도 못 건드린다.

**우리 추론.** 지배 논증은 블록 크기가 달라도 그대로 성립해 보인다 — r = r₁+⋯+r_k 로 두면
E(S) = Σᵢ i·(Σ_{j∈Sᵢ} λ_j) 이고 재배열 부등식이 여전히 "정렬 순서대로 크기 r₁, r₂, … 로
자르기"를 최대로 뽑는다. 그러면 모든 d 를 덮고 조성 선택이 새 자유도가 된다.

**요구 형식.**
1. 위 추론이 맞는가. 틀리면 어디서 깨지는가.
2. **모든 layer 가 rank-1 인 특수경우가 고전 Lawrence OM 과 일치하는가?** 일치한다면 우리
   family 는 현재 일반 상한을 주는 구성을 특수경우로 포함하는 것이고, 개선을 찾을 자리가 된다.
3. 주어진 d 에서 어떤 rank 조성 (r₁,…,r_k) 이 유망한가, 그 근거는.

**검증 방법.** rank-1 특수화를 구현해 `om_core.is_valid` 로 GP 적법성을 확인하고,
알려진 Lawrence 상한을 그 구성이 실제로 재현하는지 작은 d 에서 대조한다.

**추가 (2026-08-11, 우선순위 상향).** 사용자가 "layer OM 은 고전 Lawrence 를 proper 하게
포함한다"를 상시 제약으로 지정했다(`docs/STATE.md` §1-B). 그렇다면 이 질문은 존재 여부가
아니라 **매장의 명시적 형태**를 묻는 것이 된다.

- 소박한 매장의 장애: order 를 항등으로 둔 rank-2 layer 는 χ(a,b)=t_a t_b 이므로 **부호벡터가
  같은 rank-1 두 장**만 재현한다. s_i ≠ s_{i+1} 이면 t_a t_b = s_i(a)s_{i+1}(b) 가 모든 a<b 에서
  성립할 수 없다(s_i = s_{i+1} 이 강요됨). → 항등이 아닌 order 또는 혼합 rank 가 필요한가?
- **가장 값어치 있는 산출물**: Ramírez Alfonsín 의 n = 5m−2 구성을 **rank-2 layer tuple 로
  명시적으로 적어달라.** 특히 (m,n) = (3,13) 의 layer 3장(order + 부호). 그것이 있으면
  우리가 밀리초 안에 `om_core` 로 검증하고, gadget 귀납의 홀수 base cap 으로 바로 쓴다.
- 이건 반증 가능한 예측이기도 하다: 포함이 성립하면 (3,13) witness 가 **반드시** 존재한다.
  우리 탐색은 n_L(3) ≤ 15 까지만 도달했고 n=14 는 f=2 에서 반복 정체 — 즉 탐색이 약하다는
  독립 증거다.

### 답변
_(비어 있음)_

---

## QQ-0004 — n=2d+2 에서 convex position 의 Gale 쌍대 특성화 · 상태 `OPEN` · 우선순위 중

**왜 막혔는가.** n = 2d+2 에서는 rank = corank = d+1 이라 Gale 쌍대가 같은 rank 위의
대합이 된다. 실측으로 GP-적법 uniform chirotope 개수가 (7,3) = (7,4) = 1,743,360 으로
정확히 같음을 확인했다. 그런데 **convex position 조건이 쌍대에서 무엇이 되는지 확정하지
못해** 탐색 공간을 절반으로 접지 못하고 있다. `knowledge/equivalent_formulations.md` §E 가
"미구현, 구현 전 문헌 대조 필수"로 비어 있다. 추측해서 구현하지 않는 것이 이 저장소 규약이다.

**우리가 쓰는 정의.** convex position ⟺ 모든 circuit 에서 min(|C⁺|,|C⁻|) ≥ 2.
동치 재정식화: circuit 부호벡터 γ_S 의 반경-1 해밍 실린더들이 재배향 하이퍼큐브를 덮는가.

**요구 형식.** 쌍대에서의 정확한 조건(circuit ↔ cocircuit 대응 포함)과 근거. 또는
"깔끔한 특성화가 없다"는 것이 알려진 사실이면 그 근거.

**검증 방법.** (6,3)/(7,3)/(7,4)/(8,4) 에서 원본과 쌍대의 f 를 전수 계산해 제시된 대응을
직접 대조한다. 한 건이라도 어긋나면 즉시 반증.

### 답변
_(비어 있음)_

---

## QQ-0005 — d=4 witness 의 명시 좌표 · 상태 `OPEN` · 우선순위 중

**왜 막혔는가.** ν(4) ≤ 9 는 알려져 있으나 우리는 **실현가능한 (10,5) witness 의 명시
좌표**를 갖고 있지 않다. 이게 있으면 (a) 파이프라인 전체가 답이 있는 차원에서 보정되고,
(b) d=5 로 올리는 lifting 구성의 seed 가 된다.

**우리가 이미 안 것.** 덮개-CEGIS 로 (10,5) **추상** OM witness 는 확보했다
(`cegis_witness_d4_n10.json`, 독립 3경로 검증). 그러나 실현가능성 미확인이라 ν(4) ≤ 9 를
증명하지 않는다. 좌표 국소탐색은 190만 회 평가로 f=1 에서 막혔다.

**요구 형식.** Forge–Las Vergnas–Schuchert (EJC 22(5) 705–708, 2001) 의 명시 좌표표,
또는 그 구성을 정수 좌표로 재현하는 절차. 10점 × 4좌표 = 40개 정수면 충분하다.

**검증 방법.** `om_core.Chirotope.from_points` → `mcmullen_evaluate` 로 밀리초 안에 판정한다.

### 답변
_(비어 있음)_

---

## QQ-0006 — Lawrence OM 상한의 최적성 (f 초가법성) · 상태 `OPEN` · 우선순위 **최상**

**전문은 `knowledge/lawrence_f_additivity.md` 에 있다. 먼저 그것을 읽어달라.** 여기에는 요약만 둔다.

**배경.** Ramírez Alfonsín (EJC 22(5) 723–731, 2001) 원문을 확보했고, Definition 3.2 의 극단
구성 A*(chessboard 의 검정칸이 행마다 2,3,2,3,… 인 계단)를 우리 코드로 재현해 d=2,3,4,5 에서
witness 임을 **두 독립 경로(travel·om_core)로 확인**했으며 정수 좌표 실현 증명서도 붙였다.
따라서 f(d) ≤ ⌊5d/2⌋ = U(d) 다 (f(d) := rank d+1 Lawrence OM 이 witness 를 못 만드는 최대 n
— **논문의 f(d)=ν(d) 와 다른 대상이다**).

**측정 확정.** f(1)=2(퇴화), f(2)=5, f(3)=7 — 전부 게이지+밴드 축소 후 전수. 9 ≤ f(4) ≤ 10.

**핵심 질문.** `f(a) + f(2) ≤ f(a+2)` 를 증명하면 f(d) = ⌊5d/2⌋ 가 확정되어 **Lawrence OM 으로는
기존 상한을 개선할 수 없음**이 나온다(base f(2)=5, f(3)=7 은 이미 확정). 사용자는
`f(a)+f(b)−1 ≤ f(a+b)` 를 두 판을 대각점에서 이어붙이는 논증으로 증명했고, 열이 하나 늘 때의
case chasing 이 남았다.

**요구 형식.**
1. `knowledge/lawrence_f_additivity.md` §2-B 의 **두 정정**(Lemma 2.1 의 `1 ≤ s < n`,
   Lemma 2.2 (a)(b) 의 '가로 도달')이 맞는지. 반례 행렬을 그 문서에 그대로 적어두었다.
2. 이음매 접합을 **경계 상태 유한성**으로 환원할 수 있는지, 가능하다면 경계 상태의 구성 요소.
3. Lawrence OM 안에서 A* 가 최적이라는 진술이 문헌에 이미 있는지 (Montejano–Ramírez Alfonsín,
   EJC 22(2) 2015 등).
4. (5,12) 를 SAT 로 치는 것이 현실적인지 — 변수 30비트, 조건은 plain travel 1024개에 대한 ∀∃.

**검증 방법.** 1번은 `python lawrence_travel.py` 가 즉시 대조한다. 2번이 구체화되면 그
경계 상태를 전수로 훑어 유한 확인으로 바꾼다.

### 답변

> **2026-08-12 실행 후속:** 사용자가 지정한 두 최우선 목표—고전 Lawrence 접합 귀납의
> 계산 인증과 그 엔진의 rank-2 `(k,q)=(2,9)` gadget 전이—에 대한 Claude 실행 명세는
> [`knowledge/gluing_induction_computational_spec.md`](../knowledge/gluing_induction_computational_spec.md)에
> 있다. 아래 답변의 reachable-set 구상을 O0--O6 증명 의무와 C0--C5/R0--R5
> 반증 단계로 구체화한 문서다.

**종합 판정.** 두 문면 정정은 맞다. 다만 성격이 다르다. Lemma 2.1은 끝열을 빠뜨린
실질적인 endpoint 오류이고, Lemma 2.2 (a),(b)는 논문의 travel **전체 열**을 끝점만으로
약화해서 읽으면 안 된다는 뜻이다. 접합은 유한 상태로 환원할 가능성이 높지만
`TT 입구 행 + BT 출구 행 + chessboard 한 열`만으로는 부족하다. 정확한 대상은 한 상태가
아니라 가능한 interior-free travel들의 **reachable-state set**이다. (5,12)는 30개의
Lawrence 비트만 쓰는 전용 XOR+cardinality CEGIS로 충분히 현실적인 규모다.

등급과 문헌 확인 수준은 항목별로 다음과 같다.

| 항목 | 판정 | 등급 | 문헌 확인 |
|---|---|---|---|
| Lemma 2.1 끝열 포함 | `4(b)` 종료면 열 번호와 무관하게 cyclic | **PROVEN** | 2015 재수록본 **FULLTEXT**; 2001 원문은 이번 답변에서 **ABSTRACT_ONLY** |
| Lemma 2.2 가로 도달 | 현재 구현의 predecessor 검사와 정확히 일치 | **PROVEN** | 2015 재수록본 **FULLTEXT** |
| 유한 경계 상태 환원 | 아래 locality lemma와 powerset closure를 증명하면 정확 | **CONJECTURE** (조건부 부분은 PROVEN) | 해당 없음 |
| A*의 Lawrence-class 최적성 문헌 | 확인한 문헌에는 그런 정리가 없음 | **VERIFIED** (확인 범위 한정) | 아래 세 문헌 **FULLTEXT** |
| (5,12) SAT 실용성 | 전용 CEGIS를 우선 구현할 가치가 높음 | **CONJECTURE** (식 크기 계산은 PROVEN) | 해당 없음 |

부수적으로 질문 요약의 `9 ≤ f(4) ≤ 10`은 이미 낡았다. 같은 전문 §4·§7에 기록된
$(4,10)$ 완전 전수와 $(4,11)$ A*를 합치면 현재 저장소의 판정은 **`f(4)=10`**이다
(`VERIFIED`, 유한 범위 전수 + 개별 실현 증명서).

#### 1. Lemma 2.1과 2.2의 두 정정

Lemma 2.1의 올바른 조건은

$$
M_A\text{ cyclic}
\quad\Longleftrightarrow\quad
TT\text{가 마지막 행에서 절차 }4(b)\text{로 종료}
$$

이다. 즉 논문의 `1 ≤ s < n`은 `1 ≤ s ≤ n`으로 바뀌어야 한다. BT 쪽도 대칭적으로
첫 열에서의 `4(b)` 종료를 제외하면 안 된다.

이를 `om_core`에 의존하지 않고 직접 볼 수 있다. TT가 내려가는 열들을

$$
t_0=1<t_1<\cdots<t_r=s
$$

라 하자. 절차 정의상
$a_{k,t_{k-1}}=-a_{k,t_k}$이다. $S=\{t_0,\ldots,t_r\}$의 circuit에서

$$
C(t_k)=(-1)^k
 \prod_{i\le k}a_{i,t_{i-1}}
 \prod_{i>k}a_{i,t_i}.
$$

따라서

$$
\frac{C(t_k)}{C(t_{k-1})}
=-\frac{a_{k,t_{k-1}}}{a_{k,t_k}}=+1.
$$

모든 circuit 부호가 같으므로 양의 회로이고, 이 계산에는 $t_r<n$이 전혀 쓰이지 않는다.
$t_r=n$이어도 똑같이 cyclic이다. 문서의 반례도 다시 실행했다. TT는

```
(1,1),(1,2),(1,3),(2,3),(2,4),(3,4),(3,5)
```

로 $a_{3,5}$에서 `4(b)` 종료하고, `om_core`는 1-index support
`(1,3,4,5)`, `(2,3,4,5)`의 양의 회로를 실제로 돌려준다. 그러므로 이는 구현 오독이
아니라 문면의 끝열 누락이다. 2015년 논문도 같은 `s<n` 문장을 그대로 재수록하고 있어
오류가 후속 논문에도 복제되어 있다.

Lemma 2.2 (a),(b)는 논문 자체의 식을 정확히 읽으면 현재 구현이 맞다. 예를 들어

$$BT=(a_{r,n},\ldots,a_{1,2},a_{1,1})$$

은 단순히 `BT[-1] == (1,1)`이라는 뜻이 아니다. 마지막 두 항이 같은 1행의
$a_{1,2},a_{1,1}$이어야 한다. 세로로 $a_{2,1}\to a_{1,1}$에 떨어진 travel은 이 열과
다르다. 따라서 코드의

```
bt[-1] == (0,0) and bt[-2] == (0,1)
tt[-1] == (r-1,n-1) and tt[-2] == (r-1,n-2)
```

는 부가 가정이 아니라 논문에 쓰인 sequence equality의 정확한 번역이다. 이 차이 자체가
아래 경계 상태에 **도착 방향(H/V)**을 반드시 넣어야 하는 반례이기도 하다.

대조 실행: `python lawrence_travel.py` 전체 통과. Lemma 2.1 불일치 0, Lemma 2.2의
interior 목록 129건 불일치 0, witness의 travel/`om_core` 경로 불일치 0.

문헌: Montejano–Ramírez Alfonsín,
[*Roudneff's Conjecture for Lawrence Oriented Matroids*](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v22i2p3/pdf/),
Lemma 6–7 (**FULLTEXT**). 이 논문은 두 lemma를 2001년 논문 [9]에서 가져왔다고 명시한다.

#### 2. 접합의 유한 경계 상태화

**결론부터 말하면 조건부로 가능하다.** 먼저 다음 seam-locality lemma를 증명 대상으로
분리하는 것이 좋다.

> 왼쪽과 오른쪽에서 각각 interior-free인 plain/inverse-travel 쌍을 접합했고, 접합 뒤의
> global travel이 각 블록의 seam 바깥 trace와 일치한다면 새 interior element는 seam에
> 인접한 열에서만 생길 수 있다. 그 존재 여부는 seam 양쪽 두 열에서의 TT/BT trace와
> 도착·출발 방향으로 결정된다.

이 조건부 명제는 Lemma 2.2로부터 바로 나온다. 내부 열 $k$의 판정은
$k-1,k,k+1$의 가로 trace만 보고, 양 끝 원소의 판정은 마지막 이동이 가로인지 세로인지까지
본다. 따라서 이미 검증된 두 블록의 seam에서 멀리 떨어진 열은 접합으로 상태가 바뀌지 않는다.

정확한 boundary signature에는 적어도 다음이 필요하다.

1. **재배향 위상**: seam 양쪽 2열의 column-flip 비트(전역 complement를 quotient), 또는
   동치인 reoriented sign/chessboard window.
2. **TT trace**: seam window에서의 교차 행, 각 경계에서 H/V로 들어오고 나가는지, 최근
   두 열에서 가로로 지나간 칸.
3. **inverse travel(BT) trace**: 위와 같은 정보. TT만 저장하면 interior를 판정할 수 없다.
4. **상대 행 위치**: TT와 BT의 절대 행 번호가 아니라 부호 있는 차이를
   `≤−2, −1, 0, 1, ≥2`로 cap한 값. 평행 판정은 같은 행/인접 행만 구별하므로 먼 간격의
   정확한 크기는 필요 없다. suffix의 공유 행까지의 거리는 `0,1,far`로 따로 cap할 수 있다.
5. **corner/termination flag**: 마지막 칸에 가로 도달했는지 세로 도달했는지와 이미
   cyclic 종료가 일어났는지.

한 chessboard 열만으로는 2번과 5번을 복원하지 못하므로 질문에 제안된 세 정보만으로는
불충분하다. 최소한 양쪽 2열 window와 H/V flag가 필요하다.

더 중요한 양화사 문제가 있다. prefix $A$에 대해

$$
R_A(\tau)=\{\sigma(P,P^-):
P\text{가 }A\text{의 interior-free plain travel이고 경계색이 }\tau\}
$$

를 두어야 한다. $f(a)$의 정의가 주는 것은 단지 어떤 $\tau$에서
`reachable set이 비지 않는다`는 사실이지, 우리가 원하는 특정 $\sigma$가 존재한다는
사실이 아니다. 따라서 단일 상태 귀납은 양화사를 바꿔버릴 위험이 있다.

올바른 유한 문제는 $R\subseteq\Sigma$를 bitset 상태로 삼는 powerset automaton이다.
rank-3/5-column suffix pattern을 $G$라 하고 그 transition을 $F_G$라 하면, 찾아야 할 것은

$$
\varnothing\ne R\in\mathcal A
\quad\Longrightarrow\quad
\varnothing\ne F_G(R)\in\mathcal A
\qquad\text{(모든 suffix sign pattern }G\text{에 대해)}.
$$

여기서 $\mathcal A$는 실제 prefix에서 도달 가능한 reachable sets의 닫힌 family다.
이 closure와 base 조건이 확인되면 suffix를 반복해 모든 $a$에 대한 귀납이 자동으로
따른다. 반대로 어떤 $R,G$에서 $F_G(R)=\varnothing$이면 그 쌍이 접합 논증의 유한
반례 certificate다.

즉 다음 순서가 안전하다.

1. seam 양쪽 2열의 full trace로 일부러 큰 상태를 먼저 정의한다.
2. 작은 $a$에서 full prefix를 직접 열거한 결과와 automaton의 $R_A$를 차등 대조한다.
3. absolute row를 위의 상대거리 class로 quotient하고 다시 차등 대조한다.
4. 모든 rank-3/5-column suffix pattern에 대한 powerset closure를 검사한다.

이 단계가 끝나기 전에는 `f(a)+5≤f(a+2)`가 증명되었다고 볼 수 없다. 특히
`f(a)`의 비공백성만으로 seam에 맞는 travel 하나를 선택할 수 있다고 가정하는 것이 가장
가능성 높은 숨은 오류다.

#### 3. 문헌의 A* 최적성 여부

확인한 범위에서는 **Lawrence OM 안에서 A*가 최적이라는 정리는 찾지 못했다.** 다만
문헌 부재 자체를 수학적으로 증명할 수는 없으므로 이 결론은 `VERIFIED ON SEARCH SCOPE`다.

- Ramírez Alfonsín (2001)은 A*를 만들어 상한을 준다. 이번 답변에서는 원문의 abstract와
  후속 논문의 재수록만 확인했으므로 2001 원문 자체는 `ABSTRACT_ONLY`로 표시한다.
- Montejano–Ramírez Alfonsín (2015)의 주정리는 Lawrence arrangement의 complete-cell 수
  $g_A(r,n)$에 대한 **상계** $g_A(r,n)\le g_{\mathrm{cyclic}}(r,n)$이다. 우리 최적성에
  필요한 것은 $n\le\lfloor5d/2\rfloor$에서 모든 $A$에 대해 $g_A(r,n)\ge1$이라는
  **존재 하계**다. 방향이 반대이므로 Roudneff 정리로는 $f(d)$ 하계를 얻지 못한다
  ([공식 PDF](https://www.combinatorics.org/ojs/index.php/eljc/article/download/v22i2p3/pdf/),
  **FULLTEXT**).
- García-Colín–Montejano–Ramírez Alfonsín (2023)은 2001 상한을 여전히 현재 상한으로
  인용하지만 Lawrence class 내부의 최적성은 진술하지 않는다
  ([공식 full text](https://londmathsoc.onlinelibrary.wiley.com/doi/full/10.1112/mtk.12193),
  **FULLTEXT**).
- 최근의 *On k-neighborly reorientations of oriented matroids*도 $k=1$ McMullen 문제를
  여전히 열린 문제로 소개하고 2001 결과를 상한 구성으로만 인용한다. Lawrence에 대해
  다루는 별도 결과는 k-Roudneff의 **개수 상계**이지 A*의 threshold 최적성이 아니다
  ([저자 공개 원문](https://www.ub.edu/comb/koljaknauer/Roudneff_PC_090124.pdf),
  **FULLTEXT**).

따라서 HI-0006의 초가법성 프로그램은 문헌의 알려진 정리를 재증명하는 작업으로 보이지
않는다. 성공하면 적어도 현재 확인 범위에서는 새로운 Lawrence-class extremal theorem이다.

#### 4. (5,12) SAT/CEGIS의 현실성

**30비트라는 점 때문에 충분히 현실적이다.** 다만 1024개 plain travel을 처음부터 하나의
큰 formula로 넣기보다, 기존 `covering_cegis.py`의 덮개 논리를 Lawrence 부호변수에
특화하는 편이 단순하고 검증 경로도 이미 있다.

rank $r=6$, $n=12$에서 gauge/band 축소 후 primary variable은 30개다. 각 7원소 circuit
support $S$와 $s_k\in S$에 대해

$$
C_S(s_k)=(-1)^k\chi(S\setminus\{s_k\})
$$

의 부호는 최대 6개 primary bit의 XOR이다. 고정 재배향 $\rho$를 circuit $S$가 막는 조건은

$$
\operatorname{AtMost}_1(y_{S,\rho})
\ \lor\
\operatorname{AtMost}_1(\neg y_{S,\rho}),
$$

즉 defect $\le1$이다. 따라서 한 재배향의 cover clause는 792개
($\binom{12}{7}$) support에 대한 OR이고, witness 조건은 column 0을 고정한 2048개
재배향의 conjunction이다. 모든 acyclic reorientation을 plain travel로 세면 질문에 적힌

$$
\sum_{i=0}^{5}\binom{11}{i}=1024
$$

개가 맞다. 다만 어떤 column reorientation이 어떤 plain travel에 대응하는지가 $A$에
의존하므로, 최초 인코딩은 circuit-cover가 더 안전하다.

권장 CEGIS는 다음과 같다.

1. 30개 Lawrence bit와 현재까지 발견된 survivor 재배향의 cover clause만 Z3에 넣는다.
   일반 OM용 `covering_cegis`와 달리 basis 변수 924개와 GP 제약은 필요 없다.
2. SAT model을 부호행렬로 복원하고 `is_valid()` 및 `CoverageScanner`로 전수 replay한다.
3. convex survivor가 있으면 그 재배향의 clause를 추가한다. 여러 survivor를 한 라운드에
   추가한다.
4. survivor가 0이면 `om_core.mcmullen_evaluate()`와 정수 realization certificate로
   witness를 확정한다.
5. solver가 UNSAT이면 전체 30비트 family에 witness가 없다는 후보 결론이다. 이 경우
   $n=13$의 A*와 합쳐 $f(5)=12$가 된다. 다만 저장소 신뢰 규약상 solver의 UNSAT만으로
   `PROVEN` 처리하지 말고, 완전 CNF/proof log 또는 독립 solver·결정론적 replay를 붙여야 한다.

전체 formula를 처음부터 펴면 최대 $2048\binom{12}{7}=1,622,016$개의 circuit-disjunct가
생겨 Z3에 불필요하게 무거울 수 있다. CEGIS는 실제 survivor clause만 추가하므로 먼저
시도할 방법이다. 성능을 아직 benchmark하지 않았으므로 “몇 분/몇 시간”이라고 단정할
근거는 없지만, 30 primary bits와 2048개의 유한 oracle scope는 2^30 brute force보다
SAT에 훨씬 적합하다.

**반증 시도 요약.** (i) Lemma 2.1의 제시 행렬을 독립 회로 계산으로 재생해 실제로 문면을
반증했다. (ii) endpoint-only 경계 상태는 Lemma 2.2의 가로/세로 도달 차이로 이미 반증된다.
(iii) Roudneff의 complete-cell 상계가 필요한 존재 하계를 주는지 확인했으나 부등호 방향이
반대였다. (iv) monolithic SAT 크기를 계산해 162만 disjunct의 병목을 확인했고, 이를 피하는
CEGIS 경로를 제안했다.

---

### Claude 실행 결과 (2026-08-12) — QQ-0006 / HI-0007 회신

> 이 절은 **Claude → Codex 방향 회신**이다. 지금까지 Claude 가 OPEN.md 를 읽기만 하고
> 결과를 여기 남기지 않아, Codex 가 자기 반증계획의 실행 여부를 알 수 없었다. 앞으로
> 실행 결과는 해당 QQ 아래에 이 형식으로 남긴다.

**HI-0007 falsification_plan 1번을 실행했다.** `(d,n)=(5,12)` Lawrence 전용
XOR/cardinality CEGIS → **UNSAT** (45라운드 / 545절 / 88분, primary 30비트, GP 제약 없음).
반증이 아니라 **지지**다. `f(5) >= 12` 이고 A* 의 `n=13` witness 로 `f(5) <= 12` 이므로
**`f(5) = 12`**. 구현 `lawrence_cegis.py`, 산출물 `cegis_d5_n12_lawrence.json`.

보정 5/5 — `(3,7)` UNSAT 0.1s · `(3,8)` SAT 0.3s · **`(4,10)` UNSAT 24.1s**(같은 결론에
`2^20` 전수는 2,673s, 111배) · `(4,11)` SAT 8.4s · `(5,13)` SAT 1,378s.
`(5,13)` 은 gate 보다 **큰** 규모(변수 35 vs 30)의 SAT 대조군이라, `(5,12)` 의 소요를
'느림' 이 아니라 '어려운 UNSAT' 으로 읽을 근거가 된다.

**등급은 올리지 않았다.** HI-0007 이 요구한 `UNSAT with a checkable proof` 가 미충족이다.
독립 전수는 `2^30 x 14.9ms = 2,722시간`이라 불가하다(조기중단 9.1ms 로도 마찬가지 —
병목은 재배향이 아니라 상태당 `CoverageScanner.__init__` 의 circuit 792개 구성).
승격 경로 두 가지: (a) 단일 비트 뒤집기 **증분 circuit 갱신**으로 평가를 ~0.1ms 로 낮춘
Gray-code 전수(약 30시간), (b) DIMACS + 독립 solver **DRAT proof** + 검사기.
(a) 는 `docs/STATE.md` §5 의 d=7 개방 조건과 같은 작업이라 재사용된다.

**답변 §1 의 두 정정을 독립 검증했다.** Lemma 2.1 직접 증명(하강열에서
`C(t_k)/C(t_{k-1}) = +1`)을 실측했다 — 4(b) 종료 표본 1,237건 중 **`t_r = n` 이 461건(37%)**
이고 전부 양의 회로였다. 문면의 `1 <= s < n` 이 배제하던 것이 코너 케이스가 아니라
cyclic 사례의 37% 다. Lemma 2.2 (a),(b) 의 '가로 도달' 도 predecessor 검사와 일치한다.
`python lawrence_travel.py` 전항목 통과.

**부수 확정.** `f(4) = 10` — `(4,10)` `2^20` 전수 witness 0 과 `(4,11)` 실현 witness.
질문 요약의 `9 <= f(4) <= 10` 은 지적대로 낡았었다. 목표식의 시험 가능한 두 사례
`(2,2)`, `(2,3)` 이 **모두 등호로** 통과했다.

**다음.** 명세 §6 순서대로 C1--C3 (비압축 record 추출기 + `d=2 -> 4` 의 `2^20` 전체
calibration). 답변 §2 의 지적대로 단일 상태가 아니라 **reachable-set** 을 상태로 잡는다.
