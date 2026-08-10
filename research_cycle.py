"""
research_cycle.py — 연구 한 바퀴를 돌리는 CLI. 이 저장소의 새 주 진입점.

## 한 바퀴의 구조

    [1] 로컬 대량 계산        후보 생성 → om_core 로 검증 → 불변량 부착 (코퍼스)
    [2] 로컬 결정론적 채굴    코퍼스에서 반증 가능한 명제 자동 추출
    [3] 로컬 반증 공격        각 명제를 실제로 깨뜨리려 시도 (전수 가능하면 전수)
    [4] 프롬프트 생성         살아남은 것 + 반례 + 표본을 한 파일로 묶는다
    ---- 여기서 사람이 개입: 그 파일을 고급 모델 대화창에 붙여넣고 답을 저장 ----
    [5] 응답 흡수             새 불변량 등록(심사 후) · LLM 추측을 즉시 반증 공격
    [6] 기록                  실험 폴더 + research_log.md 에 영구 보존

비싼 자원(고급 모델 추론)은 한 바퀴에 **한 번** 쓰이고, 그 사이 로컬 CPU 가
수천~수만 개의 후보를 훑는다. API 키는 어디에서도 필요하지 않다.

## 명령

    python research_cycle.py run     --d 2 --n 6            # [1]~[4]
    python research_cycle.py ingest  --run 0001             # [5][6]
    python research_cycle.py stage   explore --run 0001     # 3단계 프롬프트
    python research_cycle.py status                         # 실험 목록
    python research_cycle.py vocab                          # 현재 불변량 어휘

## 각 산출물이 무슨 뜻인가 (소프트웨어 용어 → 연구 용어)

  experiments/run_0001/corpus.json
      이번에 실제로 계산한 모든 대상과 그 불변량 값. 나중에 다시 계산하지 않고
      같은 데이터에 새 질문을 던질 수 있다.
  experiments/run_0001/conjectures.json
      기계가 다시 검사할 수 있는 형태의 명제 목록. 사람의 메모가 아니다.
  experiments/run_0001/manifest.json
      어떤 git 커밋의 코드로, 어떤 설정으로 돌렸는지. 반년 뒤 재현하기 위한 것.
  prompts/0001-analyze.md / responses/0001-analyze.md
      고급 모델과 주고받은 내용. 대화창을 옮겨 다녀도 기록이 남는다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict

from console import enable_utf8_stdout
from om_core import Chirotope, mcmullen_evaluate
import invariants as INV
import conjecture as CJ
import falsify as FL
import reasoner as RS

ROOT = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS_DIR = os.path.join(ROOT, "experiments")
KNOWLEDGE_DIR = os.path.join(ROOT, "knowledge")
LOG_PATH = os.path.join(ROOT, "research_log.md")


# ═══════════════════════════ 유틸 ═══════════════════════════
def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:                        # noqa: BLE001
        return "unknown"


def git_dirty() -> bool:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        return bool(out.stdout.strip())
    except Exception:                        # noqa: BLE001
        return True


def next_run_id() -> str:
    os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
    used = [int(d[4:]) for d in os.listdir(EXPERIMENTS_DIR)
            if d.startswith("run_") and d[4:].isdigit()]
    return f"{(max(used) + 1) if used else 1:04d}"


def run_dir(run_id: str) -> str:
    return os.path.join(EXPERIMENTS_DIR, f"run_{run_id}")


def _write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _write_json(path: str, obj):
    _write(path, json.dumps(obj, ensure_ascii=False, indent=1, default=str))


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def append_log(line: str):
    if not os.path.exists(LOG_PATH):
        _write(LOG_PATH, "# research_log.md — 연구 기록 (append-only)\n\n"
                         "실험 한 줄 = 한 라운드. 실패한 시도도 반드시 남긴다 "
                         "(같은 막다른 길을 다시 걷지 않기 위해).\n\n")
    with open(LOG_PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(line.rstrip() + "\n")


# ═══════════════════════════ 후보 생성 ═══════════════════════════
def generate_candidates(n: int, r: int, *, om_class: str, budget: int,
                        node_budget: int, seed: int) -> tuple[list, dict]:
    """(후보 목록, scope 메타). scope 에 **실현가능성 상태**를 반드시 기록한다."""
    from generator import generate_backtracking, generate_random_realizable
    stats: dict = {}
    if om_class == "realizable_uniform":
        chs = list(generate_random_realizable(n, r, dedup=False,
                                              max_candidates=budget, seed=seed))
        meta = {"backend": "random", "exhaustive": False,
                "realizability": "REALIZABLE",
                "how": f"generate_random_realizable(n={n},r={r},seed={seed},max={budget})",
                "realizability_note":
                    "무작위 정수 점배치에서 만든 것이므로 전부 실현가능하다. "
                    "다만 실현가능한 OM 전체의 열거가 아니라 표본이다."}
    else:
        chs = list(generate_backtracking(n, r, dedup=False, max_candidates=budget,
                                         max_nodes=node_budget, stats=stats))
        meta = {"backend": "backtracking", "exhaustive": bool(stats.get("exhausted")),
                "realizability": "UNKNOWN",
                "how": f"generate_backtracking(n={n},r={r},max={budget})",
                "generator_stats": stats,
                "realizability_note":
                    "GP 공리만 만족하는 추상 OM 이라 실현가능성은 알 수 없다. "
                    "비실현 witness 는 OM 판본의 상한만 말할 뿐 ν(d) 에 대해서는 "
                    "아무것도 증명하지 않는다."}
    meta.update({"n": n, "r": r, "d": r - 1, "om_class": om_class, "seed": seed})
    return chs, meta


def pick_examples(corpus: CJ.Corpus, *, k: int = 6) -> tuple[list, list]:
    """프롬프트용 구조 다양성 표본과 non-witness 근접 실패를 고른다.

    exact canonical_form은 n!·2^(n-1)이라 표본 선택에 과도하다. 이미 계산된 궤도
    불변 feature 지문으로 다양성을 확보하고, 이것을 동형류의 증명으로 사용하지 않는다.
    """
    orbit_names = [
        name for name, inv in INV.REGISTRY.items()
        if inv.status == "active" and inv.relabel_invariant is True
        and inv.reorient_invariant is True and not inv.defines_label
    ]

    def diverse(items):
        selected, seen = [], set()
        for item in items:
            fingerprint = tuple(
                (name, json.dumps(item.features.get(name), ensure_ascii=False,
                                  sort_keys=True, default=str))
                for name in orbit_names
            )
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            selected.append(item)
            if len(selected) >= k:
                return selected
        if len(selected) < k:
            selected_ids = {item.id for item in selected}
            remaining = [item for item in items if item.id not in selected_ids]
            selected.extend(remaining[:k - len(selected)])
        return selected

    reps = diverse(corpus.witnesses)
    w_out = [{"id": it.id, "encoded": RS.encode_chirotope(Chirotope.from_dict(it.chirotope)),
              "features": it.features} for it in reps]

    nons = sorted(corpus.nonwitnesses,
                  key=lambda it: it.features.get("num_convex_reorientations", 10**9))
    nons = diverse(nons)
    n_out = [{"id": it.id, "encoded": RS.encode_chirotope(Chirotope.from_dict(it.chirotope)),
              "features": it.features} for it in nons]
    return w_out, n_out


def history_digest(limit: int = 40) -> str:
    if not os.path.exists(LOG_PATH):
        return ""
    lines = [ln for ln in _read(LOG_PATH).splitlines() if ln.startswith("- ")]
    return "\n".join(lines[-limit:])


# ═══════════════════════════ 명령: run ═══════════════════════════
def cmd_run(args) -> int:
    t0 = time.time()
    r = args.r if args.r else args.d + 1
    n = args.n if args.n else 2 * (r - 1) + 2
    run_id = args.run or next_run_id()
    rd = run_dir(run_id)
    os.makedirs(rd, exist_ok=True)

    max_cost = "expensive" if args.expensive else "moderate"
    INV.load_vocabulary(corpus=None, revet=False)
    names = INV.active_names(max_cost=max_cost)

    print(f"[run {run_id}] n={n} r={r} (d={r-1}) class={args.om_class} "
          f"예산={args.budget} 어휘={len(names)}개")

    # [1] 생성 + 검증 + 불변량
    chs, scope = generate_candidates(n, r, om_class=args.om_class,
                                     budget=args.budget,
                                     node_budget=args.node_budget, seed=args.seed)
    print(f"  후보 {len(chs)}개 생성 (exhaustive={scope['exhaustive']}, "
          f"realizability={scope['realizability']})")
    if not chs:
        print("  후보가 0개 — n/r/예산을 확인하세요.")
        return 1

    corpus = CJ.build_corpus(chs, scope, feature_names=names)
    s = corpus.summary()
    print(f"  코퍼스: witness {s['witness']} / non-witness {s['nonwitness']}")
    # 신뢰 앵커 재확인: 코퍼스 라벨이 om_core 와 일치하는지 표본 검사
    check = corpus.items[:: max(1, len(corpus.items) // 20)][:20]
    for it in check:
        assert it.label == mcmullen_evaluate(Chirotope.from_dict(it.chirotope))["witness"], \
            "코퍼스 라벨이 om_core 와 불일치 — 즉시 중단"
    print(f"  라벨 <-> om_core 표본 재확인 OK ({len(check)}건)")

    # [2] 채굴
    cjs = CJ.mine(corpus, min_support=args.min_support,
                  max_conjectures=args.max_conjectures)
    print(f"  추측 채굴 {len(cjs)}건")

    # [3] 반증 공격
    extensions = _parse_extensions(args.extend, n, r)
    def _prog(i, total, cj):
        print(f"    반증 {i+1}/{total}: {cj.text()[:70]}", flush=True)
    reps = FL.falsify_all(cjs, top=args.falsify_top, progress=_prog,
                          budget=args.falsify_budget, node_budget=args.node_budget,
                          extensions=extensions,
                          extension_budget=args.extension_budget)
    n_ref = sum(1 for c in cjs if c.status == FL.REFUTED)
    n_exh = sum(1 for c in cjs if c.status == CJ.EXHAUSTED_ON_SCOPE)
    print(f"  반증 결과: 반증 {n_ref} / 범위내 전수확인 {n_exh} / "
          f"생존 {len(FL.surviving(cjs))}")

    # [4] 산출물 + 프롬프트
    conj_md = CJ.report_markdown(corpus, cjs)
    fals_md = FL.report_markdown(cjs, reps)
    w_ex, n_ex = pick_examples(corpus, k=args.examples)

    prompt = RS.build_analyze_prompt(
        corpus_summary={**s, "realizability": scope["realizability"],
                        "realizability_note": scope["realizability_note"]},
        vocabulary=INV.vocabulary_summary(),
        conjecture_report=conj_md, falsify_report=fals_md,
        witness_examples=w_ex, nearmiss_examples=n_ex,
        history=history_digest(), extra=args.extra or "")

    fr = RS.FileReasoner(ROOT)
    answer = fr.ask("analyze", prompt, meta={"seq": int(run_id)})

    manifest = {
        "run_id": run_id, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": git_commit(), "git_dirty": git_dirty(),
        "python": sys.version.split()[0],
        "config": {k: v for k, v in vars(args).items() if k != "func"},
        "scope": scope, "corpus_summary": s,
        "vocabulary": [v["name"] for v in INV.vocabulary_summary()
                       if v["status"] == "active"],
        "counts": {"conjectures": len(cjs), "refuted": n_ref,
                   "exhausted_on_scope": n_exh,
                   "surviving": len(FL.surviving(cjs))},
        "elapsed_s": round(time.time() - t0, 2),
        "stage": "awaiting_response" if answer is None else "response_present",
    }
    _write_json(os.path.join(rd, "manifest.json"), manifest)
    corpus.save(os.path.join(rd, "corpus.json"))
    _write_json(os.path.join(rd, "conjectures.json"), [c.as_dict() for c in cjs])
    _write_json(os.path.join(rd, "falsification.json"), [r_.as_dict() for r_ in reps])
    _write(os.path.join(rd, "report.md"),
           f"# run_{run_id} 보고서\n\n"
           f"- 범위: `{json.dumps(scope, ensure_ascii=False, default=str)}`\n"
           f"- 실현가능성: **{scope['realizability']}** — {scope['realizability_note']}\n\n"
           + conj_md + "\n\n" + fals_md)
    _write(os.path.join(rd, "prompt.md"), prompt)
    if not os.path.exists(os.path.join(rd, "hypothesis.md")):
        _write(os.path.join(rd, "hypothesis.md"),
               f"# run_{run_id} 가설\n\n"
               f"(이 파일은 사람이 채웁니다 — 이번 라운드에서 무엇을 알아내려 했는지.)\n\n"
               f"- 범위: n={n}, r={r} (d={r-1}), class={args.om_class}\n"
               f"- 자동 생성 시각: {manifest['created_at']}\n")

    append_log(f"- `run_{run_id}` n={n} r={r} class={args.om_class} "
               f"실현가능성={scope['realizability']} | 후보 {len(chs)} "
               f"(witness {s['witness']}) | 추측 {len(cjs)} → 반증 {n_ref}, "
               f"전수확인 {n_exh} | commit {manifest['git_commit'][:8]}")

    print(f"\n  산출물: {rd}")
    if answer is None:
        p = fr.pending[-1]
        print("\n" + p.instruction())
        print(f"\n  응답을 저장한 뒤:  python research_cycle.py ingest --run {run_id}")
    else:
        print(f"\n  응답이 이미 있습니다. 흡수하려면: "
              f"python research_cycle.py ingest --run {run_id}")
    return 0


def _parse_extensions(spec: str | None, n: int, r: int) -> list[tuple[int, int]]:
    """--extend "7,3 8,4" → [(7,3),(8,4)]. 생략하면 n+1 을 같은 rank 로 시험."""
    if spec is None:
        return [(n + 1, r)]
    if spec.strip() in ("", "none"):
        return []
    out = []
    for tok in spec.replace(";", " ").split():
        a, b = tok.split(",")
        out.append((int(a), int(b)))
    return out


# ═══════════════════════════ 명령: ingest ═══════════════════════════
def cmd_ingest(args) -> int:
    run_id = args.run
    rd = run_dir(run_id)
    if not os.path.isdir(rd):
        print(f"실험 폴더가 없습니다: {rd}")
        return 1
    manifest = json.loads(_read(os.path.join(rd, "manifest.json")))
    corpus = CJ.Corpus.load(os.path.join(rd, "corpus.json"))

    fr = RS.FileReasoner(ROOT)
    _, rpath = fr._paths("analyze", int(run_id))
    if not os.path.exists(rpath):
        print(f"응답 파일이 없습니다: {rpath}\n"
              f"프롬프트({os.path.join(rd, 'prompt.md')})를 모델에 넣고 답을 저장하세요.")
        return 1
    raw = _read(rpath)
    data = RS.extract_json(raw)
    if not data:
        print("응답에서 JSON 블록을 찾지 못했습니다. ```json 펜스로 감싼 블록이 필요합니다.")
        return 1

    corpus_chs = [Chirotope.from_dict(it.chirotope) for it in corpus.items]
    vet_corpus = corpus_chs[:args.vet_samples]
    result = {"run_id": run_id, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
              "analysis": data.get("analysis", ""),
              "invariants": [], "deprecated": [], "conjectures": [],
              "candidate_chirotopes": [], "next_experiment": data.get("next_experiment"),
              "assessment": data.get("assessment", {}),
              "open_questions": data.get("open_questions", [])}

    # ── (a) 새 불변량: 샌드박스 + 심사 통과분만 어휘에 들어간다 ──
    for spec in data.get("new_invariants", []) or []:
        name = str(spec.get("name", "")).strip()
        inv, rep = INV.register_llm_invariant(
            name, spec.get("code", ""), spec.get("description", ""),
            vet_corpus, origin=f"run_{run_id}", persist=True)
        entry = {"name": name, "accepted": inv is not None,
                 "vet": rep.as_dict(), "why": spec.get("why", "")}
        result["invariants"].append(entry)
        mark = "채택" if inv else "거부"
        extra = ""
        if inv:
            extra = (f" [재명명불변={rep.relabel_invariant} "
                     f"재배향불변={rep.reorient_invariant} 비용={inv.cost}]")
        print(f"  불변량 {mark}: {name}{extra}"
              + ("" if inv else f" — {'; '.join(rep.reasons)}"))

    # ── (b) 폐기 요청 (삭제가 아니라 기록을 남기는 폐기) ──
    for spec in data.get("deprecate_invariants", []) or []:
        name = str(spec.get("name", "")).strip()
        try:
            INV.deprecate(name, spec.get("reason", "(사유 없음)"))
            result["deprecated"].append({"name": name, "ok": True,
                                         "reason": spec.get("reason", "")})
            print(f"  불변량 폐기: {name}")
        except INV.VocabularyError as e:
            result["deprecated"].append({"name": name, "ok": False, "error": str(e)})
            print(f"  불변량 폐기 거부: {name} — {e}")

    # ── (c) LLM 이 제안한 추측 → 즉시 반증 공격 ──
    llm_cjs: list[CJ.Conjecture] = []
    for i, spec in enumerate(data.get("conjectures", []) or []):
        try:
            cj = CJ.Conjecture(
                id=f"cj-llm-{run_id}-{i:02d}", form="llm_proposed",
                antecedent=[CJ.Atom.from_dict(a) for a in spec.get("antecedent", [])],
                consequent=CJ.Atom.from_dict(spec["consequent"]),
                scope=spec.get("scope") or {"n": corpus.scope["n"],
                                            "r": corpus.scope["r"]},
                support={"source": "llm", "grade_claimed": spec.get("grade", "")},
                invariance=CJ._invariance_of(
                    [CJ.Atom.from_dict(a) for a in spec.get("antecedent", [])]
                    + [CJ.Atom.from_dict(spec["consequent"])]),
                notes=[spec.get("statement", ""), spec.get("rationale", "")])
        except Exception as e:                # noqa: BLE001
            result["conjectures"].append({"index": i, "accepted": False,
                                          "error": f"형식 오류: {e}"})
            print(f"  추측 {i} 형식 오류: {e}")
            continue
        unknown = [a.inv for a in cj.antecedent + [cj.consequent]
                   if a.inv not in INV.REGISTRY]
        if unknown:
            result["conjectures"].append({"index": i, "accepted": False,
                                          "error": f"모르는 불변량 {unknown}"})
            print(f"  추측 {i} 거부: 모르는 불변량 {unknown}")
            continue
        llm_cjs.append(cj)

    if llm_cjs:
        print(f"  LLM 추측 {len(llm_cjs)}건 반증 공격 중...")
        reps = FL.falsify_all(llm_cjs, budget=args.falsify_budget,
                              node_budget=args.node_budget,
                              extensions=_parse_extensions(args.extend,
                                                           int(corpus.scope["n"]),
                                                           int(corpus.scope["r"])),
                              extension_budget=args.extension_budget)
        for cj, rp in zip(llm_cjs, reps):
            result["conjectures"].append({"accepted": True, "conjecture": cj.as_dict(),
                                          "falsification": rp.as_dict()})
            print(f"    {cj.id}: {cj.status} — {cj.text()[:70]}")

    # ── (d) LLM 이 제안한 구체적 chirotope → om_core 로 즉시 판정 ──
    for i, spec in enumerate(data.get("candidate_chirotopes", []) or []):
        try:
            ch = RS.decode_chirotope(spec)
        except Exception as e:                # noqa: BLE001
            result["candidate_chirotopes"].append({"index": i, "ok": False,
                                                   "error": str(e)})
            print(f"  후보 {i} 해독 실패: {e}")
            continue
        valid = ch.is_valid()
        ev = mcmullen_evaluate(ch) if valid else None
        entry = {"index": i, "ok": True, "valid_gp": valid,
                 "why": spec.get("why", ""),
                 "evaluation": ev,
                 "realizability": "UNKNOWN",
                 "note": ("GP 공리 위반 — 유향 매트로이드가 아님" if not valid else
                          "실현가능성은 판정하지 않았다. 비실현이면 ν(d) 상한에 대해 "
                          "아무것도 증명하지 않는다.")}
        result["candidate_chirotopes"].append(entry)
        if not valid:
            print(f"  후보 {i}: GP 위반 (OM 아님)")
        else:
            print(f"  후보 {i}: valid, witness={ev['witness']}, "
                  f"n={ch.n} → 상한 {ev.get('implied_upper_bound', '—')}")

    _write_json(os.path.join(rd, "ingest.json"), result)
    _write(os.path.join(rd, "response.md"), raw)
    manifest["stage"] = "ingested"
    manifest["ingested_at"] = result["at"]
    _write_json(os.path.join(rd, "manifest.json"), manifest)

    n_inv = sum(1 for e in result["invariants"] if e["accepted"])
    n_cj_ref = sum(1 for e in result["conjectures"]
                   if e.get("accepted") and
                   e["conjecture"]["status"] == FL.REFUTED)
    n_wit = sum(1 for e in result["candidate_chirotopes"]
                if e.get("evaluation") and e["evaluation"].get("witness"))
    append_log(f"  - `run_{run_id}` 흡수: 새 불변량 {n_inv}개 채택 "
               f"/ LLM 추측 {len(llm_cjs)}건 중 {n_cj_ref}건 반증 "
               f"/ 제안 구성 중 witness {n_wit}건")
    print(f"\n  흡수 완료 → {os.path.join(rd, 'ingest.json')}")
    nx = result.get("next_experiment") or {}
    if nx:
        print(f"  모델이 제안한 다음 실험: n={nx.get('n')} r={nx.get('r')} "
              f"class={nx.get('om_class')} — {nx.get('why','')[:120]}")
    return 0


# ═══════════════════════════ 명령: stage / status / vocab ═══════════════════════════
def cmd_stage(args) -> int:
    rd = run_dir(args.run) if args.run else None
    context = ""
    if rd and os.path.exists(os.path.join(rd, "report.md")):
        context = _read(os.path.join(rd, "report.md"))
    prompt = RS.build_stage_prompt(args.stage, context=context or "(맥락 없음)",
                                   question=args.question or "")
    fr = RS.FileReasoner(ROOT)
    seq = int(args.run) if args.run else None
    ans = fr.ask(args.stage, prompt, meta={"seq": seq} if seq else None)
    if ans is None:
        print(fr.pending[-1].instruction())
    else:
        print(f"응답이 이미 존재합니다 ({len(ans)}자).")
    return 0


def cmd_status(args) -> int:
    if not os.path.isdir(EXPERIMENTS_DIR):
        print("아직 실험이 없습니다. `python research_cycle.py run --d 2 --n 6` 로 시작하세요.")
        return 0
    rows = []
    for d in sorted(os.listdir(EXPERIMENTS_DIR)):
        mp = os.path.join(EXPERIMENTS_DIR, d, "manifest.json")
        if not os.path.exists(mp):
            continue
        m = json.loads(_read(mp))
        sc, c = m.get("scope", {}), m.get("counts", {})
        rows.append(f"  {d}  n={sc.get('n')} r={sc.get('r')} "
                    f"{sc.get('om_class','?'):18} {sc.get('realizability','?'):10} "
                    f"추측 {c.get('conjectures',0):3} 반증 {c.get('refuted',0):3} "
                    f"전수확인 {c.get('exhausted_on_scope',0):3}  [{m.get('stage','?')}]")
    print(f"실험 {len(rows)}건:")
    print("\n".join(rows) if rows else "  (없음)")
    return 0


def cmd_vocab(args) -> int:
    INV.load_vocabulary(corpus=None, revet=False)
    if args.deprecate:
        try:
            INV.deprecate(args.deprecate, args.reason or "(사람이 직접 폐기)",
                          origin="cli")
            print(f"폐기: {args.deprecate}")
        except INV.VocabularyError as e:
            print(f"폐기 거부: {e}")
            return 1
    if args.reinstate:
        try:
            INV.reinstate(args.reinstate)
            print(f"복원: {args.reinstate}")
        except INV.VocabularyError as e:
            print(f"복원 거부: {e}")
            return 1
    rows = INV.vocabulary_summary()
    act = [r for r in rows if r["status"] == "active"]
    print(f"불변량 어휘 {len(act)}개 (활성) / 전체 {len(rows)}개\n")
    print(f"  {'이름':32} {'종류':6} {'출처':8} {'비용':10} 재명명 재배향")
    for r in rows:
        if args.all or r["status"] == "active":
            print(f"  {r['name']:32} {r['kind']:6} {r['source']:8} "
                  f"{r.get('cost','?'):10} "
                  f"{RS._yn(r['relabel_invariant']):^6} "
                  f"{RS._yn(r['reorient_invariant']):^6}"
                  + ("" if r["status"] == "active" else "  [폐기]"))
    return 0


# ═══════════════════════════ CLI ═══════════════════════════
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="research_cycle",
        description="McMullen 연구 루프: 로컬 대량계산 → 명제 채굴 → 반증 → 고급모델 분석")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="[1]~[4] 코퍼스·채굴·반증·프롬프트 생성")
    p.add_argument("--d", type=int, default=2, help="차원 d (rank = d+1)")
    p.add_argument("--r", type=int, default=None, help="rank 직접 지정")
    p.add_argument("--n", type=int, default=None, help="원소 수 (생략 시 2d+2)")
    p.add_argument("--om-class", dest="om_class", default="uniform",
                   choices=["uniform", "realizable_uniform"],
                   help="uniform=추상 OM(실현가능성 불명) / realizable_uniform=실현가능 표본")
    p.add_argument("--budget", type=int, default=1500, help="코퍼스 후보 수 상한")
    p.add_argument("--node-budget", dest="node_budget", type=int, default=20_000_000)
    p.add_argument("--seed", type=int, default=20260809)
    p.add_argument("--min-support", dest="min_support", type=int, default=3)
    p.add_argument("--max-conjectures", dest="max_conjectures", type=int, default=40)
    p.add_argument("--falsify-top", dest="falsify_top", type=int, default=12)
    p.add_argument("--falsify-budget", dest="falsify_budget", type=int, default=20000,
                   help="반증 시 검사할 후보 수 상한. (5,3)=192 (6,4)=1920 (6,3)=11904 "
                        "이므로 이 값이 그보다 크면 그 범위는 전수 확인이 된다")
    p.add_argument("--extension-budget", dest="extension_budget", type=int, default=3000)
    p.add_argument("--extend", default=None,
                   help='확장 시험 범위 "7,3 8,4" (기본: n+1 같은 rank / "none" 이면 생략)')
    p.add_argument("--examples", type=int, default=6, help="프롬프트에 넣을 표본 수")
    p.add_argument("--expensive", action="store_true",
                   help="비싼 불변량(automorphism_order 등)도 포함")
    p.add_argument("--extra", default=None, help="프롬프트에 덧붙일 추가 지시")
    p.add_argument("--run", default=None, help="실험 id 직접 지정 (기본: 자동 증가)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("ingest", help="[5][6] 모델 응답 흡수 + 즉시 반증 + 기록")
    p.add_argument("--run", required=True)
    p.add_argument("--vet-samples", dest="vet_samples", type=int, default=40,
                   help="새 불변량 심사에 쓸 코퍼스 표본 수")
    p.add_argument("--falsify-budget", dest="falsify_budget", type=int, default=20000)
    p.add_argument("--node-budget", dest="node_budget", type=int, default=20_000_000)
    p.add_argument("--extension-budget", dest="extension_budget", type=int, default=3000)
    p.add_argument("--extend", default=None)
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("stage", help="Explore/Construct/Critique 프롬프트 생성")
    p.add_argument("stage", choices=["explore", "construct", "critique"])
    p.add_argument("--run", default=None, help="맥락으로 쓸 실험 id")
    p.add_argument("--question", default=None)
    p.set_defaults(func=cmd_stage)

    p = sub.add_parser("status", help="실험 목록")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("vocab", help="현재 불변량 어휘 (조회/폐기/복원)")
    p.add_argument("--all", action="store_true", help="폐기된 것도 표시")
    p.add_argument("--deprecate", default=None, metavar="NAME",
                   help="어휘에서 제외 (삭제 아님 — 기록과 코드는 남는다)")
    p.add_argument("--reinstate", default=None, metavar="NAME", help="폐기 취소")
    p.add_argument("--reason", default=None, help="--deprecate 의 사유")
    p.set_defaults(func=cmd_vocab)
    return ap


def main(argv=None) -> int:
    enable_utf8_stdout()
    args = build_parser().parse_args(argv)
    return args.func(args)


# ═══════════════════════════ 자체 통합 테스트 ═══════════════════════════
def _selftest() -> None:
    """run → (모의 응답) → ingest 전 과정을 예약 id `9999` 로 실제 실행하고 지운다.
    LLM 없이 돌아가며(ScriptedReasoner 대신 파일에 직접 응답을 써 넣는다),
    파이프라인이 잘못된 제안을 실제로 거부하는지까지 확인한다."""
    import shutil

    rid = "9999"
    rd = run_dir(rid)
    fr = RS.FileReasoner(ROOT)
    ppath, rpath = fr._paths("analyze", int(rid))
    for pth in (rd, ppath, rpath):
        if os.path.isdir(pth):
            shutil.rmtree(pth)
        elif os.path.exists(pth):
            os.remove(pth)

    try:
        # ── [1]~[4]: (5,3) 은 전체가 192개라 전수 소진이 보장된다 ──
        rc = main(["run", "--d", "2", "--n", "5", "--run", rid, "--budget", "300",
                   "--falsify-top", "5", "--falsify-budget", "500",
                   "--extend", "none"])
        assert rc == 0
        manifest = json.loads(_read(os.path.join(rd, "manifest.json")))
        assert manifest["scope"]["exhaustive"] is True, "(5,3) 이 전수로 잡히지 않음"
        assert manifest["scope"]["realizability"] == "UNKNOWN"
        assert manifest["stage"] == "awaiting_response"
        assert manifest["git_commit"] != "" and "corpus_summary" in manifest
        corpus = CJ.Corpus.load(os.path.join(rd, "corpus.json"))
        # (5,3) 에는 witness 가 없다 — 저장소의 기존 실측(CEGIS EXHAUSTED)과 일치해야 한다
        assert len(corpus.witnesses) == 0, "(5,3) 에서 witness 가 나옴 — 신뢰 앵커 이상"
        assert os.path.exists(ppath) and "```json" in _read(ppath)
        print("  [1]~[4] OK — (5,3) 전수, witness 0 (기존 실측과 일치)")

        # ── [5]: 모의 응답으로 흡수 경로 전체를 시험 ──
        payload = {
            "analysis": "테스트",
            "new_invariants": [
                {"name": "st_num_neg_signs", "description": "부호가 −인 기저 수",
                 "code": "def f(ch):\n    return sum(1 for v in ch.signs.values() if v < 0)\n",
                 "why": "가장 단순한 비자명 양"},
                {"name": "st_evil", "description": "샌드박스 위반",
                 "code": "def f(ch):\n    return open('x')\n", "why": "거부되어야 함"},
                {"name": "st_const", "description": "상수",
                 "code": "def f(ch):\n    return 1\n", "why": "거부되어야 함"},
            ],
            "deprecate_invariants": [{"name": "witness", "reason": "라벨 제거 시도"}],
            "conjectures": [
                {"antecedent": [{"inv": "num_positive_circuits", "op": "==", "value": 0}],
                 "consequent": {"inv": "acyclic", "op": "==", "value": True},
                 "scope": {"n": 5, "r": 3}, "statement": "정의상 참",
                 "grade": "PROVEN", "rationale": "정의 전개"},
                {"antecedent": [], "consequent": {"inv": "acyclic", "op": "==", "value": True},
                 "scope": {"n": 5, "r": 3}, "statement": "모두 acyclic (거짓)",
                 "grade": "CONJECTURE", "rationale": "반증되어야 함"},
                {"antecedent": [], "consequent": {"inv": "no_such_inv", "op": "==", "value": 1},
                 "scope": {"n": 5, "r": 3}, "statement": "모르는 불변량"},
            ],
            "candidate_chirotopes": [
                {"n": 5, "r": 3, "signs": "+" * 10, "why": "교대 OM — valid, witness 아님"},
                {"n": 5, "r": 3, "signs": "+" * 9, "why": "길이 틀림 — 거부되어야 함"},
            ],
            "next_experiment": {"n": 6, "r": 3, "om_class": "uniform", "why": "다음 단계"},
        }
        _write(rpath, "산문 분석\n\n```json\n"
               + json.dumps(payload, ensure_ascii=False) + "\n```\n")
        rc = main(["ingest", "--run", rid, "--falsify-budget", "500",
                   "--extend", "none"])
        assert rc == 0
        ing = json.loads(_read(os.path.join(rd, "ingest.json")))

        by_name = {e["name"]: e for e in ing["invariants"]}
        assert by_name["st_num_neg_signs"]["accepted"] is True
        assert by_name["st_evil"]["accepted"] is False
        assert any("샌드박스" in r for r in by_name["st_evil"]["vet"]["reasons"])
        assert by_name["st_const"]["accepted"] is False
        assert any("상수" in r for r in by_name["st_const"]["vet"]["reasons"])
        assert ing["deprecated"][0]["ok"] is False       # 라벨은 폐기 불가
        print("  [5] 어휘: 정상 채택 / 샌드박스 위반 거부 / 상수 거부 / 라벨 보호 OK")

        accepted = [e for e in ing["conjectures"] if e.get("accepted")]
        rejected = [e for e in ing["conjectures"] if not e.get("accepted")]
        assert len(accepted) == 2 and len(rejected) == 1
        assert "모르는 불변량" in rejected[0]["error"]
        st = {e["conjecture"]["status"] for e in accepted}
        assert st == {CJ.EXHAUSTED_ON_SCOPE, FL.REFUTED}, st
        ref = next(e for e in accepted
                   if e["conjecture"]["status"] == FL.REFUTED)
        ce = ref["falsification"]["in_scope"]["counterexample"]
        assert ce is not None, "반증인데 반례 객체가 없음"
        # 반례를 om_core 로 독립 재확인 — 파이프라인이 스스로를 믿지 않는다
        ch_ce = Chirotope.from_dict(ce["chirotope"])
        assert ch_ce.is_valid() and ch_ce.is_acyclic() is False
        print("  [5] LLM 추측: 참=전수확인 / 거짓=반증(반례 om_core 재확인) / 미등록=거부 OK")

        cands = ing["candidate_chirotopes"]
        assert cands[0]["ok"] and cands[0]["valid_gp"] is True
        assert cands[0]["evaluation"]["witness"] is False     # 교대 OM 은 convex
        assert cands[1]["ok"] is False                        # 길이 불일치
        assert cands[0]["realizability"] == "UNKNOWN"
        print("  [5] 제안 구성: om_core 판정 + 실현가능성 미확정 명시 OK")

        assert os.path.exists(LOG_PATH)
        log = _read(LOG_PATH)
        assert f"run_{rid}" in log and "흡수" in log
        m2 = json.loads(_read(os.path.join(rd, "manifest.json")))
        assert m2["stage"] == "ingested"
        print("  [6] research_log.md + manifest 갱신 OK")

    finally:
        for pth in (rd, ppath, rpath):
            if os.path.isdir(pth):
                shutil.rmtree(pth, ignore_errors=True)
            elif os.path.exists(pth):
                os.remove(pth)
        for nm in ("st_num_neg_signs",):
            INV.REGISTRY.pop(nm, None)
            f = os.path.join(INV.VOCAB_DIR, f"{nm}.json")
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(LOG_PATH):
            keep = [ln for ln in _read(LOG_PATH).splitlines()
                    if f"run_{rid}" not in ln]
            _write(LOG_PATH, "\n".join(keep) + "\n")

    print("research_cycle core-contract assertions OK")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        enable_utf8_stdout()
        _selftest()
        raise SystemExit(0)
    raise SystemExit(main())
