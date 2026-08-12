"""
certificate_export.py — WP8: certificate Markdown/LaTeX/Lean export 번들 (#47).

Epic #37. (source: chatgpt, relayed by user)

## 번들 구조

    <out-dir>/
    ├── manifest.json      번들 메타 (파일 목록, trust 상태 — formalized: false)
    ├── certificate.json   certificate v1 원본
    ├── chirotope.json     chirotope 만 분리 (외부 도구 소비용)
    ├── report.md          Markdown/KaTeX 보고서 (certificate.render_report)
    ├── report.tex         LaTeX 보고서
    ├── replay.py          **독립 재검증 스크립트** — 저장소 없이 표준 라이브러리만으로
    │                      certificate.json 을 재검증 (이 저장소의 어떤 모듈도 import 안 함)
    ├── theorem.lean       Lean 4 스켈레톤 (생성만 — kernel 수락 전에는 FORMALIZED 아님)
    └── SHA256SUMS         전 파일 해시 (sha256sum -c 호환)

## 신뢰 경계 (Issue #47)

- Lean 파일을 **생성**했다고 `FORMALIZED` 로 표시하지 않는다. manifest 의
  `formalized` 는 항상 false 로 생성되며, 실제 Lean kernel 수락 후에만 사람이
  별도 절차로 갱신한다. 이 번들의 최고 등급은 `CERTIFIED` 다.
- replay.py 는 번들만 들고 다른 머신에서 실행 가능해야 한다 — 저장소 import 금지,
  표준 라이브러리만. (자체 테스트가 subprocess 로 격리 실행해 확인한다.)

CLI:
    python certificate_export.py --certificate <cert.json> --out-dir <dir>
    python certificate_export.py --self-test
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys

from certificate import load_certificate, render_report, certificate_hash

BUNDLE_SCHEMA = "mcmullen-om-certificate-bundle/v1"

# ── replay.py 템플릿: 저장소 비의존, 표준 라이브러리 전용 ──
REPLAY_TEMPLATE = r'''#!/usr/bin/env python3
"""certificate v1 독립 재검증 스크립트 (자동 생성 — mcmullen-om-certificate-bundle/v1).

