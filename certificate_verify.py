"""
certificate_verify.py — McMullen-OM witness certificate v1 의 **독립** 검증기.

Epic #37 / Task #38 (source: chatgpt, relayed by user).

## 독립성 계약 (신뢰 모델의 핵심)

이 모듈은 다음을 import 하지 않는다:
    reorientation_cover / certificate / search / generator / theorist / memory /
    manager / UI 코드
허용되는 것은 표준 라이브러리와 `om_core.Chirotope`(현재 trusted kernel)뿐이다.
coverage bitmask 구현을 재사용하지 않고, certificate 의 각 obstruction 을
`chi.reorient(flip).circuit(support)` 로 직접 순회 검사한다 — 최적화된 coverage
경로에 버그가 있어도 이 검증기는 독립적으로 잡아낸다.

모든 obligation 을 통과한 뒤에만 상태를 CERTIFIED 로 출력한다. 실패 시 exit code 는
0 이 아니며, 어떤 obligation 에서 실패했는지 명시한다. 예:
    FAIL: obstruction_unbalanced: flip_index=731 does not produce an unbalanced circuit

CLI:
    python certificate_verify.py <certificate.json>
    python certificate_verify.py --self-test
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from itertools import combinations
from math import comb

from om_core import Chirotope

SCHEMA_ID = "mcmullen-om-certificate/v1"


class CertificateError(Exception):
    """obligation 이름과 메시지를 담는 검증 실패."""

    def __init__(self, obligation: str, message: str):
        self.obligation = obligation
        super().__init__(f"{obligation}: {message}")


# ── 독립 재구현 (reorientation_cover 를 import 하지 않기 위한 자체 디코더) ──
def _flip_set_from_index_independent(index: int, n: int) -> set:
    """bit i ⟺ 원소 i+1 반전, 원소 0 고정 — certificate convention 의 독립 구현."""
    return {e for e in range(1, n) if (index >> (e - 1)) & 1}


def _canonical_json_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def verify_certificate(cert: dict) -> list[str]:
    """certificate 를 처음부터 끝까지 검증. 통과한 obligation 이름 목록을 반환하고,
    실패하면 첫 실패 지점에서 CertificateError 를 던진다 (이후 검사는 하지 않는다)."""
    done: list[str] = []

    def ok(name: str):
        done.append(name)

    # 1. schema version
    if cert.get("schema") != SCHEMA_ID:
        raise CertificateError("schema", f"지원하지 않는 schema: {cert.get('schema')!r}")
    ok("schema")

    # 2. (n, r, d) 일관성
    claim = cert.get("claim", {})
    chd = cert.get("chirotope", {})
    n, r, d = claim.get("n"), claim.get("rank"), claim.get("dimension")
    if not (isinstance(n, int) and isinstance(r, int) and isinstance(d, int)):
        raise CertificateError("claim_types", "claim 의 n/rank/dimension 이 정수가 아님")
    if chd.get("n") != n or chd.get("r") != r:
        raise CertificateError("nr_consistency",
                               f"claim(n={n},r={r}) 과 chirotope(n={chd.get('n')},"
                               f"r={chd.get('r')}) 불일치")
    ok("nr_consistency")

    # 3. affine 모델: d = r - 1
    if d != r - 1:
        raise CertificateError("affine_dimension", f"d={d} != r-1={r - 1}")
    ok("affine_dimension")

    # 4. sign key 개수 = C(n, r)
    signs_raw = chd.get("signs", {})
    if len(signs_raw) != comb(n, r):
        raise CertificateError("sign_count",
                               f"sign 개수 {len(signs_raw)} != C({n},{r})={comb(n, r)}")
    ok("sign_count")

    # 5. 모든 값이 ±1
    if not all(v in (1, -1) for v in signs_raw.values()):
        raise CertificateError("sign_values", "±1 이 아닌 sign 값 존재")
    ok("sign_values")

    # 6. 모든 key 가 정렬된 서로 다른 r-튜플 (원소 범위 포함)
    seen_keys = set()
    for k in signs_raw:
        try:
            t = tuple(int(x) for x in k.split(","))
        except ValueError:
            raise CertificateError("sign_keys", f"정수 튜플이 아닌 key: {k!r}")
        if len(t) != r or list(t) != sorted(set(t)) \
                or t[0] < 0 or t[-1] >= n:
            raise CertificateError("sign_keys", f"부적법한 key: {k!r}")
        if t in seen_keys:
            raise CertificateError("sign_keys", f"중복 key: {k!r}")
        seen_keys.add(t)
    ok("sign_keys")

    chi = Chirotope.from_dict(chd)

    # 7. GP validity (trusted kernel)
    if not chi.is_valid():
        raise CertificateError("gp_validity", "Grassmann–Plücker 공리 위반")
    ok("gp_validity")

    # 8. obstruction 수 = 2^(n-1) (+ convention 필드 일관성)
    total = 1 << (n - 1)
    conv = cert.get("reorientation_convention", {})
    if conv.get("fixed_element") != 0 or conv.get("total") != total:
        raise CertificateError("convention",
                               f"reorientation_convention 불일치 (기대 total={total})")
    obstructions = cert.get("obstructions", [])
    if len(obstructions) != total:
        raise CertificateError("obstruction_count",
                               f"obstruction 수 {len(obstructions)} != 2^{n - 1}={total}")
    ok("obstruction_count")

    # 9. 모든 flip index 가 정확히 한 번
    idxs = [o.get("flip_index") for o in obstructions]
    if not all(isinstance(i, int) and 0 <= i < total for i in idxs) \
            or len(set(idxs)) != total:
        raise CertificateError("flip_index_bijection",
                               "flip_index 가 [0, 2^(n-1)) 의 전단사가 아님")
    ok("flip_index_bijection")

    # 10~11. support 크기 r+1, 원소 범위/중복
    for o in obstructions:
        S = o.get("circuit_support", [])
        if len(S) != r + 1:
            raise CertificateError("support_size",
                                   f"flip_index={o['flip_index']}: |support|={len(S)} != r+1")
        if len(set(S)) != len(S) or not all(isinstance(e, int) and 0 <= e < n for e in S):
            raise CertificateError("support_elements",
                                   f"flip_index={o['flip_index']}: 부적법한 support {S}")
    ok("support_size")
    ok("support_elements")

    # 12. 각 재배향에서 해당 circuit 이 실제로 unbalanced 인지 (trusted kernel 직접 순회)
    for o in obstructions:
        idx = o["flip_index"]
        support = tuple(sorted(o["circuit_support"]))
        flip = _flip_set_from_index_independent(idx, n)
        rch = chi.reorient(flip)
        circuit = rch.circuit(support)
        pos = sum(1 for sign in circuit.values() if sign > 0)
        neg = len(circuit) - pos
        if min(pos, neg) > 1:
            raise CertificateError(
                "obstruction_unbalanced",
                f"flip_index={idx} does not produce an unbalanced circuit "
                f"(support={list(support)}, pos={pos}, neg={neg})")
    ok("obstruction_unbalanced")

    # 13. 도출 상한 = n - 1
    if claim.get("implied_upper_bound") != n - 1:
        raise CertificateError("implied_upper_bound",
                               f"{claim.get('implied_upper_bound')} != n-1={n - 1}")
    ok("implied_upper_bound")

    # 14. canonical hash 일치
    body = {k: v for k, v in cert.items() if k != "hashes"}
    got = hashlib.sha256(_canonical_json_bytes(body)).hexdigest()
    want = cert.get("hashes", {}).get("canonical_certificate_sha256")
    if got != want:
        raise CertificateError("hash", f"SHA-256 불일치: 재계산={got} 기록={want}")
    ok("hash")

    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="McMullen-OM certificate v1 독립 검증기")
    ap.add_argument("path", nargs="?", help="certificate JSON 경로")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.path:
        ap.print_help()
        return 2

    with open(args.path, encoding="utf-8") as f:
        cert = json.load(f)
    try:
        checks = verify_certificate(cert)
    except CertificateError as e:
        print(f"FAIL: {e}")
        return 1
    c = cert["claim"]
    print(f"CERTIFIED: nu_OM({c['dimension']}) <= {c['implied_upper_bound']} "
          f"(n={c['n']}, rank={c['rank']}, 재배향 {cert['reorientation_convention']['total']}개 "
          f"전부 obstruction 확인, obligation {len(checks)}개 통과)")
    print(f"SHA-256: {cert['hashes']['canonical_certificate_sha256']}")
    return 0


# ─────────────────────────── 자체 테스트 ───────────────────────────
def _self_test() -> int:
    import copy
    import os

    # golden fixture (있으면) + 즉석 생성 대신, 검증기 독립성을 지키기 위해
    # 여기서는 fixture 검증과 '조작 → 반드시 실패' 음성 테스트만 수행한다.
    here = os.path.dirname(os.path.abspath(__file__))
    golden = os.path.join(here, "fixtures", "golden_certificate_d2_n6.json")
    if not os.path.exists(golden):
        print("SKIP: golden fixture 없음 — 저장소 상태 확인 필요")
        return 1
    with open(golden, encoding="utf-8") as f:
        cert = json.load(f)

    checks = verify_certificate(cert)
    assert checks[-1] == "hash" and "obstruction_unbalanced" in checks
    print(f"golden certificate CERTIFIED (obligation {len(checks)}개 통과)")

    def expect_fail(mutated: dict, obligation: str):
        try:
            verify_certificate(mutated)
        except CertificateError as e:
            assert e.obligation == obligation, \
                f"기대 obligation={obligation}, 실제={e.obligation}"
            return
        raise AssertionError(f"조작된 certificate({obligation})가 통과함")

    # (a) schema 조작
    bad = copy.deepcopy(cert); bad["schema"] = "unknown/v0"
    expect_fail(bad, "schema")
    # (b) sign 값 조작 → GP 위반 또는 obstruction 불일치보다 먼저 hash 로 잡히면 안 되므로
    #     검사 순서상 gp_validity 이전 단계들이 통과하는 조작을 사용: 부호 하나 뒤집기.
    bad = copy.deepcopy(cert)
    k0 = next(iter(bad["chirotope"]["signs"]))
    bad["chirotope"]["signs"][k0] = -bad["chirotope"]["signs"][k0]
    try:
        verify_certificate(bad)
        raise AssertionError("부호 조작 certificate 가 통과함")
    except CertificateError as e:
        assert e.obligation in ("gp_validity", "obstruction_unbalanced"), e.obligation
    # (c) obstruction 하나 삭제
    bad = copy.deepcopy(cert); bad["obstructions"] = bad["obstructions"][:-1]
    expect_fail(bad, "obstruction_count")
    # (d) flip_index 중복
    bad = copy.deepcopy(cert)
    bad["obstructions"][1]["flip_index"] = bad["obstructions"][0]["flip_index"]
    expect_fail(bad, "flip_index_bijection")
    # (e) support 를 '그 재배향을 차단하지 못하는' 것으로 교체 — 즉석 탐색으로 찾는다
    chi = Chirotope.from_dict(cert["chirotope"])
    n, r = chi.n, chi.r
    target = cert["obstructions"][0]
    flip = _flip_set_from_index_independent(target["flip_index"], n)
    rch = chi.reorient(flip)
    balanced_support = None
    for S in combinations(range(n), r + 1):
        C = rch.circuit(S)
        pos = sum(1 for v in C.values() if v > 0)
        if min(pos, len(C) - pos) > 1:
            balanced_support = list(S)
            break
    if balanced_support is not None:      # witness 여도 개별 재배향엔 균형 회로가 있을 수 있음
        bad = copy.deepcopy(cert)
        bad["obstructions"][0]["circuit_support"] = balanced_support
        expect_fail(bad, "obstruction_unbalanced")
    # (f) 상한 조작
    bad = copy.deepcopy(cert); bad["claim"]["implied_upper_bound"] = n - 2
    expect_fail(bad, "implied_upper_bound")
    # (g) hash 조작
    bad = copy.deepcopy(cert)
    bad["hashes"]["canonical_certificate_sha256"] = "0" * 64
    expect_fail(bad, "hash")
    # (h) 본문 조작 후 hash 미갱신 → hash 단계에서 잡힘 (앞 단계는 전부 적법한 조작)
    bad = copy.deepcopy(cert)
    bad["provenance"]["generator"] = "tampered"
    expect_fail(bad, "hash")

    print("certificate_verify self-test OK (양성 1 + 음성 8 케이스)")
    return 0


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    sys.exit(main())
