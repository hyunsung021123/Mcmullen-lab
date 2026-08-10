# rank-2 Lawrence union의 유한 gadget 귀납

> 상태: **연구 제안(CONJECTURE)**. 이 문서는 반복 가능한 gadget이 만족해야 할 정확한
> 조건과 그 조건에서 상계가 따라오는 귀납을 정리한다. 실제 \(9\)-column gadget, base cap,
> 일반 실현 정리는 아직 확보되지 않았다. 이 문서만으로 witness나 ν(d) 상계를 주장하지 않는다.

## 1. 목표와 신뢰 경계

홀수 \(d=2m-1\)에서 같은 ordered ground set 위의 uniform rank-2 layer

\[
M_0,M_1,\ldots,M_{m-1}
\]

를 Lawrence-Weinberg 방식으로 합친 rank-\(2m\) OM을 생각한다. 정렬된 basis
\(j_0<\cdots<j_{2m-1}\)에서 chirotope는

\[
\chi(j_0,\ldots,j_{2m-1})
=\prod_{i=0}^{m-1}\chi_i(j_{2i},j_{2i+1})
\tag{1}
\]

이다. 목표는 전체 차원마다 독립적으로 witness를 찾는 대신, 고정 크기의 block을 반복해
무한 family를 만드는 것이다.

이 문서에서 분리해야 하는 판정은 다음과 같다.

1. **조합적 gadget 조건**: 모든 재배향에서 defect \(\le1\)인 완성 circuit chain이 존재한다.
2. **OM 적법성**: 반복된 layer tuple이 uniform oriented matroid를 정의한다.
3. **실현가능성**: 반복 family가 실제 점배치에서 나온다.
4. **최종 판정**: 유한 후보는 반드시 `om_core.mcmullen_evaluate()`로 재검증한다.

1을 증명해도 2와 3이 자동으로 따라오지는 않는다. 특히 일반 실현 정리가 완성되기 전에는
각 유한 후보의 정수 realization certificate만 신뢰한다.

## 2. union circuit의 overlapping-triple 공식

최종 circuit support를

\[
S=\{s_0<s_1<\cdots<s_{2m}\}
\]

라 하자. chirotope가 정하는 circuit 부호를

\[
C_S(s_k)=(-1)^k\chi(S\setminus\{s_k\})
\tag{2}
\]

로 잡는다. 전역 부호 반전은 중요하지 않다.

각 \(i=0,\ldots,m-1\)에 대해

\[
u_i=
\prod_{j<i}\chi_j(s_{2j},s_{2j+1})
\prod_{j>i}\chi_j(s_{2j+1},s_{2j+2})
\]

라 두고 (1)을 (2)에 대입하면

\[
\begin{aligned}
C_S(s_{2i})&=u_i\chi_i(s_{2i+1},s_{2i+2}),\\
C_S(s_{2i+1})&=-u_i\chi_i(s_{2i},s_{2i+2}),\\
C_S(s_{2i+2})&=u_i\chi_i(s_{2i},s_{2i+1}).
\end{aligned}
\tag{3}
\]

따라서 \(C_S\)를 triple

\[
(s_0,s_1,s_2),(s_2,s_3,s_4),\ldots,
(s_{2m-2},s_{2m-1},s_{2m})
\tag{4}
\]

에 제한하면, 각각은 전역 scale \(u_i\)를 제외하고 layer \(M_i\)의 rank-2 circuit이다.
인접한 두 triple은 \(s_{2i+2}\) 하나를 공유하고 그곳의 부호가 일치한다.

반대로 증가하는 원소열 \(s_0<\cdots<s_{2m}\)과 부호열
\(z_0,\ldots,z_{2m}\)이 각 \(i\)에 대해

\[
(z_{2i},z_{2i+1},z_{2i+2})
=\lambda_i
\bigl(\chi_i(s_{2i+1},s_{2i+2}),
-\chi_i(s_{2i},s_{2i+2}),
\chi_i(s_{2i},s_{2i+1})\bigr)
\tag{5}
\]

를 만족하고 공유 endpoint의 부호가 일치하면, 이 부호열은 (2)의 circuit와 전역 부호를
제외하고 일치한다. 이후의 gadget 정의는 이 circuit-chain 표현만 사용한다.

## 3. 재배향 defect와 유한 boundary state

재배향을 \(\rho:E\to\{+1,-1\}\)라 하자. circuit \(C\)의 재배향 후 defect는

\[
\delta_\rho(C)=
\min\bigl(|C_\rho^+|,|C_\rho^-|\bigr)
\tag{6}
\]

이다. 재배향이 convex position이 아니기 위한 정확한 circuit obstruction은
\(\delta_\rho(C)\le1\)인 circuit의 존재다. \(\delta=0\)은 cyclic obstruction이고
\(\delta=1\)은 interior-element
obstruction이다.

