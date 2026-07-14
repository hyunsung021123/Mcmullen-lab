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

## 아키텍처 지도 (모듈 → 역할)

```
om_core.py     결정론적 검증 앵커 (Chirotope, GP 공리, circuit/cocircuit, mcmullen_evaluate)
om_classes.py  탐색 공간(클래스) 레지스트리 — uniform/realizable/rank2/cyclic/lawrence(소켓)
generator.py   후보 생성 (backtracking/random/z3/cyclic)
criteria.py    이론적 성질 옵션 시스템 (require/forbid/target)
discovery.py   결정론적 패턴 발견 — 검증된 witness 구조 자동 분석
memory.py      장기기억(JSON, 실행 간 누적) — 제너레이터/기준/편향 통계
theorist.py    다중 전문가 토론(제안자 LLM 5역할) + 결정론적 적대자(Hunter/Checker)
search.py      연구 루프 오케스트레이션(SearchConfig, run_search)
progress.py    실시간 현황 + 일시정지/중단 (Progress, Control, SearchRunner)
store.py       provenance 저장(ResultsStore, ResultRecord, RoundRecord)
manager.py     Manager Agent — memory 를 실행 간 지속, 연구 보고서 생성
run.py         CLI 진입점 (--class, --research, --llm 등)
dashboard.py   Streamlit UI
ui_helpers.py  대시보드용 순수 로직(라벨/검증/요약 — streamlit 비의존)
reorientation_cover.py  hypercube coverage 기반 exact witness 검증기(독립 이중 경로)
reorientation_sat.py    고정 χ convex-reorientation SAT 검증기 (z3 옵셔널, WP2)
cegis_search.py         GP outer solver + exact CEGIS 루프 — cut 학습 (z3 옵셔널, WP3)
symmetry_reduction.py   (Z2)^(n-1)⋊S_n exact orbit 축소 — relabel/canonical/automorphism (WP4)
research_ir.py          typed ResearchStep IR — kind별 obligation, legacy bias 무손실 왕복 (WP5)
process_verifier.py     결정론적 Process Verifier — first-failure, fail-closed (WP6)
evidence_db.py          append-only 근거 저장소(JSONL + hash chain) (WP6b)
step_ranker.py          rule-based 순위 — hard gate 통과분의 실행 순서만 결정 (WP7a)
translations.py         cross-domain translation registry — exactness 권한 분리 (WP7c)
witness_analysis.py     witness 구조 압축 — 최소 obstruction cover/UNSAT core/프로파일
research_manager.py     opt-in 자율 연구 오케스트레이터 — IR제안→게이트→기록→CEGIS 실행
certificate_export.py   certificate 번들 export — md/tex/lean/독립 replay.py (WP8)
certificate.py          witness certificate v1 생성 + Markdown/KaTeX 보고서 (Epic #37)
certificate_verify.py   certificate 독립 검증기 — coverage 로직 미공유, om_core 만 의존
benchmark_coverage.py   legacy(B0) vs coverage(B1) 정확성/성능 벤치마크
```

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
python discovery.py                       # 몇 초~1분 소요(무작위 점배치 탐색)
python theorist.py                        # mock LLM 으로 토론 구조 점검(Ollama 불필요)
python progress.py                        # 스레드 pause/resume/stop 점검
python search.py                          # d=2 전수 탐색 데모(약 1~2초)
python manager.py                         # d=3 연구 루프 데모(약 30초~2분)
python run.py --list-classes
python run.py --config config.example.yaml --out /tmp/ci_test.json
```

Streamlit 대시보드는 헤드리스로 부팅만 확인 가능(실제 클릭 흐름은 사람이 확인해야 함):
```bash
streamlit run dashboard.py --server.headless true &
sleep 8; curl -sf http://localhost:8501 > /dev/null && echo OK
```

## 코딩 컨벤션

- 사용자 대면 텍스트(주석, docstring, CLI 출력, README)는 **한국어**로 작성한다(사용자의
  명시적 선호). 변수/함수명은 영어.
- 새 모듈을 추가하면 `if __name__ == "__main__":` 에 최소 하나의 자체 검증 예제를 넣는다.
- `pyproject.toml` 의 `[tool.setuptools] py-modules` 목록에 새 최상위 `.py` 파일을 추가해야
  `pip install -e .` 로 계속 인식된다.
- 무거운 선택적 의존성(streamlit, z3-solver, pyyaml, requests)은 항상 `try/except ImportError`
  로 감싸 optional 로 유지한다 — 코어 검증기는 표준 라이브러리만으로 동작해야 한다.

## 다자간 AI 협업 (Claude Code · Codex · ChatGPT)

이 저장소는 Claude Code(직접 커밋), Codex(로컬 폴더 경유 간접 커밋), ChatGPT(읽기
전용)가 함께 작업할 수 있도록 설계되어 있다 — 세 참여자의 저장소 접근 권한은
대칭이 아니다. 역할 분담, 소통 채널(커밋/PR 규약·결정 로그·교차 리뷰 이슈), 건설적
반박의 형식은 `COLLABORATION.md`에 정의되어 있다 — 다른 참여자가 관여할 가능성이
있는 작업이라면 먼저 그 문서를 읽을 것. 설계 결정은 `docs/DECISIONS.md`에 append
방식으로 누적된다. 이 프로토콜도 위 불변 조건과 마찬가지로, "최적화"를 이유로
§1(신뢰 모델)을 깨는 제안은 자동 기각 대상이다.

## 자주 하는 작업 예시 프롬프트

- "criteria.py 에 '홀수 대칭군' 기준을 새로 추가해줘" → REGISTRY 패턴을 따르고 om_core.py 의
  Chirotope 에 필요한 메서드가 있는지 먼저 확인.
- "d=5 탐색이 너무 느려" → generator.py 의 backtracking 은 d≥4 에서 비실용적임을 README §10
  트랙터빌리티 섹션 참고 후 z3 백엔드나 REOM 소켓(om_classes.py 의 lawrence) 연결을 검토.
- "REOM 인코딩 연결해줘" → om_classes.py 의 `register_class(OMClass("reom",...), generator=...)`
  소켓에 (n, r, *, accept, **kw) -> Iterator[Chirotope] 시그니처로 연결.
