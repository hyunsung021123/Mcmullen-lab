"""
certificate.py — McMullen-OM witness 의 계산 증명서(certificate v1) 생성기.

Epic #37 / Task #38 (source: chatgpt, relayed by user).

certificate 는 "solver says UNSAT" 한 문장이 아니라, 사람이 다른 머신에서 search
loop·최적화된 bitset 구현을 신뢰하지 않고도 결과를 재검증할 수 있는 명시적 증거다:
모든 재배향 index(2^(n-1)개)마다 그 재배향을 차단하는 circuit support 하나를 담는다.

검증은 certificate_verify.py 가 독립적으로 수행한다 (이 모듈의 coverage 로직을
재사용하지 않음). trust label:

    CONJECTURAL < EMPIRICAL < VERIFIED < CERTIFIED < FORMALIZED

이 모듈이 만드는 것은 VERIFIED(코어 검증 통과) 결과를 CERTIFIED 후보로 포장하는
것까지이고, CERTIFIED 상태는 certificate_verify.py 의 독립 replay 통과 후에만 부여된다.

CLI:
    python certificate.py --results <results.json> --witness-id <id> --out <cert.json>
    python certificate.py --certificate <cert.json> --report <report.md>
    python certificate.py --self-test
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import sys
import time

from om_core import Chirotope
from reorientation_cover import evaluate_coverage

SCHEMA_ID = "mcmullen-om-certificate/v1"


# ─────────────────────────── canonical JSON / hash ───────────────────────────
def canonical_json_bytes(obj) -> bytes:
    """hash 계산용 canonical 직렬화 (sort_keys, 공백 없음, ensure_ascii=False)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def certificate_hash(cert: dict) -> str:
    """hashes 필드를 제외한 canonical JSON 의 SHA-256."""
    body = {k: v for k, v in cert.items() if k != "hashes"}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _repository_commit() -> str:
    try:
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)), timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


# ─────────────────────────── certificate 생성 ───────────────────────────
def build_certificate(ch: Chirotope, *, generator: str = "unknown",
                      config: dict | None = None, seed=None,
                      created_at: str | None = None,
                      repository_commit: str | None = None) -> dict:
    """witness chirotope 로부터 certificate v1 을 생성.

    witness 가 아니면(coverage 에 uncovered 재배향이 있으면) ValueError — 그 재배향이
    곧 convex 반례다. GP-invalid 여도 ValueError."""
    if not ch.is_valid():
        raise ValueError("GP-invalid chirotope 는 certificate 대상이 아님")
    cov = evaluate_coverage(ch, build_obstruction_map=True)
    if not cov.is_witness:
        raise ValueError(
            f"witness 가 아님: 재배향 index {cov.first_uncovered_index} 가 "
            f"convex position 반례")

    n, r = ch.n, ch.r
    d = r - 1
    cert = {
        "schema": SCHEMA_ID,
        "claim": {
            "dimension": d,
            "rank": r,
            "n": n,
            "implied_upper_bound": n - 1,
            "statement_katex": f"\\nu_{{\\mathrm{{OM}}}}({d})\\le {n - 1}",
        },
        "reorientation_convention": {
            "fixed_element": 0,
            "bit_i_means_flip_element": "i+1",
            "total": cov.total_reorientations,
        },
        "chirotope": ch.to_dict(),
        "obstructions": [
            {"flip_index": k, "circuit_support": list(S)}
            for k, S in enumerate(cov.obstruction_supports)
        ],
        "provenance": {
            "repository_commit": (repository_commit if repository_commit is not None
                                  else _repository_commit()),
            "generator": generator,
            "config": dict(config or {}),
            "seed": seed,
            "python_version": platform.python_version(),
            "created_at": created_at or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
    }
    cert["hashes"] = {"canonical_certificate_sha256": certificate_hash(cert)}
    return cert


def save_certificate(cert: dict, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cert, f, ensure_ascii=False, indent=1)


def load_certificate(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────── Markdown/KaTeX 보고서 ───────────────────────────
def render_report(cert: dict, *, verified_status: str = "NOT RUN") -> str:
    """certificate 에서 사람이 읽는 Markdown 보고서를 자동 생성.
    verified_status: certificate_verify 결과("CERTIFIED"/"FAILED"/"NOT RUN")."""
    c = cert["claim"]
    d, r, n = c["dimension"], c["rank"], c["n"]
    total = cert["reorientation_convention"]["total"]
    sha = cert.get("hashes", {}).get("canonical_certificate_sha256", "?")
    commit = cert.get("provenance", {}).get("repository_commit", "?")
    return f"""# Certified McMullen–OM Witness

## Claim (주장)

Let

\\[
E=\\{{0,\\ldots,{n - 1}\\}},\\qquad r=d+1={r}.
\\]

The certificate defines a uniform chirotope

\\[
\\chi:\\binom{{E}}{{{r}}}\\to\\{{-1,+1\\}}.
\\]

For every reorientation \\(\\rho\\in(\\mathbb Z/2\\mathbb Z)^{{{n - 1}}}\\)
(원소 0 고정, 총 \\(2^{{{n - 1}}}={total}\\)개),
the certificate provides a support

\\[
S_\\rho\\in\\binom{{E}}{{{r + 1}}}
\\]

such that

\\[
\\min\\left(
|C_{{\\chi^\\rho,S_\\rho}}^{{+}}|,
|C_{{\\chi^\\rho,S_\\rho}}^{{-}}|
\\right)\\le1 .
\\]

Therefore no reorientation is in convex position, and hence

\\[
{c["statement_katex"]} .
\\]

## Verification (검증 상태)

- GP validity: VERIFIED
- Reorientations checked: \\(2^{{{n - 1}}}={total}\\)
- Independent certificate replay: {verified_status}
- Lean kernel: NOT FORMALIZED
- Repository commit: `{commit}`
- Certificate SHA-256: `{sha}`

## 재검증 방법

```bash
python certificate_verify.py <이 certificate 의 경로>
```

독립 verifier 는 이 저장소의 coverage 구현을 재사용하지 않고, 각 obstruction 을
`om_core.Chirotope.reorient(...).circuit(...)` 로 직접 순회 검사한다. 모든
obligation 을 통과해야만 CERTIFIED 다 (CERTIFIED 는 FORMALIZED 가 아니다 —
Lean 등 proof assistant kernel 수락은 별도 단계다).
"""


# ─────────────────────────── CLI ───────────────────────────
def _cmd_from_results(results_path: str, witness_id: str, out_path: str) -> dict:
    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)
    rec = next((x for x in data.get("results", []) if x.get("id") == witness_id), None)
    if rec is None:
        raise SystemExit(f"FAIL: results 에 id={witness_id} 레코드가 없음")
    if not rec.get("is_witness"):
        raise SystemExit(f"FAIL: id={witness_id} 는 witness 레코드가 아님")
    ch = Chirotope.from_dict(rec["chirotope"])
    run = data.get("run", {})
    cert = build_certificate(
        ch,
        generator=str(run.get("backend", "unknown")),
        config={"om_class": run.get("om_class"), "run_id": run.get("id"),
                "om_class_realizable": run.get("om_class_realizable"),
                "criteria_active": run.get("criteria_active"),
                "class_options": run.get("class_options", {}),
                "construction": rec.get("construction")},
        seed=run.get("seed"))
    save_certificate(cert, out_path)
    print(f"certificate 저장: {out_path}")
    print(f"SHA-256: {cert['hashes']['canonical_certificate_sha256']}")
    return cert


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="McMullen-OM witness certificate v1 생성기")
    ap.add_argument("--results", help="ResultsStore JSON 경로")
    ap.add_argument("--witness-id", help="results 안의 witness 레코드 id")
    ap.add_argument("--out", help="certificate 출력 경로")
    ap.add_argument("--certificate", help="기존 certificate 경로 (보고서 생성용)")
    ap.add_argument("--report", help="Markdown 보고서 출력 경로")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    if args.results and args.witness_id and args.out:
        cert = _cmd_from_results(args.results, args.witness_id, args.out)
        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(render_report(cert))
            print(f"보고서 저장: {args.report}")
        return 0

    if args.certificate and args.report:
        cert = load_certificate(args.certificate)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(render_report(cert))
        print(f"보고서 저장: {args.report}")
        return 0

    ap.print_help()
    return 2


