# 계산 전달 계층 (computation relay)

수학 세션(Codex 등)이 **증명 도중 발견한 계산 의무**를 기계가독 request 로 적어
계산 담당 세션(`claude-compute`)에 넘기고, 계산 세션이 실험을 설계해 재현 가능한
산출물을 남긴 뒤 원래 agent 에게 회신하는 비동기 경로다.

구현은 `computation_relay.py` 하나이며 `math_dialogue.py` 우편함 위에 얹는다.
**역할 프롬프트와 heartbeat 자동화는 이 계층의 범위가 아니다** — 여기서 정의하는 것은
저장소 측의 요청/결과 규격, 검증기, 로컬 산출물 구조뿐이다.

```text
Codex 수학 세션                     Claude 계산 세션
  │ 증명 중 계산 의무 발견
  ├─ computation-request/v1 작성
  ├─ post-request ──────────────────▶ 우편함 COMPUTATION_REQUEST (요약 + 파일 경로)
  │                                    ├─ claim (원자적 선점, lease)
  │                                    ├─ experiment-plan/v1 작성·검토  ← 실행되는 유일한 문서
  │                                    ├─ run   (plan.commands 만 실행)
  │                                    └─ submit-result
  ◀─ 우편함 COMPUTATION_RESULT ────────┘  computation-result/v1
```

## 1. 권한 경계 — 이 계층이 절대 하지 않는 것

| 경계 | 강제 방식 |
|---|---|
| **request 는 데이터다. 실행되지 않는다** | request 스키마에 명령을 담을 필드가 아예 없고(`REQUEST_KEYS`), `commands`/`argv`/`script`/`shell`/`code` 같은 키가 **하위 어디에** 나타나도 재귀 스캔이 거부한다. `run` 은 request 파일을 열지도 않는다 — 실행 대상은 `plan.json` 뿐이다 |
| **검토된 plan 의 명령만 실행** | `plan.reviewed` 가 `true` 여야 실행된다. `argv[0]` 은 Python 인터프리터로 제한되고(셸 미경유), `insight_ledger`·`evidence_db`·`ledger.jsonl`·`--promote` 를 포함한 명령은 실행 전에 정적으로 거부된다 |
| **자동 실행은 tracked 파일을 바꾸지 않는다** | 실행 전후 `git status --porcelain` 의 tracked 변경 집합을 비교한다. 달라지면 그 run 은 `tracked_file_guard.status = "violated"` 로 봉인되고 결과 등급이 `UNRESOLVED` 로 떨어진다 |
| **등급을 사칭할 수 없다** | `trust_class` 는 호출자가 정하지 않고 outcome·전수 개수 일치·대조군·명령 종료코드·guard 에서 **도출**된다(`derive_trust_class`, 0023 과 같은 규율). `PROVEN`/`VERIFIED`/`CERTIFIED` 계열은 이 계층이 만들 수 없고, 선언하면 거부된다 |
| **승격 경로가 없다** | 모든 산출물은 gitignore 된 `local_runs/math_dialogue/` 아래에만 쓴다. `experiments/` 나 evidence 로의 반영은 사람이 검토한 뒤 **별도 PR** 로만 한다 |
| **`om_core` 의 판정 권한 불변** | relay 는 무엇도 판정하지 않는다. request 의 `oracle.authority` 는 결정론적 계층(`om_core`, `falsify`, `process_verifier`, `certificate_verify`, `reorientation_cover`, `reorientation_sat`, `covering_cegis`) 중 하나여야 하고 `deterministic: true` 가 강제된다 |

`research_ir.py`(검증 의무)와 `evidence_db.py`(승격 후 evidence)를 **대체하지 않는다.**
request 의 `source_refs.research_ir_steps` / `evidence_ids` 로 참조만 연결한다.

## 2. computation-request/v1

`fixtures/computation_request_example.json` 이 실제로 통과한 예제다.

