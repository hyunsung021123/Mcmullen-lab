"""lawrence_cegis.py — Lawrence 부호변수 전용 덮개-CEGIS (`gluing_induction_computational_spec.md` C0).

## 왜 일반 OM CEGIS 가 아니라 이것인가

`covering_cegis.py` 는 **기저 부호**를 변수로 삼는다. (12,6) 이면 변수 C(12,6)=924 개에
GP 3항 제약 수만 개가 붙는다. 그런데 우리가 묻는 것은 "**Lawrence** OM 중에 witness 가
있는가" 이므로, 변수를 부호행렬로 내리면

    χ(B) = ∏_p a_{p, j_p}          (B = j_0 < … < j_{R−1})

에서 χ(B) 의 부호가 **primary bit 최대 R 개의 XOR** 로 결정된다. 게다가 Lawrence union 은
항상 GP 를 만족하므로 **GP 제약이 통째로 사라진다**. `lawrence_signs.free_bits` 의
게이지+밴드 축소를 그대로 쓰면 (5,12) 에서 변수가 **30개**다.

    (d,n)=(5,12)  변수 30 · circuit C(12,7)=792 · 재배향 2^11=2048

## 인코딩

circuit S = (s_0 < … < s_R) 에 대해 C_S(s_i) = (−1)^i χ(S∖s_i) 이고, 재배향 ρ 아래
부호는 ρ_{s_i}·C_S(s_i) 다. 따라서

    t_i := [재배향된 부호가 음수]
         = (i 홀수) ⊕ (ρ 가 s_i 를 뒤집는가) ⊕ [χ(S∖s_i) < 0]

이고 마지막 항이 primary bit 들의 XOR 이다. circuit S 가 ρ 를 **덮는다**(= min-side ≤ 1) 는

    AtMost(t, 1) ∨ AtMost(¬t, 1)

witness ⟺ 모든 재배향이 어떤 circuit 에든 덮인다. 재배향은 원소 0 을 고정해 2^(n−1) 개이며
`CoverageScanner` 와 같은 인덱스 규약을 쓴다(비트 i ⟺ 원소 i+1, 즉 flip_mask = k << 1).

## CEGIS 루프

    master  : 지금까지 나온 survivor 재배향마다 "그 재배향을 덮어라" 절
    oracle  : SAT model → 부호행렬 → `CoverageScanner` 로 survivor 전수 주사
    수렴     : survivor 0 → witness (om_core 로 확정)  |  master UNSAT → 그 (n,R) 에 없음

**신뢰 규약**: solver 의 SAT 는 `om_core.mcmullen_evaluate` 로 반드시 replay 한다.
solver 의 UNSAT 은 그 자체로 `PROVEN` 이 아니다 — 명세 C0 대로 독립 확인이 필요하며,
이 모듈은 결과에 `trust` 필드로 그 한계를 명시한다.

    python lawrence_cegis.py selftest              # 답을 아는 (3,7)·(3,8)·(4,10)·(4,11) 보정
    python lawrence_cegis.py solve --d 5 --n 12 --hours 6 --out cegis_d5_n12_lawrence.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from itertools import combinations

from om_core import mcmullen_evaluate
from lawrence_signs import (evaluate, fast_chirotope, free_bits, identity_state,
                            realize_signs)
from layer_search import bound_gain, known_upper_bound

try:
    import z3
except ImportError:                                    # pragma: no cover
    z3 = None


class LawrenceEncoder:
    """primary 변수 = 게이지·밴드 축소된 부호 비트. 기저 변수도 GP 제약도 없다."""

    def __init__(self, d: int, n: int):
        if z3 is None:
            raise RuntimeError("z3 가 필요하다: pip install z3-solver")
        self.d, self.n = d, n
        self.rank = d + 1
        if n <= self.rank:
            raise ValueError("n > rank 이어야 함")
        self.bits = free_bits(n, self.rank)
        self.idx = {be: i for i, be in enumerate(self.bits)}
        self.x = [z3.Bool(f"s{p}_{e}") for (p, e) in self.bits]
        self.circuits = list(combinations(range(n), self.rank + 1))
        self._chi_cache: dict[tuple, object] = {}

    def chi_neg(self, B):
        """χ(B) < 0 을 나타내는 z3 식. 고정 성분(+1)은 XOR 에 기여하지 않는다."""
        key = tuple(B)
        hit = self._chi_cache.get(key)
        if hit is not None:
            return hit
        terms = [self.x[self.idx[(p, key[p])]]
                 for p in range(self.rank) if (p, key[p]) in self.idx]
        if not terms:
            expr = z3.BoolVal(False)
        else:
            expr = terms[0]
            for t in terms[1:]:
                expr = z3.Xor(expr, t)
        self._chi_cache[key] = expr
        return expr

    def covers(self, S, flip_mask: int):
        """circuit S 가 재배향 flip_mask 를 덮는다 (min-side ≤ 1)."""
        ts = []
        for i, s_i in enumerate(S):
            B = S[:i] + S[i + 1:]                      # 이미 정렬돼 있다
            const_odd = (i % 2 == 1) ^ bool((flip_mask >> s_i) & 1)
            lit = self.chi_neg(B)
            ts.append(z3.Not(lit) if const_odd else lit)
        return z3.Or(z3.AtMost(*ts, 1),
                     z3.AtMost(*[z3.Not(t) for t in ts], 1))

    def cover_clause(self, k: int):
        """survivor 인덱스 k(= 원소 마스크 k<<1) 를 어떤 circuit 이든 덮어야 한다."""
        flip_mask = k << 1
        return z3.Or([self.covers(S, flip_mask) for S in self.circuits])

    def model_matrix(self, model) -> list[list[int]]:
        a = identity_state(self.n, self.rank)
        for k, (p, e) in enumerate(self.bits):
            if z3.is_true(model.eval(self.x[k], model_completion=True)):
                a[p][e] = -1
        return a


def solve(d: int, n: int, *, budget_s: float = 3600.0, max_rounds: int = 100_000,
          per_round: int = 24, seed: int = 0, verbose: bool = True,
          log=None) -> dict:
    t0 = time.time()
    enc = LawrenceEncoder(d, n)
    s = z3.Solver()
    s.set("random_seed", seed)

    def say(msg):
        if verbose:
            print(msg, flush=True)
        if log is not None:
            log.append(msg)

    say(f"[lawrence-cegis] d={d} n={n} rank={enc.rank} | primary 변수 "
        f"{len(enc.bits)} (2^{len(enc.bits)}) | circuit {len(enc.circuits)} "
        f"| 재배향 2^{n-1}={1 << (n - 1)} | GP 제약 없음")

    rounds = clauses = 0
    best_f = None
    while rounds < max_rounds:
        if time.time() - t0 > budget_s:
            return {"status": "TIMEOUT", "d": d, "n": n, "r": enc.rank,
                    "rounds": rounds, "clauses": clauses, "best_f": best_f,
                    "num_vars": len(enc.bits),
                    "elapsed_s": round(time.time() - t0, 1)}
        rounds += 1
        res = s.check()
        if res == z3.unsat:
            say(f"  UNSAT — 이 (n={n}, rank={enc.rank}) 의 Lawrence family 에 "
                f"witness 가 없다 (라운드 {rounds}, 절 {clauses})")
            return {"status": "UNSAT", "d": d, "n": n, "r": enc.rank,
                    "rounds": rounds, "clauses": clauses,
                    "num_vars": len(enc.bits),
                    "implies": f"f({d}) >= {n}",
                    "trust": ("solver UNSAT 단독으로는 PROVEN 이 아니다 — 독립 solver "
                              "또는 검사 가능한 unsat proof 가 필요하다 (명세 C0)"),
                    "elapsed_s": round(time.time() - t0, 1)}
        if res != z3.sat:
            return {"status": f"UNKNOWN({res})", "d": d, "n": n, "r": enc.rank,
                    "rounds": rounds, "clauses": clauses,
                    "elapsed_s": round(time.time() - t0, 1)}

        a = enc.model_matrix(s.model())
        f, surv = evaluate(a)
        if best_f is None or f < best_f:
            best_f = f
            say(f"  라운드 {rounds}: survivor {f} (절 {clauses}, "
                f"{time.time() - t0:.0f}s)")
        if f == 0:
            ch = fast_chirotope(a)
            valid = ch.is_valid()
            ev = mcmullen_evaluate(ch)
            cert = realize_signs(a, target=ch)
            say(f"  ★★ witness! GP 적법={valid} | om_core={ev.get('witness')} "
                f"| 실현 증명서={'있음' if cert else '없음'} "
                f"| ν({d}) ≤ {n-1} (문헌 {known_upper_bound(d)}, "
                f"개선폭 {bound_gain(d, n)})")
            return {"status": "SAT_WITNESS", "d": d, "n": n, "r": enc.rank,
                    "rounds": rounds, "clauses": clauses,
                    "num_vars": len(enc.bits),
                    "gp_valid": valid,
                    "om_core_evaluate": ev,
                    "implied_upper_bound": n - 1,
                    "known_upper_bound": known_upper_bound(d),
                    "bound_gain": bound_gain(d, n),
                    "implies": f"f({d}) <= {n-1}",
                    "sign_vectors": [list(v) for v in a],
                    "realization_certificate": cert,
                    "realizability": "REALIZABLE" if cert else "CLAIMED_UNVERIFIED",
                    "elapsed_s": round(time.time() - t0, 1)}
        for k in surv[:per_round]:
            s.add(enc.cover_clause(k))
            clauses += 1

    return {"status": "MAX_ROUNDS", "d": d, "n": n, "r": enc.rank,
            "rounds": rounds, "clauses": clauses, "best_f": best_f,
            "elapsed_s": round(time.time() - t0, 1)}


# ── 자체 검증: 답을 아는 곳에서 보정 ─────────────────────────────────
_CALIBRATION = [
    # (d, n, 기대 status, 근거)
    (3, 7, "UNSAT", "(3,7) 2^6 전수 완주 witness 0 → f(3) ≥ 7"),
    (3, 8, "SAT_WITNESS", "f(3)=7 이므로 n=8 에 witness 가 있다 (A* 크기)"),
    (4, 10, "UNSAT", "(4,10) 2^20 전수 완주 witness 0 → f(4) = 10"),
    (4, 11, "SAT_WITNESS", "A* 가 n=2d+⌈(d+1)/2⌉=11 에서 witness"),
    (5, 13, "SAT_WITNESS", "A* 의 d=5 크기"),
]


def selftest(budget_s: float = 900.0) -> int:
    ok = True
    print("\n답을 아는 사례에서 CEGIS 를 보정한다 (전수·A* 결과와 대조)")
    for (d, n, want, why) in _CALIBRATION:
        t0 = time.time()
        res = solve(d, n, budget_s=budget_s, verbose=False)
        got = res["status"]
        good = got == want
        ok &= good
        extra = ""
        if got == "SAT_WITNESS":
            extra = (f" | om_core={res['om_core_evaluate'].get('witness')}"
                     f" GP={res['gp_valid']}"
                     f" 증명서={'있음' if res['realization_certificate'] else '없음'}")
            good2 = (res["om_core_evaluate"].get("witness") is True
                     and res["gp_valid"] is True)
            ok &= good2
        print(f"  {'OK  ' if good else 'FAIL'} (d={d}, n={n}) → {got}"
              f"  [기대 {want}] 변수 {res['num_vars']} 라운드 {res['rounds']} "
              f"절 {res['clauses']} {time.time()-t0:.1f}s{extra}")
        print(f"       근거: {why}")
    print("\n" + ("전체 통과" if ok else "실패 항목 있음"))
    return 0 if ok else 1


def _stamp(rec: dict) -> dict:
    snap = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".exec_sync.json")
    if os.path.exists(snap):
        with open(snap, encoding="utf-8") as fh:
            rec["snapshot_id"] = json.load(fh).get("snapshot_id")
    return rec


def main(argv=None) -> int:
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(
        prog="lawrence_cegis",
        description="Lawrence 부호변수 전용 덮개-CEGIS (명세 C0)")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("solve")
    p.add_argument("--d", type=int, required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--hours", type=float, default=1.0)
    p.add_argument("--per-round", type=int, default=24)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default=None)
    q = sub.add_parser("selftest")
    q.add_argument("--hours", type=float, default=0.25)
    args = ap.parse_args(argv)

    if args.cmd == "solve":
        log: list[str] = []
        res = _stamp(solve(args.d, args.n, budget_s=args.hours * 3600,
                           per_round=args.per_round, seed=args.seed, log=log))
        print(f"\n[결과] {res['status']} | d={args.d} n={args.n} "
              f"| 라운드 {res['rounds']} | 절 {res['clauses']} | {res['elapsed_s']}s")
        res["log"] = log
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(res, fh, ensure_ascii=False, indent=1)
            print(f"저장: {args.out}")
        return 0
    return selftest(budget_s=(args.hours * 3600 if args.cmd == "selftest" else 900))


if __name__ == "__main__":
    sys.exit(main())