# ─────────────────────────── 자체 테스트 ───────────────────────────
def _self_test() -> int:
    import tempfile
    from generator import generate_backtracking

    # (6,3) 의 결정론적 첫 witness (전수 열거 순서 고정 → 항상 같은 chirotope)
    wit = None
    for cand in generate_backtracking(6, 3, dedup=False,
                                      max_candidates=10**9, max_nodes=10**9):
        if not cand.is_reorientable_to_convex()[0]:
            wit = cand
            break
    assert wit is not None

    cert = build_certificate(wit, generator="exhaustive-backtracking",
                             config={"n": 6, "r": 3}, seed=None)
    assert cert["schema"] == SCHEMA_ID
    assert cert["claim"] == {"dimension": 2, "rank": 3, "n": 6,
                             "implied_upper_bound": 5,
                             "statement_katex": "\\nu_{\\mathrm{OM}}(2)\\le 5"}
    assert len(cert["obstructions"]) == 32
    assert sorted(o["flip_index"] for o in cert["obstructions"]) == list(range(32))
    assert cert["hashes"]["canonical_certificate_sha256"] == certificate_hash(cert)

    # 저장/로드 왕복 + hash 불변
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "cert.json")
        save_certificate(cert, p)
        back = load_certificate(p)
        assert back == cert
        assert certificate_hash(back) == back["hashes"]["canonical_certificate_sha256"]
        rp = os.path.join(tmp, "report.md")
        with open(rp, "w", encoding="utf-8") as f:
            f.write(render_report(back, verified_status="CERTIFIED"))
        assert os.path.getsize(rp) > 0

    # 독립 verifier 왕복 (certificate_verify 는 이 모듈을 import 하지 않는다)
    import certificate_verify
    checks = certificate_verify.verify_certificate(cert)
    assert "hash" in checks[-1]     # 마지막 obligation 이 hash 검증

    # non-witness 는 certificate 를 만들 수 없어야 한다
    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])
    try:
        build_certificate(quad)
        raise AssertionError("non-witness 인데 certificate 가 생성됨")
    except ValueError as e:
        assert "witness 가 아님" in str(e)

    print("certificate self-test OK (생성/왕복/독립검증/비-witness 거부)")
    return 0


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    sys.exit(main())
