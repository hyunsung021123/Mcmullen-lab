"""
benchmark_coverage.py — WP0: baseline oracle · corpus · benchmark (Epic #37 / Task #38).

목적: 새 coverage 검증기(B1, reorientation_cover)를 legacy 검증기
(B0, om_core.is_reorientable_to_convex)와 **같은 corpus** 위에서 비교한다.

정확성(절대 조건, 하나라도 어긋나면 B1 을 기본 경로에 통합하지 않는다):
  - legacy/new witness 판정 일치 100%
  - non-witness 의 first_uncovered_index flip replay(convex 확인) 100%
  - witness certificate 독립 replay 100%

corpus 정직성 규칙:
  - "exhaustive" 라벨은 완전성이 **투명하게** 보이는 방식(product 전수 열거)으로 만든
    corpus 에만 붙인다. generator 가 max_nodes/max_candidates 캡에 조용히 걸렸을 수
    있는 corpus 를 전수라고 부르지 않는다.
  - sampled corpus 는 fixed seed 로 생성하고 exhaustive 라고 표현하지 않는다.

성능 측정: warmup 1회 + repeats 회 반복, per-candidate median 을 모아 corpus 단위
median/p95 보고. 단일 실행 시간만으로 과장하지 않는다.

출력: local_runs/benchmarks/ 아래 JSON + Markdown (git 에서 무시됨). 이 스크립트
자체는 재현을 위해 커밋된다. CI 에는 빠른 자체 테스트(기본 실행)만 들어가고,
전체 벤치마크는 `--full` 로 수동 실행한다.

사용법:
    python benchmark_coverage.py            # 빠른 자체 테스트 (CI용, ~수초)
    python benchmark_coverage.py --full     # 전체 corpus 벤치마크 (수 분)
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import statistics
import sys
import time
from itertools import combinations, product

from om_core import Chirotope
from generator import generate_backtracking, generate_random_realizable
from reorientation_cover import evaluate_coverage, flip_set_from_index
from certificate import build_certificate
from certificate_verify import verify_certificate, CertificateError


# ─────────────────────────── corpus 구성 ───────────────────────────
def enumerate_uniform_chirotopes(n: int, r: int):
    """완전성이 투명한 전수 열거: 첫 부호를 +1 로 고정(전역 부호 대칭 제거)하고
    나머지 모든 부호 조합을 시도해 GP-valid 만 방출. 2^(C(n,r)-1) 회 is_valid 검사."""
    subs = sorted(combinations(range(n), r))
    for bits in product((1, -1), repeat=len(subs) - 1):
        signs = {subs[0]: 1}
        signs.update(zip(subs[1:], bits))
        ch = Chirotope(n, r, signs)
        if ch.is_valid():
            yield ch


def backtracking_exhaustive(n: int, r: int):
    """캡 없이(사실상 무한 한도) 백트래킹 전수 열거. 완전성은 product 전수 열거와의
    교차 검증(check_backtracking_completeness)으로 뒷받침한다."""
    return generate_backtracking(n, r, dedup=False,
                                 max_candidates=10**12, max_nodes=10**12)


def check_backtracking_completeness(n: int, r: int) -> int:
    """product 전수 열거와 백트래킹 열거가 같은 집합을 내는지 확인 (작은 (n,r)용).
    통과하면 개수를 반환 — 더 큰 (n,r)에서 백트래킹 전수를 신뢰하는 근거가 된다."""
    subs = sorted(combinations(range(n), r))
    a = {tuple(ch.signs[s] for s in subs) for ch in enumerate_uniform_chirotopes(n, r)}
    b = {tuple(ch.signs[s] for s in subs) for ch in backtracking_exhaustive(n, r)}
    assert a == b, f"({n},{r}) 백트래킹 열거가 product 전수와 불일치"
    return len(a)


def build_corpora(full: bool) -> list[dict]:
    """corpus 목록. 각 항목: name / kind(exhaustive|sampled) / how / chirotopes."""
    corpora = []

    # tiny exhaustive — rank-2 특이 사례 포함 (README §5: rank-2 는 정의상 전부 witness)
    tiny = [(4, 2), (4, 3), (5, 3), (5, 4)]
    if full:
        tiny += [(5, 2), (6, 4)]
    for (n, r) in tiny:
        chs = list(enumerate_uniform_chirotopes(n, r))
        corpora.append({"name": f"exhaustive({n},{r})", "kind": "exhaustive",
                        "how": "product 전수 열거 (첫 부호 +1 고정)",
                        "chirotopes": chs})

    # (6,3): d=2 witness 가 실제로 존재하는 전수 구간.
    # full 이면 product 전수(투명), quick 이면 백트래킹 전수(교차 검증으로 뒷받침).
    if full:
        chs63 = list(enumerate_uniform_chirotopes(6, 3))
        how63 = "product 전수 열거 (첫 부호 +1 고정)"
    else:
        chs63 = list(backtracking_exhaustive(6, 3))
        how63 = "백트래킹 전수 (product 교차 검증으로 완전성 뒷받침)"
    corpora.append({"name": "exhaustive(6,3)", "kind": "exhaustive",
                    "how": how63, "chirotopes": chs63})

    # sampled — fixed seed. realizable(무작위 점배치) + 교대(순환다면체).
    def sampled(n, r, cnt, seed):
        return list(generate_random_realizable(
            n, r, dedup=True, max_candidates=cnt, seed=seed))

    corpora.append({"name": "sampled realizable(6,3)", "kind": "sampled",
                    "how": "generate_random_realizable(seed=63)",
                    "chirotopes": sampled(6, 3, 30 if not full else 60, 63)})
    corpora.append({"name": "sampled realizable(8,4)", "kind": "sampled",
                    "how": "generate_random_realizable(seed=84)",
                    "chirotopes": sampled(8, 4, 10 if not full else 40, 84)})
    if full:
        corpora.append({"name": "sampled realizable(7,4)", "kind": "sampled",
                        "how": "generate_random_realizable(seed=74)",
                        "chirotopes": sampled(7, 4, 40, 74)})
        corpora.append({"name": "sampled backtracking(7,3)", "kind": "sampled",
                        "how": "generate_backtracking(dedup=True, max 40) — 비실현 포함 가능"
                               " (실현가능성은 어느 쪽으로도 인증하지 않음)",
                        "chirotopes": list(generate_backtracking(
                            7, 3, dedup=True, max_candidates=40))})
        corpora.append({"name": "alternating (cyclic polytope)", "kind": "sampled",
                        "how": "Chirotope.alternating — convex 라 non-witness 기준선"
                               " + d=5 스케일(12,6) 타이밍 포함",
                        "chirotopes": [Chirotope.alternating(8, 4),
                                       Chirotope.alternating(10, 5),
                                       Chirotope.alternating(12, 6)]})
    else:
        corpora.append({"name": "alternating (cyclic polytope)", "kind": "sampled",
                        "how": "Chirotope.alternating — convex 라 non-witness 기준선",
                        "chirotopes": [Chirotope.alternating(8, 4)]})
    return corpora


# ─────────────────────────── 측정 ───────────────────────────
def _time_median(fn, repeats: int) -> float:
    fn()                                    # warmup
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def run_benchmark(full: bool, repeats: int, max_cert_replays: int = 3,
                  max_timed_per_corpus: int | None = None) -> dict:
    """정확성 검사는 corpus **전량**에 대해 수행하고, 시간 측정(warmup+repeats)은
    corpus 당 최대 max_timed_per_corpus 개에만 수행한다 (None 이면 전량).
    quick 모드 기본값은 CI 시간을 위해 200 — 정확성 커버리지는 줄지 않는다."""
    if max_timed_per_corpus is None and not full:
        max_timed_per_corpus = 200
    corpora = build_corpora(full)

    # 백트래킹 전수 신뢰 근거: 작은 (n,r)에서 product 전수와 교차 검증
    completeness = {}
    for (n, r) in ([(4, 3), (5, 3)] if not full else [(4, 3), (5, 3), (5, 4), (6, 4)]):
        completeness[f"({n},{r})"] = check_backtracking_completeness(n, r)

    report = {
        "meta": {
            "mode": "full" if full else "quick",
            "repeats": repeats,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "backtracking_completeness_crosscheck": completeness,
        },
        "corpora": [],
        "totals": {"candidates": 0, "witnesses": 0, "mismatches": 0,
                   "nonwitness_replays": 0, "certificate_replays": 0},
    }

    for corpus in corpora:
        chs = corpus["chirotopes"]
        rows = []
        mismatches = 0
        witnesses = 0
        cert_replays = 0
        nonwit_replays = 0
        for i, ch in enumerate(chs):
            timed = max_timed_per_corpus is None or i < max_timed_per_corpus
            if timed:
                legacy_t = _time_median(lambda: ch.is_reorientable_to_convex(), repeats)
                cov_t = _time_median(lambda: evaluate_coverage(ch), repeats)
            else:
                legacy_t = cov_t = None

            legacy_witness = not ch.is_reorientable_to_convex()[0]
            cov = evaluate_coverage(ch)
            if cov.is_witness != legacy_witness:
                mismatches += 1
            elif cov.is_witness:
                witnesses += 1
                if cert_replays < max_cert_replays:
                    cert = build_certificate(ch, generator="benchmark",
                                             config={"corpus": corpus["name"]})
                    try:
                        verify_certificate(cert)
                        cert_replays += 1
                    except CertificateError:
                        mismatches += 1
            else:
                flip = flip_set_from_index(cov.first_uncovered_index, ch.n)
                if not ch.reorient(flip).is_convex_position():
                    mismatches += 1
                else:
                    nonwit_replays += 1
            rows.append({"n": ch.n, "r": ch.r, "witness": bool(legacy_witness),
                         "legacy_s": legacy_t, "coverage_s": cov_t})

        timed_rows = [x for x in rows if x["legacy_s"] is not None]
        med_l = statistics.median(x["legacy_s"] for x in timed_rows) if timed_rows else 0.0
        med_c = statistics.median(x["coverage_s"] for x in timed_rows) if timed_rows else 0.0
        p95_l = _p95([x["legacy_s"] for x in timed_rows])
        p95_c = _p95([x["coverage_s"] for x in timed_rows])
        report["corpora"].append({
            "name": corpus["name"], "kind": corpus["kind"], "how": corpus["how"],
            "candidates": len(rows), "timed": len(timed_rows), "witnesses": witnesses,
            "mismatches": mismatches,
            "legacy_median_s": med_l, "coverage_median_s": med_c,
            "legacy_p95_s": p95_l, "coverage_p95_s": p95_c,
            "speedup_median": (med_l / med_c) if med_c > 0 else None,
            "nonwitness_replays": nonwit_replays,
            "certificate_replays": cert_replays,
        })
        report["totals"]["candidates"] += len(rows)
        report["totals"]["witnesses"] += witnesses
        report["totals"]["mismatches"] += mismatches
        report["totals"]["nonwitness_replays"] += nonwit_replays
        report["totals"]["certificate_replays"] += cert_replays
    return report


def _p95(xs: list) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    return ys[min(len(ys) - 1, int(round(0.95 * (len(ys) - 1))))]


def render_markdown(report: dict) -> str:
    lines = ["# Coverage verifier 벤치마크 (B0=legacy vs B1=coverage)", "",
             f"- mode: {report['meta']['mode']}, repeats: {report['meta']['repeats']}"
             f", python {report['meta']['python']}",
             f"- platform: {report['meta']['platform']}",
             f"- 백트래킹 전수 교차검증: "
             f"{report['meta']['backtracking_completeness_crosscheck']}", "",
             "| corpus | kind | 후보 | 시간측정 | witness | mismatch | legacy median(s) "
             "| coverage median(s) | speedup | legacy p95 | coverage p95 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in report["corpora"]:
        sp = f"{c['speedup_median']:.2f}x" if c["speedup_median"] else "-"
        lines.append(
            f"| {c['name']} | {c['kind']} | {c['candidates']} | {c['timed']} "
            f"| {c['witnesses']} "
            f"| {c['mismatches']} | {c['legacy_median_s']:.6f} "
            f"| {c['coverage_median_s']:.6f} | {sp} "
            f"| {c['legacy_p95_s']:.6f} | {c['coverage_p95_s']:.6f} |")
    t = report["totals"]
    lines += ["", f"**총합**: 후보 {t['candidates']}, witness {t['witnesses']}, "
                  f"mismatch {t['mismatches']}, non-witness replay {t['nonwitness_replays']}, "
                  f"certificate replay {t['certificate_replays']}", "",
              "> speedup 은 fixed corpus 의 per-candidate median 비율이다. "
              "단일 실행 결과로 과장하지 않는다."]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="B0(legacy) vs B1(coverage) 벤치마크")
    ap.add_argument("--full", action="store_true", help="전체 corpus (수 분 소요)")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out-dir", default=None,
                    help="결과 저장 폴더 (기본: <repo>/local_runs/benchmarks)")
    args = ap.parse_args(argv)

    report = run_benchmark(args.full, args.repeats)

    # 절대 조건: mismatch 0 (quick/full 공통 — 자체 테스트의 핵심 assertion)
    assert report["totals"]["mismatches"] == 0, \
        f"정확성 mismatch {report['totals']['mismatches']}건 — B1 통합 불가"
    assert report["totals"]["candidates"] > 0
    assert report["totals"]["witnesses"] > 0, "corpus 에 witness 가 없음 — corpus 구성 오류"

    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = args.out_dir or os.path.join(here, "local_runs", "benchmarks")
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    jpath = os.path.join(out_dir, f"benchmark_{report['meta']['mode']}_{stamp}.json")
    mpath = os.path.join(out_dir, f"benchmark_{report['meta']['mode']}_{stamp}.md")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    md = render_markdown(report)
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(md)

    print(md)
    print(f"\n저장: {jpath}\n저장: {mpath}")
    print("benchmark self-test OK (mismatch 0, witness corpus 포함)")
    return 0


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    sys.exit(main())