부분 chain의 재배향 후 양·음 개수를 \(N_+,N_-\)라 하자. 미래의 성공 가능성을 판단할 때는

\[
a=\min(2,N_+),\qquad b=\min(2,N_-)
\tag{7}
\]

만 기억하면 충분하다. (a=b=2)가 되면 원소를 더 붙여도 defect가 다시 1 이하가 될 수
없으므로 이 상태는 `dead`다.

고정 크기 입력 port \(P\)를 두면 boundary state는

\[
\sigma=(p,\varepsilon,a,b)
\tag{8}
\]

로 잡을 수 있다.

- \(p\in P\): 현재 부분 chain의 마지막 endpoint
- \(\varepsilon\in\{+1,-1\}\): 재배향 전 circuit 부호 \(z(p)\)
- \(a,b\in\{0,1,2\}\): (7)의 capped counts
- \(a=b=2\)인 상태는 버린다

미래 transition은 이전에 고른 원소 전체가 아니라 (8)에만 의존한다. 전역 circuit 부호
반전을 quotient해 상태를 더 줄일 수 있지만, 정의와 최초 구현은 quotient 없이 시작하는
편이 안전하다.

## 4. 한 rank-2 layer의 정확한 transition

현재 endpoint가 \(x\), raw circuit 부호가 \(\varepsilon\)이고 \(x<y<z\)를 다음 triple로
고른다고 하자. layer chirotope를 \(\chi\)라 하면 표준 local circuit는

\[
D(x,y,z)=
(\chi(y,z),-\chi(x,z),\chi(x,y)).
\tag{9}
\]

첫 부호를 \(\varepsilon\)에 맞추는 scale은

\[
\lambda=\varepsilon\chi(y,z)
\]

이고, 새 raw signs는

\[
z(y)=-\lambda\chi(x,z),\qquad
z(z)=\lambda\chi(x,y).
\tag{10}
\]

\(\rho(y),\rho(z)\)를 곱해 두 새 effective signs를 얻고 (7)을 갱신한다. 공유 endpoint \(x\)는
이미 count에 들어 있으므로 다시 세지 않는다. 결과가 dead가 아니면 새 boundary state는

\[
(z,z(z),a',b')
\]

이다.

## 5. 반복 가능한 유한 gadget의 데이터

\((k,q)\)-gadget \(G\)는 layer \(k\)개와 ordered new block \(B\)의 원소 \(q\)개를 추가한다.
반복 가능성을 위해 다음 데이터가 모두 필요하다.

