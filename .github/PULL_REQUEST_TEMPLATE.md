## 역할
- [ ] 구현 (claude-code)
- [ ] 최적화/검토 (chatgpt)
- [ ] 사람 직접 수정

## 무엇을 / 왜
<!-- 변경 내용과 동기를 한두 문단으로. "무엇을 했다"뿐 아니라 "왜 필요했다"까지. -->

## 영향 범위 (Blast Radius)
<!-- 해당하는 항목을 모두 체크. 하나라도 체크되면 아래 "CLAUDE.md 불변 조건과의 관계"를 반드시 채울 것. -->
- [ ] `om_core.py`의 판별 로직 변경 (GP 공리 / acyclic / totally_cyclic / convex_position)
- [ ] `criteria.py`의 `REGISTRY` 변경/추가
- [ ] `om_classes.py`의 클래스 레지스트리 변경
- [ ] `theorist.py`의 결정론적 적대자(`proof_checker` / `counterexample_hunter`) 변경
- [ ] 공개 함수/클래스 시그니처 변경 (다른 모듈에서 import하는 것)
- [ ] 해당 없음 (문서 / 템플릿 / 순수 스타일 변경 등)

## CLAUDE.md 불변 조건과의 관계
<!-- 위에서 하나라도 체크했다면, CLAUDE.md §"절대 지켜야 할 불변 조건" 중 어느 항목과
     맞닿아 있는지, 그리고 그 조건을 어떻게 지켰는지 명시. -->

## 검증
- [ ] `python -m py_compile *.py`
- [ ] 변경한 모듈의 자체 테스트(`python <module>.py`) 통과
- [ ] CI(`ci.yml`) 통과 확인

## 상대방에게 남기는 질문 / 리뷰 요청 포인트
<!-- 확신이 없는 트레이드오프, 특히 반박·대안을 듣고 싶은 지점을 구체적으로 적을 것.
     없으면 "없음"이라고 명시. -->
