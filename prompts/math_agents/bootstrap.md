# 새 수학 task 최초 활성화 절차

이 절차의 입력은 고정 `{AGENT_NAME}`과 `{ROLE_FILE}`이다. 한 task에서 한 번만 수행한다.

1. 저장소 루트를 현재 작업 폴더로 확인한다.
2. 실행 파일은 루트의 `math_dialogue.py`를 우선 사용하고, 아직 PR이 병합되지 않아 없으면
   `local_runs/math_dialogue/runtime/math_dialogue.py`를 사용한다.
3. DB는 항상 저장소 루트의 `local_runs/math_dialogue/dialogue.sqlite3`를 `--db`로 명시한다.
4. Python은 PATH의 `python`, `py -3`, Codex 번들 Python 순으로 실제 실행 가능한 것을 고른다.
5. `common.md`, `{ROLE_FILE}`, `heartbeat.md`, 저장소 `AGENTS.md`, `docs/STATE.md`를 읽는다.
6. `{AGENT_NAME}`을 역할 파일에 적힌 설명으로 DB에 등록한다.
7. 현재 task로 돌아오는 10분 간격 heartbeat automation을 Local 환경으로 하나 만든다. 이름은
   `Math dialogue — {AGENT_NAME}`이다. 이미 같은 이름이 있으면 새로 만들지 말고 갱신한다.
8. automation prompt에는 선택한 Python·CLI·DB의 절대경로, agent 이름, 역할 파일,
   `heartbeat.md`의 한-message 규약을 전부 적는다. 알림 설정은 사용자가 별도로 요청하지 않으면
   기본값을 유지한다.
9. 최초 사용자 메시지에 역할 설정 외의 수학 연구 목표가 포함돼 있으면 그 부분만
   `local_runs/math_dialogue/intake/` 아래 UTF-8 파일로 쓰고 `enqueue --to {AGENT_NAME}`한다.
10. heartbeat 한 사이클을 즉시 수동 실행해 `sync-open/claim` 결과와 tracked 파일 무변경을
    확인한다.

성공 후 사용자에게는 agent 등록, automation 이름·주기, 첫 heartbeat 결과만 짧게 보고한다.
역할 설정 문장 자체를 topic으로 넣지 않는다. background run에서 권한 승인이 필요해 실패하면
우회하지 말고 해당 run을 종료하고 사람에게 필요한 최소 권한만 알린다.
