"""
store.py — 결과/근거(provenance) 저장소.

요구사항 #3: "어떤 구성이 어떤 상한 개선을 가져왔고, 어떤 이론적 성질을 사용했는지"를
한 건마다 명확히 기록한다. JSON 으로 저장되며 대시보드가 그대로 읽는다.

기록 단위:
  run     : 이번 실행의 설정/활성 기준/파라미터
  results : 채택된 후보 및 witness 들 (각각 상한 개선 + 만족/불만족 기준 포함)
  rounds  : 라운드별 통계 + 그 라운드에 '검증 통과로 승격된' LLM 편향
"""
from __future__ import annotations
import json, time, uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

from om_core import Chirotope


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ResultRecord:
    n: int
    r: int
    d: int
    is_witness: bool
    reward: float
    criteria_satisfied: list[str]
    criteria_failed: list[str]
    chirotope: dict                      # om_core.Chirotope.to_dict()
    implied_upper_bound: Optional[int] = None
    target_bound: Optional[int] = None
    solves_conjecture: bool = False
    promoted_biases: list[dict] = field(default_factory=list)
    found_at: str = field(default_factory=_now)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])


@dataclass
class RoundRecord:
    round: int
    num_candidates: int
    num_accepted: int
    num_witness: int
    best_upper_bound: Optional[int]
    promoted_biases: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)      # Discovery Engine 발견
    failures: dict = field(default_factory=dict)            # 후보 탈락 사유 집계(학습 신호)
    debate: Optional[list] = None                           # 토론 transcript(라운드별 제안)
    at: str = field(default_factory=_now)


class ResultsStore:
    def __init__(self, run_meta: dict):
        self.run = dict(run_meta)
        self.run.setdefault("id", uuid.uuid4().hex[:10])
        self.run.setdefault("started_at", _now())
        self.results: list[ResultRecord] = []
        self.rounds: list[RoundRecord] = []

    def add_result(self, ch: Chirotope, ev: dict, report, promoted_biases=None) -> ResultRecord:
        """ev: mcmullen_evaluate 결과, report: CriteriaSet.evaluate 결과."""
        rec = ResultRecord(
            n=ch.n, r=ch.r, d=ch.r - 1,
            is_witness=bool(ev.get("witness")),
            reward=float(ev.get("reward", 0.0)),
            criteria_satisfied=list(report.satisfied),
            criteria_failed=list(report.failed),
            chirotope=ch.to_dict(),
            implied_upper_bound=ev.get("implied_upper_bound"),
            target_bound=ev.get("target_bound"),
            solves_conjecture=bool(ev.get("solves_conjecture", False)),
            promoted_biases=list(promoted_biases or []),
        )
        self.results.append(rec)
        return rec

    def add_round(self, rr: RoundRecord):
        self.rounds.append(rr)

    def best_witness(self) -> Optional[ResultRecord]:
        wins = [r for r in self.results if r.is_witness]
        return min(wins, key=lambda r: r.n) if wins else None

    def to_dict(self) -> dict:
        self.run.setdefault("finished_at", _now())
        self.run["finished_at"] = _now()
        bw = self.best_witness()
        return {
            "run": self.run,
            "summary": {
                "num_results": len(self.results),
                "num_witness": sum(1 for r in self.results if r.is_witness),
                "best_upper_bound": bw.implied_upper_bound if bw else None,
                "best_witness_id": bw.id if bw else None,
            },
            "results": [asdict(r) for r in self.results],
            "rounds": [asdict(r) for r in self.rounds],
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)


if __name__ == "__main__":
    from om_core import mcmullen_evaluate
    from criteria import CriteriaSet
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    cs = CriteriaSet.from_config([{"name": "valid"}, {"name": "acyclic"},
                                  {"name": "not_reorientable_to_convex", "mode": "target"}])
    store = ResultsStore({"d": 2, "r": 3, "note": "demo"})
    store.add_result(tri, mcmullen_evaluate(tri), cs.evaluate(tri))
    store.add_round(RoundRecord(0, 1, 1, 0, None))
    store.save("/tmp/_demo_results.json")
    print("saved; summary =", store.to_dict()["summary"])
