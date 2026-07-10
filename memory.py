"""
memory.py — 장기 기억(결정론적 메타 정보). 리뷰 지적 ④ 반영.

results.json(개별 실행 결과)과 별개로, 여러 실행에 걸쳐 누적되는 '무엇이 통했나'를 저장:
  · generators : 클래스/백엔드별 시도·witness·최고상한
  · criteria   : 각 기준이 witness 에서 실제로 유효했던 빈도
  · biases     : 편향별 제안/승격/실패 횟수 (예: "이 편향은 30번 실패")
  · combos     : 유망한 기준 조합
  · findings   : Discovery Engine 이 찾은 구조적 발견 누적
전부 검증된 데이터에 대한 결정론적 집계다(LLM 주장 저장 아님).
"""
from __future__ import annotations
import json, os, time


def bias_key(bias: dict) -> str:
    t = bias.get("type", "?"); s = bias.get("spec", {})
    return f"{t}|{s.get('name','')}|{s.get('args','')}|{s.get('n','')}"


class Memory:
    def __init__(self, path: str | None = None):
        self.path = path
        self.data = {"generators": {}, "criteria": {}, "biases": {},
                     "combos": {}, "findings": [], "notes": [], "updated": None}
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def save(self):
        if not self.path:
            return
        self.data["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ---------- 기록 ----------
    def record_generator(self, name: str, attempts: int, witnesses: int, best_bound):
        g = self.data["generators"].setdefault(
            name, {"attempts": 0, "witnesses": 0, "best_bound": None, "runs": 0})
        g["attempts"] += attempts; g["witnesses"] += witnesses; g["runs"] += 1
        if best_bound is not None and (g["best_bound"] is None or best_bound < g["best_bound"]):
            g["best_bound"] = best_bound

    def record_criterion(self, name: str, in_witness: bool):
        c = self.data["criteria"].setdefault(name, {"in_witness": 0, "seen": 0})
        c["seen"] += 1
        if in_witness:
            c["in_witness"] += 1

    def record_bias(self, bias: dict, promoted: bool, reason: str = ""):
        b = self.data["biases"].setdefault(
            bias_key(bias), {"proposed": 0, "promoted": 0, "failed": 0, "last_reason": ""})
        b["proposed"] += 1
        b["promoted" if promoted else "failed"] += 1
        b["last_reason"] = reason

    def record_combo(self, criteria_names, witnesses: int):
        key = "+".join(sorted(criteria_names))
        c = self.data["combos"].setdefault(key, {"runs": 0, "witnesses": 0})
        c["runs"] += 1; c["witnesses"] += witnesses

    def add_finding(self, finding: dict):
        self.data["findings"].append({**finding, "at": time.strftime("%H:%M:%S")})
        self.data["findings"] = self.data["findings"][-200:]

    def bias_failed_count(self, bias: dict) -> int:
        return self.data["biases"].get(bias_key(bias), {}).get("failed", 0)

    # ---------- 위원회에 넘길 압축 사실 ----------
    def summary_for_committee(self, max_items: int = 10) -> list[str]:
        lines = []
        for k, b in sorted(self.data["biases"].items(),
                           key=lambda kv: -kv[1]["failed"]):
            if b["failed"] >= 3:
                lines.append(f"편향 '{k}' 은 {b['failed']}회 실패 — 재제안 지양")
        for name, c in self.data["criteria"].items():
            if c["seen"] >= 5 and c["in_witness"] == 0:
                lines.append(f"기준 '{name}' 은 witness 에서 유효한 적 없음")
        for key, c in sorted(self.data["combos"].items(),
                             key=lambda kv: -(kv[1]["witnesses"])):
            if c["witnesses"] > 0:
                lines.append(f"조합 '{key}' 은 유망(witness {c['witnesses']})")
                break
        return lines[:max_items]

    def snapshot(self) -> dict:
        return {"generators": self.data["generators"],
                "criteria": self.data["criteria"],
                "top_failed_biases": sorted(
                    ({"bias": k, **v} for k, v in self.data["biases"].items()),
                    key=lambda x: -x["failed"])[:8],
                "findings": self.data["findings"][-12:]}


if __name__ == "__main__":
    m = Memory("/tmp/mem_test.json")
    m.record_generator("realizable_uniform", attempts=300, witnesses=5, best_bound=7)
    m.record_criterion("acyclic", True); m.record_criterion("acyclic", True)
    for _ in range(4):
        m.record_bias({"type": "require_property", "spec": {"name": "convex_position"}}, promoted=False, reason="공허")
    m.record_combo(["acyclic", "not_reorientable_to_convex"], witnesses=5)
    m.save()
    print("failed count(convex require):",
          m.bias_failed_count({"type": "require_property", "spec": {"name": "convex_position"}}))
    print("summary:", m.summary_for_committee())
