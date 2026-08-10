"""
conjecture.py — 검증된 코퍼스에서 '반증 가능한 수학적 명제'를 자동 채굴한다.

## 이 모듈이 푸는 문제

지금까지 이 저장소는 witness 를 **찾고 검증**할 수는 있었지만, 찾은 것으로부터
**수학적 성질을 문장으로 뽑아내지는 못했다.** `discovery.py` 가 하던 일은
"witness 들의 80% 가 이 값을 갖는다" 수준의 빈도 보고였고, 그건 명제가 아니라 통계다.

이 모듈은 코퍼스에서 **재평가 가능한 형태의 명제**를 만든다:

    (전건 원자들의 논리곱)  ⟹  (후건 원자)

원자(atom)는 `{불변량, 비교연산, 값}` 이라 새 chirotope 에 그대로 다시 적용할 수
있다. 따라서 채굴된 명제는 감상이 아니라 **`falsify.py` 가 즉시 공격할 수 있는
표적**이다. "먼저 반증을 시도하고, 살아남은 것만 다듬는다"는 규율이 여기서 강제된다.

## 신뢰 등급 (절대 섞지 않는다)

  MINED                코퍼스에서 관찰됨. **아무것도 증명하지 않았다.**
  REFUTED              반례가 실제로 발견됨 (반례 chirotope 를 함께 보관)
  EXHAUSTED_ON_SCOPE   그 유한 범위에서 전수 확인됨 = '계산으로 검증된 유한 사례'.
                       정리가 아니다. 다른 n/rank 로는 아무것도 말하지 않는다.
  UNRESOLVED           예산 안에서 반례를 못 찾았고 전수도 아님 = 증거 없음에 가까움

## 불변성 등급 (정리로서의 의미를 좌우)

witness 성질은 재배향 궤도 불변이고 원소 이름과 무관하다. 그래서:

  ORBIT_INVARIANT           양변이 전부 궤도 불변 → witness 와 동치가 될 수 있는 명제
  REPRESENTATIVE_DEPENDENT  한쪽이 재배향에 의존 → '이 대표원소에서만' 참일 수 있음.
                            witness 와의 동치 주장은 이 등급에서 원천적으로 불가능하다.
  LABEL_DEPENDENT           원소 이름에 의존 → 정리 후보로 쓸 수 없음 (거의 폐기)

이 등급은 선언이 아니라 `invariants.vet_invariant` 의 실측 분류에서 유도된다.

의존성: 표준 라이브러리 + om_core + invariants.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

from om_core import Chirotope
import invariants as INV

SCHEMA_ID = "conjecture/v1"

# 신뢰 등급
MINED = "MINED"
REFUTED = "REFUTED"
EXHAUSTED_ON_SCOPE = "EXHAUSTED_ON_SCOPE"
UNRESOLVED = "UNRESOLVED"

# 불변성 등급
ORBIT_INVARIANT = "ORBIT_INVARIANT"
REPRESENTATIVE_DEPENDENT = "REPRESENTATIVE_DEPENDENT"
LABEL_DEPENDENT = "LABEL_DEPENDENT"

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
}


# ═══════════════════════════ 코퍼스 ═══════════════════════════
@dataclass
class CorpusItem:
    id: str
    chirotope: dict
    features: dict
    label: bool                     # om_core 가 만든 witness 라벨

    def as_dict(self):
        return asdict(self)


@dataclass
class Corpus:
    scope: dict                     # {"n","r","om_class","backend","how","exhaustive"}
    items: list[CorpusItem] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    # ---- 통계 ----
    @property
    def witnesses(self) -> list[CorpusItem]:
        return [it for it in self.items if it.label]

    @property
    def nonwitnesses(self) -> list[CorpusItem]:
        return [it for it in self.items if not it.label]

    def summary(self) -> dict:
        return {"total": len(self.items), "witness": len(self.witnesses),
                "nonwitness": len(self.nonwitnesses), "scope": dict(self.scope),
                "features": len(self.feature_names)}

    def as_dict(self):
        return {"schema": "corpus/v1", "scope": self.scope,
                "feature_names": self.feature_names, "notes": self.notes,
                "summary": self.summary(),
                "items": [it.as_dict() for it in self.items]}

    def save(self, path: str):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(self.as_dict(), f, ensure_ascii=False, indent=1)

    @classmethod
    def from_dict(cls, d: dict) -> "Corpus":
        def restore_feature(value):
            # 어휘의 tuple 값은 JSON에서 list가 된다. VALUE_KINDS에는 list가 없으므로
            # feature 값 안의 list를 재귀적으로 tuple로 복원해 hash/정렬 계약을 지킨다.
            if isinstance(value, list):
                return tuple(restore_feature(v) for v in value)
            if isinstance(value, dict):
                return {k: restore_feature(v) for k, v in value.items()}
            return value

        items = []
        for raw in d["items"]:
            item = dict(raw)
            item["features"] = {
                name: restore_feature(value)
                for name, value in item.get("features", {}).items()
            }
            items.append(CorpusItem(**item))
        return cls(scope=d["scope"], feature_names=d["feature_names"],
                   notes=d.get("notes", []), items=items)

    @classmethod
    def load(cls, path: str) -> "Corpus":
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls.from_dict(d)


def features_of(ch: Chirotope, names: list[str], *,
                with_label: bool | None = None) -> dict:
    """새 chirotope 의 특징벡터.

    라벨(`witness`)은 witness 를 전건으로 갖는 명제를 새 대상에서 다시 검사하는 데
    필요하므로 기본적으로 포함한다. `with_label=False` 로 끄면 궤도 계산(2^(n-1)
    마스크)을 건너뛰므로, 라벨을 쓰지 않는 명제를 대량으로 공격할 때 훨씬 빠르다."""
    if with_label is None:
        with_label = True
    feats = INV.evaluate(ch, [nm for nm in names if nm != INV.LABEL_NAME])
    if with_label:
        feats[INV.LABEL_NAME] = INV.label(ch)
    return feats


def build_corpus(chirotopes, scope: dict, *, feature_names: list[str] | None = None,
                 id_prefix: str = "c") -> Corpus:
    """검증된 chirotope 들에 불변량을 붙여 코퍼스를 만든다.
    라벨은 언제나 om_core 와 동치인 `invariants.label` 이 만든다 — 어휘가 아니라."""
    names = feature_names if feature_names is not None else INV.active_names()
    names = [nm for nm in names if nm != INV.LABEL_NAME]
    items: list[CorpusItem] = []
    for i, ch in enumerate(chirotopes):
        feats = features_of(ch, names)
        items.append(CorpusItem(id=f"{id_prefix}{i:05d}", chirotope=ch.to_dict(),
                                features=feats, label=feats[INV.LABEL_NAME]))
    corpus = Corpus(scope=dict(scope), items=items, feature_names=list(names))
    # None 이 섞인 불변량은 채굴에서 제외 (부분 정의된 양으로는 전칭 명제를 못 만든다)
    dropped = [nm for nm in names
               if any(it.features.get(nm) is None for it in items)]
    if dropped:
        corpus.feature_names = [nm for nm in names if nm not in dropped]
        corpus.notes.append(f"부분 정의라 채굴 제외: {sorted(dropped)}")
    n_w = sum(1 for it in items if it.label)
    if items and not scope.get("exhaustive"):
        frac = n_w / len(items)
        if frac < 0.15 or frac > 0.85:
            corpus.notes.append(
                f"표본 불균형: witness 비율 {frac:.0%}. 이 코퍼스는 전수가 아니라 "
                f"생성기 순서에 따른 표본이므로, 여기서 나온 통계는 모집단 비율이 "
                f"아니다 — 필요/충분 조건의 '판별력' 수치를 과신하지 말 것.")
    return corpus


# ═══════════════════════════ 원자 ═══════════════════════════
@dataclass(frozen=True)
class Atom:
    inv: str
    op: str
    value: object

    def holds(self, feats: dict) -> Optional[bool]:
        v = feats.get(self.inv, None)
        if v is None:
            return None
        try:
            return bool(_OPS[self.op](v, self.value))
        except TypeError:
            return None

    def text(self) -> str:
        if self.inv == INV.LABEL_NAME and self.op == "==":
            return "witness 이다" if self.value else "witness 가 아니다"
        if isinstance(self.value, bool):
            return f"{self.inv} = {'참' if self.value else '거짓'}"
        return f"{self.inv} {self.op} {self.value}"

    def dsl(self) -> str:
        return f"{self.inv} {self.op} {self.value!r}"

    def as_dict(self):
        v = self.value
        if isinstance(v, tuple):
            v = {"__tuple__": [list(x) if isinstance(x, tuple) else x for x in v]}
        return {"inv": self.inv, "op": self.op, "value": v}

    @classmethod
    def from_dict(cls, d):
        v = d["value"]
        if isinstance(v, dict) and "__tuple__" in v:
            v = tuple(tuple(x) if isinstance(x, list) else x for x in v["__tuple__"])
        return cls(d["inv"], d["op"], v)


LABEL_ATOM = Atom(INV.LABEL_NAME, "==", True)
NONLABEL_ATOM = Atom(INV.LABEL_NAME, "==", False)


def _candidate_atoms(corpus: Corpus, inv_name: str, *, max_thresholds: int = 6):
    """한 불변량에서 만들 수 있는 원자 후보. 값 종류에 따라 다르게 만든다."""
    kind = INV.REGISTRY[inv_name].value_kind if inv_name in INV.REGISTRY else "int"
    vals = [it.features[inv_name] for it in corpus.items]
    uniq = sorted({v for v in vals}, key=_sort_key)
    if len(uniq) < 2:
        return []
    out = []
    if kind == "bool":
        out += [Atom(inv_name, "==", True), Atom(inv_name, "==", False)]
    elif kind in ("int", "ratio"):
        for v in uniq[:max_thresholds * 2]:
            out.append(Atom(inv_name, "==", v))
        # 경계값 임계 — 값이 많을 때는 균등 표집
        cand = uniq if len(uniq) <= max_thresholds else [
            uniq[round(i * (len(uniq) - 1) / (max_thresholds - 1))]
            for i in range(max_thresholds)]
        for v in cand:
            out.append(Atom(inv_name, ">=", v))
            out.append(Atom(inv_name, "<=", v))
    else:                                       # tuple 등 순서 없는 값
        for v in uniq[:max_thresholds * 2]:
            out.append(Atom(inv_name, "==", v))
    return out


def _sort_key(v):
    if isinstance(v, bool):
        return (0, int(v))
    if isinstance(v, (int, float)):
        return (1, v)
    return (2, str(v))


# ═══════════════════════════ 추측 ═══════════════════════════
@dataclass
class Conjecture:
    id: str
    form: str                        # "necessary" | "sufficient" | "equivalence" | "implication"
    antecedent: list                 # Atom 목록 (논리곱)
    consequent: Atom
    scope: dict
    support: dict                    # 관찰 통계
    invariance: str
    status: str = MINED
    evidence: dict = field(default_factory=dict)   # 반증/전수 결과
    score: float = 0.0
    notes: list = field(default_factory=list)

    # ---- 재평가 ----
    def antecedent_holds(self, feats: dict) -> Optional[bool]:
        vals = [a.holds(feats) for a in self.antecedent]
        if any(v is None for v in vals):
            return None
        return all(vals)

    def check(self, feats: dict) -> Optional[bool]:
        """이 특징벡터에서 명제가 성립하는가. None = 판정 불가(값 없음).
        전건이 거짓이면 공허하게 참."""
        a = self.antecedent_holds(feats)
        if a is None:
            return None
        if not a:
            return True
        c = self.consequent.holds(feats)
        return None if c is None else c

    def is_counterexample(self, feats: dict) -> bool:
        return self.check(feats) is False

    # ---- 표현 ----
    def text(self) -> str:
        lhs = " 그리고 ".join(a.text() for a in self.antecedent) or "항상"
        return f"({lhs}) ⟹ ({self.consequent.text()})"

    def dsl(self) -> str:
        lhs = " and ".join(a.dsl() for a in self.antecedent) or "true"
        return f"forall chi in scope: ({lhs}) -> ({self.consequent.dsl()})"

    def as_dict(self):
        return {"schema": SCHEMA_ID, "id": self.id, "form": self.form,
                "antecedent": [a.as_dict() for a in self.antecedent],
                "consequent": self.consequent.as_dict(),
                "scope": dict(self.scope), "support": dict(self.support),
                "invariance": self.invariance, "status": self.status,
                "evidence": dict(self.evidence), "score": self.score,
                "text": self.text(), "dsl": self.dsl(), "notes": list(self.notes)}

    @classmethod
    def from_dict(cls, d) -> "Conjecture":
        return cls(id=d["id"], form=d["form"],
                   antecedent=[Atom.from_dict(a) for a in d["antecedent"]],
                   consequent=Atom.from_dict(d["consequent"]),
                   scope=d["scope"], support=d["support"],
                   invariance=d["invariance"], status=d.get("status", MINED),
                   evidence=d.get("evidence", {}), score=d.get("score", 0.0),
                   notes=d.get("notes", []))


def _invariance_of(atoms: list[Atom]) -> str:
    """명제가 쓰는 불변량들의 분류에서 명제 전체의 등급을 유도한다.

    **미확인(None)은 보수적으로 강등한다.** 확인되지 않은 양을 궤도 불변으로
    가정하면, 사실은 대표원소에만 해당하는 성질이 'witness 의 특징짓기'로
    승격되는 오류가 생긴다 — 이 프로젝트에서 가장 위험한 종류의 거짓 결론이다.
    따라서 명시적으로 True 로 확인된 것만 상위 등급을 받는다."""
    grade = ORBIT_INVARIANT
    for a in atoms:
        inv = INV.REGISTRY.get(a.inv)
        if inv is None or inv.relabel_invariant is not True:
            return LABEL_DEPENDENT
        if inv.reorient_invariant is not True:
            grade = REPRESENTATIVE_DEPENDENT
    return grade


# ═══════════════════════════ 채굴 ═══════════════════════════
def mine(corpus: Corpus, *, min_support: int = 3, max_conjectures: int = 60,
         include_nonlabel_implications: bool = True,
         drop_label_dependent: bool = True) -> list[Conjecture]:
    """코퍼스에서 명제를 채굴한다. 반환은 점수 내림차순.

    채굴하는 형태:
      necessary   : witness ⟹ A            (witness 의 필요조건)
      sufficient  : A ⟹ witness            (witness 의 충분조건)
      equivalence : A ⟺ witness            (양방향 전부 성립)
      implication : A ⟹ B  (라벨 무관)      (구조 자체에 대한 보조정리 후보)

    반드시 만족해야 하는 조건 (쓰레기 명제 차단):
      · 전건이 코퍼스에서 min_support 개 이상 참 (공허한 전칭 금지)
      · 후건이 코퍼스에서 항상 참이 아님 (자명한 명제 금지)
      · 같은 진리벡터를 갖는 원자는 하나로 묶음 (중복 명제 금지)
    """
    items = corpus.items
    if not items:
        return []
    n_wit = len(corpus.witnesses)
    n_non = len(corpus.nonwitnesses)

    # 1) 원자 생성 + 진리벡터 계산 + 진리벡터로 중복 제거
    atoms: list[Atom] = []
    for nm in corpus.feature_names:
        # witness 의 정의를 다시 쓴 양(num_convex_reorientations, convex_tope_ratio)
        # 은 어떤 명제에도 쓰지 않는다 — 라벨과의 함의는 물론이고 다른 양과의
        # 함의도 '정의를 우회한 동어반복'이 되기 쉽다. 이 양들은 근접 실패 정렬과
        # 보고서에서만 쓰인다.
        inv = INV.REGISTRY.get(nm)
        if inv is not None and inv.defines_label:
            continue
        atoms.extend(_candidate_atoms(corpus, nm))
    truth: dict[Atom, tuple] = {}
    by_vector: dict[tuple, list[Atom]] = {}
    for a in atoms:
        vec = tuple(a.holds(it.features) for it in items)
        if any(v is None for v in vec):
            continue
        cnt = sum(vec)
        if cnt == 0 or cnt == len(items):        # 항상 거짓/항상 참인 원자는 무의미
            continue
        truth[a] = vec
        by_vector.setdefault(vec, []).append(a)

    # 각 진리벡터의 대표: 궤도 불변 > 재배향 의존 > 이름 의존, 그 다음 이름 짧은 순
    def rep_rank(a: Atom):
        g = _invariance_of([a])
        order = {ORBIT_INVARIANT: 0, REPRESENTATIVE_DEPENDENT: 1, LABEL_DEPENDENT: 2}[g]
        return (order, len(a.inv), a.inv, str(a.op), str(a.value))

    reps: list[Atom] = []
    equiv_groups: dict[Atom, list[Atom]] = {}
    for vec, group in by_vector.items():
        group_sorted = sorted(group, key=rep_rank)
        rep = group_sorted[0]
        reps.append(rep)
        equiv_groups[rep] = group_sorted[1:]

    label_vec = tuple(it.label for it in items)
    out: list[Conjecture] = []

    def add(form, ante: list[Atom], cons: Atom, support: dict, notes=None):
        grade = _invariance_of(ante + [cons])
        if drop_label_dependent and grade == LABEL_DEPENDENT:
            return
        cj = Conjecture(id=f"cj-{uuid.uuid4().hex[:8]}", form=form,
                        antecedent=list(ante), consequent=cons,
                        scope=dict(corpus.scope), support=support,
                        invariance=grade, notes=list(notes or []))
        eq = equiv_groups.get(cons, [])
        if eq:
            cj.notes.append("코퍼스에서 후건과 진리값이 같은 다른 표현: "
                            + ", ".join(a.text() for a in eq[:4]))
        out.append(cj)

    # 2) witness 의 필요조건 / 충분조건 / 동치
    if n_wit >= min_support and n_non >= 1:
        for a in reps:
            if a.inv == INV.LABEL_NAME:
                continue
            vec = truth[a]
            # 필요조건: witness ⟹ a
            nec = all(v for v, lab in zip(vec, label_vec) if lab)
            # 충분조건: a ⟹ witness
            suf = all(lab for v, lab in zip(vec, label_vec) if v)
            n_a = sum(vec)
            n_a_non = sum(1 for v, lab in zip(vec, label_vec) if v and not lab)
            if nec and suf:
                add("equivalence", [LABEL_ATOM], a,
                    {"witness": n_wit, "nonwitness": n_non,
                     "antecedent_true": n_a,
                     "discrimination": 1.0, "coverage": 1.0},
                    notes=["양방향 모두 코퍼스에서 성립 — 이 범위에서 witness 의 특징짓기 후보"])
            elif nec:
                disc = 1.0 - (n_a_non / n_non if n_non else 0.0)
                add("necessary", [LABEL_ATOM], a,
                    {"witness": n_wit, "nonwitness": n_non,
                     "nonwitness_also_satisfying": n_a_non,
                     "discrimination": round(disc, 4)})
            elif suf and n_a >= min_support:
                add("sufficient", [a], LABEL_ATOM,
                    {"witness": n_wit, "nonwitness": n_non,
                     "antecedent_true": n_a,
                     "coverage": round(n_a / n_wit, 4) if n_wit else 0.0})

    # 3) 라벨과 무관한 구조 함의 A ⟹ B (보조정리 후보)
    if include_nonlabel_implications:
        pool = [a for a in reps if a.inv != INV.LABEL_NAME]
        for a in pool:
            va = truth[a]
            na = sum(va)
            if na < min_support:
                continue
            for b in pool:
                if b is a or b.inv == a.inv:
                    continue
                vb = truth[b]
                if sum(vb) == len(items):
                    continue
                if all((not x) or y for x, y in zip(va, vb)):
                    # 역이 성립하면 위에서 동치로 별도 처리되므로 중복 방지
                    if all((not y) or x for x, y in zip(va, vb)):
                        if rep_rank(a) > rep_rank(b):
                            continue
                        form = "equivalence"
                    else:
                        form = "implication"
                    add(form, [a], b,
                        {"antecedent_true": na, "consequent_true": sum(vb),
                         "total": len(items)})

    # 4) 점수: 궤도 불변 우선 → 판별력/피복률 → 지지 표본 수 → 단순함
    grade_bonus = {ORBIT_INVARIANT: 2.0, REPRESENTATIVE_DEPENDENT: 0.5,
                   LABEL_DEPENDENT: 0.0}
    form_bonus = {"equivalence": 2.0, "necessary": 1.2, "sufficient": 1.2,
                  "implication": 0.6}
    for cj in out:
        s = grade_bonus[cj.invariance] + form_bonus.get(cj.form, 0.0)
        s += float(cj.support.get("discrimination", 0.0))
        s += float(cj.support.get("coverage", 0.0))
        s += min(1.0, cj.support.get("antecedent_true", 0) / max(1, len(items)))
        s -= 0.1 * len(cj.antecedent)
        cj.score = round(s, 4)

    out.sort(key=lambda c: (-c.score, c.text()))
    return out[:max_conjectures]


def report_markdown(corpus: Corpus, conjectures: list[Conjecture]) -> str:
    """사람이 읽는 요약 — 실험 폴더와 프롬프트에 그대로 들어간다."""
    s = corpus.summary()
    lines = [
        "# 추측 채굴 보고",
        "",
        f"- 범위(scope): `{json.dumps(corpus.scope, ensure_ascii=False)}`",
        f"- 표본: 전체 {s['total']} (witness {s['witness']} / non-witness {s['nonwitness']})",
        f"- 사용한 불변량 {s['features']}개",
    ]
    for note in corpus.notes:
        lines.append(f"- 주의: {note}")
    lines += ["", "> 아래는 전부 **관찰(MINED)** 이며 증명이 아니다. "
              "`falsify.py` 를 통과하기 전에는 어떤 것도 정리로 인용하지 말 것.", ""]

    by_form: dict[str, list[Conjecture]] = {}
    for cj in conjectures:
        by_form.setdefault(cj.form, []).append(cj)
    titles = {"equivalence": "동치 후보 (witness 의 특징짓기)",
              "necessary": "witness 의 필요조건",
              "sufficient": "witness 의 충분조건",
              "implication": "구조 함의 (보조정리 후보)"}
    for form in ("equivalence", "necessary", "sufficient", "implication"):
        group = by_form.get(form)
        if not group:
            continue
        lines += [f"## {titles[form]} ({len(group)}건)", ""]
        for cj in group:
            lines.append(f"- **{cj.id}** `[{cj.invariance}]` `{cj.status}` "
                         f"(score {cj.score})")
            lines.append(f"  - {cj.text()}")
            lines.append(f"  - 지지: `{json.dumps(cj.support, ensure_ascii=False)}`")
            if cj.evidence:
                lines.append(f"  - 반증 시도: `{json.dumps(cj.evidence, ensure_ascii=False)}`")
            for nt in cj.notes:
                lines.append(f"  - 비고: {nt}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from console import enable_utf8_stdout
    from generator import generate_backtracking
    from om_core import mcmullen_evaluate

    enable_utf8_stdout()

    # (6,3) 전수 일부 — witness 와 non-witness 가 모두 섞이는 범위
    chs = list(generate_backtracking(6, 3, dedup=False, max_candidates=200,
                                     max_nodes=600_000))
    corpus = build_corpus(chs, {"n": 6, "r": 3, "om_class": "uniform",
                                "backend": "backtracking", "exhaustive": False,
                                "how": "generate_backtracking(6,3,max=200)"})
    print("코퍼스:", corpus.summary())
    assert corpus.summary()["witness"] > 0 and corpus.summary()["nonwitness"] > 0

    # tuple 불변량이 JSON list로 바뀌어도 로드 후 다시 채굴할 수 있어야 한다.
    corpus_rt = Corpus.from_dict(json.loads(json.dumps(corpus.as_dict(), ensure_ascii=False)))
    assert isinstance(corpus_rt.items[0].features["circuit_balance_profile"], tuple)
    assert mine(corpus_rt, min_support=3, max_conjectures=4)
    print("코퍼스 직렬화 왕복 + 재채굴 OK")

    # 라벨이 om_core 와 일치 (코퍼스 구축이 판정을 바꾸지 않음)
    for it in corpus.items[:40]:
        ch = Chirotope.from_dict(it.chirotope)
        assert it.label == mcmullen_evaluate(ch)["witness"]
    print("코퍼스 라벨 <-> om_core 일치 OK")

    cjs = mine(corpus, min_support=3)
    print(f"채굴된 추측 {len(cjs)}건")
    for cj in cjs[:6]:
        print(f"  [{cj.invariance:24}] {cj.form:11} score={cj.score:5} {cj.text()}")

    # (1) 채굴된 명제는 코퍼스 전체에서 실제로 반례가 없어야 한다 (채굴기 자체의 무결성)
    for cj in cjs:
        for it in corpus.items:
            assert not cj.is_counterexample(it.features), (cj.text(), it.id)
    print("채굴 무결성 OK — 모든 명제가 코퍼스에서 반례 0")

    # (2) 직렬화 왕복이 명제의 의미를 보존하는가
    for cj in cjs[:10]:
        rt = Conjecture.from_dict(json.loads(json.dumps(cj.as_dict(), ensure_ascii=False)))
        for it in corpus.items[:30]:
            assert rt.check(it.features) == cj.check(it.features)
    print("추측 직렬화 왕복 OK")

    # (3) 등급 규율: witness 와의 '동치'는 궤도 불변 명제에서만 나올 수 있다.
    #     재배향 의존 양(acyclic 등)이 witness 와 동치로 승격되면 그건 오류다.
    for cj in cjs:
        if cj.form == "equivalence" and INV.LABEL_NAME in (
                [a.inv for a in cj.antecedent] + [cj.consequent.inv]):
            assert cj.invariance == ORBIT_INVARIANT, \
                f"재배향 의존 양이 witness 와 동치로 승격됨: {cj.text()}"
    print("등급 규율 OK (witness 동치는 궤도 불변 명제만)")

    # (4) 일부러 틀린 명제를 만들어 반례 탐지가 실제로 작동하는지
    bogus = Conjecture(id="cj-bogus", form="necessary", antecedent=[LABEL_ATOM],
                       consequent=Atom("num_singleton_circuits", "==", -1),
                       scope=corpus.scope, support={}, invariance=ORBIT_INVARIANT)
    assert any(bogus.is_counterexample(it.features) for it in corpus.witnesses)
    print("반례 탐지 OK (거짓 명제는 즉시 반례가 잡힘)")

    md = report_markdown(corpus, cjs)
    assert "MINED" in md and "증명이 아니다" in md
    print("보고서 생성 OK")
    print("conjecture core-contract assertions OK")
