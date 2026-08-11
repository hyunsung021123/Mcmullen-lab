"""
generator.py — Generator Agent: Chirotope 공리를 만족하는 uniform OM 후보 생성.

두 가지 백엔드:
  1) backtracking (기본, 의존성 없음): 3-term GP 위반을 '증분 가지치기'하며 DFS.
     작은 n 에 적합. 전역 부호반전 대칭을 1회 제거.
  2) z3 (선택, 대규모용): GP 제약을 SMT 로 인코딩하고 모델을 열거. (z3-solver 설치 시)

생성기는 '적법성(GP)'만 보장한다. 어떤 성질을 채택/목표로 볼지는 criteria 가 결정하며,
accept 콜백으로 조기 필터링할 수 있다(require/forbid 통과분만 방출).
"""
from __future__ import annotations
from functools import lru_cache
from itertools import combinations, product
from typing import Callable, Iterator, Optional

from om_core import Chirotope


# ───────────────────── GP 관계 사전 컴파일(증분 가지치기용) ─────────────────────
def _parity_and_key(t):
    """튜플 t 를 정렬했을 때의 (정렬키, 치환부호 ±1)."""
    arr = list(t); swaps = 0; m = len(arr)
    for i in range(m):
        for j in range(m - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]; swaps += 1
    return tuple(arr), (1 if swaps % 2 == 0 else -1)


@lru_cache(maxsize=None)
def _compile_relations(n: int, r: int):
    subs = sorted(combinations(range(n), r))
    idx = {s: i for i, s in enumerate(subs)}
    by_max: dict[tuple, list] = {s: [] for s in subs}
    E = range(n)
    for Y in combinations(E, r - 2):
        rest = [e for e in E if e not in Y]
        for a, b, c, d in combinations(rest, 4):
            terms = [(Y + (a, b)), (Y + (c, d)),
                     (Y + (a, c)), (Y + (b, d)),
                     (Y + (a, d)), (Y + (b, c))]
            compiled = [_parity_and_key(t) for t in terms]   # [(key,parity)*6]
            keys = [k for k, _ in compiled]
            mx = max(keys, key=lambda k: idx[k])
            by_max[mx].append(compiled)
    return subs, by_max


def _violates(compiled_rel, signs):
    (k1, p1), (k2, p2), (k3, p3), (k4, p4), (k5, p5), (k6, p6) = compiled_rel
    c1 = p1 * signs[k1]; c2 = p2 * signs[k2]
    c3 = p3 * signs[k3]; c4 = p4 * signs[k4]
    c5 = p5 * signs[k5]; c6 = p6 * signs[k6]
    s1 = c1 * c2; s2 = c3 * c4; s3 = c5 * c6
    return s1 == s3 and s2 == -s1     # 금지 패턴 (+,-,+)/(-,+,-)


