"""
om_core.py — McMullen 문제의 유향 매트로이드(OM) 검증 핵심 (Computing Agent의 신뢰 앵커).

이 파일의 모든 판별 로직은 신뢰의 기준점입니다. LLM 위원회/생성기가 무엇을 내놓든,
어떤 구성이 '상한을 개선했다'고 인정되려면 반드시 이 파일의 결정론적 검증을 통과해야 합니다.

제공 기능:
  - Uniform chirotope 표현 + 3-term Grassmann–Plücker 공리 검증 (uniform 에서 필요충분)
  - circuit(=Radon 분할) / cocircuit 부호 계산
  - acyclic / totally cyclic / convex-position(=convex independent) 의 '엄격히 분리된' 판별
  - 재배향(=사영변환) 하에서 convex position 으로 만들 수 있는지(McMullen witness) 판정
  - 직렬화(to_dict/from_dict) 및 재배향-불변 서명(canonical_key)

의존성: 표준 라이브러리만 사용 (numpy/z3 불필요).
"""
from __future__ import annotations
from itertools import combinations, product


def det_sign_int(M):
    """정수 정사각 행렬의 행렬식 부호(-1/0/1)를 Bareiss(분수-free)로 '정확히' 계산.
    부동소수 오차 없이 균일성(uniform)을 판정하기 위함."""
    M = [list(map(int, row)) for row in M]
    n = len(M); sign = 1; prev = 1
    for k in range(n - 1):
        if M[k][k] == 0:
            piv = next((i for i in range(k + 1, n) if M[i][k] != 0), None)
            if piv is None:
                return 0
            M[k], M[piv] = M[piv], M[k]; sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                M[i][j] = (M[i][j] * M[k][k] - M[i][k] * M[k][j]) // prev
        prev = M[k][k]
    det = M[-1][-1] * sign
    return (det > 0) - (det < 0)


