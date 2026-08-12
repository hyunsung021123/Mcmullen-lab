"""lawrence_travel.py — Ramírez Alfonsín (EJC 22(5) 723–731, 2001) 의 **travel 기계**.

논문의 판정 언어를 저장소 안으로 들여온다. 두 가지 값어치가 있다.

  1. **독립 검증 경로.** `om_core` 는 circuit 균형으로 convex position 을 판정한다. 이 모듈은
     TT/BT 라는 완전히 다른 조합적 대상으로 같은 결론에 도달한다. 둘이 일치하면 두 구현이
     같은 버그를 공유할 가능성이 낮다. **판정 권한은 여전히 `om_core` 에만 있다** —
     이 모듈은 대조용이며, 불일치가 나오면 이 모듈이 틀린 것으로 취급한다.
  2. **증명이 사는 언어.** 사용자의 f(a)+f(b) ≤ f(a+b) 논증은 chessboard 위에서 TT/BT 쌍을
     훑는 형태다. 그 논증을 기계로 확인하려면 travel 자체가 있어야 한다.

## 논문의 사전 (모두 1-index)

부호행렬 A = (a_{i,j}), 1 ≤ i ≤ r, 1 ≤ j ≤ n. LOM 의 chirotope 는 χ(B) = ∏_i a_{i,j_i}.

  · **Remark (i)**: i > j 또는 j−n > i−r 인 계수는 (∗) 에 한 번도 안 나온다 → 무관.
    (우리 `lawrence_signs.free_bits` 의 밴드 축소가 바로 이것이다.)
  · **chessboard** B[A] = (r−1)×(n−1), s(i,j) = a_{i,j}a_{i+1,j}a_{i,j+1}a_{i+1,j+1}.
    열 부호반전(=재배향)에 불변.
  · **Top Travel**: a_{1,1} 에서 출발. a_{i,j} 에 있을 때 s = min{s : j<s≤n, a_{i,j} = −a_{i,s}}.
      s 가 없으면 가로로 a_{i,n} 까지 가고 정지.
      s 가 있고 i ≤ r−1 이면 가로로 a_{i,s} 로 간 뒤 세로로 a_{i+1,s} 로.
      s 가 있고 i = r 이면 가로로 a_{r,s} 로 가고 정지.
    **Bottom Travel** 은 a_{r,n} 에서 좌·상 방향으로 대칭.
  · **Lemma 2.1**: M_A 가 cyclic ⟺ TT 가 a_{r,s} (s<n) 에서 끝난다 ⟺ BT 가 a_{1,s'} (s'>1) 에서 끝난다.
  · **interior point**: acyclic OM 의 원소 e 로서 C⁻ = {e} 인 부호회로가 존재하는 것.
    (= e 를 재배향하면 cyclic 이 되는 원소.)
  · **Lemma 2.2** (M_A acyclic 일 때): k 가 interior ⟺
      k=1 이면 BT 가 a_{1,1} 에서 끝나고, k=n 이면 TT 가 a_{r,n} 에서 끝나며,
      2 ≤ k ≤ n−1 이면 TT 와 BT 가 **열 k 에서 평행**하다.
    평행: TT 가 행 i 에서 열 k−1,k,k+1 을 가로로 지나고, BT 가 행 i 또는 i+1 에서
          열 k+1,k,k−1 을 가로로 지난다.
  · **Lemma 3.1**: plain travel(가로/세로 이동, 연속 세로 금지, a_{1,1}a_{1,2} 로 시작,
    a_{i,n} 에서 종료) 전체와 M_A 의 acyclic 재배향 전체가 자연 전단사.

## 이 저장소의 목적어

    "(r, n) 에 witness 가 없다"  ⟺  모든 A 에 대해, interior point 가 하나도 없는
                                   acyclic 재배향이 존재한다.

즉 f(d) = (rank d+1 LOM 이 witness 를 못 만드는 최대 n) 은 위 명제가 성립하는 최대 n 이다.

    python lawrence_travel.py selftest
"""
from __future__ import annotations

import sys
from itertools import combinations
from math import ceil

from om_core import Chirotope


