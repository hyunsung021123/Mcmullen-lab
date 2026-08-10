# knowledge/papers/ — 원문 반입함

유료 저널 접근은 AI 에게 위임할 수 없다. **사람이 여기에 PDF 를 넣으면 AI 가 읽는다.**

## 넣는 법

파일명: `<저자성>-<연도>-<짧은슬러그>.pdf`  (예: `forge-2001-10points-dim4.pdf`)

넣은 뒤 아래 표에 한 줄 추가한다. **표에 없는 파일은 읽지 않은 것으로 취급한다.**

## 반입 목록

| 파일 | 서지 | 우선순위 | 왜 필요한가 | 확인 수준 |
|---|---|---|---|---|
| _(비어 있음)_ | Forge–Las Vergnas–Schuchert, *10 Points in Dimension 4…*, EJC 22(5) 705–708, 2001 | **최상** | d=4 witness 명시 좌표 → 파이프라인 보정 + d=5 lifting seed (QQ-0005) | — |
| _(비어 있음)_ | Ramírez Alfonsín, *Lawrence Oriented Matroids…*, EJC 22(5) 723–731, 2001 | **최상** | 현재 일반 상한 U(d) 의 출처와 정확한 값 (QQ-0001) | — |
| _(비어 있음)_ | Lawrence–Weinberg, *Unions of oriented matroids*, LAA 41, 183–200, 1981 | 상 | union 이 항상 OM 인가 / realizable 이 보존되는가 (QQ-0002) | — |
| _(비어 있음)_ | García-Colin–Montejano–Ramírez Alfonsín, Mathematika 69, 535–561, 2023 | 중 | 2023 시점 최선 상한이 정말 고전 값인지 (QQ-0001) | — |
| _(비어 있음)_ | Cordovil–Silva, EJC 6(2) 157–161, 1985 | 하 | 하한 ν(d) ≥ 2d+1 의 원문 진술 | — |

## 확인 수준 (인용 규약)

| 값 | 뜻 |
|---|---|
| `FULLTEXT` | 원문을 읽고 해당 정리·좌표를 직접 확인했다 |
| `ABSTRACT_ONLY` | 초록/서지만 봤다 — **결론에 인용 금지** |
| `SECONDHAND` | 다른 문헌이나 모델의 전언 — **결론에 인용 금지** |

`FULLTEXT` 로 올라간 주장만 `knowledge/known_results.md` 의 `[출처 확인 필요]` 표시를 뗄 수 있다.

## 저작권

여기 있는 PDF 는 **개인 연구용 로컬 사본**이다. `.gitignore` 로 커밋에서 제외되며,
저장소에는 서지·확인 수준·인용 문장만 남는다.
