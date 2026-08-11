"""audit_lawrence.py — HI-0001 (extended Lawrence rank-2 union) 반증 시험.

ledger 의 falsification_plan 을 그대로 실행하고, 거기 없던 항목 둘을 추가한다.
  T1 union 이 항상 GP 적법한가 (계획 1항)
  T2 layer 재배향 ↔ union 재배향 교환 (계획 2항)
  T3 '각 layer 가 realizable 이므로 union 도 realizable' 의 **자명한 실현**이 실제로
     union chirotope 를 재현하는가 — REALIZABLE 라벨의 근거 검사
  T4 이 class 가 답이 알려진 영역에서 witness 를 실제로 담는가 (d=3, (8,4))
"""
import pathlib
import random
import sys
from itertools import combinations

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from console import enable_utf8_stdout  # noqa: E402
from om_core import Chirotope, mcmullen_evaluate  # noqa: E402
from extended_lawrence import (Rank2Layer, lawrence_union_chirotope,  # noqa: E402
                               generate_extended_lawrence_rank2)
from mutation_lab import MutationLab  # noqa: E402

enable_utf8_stdout()
rng = random.Random(20260810)


def rand_layers(n, m):
    out = []
    for _ in range(m):
        order = list(range(n)); rng.shuffle(order)
        signs = [rng.choice((-1, 1)) for _ in range(n)]
        out.append(Rank2Layer(tuple(order), tuple(signs)))
    return tuple(out)


print("=== T1. union 은 항상 GP 적법한가 (계획 1항) ===")
bad = 0; tot = 0
for (n, m) in [(6, 2), (7, 2), (8, 2), (9, 2), (8, 3), (9, 3), (10, 3),
               (12, 3), (11, 4), (12, 4), (13, 5)]:
    r = 2 * m
    if r >= n:
        continue
    fails = 0
    trials = 40 if n <= 10 else 12
    for _ in range(trials):
        ch = lawrence_union_chirotope(rand_layers(n, m))
        tot += 1
        if not ch.is_valid():
            fails += 1; bad += 1
    print(f"  (n={n}, r={r}): {trials}개 중 GP 위반 {fails}")
print(f"  총 {tot}개 중 위반 {bad}개 → 계획 1항 "
      f"{'반증되지 않음(증명은 아님)' if bad == 0 else '★반증됨★'}")

print("\n=== T2. layer 재배향 ↔ union 재배향 교환 (계획 2항) ===")
mis = 0
for (n, m) in [(7, 2), (8, 3), (9, 3)]:
    layers = rand_layers(n, m)
    ch = lawrence_union_chirotope(layers)
    for _ in range(30):
        flip = {e for e in range(1, n) if rng.random() < 0.5}
        a = lawrence_union_chirotope([L.reorient(flip) for L in layers]).signs
        b = ch.reorient(flip).signs
        if a != b:
            mis += 1
    print(f"  (n={n}, r={2*m}): 30회 검사, 불일치 {mis}")
print(f"  → 계획 2항 {'반증되지 않음' if mis == 0 else '★반증됨★'}")

print("\n=== T3. 'layer 가 realizable ⇒ union 이 realizable' 의 자명한 실현 검사 ===")
print("  각 layer 를 R^2 에 실현하고 세로로 쌓은 R^2m 벡터의 chirotope 가")
print("  union chirotope 와 같은가? (같다면 REALIZABLE 라벨에 즉각적 근거가 생긴다)")


def stacked_vectors(layers, scale=None):
    """layer i 의 rank-2 실현 v_j=(s_j, s_j*x_j) 를 세로로 쌓는다."""
    n = layers[0].n
    vecs = []
    for j in range(n):
        row = []
        for i, L in enumerate(layers):
            x = L.positions[j] + 1
            s = L.signs[j]
            mul = 1 if scale is None else scale[i]
            row += [s * mul, s * mul * x]
        vecs.append(row)
    return vecs


match_any = 0
for trial in range(6):
    for (n, m) in [(7, 2), (8, 3)]:
        layers = rand_layers(n, m)
        target = lawrence_union_chirotope(layers)
        got = None
        for scale in [None, [1] * m, [10 ** (3 * i) for i in range(m)],
                      [10 ** (3 * (m - 1 - i)) for i in range(m)]]:
            try:
                cand = Chirotope.from_vectors(stacked_vectors(layers, scale))
            except ValueError:
                continue
            if cand.signs == target.signs:
                got = scale; break
        if got is not None:
            match_any += 1
print(f"  12개 시도 중 자명한 쌓기 실현이 union 을 재현한 횟수: {match_any}")
print("  → 0 이면, 'union 은 realizable' 주장에 **즉각적 구성 근거가 없다**")
print("     (Laplace 전개상 det 는 한 짝짓기의 곱이 아니라 모든 짝짓기의 부호합이다)")

print("\n=== T4. 답이 알려진 d=3 (8,4) 에서 이 class 가 witness 를 담는가 ===")
print("  rank=d+1 이 짝수여야 하므로 이 class 는 **홀수 d 에서만** 정의된다 (d=4 불가).")
found = 0; seen = 0; best = None
for ch in generate_extended_lawrence_rank2(8, 4, max_candidates=400, seed=99,
                                           dedup=True):
    seen += 1
    if not ch.is_valid():
        print("  !! GP 위반 후보가 방출됨 — 생성기가 is_valid 를 걸지 않는다")
        continue
    lab = MutationLab(ch)
    _, f, _ = lab.evaluate()
    best = f if best is None else min(best, f)
    if f == 0:
        found += 1
        if found == 1:
            print(f"  witness 발견: om_core={mcmullen_evaluate(ch).get('witness')}")
print(f"  후보 {seen}개 | witness {found}개 | 최선 f = {best}")
print("  (참고: 같은 (8,4) 에서 무작위 실현가능 표집은 1.6%, 덮개-CEGIS 는 2라운드에 SAT)")