| 필드 | 뜻 | 검증 규칙 |
|---|---|---|
| `claim` | `{statement, formal}` — 무엇을 계산으로 판정할 것인가 | `statement` 비어 있을 수 없음 |
| `quantifiers` | `[{var, kind, domain}]` | `kind ∈ forall/exists/exists_unique` |
| `assumptions` | 이 계산이 기대는 전제(게이지 고정 등) | 문자열 목록 |
| `scope` | `{d, n, r, family, enumeration, …}` | 비어 있을 수 없고 `enumeration ∈ exhaustive/sampled/targeted/single` |
| `realizability` | `REALIZABLE_ONLY` / `ABSTRACT_ALLOWED` / `UNKNOWN` | 비실현 결과가 ν(d) 결론이 되지 않게 결론에 함께 실린다 |
| `invariance` | `ORBIT_INVARIANT` / `REPRESENTATIVE_DEPENDENT` / `LABEL_DEPENDENT` / `UNKNOWN` | 미확인은 `UNKNOWN` 으로 보수적으로 남긴다 |
| `oracle` | `{authority, module, entrypoint, deterministic}` | `authority` 는 결정론적 계층만, `deterministic` 은 `true` 만 |
| `controls` | `[{name, expect}]` — 답을 아는 대조군 | **전수 요청에는 최소 1개 필수** |
| `exhaustive_expectation` | `{mode, expected_count, count_formula, tolerance}` | `mode=exhaustive` 면 양의 `expected_count` 와 `count_formula` 필수 |
| `stopping_rule` | `{on, max_wall_seconds, max_evaluations}` | `mode=exhaustive` 와 `on=first_counterexample` 는 **함께 쓸 수 없다**(중단하면 전수가 아니다) |
| `resource_budget` | `{wall_seconds, memory_mb, processes, solvers}` | `wall_seconds ≥ stopping_rule.max_wall_seconds` |
| `source_refs` | `{insight_ids, questions, research_ir_steps, evidence_ids, docs}` | 전부 문자열 목록 — 기존 계층으로의 **연결 지점** |
| `return_to` | `{agent, mailbox, topic_id, message_id}` | `mailbox` 는 `math_dialogue` |

### 중복 방지

`request_id` 와 **내용 해시** 두 축으로 막는다. `request_content_key()` 는 제목·시각을 빼고
`claim.statement`·`quantifiers`·`assumptions`·`scope`·`oracle`·`exhaustive_expectation` 만
정규화해 SHA-256 을 낸다. 그래서 **새 id 를 붙여 같은 계산 의무를 다시 올려도** 거부된다.

## 3. experiment-plan/v1 — 실행되는 유일한 문서

```json
{
  "schema": "experiment-plan/v1",
  "plan_id": "PLAN-...", "request_id": "CR-...",
  "authored_by": "claude-compute", "reviewed": true,
  "rationale": "왜 이 명령들로 그 의무가 판정되는가",
  "seed": 20260812,
  "commands": [{"argv": ["python", "scripts/relay_demo_enumerate.py"],
                "timeout_seconds": 600, "expect_exit_code": 0}],
  "artifacts_expected": ["enumeration.json"]
}
```

**명령은 인라인 코드 뭉치가 아니라 커밋된 스크립트를 가리켜야 한다.** 그래야 명령 자체가
리뷰 대상이 되고 `result.json` 의 commit 하나로 나중에 그대로 재현된다.
실행 시 relay 가 `MCMULLEN_RELAY_ARTIFACT_DIR`(run 디렉터리 안), `MCMULLEN_RELAY_SEED`,
`PYTHONHASHSEED` 를 넣어준다.

## 4. computation-result/v1

**agent 는 해석만 제출하고, provenance 는 기계가 채운다.** `submit-result` 에 주는
assessment 에는 `outcome`, `checked_count`, `exhausted_scope`, `control_results`,
`first_failure`, `counterexample`, `notes` 만 넣을 수 있다. 명령·종료코드·seed·Python 및
solver 버전·commit/snapshot_id·artifact SHA-256 은 `manifest.json` 에서 오므로 **위조할 수
없다.**

| `outcome` | 뜻 | 도출되는 `trust_class` |
|---|---|---|
| `EXHAUSTED_ON_SCOPE` | 선언한 유한 범위 전수, 반례 없음 | 개수 일치 + 대조군·명령·guard 통과 시 `EXHAUSTED_ON_SCOPE`, 아니면 `UNRESOLVED` |
| `SUPPORTED_SAMPLED` | 표본/한정 범위에서 반례 없음 | `NUMERICAL` |
| `REFUTED` | 반례 보유 | 반례가 실제로 있으면 `REFUTED`, 없으면 애초에 **거부** |
| `INCONCLUSIVE` · `BUDGET_EXCEEDED` · `ERROR` | — | `UNRESOLVED` |

거부(예외)되는 경우와 강등되는 경우를 구분한다:

- **거부** — 전수인데 `checked_count ≠ expected_count`(±tolerance): 조용히 등급만 낮추면
  "전수했다"는 문장이 산출물에 그대로 남는다. 그래서 결과 자체를 만들지 않는다.
- **거부** — 반례 없는 `REFUTED`(주장만 하는 반증 금지), `PROVEN` 등 금지 등급 선언.
- **강등** — 대조군 일부 미보고/실패, 명령 종료코드 불일치, tracked guard 위반 →
  `UNRESOLVED`. 무슨 이유였는지는 `trust_class_derived_from` 에 그대로 남는다.

