# docs/REFACTOR_BACKLOG.md — 정리 작업 지시서 (Codex 용)

Codex 가 이 문서만 읽고 작업할 수 있게 쓴 지시서다. **근거 없이 지우지 말라** — 각 항목에
왜 무용한지와 무엇을 잃는지 적어뒀다. 판단이 갈리면 §0 을 따르고, 그래도 애매하면 남긴다.

## 0. 절대 건드리지 말 것 (신뢰 앵커)

| 파일 | 이유 |
|---|---|
| `om_core.py` | **유일한 수학적 판정자.** 어떤 최적화·중복제거도 여기선 금지 |
| `certificate_verify.py` | coverage 로직을 **일부러** 공유하지 않는 독립 검증기. "중복"으로 보이는 것이 신뢰 근거 자체다. `reorientation_cover`/`search`/`generator`/`theorist` import 금지 |
| `reorientation_cover.py` | 위와 독립 이중 경로. 둘을 합치는 리팩터링 금지 |
| `theorist.py` 의 `counterexample_hunter` / `proof_checker` | 결정론적 적대자. LLM 호출로 대체 금지 |
| `insight_ledger.py` | append-only + hash chain. 과거 레코드 재작성 금지 |
| `scripts/sync_exec.py` | 저장소 운영 규약(DECISIONS 0032)을 강제하는 코드 |

각 모듈의 `if __name__ == "__main__":` 자체 테스트는 **삭제·약화 금지**. 이 저장소에는
별도 테스트 프레임워크가 없고 그게 CI 의 전부다.

---

## 1. 삭제 후보 — 근거와 잃는 것

### 1-A. 실측으로 폐기된 탐색 경로

| 파일 | 근거 | 권고 |
|---|---|---|
| `climb.py` (15KB) | 좌표공간 국소탐색. **realization chamber 내부에서 f 가 상수**라 원리상 gradient 가 없음이 확정됨(DECISIONS 0035, STATE §3). 190만 회 평가 0건이 이걸로 설명된다. 후속은 `layer_search.py` | `attic/` 로 이동. 삭제까지는 불필요 — 코드가 아니라 **왜 실패했는지가 자산**이고 그건 research_log 에 남아 있다 |
| `sweep.py` (12KB) | 무작위 정수 box 표집. (10,5) 153,379 표본 witness 0 으로 경로 폐기 | 위와 동일 |

**잃는 것**: 없음. 두 모듈의 산출물 중 가치 있는 것(`nearmiss_d4.json`, `nearmiss_d5.json`)은
이미 별도 파일로 분리돼 있고 `mutation_lab`/`layer_search` 가 그걸 읽는다.

### 1-B. 일회성 스크립트 (임무 완료)

| 파일 | 근거 | 권고 |
|---|---|---|
| `feasibility_probe.py` + `feasibility_probe.json` | d=5 착수 전 비용 실측용 일회성 진단. 결과는 research_log `probe` 줄과 `prompts/0001-d5project.md` §1 표에 흡수됨 | 삭제 가능 |
| `d5_project.py` (23KB) | d=5 프롬프트 생성 + 응답 흡수 전용 진입점. 그 왕복은 `prompts/0001-d5project.md` · `responses/0001-d5project.md` 로 **원문 보존이 끝났고**, 자문 채널은 `questions/` 로 대체됨 | `attic/` 이동. 재사용할 로직(근접실패 도시에 직렬화)이 있으면 `nearmiss.py` 로 흡수 후 삭제 |

### 1-C. 런타임 찌꺼기 (연구 기록 아님)

| 파일 | 근거 |
|---|---|
| `results_llm_test.json` (105KB) | LLM 실험 임시 출력. 어떤 모듈도 읽지 않음 |
| `memory_llm_test.json` | 위와 동일 |
| `memory.json` | 런타임 장기기억. 이미 `.gitignore` 대상(`memory*.json`) |
| `autopull.log` (54KB) | 스크립트 로그. `.gitignore` 대상 |

**주의**: `memory.py`(모듈)는 남긴다. 지우는 것은 데이터 파일뿐이다.

---

## 2. 리팩터링 과제 (삭제 아님)

### 2-A. `mcmullen_evaluate` 가 GP 적법성을 확인하지 않는다 — **우선순위 상**

`om_core.mcmullen_evaluate` 는 `is_valid()` 를 거치지 않고 곧장
`is_reorientable_to_convex()` 로 간다. 따라서 **비-OM 부호벡터를 넣으면 그대로
`witness: True` 를 돌려준다.** 지금은 호출부마다 개별로 막고 있다
(`extended_lawrence.lawrence_union_chirotope` 의 fail-closed 게이트 등).

