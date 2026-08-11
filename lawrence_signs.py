"""lawrence_signs.py — **순수 rank-1 Lawrence 부호공간** 탐색 (탐색 결함 보정).

## 왜 이 공간인가 (직전 라운드의 진단)

`layer_search` 의 상태는 rank-2 layer m 장 = (order, signs) 이고, `random_layers` 는 그
둘을 **균등 표집**한다. 그런데 고전 Lawrence 구성에 대응하는 **곱형(product-form)** rank-2
OM 은 전체의

    2^(n−2) / (n−1)!        ← n=13 이면 약 1/233,888

밖에 안 된다. 즉 **답이 보장된 영역을 표본이 사실상 한 번도 방문하지 않았다.** n_L(3) 이
13 이 아니라 15 에서 멈춘 원인이 이것이다 (`docs/STATE.md` §1-B, research_log `탐색 결함 특정`).

이 모듈은 그 부분공간만 좌표로 삼는다. 상태는 rank-1 부호벡터 R=2m 장이고

    χ(j_0 < j_1 < … < j_{R−1}) = ∏_p s_p(j_p)                              (★)

가 고전 Lawrence union chirotope 다. order 순열이 없으므로 공간이 훨씬 순하다.

## rank-2 layer 로의 정확한 매장 (이 모듈의 핵심 보조정리)

QQ-0003 에 "order 를 항등으로 둔 rank-2 layer 는 부호벡터가 같은 rank-1 두 장만 재현한다"
는 장애가 적혀 있다. **항등 order 를 버리면 장애가 사라진다.** σ = s_{2c}, τ = s_{2c+1} 에
대해 ψ_c(a,b) := σ(a)τ(b) (a<b) 로 두고

    g(b) := σ(b)·τ(b)                                                (b ≥ 1)
    order := 0 에서 시작해 b=1,…,n−1 을 g(b)=+1 이면 오른쪽, −1 이면 왼쪽에 붙인 deque
    signs := σ

라 하면 `Rank2Layer.chi(a,b) = σ(a)σ(b)·sign(pos b − pos a) = σ(a)σ(b)·g(b) = σ(a)τ(b)`
로 a<b 에서 **항등적으로 일치**한다. (deque 구성이므로 b 는 항상 양 끝에 놓여
sign(pos b − pos a) = g(b) 가 모든 a<b 에서 성립한다.)

따라서 이 공간의 모든 상태는 `extended_lawrence.realize_union` 의 **정수 좌표 실현 증명서**를
그대로 물려받는다 — 탐색 도중 한 번도 실현가능성을 잃지 않는다.

## 게이지 (직교하는 두 대칭)

  (A) 한 장의 전역 반전 s_p → −s_p 는 (★) 에서 χ → −χ 다. χ 와 −χ 는 같은 OM.
  (B) 원소 e 에서 **모든 장을 동시에** 뒤집으면(s_p(e) → −s_p(e), ∀p) 정렬된 basis 안에서
      e 는 정확히 한 위치를 차지하므로 χ(B) 는 e ∈ B 일 때만 한 번 뒤집힌다 = **원소 e 의
      재배향**. witness 판정은 재배향 궤도의 성질이므로 불변이다.

(B) 로 `s_0 ≡ +1` 을 만들고, 남은 (A)(p ≥ 1) 로 `s_p(0) = +1` 을 만든다. 자유 비트는

    (R − 1) · (n − 1)          m=3, n=13 → 5·12 = 60

이고 이동은 그 비트 하나 뒤집기다. **모든 궤도가 이 대표원소를 하나 이상 가지므로 전수
탐색은 완전하다** (UNSAT 을 말할 수 있다).

## 신뢰 경계 — 이 모듈은 판정 권한이 없다

내부 루프는 (★) 로 chirotope 를 직접 만들고 `is_valid()`(GP 전수, 후보당 9만 검사)를
**건너뛴다**. 이것은 `mutation_lab` 과 같은 가속기 지위이며, f=0 이 나오면 반드시

    to_layers → lawrence_union_chirotope(= fail-closed GP 게이트) → mcmullen_evaluate
              → realize_union(정수 좌표 증명서)

의 신뢰 경로를 전부 통과시킨 뒤에만 witness 로 기록한다. GP 게이트가 거부하면 그것은
HI-0001 의 union validity 주장에 대한 반례이므로 상태를 보존해 함께 보고한다.

## 무엇을 재는 실험인가

고전 구성의 크기는 n = 5m−2 이고, 이것이 곧 문헌 상한의 출처다:
n=5m−2 witness ⟹ ν(d) ≤ 5m−3 = (5d−1)/2 = `layer_search.known_upper_bound(d)`.

    m=2 → n=8  (= n_L(2), 이미 전수로 확정)
    m=3 → n=13 ← **반드시 존재한다.** 찾으면 탐색 보정 완료 + QQ-0003 의 (3,13) layer tuple 확보
    m=3, n=12  ← 이 family 에서 여기를 뚫으면 ν(5) ≤ 11 = 2d+1, 즉 **Larman 도달**

    python lawrence_signs.py selftest
    python lawrence_signs.py climb --d 5 --n 13 --hours 2 --out climb_d5_n13_signs.json
    python lawrence_signs.py exhaustive --d 3 --n 7
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import deque
from itertools import combinations
from math import factorial

from om_core import Chirotope, mcmullen_evaluate
from extended_lawrence import Rank2Layer, lawrence_union_chirotope, realize_union
from layer_search import CoverageScanner, bound_gain, known_upper_bound


def classical_n(m: int) -> int:
    """고전 Lawrence 구성이 witness 를 주는 크기. 이것이 문헌 상한의 출처다.

    n = 5m−2 witness ⟹ ν(d) ≤ 5m−3 = (5d−1)/2 = known_upper_bound(d)  (d = 2m−1).
    **rank = 2m 인 짝수 rank 에만 있는 공식이다.** 홀수 rank 의 대응값은 확보돼 있지 않다
    — `measure_f` 로 직접 재야 한다."""
    return 5 * m - 2


# ── 상태 ─────────────────────────────────────────────────────────────
def free_bits(n: int, rank: int, *, band: bool = True) -> list[tuple[int, int]]:
    """게이지 고정 후 남는 자유 비트 (p, e) 목록. s_0 ≡ +1, s_p(0) = +1 을 고정한다.

    `band=True`(기본) 면 **χ 에 실제로 쓰이는 성분만** 남긴다. 정렬된 basis
    j_0<…<j_{R−1} 에서 위치 p 가 가질 수 있는 원소 인덱스는 p ≤ j_p ≤ n−R+p 뿐이므로,
    그 밖의 s_p(e) 는 어떤 basis 에서도 곱해지지 않는다 — 뒤집어도 chirotope 가 전혀
    바뀌지 않는다(실측: 밴드 밖 뒤집기 0/전부 불변, (3,6)·(4,8)·(5,10)·(6,13)).

        자유도  (R−1)(n−1)  →  (R−1)(n−R+1)

    이것은 Ramírez Alfonsín 계열의 **chessboard** 관점과 같은 축소다. r×n 부호행렬 A 의
    chessboard 는 s(i,j) = a_{i,j}a_{i,j+1}a_{i+1,j}a_{i+1,j+1} 로 정의되며 열 재배향과
    행 전역반전에 불변이고(실측 확인), 우리 게이지 고정 상태와 일대일 대응한다.
    실제 서로 다른 chirotope 수는 그보다도 작아 2^((R−1)(n−R+1)−(R−2)) 였다
    ((3,5..7)·(4,6..8) 전수 실측) — 남은 (R−2) 만큼은 아직 명시적으로 제거하지 않았으므로
    이 열거는 **완전하되 중복을 포함**한다(전수 결론의 타당성에는 영향이 없다).

    남은 (R−2) 의 정체도 밝혀졌다. 행 전역반전 게이지를 `s_p(0)=+1` 로 걸었는데 행 p≥1 의
    밴드는 [p, n−R+p] 이므로 **열 0 은 밴드 밖**이다 — 즉 그 게이지는 관측 가능한 것을
    아무것도 고정하지 못했다. 밴드 안 성분 `s_p(p)=+1` 로 다시 걸면(행 p 를 통째로 뒤집는
    것은 χ→−χ 라 OM 도 witness 판정도 그대로) 행마다 1비트씩 더 사라져

        자유도  (R−1)(n−R+1)  →  (R−1)(n−R)

    가 된다. 실측 잉여가 (R−2) 였던 것은 서로 다른 chirotope 를 ±χ 로 나누어 세지 않았기
    때문이고, witness 판정은 ±χ 에 무관하므로 여기서는 (R−1) 을 전부 뺄 수 있다.

    `band=False` 는 축소 이전의 동작이다."""
    if not band:
        return [(p, e) for p in range(1, rank) for e in range(1, n)]
    # 행 p 의 밴드는 [p, n−rank+p]; 그중 맨 왼쪽 (p, p) 를 행 게이지로 고정한다.
    return [(p, e) for p in range(1, rank)
            for e in range(p + 1, min(n - 1, n - rank + p) + 1)]


def identity_state(n: int, rank: int) -> list[list[int]]:
    """모든 부호가 + 인 게이지 고정 상태."""
    return [[1] * n for _ in range(rank)]


def random_state(n: int, rank: int, rng: random.Random) -> list[list[int]]:
    st = identity_state(n, rank)
    for (p, e) in free_bits(n, rank):
        st[p][e] = rng.choice((-1, 1))
    return st


def state_from_index(idx: int, n: int, rank: int) -> list[list[int]]:
    """전수 탐색용 — 자유 비트를 정수 하나로 인덱싱한다."""
    st = identity_state(n, rank)
    for k, (p, e) in enumerate(free_bits(n, rank)):
        if (idx >> k) & 1:
            st[p][e] = -1
    return st


def clone(state) -> list[list[int]]:
    return [row[:] for row in state]


# ── (★) 직접 곱 공식 — 가속기, 판정 권한 없음 ────────────────────────
def fast_chirotope(state) -> Chirotope:
    """χ(j_0<…<j_{R−1}) = ∏_p s_p(j_p). **is_valid 게이트를 통과하지 않는다.**"""
    rank = len(state)
    n = len(state[0])
    signs = {}
    for basis in combinations(range(n), rank):
        v = 1
        for p in range(rank):
            v *= state[p][basis[p]]
        signs[basis] = v
    return Chirotope(n, rank, signs)


def evaluate(state, stop_after: int | None = None) -> tuple[int, list[int]]:
    """(f = convex 재배향 수, survivor 목록). f=0 이면 witness 후보다."""
    return CoverageScanner(fast_chirotope(state)).survivors(stop_after=stop_after)


# ── rank-2 layer 로의 매장 (신뢰 경로 진입점) ────────────────────────
def pair_to_layer(sigma, tau) -> Rank2Layer:
    """ψ(a,b) = σ(a)τ(b) (a<b) 를 재현하는 rank-2 layer. 모듈 docstring 의 보조정리."""
    n = len(sigma)
    dq = deque([0])
    for b in range(1, n):
        if sigma[b] * tau[b] > 0:
            dq.append(b)
        else:
            dq.appendleft(b)
    return Rank2Layer(tuple(dq), tuple(sigma))


def to_layers(state) -> tuple[Rank2Layer, ...]:
    """rank-1 부호벡터 2m 장 → rank-2 layer m 장. union 이 정확히 보존된다."""
    if len(state) % 2:
        raise ValueError("rank-1 장 수는 짝수여야 한다 (rank = 2m)")
    return tuple(pair_to_layer(state[2 * c], state[2 * c + 1])
                 for c in range(len(state) // 2))


def verified_chirotope(state) -> Chirotope:
    """신뢰 경로 — fail-closed GP 게이트를 통과한 union chirotope. **짝수 rank 전용.**"""
    return lawrence_union_chirotope(to_layers(state))


# ── 실현 증명서 (rank-1 블록 — 홀수 rank 도 덮는다) ─────────────────
_REALIZATION_T_LADDER = (3, 11, 101, 1009, 40321, 3628801)


def realize_signs(state, target=None) -> dict | None:
    """rank-1 블록만으로 만드는 정수 좌표 실현. w_j[i] = t^(i·λ_j)·s_i(j), λ_j = j.

        det(B) = Σ_π sgn(π) · t^(Σ_p π(p)·λ_{j_p}) · ∏_p s_{π(p)}(j_p)

    λ 와 j 가 **둘 다 강증가**라 재배열 부등식의 최대점은 **π = 항등 하나뿐**이다.
    HI-0004/QQ-0002 가 rank-2 블록에서 걱정한 λ 동점 문제가 rank-1 블록에서는
    구조적으로 발생하지 않는다. 항등 항은 sgn=+1 이고 곱이 정확히 χ(B) 이므로
    t > R! 이면 나머지 R!−1 개 항을 크기로 압도한다.

    그래도 **일반 정리로 가정하지 않는다** — 후보마다 좌표를 실제로 만들어 `om_core` 로
    대조하고, 대조에 성공한 좌표 자체가 그 후보의 증명서다. 실패하면 None (fail-closed).
    `extended_lawrence.realize_union`(rank-2 블록) 과 독립 경로이며, 짝수 rank 에서는
    둘 다 붙여 교차 확인한다."""
    rank, n = len(state), len(state[0])
    if target is None:
        target = fast_chirotope(state)
    for t in _REALIZATION_T_LADDER:
        vectors = [[t ** (i * j) * state[i][j] for i in range(rank)]
                   for j in range(n)]
        try:
            cand = Chirotope.from_vectors(vectors)
        except ValueError:
            continue                       # 균일하지 않으면 다음 t
        if cand.signs == target.signs:
            return {"kind": "integer_vector_realization/rank1-blocks",
                    "rank": rank, "n": n, "lambda": "j", "scale_t": t,
                    "t_exceeds_rank_factorial": t > factorial(rank),
                    "vectors": vectors,
                    "verified_by": "om_core.Chirotope.from_vectors 부호 완전 일치",
                    "insight_ids": ["HI-0004"]}
    return None


# ── 탐색 ─────────────────────────────────────────────────────────────
def neighbors(state) -> list:
    """자유 비트 하나 뒤집기. m=3, n=13 이면 60개."""
    n, rank = len(state[0]), len(state)
    out = []
    for (p, e) in free_bits(n, rank):
        nxt = clone(state)
        nxt[p][e] = -nxt[p][e]
        out.append(nxt)
    return out


def _witness_record(state, d: int, n: int, *, evals: int = 0,
                    restarts: int = 0, elapsed: float = 0.0, seed: int = -1,
                    say=lambda _msg: None) -> dict:
    """f=0 후보를 신뢰 경로에 태운다. 홀·짝 rank 를 모두 다룬다.

    게이트 순서: `is_valid`(GP 전수, fail-closed) → `mcmullen_evaluate` → 실현 증명서.
    짝수 rank 면 rank-2 layer 경로도 함께 붙여 **독립 이중 확인**한다."""
    rank = len(state)
    ch = fast_chirotope(state)
    if not ch.is_valid():
        say("  ✗ GP 게이트 거부 — 이 상태는 OM 이 아니다 "
            "(rank-1 Lawrence union validity 에 대한 반례 후보)")
        return {"status": "GP_VIOLATION", "d": d, "n": n, "r": rank,
                "sign_vectors": [list(v) for v in state],
                "evals": evals, "elapsed_s": round(elapsed, 1), "seed": seed}
    ev = mcmullen_evaluate(ch)
    cert = realize_signs(state, target=ch)

    cross = None                       # 짝수 rank 한정 독립 경로
    if rank % 2 == 0:
        try:
            layers = to_layers(state)
            union = lawrence_union_chirotope(layers)
            cross = {"path": "rank-2 layer union",
                     "matches_product_formula": union.signs == ch.signs,
                     "layers": [L.to_dict() for L in layers],
                     "rank2_block_certificate":
                         realize_union(layers, target=union) is not None}
        except ValueError as exc:
            cross = {"path": "rank-2 layer union", "error": str(exc)}

    cls = classical_n(rank // 2) if rank % 2 == 0 else None
    say(f"  ★★ witness! om_core={ev.get('witness')} | GP 게이트 통과 "
        f"| 실현 증명서={'있음' if cert else '없음'} "
        f"| ν({d}) ≤ {n-1} (문헌 {known_upper_bound(d)}, 개선폭 {bound_gain(d, n)})"
        + (f" | 고전 구성 n={cls} 대비 {cls - n:+d}" if cls else " | 홀수 rank"))
    return {"status": "WITNESS", "d": d, "n": n, "r": rank,
            "implied_upper_bound": n - 1,
            "known_upper_bound": known_upper_bound(d),
            "bound_gain": bound_gain(d, n),
            "classical_n": cls,
            "beats_classical": (n < cls) if cls else None,
            "om_core_evaluate": ev,
            "sign_vectors": [list(v) for v in state],
            "realization_certificate": cert,
            "realizability": "REALIZABLE" if cert else "CLAIMED_UNVERIFIED",
            "cross_check": cross,
            "evals": evals, "restarts": restarts,
            "elapsed_s": round(elapsed, 1), "seed": seed}


def climb(d: int, n: int, *, seed: int = 0, budget_s: float = 600.0,
          stall_limit: int = 60, verbose: bool = True, log=None) -> dict:
    """부호공간 언덕오르기. 이동은 자유 비트 하나 뒤집기뿐이다. 홀·짝 rank 모두."""
    rank = d + 1
    if d < 1:
        raise ValueError("d ≥ 1 이어야 함")
    if n <= rank:
        raise ValueError("n > rank 이어야 함")
    rng = random.Random(seed)
    t0 = time.time()
    best_f = None
    best_state = None
    evals = restarts = 0

    def say(msg):
        if verbose:
            print(msg, flush=True)
        if log is not None:
            log.append(msg)

    cls = classical_n(rank // 2) if rank % 2 == 0 else None
    say(f"[signs] d={d} n={n} rank={rank} (rank-1 부호벡터 {rank}장, "
        f"자유 비트 {len(free_bits(n, rank))}개) | 예산 {budget_s:.0f}s")
    say("        " + (f"고전 구성 n={cls} → 이 n 은 "
                      + ("고전과 동일 (반드시 존재)" if n == cls
                         else f"고전 대비 {cls-n:+d}")
                      if cls else "홀수 rank — 고전 구성 공식 없음")
        + f" | 문헌 상한 U({d})={known_upper_bound(d)}, bound_gain={bound_gain(d, n)}")

    while time.time() - t0 < budget_s:
        cur = random_state(n, rank, rng)
        cur_f = evaluate(cur)[0]
        evals += 1
        restarts += 1
        stall = 0
        while stall < stall_limit and time.time() - t0 < budget_s:
            cand_list = neighbors(cur)
            rng.shuffle(cand_list)
            improved = False
            for cand in cand_list:
                if time.time() - t0 > budget_s:
                    break
                f = evaluate(cand, stop_after=cur_f)[0]
                evals += 1
                if f < cur_f:
                    cur, cur_f = cand, f
                    improved = True
                    break
            if best_f is None or cur_f < best_f:
                best_f, best_state = cur_f, clone(cur)
                say(f"  최선 f={best_f} (평가 {evals}, {time.time()-t0:.0f}s)")
            if cur_f == 0:
                return _witness_record(cur, d, n, evals=evals,
                                       restarts=restarts,
                                       elapsed=time.time() - t0,
                                       seed=seed, say=say)
            if not improved:
                stall += 1
                for cand in cand_list:      # 평탄면: 같은 f 로 한 걸음
                    evals += 1
                    if evaluate(cand, stop_after=cur_f)[0] == cur_f:
                        cur = cand
                        break
            else:
                stall = 0

    return {"status": "NO_WITNESS", "d": d, "n": n, "r": rank,
            "best_f": best_f,
            "classical_n": classical_n(rank // 2) if rank % 2 == 0 else None,
            "sign_vectors": ([list(v) for v in best_state] if best_state else None),
            "evals": evals, "restarts": restarts,
            "elapsed_s": round(time.time() - t0, 1), "seed": seed,
            "note": "witness 를 못 찾은 것은 없다는 증명이 아니다 (전수가 아니면)"}


def exhaustive(d: int, n: int, *, budget_s: float | None = None,
               verbose: bool = True, collect: int = 4,
               stop_on_first: bool = False) -> dict:
    """게이지 고정 자유 비트를 전수로 훑는다. 완주하면 **없음이 증명**된다.

    모든 재배향·전역부호 궤도가 이 대표원소 집합에 하나 이상 들어 있으므로,
    전수 후 witness 0 이면 '이 family 의 그 (n, rank) 에는 witness 가 없다'가 결론이다.
    `stop_on_first` 는 임계 n 만 찾을 때 쓴다(밀도는 못 잰다)."""
    rank = d + 1
    if n <= rank:
        raise ValueError("n > rank 이어야 함")
    bits = free_bits(n, rank)
    total = 1 << len(bits)
    t0 = time.time()
    found: list[dict] = []
    best_f = None
    scanned = 0
    for idx in range(total):
        st = state_from_index(idx, n, rank)
        f = evaluate(st, stop_after=None)[0]
        scanned += 1
        if best_f is None or f < best_f:
            best_f = f
            if verbose:
                print(f"  최선 f={best_f} ({scanned}/{total}, "
                      f"{time.time()-t0:.0f}s)", flush=True)
        if f == 0:
            if len(found) < collect:
                found.append(_witness_record(
                    st, d, n, evals=scanned, elapsed=time.time() - t0,
                    say=(print if verbose else (lambda _m: None))))
            else:
                found.append({"status": "WITNESS",
                              "sign_vectors": [list(v) for v in st]})
            if stop_on_first:
                break
        if budget_s is not None and time.time() - t0 > budget_s:
            break
    complete = scanned == total
    return {"status": ("WITNESS" if found else
                       ("NO_WITNESS_PROVEN" if complete else "NO_WITNESS_PARTIAL")),
            "d": d, "n": n, "r": rank,
            "classical_n": classical_n(rank // 2) if rank % 2 == 0 else None,
            "num_states": total, "scanned": scanned, "complete": complete,
            "stopped_on_first": stop_on_first and bool(found),
            "num_witnesses": len(found), "best_f": best_f,
            "witness_rate": (None if stop_on_first
                             else (len(found) / scanned if scanned else None)),
            "witnesses": found[:collect],
            "elapsed_s": round(time.time() - t0, 1)}


# ── f(d) 측정 ────────────────────────────────────────────────────────
def measure_f(d: int, *, n_max: int | None = None,
              budget_s: float | None = None, verbose: bool = True) -> dict:
    """f(d) = **rank d+1 Lawrence OM 이 witness 를 하나도 못 만드는 n 의 최대치.**

    이 family 는 삭제에 닫혀 있다 — 부호벡터를 부분집합으로 제한하면 그것이 그대로
    제한된 union 이다. 그리고 볼록위치는 부분집합에 유전되므로 **witness 존재는 n 에
    단조**다. 따라서 임계 N(d) = (witness 가 처음 생기는 n) 하나만 찾으면

        f(d) = N(d) − 1

    이고, 우리는 n = rank+1 부터 올리며 각 n 에서 전수로 판정한다. 전수가 완주하지 못하면
    그 n 에서 멈추고 **하한만** 보고한다(추정으로 f 를 확정하지 않는다).

    ⚠ f(d) 는 이 family 의 조합적 용량이다. 실현가능성은 별개이며, witness 가 나오면
    `realize_signs` 로 좌표 증명서를 붙여 ν(d) 결론으로 승격할 수 있는지 함께 기록한다."""
    rank = d + 1
    rows = []
    n = rank + 1
    while n_max is None or n <= n_max:
        res = exhaustive(d, n, verbose=False, stop_on_first=True,
                         budget_s=budget_s)
        row = {k: res[k] for k in ("n", "status", "num_states", "scanned",
                                   "complete", "num_witnesses", "best_f",
                                   "elapsed_s")}
        rows.append(row)
        if verbose:
            print(f"  n={n:3d} | 상태 2^{len(free_bits(n, rank)):2d} = "
                  f"{res['num_states']:>15,} | {res['status']:<18} "
                  f"| 최선 f={res['best_f']} | {res['elapsed_s']}s", flush=True)
        if res["num_witnesses"]:
            cert = res["witnesses"][0].get("realization_certificate")
            return {"d": d, "rank": rank, "status": "EXACT",
                    "f": n - 1, "threshold_n": n,
                    "known_upper_bound": known_upper_bound(d),
                    "classical_n": (classical_n(rank // 2)
                                    if rank % 2 == 0 else None),
                    "threshold_witness_realizable": cert is not None,
                    "witness": res["witnesses"][0], "rows": rows}
        if not res["complete"]:
            return {"d": d, "rank": rank, "status": "LOWER_BOUND_ONLY",
                    "f": None, "f_at_least": n - 1,
                    "note": f"n={n} 전수 미완주 — 여기서부터는 결론 없음", "rows": rows}
        n += 1
    return {"d": d, "rank": rank, "status": "LOWER_BOUND_ONLY",
            "f": None, "f_at_least": n - 1,
            "note": f"n_max={n_max} 까지 witness 없음", "rows": rows}


# ── 자체 검증 ────────────────────────────────────────────────────────
def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'} {label}: {got}"
              + ("" if good else f"  (기대 {want})"))

    rng = random.Random(20260811)

    print("\n[1] 매장 보조정리 — ψ_c(a,b) = σ(a)τ(b) 를 Rank2Layer 가 정확히 재현하는가")
    bad = 0
    for (n, m) in [(6, 2), (8, 2), (9, 3), (13, 3)]:
        for _ in range(25):
            st = random_state(n, 2 * m, rng)
            for c in range(m):
                L = pair_to_layer(st[2 * c], st[2 * c + 1])
                for a, b in combinations(range(n), 2):
                    if L.chi(a, b) != st[2 * c][a] * st[2 * c + 1][b]:
                        bad += 1
    chk("layer chi 불일치", bad, 0)

    print("\n[2] 가속기 ↔ 신뢰 경로 — 직접 곱 (★) 과 lawrence_union_chirotope 가 같은가")
    bad = gp_reject = 0
    for (n, m) in [(6, 2), (8, 2), (9, 3), (13, 3)]:
        for _ in range(15):
            st = random_state(n, 2 * m, rng)
            fast = fast_chirotope(st)
            try:
                trusted = verified_chirotope(st)
            except ValueError:
                gp_reject += 1
                continue
            if fast.signs != trusted.signs:
                bad += 1
    chk("union 부호 불일치", bad, 0)
    chk("GP 게이트 거부 (0 이 아니면 HI-0001 반례)", gp_reject, 0)

    print("\n[3] 게이지 — (A) 장 전역반전과 (B) 원소 동시반전이 f 를 보존하는가")
    bad_a = bad_b = 0
    for (n, m) in [(7, 2), (9, 3)]:
        for _ in range(6):
            st = random_state(n, 2 * m, rng)
            base = evaluate(st)[0]
            p = rng.randrange(2 * m)
            st_a = clone(st); st_a[p] = [-x for x in st_a[p]]
            if evaluate(st_a)[0] != base:
                bad_a += 1
            e = rng.randrange(n)
            st_b = clone(st)
            for q in range(2 * m):
                st_b[q][e] = -st_b[q][e]
            if evaluate(st_b)[0] != base:
                bad_b += 1
    chk("(A) 전역반전이 f 를 바꾼 횟수", bad_a, 0)
    chk("(B) 원소 동시반전이 f 를 바꾼 횟수", bad_b, 0)

    print("\n[4] 평가기 대조 — CoverageScanner f 와 om_core 직접 판정이 일치하는가")
    bad = 0
    for _ in range(4):
        st = random_state(8, 4, rng)
        ch = fast_chirotope(st)
        f = CoverageScanner(ch).survivors()[0]
        direct = sum(1 for k in range(1 << (ch.n - 1))
                     if ch.reorient([e for e in range(ch.n)
                                     if (k << 1) >> e & 1]).is_convex_position())
        if f != direct:
            bad += 1
    chk("f 불일치", bad, 0)

    print("\n[5] m=2 보정 — 고전 구성 크기 n = 5m−2 = 8 에 witness 가 있어야 한다")
    res8 = climb(3, 8, seed=7, budget_s=90, verbose=False)
    chk("(m=2, n=8) status", res8["status"], "WITNESS")
    if res8["status"] == "WITNESS":
        chk("om_core witness", res8["om_core_evaluate"].get("witness"), True)
        chk("실현 증명서 존재", res8["realization_certificate"] is not None, True)
        cert = res8["realization_certificate"]
        rebuilt = Chirotope.from_vectors(cert["vectors"])
        chk("증명서 재검증(좌표 → 부호 완전 일치)",
            rebuilt.signs == verified_chirotope(
                [list(v) for v in res8["sign_vectors"]]).signs, True)

    print("\n[6] 상한 대조 — 고전 구성이 문헌 상한을 정확히 재현하는가")
    for d_ in (3, 5, 7, 9, 11):
        m_ = (d_ + 1) // 2
        chk(f"d={d_}: 5m−3 == known_upper_bound",
            classical_n(m_) - 1, known_upper_bound(d_))

    print("\n[7] rank-1 블록 실현 — 홀수 rank 포함, t > R! 이면 항상 성공해야 한다")
    bad = 0
    for rank in (2, 3, 4, 5, 6):
        for n in (rank + 1, rank + 4):
            for _ in range(5):
                st = random_state(n, rank, rng)
                if realize_signs(st) is None:
                    bad += 1
    chk("실현 실패 횟수", bad, 0)

    print("\n[8] f(d) 측정기 — 알려진 값에서 보정")
    # 단조성으로 f 는 임계값 하나다. d=2(rank 3)는 전수가 매우 싸다.
    f2 = measure_f(2, n_max=12, verbose=False)
    chk("f(2) 측정 완료", f2["status"], "EXACT")
    chk("f(2) 임계 witness 가 실현가능", f2.get("threshold_witness_realizable"), True)
    # d=3 은 이미 전수로 확인돼 있다: n=7 없음 / n=8 있음 → f(3)=7
    chk("(3,7) 전수 = 없음", exhaustive(3, 7, verbose=False,
                                       stop_on_first=True)["status"],
        "NO_WITNESS_PROVEN")

    print("\n[9] 단조성 — witness at n ⟹ witness at n+1 (원소 추가)")
    # family 는 삭제에 닫혀 있으므로, witness 상태에 원소를 하나 덧붙여도 witness 여야 한다.
    bad = 0
    for _ in range(3):
        base = climb(3, 8, seed=rng.randrange(10 ** 6), budget_s=60,
                     verbose=False)
        if base["status"] != "WITNESS":
            continue
        st = [list(v) for v in base["sign_vectors"]]
        for extra_sign in ((1,) * 4, (-1, 1, -1, 1)):
            grown = [row + [s] for row, s in zip(st, extra_sign)]
            if evaluate(grown)[0] != 0:
                bad += 1
    chk("원소 추가 후 witness 가 깨진 횟수", bad, 0)

    print("\n" + ("전체 통과" if ok else "실패 항목 있음"))
    return 0 if ok else 1


# ── CLI ──────────────────────────────────────────────────────────────
def _stamp_snapshot(rec: dict) -> dict:
    snap = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".exec_sync.json")
    if os.path.exists(snap):
        with open(snap, encoding="utf-8") as fh:
            rec["snapshot_id"] = json.load(fh).get("snapshot_id")
    return rec


def _save(path, rec):
    if path:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        print(f"저장: {path}")


def main(argv=None) -> int:
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    ap = argparse.ArgumentParser(
        prog="lawrence_signs",
        description="순수 rank-1 Lawrence 부호공간 탐색")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("climb", help="고정 (d, n) 에서 witness 탐색")
    p.add_argument("--d", type=int, required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--hours", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=20260811)
    p.add_argument("--out", default=None)

    q = sub.add_parser("exhaustive", help="게이지 고정 전수 — 완주하면 없음이 증명된다")
    q.add_argument("--d", type=int, required=True)
    q.add_argument("--n", type=int, required=True)
    q.add_argument("--hours", type=float, default=None)
    q.add_argument("--out", default=None)

    r = sub.add_parser("fmeasure",
                       help="f(d) = Lawrence OM 이 witness 를 못 만드는 n 의 최대치")
    r.add_argument("--d", type=int, required=True)
    r.add_argument("--n-max", type=int, default=None)
    r.add_argument("--hours", type=float, default=None,
                   help="각 n 의 전수에 주는 예산. 초과하면 하한만 보고한다")
    r.add_argument("--out", default=None)

    sub.add_parser("selftest")
    args = ap.parse_args(argv)

    if args.cmd == "climb":
        log: list[str] = []
        res = _stamp_snapshot(climb(args.d, args.n, seed=args.seed,
                                    budget_s=args.hours * 3600, log=log))
        print(f"\n[결과] {res['status']} | d={args.d} n={args.n} "
              f"| 최선 f={res.get('best_f', 0)} | 평가 {res['evals']}회 "
              f"| {res['elapsed_s']}s")
        res["log"] = log
        _save(args.out, res)
        return 0
    if args.cmd == "exhaustive":
        res = _stamp_snapshot(exhaustive(
            args.d, args.n,
            budget_s=(args.hours * 3600 if args.hours else None)))
        print(f"\n[전수] {res['status']} | d={args.d} n={args.n} "
              f"| 상태 {res['scanned']}/{res['num_states']} "
              f"| witness {res['num_witnesses']}개 | 최선 f={res['best_f']} "
              f"| {res['elapsed_s']}s")
        _save(args.out, res)
        return 0
    if args.cmd == "fmeasure":
        print(f"[fmeasure] d={args.d} rank={args.d+1} — n 을 올리며 각 n 을 전수 판정")
        res = _stamp_snapshot(measure_f(
            args.d, n_max=args.n_max,
            budget_s=(args.hours * 3600 if args.hours else None)))
        if res["status"] == "EXACT":
            print(f"\n[f측정] f({args.d}) = {res['f']}  "
                  f"(임계 n = {res['threshold_n']}, 즉 n={res['threshold_n']} 에서 "
                  f"witness 가 처음 생긴다)")
            print(f"        문헌 상한 U({args.d}) = {res['known_upper_bound']}"
                  + (f" · 고전 구성 n = {res['classical_n']}"
                     if res["classical_n"] else " · 홀수 rank")
                  + f" · 임계 witness 실현가능={res['threshold_witness_realizable']}")
        else:
            print(f"\n[f측정] f({args.d}) 미확정 — f ≥ {res['f_at_least']} "
                  f"({res['note']})")
        _save(args.out, res)
        return 0
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
