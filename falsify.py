"""
falsify.py — 채굴된 명제를 '먼저 반증하려고' 공격하는 결정론적 검사기.

## 규율

이 저장소의 연구 규칙은 "보조정리를 제안하면, 증명을 다듬기 전에 먼저 반증을
시도한다"이다. 이 모듈이 그 규칙을 코드로 강제한다. `conjecture.mine` 이 내놓는
것은 전부 **관찰(MINED)** 이며, 여기를 통과하기 전에는 어떤 것도 정리로 인용될 수
없다.

## 두 종류의 시험 — 절대 섞지 않는다

1. **범위 내 반증 (in-scope)** — 명제가 선언한 그 (n, r) 에서 반례를 찾는다.
     REFUTED             반례 발견. 반례 chirotope 를 그대로 보관한다.
     EXHAUSTED_ON_SCOPE  그 (n, r) 의 GP-적법 uniform OM 을 **전수** 확인했고
                         반례가 없었다. → '계산으로 검증된 유한 사례'.
                         **정리가 아니다.** 다른 n 에 대해 아무 말도 하지 않는다.
     UNRESOLVED          예산 안에서 반례를 못 찾았으나 전수도 아님 → 증거 거의 없음.

2. **확장 시험 (extension)** — 다른 (n, r) 로 옮겨도 성립하는가.
     EXTENDS             그 범위에서도 반례 없음 (전수면 그 범위에서 전수 확인)
     FAILS_TO_EXTEND     그 범위에서 반례 발견 — **가장 유용한 결과 중 하나다.**
                         "n=6 에서는 참인데 n=7 에서 처음 깨진다"는 구조 정보이고,
                         그 첫 반례가 다음 연구 세션의 출발점이 된다.

확장 시험의 실패는 원래 명제의 반증이 **아니다**. 원래 명제는 자기 범위에서만
주장되었기 때문이다. 이 구분을 흐리지 않는 것이 이 모듈의 핵심 계약이다.

## 소진(exhaustion) 주장의 근거

`generator.generate_backtracking(..., dedup=False, stats=...)` 이 캡에 걸리지 않고
끝나면, 그 (n, r) 의 GP-적법 uniform chirotope 를 χ(0,…,r−1)=+1 로 고정한 대표계로
전부 방출한 것이다. 전역 부호반전은 모든 회로 부호를 동시에 뒤집으므로
acyclic/convex/witness 판정과 이 저장소의 모든 불변량을 보존한다 — 따라서 그 대표계
전수는 전체 전수와 같은 결론을 준다.

의존성: 표준 라이브러리 + om_core + generator + invariants + conjecture.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Iterable, Optional

from om_core import Chirotope
from generator import generate_backtracking, generate_random_realizable
import invariants as INV
from conjecture import (Conjecture, features_of, REFUTED, EXHAUSTED_ON_SCOPE,
                        UNRESOLVED, MINED)

EXTENDS = "EXTENDS"
FAILS_TO_EXTEND = "FAILS_TO_EXTEND"
NOT_TESTED = "NOT_TESTED"


@dataclass
class Attack:
    """한 범위에 대한 한 번의 공격 결과."""
    scope: dict
    status: str
    tested: int = 0
    exhausted: bool = False
    elapsed_s: float = 0.0
    counterexample: Optional[dict] = None      # {"chirotope","features","failed_atom"}
    note: str = ""

    def as_dict(self):
        return asdict(self)


@dataclass
class FalsifyReport:
    conjecture_id: str
    in_scope: Optional[Attack] = None
    extensions: list = field(default_factory=list)
    verdict: str = MINED

    def as_dict(self):
        return {"conjecture_id": self.conjecture_id, "verdict": self.verdict,
                "in_scope": self.in_scope.as_dict() if self.in_scope else None,
                "extensions": [a.as_dict() for a in self.extensions]}


# ═══════════════════════════ 후보 공급 ═══════════════════════════
def _candidates(n: int, r: int, *, backend: str, budget: int, seed: int,
                node_budget: int) -> tuple[Iterable[Chirotope], dict]:
    stats: dict = {}
    if backend == "backtracking":
        gen = generate_backtracking(n, r, dedup=False, max_candidates=budget,
                                    max_nodes=node_budget, stats=stats)
    elif backend == "random":
        gen = generate_random_realizable(n, r, dedup=False, max_candidates=budget,
                                         seed=seed)
        stats["exhausted"] = False
    else:
        raise ValueError(f"알 수 없는 backend '{backend}'")
    return gen, stats


def needed_features(cj: Conjecture) -> list[str]:
    """명제가 실제로 언급하는 불변량만. 반증은 이것만 계산하면 되므로,
    비싼 불변량(automorphism_order 등)이 어휘에 있어도 공격 속도가 느려지지 않는다."""
    names = {a.inv for a in cj.antecedent} | {cj.consequent.inv}
    return sorted(names)


def _failed_atom(cj: Conjecture, feats: dict) -> str:
    if cj.consequent.holds(feats) is False:
        return cj.consequent.text()
    return "(후건 판정 불가)"


def _attack(cj: Conjecture, n: int, r: int, *, backend: str, budget: int,
            node_budget: int, seed: int, feature_names: list[str],
            in_scope: bool) -> Attack:
    scope = {"n": n, "r": r, "backend": backend, "budget": budget}
    t0 = time.perf_counter()
    gen, stats = _candidates(n, r, backend=backend, budget=budget, seed=seed,
                             node_budget=node_budget)
    tested = 0
    for ch in gen:
        tested += 1
        feats = features_of(ch, feature_names,
                            with_label=INV.LABEL_NAME in feature_names)
        if cj.is_counterexample(feats):
            return Attack(scope=scope,
                          status=REFUTED if in_scope else FAILS_TO_EXTEND,
                          tested=tested, exhausted=False,
                          elapsed_s=round(time.perf_counter() - t0, 3),
                          counterexample={
                              "chirotope": ch.to_dict(),
                              "features": {k: _jsonable(v) for k, v in feats.items()},
                              "failed_atom": _failed_atom(cj, feats)},
                          note="전건은 성립하는데 후건이 깨지는 대상을 찾았다")
    exhausted = bool(stats.get("exhausted"))
    if in_scope:
        status = EXHAUSTED_ON_SCOPE if exhausted else UNRESOLVED
    else:
        status = EXTENDS
    note = ("이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 (전역 부호 고정 대표계)"
            if exhausted else
            f"예산 {budget}개 안에서 반례 없음 — 전수가 아니므로 증거로 약함")
    return Attack(scope=scope, status=status, tested=tested, exhausted=exhausted,
                  elapsed_s=round(time.perf_counter() - t0, 3), note=note)


def _attack_many(targets: list[tuple[int, Conjecture, list[str]]], n: int, r: int,
                 *, backend: str, budget: int, node_budget: int, seed: int,
                 in_scope: bool) -> dict[int, Attack]:
    """같은 범위·예산의 여러 명제를 후보 한 번의 순회로 함께 공격한다.

    후보 순서와 최초 반례는 개별 `_attack`과 동일하다. 각 반례에는 그 명제가 실제로
    요구한 feature만 기록해 기존 산출물 스키마도 보존한다.
    """
    scope = {"n": n, "r": r, "backend": backend, "budget": budget}
    union_names = sorted({name for _, _, names in targets for name in names})
    active = {idx: (cj, names) for idx, cj, names in targets}
    results: dict[int, Attack] = {}
    t0 = time.perf_counter()
    gen, stats = _candidates(n, r, backend=backend, budget=budget, seed=seed,
                             node_budget=node_budget)
    tested = 0
    for ch in gen:
        tested += 1
        feats = features_of(ch, union_names,
                            with_label=INV.LABEL_NAME in union_names)
        for idx, (cj, names) in list(active.items()):
            if not cj.is_counterexample(feats):
                continue
            own_feats = {name: feats.get(name) for name in names}
            results[idx] = Attack(
                scope=dict(scope),
                status=REFUTED if in_scope else FAILS_TO_EXTEND,
                tested=tested, exhausted=False,
                elapsed_s=round(time.perf_counter() - t0, 3),
                counterexample={
                    "chirotope": ch.to_dict(),
                    "features": {k: _jsonable(v) for k, v in own_feats.items()},
                    "failed_atom": _failed_atom(cj, own_feats),
                },
                note="전건은 성립하는데 후건이 깨지는 대상을 찾았다 (배치 공격)")
            del active[idx]
        if not active:
            break

    exhausted = bool(stats.get("exhausted"))
    elapsed = round(time.perf_counter() - t0, 3)
    for idx in active:
        status = ((EXHAUSTED_ON_SCOPE if exhausted else UNRESOLVED)
                  if in_scope else EXTENDS)
        note = ("이 (n,r) 의 GP-적법 uniform OM 을 전수 확인함 "
                "(전역 부호 고정 대표계, 배치 공격)" if exhausted else
                f"예산 {budget}개 안에서 반례 없음 — 전수가 아니므로 증거로 약함 "
                "(배치 공격)")
        results[idx] = Attack(scope=dict(scope), status=status, tested=tested,
                              exhausted=exhausted, elapsed_s=elapsed, note=note)
    return results


def _jsonable(v):
    if isinstance(v, tuple):
        return [list(x) if isinstance(x, tuple) else x for x in v]
    return v


def _budget_scale(cj: Conjecture) -> tuple[list[str], float]:
    names = needed_features(cj)
    costs = [INV.REGISTRY[nm].cost for nm in names if nm in INV.REGISTRY]
    scale = 0.05 if "expensive" in costs else (0.5 if "moderate" in costs else 1.0)
    return names, scale


# ═══════════════════════════ 공개 API ═══════════════════════════
def falsify(cj: Conjecture, *, feature_names: list[str] | None = None,
            budget: int = 400, node_budget: int = 4_000_000,
            extensions: list[tuple[int, int]] | None = None,
            backend: str = "backtracking", seed: int = 20260809,
            extension_budget: int | None = None) -> FalsifyReport:
    """명제 하나를 공격한다. extensions 는 [(n, r), ...] 형태의 추가 시험 범위.

    feature_names 는 무시해도 되는 힌트다 — 실제로는 명제가 언급하는 불변량만
    계산한다(needed_features). 반례 판정에 필요한 값은 그것뿐이기 때문이다."""
    names, scale = _budget_scale(cj)
    n = int(cj.scope.get("n"))
    r = int(cj.scope.get("r"))
    rep = FalsifyReport(conjecture_id=cj.id)

    # 비싼 불변량을 참조하는 명제는 같은 예산으로 훨씬 오래 걸린다. 예산을 조용히
    # 유지해 무한정 도는 대신 명시적으로 줄이고, 그 사실을 결과에 남긴다 —
    # 축소된 예산으로 얻은 '반례 없음'은 그만큼 약한 증거이기 때문.
    eff_budget = max(50, int(budget * scale))

    rep.in_scope = _attack(cj, n, r, backend=backend, budget=eff_budget,
                           node_budget=node_budget, seed=seed,
                           feature_names=names, in_scope=True)
    if scale < 1.0:
        rep.in_scope.note += (f" | 비싼 불변량({[nm for nm in names if nm in INV.REGISTRY and INV.REGISTRY[nm].cost != 'cheap']}) "
                              f"때문에 예산 {budget}→{eff_budget} 로 축소됨")

    if rep.in_scope.status != REFUTED:
        for (en, er) in (extensions or []):
            if (en, er) == (n, r):
                continue
            att = _attack(cj, en, er, backend=backend,
                          budget=max(20, int((extension_budget or budget) * scale)),
                          node_budget=node_budget, seed=seed + en * 31 + er,
                          feature_names=names, in_scope=False)
            rep.extensions.append(att)

    rep.verdict = rep.in_scope.status
    cj.status = rep.verdict
    cj.evidence = rep.as_dict()
    return rep


def falsify_all(conjectures: list[Conjecture], *, top: int | None = None,
                progress=None, **kw) -> list[FalsifyReport]:
    """점수 상위 명제를 범위별로 묶어 공격. 반환 순서는 입력 순서와 같다."""
    targets = conjectures if top is None else conjectures[:top]
    if not targets:
        return []

    budget = int(kw.get("budget", 400))
    node_budget = int(kw.get("node_budget", 4_000_000))
    extensions = kw.get("extensions") or []
    backend = kw.get("backend", "backtracking")
    seed = int(kw.get("seed", 20260809))
    extension_budget = kw.get("extension_budget")

    reports = [FalsifyReport(conjecture_id=cj.id) for cj in targets]
    metadata: dict[int, tuple[list[str], float]] = {}
    groups: dict[tuple, list[tuple[int, Conjecture, list[str]]]] = {}
    for idx, cj in enumerate(targets):
        names, scale = _budget_scale(cj)
        metadata[idx] = (names, scale)
        n, r = int(cj.scope["n"]), int(cj.scope["r"])
        eff_budget = max(50, int(budget * scale))
        key = (n, r, backend, eff_budget, node_budget, seed)
        groups.setdefault(key, []).append((idx, cj, names))

    # 진행 보고는 **각 그룹을 실제로 공격하기 직전**에 한다. 시작 시점에 전부
    # 몰아서 부르면(배치 도입 시 그렇게 되어 있었다) 화면에는 1/N…N/N 이 순식간에
    # 찍힌 뒤 긴 침묵이 이어져, 오래 걸리는 실행이 멈춘 것처럼 보인다.
    done = 0
    for key, group in groups.items():
        for _idx, _cj, _names in group:
            if progress:
                progress(done, len(targets), _cj)
            done += 1
        n, r, group_backend, eff_budget, group_nodes, group_seed = key
        attacked = _attack_many(group, n, r, backend=group_backend,
                                budget=eff_budget, node_budget=group_nodes,
                                seed=group_seed, in_scope=True)
        for idx, attack in attacked.items():
            reports[idx].in_scope = attack
            names, scale = metadata[idx]
            if scale < 1.0:
                costly = [nm for nm in names if nm in INV.REGISTRY
                          and INV.REGISTRY[nm].cost != "cheap"]
                attack.note += f" | 비싼 불변량({costly}) 때문에 예산 {budget}→{eff_budget} 로 축소됨"

    # 범위 내에서 살아남은 명제의 확장 공격도 같은 확장 범위끼리 한 번만 열거한다.
    for en, er in extensions:
        ext_groups: dict[tuple, list[tuple[int, Conjecture, list[str]]]] = {}
        for idx, cj in enumerate(targets):
            if reports[idx].in_scope.status == REFUTED:
                continue
            n, r = int(cj.scope["n"]), int(cj.scope["r"])
            if (en, er) == (n, r):
                continue
            names, scale = metadata[idx]
            eff_budget = max(20, int((extension_budget or budget) * scale))
            ext_seed = seed + en * 31 + er
            key = (en, er, backend, eff_budget, node_budget, ext_seed)
            ext_groups.setdefault(key, []).append((idx, cj, names))
        for key, group in ext_groups.items():
            gn, gr, group_backend, eff_budget, group_nodes, group_seed = key
            attacked = _attack_many(group, gn, gr, backend=group_backend,
                                    budget=eff_budget, node_budget=group_nodes,
                                    seed=group_seed, in_scope=False)
            for idx, attack in attacked.items():
                reports[idx].extensions.append(attack)

    for idx, cj in enumerate(targets):
        reports[idx].verdict = reports[idx].in_scope.status
        cj.status = reports[idx].verdict
        cj.evidence = reports[idx].as_dict()
    return reports


def surviving(conjectures: list[Conjecture]) -> list[Conjecture]:
    """반증되지 않은 것만. 등급은 여전히 각자 status 로 구분해야 한다."""
    return [c for c in conjectures if c.status != REFUTED]


def report_markdown(conjectures: list[Conjecture],
                    reports: list[FalsifyReport]) -> str:
    by_id = {r.conjecture_id: r for r in reports}
    n_ref = sum(1 for c in conjectures if c.status == REFUTED)
    n_exh = sum(1 for c in conjectures if c.status == EXHAUSTED_ON_SCOPE)
    n_unr = sum(1 for c in conjectures if c.status == UNRESOLVED)
    lines = [
        "# 반증 시도 결과",
        "",
        f"- 공격한 명제 {len(reports)}건 → 반증 {n_ref} / 범위내 전수확인 {n_exh} / 미해결 {n_unr}",
        "",
        "> `EXHAUSTED_ON_SCOPE` 는 **그 유한 범위에서만** 확인된 것이다. 정리가 아니다.",
        "> 확장 시험의 `FAILS_TO_EXTEND` 는 원 명제의 반증이 아니라 '더 큰 범위로는",
        "> 넘어가지 않는다'는 별개의 사실이다.",
        "",
    ]
    order = {EXHAUSTED_ON_SCOPE: 0, UNRESOLVED: 1, REFUTED: 2, MINED: 3}
    for cj in sorted(conjectures, key=lambda c: (order.get(c.status, 9), -c.score)):
        rep = by_id.get(cj.id)
        if rep is None:
            continue
        lines.append(f"## {cj.id} — `{cj.status}` `[{cj.invariance}]` (score {cj.score})")
        lines.append("")
        lines.append(f"- 명제: {cj.text()}")
        lines.append(f"- 형식: `{cj.dsl()}`")
        a = rep.in_scope
        lines.append(f"- 범위내: {a.status} — {a.tested}개 검사, "
                     f"전수={a.exhausted}, {a.elapsed_s}s ({a.note})")
        if a.counterexample:
            ce = a.counterexample
            lines.append(f"  - **반례**: n={ce['chirotope']['n']} r={ce['chirotope']['r']}, "
                         f"깨진 부분 = {ce['failed_atom']}")
            lines.append(f"  - 반례 chirotope: `{json.dumps(ce['chirotope']['signs'], ensure_ascii=False)}`")
        for ext in rep.extensions:
            lines.append(f"- 확장 (n={ext.scope['n']}, r={ext.scope['r']}): "
                         f"{ext.status} — {ext.tested}개 검사, 전수={ext.exhausted}")
            if ext.counterexample:
                ce = ext.counterexample
                lines.append(f"  - **확장 반례**: 깨진 부분 = {ce['failed_atom']}")
                lines.append(f"  - chirotope: `{json.dumps(ce['chirotope']['signs'], ensure_ascii=False)}`")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from console import enable_utf8_stdout
    from conjecture import (build_corpus, mine, Atom, Conjecture, LABEL_ATOM,
                            ORBIT_INVARIANT)

    enable_utf8_stdout()

    # (1) 소진 판정이 실제로 작동하는가 — (5,3) 은 전수가 빠르다.
    stats: dict = {}
    got = list(generate_backtracking(5, 3, dedup=False, max_candidates=10**9,
                                     max_nodes=10**9, stats=stats))
    assert stats["exhausted"] is True and stats["hit_candidate_cap"] is False
    print(f"(5,3) 전수 소진 OK — {len(got)}개, nodes={stats['nodes']}")
    # 캡에 걸리면 소진 주장이 자동으로 철회되는가
    stats2: dict = {}
    list(generate_backtracking(6, 3, dedup=False, max_candidates=5,
                               max_nodes=10**9, stats=stats2))
    assert stats2["exhausted"] is False and stats2["hit_candidate_cap"] is True
    print("캡 도달 시 소진 주장 철회 OK")

    # (2) 참인 명제: (5,3) 에는 witness 가 없다는 것이 알려져 있다
    #     (docs/RESEARCH_STATUS.md — CEGIS EXHAUSTED). 이를 명제로 만들어 전수 확인.
    names = INV.active_names()
    true_cj = Conjecture(id="cj-true", form="necessary", antecedent=[LABEL_ATOM],
                         consequent=Atom("n", ">=", 6),
                         scope={"n": 5, "r": 3}, support={},
                         invariance=ORBIT_INVARIANT)
    rep = falsify(true_cj, feature_names=names, budget=10**9,
                  node_budget=10**9, extensions=[])
    assert rep.verdict == EXHAUSTED_ON_SCOPE, rep.as_dict()
    print(f"참인 명제 → {rep.verdict} ({rep.in_scope.tested}개 전수)")

    # (3) 거짓 명제는 반드시 반례와 함께 REFUTED 여야 한다
    false_cj = Conjecture(id="cj-false", form="necessary", antecedent=[LABEL_ATOM],
                          consequent=Atom("acyclic", "==", True),
                          scope={"n": 6, "r": 3}, support={},
                          invariance=ORBIT_INVARIANT)
    rep2 = falsify(false_cj, feature_names=names, budget=3000,
                   node_budget=10**8, extensions=[])
    assert rep2.verdict == REFUTED, rep2.as_dict()
    ce = rep2.in_scope.counterexample
    assert ce is not None
    ch_ce = Chirotope.from_dict(ce["chirotope"])
    # 반례를 om_core 로 독립 재확인 — 반증기가 스스로를 믿지 않는다
    assert INV.label(ch_ce) is True and ch_ce.is_acyclic() is False
    from om_core import mcmullen_evaluate
    assert mcmullen_evaluate(ch_ce)["witness"] is True
    print(f"거짓 명제 → REFUTED, 반례를 om_core 로 독립 재확인 OK "
          f"({rep2.in_scope.tested}개 만에 발견)")

    # (4) 확장 시험: 범위 밖 반례가 REFUTED 로 잘못 승격되지 않는가
    ext_cj = Conjecture(id="cj-ext", form="necessary", antecedent=[LABEL_ATOM],
                        consequent=Atom("n", "<=", 6),
                        scope={"n": 6, "r": 3}, support={},
                        invariance=ORBIT_INVARIANT)
    rep3 = falsify(ext_cj, feature_names=names, budget=800, node_budget=10**8,
                   extensions=[(7, 3)], extension_budget=200)
    assert rep3.verdict != REFUTED
    assert rep3.extensions and rep3.extensions[0].status == FAILS_TO_EXTEND
    print("확장 실패가 범위내 반증으로 오염되지 않음 OK "
          f"(in_scope={rep3.verdict}, ext={rep3.extensions[0].status})")

    # (5) 실제 채굴 → 반증 파이프라인 end-to-end
    chs = list(generate_backtracking(6, 3, dedup=False, max_candidates=150,
                                     max_nodes=600_000))
    corpus = build_corpus(chs, {"n": 6, "r": 3, "om_class": "uniform",
                                "backend": "backtracking", "exhaustive": False})
    cjs = mine(corpus, min_support=3, max_conjectures=8)
    reps = falsify_all(cjs, feature_names=corpus.feature_names, budget=1200,
                       node_budget=10**8, extensions=[(7, 3)],
                       extension_budget=150)
    n_ref = sum(1 for c in cjs if c.status == REFUTED)
    print(f"end-to-end: 채굴 {len(cjs)}건 → 반증 {n_ref}건, "
          f"생존 {len(surviving(cjs))}건")
    # 반증된 명제는 반드시 반례 객체를 갖고 있어야 한다 (주장만 하는 반증 금지)
    for c in cjs:
        if c.status == REFUTED:
            assert c.evidence["in_scope"]["counterexample"] is not None
    md = report_markdown(cjs, reps)
    assert "정리가 아니다" in md
    print("반증 보고서 생성 OK")
    print("falsify core-contract assertions OK")