1. 고정된 finite input port \(P\)
2. 새 ordered block \(B\), \(|B|=q\), 모든 \(p\in P\)보다 뒤에 놓임
3. output port \(P'\subseteq B\), 다음 복사본의 input port와 정준적으로 식별됨
4. 새 rank-2 layers \(G_1,\ldots,G_k\)의 signed-permutation templates
5. 기존 layers에 \(B\)를 삽입하되 이전 ground-set restriction을 보존하는 extension rule
6. 새 layers의 \(P\cup B\) template를 과거 전체 ground set으로 확장하는 extension rule

마지막 두 조건이 없으면 작은 support 위의 pattern일 뿐, 반복 가능한 OM construction이 아니다.
rank 2에서는 signed permutation의 부분 template에 나머지 원소를 정해진 한쪽 끝으로
삽입하는 방식으로 coherent extension을 명시할 수 있다.

입구 상태 \(\sigma=(p,\varepsilon,a,b)\)에서 gadget 내부 chain은

\[
p=x_0<y_1<x_1<y_2<x_2<\cdots<y_k<x_k,
\qquad y_i,x_i\in B
\tag{11}
\]

형태다. 각 \(i\)에서 layer \(G_i\)와 공식 (10)을 적용한다. 마지막 \(x_k\in P'\)이고
중간에 dead가 되지 않은 모든 선택이 출력 상태를 만든다.

input-port coloring \(\tau:P\to\{\pm1\}\)와 new-block coloring
\(\alpha:B\to\{\pm1\}\)를 고정했을 때
가능한 출력 상태의 집합을

\[
T_{G,\tau,\alpha}(\sigma)
\tag{12}
\]

라 쓴다. (P,B,k,q)가 고정되어 있으므로 이 관계는 유한 전수검사 대상이다.

## 6. 두 가지 gadget closure 조건

### 6.1 상태별로 강한 충분조건

각 port coloring \(\tau\)에 대해 admissible state set \(A_\tau\)를 정한다. 다음 조건은 귀납에
충분하다.

\[
\forall\tau\ \forall\sigma\in A_\tau\ \forall\alpha
\quad
T_{G,\tau,\alpha}(\sigma)\cap A_{\tau'}\ne\varnothing,
\tag{G}
\]

여기서 \(\tau'\)는 \(\alpha\)를 output port \(P'\)에 제한한 coloring이다. 즉 어떤 admissible 입구
상태와 어떤 local reorientation에서도 적어도 하나의 admissible extension이 존재해야 한다.

### 6.2 정확한 powerset 조건

(G)는 필요 이상으로 강할 수 있다. 실제 prefix가 제공하는 것은 하나의 상태가 아니라 가능한
부분 chain들의 reachable set \(R\subseteq\Sigma_\tau\)다. gadget action을

\[
F_{G,\tau,\alpha}(R)
=\bigcup_{\sigma\in R}T_{G,\tau,\alpha}(\sigma)
\tag{13}
\]

로 둔다. 각 \(\tau\)에 대해 nonempty reachable sets의 finite collection

\[
\mathcal A_\tau\subseteq
2^{\Sigma_\tau}\setminus\{\varnothing\}
\]

를 잡고

\[
\forall\tau\ \forall R\in\mathcal A_\tau\ \forall\alpha
\quad
F_{G,\tau,\alpha}(R)\in\mathcal A_{\tau'}
\tag{PG}
\]

를 요구한다. (PG)는 nondeterministic circuit 선택을 잃지 않는 정확한 closure 조건이다.
구현에서는 reachable set을 canonical bitset으로 표현할 수 있다.

## 7. base cap 조건

반복 gadget에 들어가기 위한 finite base construction \(B_0\)가 필요하다. base의 모든
재배향 \(\rho_0\)에 대해, base layers를 처리한 뒤의 정확한 reachable set을
\(R_0(\rho_0)\)라 하자.
필요한 조건은

\[
\forall\rho_0
\quad
R_0(\rho_0)\in\mathcal A_{\tau_0}
\tag{B}
\]

이다. 따라서 base가 단순히 witness라는 사실만으로는 부족하다. 모든 재배향에서 지정된
output port에 도착하는 admissible boundary state까지 제공해야 한다.

layer 수를 \(k\)씩 늘리는 gadget이 모든 큰 layer 수를 다루려면 residue class마다 base cap이
필요하다. (k=2)이면 짝수 (m)용 base와 홀수 (m)용 base 두 개를 따로 둘 수 있다.

## 8. 유한 gadget 귀납정리

**정리(조건부).** 다음을 가정한다.

1. \(m_0\)개 layer와 \(n_0\)개 원소를 가진 base cap이 (B)를 만족한다.
2. 고정된 \((k,q)\)-gadget이 coherent extension rule과 (PG)를 만족한다.
3. 반복해서 얻은 ordered union들이 uniform OM이다.

그러면 모든 \(t\ge0\)에 대해

\[
m_t=m_0+tk,\qquad n_t=n_0+tq
\]

인 union은 모든 재배향에서 defect \(\le1\)인 circuit를 가진다.

**증명.** 전체 ground set의 임의 재배향 \(\rho\)를 고정한다. base restriction에 (B)를 적용하면
nonempty \(R_0\in\mathcal A_{\tau_0}\)를 얻는다. \(j\)번째 new block의 coloring을
\(\alpha_j\)라 하고

\[
R_j=F_{G,\tau_{j-1},\alpha_j}(R_{j-1})
\]

라 두면, (PG)에 의해 귀납적으로

\[
R_j\in\mathcal A_{\tau_j},\qquad R_j\ne\varnothing
\]

이다. \(R_t\)의 한 상태를 실현하는 transition path를 역추적하면 모든 \(m_t\)개 layer를
사용하는 increasing chain을 얻는다. 식 (5)에 의해 이는 최종 union circuit이고, dead state를
버렸으므로 (6)의 defect가 1 이하이다. \(\rho\)가 임의였으므로 모든 재배향이 convex position에
실패한다. □

이 증명에서 existential chain 선택은 \(\rho\) 전체에 의존해도 된다. 목표의 양화사가
“모든 재배향 \(\rho\)에 대해 어떤 circuit \(C\)가 존재”이기 때문이며 online strategy는
요구하지 않는다.

## 9. two-layer / nine-column 목표

첫 연구 목표는

\[
k=2,\qquad q=9
\]

인 gadget이다. 짝수 layer 수의 base를 \((m_0,n_0)=(2,8)\), 홀수 layer 수의 base를
\((3,13)\)으로 잡고 두 base 모두 (B)를 만족한다고 가정하면

\[
\begin{aligned}
m=2+2t&:\quad n=8+9t,\\
m=3+2t&:\quad n=13+9t.
\end{aligned}
\]

두 식은

\[
n=4m-1+\left\lceil\frac m2\right\rceil
\tag{14}
\]

로 합쳐진다. \(d=2m-1\)을 대입하고 witness at \(n\)이 \(\nu(d)\le n-1\)을 준다는 사실을 쓰면

\[
\nu(d)\le
2d+\left\lceil\frac{d+1}{4}\right\rceil
\tag{15}
\]

이다. 점근 계수는 (9/4=2.25)다.

식 (15)는 **조건부 목표**다. 아직 확인해야 할 것은 다음 세 가지다.

- \((2,8)\), \((3,13)\) base가 단순 witness를 넘어 동일 admissible family에 대한 (B)를 만족하는가?
- 실제 \((2,9)\)-gadget와 closed powerset family가 존재하는가?
- 반복 family의 실현가능성을 모든 (t)에 대해 증명할 수 있는가?

## 10. 탐색을 유한 문제로 만드는 방법

gadget 후보 하나의 검사는 유한하다.

1. input/output port 크기와 signed-permutation templates를 고정한다.
2. 모든 input-port colorings \(\tau\)와 \(2^q\)개의 block colorings \(\alpha\)를 열거한다.
3. 식 (10)으로 exact transition tensor (12)를 계산한다.
4. powerset action (13)의 닫힌 nonempty family를 찾는다.
5. 닫힌 family가 없거나 어떤 \(\alpha\)에서 reachable set이 비면 그 후보는 반증된다.

후보 생성은 압축된 classical run pattern `22|23` 또는 `23|22`에서 시작할 수 있다.
rank-1 두 개에서 유도되는 특수 rank-2 permutation을 유지하되, 빠진 3-run 근처의 작은
window에서만 일반 signed permutation의 nonfactorable split을 허용하는 방식이 첫 ansatz다.

더 일반적으로 boundary signatures를 vertex, gadget blocks를 weight \(q\)인 edge로 하는
유한 그래프를 만들 수 있다. layer 증가량 \(k\)에 대한 최소 평균 \(q/k\) cycle을 찾으면
미리 `2223`을 고정하지 않고 가능한 최선의 periodic cost를 데이터에서 추출할 수 있다.

## 11. 결정론적 테스트 명세

실제 구현은 다음 순서로 반증부터 시도한다.

### T1. local transition 차등검사

작은 random signed-permutation layer와 모든 triple에서 식 (10)이
`Rank2Layer.to_chirotope().circuit()`와 전역 부호를 제외하고 일치하는지 검사한다.

### T2. chain ↔ union circuit 차등검사

작은 (m,n)의 모든 또는 고정 seed 표본 support에서 식 (5)로 연결한 chain과
`lawrence_union_chirotope(layers).circuit(S)`를 완전 대조한다. 이 검사는 gadget search보다
먼저 통과해야 한다.

### T3. powerset transition exactness

작은 port/block에서 brute-force로 직접 열거한 partial chains와 bitset transition tensor를
대조한다. reachable set을 합치는 과정에서 서로 다른 endpoint/raw sign을 잘못 quotient하지
않는지 확인한다.

### T4. base-cap 전수검사

제안한 각 base의 모든 gauge-fixed 재배향에서 (B)를 검사한다. base가
`mcmullen_evaluate()`를 통과한다는 사실은 이 테스트를 대체하지 않는다.

### T5. gadget closure 전수검사

(q=9)이면 모든 512개 block colorings에 대해 (PG)를 검사한다. 실패 시
`input coloring / reachable set / block coloring`을 반례 certificate로 보존한다.

### T6. 반복 construction 대조

한두 번 gadget를 반복한 작은 차원에서 automaton의 `항상 nonempty` 예측과
`CoverageScanner`의 survivor 0, 최종 `om_core.mcmullen_evaluate()` 결과를 대조한다.

### T7. 실현가능성

각 유한 후보에 `extended_lawrence.realize_union`의 정수 벡터 증명서를 붙이고
`om_core.Chirotope.from_vectors`로 부호를 완전 대조한다. 무한 family 정리를 주장하려면
별도로 separated-scale determinant의 유일 leading term과 충분한 scale bound를 증명한다.

## 12. 구현 권한

- transition tensor와 closed-family 검색기는 독립적인 **분석/반증 도구**다.
- gadget closure를 통과하지 않은 signature는 candidate ranking에만 쓸 수 있다.
- 이 분석량에는 witness 판정 권한이 없다.
- 검증 전 signature를 generator의 hard pruning에 연결하지 않는다.
- 실제 witness 기록은 항상 `om_core.mcmullen_evaluate()`와 실현가능성 증명서를 요구한다.

관련 insight: `HI-0001`, `HI-0002`, `HI-0004`, `HI-0005`.