# ── travel ───────────────────────────────────────────────────────────
def top_travel(a) -> tuple[list[tuple[int, int]], bool]:
    """(방문 칸 목록, 4(b) 로 끝났는가). 0-index 로 (행, 열) 을 돌려준다.

    두 번째 값이 True 면 TT 가 a_{r,s} 에서 멈춘 것이고, s < n 이면 Lemma 2.1 로 cyclic."""
    r, n = len(a), len(a[0])
    i = j = 0
    cells = [(0, 0)]
    while True:
        s = None
        for t in range(j + 1, n):
            if a[i][t] == -a[i][j]:
                s = t
                break
        if s is None:                       # (3) 가로로 끝까지 가고 정지
            cells += [(i, t) for t in range(j + 1, n)]
            return cells, False
        cells += [(i, t) for t in range(j + 1, s + 1)]
        if i <= r - 2:                      # (4a) 세로 한 칸
            i += 1
            cells.append((i, s))
            j = s
        else:                               # (4b) 마지막 행에서 정지
            return cells, True


def bottom_travel(a) -> tuple[list[tuple[int, int]], bool]:
    """TT 의 좌우·상하 반전. (방문 칸 목록, 4(b) 로 끝났는가)."""
    r, n = len(a), len(a[0])
    i, j = r - 1, n - 1
    cells = [(i, j)]
    while True:
        s = None
        for t in range(j - 1, -1, -1):
            if a[i][t] == -a[i][j]:
                s = t
                break
        if s is None:
            cells += [(i, t) for t in range(j - 1, -1, -1)]
            return cells, False
        cells += [(i, t) for t in range(j - 1, s - 1, -1)]
        if i >= 1:
            i -= 1
            cells.append((i, s))
            j = s
        else:
            return cells, True


def is_cyclic(a) -> bool:
    """Lemma 2.1 — **TT 가 절차 4(b) 로 끝나면** cyclic.

    ⚠ 논문 Lemma 2.1 의 문면은 "TT 가 a_{r,s} (1 ≤ s < n) 에서 끝난다"인데, s = n 인 경우가
    실제로 발생하고 그때도 OM 은 cyclic 이다. 반례(우리 측):

        A = [[-,-,+,+,+], [+,+,-,+,+], [+,+,+,-,+]]   (r=3, n=5)
        양의 회로 (0,2,3,4) 와 (1,2,3,4) 가 존재 → cyclic
        그러나 TT 는 a_{3,5} = a_{r,n} 에서 4(b) 로 종료 → 문면대로면 acyclic

    Lemma 2.2 증명의 "we say that TT arrives at line r+1 if TT ends in step 4(b)" 가
    의도된 신호로 보이며, 그 해석(=4(b) 종료 자체가 cyclic)은 실측에서 om_core 와 완전히
    일치한다. 문면의 's < n' 은 전형적인 경우를 적은 것으로 읽는다."""
    return top_travel(a)[1]


def _horizontal_row_at(cells, k: int):
    """열 k−1, k, k+1 을 **같은 행에서 가로로** 지나는 행 번호. 없으면 None."""
    have = set(cells)
    rows = {i for (i, j) in cells if j == k}
    for i in rows:
        if (i, k - 1) in have and (i, k + 1) in have:
            return i
    return None


def interior_points(a) -> list[int]:
    """Lemma 2.2 — acyclic 인 A 의 interior 원소 목록(0-index). cyclic 이면 ValueError."""
    if is_cyclic(a):
        raise ValueError("Lemma 2.2 는 acyclic 인 M_A 에만 적용된다")
    n = len(a[0])
    r = len(a)
    tt, _ = top_travel(a)
    bt, _ = bottom_travel(a)
    out = []
    # (a) k=1 : BT = (a_{r,n}, …, a_{1,2}, a_{1,1}) — **행 1 안에서 가로로** a_{1,1} 에 닿아야
    #           한다. 세로 이동으로 (0,0) 에 떨어진 경우는 해당하지 않는다.
    if bt[-1] == (0, 0) and bt[-2] == (0, 1):
        out.append(0)
    # (b) k=n : TT = (a_{1,1}, …, a_{r,n−1}, a_{r,n}) — 마찬가지로 행 r 안에서 가로 도달.
    if tt[-1] == (r - 1, n - 1) and tt[-2] == (r - 1, n - 2):
        out.append(n - 1)
    for k in range(1, n - 1):                  # (c) 2 ≤ k ≤ n−1
        i = _horizontal_row_at(tt, k)
        j = _horizontal_row_at(bt, k)
        if i is not None and j is not None and (j == i or j == i + 1):
            out.append(k)
    return sorted(set(out))