이 스크립트는 원 저장소 없이 표준 라이브러리만으로 동작한다. 성공 시 exit 0 과
"CERTIFIED", 실패 시 exit 1 과 실패 지점을 출력한다.
사용법: python replay.py [certificate.json 경로 (기본: 같은 폴더의 certificate.json)]
"""
import hashlib, json, os, sys
from itertools import combinations
from math import comb


def chi(signs, idx):
    arr = list(idx); swaps = 0; m = len(arr)
    for i in range(m):
        for j in range(m - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]; swaps += 1
    base = signs[tuple(arr)]
    return base if swaps % 2 == 0 else -base


def reorient(signs, flip):
    return {t: (s if sum(e in flip for e in t) % 2 == 0 else -s)
            for t, s in signs.items()}


def circuit(signs, S):
    S = tuple(sorted(S))
    return {s: ((-1) ** i) * chi(signs, S[:i] + S[i + 1:])
            for i, s in enumerate(S)}


def fail(obligation, msg):
    print(f"FAIL: {obligation}: {msg}")
    sys.exit(1)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "certificate.json")
    cert = json.load(open(path, encoding="utf-8"))

    if cert.get("schema") != "mcmullen-om-certificate/v1":
        fail("schema", str(cert.get("schema")))
    claim = cert["claim"]; chd = cert["chirotope"]
    n, r, d = claim["n"], claim["rank"], claim["dimension"]
    if chd["n"] != n or chd["r"] != r or d != r - 1:
        fail("nr_consistency", f"n={n} r={r} d={d}")
    raw = chd["signs"]
    if len(raw) != comb(n, r) or not all(v in (1, -1) for v in raw.values()):
        fail("signs", "개수 또는 값 부적법")
    seen_keys = set()
    for k in raw:
        t = tuple(int(x) for x in k.split(","))
        if len(t) != r or list(t) != sorted(set(t)) or t[0] < 0 or t[-1] >= n \
                or t in seen_keys:
            fail("sign_keys", f"부적법/중복 key: {k!r}")
        seen_keys.add(t)
    signs = {tuple(int(x) for x in k.split(",")): v for k, v in raw.items()}
    # Grassmann-Pluecker 3-term validity (uniform OM 이 아닌 부호표의 인증 방지 —
    # 이 검사가 없으면 GP-invalid 부호표도 obstruction 만 맞으면 CERTIFIED 가 된다)
    E = range(n)
    for Y in combinations(E, r - 2):
        rest = [e for e in E if e not in Y]
        for a, b, c, d in combinations(rest, 4):
            s1 = chi(signs, Y + (a, b)) * chi(signs, Y + (c, d))
            s2 = chi(signs, Y + (a, c)) * chi(signs, Y + (b, d))
            s3 = chi(signs, Y + (a, d)) * chi(signs, Y + (b, c))
            if s1 == s3 and s2 == -s1:
                fail("gp_validity", "Grassmann-Pluecker 공리 위반 (uniform OM 아님)")
    total = 1 << (n - 1)
    obstructions = cert["obstructions"]
    if cert["reorientation_convention"]["total"] != total \
            or cert["reorientation_convention"]["fixed_element"] != 0:
        fail("convention", "재배향 convention 불일치")
    if len(obstructions) != total or \
            sorted(o["flip_index"] for o in obstructions) != list(range(total)):
        fail("flip_index_bijection", "obstruction 수/index 부적법")
    for o in obstructions:
        k = o["flip_index"]; S = tuple(sorted(o["circuit_support"]))
        if len(S) != r + 1 or len(set(S)) != r + 1 \
                or not all(0 <= e < n for e in S):
            fail("support", f"flip_index={k}")
        flip = {e for e in range(1, n) if (k >> (e - 1)) & 1}
        C = circuit(reorient(signs, flip), S)
        pos = sum(1 for v in C.values() if v > 0)
        if min(pos, len(C) - pos) > 1:
            fail("obstruction_unbalanced",
                 f"flip_index={k} does not produce an unbalanced circuit")
    if claim["implied_upper_bound"] != n - 1:
        fail("implied_upper_bound", str(claim["implied_upper_bound"]))
    body = {kk: vv for kk, vv in cert.items() if kk != "hashes"}
    got = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode("utf-8")).hexdigest()
    if got != cert["hashes"]["canonical_certificate_sha256"]:
        fail("hash", "SHA-256 불일치")
    print(f"CERTIFIED: nu_OM({d}) <= {n - 1} "
          f"(재배향 {total}개 전부 obstruction 재검증, 저장소 비의존 replay)")
    sys.exit(0)


if __name__ == "__main__":
    main()
'''


def _render_tex(cert: dict) -> str:
    c = cert["claim"]
    d, r, n = c["dimension"], c["rank"], c["n"]
    total = cert["reorientation_convention"]["total"]
    sha = cert["hashes"]["canonical_certificate_sha256"]
    return rf"""\documentclass{{article}}