# ───────────────────────────── 백트래킹 백엔드 ─────────────────────────────
def generate_backtracking(
    n: int, r: int, *,
    accept: Optional[Callable[[Chirotope], bool]] = None,
    dedup: bool = True,
    max_candidates: int = 200,
    max_nodes: int = 2_000_000,
    stats: Optional[dict] = None,
) -> Iterator[Chirotope]:
    """GP-적법한 uniform chirotope 들을 차례로 방출.
    accept(ch): True 인 것만 방출(require/forbid 조기 필터). None 이면 전부.
    dedup: 재배향-서명으로 중복 제거. max_* 는 안전장치.

    stats: dict 를 주면 소진 여부를 기록한다 —
      {"nodes","emitted","hit_candidate_cap","hit_node_cap","exhausted"}.
    `exhausted=True` 는 "이 (n,r) 의 GP-적법 uniform chirotope 를 (전역 부호 고정
    하에) 하나도 빠짐없이 방출했다"는 뜻이며, `falsify.py` 가 '전수 확인' 등급을
    주장할 수 있는 유일한 근거다. 캡에 걸리면 False 가 되어 주장이 자동으로 약해진다.
    (dedup=True 면 중복 제거로 일부가 생략되므로 exhausted 는 항상 False.)"""
    subs, by_max = _compile_relations(n, r)
    signs: dict[tuple, int] = {}
    seen: set = set()
    emitted = [0]; nodes = [0]
    first = subs[0]                    # (0,1,...,r-1): 전역 부호 고정

    def dfs(i: int):
        if emitted[0] >= max_candidates or nodes[0] >= max_nodes:
            return
        if i == len(subs):
            ch = Chirotope(n, r, dict(signs))
            if dedup:
                key = ch.canonical_key()
                if key in seen:
                    return
                seen.add(key)
            if accept is None or accept(ch):
                emitted[0] += 1
                yield ch
            return
        s = subs[i]
        choices = (1,) if s == first else (1, -1)
        for v in choices:
            nodes[0] += 1
            signs[s] = v
            if not any(_violates(rel, signs) for rel in by_max[s]):
                yield from dfs(i + 1)
            del signs[s]
            if emitted[0] >= max_candidates or nodes[0] >= max_nodes:
                return

    yield from dfs(0)
    if stats is not None:
        hit_cand = emitted[0] >= max_candidates
        hit_node = nodes[0] >= max_nodes
        stats.update({"nodes": nodes[0], "emitted": emitted[0],
                      "hit_candidate_cap": hit_cand, "hit_node_cap": hit_node,
                      "exhausted": (not hit_cand) and (not hit_node) and (not dedup)})


# ───────────────────────────── Z3 백엔드 (선택) ─────────────────────────────
def generate_z3(
    n: int, r: int, *,
    accept: Optional[Callable[[Chirotope], bool]] = None,
    max_candidates: int = 200,
) -> Iterator[Chirotope]:
    """SMT 인코딩으로 GP-적법 chirotope 열거 (z3-solver 필요).
    대규모 n / 구조적 제약(편향) 결합 시 권장. 미설치면 안내 후 종료."""
    try:
        import z3
    except ImportError:
        print("[generate_z3] z3-solver 가 없습니다.  pip install z3-solver  후 사용하세요.")
        return

    subs = sorted(combinations(range(n), r))
    x = {s: z3.Int(f"x_{'_'.join(map(str,s))}") for s in subs}
    solver = z3.Solver()
    for s in subs:
        solver.add(z3.Or(x[s] == 1, x[s] == -1))
    solver.add(x[subs[0]] == 1)        # 전역 부호 고정

    # GP 제약: 금지 패턴 차단
    E = range(n)
    def chi_expr(t):
        key, par = _parity_and_key(t)
        return par * x[key]
    for Y in combinations(E, r - 2):
        rest = [e for e in E if e not in Y]
        for a, b, c, d in combinations(rest, 4):
            s1 = chi_expr(Y + (a, b)) * chi_expr(Y + (c, d))
            s2 = chi_expr(Y + (a, c)) * chi_expr(Y + (b, d))
            s3 = chi_expr(Y + (a, d)) * chi_expr(Y + (b, c))
            solver.add(z3.Not(z3.And(s1 == s3, s2 == -s1)))

    count = 0
    while count < max_candidates and solver.check() == z3.sat:
        m = solver.model()
        signs = {s: (1 if m.evaluate(x[s]).as_long() == 1 else -1) for s in subs}
        ch = Chirotope(n, r, signs)
        if accept is None or accept(ch):
            count += 1
            yield ch
        # 블로킹 절: 이 모델 배제
        solver.add(z3.Or([x[s] != m.evaluate(x[s]) for s in subs]))


