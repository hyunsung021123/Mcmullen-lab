# 답변된 질문 아카이브

각 항목은 **답변 + 우리 측 검증 판정**을 함께 담는다. 답변 자체는 권한이 없다.

---

## QQ-0001 — 기존 상한 U(d) 의 정확한 출처와 값 · `ANSWERED` (2026-08-11, claude/웹조사)

### 답변

García-Colín · Montejano · Ramírez Alfonsín, *On the number of vertices of projective
polytopes* (Mathematika **69** (2023) 535–561; arXiv:1810.02671) 서론 식 (2), 원문 그대로:

> **2d+1 ≤ ν(d) < 2d + ⌈(d+1)/2⌉**
>
> "The lower bound was given by Larman [9] while the upper bound was provided by
> Ramirez Alfonsin [13]."

**부등호가 강부등호(<)다.** 따라서

$$\nu(d)\ \le\ 2d + \lceil (d+1)/2 \rceil - 1$$

홀수 d 에서는 ⌈(d+1)/2⌉ = (d+1)/2 이므로 **ν(d) ≤ (5d−1)/2**, layer 수 m=(d+1)/2 로 쓰면
**5m − 3**.

보조 확인(Wikipedia, `SECONDHAND`): Larman 1972 `ν(d) ≤ (d+1)²`, Las Vergnas 1986
`ν(d) ≤ (d+1)(d+2)/2`, Ramírez Alfonsín 2001 `ν(d) ≤ 2d+⌈(d+1)/2⌉` — 마지막이 최선.
추측 ν(d)=2d+1 은 d=2,3,4 에서 증명됨.

| 확인 수준 | 대상 |
|---|---|
| `FULLTEXT` | arXiv:1810.02671 (ar5iv HTML) 서론 식 (2) 와 귀속 문장을 직접 읽음 |
| `SECONDHAND` | Ramírez Alfonsín 2001 **원논문 자체는 미확인** — 위 논문의 인용을 통한 것 |
| `SECONDHAND` | Wikipedia 의 Larman/Las Vergnas 수치 |

### 우리 측 판정 — **정정 반영, 종전 구현은 오류였다**

`layer_search.known_upper_bound` 가 `2d + ⌊(1+d)/2⌋` 를 상한으로 썼다. **두 군데가 틀렸다**:
(a) floor/ceil, (b) 강부등호의 −1 누락. 결과적으로 기준선이 한 칸 느슨했고,
"d=5 에서 n=13 witness 면 개선"이라는 **잘못된 결론**을 냈다. 실제로는 ν(5) ≤ 12 가 이미
알려져 있어 n=13 witness 는 아무것도 개선하지 않는다.

정정 후 개선 구간:

| d | m | 하한 2d+1 | 문헌 최선 ν(d) ≤ | Larman witness n = 4m | **개선되는 n** | 구간 크기 m−2 |
|---|---|---|---|---|---|---|
| 3 | 2 | 7 | 7 | 8 | 없음 | 0 |
| 5 | 3 | 11 | **12** | 12 | **{12}** | 1 |
| 7 | 4 | 15 | 17 | 16 | {16, 17} | 2 |
| 9 | 5 | 19 | 22 | 20 | {20, 21, 22} | 3 |
| 11 | 6 | 23 | 27 | 24 | {24…27} | 4 |

**전략적 함의.** d=5 는 개선 구간이 Larman 목표 한 점과 일치한다 — 즉 **d=5 에서 상한을
개선하려면 곧바로 Larman 을 증명해야 한다.** 반면 d ≥ 7 은 Larman 최적이 아니어도 상한이
내려간다(구간 크기 m−2). 상한 개선이 목표라면 **d=7 이 d=5 보다 쉽다.**

**후속.** `om_core.mcmullen_evaluate` 의 기준선 `U = 2d + (1+d)//2` 에도 같은 오류가 있다.
신뢰 앵커라 자체 테스트 확장과 함께 처리한다 — `docs/REFACTOR_BACKLOG.md` §2-E.
Ramírez Alfonsín 2001 원논문은 여전히 미확인이므로 `knowledge/papers/` 반입 목록 최상위에
남긴다.
