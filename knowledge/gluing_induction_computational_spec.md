# 접합 귀납에서 rank-2 gadget까지: 계산 인증 명세

> 상태: **CONJECTURE / 실행 명세**  
> 관련 insight: `HI-0005`, `HI-0006`, `HI-0007`  
> 목적: Claude의 계산을 단순한 저차원 실험이 아니라, 유한 상태 접합 귀납의
> 가정을 검증하거나 반증하는 **증명 인증서 생성 과정**으로 만든다.

## 0. 현재의 두 목표

1. 순수 rank-1 Lawrence 계열의 임계값을 `f(d)`라 할 때

   \[
   f(a+2)\ge f(a)+5\qquad(a\ge2)
   \tag{C}
   \]

   를 접합 귀납으로 증명한다. `f(2)=5`, `f(3)=7` 및 Alfonso의 `A*` 구성과
   결합하면 `f(d)=floor(5d/2)`가 모든 `d>=2`에서 따른다.

2. (C)의 증명 과정에서 얻은 `경계 상태 + powerset 전이 + 폐쇄성` 엔진을
   rank-2 layer OM으로 옮긴다. 먼저 고전 증가량에 해당하는 `(k,q)=(2,10)`
   gadget을 양성 대조군으로 검사하고, 최종적으로 `(2,9)` gadget을 찾는다.

두 목표 모두 **현재는 미증명**이다. 아래 유한 계산이 무한 명제를 증명하는 것은
전이계의 정확성을 수학적으로 확인한 뒤 폐쇄성 검사가 완전 탐색일 때뿐이다.

## 1. 정확한 양화사와 reachable-set 전이

prefix `A`에서 경계를 통과할 수 있는 travel의 상태 집합을 `R(A)`라 하자. 새 local
symbol 또는 gadget coloring을 `alpha`라 하고, 한 상태의 가능한 후속 상태 집합을
`T_alpha(sigma)`라 하면 정확한 전이는

\[
F_\alpha(R)=\bigcup_{\sigma\in R}T_\alpha(\sigma)
\tag{1}
\]

이다. 귀납에 필요한 양화사는

\[
\forall A\;\forall\alpha\;\exists\sigma\in R(A):
T_\alpha(\sigma)\ne\varnothing.
\tag{2}
\]

따라서 한 대표 travel을 임의로 고르면 안 되고 `R` 전체를 bitset으로 보존해야 한다.
반대로 모든 `alpha`에 통하는 하나의 `sigma`를 요구하는 것도 불필요하게 강하다.

상태 공간 `Sigma`와 local alphabet `Gamma`가 유한하다면 모든 powerset을 미리 열거할
필요는 없다. base에서 실제로 나타나는 `R`만 시작점으로 놓고 다음 orbit을 포화한다.

```text
queue := all base pairs (boundary-color, R)
seen  := queue
while queue is not empty:
    pop (tau, R)
    for alpha in Gamma(tau):
        R_next := union(T_alpha(sigma) for sigma in R)
        if R_next is empty:
            return finite counterexample
        push (tau_next(alpha), R_next) if unseen
return the finite closed reachable orbit
```

유한 bitset BFS이므로 반드시 정지한다. 빈 집합에 도달하지 않은 orbit 자체가 필요한
폐쇄 family다. 단, 이 계산의 증명력은 아래 `O0--O6`에 달려 있다.

## 2. 고전 Lawrence 접합의 증명 의무

### O0. 기하적 분해

임의의 큰 Lawrence sign matrix를 `prefix + local suffix symbol`로 분해하는 명시적
함수 `decompose(A)`가 있어야 한다. suffix alphabet의 크기는 `a`와 무관해야 하며,
무시한 entry가 접합하여 만드는 plain travel 또는 inverse travel에 영향을 주지
않는다는 증명도 필요하다.

이 단계가 가장 위험하다. 표준 gauge에서 자유 bit들은 크기
`(r-1)(n-r)`의 직사각형을 이룬다. `d -> d+2`, `n -> n+5`에서는 두 행과 세 열만
추가되는 것이 아니라 기존 크기에 비례하는 cross strip도 생긴다. 따라서 고정된
`2 x 3` 블록을 붙이는 것으로 자동 환원되지 않는다. cross strip이 구성된 두 travel에
무관함을 증명하거나, 유한 경계 정보에 흡수해야 한다.

### O1. 건전성

전이계의 모든 path를 원래 sign matrix 위의 실제 plain travel `P`와 inverse travel
`P^-`로 복원할 수 있어야 한다. 두 travel은 내부 점을 모두 덮어야 하고, 최종 결과는
`lawrence_travel.py`와 `om_core.py`에 replay한다.