class Chirotope:
    """rank r, ground set {0,..,n-1} 위의 uniform chirotope.
    signs: 정렬된 r-튜플 -> +1/-1 의 dict 로 저장하고, 임의 순서는 교대성으로 평가."""

    def __init__(self, n, r, signs):
        self.n, self.r = n, r
        self.signs = dict(signs)

    # ---------- 생성자 ----------
    @classmethod
    def from_vectors(cls, vectors):
        """vectors: 각 길이 r 인 정수 벡터들. rank=r chirotope (부호=행렬식 부호)."""
        r = len(vectors[0]); n = len(vectors); signs = {}
        for sub in combinations(range(n), r):
            s = det_sign_int([vectors[i] for i in sub])
            if s == 0:
                raise ValueError(f"non-uniform: {sub} 의 부호가 0")
            signs[sub] = s
        return cls(n, r, signs)

    @classmethod
    def from_points(cls, points):
        """points: R^d 정수 점들 -> 동차화하여 rank d+1 'acyclic' chirotope."""
        return cls.from_vectors([list(p) + [1] for p in points])

    @classmethod
    def alternating(cls, n, r):
        """교대 OM = 순환 다면체(cyclic polytope) 의 chirotope (정렬 튜플 모두 +1)."""
        return cls(n, r, {sub: 1 for sub in combinations(range(n), r)})

    # ---------- 핵심 평가 ----------
    def chi(self, idx):
        """임의의 서로 다른 r개 인덱스 튜플에 대한 교대(alternating) 부호."""
        arr = list(idx); swaps = 0; m = len(arr)
        for i in range(m):
            for j in range(m - 1 - i):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]; swaps += 1
        base = self.signs[tuple(arr)]
        return base if swaps % 2 == 0 else -base

    def circuit(self, S):
        """(r+1)-부분집합 S 의 부호 회로(=최소 Radon 분할). dict{elem: +/-1}."""
        S = tuple(sorted(S)); C = {}
        for i, s in enumerate(S):
            rest = S[:i] + S[i + 1:]
            C[s] = ((-1) ** i) * self.chi(rest)
        return C

    def cocircuit(self, H):
        """(r-1)-부분집합 H 가 정의하는 부호 코회로(=초평면의 양/음 쪽)."""
        H = tuple(sorted(H)); D = {}
        for e in range(self.n):
            if e not in H:
                D[e] = self.chi(H + (e,))
        return D

    # ---------- 공리 검증 (uniform: 3-term GP 가 필요충분) ----------
    def is_valid(self):
        E = range(self.n)
        for Y in combinations(E, self.r - 2):       # coline
            rest = [e for e in E if e not in Y]
            for a, b, c, d in combinations(rest, 4):
                s1 = self.chi(Y + (a, b)) * self.chi(Y + (c, d))
                s2 = self.chi(Y + (a, c)) * self.chi(Y + (b, d))
                s3 = self.chi(Y + (a, d)) * self.chi(Y + (b, c))
                # p1 - p2 + p3 = 0 (Plücker). 세 항이 부호상 모순되는 패턴 금지:
                #   (s1, s2, s3) in {(+,-,+), (-,+,-)}  <=>  s1==s3 and s2==-s1
                if s1 == s3 and s2 == -s1:
                    return False
        return True

    # ---------- 세 상태의 '엄격히 분리된' 판별 ----------
    def is_acyclic(self):
        """양의 회로(부호가 전부 +/전부 - 인 circuit)가 없으면 acyclic."""
        for S in combinations(range(self.n), self.r + 1):
            vals = set(self.circuit(S).values())
            if vals == {1} or vals == {-1}:
                return False
        return True

    def is_totally_cyclic(self):
        """양의 코회로가 없으면 totally cyclic = acyclic 의 '쌍대' 개념.
        (벡터들이 공간을 양으로 생성 / 원점이 내부) — convex position 과 무관."""
        for H in combinations(range(self.n), self.r - 1):
            vals = set(self.cocircuit(H).values())
            if vals == {1} or vals == {-1}:
                return False
        return True

    def is_convex_position(self):
        """모든 Radon 분할(circuit)이 '균형'(양쪽 크기 >= 2)이면 convex independent.
        => acyclic 이면서 어떤 점도 나머지의 볼록껍질 내부에 갇히지 않음.
        주의: 이것은 totally cyclic 과 전혀 다른 상태다."""
        for S in combinations(range(self.n), self.r + 1):
            C = self.circuit(S)
            pos = sum(1 for v in C.values() if v > 0)
            neg = len(C) - pos
            if min(pos, neg) < 2:
                return False
        return True

    # ---------- 재배향(=사영변환) ----------
    def reorient(self, flip):
        flip = set(flip)
        new = {t: (s if sum(e in flip for e in t) % 2 == 0 else -s)
               for t, s in self.signs.items()}
        return Chirotope(self.n, self.r, new)

    def is_reorientable_to_convex(self):
        """어떤 재배향(부호반전 부분집합)으로 convex position 이 되면 (True, flip),
        아니면 (False, None). 전역반전은 convexity 보존 → 원소 0 고정(2^(n-1) 탐색).
        ※ 대규모(d=5, n~12)에서는 to_z3 로 SAT/Z3 위임 권장(README 참조)."""
        others = list(range(1, self.n))
        for bits in product((0, 1), repeat=len(others)):
            flip = {others[i] for i, b in enumerate(bits) if b}
            if self.reorient(flip).is_convex_position():
                return True, flip
        return False, None

    # ---------- 직렬화 / 서명 ----------
    def to_dict(self):
        # JSON 호환: 튜플 키를 콤마 문자열로
        return {"n": self.n, "r": self.r,
                "signs": {",".join(map(str, k)): v for k, v in self.signs.items()}}

    @classmethod
    def from_dict(cls, d):
        signs = {tuple(int(x) for x in k.split(",")): v for k, v in d["signs"].items()}
        return cls(d["n"], d["r"], signs)

    def canonical_key(self):
        """재배향-동치류를 (느슨하게) 식별하기 위한 서명.
        전역 부호반전 및 원소 0 고정 하에서 사전식 최소 부호열을 택한다.
        (완전한 동형류 정규화는 아니며, 빠른 중복 제거용 휴리스틱)."""
        subs = sorted(self.signs)
        best = None
        others = list(range(1, self.n))
        for bits in product((0, 1), repeat=len(others)):
            flip = {others[i] for i, b in enumerate(bits) if b}
            ch = self.reorient(flip)
            seq = tuple(ch.signs[s] for s in subs)
            if best is None or seq < best:
                best = seq
        return best


