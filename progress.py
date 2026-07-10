"""
progress.py — 실시간 현황(요구사항 #2) + 일시정지/중단.

구성:
  Progress     : 루프 현황 스냅샷(현재 최선 구성, 최소 상한, 카운터, 경과시간, 로그).
  Control      : pause/resume/stop 플래그(스레드 안전). 루프가 후보마다 checkpoint() 확인.
  SearchRunner : run_search 를 백그라운드 스레드로 돌리고, 현황을 폴링하고, 제어한다.

CLI 와 UI 모두 같은 메커니즘을 쓴다. 중단 시에도 그때까지의 결과는 저장된다.
"""
from __future__ import annotations
import threading, time, copy
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Progress:
    round: int = 0
    n: int = 0
    candidates: int = 0                  # 이번 실행에서 처리한 후보 누계
    accepted: int = 0
    witnesses: int = 0
    best_upper_bound: Optional[int] = None      # = 지금까지 가장 작은 상한
    best_config: Optional[dict] = None          # {id,n,implied_upper_bound,criteria_satisfied}
    elapsed: float = 0.0
    message: str = ""
    log: list = field(default_factory=list)     # 최근 로그 줄(최대 200)
    state: str = "idle"                          # snapshot() 가 채움


class Control:
    """pause/resume/stop. 루프는 후보 사이마다 checkpoint() 를 부른다."""
    def __init__(self):
        self._pause = threading.Event()
        self._stop = threading.Event()

    def pause(self):  self._pause.set()
    def resume(self): self._pause.clear()
    def stop(self):   self._stop.set(); self._pause.clear()
    def is_paused(self):  return self._pause.is_set()
    def is_stopped(self): return self._stop.is_set()

    def checkpoint(self, poll: float = 0.1) -> bool:
        """일시정지면 블록(중단되면 즉시 해제). 계속 진행하면 True, 중단이면 False."""
        while self._pause.is_set() and not self._stop.is_set():
            time.sleep(poll)
        return not self._stop.is_set()


class SearchRunner:
    """run_search 를 스레드로 구동. snapshot()/pause()/resume()/stop() 제공."""
    def __init__(self, cfg, out_path: str = "results.json"):
        self.cfg = cfg
        self.out_path = out_path
        self.control = Control()
        self.store = None
        self._lock = threading.Lock()
        self._prog = Progress()
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._finished = False
        self._error: Optional[str] = None

    # 루프가 호출하는 보고 콜백
    def _reporter(self, prog: Progress):
        with self._lock:
            self._prog = prog

    def start(self):
        self._started = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        from search import run_search
        try:
            self.store = run_search(self.cfg, out_path=self.out_path, verbose=False,
                                    reporter=self._reporter, control=self.control)
        except Exception as e:
            self._error = f"{type(e).__name__}: {e}"
        finally:
            self._finished = True

    def snapshot(self) -> Progress:
        with self._lock:
            p = copy.deepcopy(self._prog)
        if self._error:
            p.state = "error"; p.message = self._error
        elif not self._started:
            p.state = "idle"
        elif self._finished:
            p.state = "stopped" if self.control.is_stopped() else "done"
        elif self.control.is_stopped():
            p.state = "stopping"
        elif self.control.is_paused():
            p.state = "paused"
        else:
            p.state = "running"
        return p

    def pause(self):  self.control.pause()
    def resume(self): self.control.resume()
    def stop(self):   self.control.stop()
    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())


if __name__ == "__main__":
    # 헤드리스 점검: 백그라운드 실행 + 일시정지 + 재개 + 중단
    from search import SearchConfig
    cfg = SearchConfig(d=2, om_class="uniform", n_min=6, n_max=6, rounds=1,
                       criteria=[{"name": "acyclic", "mode": "require"},
                                 {"name": "not_reorientable_to_convex", "mode": "target"}],
                       max_candidates_per_round=300)
    r = SearchRunner(cfg, out_path="/tmp/runner_test.json")
    r.start()
    time.sleep(0.05); r.pause()
    s = r.snapshot(); print("paused snapshot:", s.state, "cand=", s.candidates)
    time.sleep(0.2); r.resume()
    while r.is_alive():
        time.sleep(0.1)
    s = r.snapshot()
    print("final:", s.state, "best_upper_bound=", s.best_upper_bound,
          "witnesses=", s.witnesses, "best_config=", s.best_config)