### O2. 존재 선택의 완전성

`R(A)`는 prefix `A`에서 가능한 모든 경계 호환 travel pair의 상태를 담거나, 모든
suffix 아래에서 닫힌다는 것이 별도로 증명된 충분한 부분집합이어야 한다. `f(a)`는
“어떤 좋은 travel이 있다”고만 말하며 특정 endpoint type을 보장하지 않는다.

### O3. 국소성, 즉 right congruence

두 concrete prefix 기록 `x,y`가 같은 signature면 모든 local symbol에 대해 후속
signature 집합이 같아야 한다.

\[
x\sim y\Longrightarrow
\{[x'] : x\xrightarrow{\alpha}x'\}
=\{[y'] : y\xrightarrow{\alpha}y'\}
\quad(\forall\alpha).
\tag{3}
\]

충돌 하나라도 나오면 signature가 불충분하다. 그 두 concrete record와 구분에 필요한
좌표를 저장하고 상태를 세분해야 한다.

### O4. base 진입

`a=2,n=5`와 `a=3,n=7`의 모든 gauge-fixed matrix가 비어 있지 않은 exact base
reachable set을 가져야 한다. 자유 bit 수는 각각 `4`, `9`이므로 board 수는 `16`,
`512`다.

### O5. 보편 폐쇄

모든 도달 가능한 `(tau,R)`와 모든 허용 local symbol `alpha`에 대해 `F_alpha(R)`가
비어 있지 않고 다시 도달 가능한 family에 속해야 한다.

### O6. 독립 replay

각 전이와 최종 경로는 전이 코드를 호출하지 않는 별도 checker로 검증한다. 실패
artifact에는 전체 matrix, reorientation, `P`, `P^-`, old/new signature, local
symbol과 최초 실패 step을 넣는다.

### 조건부 접합 정리

`O0--O6`가 모두 성립하면 (C)가 따른다. 임의의 큰 matrix를 base와 local symbols
`alpha_1,...,alpha_t`로 분해한다. O4에서 `R_0`가 비어 있지 않고, O3 때문에 (1)이
concrete prefix의 exact 전이이며, O5에 의해 모든
`R_i=F_{alpha_i}(R_{i-1})`가 비어 있지 않다. 마지막 상태에서 predecessor를 역추적하고
O1을 적용하면 전체 matrix의 내부를 덮는 실제 `P,P^-`를 얻는다. Lawrence travel
criterion으로 이 matrix는 witness가 아니다. matrix가 임의였으므로 (C)가 성립한다.

계산이 담당하는 것은 유한한 O3--O6 전부를 열거하는 일이고, 수학적 핵심은 O0와
상태 정의가 O1--O3을 만족한다는 정당화다.

## 3. 최초 경계 상태는 최소화하지 않는다

첫 구현은 다음 정보를 가진 **비압축 concrete signature**를 사용한다.

1. plain/inverse travel pair `(P,P^-)`;
2. seam 양쪽 최소 두 열의 실제 부호 trace;
3. 각 경로의 수평/수직 도착 및 출발 방향;
4. 두 경로가 접촉하는 행 번호, 상대 순서와 정확한 gap;
5. seam 근처 reorientation과 chessboard sign;
6. endpoint, cyclic 종료 여부, 아직 덮이지 않은 seam cell;
7. concrete predecessor id.

endpoint만 저장하는 상태는 충분하지 않다. travel 판정의 국소 조건이 인접 세 열을
보므로 seam의 한 열만 저장해서도 안 된다. 행 gap도 처음부터 `0,1,far`로 cap하지
않는다. exact row를 보존해 (3)을 검사한 뒤에만 quotient 후보를 만든다.

## 4. Claude가 실행할 고전 Lawrence 계산

### C0. 첫 전면 반증 gate: `(d,n)=(5,12)` CEGIS

자유 bit 30개인 가장 가까운 미해결 사례를 먼저 공격한다.

- 변수: `lawrence_signs.free_bits(5,12)`의 gauge-fixed bit.
- separation oracle: `CoverageScanner`가 찾는 convexifying reorientation.
- master: 지금까지 발견한 각 reorientation을 막는 XOR + cardinality 절.
- SAT: `n=12` Lawrence witness를 `om_core.mcmullen_evaluate()`로 replay해 저장한다.
  그러면 (C)의 첫 새 사례 `f(5)>=12`가 거짓이다.
- UNSAT: 독립 solver 또는 checkable unsat proof를 붙여 `f(5)>=12`의 유한 증거로
  삼는다. `A*`의 `n=13` witness와 합치면 `f(5)=12`다.

이는 접합 automaton 자체를 증명하지는 않지만 긴 개발 전에 목표를 반증하는 gate다.

### C1. exact travel record 추출기

```python
enumerate_plain_travels(A) -> Iterable[Travel]
corresponding_reorientation(A, P) -> Reorientation
enumerate_inverse_travels(A, reorientation) -> Iterable[Travel]
covered_interior(P, P_inv) -> CellSet
full_boundary_record(A, P, P_inv, seam) -> ConcreteRecord
replay_record(A, record) -> bool
```

record는 실제 path 좌표와 reorientation을 포함한다. signature hash만 남기지 않는다.

### C2. base 전수 수집

- `(d,n)=(2,5)`: 16개 matrix.
- `(d,n)=(3,7)`: 512개 matrix.
- matrix마다 가능한 모든 good `(P,P^-)`의 concrete record를 얻는다.
- 여러 선택을 합쳐 하나의 reachable-set bitset으로 저장한다.

### C3. `d=2 -> d=4` 완전 calibration

`(d,n)=(4,10)`의 gauge-fixed board는 `2^20=1,048,576`개다. 이미 witness가 없다는
전수 결과가 있으므로 첫 decomposition/transition은 이 전체 scope에서 exact travel
판정과 같아야 한다. 각 board에서 다음을 비교한다.

- 분해된 base board와 local symbol;
- automaton의 `R_next`;
- 직접 열거한 good travel pair의 boundary record 집합;
- predecessor를 replay한 전체 `P,P^-`.

불일치 board를 최소화하고 O0--O3 중 무엇이 깨졌는지 태그한다.

### C4. signature refinement와 locality test

calibration record를 후보 signature별로 묶고, 같은 그룹의 모든 두 record와 모든
관측 local symbol에 대해 successor signature set을 비교한다.

- 다르면 collision pair와 구분 좌표를 저장하고 signature를 세분한다.
- suffix alphabet 또는 필요한 signature 좌표 수가 `d`와 함께 증가하면
  **O0/O3 미확립**으로 멈춘다. 억지로 cap하지 않는다.
- 유한 표본에서 collision이 없다는 것만으로 무한 congruence를 주장하지 않는다.
  전이 코드가 참조하는 좌표가 signature에 전부 들어 있음을 수식으로 보여야 한다.

### C5. exact reachable-orbit closure

O0--O3이 정리된 뒤 base reachable sets에서 Section 1의 BFS를 실행한다.

- empty에 도달하면 전체 matrix와 선택 실패를 복원한다.
- empty 없이 닫히면 state ordering, alphabet, transition tensor, bases, orbit,
  predecessor와 hash를 JSON으로 저장한다.
- 별도 replay code가 모든 edge를 재검사한다.

권장 artifact의 핵심 필드는 `schema`, `source_commit`, `state_codec`, `alphabet`,
`base_reachable_sets`, `reachable_orbit`, `transitions_sha256`, `replay`,
`counterexample`이다. `manifest.json`에는 명령, seed, solver/version, 실행 시간과 완료
범위를 기록한다.

## 5. rank-2 layer OM으로 전이

재사용할 모듈은 `StateCodec`, `local_transition`, `base_reachable_sets`,
`saturate_reachable_orbit`, `replay_certificate`다. rank-2에서는 union circuit chain이
자연스러운 유한 전이를 준다. port coloring `tau`에서 상태는

\[
\sigma=(p,\epsilon,a,b)
\]

로 둔다. `p`는 마지막 port endpoint, `epsilon`은 마지막 raw circuit sign,
`a,b in {0,1,2}`는 reorientation 뒤 +/- 개수의 capped count다. `(a,b)=(2,2)`는
dead state이므로 제거한다. quotient 전 상태 수는 coloring마다
`|Sigma_tau|=|P|*2*8=16|P|`다. 처음에는 global-sign quotient를 쓰지 않는다.

### R0. differential unit test

1. 작은 두 layer의 모든 rank-2 triple에서 local formula와 chirotope circuit sign을
   비교한다.
2. 모든 짧은 overlapping chain에서 누적 state와 직접 계산한 최종 union circuit의
   capped count를 비교한다.
3. 실패하면 layers, chain, reorientation과 두 결과를 저장한다.

### R1. base cap 전수 검사

고전 `A*`를 `lawrence_signs.to_layers`로 옮긴 base를 쓴다.

- `(m,n)=(2,8)`: global complement를 제외한 `2^7=128` reorientation;
- `(m,n)=(3,13)`: `2^12=4096` reorientation.

모든 시작 port와 circuit chain을 열거해 exact output-port reachable set을 저장한다.

### R2. `(k,q)=(2,10)` 양성 대조군

고전 성장률 `n=5m-2`에서 두 layer 증가는 원소 10개다. `A*_{m+2}`와 `A*_m`을 비교해
repeatable block 후보를 추출한다. 다음을 먼저 검사한다.

1. 큰 instance를 old layers/elements에 제한하면 작은 instance와
   gauge/reorientation/relabeling 동치인가;
2. 10개 새 원소와 port만으로 모든 mixed circuit transition이 결정되는가;
3. even base `(2,8)`과 odd base `(3,13)` 모두 같은 template 또는 유한 phase set으로
   연장되는가.

각 A* instance가 witness라는 것만으로 repeatable gadget이 생기지는 않는다. R2 실패는
고전 O0와 같은 성격이며 필요한 port/phase 정보를 알려준다.

### R3. q=10 exact powerset closure

coherent template가 만들어지면 모든 `2^10` block coloring과 모든 input port
coloring에 대해 reachable orbit을 포화한다. 이 대조군을 통과해야 q=9 실패를 제대로
해석할 수 있다.

### R4. `(k,q)=(2,9)` 후보 순서

1. q=10 block의 각 위치를 하나씩 삭제한 10개 phase 후보;
2. port 크기 `2,3,4`와 가능한 old/new port 위치;
3. 삭제점 주변의 국소 signed-permutation 변형;
4. 그 뒤에만 더 일반적인 nonfactorable rank-2 chirotope template.

후보마다 모든 `2^9=512` block coloring을 확인하고 `(tau,R)` orbit을 포화한다.
empty이면 최소 block word와 predecessor chain을 반환한다.

### R5. concrete replay와 실현가능성

closure를 통과한 후보는 1, 2 block을 실제 layer OM으로 구성해 `CoverageScanner`와
`om_core.mcmullen_evaluate()`에 replay한다. abstract closure는 `nu(d)` 상한이 아니다.
유한 instance는 `extended_lawrence.realize_union` 등으로 좌표 실현을 별도 확인하고,
무한 family에는 일관된 separated-scale 구성 또는 동등한 실현가능성 증명이 필요하다.

### 조건부 rank-2 귀납 정리

rank-2 local transition이 exact이고, 두 base cap이 성립하며, 모든 port/block coloring
아래 q=9 reachable orbit가 empty 없이 닫히고, coherent realizable extension이 있으면
임의의 block word에 대해 귀납적으로 필요한 signed union circuit를 얻는다. 그때에만
독립 판정기를 통과한 family를 McMullen 상한 후보로 승격한다.

## 6. 실행 순서와 중단 기준

1. **C0**: `(5,12)` CEGIS.
2. **C1--C3**: 비압축 record와 `d=2 -> 4`의 `2^20` 전체 calibration.
3. **C4**: right-congruence collision refinement.
4. **C5**: exact orbit와 replay 인증서.
5. **R0--R2**: rank-2 전이와 q=10 대조군.
6. **R3--R5**: q=10 closure 뒤 q=9 후보 및 realization.

다음 중 하나가 나오면 더 큰 계산 전에 모델을 수정한다.

- 같은 signature인데 successor set이 다른 collision;
- `d`와 함께 커지는 suffix alphabet 또는 경계 좌표;
- automaton path가 실제 travel/circuit로 replay되지 않음;
- q=10 A*조차 coherent repeatable template가 아님;
- abstract q=9 후보가 좌표 실현에서 반복 실패함.

`d<=D`에서 모두 맞았다는 사실만으로는 무한 귀납 증명이 아니다. O0--O6 또는 rank-2
조건부 정리의 의무가 전부 닫혔을 때만 `PROVEN`으로 올린다.

## 7. 권장 구현 경계

- `lawrence_boundary.py`: 고전 record, decomposition, signature refinement.
- `finite_state_closure.py`: family와 무관한 bitset orbit과 인증서 replay.
- `rank2_gadget_search.py`: rank-2 transition, q=10 extraction, q=9 search.
- `experiments/run_*/manifest.json`: 모든 장기 실행 provenance.

공통 closure 코드는 부호를 직접 해석하지 않고 명시적인 `StateCodec`과 transition만
다루게 한다. 그래야 고전 calibration에서 검증한 양화사 처리와 orbit 알고리즘을
rank-2에서 그대로 재사용할 수 있다.

