"""
autonomous_ui.py — 자율 ResearchStep IR 경로의 Streamlit 비의존 연결 계층.

대시보드 위젯 값을 research_manager.run_autonomous_research 인자로 전달하고,
백그라운드 실행 상태·audit/backlog/certificate·witness 구조 분석 결과를 보관한다.
수학적 판정이나 Process Verifier 로직은 재구현하지 않는다.
"""
from __future__ import annotations

import copy
import json
import os
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from certificate import save_certificate
from certificate_export import export_bundle
from research_ir import STEP_KINDS
from research_manager import run_autonomous_research
from witness_analysis import minimal_obstruction_cover, witness_profile


@dataclass(frozen=True)
class AutonomousRunConfig:
    d: int
    r: int
    rounds: int = 2
    debate_rounds: int = 1
    max_witnesses: int = 1
    enabled_kinds: tuple[str, ...] = tuple(STEP_KINDS)
    cegis_max_outer_models: int = 100_000
    cegis_inner_timeout_ms: Optional[int] = None
    evidence_path: Optional[str] = None
    model: str = "qwen2.5"
    ollama_url: str = "http://localhost:11434/api/chat"
    ollama_temperature: float = 0.7
    ollama_timeout_s: int = 300
    common_prompt: str = ""
    personas: dict[str, str] = field(default_factory=dict)
    analyze_witnesses: bool = True
    export_certificates: bool = True
    artifact_dir: Optional[str] = None


def validate_config(cfg: AutonomousRunConfig) -> list[str]:
    """실행 전에 막아야 할 UI 설정 오류만 반환한다."""
    errors = []
    if cfg.r != cfg.d + 1:
        errors.append(f"일반 McMullen 탐색에서는 rank({cfg.r})가 d+1({cfg.d + 1})이어야 합니다.")
    if cfg.rounds < 1 or cfg.debate_rounds < 1:
        errors.append("자율 연구 라운드와 제안 토론 라운드는 1 이상이어야 합니다.")
    if cfg.max_witnesses < 1:
        errors.append("최대 witness 수는 1 이상이어야 합니다.")
    unknown = sorted(set(cfg.enabled_kinds) - set(STEP_KINDS))
    if unknown:
        errors.append(f"알 수 없는 ResearchStep kind: {unknown}")
    if cfg.cegis_max_outer_models < 1:
        errors.append("CEGIS outer model 예산은 1 이상이어야 합니다.")
    if cfg.cegis_inner_timeout_ms is not None and cfg.cegis_inner_timeout_ms < 1:
        errors.append("CEGIS inner timeout은 비우거나 1ms 이상이어야 합니다.")
    if not cfg.ollama_url.startswith(("http://", "https://")):
        errors.append("Ollama URL은 http:// 또는 https://로 시작해야 합니다.")
    return errors


def compose_personas(common_prompt: str, personas: dict[str, str]) -> dict[str, str]:
    """공통 지침을 각 역할 프롬프트 앞에 붙인다. 빈 공통 지침은 원문을 보존한다."""
    common = common_prompt.strip()
    if not common:
        return dict(personas)
    return {role: f"{common}\n\n[역할별 지침]\n{prompt.strip()}"
            for role, prompt in personas.items()}


def make_ollama_client(url: str, *, temperature: float, timeout_s: int) -> Callable:
    """theorist의 llm_fn 계약과 같은 Ollama 클라이언트를 만든다."""
    def chat(model: str, system: str, user: str) -> str:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests 미설치. pip install requests 후 Ollama를 사용하세요.") from exc
        payload = {
            "model": model, "stream": False, "format": "json",
            "options": {"temperature": temperature},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }
        response = requests.post(url, json=payload, timeout=timeout_s)
        response.raise_for_status()
        return response.json()["message"]["content"]
    return chat


@dataclass
class AutonomousProgress:
    state: str = "idle"
    round: int = -1
    rounds_total: int = 0
    witnesses: int = 0
    message: str = ""
    log: list[str] = field(default_factory=list)


