# knowledge/equivalent_formulations.md — 정식화들 사이의 관계

McMullen 문제는 여러 언어로 옮길 수 있다. 그런데 그 번역들은 **가설 없이 자유롭게
오갈 수 있는 것이 아니다.** 이 파일은 각 번역이 어떤 조건에서 성립하는지, 그리고
이 저장소가 어느 것을 실제로 구현했는지 고정한다.

기호: `⟺(가설)` = 그 가설 아래에서만 동치.

---

## A. 점배치 ⟷ 유향 매트로이드 — **구현됨**

    R^d 일반위치 n점  →  동차화  →  rank d+1 uniform acyclic OM

- 방향 →: 항상 성립. `om_core.Chirotope.from_points`.
- 방향 ←: **성립하지 않는다.** 모든 uniform OM 이 점배치에서 오지는 않는다
  (비실현 OM). 이 저장소는 실현가능성을 **판정하지 않는다** — 판정하지 않았다는
  사실을 `scope.realizability = UNKNOWN` 으로 기록할 뿐이다.

⚠ 이 비대칭이 이 프로젝트에서 가장 중요한 함정이다. `problem.md` §3.2 참조.

---

## B. 사영변환 ⟷ 재배향 — **구현됨** (실현가능한 경우)

허용가능한 사영변환으로 얻는 점배치들 ⟷ **acyclic 이 되는 재배향** (= tope).

근거: 벡터배치 v_1,…,v_n 에 대해 선형범함수 f 로 v_i/f(v_i) 로 재정규화하면
f(v_i) < 0 인 원소가 뒤집힌다. 그리고 재배향이 acyclic ⟺ 모든 원소에 양인 f 가
존재(Farkas/Gale 쌍대) ⟺ 그 재배향이 tope.

`om_core.is_reorientable_to_convex` 는 acyclic 여부를 따지지 않고 **2^{n−1} 개
재배향 전체**를 훑는다. 그래도 결과가 같은 이유: convex position ⟹ acyclic 이므로,
convex 가 되는 재배향은 자동으로 tope 안에 있다. 즉 전수 재배향 탐색 = tope 탐색.

⚠ 추상(비실현) OM 에 대해서는 "사영변환"이라는 말 자체가 의미를 잃는다. 그때
계산되는 것은 OM 판본의 명제이지 원 문제의 명제가 아니다.

---

## C. convex position ⟷ Radon 분할 조건 — **구현됨**

    convex position ⟺ 어떤 circuit 도 한쪽 크기가 1 이하가 아님
                    ⟺ 모든 circuit 에서 min(|양|,|음|) ≥ 2

근거는 `problem.md` §2.4. 가설: **일반위치(uniform)**. 비uniform OM 에서는 circuit
크기가 r+1 이 아닐 수 있어 이 형태가 그대로 성립하지 않는다. 이 저장소는
uniform 만 다룬다.

---

## D. witness ⟷ Boolean hypercube covering — **구현됨, 이중 경로**

    witness(χ) ⟺ (Z/2)^{n−1} = ⋃_{S} B_S,
        B_S = {ρ : 재배향 ρ 후 circuit S 가 min(|양|,|음|) ≤ 1}

양방향 논증과 검증 절차는 `docs/AUTONOMOUS_VERIFICATION_PIPELINE.md` §3.
구현은 `reorientation_cover.py`(독립 경로) + `invariants._nonconvex_reorientation_mask`.

이 번역의 값어치는 속도만이 아니라 **부분 정보**다: 덮이지 않은 재배향의 개수가
곧 `num_convex_reorientations` 이고, 그것이 0 에 얼마나 가까운지가 '근접 실패'를
잰다. witness 를 0/1 이 아니라 연속량으로 보게 해 준다.

---

## E. Gale 쌍대 — **미구현. 구현 전 문헌 대조 필수**

n 점, rank r = d+1 → 쌍대 OM 의 rank 는 n − r.

목표점 n = 2d+2 에서는 n − r = (2d+2) − (d+1) = d+1 = r 이므로 **쌍대가 같은 rank
위의 대합**이 된다. 열거 수치도 이와 정합한다((7,3) 과 (7,4) 가 같은 개수 —
`known_results.md` O-1).

쓸 수 있다면 얻는 것:
- 탐색 공간을 쌍대 대합으로 접어 절반으로 줄이기,
- 자기쌍대 구성만 겨냥하기,
- circuit(원) ↔ cocircuit(쌍대) 로 조건을 옮겨 다른 각도에서 인코딩하기.

**하지 말 것**: convex position 조건이 쌍대에서 무엇이 되는지 추측해서 구현하는 것.
circuit 이 쌍대의 cocircuit 이라는 대응 자체는 표준이지만, "모든 circuit 이 균형"이
쌍대에서 어떤 익숙한 성질이 되는지는 이 저장소에서 **확정하지 않았다.** 틀린
쌍대 조건으로 만든 '검증기'는 조용히 틀린 결과를 대량 생산한다.

→ 절차: (1) Björner–Las Vergnas–Sturmfels–White–Ziegler 로 정확한 진술 확인,
(2) 작은 (n,r) 에서 원 판정과 쌍대 판정을 **전수 차등 검증**,
(3) 100% 일치할 때만 채택. `reorientation_cover` 가 밟은 절차와 같다.

---

## F. 초평면 배열 / 재배향류 / 1-neighborly — **미구현**

문헌에서 McMullen 문제와 함께 언급되는 다른 언어들:
- 초평면 배열의 셀 구조,
- 재배향류(reorientation class) 위의 성질,
- neighborly / 1-neighborly 재배향 존재성,
- 실현가능성(realizability) 판정 문제.

이 저장소는 **아직 어느 것도 구현하지 않았다.** 특히 "1-neighborly 재배향"과
"convex 재배향"을 같은 것으로 취급하지 말 것 — 두 개념이 어떤 가설 아래 일치하는지
확인되기 전에는 별개의 이름으로 둔다.

---

## 규칙

1. 이 문서에 없는 동치를 코드에 새로 넣지 않는다. 넣으려면 먼저 여기에
   **가설과 함께** 적고, 작은 범위 전수 차등 검증을 통과시킨다.
2. 번역이 한 방향으로만 성립하면 그 방향을 명시한다 (A 가 그 예다).
3. 실현가능성이 필요한 번역인지 항상 표시한다.