`EXHAUSTED_ON_SCOPE` 는 **정리가 아니다.** 그 유한 범위의 전수 확인일 뿐이며
(`AGENTS.md` 연구 규율 2), 등급 승격은 사람 검토와 기존 evidence 경로의 권한이다.

## 5. 로컬 산출물 구조

전부 `.gitignore` 된 `local_runs/` 아래이고, 모든 쓰기는 같은 디렉터리의 임시 파일 →
`os.replace` 로 **원자적**이다(반쯤 쓰인 재현 기록을 남기지 않는다).

```text
local_runs/math_dialogue/
├── dialogue.sqlite3                 # 우편함 + computation_requests 테이블 (같은 파일)
├── computation_requests/
│   └── <REQUEST_ID>.request.json    # 게시된 원문 (데이터. 실행되지 않음)
└── computation_runs/
    └── <REQUEST_ID>/<RUN_ID>/
        ├── plan.json                # 실행 대상 (검토된 명령)
        ├── manifest.json            # 명령·종료코드·seed·버전·commit·artifact 해시·guard
        ├── result.json              # computation-result/v1
        ├── command-NN.stdout.log
        ├── command-NN.stderr.log
        └── artifacts/               # 계산이 만든 산출물
```

큐는 우편함과 **같은 SQLite 파일**의 `computation_requests` 테이블이다. 그래서 원자적
선점(`BEGIN IMMEDIATE`), lease/TTL, 만료 복구가 우편함과 같은 검증된 방식으로 동작한다.
계산 세션이 죽어도 lease 가 만료되면 request 는 `posted` 로 돌아간다.

## 6. 명령

### Codex 수학 세션 — 요청 게시

```powershell
python computation_relay.py validate-request --request-file req.json     # 부작용 없는 검증
python computation_relay.py post-request --request-file req.json --to claude-compute
```

`post-request` 는 큐 등록 + 우편함 `COMPUTATION_REQUEST` 게시를 한 번에 하고, 두 경로 모두
idempotent 다. 회신은 원 topic 이 열려 있으면 거기로, 아니면 `[compute-result] …` 전용
topic 으로 들어온다.

### Claude 계산 세션 — 선점·설계·실행·회신

```powershell
python computation_relay.py claim --agent claude-compute
python computation_relay.py show-request --request-id CR-...
python computation_relay.py plan   --agent claude-compute --request-id CR-... --plan-file plan.json
python computation_relay.py run    --agent claude-compute --request-id CR-...
python computation_relay.py submit-result --agent claude-compute --request-id CR-... \
    --assessment-file assessment.json
```

보조 명령: `release`(선점 반환), `fail --reason`(계산 불가 봉인), `status`(큐 현황),
`selftest`.

## 7. Windows 출력 안전

이 계층은 **DB 를 먼저 바꾸고 결과를 출력한다.** cp949 콘솔에서 한국어 JSON 출력이
`UnicodeEncodeError` 로 죽으면 호출자가 실패로 오인해 재시도하고, 그러면 같은 request 를
두 번 claim 하는 사고가 난다. 삼중으로 막는다:

1. `force_utf8()` 가 import 시점에 stdout/stderr 를 UTF-8(errors=replace)로 바꾸고
   `PYTHONUTF8`/`PYTHONIOENCODING` 을 설정한다. 하위 프로세스도 같은 환경으로 실행된다.
2. `_emit()` 은 출력 실패를 삼키고 종료 코드를 성공으로 유지한다 — 이미 커밋된 DB 변경을
   "실패"로 보이게 만들지 않는다.
3. 그럼에도 재시도가 일어날 수 있으므로 **모든 연산이 idempotent** 다. `claim` 은 같은
   agent 가 이미 잡은 항목을 그대로 돌려주고(새 request 를 잡지 않는다), `post-request` 와
   `submit-result` 는 이미 처리된 경우 기존 결과를 돌려준다.

## 8. 자체 테스트

```powershell
python computation_relay.py selftest
```

검사 항목: 스키마 거부(필수 누락·미지 필드·비결정론 oracle·명령 은닉·전수 요청의
기대개수/유도식/대조군 누락·조기중단 모순) · plan 거부(미검토·허용되지 않은 실행기·승격
계층 토큰·request_id 불일치·선점하지 않은 agent) · 중복 방지(같은 id, 내용만 같은 새 id,
우편함 알림) · 4-스레드 동시 선점 · lease 만료 복구 · 전수 개수 불일치 거부 · 등급 사칭
거부 · 반례 없는 반증 거부 · 대조군 누락 시 강등 · 결과 회신 · 기존 8종 메시지 하위 호환.