class AutonomousResearchRunner:
    """자율 연구 루프를 백그라운드에서 실행하고 읽기 전용 스냅샷을 제공한다."""

    def __init__(self, cfg: AutonomousRunConfig, *, research_fn=run_autonomous_research):
        errors = validate_config(cfg)
        if errors:
            raise ValueError("; ".join(errors))
        self.cfg = cfg
        self._research_fn = research_fn
        self._lock = threading.Lock()
        self._progress = AutonomousProgress(rounds_total=cfg.rounds)
        self._thread: Optional[threading.Thread] = None
        self._error: Optional[str] = None
        self.report: Optional[dict] = None

    def start(self):
        if self._thread is not None:
            raise RuntimeError("이미 시작된 자율 연구 실행입니다.")
        with self._lock:
            self._progress.state = "running"
            self._progress.log.append("자율 ResearchStep IR 연구를 시작했습니다.")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _reporter(self, event: dict):
        with self._lock:
            self._progress.round = int(event.get("round", self._progress.round))
            self._progress.witnesses = int(event.get("witnesses", self._progress.witnesses))
            if event.get("event") == "round_started":
                self._progress.message = f"round {self._progress.round} 제안·검증 중"
            elif event.get("event") == "round_completed":
                counts = event.get("counts", {})
                self._progress.message = f"round {self._progress.round} 완료"
                self._progress.log.append(
                    f"round {self._progress.round}: 분류 {counts}, witness {self._progress.witnesses}")
            self._progress.log = self._progress.log[-200:]

    def _run(self):
        cfg = self.cfg
        try:
            personas = compose_personas(cfg.common_prompt, cfg.personas)
            report = self._research_fn(
                cfg.d, cfg.r, rounds=cfg.rounds, debate_rounds=cfg.debate_rounds,
                max_witnesses=cfg.max_witnesses, enabled_kinds=set(cfg.enabled_kinds),
                cegis_max_outer_models=cfg.cegis_max_outer_models,
                cegis_inner_timeout_ms=cfg.cegis_inner_timeout_ms,
                evidence_path=cfg.evidence_path, model=cfg.model, personas=personas,
                llm_fn=make_ollama_client(
                    cfg.ollama_url, temperature=cfg.ollama_temperature,
                    timeout_s=cfg.ollama_timeout_s),
                reporter=self._reporter, verbose=False)

            report["witness_analysis"] = []
            if cfg.analyze_witnesses:
                for ch in report["witnesses"]:
                    cover = minimal_obstruction_cover(ch, exact=False)
                    report["witness_analysis"].append({
                        "n": ch.n, "r": ch.r,
                        "profile": witness_profile(ch),
                        "obstruction_cover_size": len(cover),
                        "obstruction_cover": [list(s) for s in cover],
                    })

            report["certificate_bundles"] = []
            if cfg.export_certificates and report["certificates"]:
                if not cfg.artifact_dir:
                    raise ValueError("certificate export가 켜져 있지만 artifact_dir가 없습니다.")
                os.makedirs(cfg.artifact_dir, exist_ok=True)
                for idx, cert in enumerate(report["certificates"], start=1):
                    bundle_dir = os.path.join(cfg.artifact_dir, f"certificate_{idx}")
                    os.makedirs(bundle_dir, exist_ok=True)
                    cert_path = os.path.join(bundle_dir, "certificate.json")
                    save_certificate(cert, cert_path)
                    manifest = export_bundle(cert, bundle_dir)
                    report["certificate_bundles"].append({
                        "directory": bundle_dir, "manifest": manifest})

            self.report = report
            with self._lock:
                self._progress.state = "done"
                self._progress.witnesses = len(report["witnesses"])
                self._progress.message = "자율 연구 실행 완료"
        except Exception as exc:
            self._error = f"{type(exc).__name__}: {exc}"
            with self._lock:
                self._progress.state = "error"
                self._progress.message = self._error

    def snapshot(self) -> AutonomousProgress:
        with self._lock:
            return copy.deepcopy(self._progress)

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())


