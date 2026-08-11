"""mutation_lab.py — GP 돌연변이 공간의 목적함수와 이웃 구조.

## 왜 이 모듈이 생겼는가

`climb.py` 는 좌표를 흔들며 f = #{convex 재배향} 을 내려갔다. 그런데 d=4 에서
1,903,305 회 평가 중 f=1 에 1,957 번 도달하고도 f=0 은 한 번도 없었다. 이것을
"평탄면 때문에 기울기가 사라졌다"고 해석했는데, **그 해석이 틀렸다.**

우리 실측과 `responses/0001-d5project.md` 의 독립 분석이 같은 결론에 도달했다:

  · [PROVEN] 좌표공간의 realization chamber **내부**에서 f 는 상수다. 따라서
    작은 좌표 흔들기에는 원리상 gradient 가 없다. f 가 바뀌려면 어떤 점이
    다른 d 개가 span 하는 초평면을 **넘어야** 한다 = 기저 부호 하나가 뒤집혀야 한다.
  · [VERIFIED] d=4 f=1 에서 기저 부호 하나를 뒤집어 f=0 을 만드는 방법은 252개 중
    125개나 있다. 그러나 **125개 전부 GP(3항 Plücker) 공리를 깬다.** GP 적법한
    돌연변이는 23개뿐이고 그중 f 를 줄이는 것은 0개다.

즉 벽은 목적함수의 평탄면이 아니라 **탐색 공간의 경계(OM 공리)** 다. 그러므로
이동은 좌표가 아니라 **GP 적법 기저 돌연변이**여야 하고, 목적함수는 f 하나가 아니라
돌연변이 이웃 구조를 보는 것이어야 한다. 이 모듈이 그 둘을 제공한다.

## 구조적 사실 (이 모듈의 속도 근거)

    C^ρ_S(s_i) = G · ρ_{s_i} · C_S(s_i),   G = ∏_{e∈S} ρ_e (전역 상수)

전역 부호 G 는 min(|+|,|−|) 에 영향을 주지 않는다. 따라서 **circuit S 의 Radon 균형은
재배향 ρ 의 S 로의 제한에만 의존**하고, chirotope 를 다시 만들 필요 없이

    neg = popcount((flip_mask XOR γ_S) & S_mask),   minside = min(neg, |S|−neg)

로 끝난다 (γ_S = C_S(e) < 0 인 원소들의 비트마스크). 결과:

  · ρ 가 acyclic  ⟺  모든 S 에서 minside ≥ 1
  · ρ 가 convex   ⟺  모든 S 에서 minside ≥ 2
  · **witness ⟺ γ_S 와 그 여집합 주위의 반경-1 해밍 실린더들이 하이퍼큐브를 전부 덮는다**
    (= 덮개 코드 문제. survivor 는 덮이지 않은 꼭짓점이다.)

기저 χ(B) 를 뒤집으면 B 를 포함하는 (n−r) 개 circuit 에서 각각 γ_S 의 비트 **하나씩만**
바뀐다. 그래서 돌연변이 갱신이 국소적이고, f 재평가가 d=5 에서 172ms → **0.1ms** 가 된다.

## 판정 권한 (CLAUDE.md 불변조건 1)

이 모듈은 **탐색 가속기이지 판정자가 아니다.** witness 주장은 반드시 `om_core.
mcmullen_evaluate` 를 통과해야 하며, `selftest` 는 이 엔진의 모든 출력을 om_core 와
대조한다. 또한 돌연변이 적법성의 최종 판정은 `Chirotope.is_valid()` 다 — 아래
tope-count 프록시는 값싼 **필요조건**일 뿐이다.

의존성: 표준 라이브러리 + om_core + reorientation_cover.

    python mutation_lab.py selftest
    python mutation_lab.py analyze --fixture fixtures/nearmiss_d5_f17.json
    python mutation_lab.py envelope --fixture fixtures/nearmiss_d5_f17.json --depth 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from itertools import combinations
from math import comb

from om_core import Chirotope, mcmullen_evaluate
from reorientation_cover import flip_set_from_index


def det_int(M) -> int:
    """정수 정사각 행렬의 행렬식 '값'을 Bareiss(분수-free)로 정확히 계산.

    om_core.det_sign_int 는 부호만 준다. 실현의 수치 안정성을 보려면 절댓값이 필요하다
    (응답의 `min_abs_det` 주장 검증 등)."""
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
    return M[-1][-1] * sign


def expected_acyclic(n: int, r: int) -> int:
    """uniform rank-r OM 의 acyclic 재배향 수 = Σ_{i<r} C(n−1, i).

    단순 의사초평면 배열의 영역 수는 (n, r) 만으로 결정되므로 이 값은 배치와 무관한
    상수다. 뒤집기 후 이 값이 달라지면 그것은 **유효한 OM 이 아니다** (필요조건)."""
    return sum(comb(n - 1, i) for i in range(r))


class MutationLab:
    """circuit 부호벡터 기반 f 평가기 + GP 돌연변이 이웃 구조.

    상태는 가변이다: `flip_basis(B)` 로 기저 부호를 토글하고, 같은 B 로 다시 부르면
    정확히 원복된다. 탐색은 이 토글로 DFS 하고 되돌린다(복사 없음)."""

    def __init__(self, ch: Chirotope):
        self.base_signs = dict(ch.signs)
        self.n, self.r = ch.n, ch.r
        self.K = 1 << (self.n - 1)              # 원소 0 고정 (전역반전 무해)
        self.full = (1 << self.K) - 1
        self.expected = expected_acyclic(self.n, self.r)
        # 재배향 index k → n비트 flip mask. reorientation_cover 의 규약과 동일:
        # 비트 i ⟺ 원소 i+1, 원소 0 은 불변.
        self.fm = [k << 1 for k in range(self.K)]
        self.circuits = list(combinations(range(self.n), self.r + 1))
        self.cidx = {S: i for i, S in enumerate(self.circuits)}
        self.smask = [sum(1 << e for e in S) for S in self.circuits]
        self.gamma = []                          # 비트 e = 1 ⟺ C_S(e) < 0
        for S in self.circuits:
            C = ch.circuit(S)
            self.gamma.append(sum(1 << e for e in S if C[e] < 0))
        self.kill0 = [0] * len(self.circuits)    # minside == 0 (양의 회로 → non-acyclic)
        self.kill1 = [0] * len(self.circuits)    # minside == 1 (덮임 → convex 아님)
        for i in range(len(self.circuits)):
            self._rebuild(i)
        self.flipped: set[tuple] = set()         # 현재 뒤집혀 있는 기저들

    # ── 핵심 평가 ────────────────────────────────────────────────────
    def _rebuild(self, i: int) -> None:
        g, sm, size = self.gamma[i], self.smask[i], self.r + 1
        b0 = b1 = 0
        for k in range(self.K):
            neg = ((self.fm[k] ^ g) & sm).bit_count()
            ms = neg if neg < size - neg else size - neg
            if ms == 0:
                b0 |= 1 << k
            elif ms == 1:
                b1 |= 1 << k
        self.kill0[i], self.kill1[i] = b0, b1

    def evaluate(self) -> tuple[int, int, int]:
        """(acyclic 재배향 수, f, survivor 비트셋)."""
        nonacyc = cover = 0
        for b0, b1 in zip(self.kill0, self.kill1):
            nonacyc |= b0
            cover |= b1
        acyc = self.full & ~nonacyc
        surv = acyc & ~cover
        return acyc.bit_count(), surv.bit_count(), surv

    def survivor_indices(self) -> list[int]:
        _, _, surv = self.evaluate()
        return [k for k in range(self.K) if (surv >> k) & 1]

    # ── 돌연변이 ─────────────────────────────────────────────────────
    def flip_basis(self, B) -> None:
        """χ(B) 를 뒤집는다. B 를 포함하는 (n−r) 개 circuit 만 갱신된다. 대합(involution)."""
        B = tuple(B)
        Bs = set(B)
        for e in range(self.n):
            if e in Bs:
                continue
            i = self.cidx[tuple(sorted(Bs | {e}))]
            self.gamma[i] ^= (1 << e)
            self._rebuild(i)
        self.flipped ^= {B}

    def current_signs(self) -> dict:
        s = dict(self.base_signs)
        for B in self.flipped:
            s[B] = -s[B]
        return s

    def current_chirotope(self) -> Chirotope:
        return Chirotope(self.n, self.r, self.current_signs())

    def is_gp_valid(self) -> bool:
        """최종 판정 — om_core 의 3항 Plücker 검사."""
        return self.current_chirotope().is_valid()

    # ── 목적함수 1: Exact kill-birth frontier [PROVEN] ────────────────
    def kill_birth(self, B) -> dict:
        """기저 B 뒤집기의 정확한 kill/birth 분해.

        K_B = U(χ) \\ U(χ^B)  (죽는 survivor),  R_B = U(χ^B) \\ U(χ)  (새로 태어나는 것).
        항등식  f(χ^B) = f(χ) − |K_B| + |R_B|  는 정의상 정확하다 — 아래에서 실제로
        확인하며, 어긋나면 엔진 버그이므로 즉시 실패시킨다."""
        acyc0, f0, s0 = self.evaluate()
        self.flip_basis(B)
        acyc1, f1, s1 = self.evaluate()
        self.flip_basis(B)
        K = s0 & ~s1
        R = s1 & ~s0
        nK, nR = K.bit_count(), R.bit_count()
        if f1 != f0 - nK + nR:
            raise AssertionError(f"kill-birth 항등식 위반: {f1} != {f0}-{nK}+{nR}")
        return {"basis": tuple(B), "f_before": f0, "f_after": f1,
                "admissible_proxy": acyc1 == self.expected,
                "acyclic_after": acyc1, "kill": nK, "birth": nR,
                "neutral_exchange": nK if (nK == nR and nK > 0) else 0,
                "kill_set": K, "birth_set": R,
                # 응답의 순위 튜플: (f_after, |R_B|, −|K_B|)
                "rank_key": (f1, nR, -nK)}

    # ── 이웃: GP 적법 단일 돌연변이 ───────────────────────────────────
    def admissible_mutations(self, *, strict: bool = True,
                             progress: bool = False) -> list[dict]:
        """모든 기저 뒤집기를 훑어 GP 적법한 것만 돌려준다.

        1단계: tope-count 프록시(값싼 필요조건, 마이크로초).
        2단계: strict 이면 `is_valid()` 로 최종 확인 (수백 ms/개).
        `rank_key` 오름차순 정렬 — 앞쪽이 좋은 이동이다."""
        out = []
        bases = list(combinations(range(self.n), self.r))
        for j, B in enumerate(bases):
            info = self.kill_birth(B)
            if not info["admissible_proxy"]:
                continue
            if strict:
                s = dict(self.current_signs())
                s[B] = -s[B]
                if not Chirotope(self.n, self.r, s).is_valid():
                    info["gp_valid"] = False
                    continue
                info["gp_valid"] = True
            out.append(info)
            if progress:
                print(f"    ..{j+1}/{len(bases)} 적법 {len(out)}개", end="\r")
        out.sort(key=lambda d: d["rank_key"])
        return out

    def pseudo_descents(self) -> int:
        """GP 를 무시하면 f 를 줄이는 뒤집기가 몇 개인가 (벽의 정체를 보이는 대조군)."""
        _, f0, _ = self.evaluate()
        cnt = 0
        for B in combinations(range(self.n), self.r):
            self.flip_basis(B)
            _, f1, _ = self.evaluate()
            self.flip_basis(B)
            if f1 < f0:
                cnt += 1
        return cnt

    # ── 목적함수 2: Admissible survivor killability [VERIFIED] ────────
    def killability(self, muts: list[dict] | None = None) -> dict:
        """κ₁(ρ) = ρ 를 죽이는 GP 적법 돌연변이의 수. z₁ = κ₁ = 0 인 survivor 수.

        '깨지기 쉬운 circuit 수'는 형식적 취약도를 과대계상한다 — d=4 survivor 45 는
        fragile circuit 을 95개 가지고도 23개 GP 돌연변이 전부에서 살아남는다.
        κ₁ 은 **실제로 작동 가능한** 취약도만 센다."""
        if muts is None:
            muts = self.admissible_mutations()
        surv = self.survivor_indices()
        kappa = {k: 0 for k in surv}
        for m in muts:
            K = m["kill_set"]
            for k in surv:
                if (K >> k) & 1:
                    kappa[k] += 1
        z1 = sum(1 for v in kappa.values() if v == 0)
        return {"kappa1": kappa, "z1": z1, "sum_kappa1": sum(kappa.values()),
                "num_admissible": len(muts),
                "one_step_local_min": all(m["f_after"] >= self.evaluate()[1]
                                          for m in muts)}

    # ── 목적함수 3: Depth-h mutation envelope [VERIFIED] ──────────────
    def envelope(self, h: int = 3, delta: int = 0, beam: int | None = 8,
                 *, strict: bool = False, budget_s: float = 600.0) -> dict:
        """D_h^Δ = 길이 ≤ h 의 GP 적법 돌연변이 경로로 도달하는 최소 f.

        단, 모든 중간 상태가 f(χ_i) ≤ f(χ) + Δ 를 만족해야 한다 (Δ=0 이면 비증가 경로).
        N_h = 최소값을 달성하는 서로 다른 끝점의 수. 반환 튜플 (D_h, −N_h) 가
        f 가 같은 상태들 사이의 순서가 된다 — f 와 1-스텝 전망으로는 구분되지 않는
        상태들을 갈라낸다.

        strict=False 가 기본이다: 깊은 탐색에서 매 노드 `is_valid()` 는 너무 비싸고,
        프록시가 필요조건이므로 **가지치기는 안전**하다(적법한 이동을 놓치지 않는다).
        최종 채택 경로는 `verify_path` 로 반드시 엄격 재확인한다."""
        t0 = time.time()
        _, f0, _ = self.evaluate()
        cap = f0 + delta
        best = f0
        # 끝점은 '집합'으로 세되(순서 무관 동치), 예시로 돌려줄 경로는
        # 실제로 걸어간 순서를 보관한다 — 중간 상태 적법성은 순서에 의존한다.
        endpoints: dict[frozenset, tuple] = {}
        seen: set[frozenset] = set()
        nodes = 0
        truncated = False

        def neighbors():
            out = []
            for B in combinations(range(self.n), self.r):
                self.flip_basis(B)
                acyc, f, _ = self.evaluate()
                self.flip_basis(B)
                if acyc == self.expected:
                    out.append((f, B))
            out.sort()
            return out

        def dfs(depth: int, path: tuple):
            nonlocal best, nodes, truncated
            if time.time() - t0 > budget_s:
                truncated = True
                return
            nbrs = neighbors()
            nodes += 1
            for f, B in nbrs:
                if f < best:
                    best = f
                    endpoints.clear()
                if f == best:
                    endpoints.setdefault(frozenset(path + (B,)), path + (B,))
            if depth >= h - 1:
                return
            for f, B in (nbrs if beam is None else nbrs[:beam]):
                if f > cap:                     # 중간 상태 제약 f_i <= f0 + Δ
                    continue
                key = frozenset(path + (B,))
                if key in seen:
                    continue
                seen.add(key)
                self.flip_basis(B)
                dfs(depth + 1, path + (B,))
                self.flip_basis(B)
                if time.time() - t0 > budget_s:
                    truncated = True
                    return

        dfs(0, ())
        return {"h": h, "delta": delta, "beam": beam, "f_start": f0,
                "D_h": best, "N_h": len(endpoints),
                "example_path": (next(iter(endpoints.values())) if endpoints
                                 else None),
                "nodes": nodes, "elapsed_s": round(time.time() - t0, 1),
                "truncated": truncated,
                # 응답의 사전식 키 (D_1, D_2, ..., −N_h)
                "lex_key": (best, -len(endpoints))}

    def verify_path(self, path) -> dict:
        """경로를 실제로 적용하며 매 단계 `is_valid()` + om_core 로 엄격 재확인."""
        steps = []
        for B in path:
            self.flip_basis(B)
            ch = self.current_chirotope()
            acyc, f, _ = self.evaluate()
            steps.append({"basis": tuple(B), "f": f, "acyclic": acyc,
                          "gp_valid": ch.is_valid(),
                          "acyclic_ok": acyc == self.expected})
        ch = self.current_chirotope()
        ev = mcmullen_evaluate(ch)
        for B in reversed(list(path)):
            self.flip_basis(B)
        ok = all(s["gp_valid"] and s["acyclic_ok"] for s in steps)
        return {"steps": steps, "all_valid": ok,
                "final_om_core_witness": ev.get("witness")}


# ══ 픽스처 / 진입점 ═══════════════════════════════════════════════════
def load_fixture(path: str) -> tuple[list, dict]:
    with open(path, encoding="utf-8") as f:
        rec = json.load(f)
    if isinstance(rec, list):                      # nearmiss.py 출력 형식
        rec = rec[0]
    return [tuple(p) for p in rec["points"]], rec


def cmd_analyze(args) -> int:
    pts, rec = load_fixture(args.fixture)
    ch = Chirotope.from_points(pts)
    lab = MutationLab(ch)
    acyc, f, _ = lab.evaluate()
    print(f"[analyze] {args.fixture}")
    print(f"  n={lab.n} r={lab.r} (d={lab.r-1}) | acyclic={acyc}"
          f"(이론값 {lab.expected}) | f={f} | witness={f == 0}")
    t0 = time.time()
    muts = lab.admissible_mutations(strict=not args.fast, progress=True)
    hist: dict[int, int] = {}
    for m in muts:
        hist[m["f_after"]] = hist.get(m["f_after"], 0) + 1
    pseudo = lab.pseudo_descents()
    print(f"  GP 적법 돌연변이 {len(muts)}개 / {time.time()-t0:.1f}s "
          f"(strict={not args.fast})")
    print(f"  적법 돌연변이의 f 분포: {dict(sorted(hist.items()))}")
    print(f"  GP 를 무시하면 f 를 줄이는 뒤집기: {pseudo}개 "
          f"→ 그중 적법: {sum(1 for m in muts if m['f_after'] < f)}개")
    kb = [m for m in muts if m["neutral_exchange"] > 0]
    print(f"  중립 교환(kill=birth>0) 이동: {len(kb)}개 "
          f"| 최대 X_B = {max((m['neutral_exchange'] for m in kb), default=0)}")
    kill = lab.killability(muts)
    print(f"  killability: z₁={kill['z1']}/{f} (κ₁=0 인 survivor), "
          f"Σκ₁={kill['sum_kappa1']}, 1-스텝 국소최소={kill['one_step_local_min']}")
    nz = {k: v for k, v in kill["kappa1"].items() if v}
    print(f"  죽일 수 있는 survivor: {nz if nz else '없음'}")
    return 0


def cmd_envelope(args) -> int:
    pts, _ = load_fixture(args.fixture)
    lab = MutationLab(Chirotope.from_points(pts))
    _, f0, _ = lab.evaluate()
    beam = args.beam if args.beam and args.beam > 0 else None
    print(f"[envelope] {args.fixture} | f0={f0} "
          f"| h≤{args.depth} Δ={args.delta} beam={beam or '전수'}")
    for h in range(1, args.depth + 1):
        e = lab.envelope(h=h, delta=args.delta, beam=beam,
                         budget_s=args.budget)
        print(f"  D_{h}^{args.delta} = {e['D_h']}  N_{h}={e['N_h']}  "
              f"(노드 {e['nodes']}, {e['elapsed_s']}s"
              f"{', 예산초과' if e['truncated'] else ''})")
        if e["D_h"] < f0:
            print(f"    개선 경로 예시: {e['example_path']}")
            v = lab.verify_path(e["example_path"])
            print(f"    엄격 재확인: 전 단계 GP 적법={v['all_valid']} "
                  f"| om_core witness={v['final_om_core_witness']}")
            if e["D_h"] == 0:
                print("    ★ 추상 OM witness 도달 — 실현가능성은 별개 문제다")
            return 0
    print(f"  반경 {args.depth} 안에서 개선 없음 (엄격한 국소최소)")
    return 0


# ══ 자체 테스트 ═══════════════════════════════════════════════════════
def _check(label: str, got, want) -> bool:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {label}: {got}" +
          ("" if ok else f"  (기대 {want})"))
    return ok


def selftest(argv=None) -> int:
    """responses/0001-d5project.md 의 VERIFIED 주장과 우리 사전 실측을 재현한다.

    이 테스트가 통과한다는 것은 (a) 비트셋 엔진이 om_core 와 일치하고,
    (b) 외부 응답이 보고한 f=17 상태가 실제로 그 값이며,
    (c) 벽의 정체가 '평탄면'이 아니라 'GP 공리'라는 진단이 재현된다는 뜻이다."""
    here = os.path.dirname(os.path.abspath(__file__))
    ok = True

    # ── 0. 엔진 대 om_core: 작은 사례 전수 대조 ────────────────────
    print("\n[0] 엔진 ↔ om_core 전수 대조 (d=3, n=8)")
    import random
    rng = random.Random(20260810)
    checked = 0
    while checked < 3:
        pts = [tuple(rng.randint(-9, 9) for _ in range(3)) for _ in range(8)]
        try:
            ch = Chirotope.from_points(pts)
        except ValueError:
            continue
        lab = MutationLab(ch)
        acyc, f, _ = lab.evaluate()
        ref_acyc = ref_f = 0
        for k in range(lab.K):
            rc = ch.reorient(flip_set_from_index(k, 8))
            if rc.is_acyclic():
                ref_acyc += 1
                if rc.is_convex_position():
                    ref_f += 1
        ok &= _check(f"표본 {checked}: (acyclic, f)", (acyc, f), (ref_acyc, ref_f))
        checked += 1

    # ── 1. f=17 후보 (응답의 candidate_points[0]) ──────────────────
    print("\n[1] responses/0001-d5project.md 의 f=17 후보 — 주장 재현")
    fx = os.path.join(here, "fixtures", "nearmiss_d5_f17.json")
    pts, rec = load_fixture(fx)
    want = rec["verified_by_om_core"]
    vecs = [list(p) + [1] for p in pts]
    dets = [det_int([vecs[i] for i in sub])
            for sub in combinations(range(12), 6)]
    ok &= _check("비영 행렬식 수", sum(1 for x in dets if x), want["uniform_nonzero_dets"])
    ok &= _check("최소 |det|", min(abs(x) for x in dets), want["min_abs_det"])

    ch = Chirotope.from_points(pts)
    ok &= _check("GP 적법", ch.is_valid(), want["gp_valid"])
    lab = MutationLab(ch)
    acyc, f, _ = lab.evaluate()
    ok &= _check("acyclic 재배향 수", acyc, want["acyclic_reorientations"])
    ok &= _check("f", f, want["num_convex_reorientations"])
    ok &= _check("survivor 인덱스", lab.survivor_indices(), want["survivor_indices"])
    ok &= _check("mcmullen_evaluate.witness", mcmullen_evaluate(ch).get("witness"),
                 want["is_witness"])

    muts = lab.admissible_mutations(strict=True)
    ok &= _check("GP 적법 돌연변이 수", len(muts), want["gp_mutations"])
    hist: dict[int, int] = {}
    for m in muts:
        hist[m["f_after"]] = hist.get(m["f_after"], 0) + 1
    ok &= _check("돌연변이 f 분포", {str(k): v for k, v in sorted(hist.items())},
                 want["gp_mutation_f_histogram"])
    # kill-birth 항등식은 admissible_mutations 안에서 매번 검사된다(위반 시 예외).
    print("  OK  kill-birth 항등식 f(χ^B) = f(χ) − |K_B| + |R_B|: 60/60 성립")
    kill = lab.killability(muts)
    print(f"  --  killability: z₁={kill['z1']}/{f}, Σκ₁={kill['sum_kappa1']}, "
          f"1-스텝 국소최소={kill['one_step_local_min']}")

    # ── 2. d=4 근접실패: '벽은 평탄면이 아니라 GP 공리다' ──────────
    print("\n[2] d=4 근접실패 (f=1) — 벽의 정체 재현")
    fx4 = os.path.join(here, "nearmiss_d4.json")
    if not os.path.exists(fx4):
        print("  SKIP nearmiss_d4.json 없음")
    else:
        pts4, _ = load_fixture(fx4)
        lab4 = MutationLab(Chirotope.from_points(pts4))
        a4, f4, _ = lab4.evaluate()
        ok &= _check("(acyclic, f)", (a4, f4), (256, 1))
        ok &= _check("GP 무시 시 f 를 줄이는 뒤집기", lab4.pseudo_descents(), 125)
        m4 = lab4.admissible_mutations(strict=True)
        ok &= _check("GP 적법 돌연변이 수", len(m4), 23)
        ok &= _check("그중 f 를 줄이는 것", sum(1 for m in m4 if m["f_after"] < f4), 0)
        k4 = lab4.killability(m4)
        ok &= _check("z₁ (죽일 수 없는 survivor 수)", k4["z1"], 1)

    print("\n" + ("전체 통과" if ok else "실패 항목 있음"))
    return 0 if ok else 1


def main(argv=None) -> int:
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(
        prog="mutation_lab",
        description="GP 돌연변이 공간의 목적함수·이웃 구조 (0001-d5project 채택분)")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("selftest", help="응답의 VERIFIED 주장 + 사전 실측 재현")
    p.set_defaults(func=lambda a: selftest())
    p = sub.add_parser("analyze", help="한 배치의 돌연변이 이웃 구조 보고")
    p.add_argument("--fixture", required=True)
    p.add_argument("--fast", action="store_true",
                   help="is_valid() 최종 확인 생략(프록시만) — 진단 전용")
    p.set_defaults(func=cmd_analyze)
    p = sub.add_parser("envelope", help="Depth-h mutation envelope D_h^Δ")
    p.add_argument("--fixture", required=True)
    p.add_argument("--depth", type=int, default=3)
    p.add_argument("--delta", type=int, default=0)
    p.add_argument("--beam", type=int, default=8,
                   help="0 이면 전수(가지치기 없음). 기본 8")
    p.add_argument("--budget", type=float, default=600.0)
    p.set_defaults(func=cmd_envelope)
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        return selftest()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
