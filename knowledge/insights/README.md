# Human insight ledger

이 디렉터리는 인간과의 수학 대화에서 나온 아이디어를 Claude와 Codex가 공동으로 읽는
append-only 기록 위치다.

- 권위 있는 데이터: `ledger.jsonl` (`insight_ledger.py`가 첫 등록 때 생성)
- 절차와 신뢰 경계: `docs/HUMAN_INSIGHT_PROTOCOL.md`
- 검증된 evidence: 이 ledger가 아니라 기존 `evidence_db.py`와 `experiments/`

`ledger.jsonl`을 직접 수정하거나 과거 줄을 삭제하지 않는다.