def audit_rows(report: dict) -> list[dict]:
    """audit 결과를 Streamlit dataframe용 평면 행으로 변환한다."""
    rows = []
    for rec in report.get("audits", []):
        if rec["category"] == "malformed":
            bad = rec["malformed"]
            rows.append({"round": rec["round"], "분류": "malformed",
                         "step id": "—", "kind": "—",
                         "주장": "—", "첫 실패": "정규화",
                         "상세": bad.get("error", "")})
            continue
        step, audit = rec["step"], rec["audit"]
        rows.append({"round": rec["round"], "분류": rec["category"],
                     "step id": step["id"], "kind": step["kind"],
                     "주장": step["claim"]["dsl"],
                     "첫 실패": audit.get("first_failed_obligation") or "—",
                     "상세": audit.get("detail", "")})
    return rows


if __name__ == "__main__":
    import tempfile

    defaults = {"geometer": "기하 관점"}
    assert compose_personas("공통 규칙", defaults)["geometer"].startswith("공통 규칙")
    assert compose_personas("", defaults) == defaults
    assert validate_config(AutonomousRunConfig(d=2, r=3)) == []
    assert validate_config(AutonomousRunConfig(d=2, r=4))

    events = []
    def fake_research(d, r, **kwargs):
        kwargs["reporter"]({"event": "round_started", "round": 0,
                            "rounds_total": 1, "witnesses": 0})
        kwargs["reporter"]({"event": "round_completed", "round": 0,
                            "rounds_total": 1, "witnesses": 0,
                            "counts": {"positive": 0}})
        events.append((d, r, kwargs["cegis_max_outer_models"]))
        return {"witnesses": [], "certificates": [], "backlog": [], "facts": [],
                "adopted_rules": [], "rounds": [], "audits": [],
                "evidence_path": kwargs["evidence_path"]}

    cfg = AutonomousRunConfig(d=2, r=3, rounds=1, analyze_witnesses=False,
                              export_certificates=False, cegis_max_outer_models=17)
    runner = AutonomousResearchRunner(cfg, research_fn=fake_research)
    runner.start()
    runner._thread.join(timeout=5)
    assert not runner.is_alive() and runner.snapshot().state == "done"
    assert events == [(2, 3, 17)] and audit_rows(runner.report) == []

    # 결과 후처리 배선: rank-2 알려진 특이 사례를 UI transport fixture 로만 사용한다.
    # 수학적 일반화나 literal McMullen 결과로 해석하지 않는다(CLAUDE.md 불변 조건).
    from certificate import build_certificate
    from om_core import Chirotope
    fixture = Chirotope.alternating(4, 2)
    fixture_cert = build_certificate(fixture, generator="autonomous-ui-self-test")

    def fake_with_artifacts(d, r, **kwargs):
        return {"witnesses": [fixture], "certificates": [fixture_cert],
                "backlog": [], "facts": ["UI fixture"], "adopted_rules": [],
                "rounds": [], "audits": [], "evidence_path": None}

    with tempfile.TemporaryDirectory() as tmp:
        cfg2 = AutonomousRunConfig(d=1, r=2, rounds=1, artifact_dir=tmp)
        runner2 = AutonomousResearchRunner(cfg2, research_fn=fake_with_artifacts)
        runner2.start(); runner2._thread.join(timeout=10)
        assert runner2.snapshot().state == "done"
        assert runner2.report["witness_analysis"][0]["obstruction_cover_size"] > 0
        bundle = runner2.report["certificate_bundles"][0]["directory"]
        assert os.path.exists(os.path.join(bundle, "replay.py"))
    print("autonomous_ui core-contract assertions OK "
          "(설정 검증 / 공통 프롬프트 / 진행 상태 / 예산 전달 / 결과 후처리)")