# ─────────────────────── 무작위 실현가능 백엔드 (선택) ───────────────────────
def generate_random_realizable(
    n: int, r: int, *,
    accept: Optional[Callable[[Chirotope], bool]] = None,
    dedup: bool = True,
    max_candidates: int = 200,
    coord: int = 9,
    seed: Optional[int] = None,
    max_tries: int = 50_000,
) -> Iterator[Chirotope]:
    """R^(r-1) 무작위 정수 점배치 → 동차화한 chirotope 를 방출.
    '실현 가능한' uniform OM 만 생성하므로 (비실현 witness 는 못 찾지만) 작은~중간 n 에서
    실현가능 witness 를 매우 빠르게 찾는다. 백트래킹이 convex 영역을 먼저 훑는 d>=3 에 특히 유용."""
    import random
    rng = random.Random(seed)
    seen: set = set(); emitted = 0; tries = 0
    while emitted < max_candidates and tries < max_tries:
        tries += 1
        pts = [tuple(rng.randint(-coord, coord) for _ in range(r - 1)) for _ in range(n)]
        try:
            ch = Chirotope.from_points(pts)         # 비균일(공면)이면 ValueError
        except ValueError:
            continue
        if dedup:
            k = ch.canonical_key()
            if k in seen:
                continue
            seen.add(k)
        if accept is None or accept(ch):
            emitted += 1
            yield ch


def generate_cyclic(n: int, r: int, *,
                    accept: Optional[Callable[[Chirotope], bool]] = None,
                    **_) -> Iterator[Chirotope]:
    """순환다면체(교대) OM 한 개를 방출. 기준선/시드용(convex 라 witness 아님)."""
    ch = Chirotope.alternating(n, r)
    if accept is None or accept(ch):
        yield ch


def generate_cegis(n: int, r: int, *,
                   accept: Optional[Callable[[Chirotope], bool]] = None,
                   max_candidates: int = 200, **_) -> Iterator[Chirotope]:
    """실험적 백엔드 (0026): CEGIS 로 CERTIFIED witness 만 직접 방출.
    다른 백엔드와 달리 '후보'가 아니라 이미 legacy+certificate 이중 replay 를
    통과한 witness 를 내놓는다 (파이프라인의 mcmullen_evaluate 가 다시 한 번
    검증하므로 이중 안전). z3 미설치면 안내 후 종료. solver unknown 이 발생해
    완전성이 깨지면 RuntimeError (조용한 누락 금지)."""
    try:
        from cegis_search import cegis_enumerate_witnesses
    except (ImportError, RuntimeError):
        print("[generate_cegis] z3-solver 가 없습니다. pip install z3-solver 후 사용하세요.")
        return
    emitted = 0
    for out in cegis_enumerate_witnesses(n, r, max_witnesses=max_candidates):
        if out.status == "INCONCLUSIVE_WITH_UNKNOWN":
            raise RuntimeError("CEGIS inner solver unknown 발생 — 열거 완전성 주장 불가")
        ch = out.chirotope
        if accept is None or accept(ch):
            emitted += 1
            yield ch
        if emitted >= max_candidates:
            return


def generate(n: int, r: int, *, backend: str = "backtracking", **kw) -> Iterator[Chirotope]:
    if backend == "z3":
        return generate_z3(n, r, **kw)
    if backend == "random":
        return generate_random_realizable(n, r, **kw)
    if backend == "cyclic":
        return generate_cyclic(n, r, **kw)
    if backend == "cegis":
        return generate_cegis(n, r, **kw)
    return generate_backtracking(n, r, **kw)


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    # 데모: d=2 (r=3), n=5 에서 GP-적법 uniform OM 을 몇 개 만들어 본다.
    _compile_relations.cache_clear()
    first_run = list(generate_backtracking(5, 3, dedup=True, max_candidates=8))
    second_run = list(generate_backtracking(5, 3, dedup=True, max_candidates=8))
    assert [ch.canonical_key() for ch in first_run] == [ch.canonical_key() for ch in second_run]
    assert _compile_relations.cache_info().hits > 0

    got = second_run
    print(f"n=5,r=3 GP-적법 후보 {len(got)}개 생성 (중복 제거, 최대 8개)")
    for ch in got[:3]:
        print("  acyclic=%-5s convex=%-5s tot_cyclic=%-5s" %
              (ch.is_acyclic(), ch.is_convex_position(), ch.is_totally_cyclic()))