- 과제: `mcmullen_evaluate` 에 `validate: bool = True` 매개변수를 추가하고 기본을 검증으로
  둔다. 성능이 문제되는 내부 루프만 `validate=False` 로 명시 우회한다.
- **주의**: 이건 신뢰 앵커 수정이다. 반드시 `python om_core.py` 자체 테스트를 확장해
  "비-OM 입력이 witness 로 보고되지 않는다"는 케이스를 추가하고 함께 커밋할 것.

### 2-E. `om_core.mcmullen_evaluate` 의 기준선 U 가 틀렸다 — 우선순위 상

`U = 2*d + (1+d)//2` 로 되어 있는데 문헌 최선은 `2d + ⌈(d+1)/2⌉ − 1` 이다(QQ-0001,
`questions/ANSWERED.md`). floor/ceil 과 강부등호 −1 둘 다 틀려 **기준선이 한 칸 느슨**하다.
`reward = (U+1) − n` 이 이 값을 쓰므로 보상이 과대평가된다.

- 과제: `known_upper_bound(d) = 2*d + -(-(d+1)//2) - 1` 로 교정하고 `reward` 를 맞춘다.
  `layer_search.known_upper_bound` 에 이미 교정본과 출처 주석이 있다 — 그것과 일치시킬 것.
- **주의**: 신뢰 앵커 수정이다. `witness` 판정 자체는 U 와 무관하므로 위험은 낮지만,
  `python om_core.py` 자체 테스트에 d=3,5,7 의 기대 U 값을 assert 로 고정하고 함께 커밋할 것.

### 2-B. f 평가기가 세 곳에 흩어져 있다 — 우선순위 중

같은 계산(재배향별 circuit 균형)이 세 군데에 있다.

| 위치 | 방식 | 용도 |
|---|---|---|
| `om_core.is_reorientable_to_convex` | 전수, chirotope 재계산 | 판정(느림, 정확) |
| `mutation_lab.MutationLab` | 비트셋, 전 circuit × 전 재배향 | 돌연변이 이웃 분석 |
| `layer_search.CoverageScanner` | 단락(첫 덮개에서 중단) | 대규모 탐색 |

- 과제: 뒤의 둘만 공통 코어(circuit γ 마스크 생성)를 공유하게 한다. **`om_core` 는 합치지 말 것** —
  독립 경로 유지가 신뢰 근거다(§0).
- 회귀 방지: `layer_search.selftest` 의 "[1] 단락 주사 ↔ mutation_lab 완전 일치" 는 유지·강화.

### 2-C. 미연결 인프라의 상태 표시 — 우선순위 하

WP5~8 산출물 중 현재 어떤 경로에서도 import 되지 않는 것들:
`research_manager.py`, `research_ir.py`, `process_verifier.py`, `step_ranker.py`,
`translations.py`, `witness_analysis.py`, `certificate_export.py`, `benchmark_coverage.py`.

- **삭제하지 말 것.** 설계 결정(DECISIONS 0023~0027)의 산출물이고 자체 테스트가 있다.
- 과제: `CLAUDE.md` 아키텍처 지도에서 이들에 `(현재 미연결)` 표시를 붙여, 새 세션이
  "왜 안 쓰이나"를 다시 조사하지 않게 한다.

### 2-D. `attic/` 도입 — 우선순위 중

`attic/README.md` 에 "여기 있는 것은 **실측으로 폐기된** 경로다. 되살리려면 research_log 의
폐기 근거를 먼저 반증하라" 를 적고, 1-A/1-B 를 옮긴다. `pyproject.toml` 의 `py-modules`
에서도 함께 제거한다.

---

## 3. 작업 순서 (권고)

1. **2-A** (신뢰 구멍 — 다른 것보다 먼저)
2. 1-C 삭제 + `.gitignore` 확인
3. 2-D `attic/` 생성 → 1-A, 1-B 이동 → `pyproject.toml` 정리
4. 2-C 표시 추가
5. 2-B 공통 코어 추출

## 4. 완료 조건 (매 단계 후 전부 통과해야 한다)

```bash
python -m py_compile *.py scripts/*.py
python om_core.py && python criteria.py && python generator.py && python om_classes.py
python extended_lawrence.py && python interval_maps.py
python mutation_lab.py selftest && python layer_search.py selftest
python covering_cegis.py selftest && python insight_ledger.py verify
python scripts/sync_exec.py selftest
python scripts/session_bootstrap.py
```

그리고 `docs/DECISIONS.md` 에 append 로 무엇을 왜 지웠는지 남긴다. **삭제 자체가 결정이므로
기록 없이 지우면 다음 세션이 같은 조사를 반복한다.**