# ── plain travel ↔ acyclic 재배향 (Lemma 3.1) ────────────────────────
def reorient(a, cols) -> list[list[int]]:
    cols = set(cols)
    return [[-x if j in cols else x for j, x in enumerate(row)] for row in a]


def acyclic_reorientations(a):
    """열 0 을 고정한 2^(n−1) 재배향 중 acyclic 인 것만 (부분집합, 행렬) 로 내놓는다.

    Lemma 3.1 은 이것이 plain travel 전체와 전단사임을 말한다 — 개수를 그 공식
    Σ_{i<r} C(n−1, i) 과 대조해 검증한다."""
    n = len(a[0])
    for mask in range(1 << (n - 1)):
        cols = {e for e in range(1, n) if (mask >> (e - 1)) & 1}
        b = reorient(a, cols)
        if not is_cyclic(b):
            yield cols, b


def has_convex_reorientation(a) -> tuple[bool, set | None]:
    """interior point 가 없는 acyclic 재배향이 존재하는가 = **witness 가 아닌가**."""
    for cols, b in acyclic_reorientations(a):
        if not interior_points(b):
            return True, cols
    return False, None


def is_witness(a) -> bool:
    """모든 acyclic 재배향이 interior point 를 갖는가 (travel 경로 판정)."""
    return not has_convex_reorientation(a)[0]


# ── 논문 Definition 3.2 의 극단 구성 ─────────────────────────────────
def star_n(r: int) -> int:
    """A* 의 열 수 n = 2(r−1) + ⌈r/2⌉.  r = d+1 이면 n = 2d + ⌈(d+1)/2⌉ = ⌊5d/2⌋+1."""
    return 2 * (r - 1) + ceil(r / 2)


