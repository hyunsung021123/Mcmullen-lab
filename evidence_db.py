"""
evidence_db.py — WP6b: append-only 수학적 근거 저장소 (#44).

Epic #37. (source: chatgpt, relayed by user)

## 왜 memory.json 으로는 안 되는가

`memory.py` 의 횟수 집계(편향 실패 카운트 등)는 학습 신호로는 유효하지만 수학적
근거 저장소가 아니다 — "무엇이 어떤 검증을 통과/실패했고, 그때 코드/설정이
정확히 무엇이었나"를 재현 가능하게 답할 수 없다. 이 모듈은 그 답을 저장한다.

## 설계: append-only JSONL (SQLite 대신 — 근거는 DECISIONS 0019)

- 레코드는 한 줄 JSON. **수정/삭제 API 가 없다** — append 와 조회뿐.
- 각 레코드에 이전 레코드 hash 를 연결(chain_hash)해 중간 개찬을 탐지한다.
- 저장 항목: step id/claim/parents/assumptions, obligation 결과(첫 실패 포함),
  반례, code commit, config hash, artifact hash, runtime, verifier version,
  certificate path, trust status.
- LLM 자유 서술 필드는 없다 — 검증된 evidence 가 자유 서술보다 우선한다는 원칙을
  스키마 차원에서 강제.

의존성: 표준 라이브러리만.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from typing import Iterator, Optional

VERIFIER_VERSION = "process-verifier/wp6.1"
TRUST_LEVELS = ("CONJECTURAL", "EMPIRICAL", "UNVERIFIED", "REFUTED", "VERIFIED",
                "VERIFIED_BY_SOLVER", "CERTIFIED", "FORMALIZED", "REJECTED")


def derive_trust_status(audit: dict, *, solver_only: bool = False,
                        certificate_verified: bool = False,
                        kernel_accepted: bool = False) -> str:
    """trust 등급을 호출자가 정하지 않고 **증거에서 도출**한다 (0023).

        refuted audit                          → REFUTED
        unverified audit (실행기 없음)          → UNVERIFIED
        positive + kernel_accepted             → FORMALIZED
        positive + certificate_verified        → CERTIFIED
        positive + solver_only                 → VERIFIED_BY_SOLVER
        positive (결정론적 audit 만)            → VERIFIED

    상위 플래그(certificate/kernel)는 positive audit 없이는 아무 효과가 없다 —
    negative 증거에 CERTIFIED 를 붙이는 경로 자체가 존재하지 않는다."""
    status = audit.get("status")
    if status == "refuted":
        return "REFUTED"
    if status == "unverified":
        return "UNVERIFIED"
    if status != "positive":
        return "REJECTED"          # 알 수 없는 audit — 보수적으로
    if kernel_accepted:
        return "FORMALIZED"
    if certificate_verified:
        return "CERTIFIED"
    if solver_only:
        return "VERIFIED_BY_SOLVER"
    return "VERIFIED"


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _repo_commit() -> str:
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10,
                             cwd=os.path.dirname(os.path.abspath(__file__)))
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


class EvidenceDB:
    """append-only JSONL. 수정/삭제 메서드는 의도적으로 존재하지 않는다."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    # ── 기록 ──
    def append(self, *, step: dict, audit: dict,
               solver_only: bool = False,
               certificate_verified: bool = False,
               kernel_accepted: bool = False,
               config: dict | None = None,
               runtime_s: float | None = None,
               certificate_path: Optional[str] = None,
               artifact_hashes: dict | None = None) -> dict:
        """검증 결과 한 건을 append. 기록된 레코드(chain_hash 포함)를 반환.

        trust_status 는 호출자가 지정할 수 없다 — audit 와 플래그에서
        derive_trust_status 로 자동 도출된다 (등급 사칭 경로 차단, 0023)."""
        trust_status = derive_trust_status(
            audit, solver_only=solver_only,
            certificate_verified=certificate_verified,
            kernel_accepted=kernel_accepted)
        if trust_status not in TRUST_LEVELS:
            raise ValueError(f"알 수 없는 trust_status '{trust_status}'")
        prev = self._last_hash()
        rec = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "step": {
                "id": step.get("id"),
                "kind": step.get("kind"),
                "claim": step.get("claim"),
                "parents": step.get("parents", []),
                "assumptions": step.get("assumptions", []),
            },
            "audit": {
                "status": audit.get("status"),
                "passed": audit.get("passed", []),
                "first_failed_obligation": audit.get("first_failed_obligation"),
                "counterexample_id": audit.get("counterexample_id"),
                "counterexample": audit.get("counterexample"),
            },
            "trust_status": trust_status,
            "repository_commit": _repo_commit(),
            "config_hash": hashlib.sha256(_canonical(config or {})).hexdigest(),
            "config": dict(config or {}),
            "artifact_hashes": dict(artifact_hashes or {}),
            "runtime_s": runtime_s,
            "verifier_version": VERIFIER_VERSION,
            "certificate_path": certificate_path,
            "prev_hash": prev,
        }
        rec["chain_hash"] = hashlib.sha256(
            (prev or "genesis").encode() + _canonical(rec)).hexdigest()
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    # ── 조회 ──
    def iter_records(self) -> Iterator[dict]:
        if not os.path.exists(self.path):
            return
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def verify_chain(self) -> int:
        """append-only 무결성 검사: chain hash 재계산. 통과한 레코드 수 반환,
        개찬 발견 시 ValueError."""
        prev = None
        count = 0
        for rec in self.iter_records():
            claimed = rec.get("chain_hash")
            body = {k: v for k, v in rec.items() if k != "chain_hash"}
            if body.get("prev_hash") != prev:
                raise ValueError(f"레코드 {count}: prev_hash 불일치 (append-only 위반)")
            got = hashlib.sha256(
                (prev or "genesis").encode() + _canonical(body)).hexdigest()
            if got != claimed:
                raise ValueError(f"레코드 {count}: chain_hash 불일치 (개찬 의심)")
            prev = claimed
            count += 1
        return count

    def _last_hash(self) -> Optional[str]:
        last = None
        for rec in self.iter_records():
            last = rec.get("chain_hash")
        return last


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    import tempfile
    from research_ir import from_legacy_bias
    from process_verifier import verify_until_first_failure

    with tempfile.TemporaryDirectory() as tmp:
        db = EvidenceDB(os.path.join(tmp, "evidence.jsonl"))

        # (1) 실제 Process Verifier 산출물을 기록/조회
        step = from_legacy_bias({"type": "require_property", "spec": {"name": "acyclic"}})
        audit = verify_until_first_failure(step, d=2, r=3)
        rec1 = db.append(step=step, audit=audit,
                         config={"d": 2, "r": 3}, runtime_s=0.01)
        assert rec1["trust_status"] == ("VERIFIED" if audit["hard_gate_passed"]
                                        else audit["status"].upper())
        step2 = from_legacy_bias({"type": "require_property", "spec": {"name": "nonexistent"}})
        audit2 = verify_until_first_failure(step2, d=2, r=3)
        rec2 = db.append(step=step2, audit=audit2, config={"d": 2, "r": 3})
        assert rec2["trust_status"] == "UNVERIFIED"      # 미등록 기준 = 실행기 부재
        # 등급 사칭 경로 부재: negative audit 에 CERTIFIED 를 붙일 방법이 없다
        fake = db.append(step=step2, audit=audit2, certificate_verified=True)
        assert fake["trust_status"] == "UNVERIFIED"      # 플래그는 positive 없이는 무효
        recs = list(db.iter_records())
        assert len(recs) == 3
        assert recs[1]["audit"]["first_failed_obligation"] == "type_valid"
        assert recs[1]["prev_hash"] == rec1["chain_hash"]
        print("append/조회/체인 연결 OK (3건)")

        # (2) 무결성 검사 통과
        assert db.verify_chain() == 3
        print("chain 무결성 OK")

        # (3) 개찬 탐지: 파일을 직접 조작하면 verify_chain 이 잡아야 한다
        lines = open(db.path, encoding="utf-8").read().splitlines()
        tampered = json.loads(lines[0])
        tampered["trust_status"] = "CERTIFIED"           # 등급 사칭 시도
        with open(db.path, "w", encoding="utf-8") as f:
            f.write(json.dumps(tampered, ensure_ascii=False) + "\n"
                    + "\n".join(lines[1:]) + "\n")
        try:
            db.verify_chain()
            raise AssertionError("개찬이 탐지되지 않음")
        except ValueError as e:
            assert "불일치" in str(e)
        print("개찬 탐지 OK (등급 사칭 → chain_hash 불일치)")

        # (4) 수정/삭제 API 부재 (append-only 계약) + trust 자동 도출 어휘 확인
        assert not hasattr(db, "update") and not hasattr(db, "delete")
        from evidence_db import derive_trust_status as _d
        assert _d({"status": "refuted"}) == "REFUTED"
        assert _d({"status": "unverified"}) == "UNVERIFIED"
        assert _d({"status": "positive"}) == "VERIFIED"
        assert _d({"status": "positive"}, solver_only=True) == "VERIFIED_BY_SOLVER"
        assert _d({"status": "positive"}, certificate_verified=True) == "CERTIFIED"
        assert _d({"status": "refuted"}, certificate_verified=True) == "REFUTED"
        print("append-only 계약 + trust 자동 도출 OK (사칭 경로 없음)")

    print("evidence_db core-contract assertions OK")
