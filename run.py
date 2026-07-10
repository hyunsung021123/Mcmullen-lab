#!/usr/bin/env python3
"""
run.py — 명령행 진입점. 설정(YAML/JSON)을 읽어 탐색 루프를 돌린다.
실시간 한 줄 현황을 출력하고, Ctrl-C 로 안전하게 중단(부분 결과 저장)한다.

예:
  python run.py --config config.example.yaml
  python run.py --config config.example.yaml --class realizable_uniform --d 3 --n-min 8
  python run.py --config config.example.yaml --class rank2_uniform
  python run.py --config config.example.yaml --llm --model qwen2.5
"""
from __future__ import annotations
import argparse, json, sys, signal

from search import SearchConfig, run_search
from progress import Control, Progress
from om_classes import list_classes


def load_config(path: str) -> dict:
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError:
            sys.exit("PyYAML 이 필요합니다:  pip install pyyaml   (또는 JSON 설정을 쓰세요)")
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_reporter():
    last_msg = [""]
    def reporter(p: Progress):
        if p.message and p.message != last_msg[0]:
            last_msg[0] = p.message
            sys.stdout.write("\r" + " " * 100 + "\r")     # 줄 비우기
            print(p.message)
        bc = f" best=n{p.best_config['n']}→{p.best_config['implied_upper_bound']}" if p.best_config else ""
        line = (f"\r[{p.state}] round {p.round} n={p.n} | 후보 {p.candidates} "
                f"witness {p.witnesses} | 최소상한 "
                f"{p.best_upper_bound if p.best_upper_bound is not None else '—'}{bc} "
                f"| {p.elapsed:5.1f}s")
        sys.stdout.write(line[:99]); sys.stdout.flush()
    return reporter


def main():
    ap = argparse.ArgumentParser(description="McMullen-OM 탐색 루프")
    ap.add_argument("--config", default="config.example.yaml")
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--class", dest="om_class", help="탐색 클래스(uniform/realizable_uniform/rank2_uniform/cyclic/...)")
    ap.add_argument("--list-classes", action="store_true", help="사용 가능한 클래스 출력 후 종료")
    ap.add_argument("--d", type=int)
    ap.add_argument("--n-min", type=int)
    ap.add_argument("--n-max", type=int)
    ap.add_argument("--U", type=int)
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--backend", choices=["backtracking", "random", "z3"],
                    help="generic 클래스 백엔드 override")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--memory", dest="memory_path", help="장기기억 파일 경로(누적)")
    ap.add_argument("--debate-rounds", type=int, dest="debate_rounds")
    ap.add_argument("--no-discovery", action="store_true")
    ap.add_argument("--research", action="store_true",
                    help="ResearchManager 로 구동하고 연구 보고서 출력")
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--no-dedup", action="store_true")
    args = ap.parse_args()

    if args.list_classes:
        for c in list_classes():
            print(f"  {c['name']:20} rank={c['rank']!s:5} {c['description']}")
            if c["note"]:
                print(f"  {'':20} ⚠ {c['note']}")
        return

    raw = load_config(args.config)
    for cli, cfg_key in [("om_class", "om_class"), ("d", "d"), ("n_min", "n_min"),
                         ("n_max", "n_max"), ("U", "U"), ("rounds", "rounds"),
                         ("backend", "backend"), ("seed", "seed"), ("model", "llm_model"),
                         ("memory_path", "memory_path"), ("debate_rounds", "debate_rounds")]:
        v = getattr(args, cli, None)
        if v is not None:
            raw[cfg_key] = v
    if args.llm:
        raw["llm_enabled"] = True
    if args.no_dedup:
        raw["dedup"] = False
    if args.no_discovery:
        raw["discovery_enabled"] = False
    if "d" not in raw:
        sys.exit("설정에 d(차원)가 필요합니다.")

    cfg = SearchConfig(**{k: v for k, v in raw.items()
                          if k in SearchConfig.__dataclass_fields__})

    control = Control()
    def on_sigint(sig, frame):
        sys.stdout.write("\n[Ctrl-C] 중단 요청 — 부분 결과 저장 중…\n")
        control.stop()
    signal.signal(signal.SIGINT, on_sigint)

    print(f"▶ class={raw.get('om_class','uniform')}  d={cfg.d}  "
          f"backend={raw.get('backend') or '클래스 기본'}  "
          f"llm={'on' if raw.get('llm_enabled') else 'off'}  "
          f"discovery={'off' if args.no_discovery else 'on'}  "
          f"{'[research]' if args.research else ''}   (Ctrl-C=중단)")

    if args.research:
        from manager import ResearchManager
        mgr = ResearchManager(memory_path=raw.get("memory_path", "memory.json"))
        store = mgr.run(cfg, out_path=args.out, reporter=make_reporter(), control=control)
        print()
        mgr.print_report(store)
    else:
        run_search(cfg, out_path=args.out, verbose=False,
                   reporter=make_reporter(), control=control)
        print()


if __name__ == "__main__":
    main()