def mcmullen_evaluate(chi, U=None):
    """McMullen(OM 버전) 평가/보상.
    witness = '어떤 재배향으로도 convex 가 되지 않는' uniform OM
            => OM-McMullen 수의 상한을 n-1 로 끌어내림.
    U: 기존 느슨한 상한 2d + floor((1+d)/2). reward = (U+1) - n  (n 작을수록 강함)."""
    d = chi.r - 1
    if U is None:
        U = 2 * d + (1 + d) // 2
    reorientable, flip = chi.is_reorientable_to_convex()
    if reorientable:
        return {"witness": False, "reorientable": True, "n": chi.n, "reward": 0.0}
    return {"witness": True, "reorientable": False, "n": chi.n,
            "implied_upper_bound": chi.n - 1, "target_bound": 2 * d + 1,
            "solves_conjecture": (chi.n - 1 == 2 * d + 1),
            "reward": float(U + 1 - chi.n)}


if __name__ == "__main__":
    # core-contract: 이 값들은 실측(수학적으로 확인된) 기대값이다 — 출력만 하지 않고
    # 반드시 assert한다. 판별 로직이 회귀하면(예: is_convex_position 부호 반전) 여기서
    # 반드시 실패해야 한다. (ChatGPT 리뷰 0004/0006 반영 — 기존엔 print만 하고 값
    # 자체는 검증하지 않아 CI가 smoke test에 불과했다.)
    def report(name, ch):
        print(f"[{name:24}] n={ch.n} r={ch.r} | "
              f"valid={ch.is_valid()!s:5} acyclic={ch.is_acyclic()!s:5} "
              f"tot_cyclic={ch.is_totally_cyclic()!s:5} convex={ch.is_convex_position()!s:5}")

    # 볼록 사각형: valid/acyclic/convex 전부 True, totally_cyclic은 False
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    report("convex quad", quad)
    assert quad.is_valid() is True
    assert quad.is_acyclic() is True
    assert quad.is_totally_cyclic() is False
    assert quad.is_convex_position() is True
    assert quad.is_reorientable_to_convex()[0] is True   # 이미 convex이므로 당연히 True
    ev_quad = mcmullen_evaluate(quad)
    assert ev_quad["witness"] is False and ev_quad["reorientable"] is True

    # 삼각형 + 내부점: acyclic이지만 convex 아님. 그러나 재배향하면 convex 가능(witness 아님)
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    report("triangle+interior", tri)
    assert tri.is_valid() is True
    assert tri.is_acyclic() is True
    assert tri.is_totally_cyclic() is False
    assert tri.is_convex_position() is False          # 내부점 때문에 convex 아님
    assert tri.is_reorientable_to_convex()[0] is True  # 하지만 재배향하면 convex 가능
    ev_tri = mcmullen_evaluate(tri)
    assert ev_tri["witness"] is False and ev_tri["reorientable"] is True

    # rank-2 totally cyclic 예: acyclic=False, totally_cyclic=True.
    # convex=False인데, 이건 README §5에 문서화된 rank-2 특이 케이스(회로가 3원소라
    # convex 정의가 자명하게 깨짐)이지 버그가 아니다 — CLAUDE.md 불변 조건 §3 참고.
    tc = Chirotope.from_vectors([(1, 0), (0, 1), (-1, -2), (-2, -1)])
    report("totally cyclic (rank2)", tc)
    assert tc.is_valid() is True
    assert tc.is_acyclic() is False
    assert tc.is_totally_cyclic() is True
    assert tc.is_convex_position() is False

    # 직렬화 왕복 점검
    d = quad.to_dict(); back = Chirotope.from_dict(d)
    assert back.signs == quad.signs and back.canonical_key() == quad.canonical_key()
    print("serialize round-trip OK")
    print("core-contract assertions OK (valid/acyclic/totally_cyclic/convex/witness 실측값 고정)")