def star_board(r: int) -> tuple[int, dict[int, set[int]]]:
    """B[A*] 의 검정칸 (1-index). 행 k 가 홀수면 2칸, 짝수면 3칸 — **2,3,2,3 run**.

        k 홀수 : l = (5k−3)/2, (5k−1)/2            (2-corner)
        k 짝수 : l = 5k/2 − 2, 5k/2 − 1, 5k/2      (3-corner)"""
    n = star_n(r)
    black = {}
    for k in range(1, r):
        if k % 2:
            black[k] = {(5 * k - 3) // 2, (5 * k - 1) // 2}
        else:
            black[k] = {5 * k // 2 - 2, 5 * k // 2 - 1, 5 * k // 2}
    return n, black


def board_to_matrix(r: int, n: int, black: dict[int, set[int]]) -> list[list[int]]:
    """chessboard → 부호행렬. 게이지 a_{1,j} = a_{i,1} = +1 로 유일하게 복원한다.

        a_{i+1,j+1} = s(i,j) · a_{i,j} · a_{i+1,j} · a_{i,j+1}"""
    a = [[1] * n for _ in range(r)]
    for i in range(1, r):
        for j in range(1, n):
            s = -1 if j in black[i] else 1
            a[i][j] = s * a[i - 1][j - 1] * a[i][j - 1] * a[i - 1][j]
    return a


def star_matrix(r: int) -> list[list[int]]:
    n, black = star_board(r)
    return board_to_matrix(r, n, black)


def chessboard(a) -> list[list[int]]:
    r, n = len(a), len(a[0])
    return [[a[i][j] * a[i][j + 1] * a[i + 1][j] * a[i + 1][j + 1]
             for j in range(n - 1)] for i in range(r - 1)]


# ── 자체 검증 (om_core 대조) ─────────────────────────────────────────
def _chirotope(a) -> Chirotope:
    r, n = len(a), len(a[0])
    return Chirotope(n, r, {B: _prod(a, B) for B in combinations(range(n), r)})


def _prod(a, B):
    v = 1
    for p, j in enumerate(B):
        v *= a[p][j]
    return v


def _interior_by_om_core(ch: Chirotope) -> list[int]:
    """C⁻ = {e} 인 circuit 이 있는 원소. om_core 만으로 직접 계산한다."""
    out = set()
    for S in combinations(range(ch.n), ch.r + 1):
        C = ch.circuit(S)
        neg = [e for e, v in C.items() if v < 0]
        pos = [e for e, v in C.items() if v > 0]
        if len(neg) == 1:
            out.add(neg[0])
        if len(pos) == 1:
            out.add(pos[0])
    return sorted(out)


def selftest() -> int:
    import random
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'} {label}: {got}"
              + ("" if good else f"  (기대 {want})"))

    rng = random.Random(20260811)

    def rnd(r, n):
        return [[rng.choice((-1, 1)) for _ in range(n)] for _ in range(r)]

    print("\n[1] Lemma 2.1 — TT/BT 의 cyclic 판정이 om_core 의 is_acyclic 과 일치하는가")
    bad_tt = bad_bt = 0
    for (r, n) in [(3, 6), (4, 7), (4, 8), (5, 9)]:
        for _ in range(60):
            a = rnd(r, n)
            ch = _chirotope(a)
            want = not ch.is_acyclic()
            if is_cyclic(a) != want:
                bad_tt += 1
            if bottom_travel(a)[1] != want:
                bad_bt += 1
    chk("TT 판정 불일치", bad_tt, 0)
    chk("BT 판정 불일치", bad_bt, 0)

    print("\n[2] Lemma 2.2 — interior point 목록이 om_core 와 일치하는가")
    bad = tested = 0
    for (r, n) in [(3, 6), (4, 7), (4, 8), (5, 9)]:
        for _ in range(60):
            a = rnd(r, n)
            if is_cyclic(a):
                continue
            tested += 1
            if interior_points(a) != _interior_by_om_core(_chirotope(a)):
                bad += 1
    chk(f"interior 목록 불일치 ({tested}건 검사)", bad, 0)

    print("\n[3] Lemma 3.1 — acyclic 재배향 수 = Σ_{i<r} C(n−1, i)")
    from math import comb
    bad = 0
    for (r, n) in [(3, 6), (4, 7), (4, 8), (5, 9)]:
        for _ in range(6):
            a = rnd(r, n)
            got = sum(1 for _ in acyclic_reorientations(a))
            want = sum(comb(n - 1, i) for i in range(r))
            if got != want:
                bad += 1
    chk("재배향 수 불일치", bad, 0)

    print("\n[4] witness 판정이 om_core 경로와 일치하는가 (독립 이중 확인)")
    import lawrence_signs as ls
    bad = 0
    for (r, n) in [(3, 6), (3, 7), (4, 7), (4, 8), (5, 9)]:
        for _ in range(40):
            a = rnd(r, n)
            if is_witness(a) != (ls.evaluate(a)[0] == 0):
                bad += 1
    chk("witness 판정 불일치", bad, 0)

    print("\n[5] chessboard 복원 — board → matrix → board 왕복")
    bad = 0
    for (r, n) in [(3, 6), (4, 8), (5, 10)]:
        for _ in range(20):
            a = rnd(r, n)
            cb = chessboard(a)
            black = {i + 1: {j + 1 for j in range(n - 1) if cb[i][j] < 0}
                     for i in range(r - 1)}
            if chessboard(board_to_matrix(r, n, black)) != cb:
                bad += 1
    chk("왕복 불일치", bad, 0)

    print("\n[6] 논문 Definition 3.2 의 A* 가 실제로 witness 인가")
    for r in range(3, 7):
        d = r - 1
        a = star_matrix(r)
        n = star_n(r)
        ch = _chirotope(a)
        w_travel = is_witness(a)
        w_core = ls.evaluate(a)[0] == 0
        cert = ls.realize_signs(a, target=ch)
        chk(f"d={d}: n = 2d+⌈(d+1)/2⌉ = {n} = ⌊5d/2⌋+1", n, 5 * d // 2 + 1)
        chk(f"d={d}: GP 적법", ch.is_valid(), True)
        chk(f"d={d}: witness (travel 경로)", w_travel, True)
        chk(f"d={d}: witness (om_core 경로)", w_core, True)
        chk(f"d={d}: 실현 증명서 존재 → ν({d}) ≤ {n-1}", cert is not None, True)

    print("\n" + ("전체 통과" if ok else "실패 항목 있음"))
    return 0 if ok else 1


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    sys.exit(selftest())
