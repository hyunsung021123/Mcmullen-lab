# CLAUDE.md

Claude Code 가 이 저장소를 작업할 때 참고하는 프로젝트 지침입니다.

## 프로젝트 한 줄 요약

McMullen 문제(특히 d=5, Larman 추측 f(5)=11)의 상한을 **유향 매트로이드(OM) 재구성**으로
탐색하는 로컬 연구 에이전트. 결정론적 검증기가 유일한 신뢰 앵커이고, LLM(로컬 Ollama)은
방향만 제안하며 채택 여부는 항상 코드가 결정한다.

## 절대 지켜야 할 불변 조건 (신뢰 모델)

이 저장소를 수정할 때 다음을 절대 깨서는 안 됩니다:

1. **`om_core.py` 가 유일한 수학적 진실**이다. 어떤 결과가 "witness"로 기록되려면 반드시
   `mcmullen_evaluate()` 를 통과해야 한다. LLM 출력이나 휴리스틱만으로 witness 를 기록하지 말 것.
2. **적대자(`theorist.py` 의 `counterexample_hunter`, `proof_checker`)는 항상 결정론적 코드**여야
   한다. 이걸 LLM 호출로 바꾸면 신뢰 모델이 깨진다. (사용자가 명시적으로 "다분야 전문가가
   토론하되 통합 모델 하나가 처리하지 않는 구조"를 요구했음 — 역할 분리 + 결정론적 반박 유지.)
3. `acyclic`(GP 재구성) / `totally_cyclic`(쌍대) / `is_convex_position`(회로 균형) 은 서로
   **다른 개념**이다. 절대 섞지 말 것. `rank2_uniform` 클래스는 회로가 3원소라 convex 정의가
   자명하게 깨지는 알려진 특이 케이스이며 README §5 에 경고가 있다 — "버그"로 착각해 고치지 말 것.
4. `criteria.py` 의 `REGISTRY` 에 없는 이름을 조건으로 쓰면 안 된다. 새 이론적 성질을 추가할
   때는 `criteria.py` 에 `register()` 로 추가하고, `Chirotope`(om_core.py)에 필요한 메서드가
   있는지 먼저 확인할 것.
5. **불변량 어휘(`invariants.py`)는 판정 권한이 없다.** LLM 이 코드로 새 불변량을 추가할 수
   있지만(0028), 그것은 검증된 대상에 값을 붙이는 '자'일 뿐이다. `frozen=True` 인 라벨
   `witness` 는 덮어쓰기·폐기 모두 금지이며, 어휘는 `criteria` 의 `target` 모드로 승격되지
   않는다 — witness 의 정의를 바꾸는 경로는 존재해서는 안 된다.
6. **불변성(invariance) 등급을 임의로 올리지 말 것.** 표본 검사는 불변성을 반증할 수만 있고
   확증할 수 없다. `conjecture._invariance_of` 가 미확인(None)을 하위 등급으로 강등하는
   동작은 의도된 것이며, "너무 보수적"이라는 이유로 완화 금지.
7. **실현가능성(realizability)을 결론에 반영할 것.** 비실현 witness 는 ν(d) 상한을 증명하지
   않는다. 새 산출물에 witness 관련 주장을 넣을 때는 `scope.realizability` 를 함께 표시한다.
8. **인간 insight는 채팅 기억이 아니라 `insight_ledger.py`에 기록한다.** 사용자가 기록·검증·
   반영·탐색 적용을 요청한 아이디어는 `docs/HUMAN_INSIGHT_PROTOCOL.md`에 따라 처리한다.
   검증 전 아이디어를 pruning이나 witness 판정 경로에 바로 넣지 말 것.

## 세션 재시작 — 여기부터 읽는다

**새 세션이면 `docs/STATE.md` 를 먼저 읽는다.** 지금 무엇을 풀고 있는지, 확정된 사실,
**다시 걷지 말아야 할 죽은 길**, 진행 중 실험이 한 장에 있다. §6 자동 부록은
`python scripts/session_bootstrap.py` 로 갱신한다(실험을 시작·종료할 때마다).

이 문서(CLAUDE.md)는 **규칙**, `docs/STATE.md` 는 **상태**, `research_log.md` 는 **이력**이다.
셋을 섞지 않는다. 정리 대상 파일은 `docs/REFACTOR_BACKLOG.md`,
ChatGPT 자문 질문은 `questions/OPEN.md` 에 있다.

## 아키텍처 지도 (모듈 → 역할)

```
om_core.py     결정론적 검증 앵커 (Chirotope, GP 공리, circuit/cocircuit, mcmullen_evaluate)
om_classes.py  탐색 공간 레지스트리 — uniform/realizable/extended_lawrence_r2 등
generator.py   후보 생성 (backtracking/random/z3/cyclic)
extended_lawrence.py  signed-permutation rank-2 layer → rank-2m union 후보(HI-0001) +
                      블록·원소별 계수 t^(i·λ_j) 로 만든 **정수 좌표 실현 증명서**(HI-0004).
                      층별 상수배는 Laplace 전개상 원리상 무력 — 되돌리지 말 것(DECISIONS 0035)
interval_maps.py      ordered OM의 beta_k lower envelope + rank-2 fast path; 합성은 heuristic
criteria.py    이론적 성질 옵션 시스템 (require/forbid/target)
discovery.py   결정론적 패턴 발견 — 검증된 witness 구조 자동 분석
memory.py      장기기억(JSON, 실행 간 누적) — 제너레이터/기준/편향 통계
theorist.py    다중 전문가 토론(제안자 LLM 5역할) + 결정론적 적대자(Hunter/Checker)
search.py      연구 루프 오케스트레이션(SearchConfig, run_search)
progress.py    실시간 현황 + 일시정지/중단 (Progress, Control, SearchRunner)
store.py       provenance 저장(ResultsStore, ResultRecord, RoundRecord)
manager.py     Manager Agent — memory 를 실행 간 지속, 연구 보고서 생성
run.py         CLI 진입점 (--class, --research, --llm 등)
reorientation_cover.py  hypercube coverage 기반 exact witness 검증기(독립 이중 경로)
reorientation_sat.py    고정 χ convex-reorientation SAT 검증기 (z3 옵셔널, WP2)
cegis_search.py         GP outer solver + exact CEGIS 루프 — cut 학습 (z3 옵셔널, WP3)
symmetry_reduction.py   (Z2)^(n-1)⋊S_n exact orbit 축소 — relabel/canonical/automorphism (WP4)
research_ir.py          typed ResearchStep IR — kind별 obligation, legacy bias 무손실 왕복 (WP5)
process_verifier.py     결정론적 Process Verifier — first-failure, fail-closed (WP6)
evidence_db.py          append-only 근거 저장소(JSONL + hash chain) (WP6b)
insight_ledger.py       인간 수학 insight 공동 ledger — append-only 상태·출처·반증 계획 (0031)
step_ranker.py          rule-based 순위 — hard gate 통과분의 실행 순서만 결정 (WP7a)
translations.py         cross-domain translation registry — exactness 권한 분리 (WP7c)
witness_analysis.py     witness 구조 압축 — 최소 obstruction cover/UNSAT core/프로파일
research_manager.py     opt-in 자율 연구 오케스트레이터 — IR제안→게이트→기록→CEGIS 실행
certificate_export.py   certificate 번들 export — md/tex/lean/독립 replay.py (WP8)
certificate.py          witness certificate v1 생성 + Markdown/KaTeX 보고서 (Epic #37)
certificate_verify.py   certificate 독립 검증기 — coverage 로직 미공유, om_core 만 의존
benchmark_coverage.py   legacy(B0) vs coverage(B1) 정확성/성능 벤치마크
mutation_lab.py         GP 돌연변이 공간 — 비트셋 f 평가기(172ms→0.1ms) + kill-birth 분해
                        + killability(κ₁) + depth-h envelope. 판정 권한 없음(가속기)
layer_search.py         rank-2 layer 공간 탐색 — **상한 개선 주력**. 단락 덮개 주사(d 확장)
                        + n 스윕(U(d)부터 하강) + bound_gain 보상. 상태가 항상 실현가능
covering_cegis.py       덮개 조건 CEGIS — witness 존재/부재를 **완전하게** 판정. UNSAT 은
                        "그 (n,r) 에 OM witness 가 없다"는 결론 (z3 필수)
climb.py / sweep.py     (폐기 예정) 좌표공간 국소탐색·무작위 표집. chamber 내부에서 f 가
                        상수이므로 원리상 gradient 가 없음이 실측·증명됨 — 신규 사용 금지
nearmiss.py             근접 실패 구성의 survivor/fragile circuit 구조 보고서
scripts/sync_exec.py    main → exec 동결 스냅샷 동기화 + 실행 잠금 (저장소 운영 규약)

── 정리 발굴 파이프라인 (0028) — 새 주 진입점은 research_cycle.py ──
console.py          Windows 콘솔 UTF-8 전환 (표시 계층, 수학과 무관)
sandbox.py          LLM 작성 불변량 코드의 제한 문법 컴파일 (import/while/eval 금지)
invariants.py       개방형 불변량 어휘 — 내장 22개 + LLM 추가/폐기, 불변성 실측 분류
conjecture.py       코퍼스에서 '재평가 가능한 명제' 자동 채굴 + 등급 부여
falsify.py          명제를 먼저 반증하려 공격 (범위내 전수 / 확장 시험 분리)
reasoner.py         공급자 독립 추론 인터페이스 (FileReasoner=수동, Ollama, Scripted) + 프롬프트
research_cycle.py   CLI: run(코퍼스→채굴→반증→프롬프트) / ingest(응답 흡수) / vocab / status
```

정리 발굴 파이프라인의 신뢰 구조는 한 줄로: **LLM 은 어휘와 가설을 넓히고, 판정은
`om_core` 가, 기각은 `falsify` 가 한다.** LLM 이 제안한 추측은 흡수 즉시 반증 공격을
받으며, 반증되면 반례 chirotope 를 반드시 함께 보관한다(주장만 하는 반증 금지).
배경 정의는 `knowledge/problem.md`, 번역의 가설은 `knowledge/equivalent_formulations.md`,
문헌 주장과 실측의 분리는 `knowledge/known_results.md` 참조.

수정 전에 관련 모듈의 `if __name__ == "__main__":` 자체 테스트를 먼저 읽을 것 — 각 모듈에
기대 동작이 실행 가능한 예제로 들어있다.

coverage/certificate 파이프라인의 수학적 근거·trust label·후속 로드맵은
`docs/AUTONOMOUS_VERIFICATION_PIPELINE.md` 참고. **`certificate_verify.py` 의 독립성
(reorientation_cover/search/generator/theorist 등 import 금지)은 그 자체가 신뢰
근거이므로, "중복 제거"를 이유로 coverage 로직과 합치는 리팩터링은 금지.**

## 테스트 / 검증 명령

이 저장소에는 별도 테스트 프레임워크가 없다(의도적으로 표준 라이브러리만으로 각 모듈이
자체 테스트를 갖도록 설계됨). 수정 후 반드시 아래를 순서대로 실행:

```bash
python -m py_compile *.py                 # 문법/임포트 오류 확인
python om_core.py                         # 검증 앵커 자체 테스트
python criteria.py && python generator.py && python om_classes.py
python extended_lawrence.py && python interval_maps.py
python discovery.py                       # 몇 초~1분 소요(무작위 점배치 탐색)
python theorist.py                        # mock LLM 으로 토론 구조 점검(Ollama 불필요)
python progress.py                        # 스레드 pause/resume/stop 점검
python search.py                          # d=2 전수 탐색 데모(약 1~2초)
python manager.py                         # d=3 연구 루프 데모(약 30초~2분)
python run.py --list-classes
python run.py --config config.example.yaml --out /tmp/ci_test.json

# 정리 발굴 파이프라인 (0028)
python console.py && python sandbox.py    # 표시 계층 / 샌드박스 정책
python invariants.py                      # 어휘 + 라벨<->om_core 일치 (약 1~2분)
python conjecture.py                      # 채굴 무결성 + 등급 규율
python falsify.py                         # 소진 판정 + 반례 om_core 재확인 (약 2~4분)
python reasoner.py                        # 프롬프트/JSON 파싱 (LLM 불필요)
python research_cycle.py selftest         # run→모의응답→ingest 통합 (약 1~2분)
python insight_ledger.py                  # insight ledger 상태전이/hash-chain 자체 테스트
```


## 코딩 컨벤션

- 사용자 대면 텍스트(주석, docstring, CLI 출력, README)는 **한국어**로 작성한다(사용자의
  명시적 선호). 변수/함수명은 영어.
- 새 모듈을 추가하면 `if __name__ == "__main__":` 에 최소 하나의 자체 검증 예제를 넣는다.
- `pyproject.toml` 의 `[tool.setuptools] py-modules` 목록에 새 최상위 `.py` 파일을 추가해야
  `pip install -e .` 로 계속 인식된다.
- 무거운 선택적 의존성(z3-solver, pyyaml, requests)은 항상 `try/except ImportError`
  로 감싸 optional 로 유지한다 — 코어 검증기는 표준 라이브러리만으로 동작해야 한다.

## 다자간 AI 협업 (Claude Code · Codex · ChatGPT)

이 저장소는 Claude Code(직접 커밋), Codex(로컬 폴더 경유 간접 커밋), ChatGPT(읽기
전용)가 함께 작업할 수 있도록 설계되어 있다 — 세 참여자의 저장소 접근 권한은
대칭이 아니다. 역할 분담, 소통 채널(커밋/PR 규약·결정 로그·교차 리뷰 이슈), 건설적
반박의 형식은 `COLLABORATION.md`에 정의되어 있다 — 다른 참여자가 관여할 가능성이
있는 작업이라면 먼저 그 문서를 읽을 것. 설계 결정은 `docs/DECISIONS.md`에 append
방식으로 누적된다. 이 프로토콜도 위 불변 조건과 마찬가지로, "최적화"를 이유로
§1(신뢰 모델)을 깨는 제안은 자동 기각 대상이다.

인간과의 수학 대화에서 나온 아이디어를 다른 세션/에이전트가 이어받아야 하면
`docs/HUMAN_INSIGHT_PROTOCOL.md`를 따른다. 채팅 원문은 공유 상태가 아니며, Issue·PR·HANDOFF에
관련 `HI-NNNN`과 evidence/implementation 참조를 남겨야 한다.

## 자주 하는 작업 예시 프롬프트

- "criteria.py 에 '홀수 대칭군' 기준을 새로 추가해줘" → REGISTRY 패턴을 따르고 om_core.py 의
  Chirotope 에 필요한 메서드가 있는지 먼저 확인.
- "d=5 탐색이 너무 느려" → generator.py 의 backtracking 은 d≥4 에서 비실용적임을 README §10
  트랙터빌리티 섹션 참고 후 z3 백엔드나 REOM 소켓(om_classes.py 의 lawrence) 연결을 검토.
- "rank-2 Lawrence class로 탐색해줘" → `extended_lawrence_r2`와 `class_options` 사용.
  minimum interval composition은 ranking 전용이며 pruning이나 witness 판정으로 승격하지 말 것.
