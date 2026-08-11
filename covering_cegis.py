"""covering_cegis.py — witness 존재 여부를 **완전(complete)** 하게 판정하는 CEGIS.

## 왜 완전성이 필요한가

지금까지의 모든 방법(무작위 표집, 좌표 국소탐색, GP 돌연변이 탐색)은 탐색이다. 탐색은
"찾았다"는 말할 수 있어도 **"없다"는 절대 말할 수 없다.** 그런데 우리가 반복해서 부딪히는
벽이 정확히 그 지점이다 — d=4 는 witness 가 존재한다고 알려져 있는데 우리 탐색이 못 찾으니,
방법이 나쁜 것인지 정식화가 틀린 것인지 구분할 수가 없다.

이 모듈은 두 방향 모두 결론을 낸다.

  · **SAT** → (n, r) 의 추상 uniform OM witness 를 손에 넣는다. 그다음은 실현가능성 문제.
  · **UNSAT** → 그 (n, r) 에는 **OM witness 가 존재하지 않는다.** d=4 에서 이게 나오면
    문헌과 모순이므로 **우리 정식화 어딘가가 틀렸다는 뜻**이고, 그것이 이 실험의 가장
    중요한 산출물이 된다. 즉 이 테스트는 탐색이면서 동시에 **우리 명세의 감사**다.

## 인코딩 (mutation_lab 의 덮개 재정식화를 그대로 쓴다)

변수는 기저 부호 χ(B) ∈ {±1}, B ∈ C(n, r) 뿐이다. 제약은 둘.

**(1) GP 3항 Plücker** — uniform 에서 chirotope 의 필요충분조건 (`om_core.is_valid` 와 동일).
    coline Y (r−2 집합) 와 나머지 4원소 a<b<c<d 에 대해
      s1 = χ(Y∪ab)χ(Y∪cd),  s2 = χ(Y∪ac)χ(Y∪bd),  s3 = χ(Y∪ad)χ(Y∪bc)
    에서 (s1, s2, s3) 가 (+,−,+) / (−,+,−) 가 되는 것을 금지한다.

**(2) 덮개** — witness ⟺ 모든 재배향 ρ 가 어떤 circuit 에서 min-side ≤ 1 을 갖는다.
    circuit S 의 균형은 ρ 의 **S 로의 제한**에만 의존하므로(mutation_lab 참조),
    "S 가 ρ 를 덮는다"는 **단 r+1 개 기저 변수**에 대한 조건이 된다:
      t_i := [ρ_{s_i}·C_S(s_i) = −1],   덮음 ⟺ AtMost(t, 1) ∨ AtMost(¬t, 1)

(2) 는 ∀ρ 이므로 미리 다 넣으면 2^(n−1) 개 절이 된다. 대신 **CEGIS** 로 간다: 풀고 →
살아남은 ρ 를 반례로 받아 → 그 ρ 에 대한 덮개 절만 추가 → 다시 푼다.

**건전성.** 추가되는 절은 전부 "witness 라면 반드시 만족해야 하는 조건"이다. 따라서
누적 절 + GP 가 UNSAT 이면 witness 는 존재하지 않는다. 반대로 SAT 이 나오면 그 모델을
`om_core` 로 독립 재확인한다 — **판정은 여기서 하지 않는다.**

## 게이지 고정 (재배향 대칭 제거)

재배향 ρ 는 χ(B) 에 ∏_{e∈B} ρ_e 를 곱한다. F2 위에서 이건 선형사상이므로, 그 상(image)의
차원 k 만큼 기저 부호를 +1 로 **손해 없이** 고정할 수 있다 (f 는 재배향 불변이므로 건전).
r 이 홀수면 k = n, 짝수면 k = n−1 이다. d=5 에서 2^11 = 2048 배 축소.

의존성: 표준 라이브러리 + om_core + mutation_lab + **z3 (필수)**.

    python covering_cegis.py selftest
    python covering_cegis.py solve --n 10 --r 5 --budget 3600 --out cegis_d4.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from itertools import combinations

from om_core import Chirotope, mcmullen_evaluate
from mutation_lab import MutationLab, expected_acyclic

try:
    import z3
except ImportError:                                    # pragma: no cover
    z3 = None


# ── 부호 대수 ────────────────────────────────────────────────────────
def perm_odd(T) -> bool:
    """튜플 T 를 정렬하는 데 필요한 교환 횟수가 홀수인가 (교대성 부호)."""
    arr = list(T); swaps = 0
    for i in range(len(arr)):
        for j in range(len(arr) - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]; swaps += 1
    return swaps % 2 == 1


class Encoder:
    """기저 부호 Bool 변수 v[B] (True = χ(B) 가 음수) 와 그 위의 부호 대수."""

    def __init__(self, n: int, r: int):
        if z3 is None:
            raise RuntimeError("z3 가 필요하다: pip install z3-solver")
        self.n, self.r = n, r
        self.bases = list(combinations(range(n), r))
        self.v = {B: z3.Bool(f"x_{'_'.join(map(str, B))}") for B in self.bases}
        self.circuits = list(combinations(range(n), r + 1))

    def neg(self, T):
        """χ(T) 가 음수임을 나타내는 리터럴 (T 는 정렬 안 돼 있어도 된다)."""
        B = tuple(sorted(T))
        return z3.Not(self.v[B]) if perm_odd(T) else self.v[B]

    # ── (1) GP 3항 Plücker ───────────────────────────────────────────
    def gp_constraints(self) -> list:
        out = []
        E = range(self.n)
        for Y in combinations(E, self.r - 2):
            rest = [e for e in E if e not in Y]
            for a, b, c, d in combinations(rest, 4):
                S1 = z3.Xor(self.neg(Y + (a, b)), self.neg(Y + (c, d)))
                S2 = z3.Xor(self.neg(Y + (a, c)), self.neg(Y + (b, d)))
                S3 = z3.Xor(self.neg(Y + (a, d)), self.neg(Y + (b, c)))
                # 금지: s1 == s3 이면서 s2 == −s1
                out.append(z3.Or(z3.Xor(S1, S3), z3.Not(z3.Xor(S1, S2))))
        return out

    # ── 게이지 고정 ──────────────────────────────────────────────────
    def gauge_bases(self) -> list:
        """재배향 사상 M[B][e] = [e ∈ B] 의 F2 행공간 기저가 되는 기저들."""
        pivots: dict[int, int] = {}      # 선두 열 → 소거된 행벡터
        chosen = []
        for B in self.bases:
            vec = 0
            for e in B:
                vec |= 1 << e
            cur = vec
            for col in sorted(pivots, reverse=True):
                if (cur >> col) & 1:
                    cur ^= pivots[col]
            if cur:
                pivots[cur.bit_length() - 1] = cur
                chosen.append(B)
                if len(chosen) >= self.n:
                    break
        return chosen

    # ── (2) 덮개 절 ──────────────────────────────────────────────────
    def covers(self, S, flip_mask: int):
        """circuit S 가 재배향(flip_mask) 을 덮는다: min-side ≤ 1."""
        ts = []
        for i, s_i in enumerate(S):
            B = S[:i] + S[i + 1:]                  # 이미 정렬돼 있다
            const_odd = (i % 2 == 1) ^ bool((flip_mask >> s_i) & 1)
            ts.append(z3.Not(self.v[B]) if const_odd else self.v[B])
        return z3.Or(z3.AtMost(*ts, 1),
                     z3.AtMost(*[z3.Not(t) for t in ts], 1))

    def cover_clause(self, k: int):
        """어떤 circuit 이든 재배향 k 를 덮어야 한다.

        k 는 `MutationLab`/`reorientation_cover` 의 규약을 따르는 **인덱스**다:
        비트 i ⟺ 원소 i+1, 원소 0 은 절대 뒤집지 않는다. 따라서 원소 단위 마스크는
        `k << 1` 이다 — 이 변환을 빠뜨리면 절이 엉뚱한 재배향을 막아 루프가 수렴하지
        않는다(실제로 처음에 그렇게 틀렸다)."""
        flip_mask = k << 1
        return z3.Or([self.covers(S, flip_mask) for S in self.circuits])

    def model_chirotope(self, model) -> Chirotope:
        signs = {}
        for B in self.bases:
            val = model.eval(self.v[B], model_completion=True)
            signs[B] = -1 if z3.is_true(val) else 1
        return Chirotope(self.n, self.r, signs)


# ── CEGIS 루프 ───────────────────────────────────────────────────────
def solve(n: int, r: int, *, budget_s: float = 1800.0, max_rounds: int = 10_000,
          per_round: int = 16, verbose: bool = True, log=None) -> dict:
    t0 = time.time()
    enc = Encoder(n, r)
    s = z3.Solver()
    gp = enc.gp_constraints()
    s.add(gp)
    gauge = enc.gauge_bases()
    for B in gauge:
        s.add(z3.Not(enc.v[B]))                    # χ(B) = +1
    exp_acyc = expected_acyclic(n, r)

    def say(msg):
        if verbose:
            print(msg, flush=True)
        if log is not None:
            log.append(msg)

    say(f"[cegis] n={n} r={r} (d={r-1}) | 변수 {len(enc.bases)} "
        f"| GP 제약 {len(gp)} | 게이지 고정 {len(gauge)} (2^{len(gauge)} 배 축소)")
    say(f"  circuit {len(enc.circuits)} | 재배향 2^{n-1}={1 << (n-1)} "
        f"| acyclic 이론값 {exp_acyc}")

    rounds = 0
    clauses = 0
    best_f = None
    while rounds < max_rounds:
        left = budget_s - (time.time() - t0)
        if left <= 0:
            return {"status": "TIMEOUT", "rounds": rounds, "clauses": clauses,
                    "best_f": best_f, "elapsed_s": round(time.time() - t0, 1),
                    "n": n, "r": r}
        s.set("timeout", max(1000, int(left * 1000)))
        res = s.check()
        if res == z3.unsat:
            say(f"  ★ UNSAT — (n={n}, r={r}) 에 OM witness 는 존재하지 않는다 "
                f"(라운드 {rounds}, 절 {clauses})")
            return {"status": "UNSAT", "rounds": rounds, "clauses": clauses,
                    "best_f": best_f, "elapsed_s": round(time.time() - t0, 1),
                    "n": n, "r": r}
        if res != z3.sat:
            return {"status": "UNKNOWN", "reason": str(s.reason_unknown()),
                    "rounds": rounds, "clauses": clauses, "best_f": best_f,
                    "elapsed_s": round(time.time() - t0, 1), "n": n, "r": r}

        ch = enc.model_chirotope(s.model())
        # 신뢰 규약: 인코딩을 믿지 않고 om_core 로 직접 재확인한다.
        if not ch.is_valid():
            raise AssertionError("GP 인코딩 결함: 모델이 om_core.is_valid 를 통과 못 함")
        lab = MutationLab(ch)
        acyc, f, _ = lab.evaluate()
        if acyc != exp_acyc:
            raise AssertionError(f"tope 수 불변 위반: {acyc} != {exp_acyc}")
        best_f = f if best_f is None else min(best_f, f)
        rounds += 1

        if f == 0:
            ev = mcmullen_evaluate(ch)
            say(f"  ★★ SAT — witness 발견 (라운드 {rounds}, 절 {clauses}, "
                f"{time.time()-t0:.1f}s) | om_core: witness={ev.get('witness')}")
            subs = sorted(enc.bases)
            return {"status": "SAT", "rounds": rounds, "clauses": clauses,
                    "elapsed_s": round(time.time() - t0, 1), "n": n, "r": r,
                    "best_f": 0,
                    "signs": "".join("+" if ch.signs[B] > 0 else "-"
                                     for B in subs),
                    "chirotope": ch.to_dict(),
                    "om_core_evaluate": ev,
                    "gp_valid": True, "acyclic": acyc,
                    "scope": {"realizability": "UNKNOWN — 추상 OM. 정수 좌표 실현 "
                                               "전에는 ν(d) 상한을 증명하지 않는다"}}

        surv = lab.survivor_indices()
        improved = (f == best_f)
        for k in surv[:per_round]:
            s.add(enc.cover_clause(k))
            clauses += 1
        if improved or rounds % 100 == 1:
            say(f"  라운드 {rounds}: f={f} (최선 {best_f}) "
                f"| 절 {clauses} | {time.time()-t0:.0f}s")

    return {"status": "MAXROUNDS", "rounds": rounds, "clauses": clauses,
            "best_f": best_f, "elapsed_s": round(time.time() - t0, 1),
            "n": n, "r": r}


# ── CLI ──────────────────────────────────────────────────────────────
def cmd_solve(args) -> int:
    log: list[str] = []
    res = solve(args.n, args.r, budget_s=args.budget, per_round=args.per_round,
                max_rounds=args.max_rounds, log=log)
    print(f"\n[결과] {res['status']} | 라운드 {res['rounds']} "
          f"| 절 {res['clauses']} | 최선 f {res['best_f']} "
          f"| {res['elapsed_s']}s")
    if args.out:
        res["log"] = log
        snap = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            ".exec_sync.json")
        if os.path.exists(snap):
            with open(snap, encoding="utf-8") as f:
                res["snapshot_id"] = json.load(f).get("snapshot_id")
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print(f"저장: {args.out}")
    return 0


def selftest() -> int:
    """답을 아는 작은 사례에서 인코딩과 판정을 검증한다.

    d=2 (6,3): witness 는 흔하다(전수 11,904 중 약 84%) → SAT 이어야 한다.
    d=3 (8,4): 무작위 실현가능 표집에서 1.6% 가 witness → SAT 이어야 한다.
    그리고 (5,3): n = 2d+1 = 5 는 **하한 ν(2) ≥ 5** 에 해당하므로 witness 가
    존재하면 안 된다 → **UNSAT 이어야 한다.** UNSAT 쪽을 한 번은 확인해야
    "없다"를 말하는 능력 자체가 검증된다.
    """
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'OK ' if good else 'FAIL'} {label}: {got}"
              + ("" if good else f" (기대 {want})"))

    print("\n[1] (5,3) d=2, n=2d+1 — 하한 ν(2) ≥ 5 이므로 witness 가 없어야 한다")
    r1 = solve(5, 3, budget_s=120, verbose=False)
    chk("status", r1["status"], "UNSAT")

    print("\n[2] (6,3) d=2, n=2d+2 — witness 가 흔한 영역")
    r2 = solve(6, 3, budget_s=180, verbose=False)
    chk("status", r2["status"], "SAT")
    if r2["status"] == "SAT":
        ch = Chirotope.from_dict(r2["chirotope"])
        chk("om_core.is_valid", ch.is_valid(), True)
        chk("om_core witness", mcmullen_evaluate(ch).get("witness"), True)
        chk("독립 재확인 f", MutationLab(ch).evaluate()[1], 0)
        print(f"  -- 라운드 {r2['rounds']}, 절 {r2['clauses']}, {r2['elapsed_s']}s")

    print("\n[3] (8,4) d=3, n=2d+2")
    r3 = solve(8, 4, budget_s=600, verbose=False)
    chk("status", r3["status"], "SAT")
    if r3["status"] == "SAT":
        ch = Chirotope.from_dict(r3["chirotope"])
        chk("om_core witness", mcmullen_evaluate(ch).get("witness"), True)
        print(f"  -- 라운드 {r3['rounds']}, 절 {r3['clauses']}, {r3['elapsed_s']}s")

    print("\n" + ("전체 통과" if ok else "실패 항목 있음"))
    return 0 if ok else 1


def main(argv=None) -> int:
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(
        prog="covering_cegis",
        description="덮개 조건 CEGIS — witness 존재/부재를 완전하게 판정")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("solve")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--r", type=int, required=True)
    p.add_argument("--budget", type=float, default=1800.0, help="초")
    p.add_argument("--per-round", type=int, default=16,
                   help="라운드당 추가할 반례 재배향 수")
    p.add_argument("--max-rounds", type=int, default=10_000)
    p.add_argument("--out", default=None)
    p.set_defaults(func=cmd_solve)
    sub.add_parser("selftest").set_defaults(func=lambda a: selftest())
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        return selftest()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
