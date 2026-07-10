"""
manager.py — Manager Agent (연구 오케스트레이터). 리뷰의 'Manager → Search/Theory/Discovery/Memory' 반영.

역할:
  · 장기기억(Memory)을 실행들 사이에서 '지속'시킨다(무엇이 통했나 축적).
  · 탐색 루프(run_search: Search + Discovery + Theory 토론)를 구동한다.
  · 끝나면 '연구 보고서'를 만든다: 최선 상한, 해결 여부, 핵심 발견, 승격된 편향, 기억 스냅샷.

이 오케스트레이터가 있어서 단순 탐색기가 아니라 '연구 루프'가 된다:
  탐색 → (검증된 데이터에서) 발견 → 편향 심사(게이트+반례) → 기준/ n 조정 → 재탐색,
  그리고 그 학습이 memory.json 에 남아 다음 실행에 이어진다.

확장 훅(미구현, 문서화만): Literature 에이전트(arXiv 검색) 를 Theory 옆에 붙여
  '논문 근거 → 검증 가능한 편향' 파이프라인으로 확장할 수 있다.
"""
from __future__ import annotations
from dataclasses import asdict

from search import SearchConfig, run_search
from memory import Memory
from progress import Progress, Control


class ResearchManager:
    def __init__(self, memory_path: str = "memory.json"):
        self.memory = Memory(memory_path)

    def run(self, cfg: SearchConfig, out_path: str = "results.json",
            reporter=None, control: Control | None = None):
        """공유 장기기억으로 연구 루프 1회 구동."""
        store = run_search(cfg, out_path=out_path, verbose=False,
                           reporter=reporter, control=control, memory=self.memory)
        return store

    def report(self, store) -> dict:
        data = store.to_dict()
        rounds = data["rounds"]
        # 최신 라운드의 발견 + 전체 승격 편향 취합
        latest_findings = rounds[-1]["findings"] if rounds else []
        promoted = []
        seen = set()
        for rr in rounds:
            for pb in rr.get("promoted_biases", []):
                key = str(pb.get("bias"))
                if key not in seen:
                    seen.add(key); promoted.append(pb)
        best_ub = data["summary"]["best_upper_bound"]
        d_eff = data["run"]["d"]
        return {
            "class": data["run"]["om_class"],
            "solved": bool(best_ub is not None and best_ub == 2 * d_eff + 1),
            "best_upper_bound": best_ub,
            "target_bound": 2 * d_eff + 1,
            "loose_U": data["run"]["U"],
            "num_witness": data["summary"]["num_witness"],
            "key_findings": latest_findings,
            "promoted_biases": promoted,
            "memory": self.memory.snapshot(),
        }

    def print_report(self, store):
        rep = self.report(store)
        print("\n" + "=" * 60)
        print(f"연구 보고서  ·  class={rep['class']}")
        print("=" * 60)
        print(f"최선 상한 : {rep['best_upper_bound']}  (목표 {rep['target_bound']}, "
              f"느슨한 U {rep['loose_U']})   해결={rep['solved']}")
        print(f"witness   : {rep['num_witness']}개")
        if rep["key_findings"]:
            print("핵심 발견 (검증된 데이터 기반):")
            for f in rep["key_findings"][:6]:
                print(f"   - {f['invariant']}={f['value']} [{f['kind']}] {f['support']} {f.get('note','')}")
        if rep["promoted_biases"]:
            print("승격된 편향 (게이트+반례 통과):")
            for pb in rep["promoted_biases"][:6]:
                print(f"   - {pb['bias']}  ({pb.get('gate_reason','')})")
        gens = rep["memory"]["generators"]
        if gens:
            print("장기기억 — 제너레이터:")
            for name, g in gens.items():
                print(f"   - {name}: 시도 {g['attempts']}, witness {g['witnesses']}, "
                      f"최고상한 {g['best_bound']}, 실행 {g['runs']}")
        return rep


if __name__ == "__main__":
    mgr = ResearchManager(memory_path="/tmp/mgr_memory.json")
    cfg = SearchConfig(
        d=3, om_class="realizable_uniform", n_min=8, n_max=8, rounds=1,
        criteria=[{"name": "acyclic", "mode": "require"},
                  {"name": "not_reorientable_to_convex", "mode": "target"}],
        dedup=True, max_candidates_per_round=60, accepted_cap=15,
        discovery_enabled=True, llm_enabled=False)
    store = mgr.run(cfg, out_path="/tmp/mgr_results.json")
    mgr.print_report(store)
