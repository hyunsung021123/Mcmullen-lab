# questions/ — 수학 자문 채널 (ChatGPT ↔ 저장소)

ChatGPT 는 이 저장소를 읽을 수 있다. 사람이 매번 질문을 옮겨 적는 대신, **여기에 질문을
쌓아두면 ChatGPT 가 읽고 답을 채운다.** 사람은 중계자가 아니라 승인자다.

## 파일 세 개뿐이다 (의도적으로 단순하게)

```
questions/OPEN.md       열린 질문 큐. ChatGPT 가 읽을 곳.
questions/ANSWERED.md   답변 + 우리 측 검증 판정 아카이브.
questions/README.md     이 문서(규약).
```

원문 길이가 긴 왕복(수십 KB 프롬프트/응답)은 기존 `prompts/` · `responses/` 를 쓴다.
여기는 **짧고 반증 가능한 질문**을 위한 채널이다.

## 질문 작성 규약 (Claude/Codex 가 쓴다)

각 질문은 `QQ-NNNN` 번호를 갖고 다음을 반드시 포함한다.

| 항목 | 내용 |
|---|---|
| `상태` | `OPEN` / `ANSWERED` / `RETIRED` |
| `왜 막혔는가` | 이 답이 없으면 **무엇을 못 하는지**. 없으면 질문 자격이 없다 |
| `우리가 이미 안 것` | 실측값과 그 출처 파일 — 중복 노동을 막는다 |
| `요구 형식` | 계산으로 확인 가능한 형태. 좌표·공식·반례 |
| `검증 방법` | 답이 오면 **우리가 어떤 코드로 확인할지** 미리 적는다 |

## 답변 규약 (ChatGPT 가 쓴다)

1. **등급을 반드시 붙인다**: `PROVEN` / `VERIFIED` / `NUMERICAL` / `CONJECTURE` / `SPECULATION`.
   등급 없는 주장은 `SPECULATION` 으로 강등되어 처리된다.
2. **문헌 인용은 확인 수준을 함께 적는다**: `FULLTEXT` / `ABSTRACT_ONLY` / `SECONDHAND`.
   우리는 `FULLTEXT` 아닌 인용을 결론에 쓰지 않는다.
3. 보조정리를 제안하면 **반례를 찾으려 시도한 흔적**을 함께 남긴다.
4. 답은 `questions/OPEN.md` 의 해당 항목 아래 `### 답변` 절에 직접 쓴다.

## 처리 규약 (Claude 가 한다 — 이게 신뢰 경계다)

답변이 도착해도 **그 자체로는 아무 권한이 없다.**

- 검증 전 아이디어를 pruning·witness 판정 경로에 넣지 않는다 (CLAUDE.md 불변조건 8).
- 채택하려면 `knowledge/insights/ledger.jsonl` 에 `HI-NNNN` 으로 등록하고
  `docs/HUMAN_INSIGHT_PROTOCOL.md` 의 상태 전이를 거친다.
- 검증이 끝나면 질문을 `ANSWERED.md` 로 옮기고 **우리 측 판정**(재현됨/반증됨/미확인)을 적는다.