\usepackage{{amsmath, amssymb}}
\usepackage[margin=2.5cm]{{geometry}}
\title{{Certified McMullen--OM Witness: $\nu_{{\mathrm{{OM}}}}({d})\le {n - 1}$}}
\date{{}}
\begin{{document}}\maketitle
\section*{{Claim}}
Let $E=\{{0,\ldots,{n - 1}\}}$ and $r=d+1={r}$. The certificate defines a uniform
chirotope $\chi:\binom{{E}}{{{r}}}\to\{{-1,+1\}}$. For every reorientation
$\rho\in(\mathbb{{Z}}/2\mathbb{{Z}})^{{{n - 1}}}$ (element $0$ fixed, $2^{{{n - 1}}}={total}$
in total), the certificate provides a support $S_\rho\in\binom{{E}}{{{r + 1}}}$ with
\[ \min\bigl(|C^{{+}}_{{\chi^\rho,S_\rho}}|,\,|C^{{-}}_{{\chi^\rho,S_\rho}}|\bigr)\le 1. \]
Hence no reorientation is in convex position, and therefore
\[ \nu_{{\mathrm{{OM}}}}({d})\le {n - 1}. \]
\section*{{Verification status}}
GP validity: \textsc{{verified}}. Independent replay: \textsc{{certified}}
(\texttt{{replay.py}}). Lean kernel: \textbf{{not formalized}}.\\
Certificate SHA-256: \texttt{{{sha}}}
\end{{document}}
"""


def _render_lean(cert: dict) -> str:
    c = cert["claim"]
    d, r, n = c["dimension"], c["rank"], c["n"]
    total = cert["reorientation_convention"]["total"]
    return f"""/- 자동 생성 Lean 4 스켈레톤 (mcmullen-om-certificate-bundle/v1).

   경고: 이 파일의 존재는 FORMALIZED 를 의미하지 않는다. 실제 Lean kernel 이
   아래 정리들을 수락한 뒤에만 FORMALIZED 등급을 부여할 수 있다 (Issue #47).
   UniformChirotope / ConvexPosition / decodeReorientation 정의부는 향후
   라이브러리 작업(WP8 후속)에서 채워야 한다. -/

-- def witnessChi : UniformChirotope {n} {r} :=
--   -- chirotope.json 의 sign table 에서 생성
--   sorry

-- theorem witnessChi_valid : witnessChi.IsValid := by
--   native_decide

-- def obstructionSupport : Fin {total} → Finset (Fin {n}) :=
--   -- certificate.json 의 obstructions 에서 생성
--   sorry

-- theorem every_reorientation_has_bad_circuit (ρ : Fin {total}) :
--     let A := decodeReorientation ρ
--     let S := obstructionSupport ρ
--     let C := (witnessChi.reorient A).circuit S
--     C.pos.card ≤ 1 ∨ C.neg.card ≤ 1 := by
--   native_decide

-- theorem no_convex_reorientation :
--     ∀ A : Finset (Fin {n}), ¬ ConvexPosition (witnessChi.reorient A) := by
--   sorry

-- theorem mcmullen_upper_bound : nuOM {d} ≤ {n - 1} := by
--   sorry
"""


def export_bundle(cert: dict, out_dir: str) -> dict:
    """certificate 하나에서 번들 전체를 결정론적으로 생성. manifest 를 반환."""
    os.makedirs(out_dir, exist_ok=True)
    # certificate 자체를 완전 검증 (hash 만이 아니라 GP/obstruction 전부 —
    # 부적합 certificate 의 번들화 자체를 거부한다. 0023 참고)
    from certificate_verify import verify_certificate, CertificateError
    try:
        verify_certificate(cert)
    except CertificateError as e:
        raise ValueError(f"certificate 검증 실패({e.obligation}) — 번들 생성 거부") from e

    files: dict[str, str] = {}

    def write(name: str, content: str):
        p = os.path.join(out_dir, name)
        # SHA256은 content의 UTF-8 bytes 기준이다. Windows의 text mode가 \n을
        # \r\n으로 바꾸면 기록한 hash와 실제 파일이 달라지므로 개행 변환을 끈다.
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        files[name] = hashlib.sha256(content.encode("utf-8")).hexdigest()

    write("certificate.json", json.dumps(cert, ensure_ascii=False, indent=1))
    write("chirotope.json", json.dumps(cert["chirotope"], ensure_ascii=False, indent=1))
    write("report.md", render_report(cert, verified_status="CERTIFIED"))
    write("report.tex", _render_tex(cert))
    write("replay.py", REPLAY_TEMPLATE)
    write("theorem.lean", _render_lean(cert))

    manifest = {
        "schema": BUNDLE_SCHEMA,
        "claim": cert["claim"],
        "trust": {"certified": True, "formalized": False,
                  "note": "FORMALIZED 는 Lean kernel 수락 후에만 — 파일 생성은 등급이 아님"},
        "certificate_sha256": cert["hashes"]["canonical_certificate_sha256"],
        "files": dict(files),
    }
    write("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))

    sums = "".join(f"{h}  {name}\n" for name, h in sorted(files.items()))
    with open(os.path.join(out_dir, "SHA256SUMS"), "w", encoding="utf-8", newline="") as f:
        f.write(sums)
    return manifest


def verify_bundle_sums(out_dir: str) -> int:
    """SHA256SUMS 재검증. 통과 파일 수 반환, 불일치 시 ValueError."""
    count = 0
    with open(os.path.join(out_dir, "SHA256SUMS"), encoding="utf-8") as f:
        for line in f:
            h, name = line.strip().split("  ", 1)
            data = open(os.path.join(out_dir, name), "rb").read()
            if hashlib.sha256(data).hexdigest() != h:
                raise ValueError(f"SHA256 불일치: {name}")
            count += 1
    return count


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="certificate v1 export 번들 생성기")
    ap.add_argument("--certificate", help="certificate JSON 경로")
    ap.add_argument("--out-dir", help="번들 출력 폴더")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()
    if not (args.certificate and args.out_dir):
        ap.print_help()
        return 2
    manifest = export_bundle(load_certificate(args.certificate), args.out_dir)
    print(f"번들 생성: {args.out_dir} (파일 {len(manifest['files']) + 1}개, "
          f"trust: certified=True, formalized=False)")
    return 0


def _self_test() -> int:
    import copy
    import subprocess
    import tempfile

    here = os.path.dirname(os.path.abspath(__file__))
    golden = os.path.join(here, "fixtures", "golden_certificate_d2_n6.json")
    cert = load_certificate(golden)

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "bundle")
        manifest = export_bundle(cert, out)

        # (1) 파일 구성 + SHA256SUMS 재검증
        expected = {"certificate.json", "chirotope.json", "report.md", "report.tex",
                    "replay.py", "theorem.lean"}
        assert set(manifest["files"]) >= expected
        # SHA256SUMS 는 manifest.json 자신도 포함 (manifest["files"] + 1)
        assert verify_bundle_sums(out) == len(manifest["files"]) + 1
        print(f"번들 파일 {len(manifest['files']) + 1}개 + SHA256SUMS 재검증 OK")

        # (2) trust 라벨: formalized 는 반드시 False 로 생성
        assert manifest["trust"] == {"certified": True, "formalized": False,
                                     "note": manifest["trust"]["note"]}
        assert "FORMALIZED" in open(os.path.join(out, "theorem.lean"),
                                    encoding="utf-8").read()
        print("trust 라벨 OK (formalized=False 강제, Lean 파일에 경고 포함)")

        # (3) replay.py 가 **저장소 없이** 표준 라이브러리만으로 CERTIFIED 를 재현하는지
        #     — cwd 를 번들 폴더로, 빈 환경에 가깝게 subprocess 격리 실행
        r = subprocess.run([sys.executable, "replay.py"], cwd=out,
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0 and "CERTIFIED" in r.stdout, (r.returncode, r.stdout, r.stderr)
        src = open(os.path.join(out, "replay.py"), encoding="utf-8").read()
        assert "import om_core" not in src and "reorientation" not in src.replace(
            "reorientation_convention", "")     # 저장소 모듈 import 없음
        print("replay.py 저장소 비의존 재검증 OK (subprocess 격리, CERTIFIED)")

        # (4) 조작된 certificate 는 이제 export_bundle 자체가 거부한다 (full verify 게이트).
        #     replay.py 단독 방어도 별도로 확인: 번들 파일을 직접 조작해 넣었을 때
        #     replay 가 비-0 으로 실패해야 한다.
        def replay_standalone(c: dict):
            d2 = os.path.join(tmp, f"standalone_{id(c)}")
            os.makedirs(d2, exist_ok=True)
            with open(os.path.join(d2, "certificate.json"), "w", encoding="utf-8") as f:
                json.dump(c, f, ensure_ascii=False)
            with open(os.path.join(d2, "replay.py"), "w", encoding="utf-8") as f:
                f.write(REPLAY_TEMPLATE)
            return subprocess.run([sys.executable, "replay.py"], cwd=d2,
                                  capture_output=True, text=True, timeout=120)

        bad2 = copy.deepcopy(cert)
        bad2["claim"]["implied_upper_bound"] = 3
        bad2["hashes"]["canonical_certificate_sha256"] = certificate_hash(bad2)
        try:
            export_bundle(bad2, os.path.join(tmp, "bundle_bad2"))
            raise AssertionError("조작 certificate 가 번들화됨 (full verify 게이트 미동작)")
        except ValueError:
            pass
        r3 = replay_standalone(bad2)
        assert r3.returncode != 0 and "FAIL" in r3.stdout, (r3.returncode, r3.stdout)
        print("조작 certificate → export 거부 + replay 단독 비-0 실패 OK")

        # (4b) GP-invalid 부호표 공격 (0023): 임의 ±1 부호표는 uniform OM 이 아니어도
        #      모든 재배향에 unbalanced circuit 을 가질 수 있다 — GP 검사 없는 replay 는
        #      이를 CERTIFIED 로 오인했었다. 이제 export/replay 양쪽에서 차단돼야 한다.
        import random as _rnd
        from itertools import combinations as _c
        from om_core import Chirotope as _Ch
        rng = _rnd.Random(1)
        subs6 = sorted(_c(range(6), 3))
        gp_bad = None
        for _ in range(20000):
            sg = {s: rng.choice([1, -1]) for s in subs6}; sg[subs6[0]] = 1
            ch6 = _Ch(6, 3, sg)
            if ch6.is_valid():
                continue
            if all(any(min(sum(1 for v in ch6.reorient(
                    {e for e in range(1, 6) if (k >> (e - 1)) & 1}).circuit(S).values()
                    if v > 0), 4 - sum(1 for v in ch6.reorient(
                    {e for e in range(1, 6) if (k >> (e - 1)) & 1}).circuit(S).values()
                    if v > 0)) <= 1 for S in _c(range(6), 4)) for k in range(32)):
                gp_bad = ch6
                break
        assert gp_bad is not None
        obst = []
        for k in range(32):
            rch = gp_bad.reorient({e for e in range(1, 6) if (k >> (e - 1)) & 1})
            for S in _c(range(6), 4):
                C = rch.circuit(S); pos = sum(1 for v in C.values() if v > 0)
                if min(pos, 4 - pos) <= 1:
                    obst.append({"flip_index": k, "circuit_support": list(S)}); break
        fake = {"schema": "mcmullen-om-certificate/v1",
                "claim": {"dimension": 2, "rank": 3, "n": 6, "implied_upper_bound": 5,
                          "statement_katex": "x"},
                "reorientation_convention": {"fixed_element": 0,
                                             "bit_i_means_flip_element": "i+1", "total": 32},
                "chirotope": gp_bad.to_dict(), "obstructions": obst,
                "provenance": {"repository_commit": "attack", "generator": "attack",
                               "config": {}, "seed": None, "python_version": "3",
                               "created_at": "2026-01-01"}}
        fake["hashes"] = {"canonical_certificate_sha256": certificate_hash(fake)}
        try:
            export_bundle(fake, os.path.join(tmp, "bundle_gp_bad"))
            raise AssertionError("GP-invalid certificate 가 번들화됨")
        except ValueError as e:
            assert "gp_validity" in str(e), e
        r4 = replay_standalone(fake)
        assert r4.returncode != 0 and "gp_validity" in r4.stdout, (r4.returncode, r4.stdout)
        print("GP-invalid 부호표 공격 → export/replay 양쪽 차단 OK (0023 회귀 방지)")

        # (5) hash 불일치 certificate 는 번들 생성 자체가 거부돼야 한다
        bad3 = copy.deepcopy(cert)
        bad3["provenance"]["generator"] = "tampered"     # hash 미갱신
        try:
            export_bundle(bad3, os.path.join(tmp, "bundle_bad3"))
            raise AssertionError("hash 불일치 certificate 가 번들화됨")
        except ValueError:
            pass
        print("hash 불일치 certificate 번들화 거부 OK")

    print("certificate_export core-contract assertions OK "
          "(비의존 replay / formalized=False 강제 / SHA256SUMS / 음성 케이스)")
    return 0


if __name__ == "__main__":
    # 주의: 이 import 는 **이 모듈의** main 에만 있어야 한다. 위 REPLAY_TEMPLATE 안의
    # main 블록에 넣으면 생성된 replay.py 가 저장소 모듈(console)에 의존하게 되어,
    # "저장소 비의존 재검증"이라는 certificate 의 신뢰 근거가 깨진다 (0029 에서 실측).
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    sys.exit(main())
