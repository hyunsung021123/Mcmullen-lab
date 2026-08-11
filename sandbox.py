"""
sandbox.py — LLM 이 작성한 '불변량 코드'를 제한 환경에서 컴파일/검사한다.

## 왜 필요한가

기존 구조에서 LLM 의 행동 공간은 `criteria.REGISTRY` 에 사람이 미리 등록해 둔 이름
몇 개뿐이었다. 그래서 LLM 은 "새로운 수학적 성질"을 제안할 수 없고, 기껏해야 사람이
정의해 둔 성질을 켜고 끄는 제안만 할 수 있었다 — 창발적 제안이 원천적으로 불가능한
구조다 (docs/AUTONOMOUS_VERIFICATION_PIPELINE.md §1 의 실측 실패와 같은 원인).

이 모듈은 그 벽을 연다: LLM 이 **새 불변량을 파이썬 코드로 직접 써서** 어휘에 추가할
수 있게 하되, 그 코드가 할 수 있는 일을 문법 수준에서 제한한다.

## 신뢰 경계 (가장 중요)

LLM 이 작성한 코드는 **어떤 수학적 판정 권한도 갖지 못한다**:

  * witness 판정은 언제나 `om_core.mcmullen_evaluate` 만 한다. 샌드박스 코드는
    라벨을 만들 수 없고, 오직 '이미 검증된 대상에 숫자/불리언을 붙이는' 일만 한다.
  * 따라서 샌드박스 코드가 틀렸거나 악의적이어도 **틀린 정리가 참으로 승격되지
    않는다.** 최악의 경우 쓸모없는 추측이 생기고, 그 추측은 falsify.py 가 반증한다.
  * 샌드박스 코드는 `criteria` 의 `target` 모드로 쓸 수 없다 (invariants.py 에서 강제).

## 문법 제한 (거부하는 것)

  import / while / try / with / class / global / nonlocal / del / raise / yield /
  await / lambda 외 함수정의 / f-string 아닌 동적 코드 / `_` 로 시작하는 이름 /
  화이트리스트 밖 속성 접근 / 화이트리스트 밖 전역 이름 / AST 노드 수 상한 초과

`while` 을 금지하고 range/combinations/permutations/product의 전개 크기를 제한한다.
또한 Chirotope는 읽기 전용 facade로 전달되어 LLM 코드가 원본 부호를 바꿀 수 없다.

의존성: 표준 라이브러리만.
"""
from __future__ import annotations

import ast
from itertools import combinations, permutations, product
from collections import Counter
from math import comb, gcd, perm
from types import MappingProxyType
from typing import Callable

MAX_AST_NODES = 3000
MAX_SOURCE_CHARS = 8000
MAX_ITER_ITEMS = 1_000_000

# 허용 AST 노드 (여기에 없는 노드가 하나라도 있으면 거부)
_ALLOWED_NODES = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
    ast.Assign, ast.AugAssign, ast.Expr, ast.Pass, ast.Break, ast.Continue,
    ast.For, ast.If, ast.IfExp, ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp,
    ast.Call, ast.Name, ast.Load, ast.Store, ast.Del, ast.Constant,
    ast.Tuple, ast.List, ast.Dict, ast.Set, ast.Subscript, ast.Slice,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
    ast.Attribute, ast.Starred, ast.keyword, ast.NamedExpr, ast.Lambda,
    # 연산자
    ast.And, ast.Or, ast.Not, ast.Invert, ast.UAdd, ast.USub,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
}

# 허용 속성 이름 (Chirotope 의 읽기 전용 표면 + 표준 컨테이너 메서드)
_ALLOWED_ATTRS = {
    # Chirotope
    "n", "r", "signs", "chi", "circuit", "cocircuit", "reorient",
    "is_valid", "is_acyclic", "is_totally_cyclic", "is_convex_position",
    # 컨테이너
    "items", "values", "keys", "get", "add", "append", "extend", "update",
    "most_common", "elements", "count", "index", "union", "intersection",
    "difference", "issubset", "issuperset", "bit_count", "bit_length",
}

# 허용 전역 이름 (이 밖의 자유 변수는 거부)
_SAFE_BUILTINS: dict = {
    "len": len, "min": min, "max": max, "sum": sum, "sorted": sorted,
    "abs": abs, "any": any, "all": all, "range": range, "enumerate": enumerate,
    "zip": zip, "tuple": tuple, "list": list, "set": set, "frozenset": frozenset,
    "dict": dict, "int": int, "bool": bool, "str": str, "float": float,
    "map": map, "filter": filter, "reversed": reversed, "divmod": divmod,
    "pow": pow, "round": round, "True": True, "False": False, "None": None,
    "combinations": combinations, "permutations": permutations, "product": product,
    "Counter": Counter, "gcd": gcd,
}


class SandboxError(ValueError):
    """샌드박스 정책 위반. reason 에 사람이 읽을 수 있는 사유를 담는다."""

    def __init__(self, reason: str, lineno: int | None = None):
        self.reason = reason
        self.lineno = lineno
        super().__init__(f"{reason}" + (f" (line {lineno})" if lineno else ""))


def _guard_count(name: str, count: int) -> None:
    if count > MAX_ITER_ITEMS:
        raise SandboxError(
            f"{name} 반복 크기 {count}가 상한 {MAX_ITER_ITEMS}을 초과함")


def _safe_range(*args):
    out = range(*args)
    _guard_count("range", len(out))
    return out


def _safe_combinations(iterable, r):
    pool = tuple(iterable)
    count = comb(len(pool), r) if 0 <= r <= len(pool) else 0
    _guard_count("combinations", count)
    return combinations(pool, r)


def _safe_permutations(iterable, r=None):
    pool = tuple(iterable)
    size = len(pool) if r is None else r
    count = perm(len(pool), size) if 0 <= size <= len(pool) else 0
    _guard_count("permutations", count)
    return permutations(pool, r) if r is not None else permutations(pool)


def _safe_product(*iterables, repeat=1):
    pools = [tuple(it) for it in iterables] * repeat
    count = 1
    for pool in pools:
        count *= len(pool)
        _guard_count("product", count)
    return product(*pools)


class _ReadOnlyChirotope:
    """LLM 불변량에 노출하는 읽기 전용 Chirotope 표면.

    원본 객체와 signs dict를 직접 건네면 샌드박스 코드가 이후 라벨 계산을 변조할 수
    있다. 이 facade는 모든 읽기를 원본에 위임하되 재배향 결과도 다시 감싼다.
    """

    __slots__ = ("_ch", "_signs")

    def __init__(self, ch):
        object.__setattr__(self, "_ch", ch)
        object.__setattr__(self, "_signs", MappingProxyType(ch.signs))

    def __setattr__(self, name, value):
        raise TypeError("sandbox chirotope는 읽기 전용")

    @property
    def n(self):
        return self._ch.n

    @property
    def r(self):
        return self._ch.r

    @property
    def signs(self):
        return self._signs

    def chi(self, idx):
        return self._ch.chi(idx)

    def circuit(self, support):
        return self._ch.circuit(support)

    def cocircuit(self, hyperplane):
        return self._ch.cocircuit(hyperplane)

    def reorient(self, flip):
        return _ReadOnlyChirotope(self._ch.reorient(flip))

    def is_valid(self):
        return self._ch.is_valid()

    def is_acyclic(self):
        return self._ch.is_acyclic()

    def is_totally_cyclic(self):
        return self._ch.is_totally_cyclic()

    def is_convex_position(self):
        return self._ch.is_convex_position()


# 정의 순서상 기본 화이트리스트를 만든 뒤 bounded 버전으로 교체한다.
_SAFE_BUILTINS.update({
    "range": _safe_range,
    "combinations": _safe_combinations,
    "permutations": _safe_permutations,
    "product": _safe_product,
})


def _check_ast(tree: ast.AST, func_name: str) -> None:
    count = 0
    for node in ast.walk(tree):
        count += 1
        if count > MAX_AST_NODES:
            raise SandboxError(f"AST 노드 수 상한 {MAX_AST_NODES} 초과 — 너무 복잡함")
        if type(node) not in _ALLOWED_NODES:
            raise SandboxError(f"허용되지 않은 문법 요소 {type(node).__name__}",
                               getattr(node, "lineno", None))
        if isinstance(node, ast.Attribute):
            if node.attr not in _ALLOWED_ATTRS:
                raise SandboxError(f"허용되지 않은 속성 접근 '.{node.attr}'",
                                   node.lineno)
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
                node.ctx, (ast.Store, ast.Del)):
            raise SandboxError("외부 객체의 속성/항목 변경 금지", node.lineno)
        if isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise SandboxError(f"'_' 로 시작하는 이름 사용 금지: {node.id}",
                                   node.lineno)
        if isinstance(node, ast.arg) and node.arg.startswith("_"):
            raise SandboxError(f"'_' 로 시작하는 인자명 금지: {node.arg}")

    body = tree.body
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef):
        raise SandboxError("최상위에는 함수 정의가 정확히 하나만 있어야 함")
    fn = body[0]
    if fn.name != func_name:
        raise SandboxError(f"함수 이름이 '{func_name}' 이어야 함 (실제: '{fn.name}')")
    a = fn.args
    if (len(a.args) != 1 or a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs
            or a.defaults):
        raise SandboxError("함수는 인자를 정확히 하나(chirotope)만 받아야 함")
    if fn.decorator_list:
        raise SandboxError("데코레이터 사용 금지")


def _check_free_names(tree: ast.AST) -> None:
    """전역에서 찾게 될 자유 이름이 전부 화이트리스트인지 정적으로 확인."""
    fn = tree.body[0]
    bound: set[str] = {fn.args.args[0].arg}
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.comprehension):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
        elif isinstance(node, ast.For):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    bound.add(t.id)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in bound and node.id not in _SAFE_BUILTINS:
                raise SandboxError(f"허용되지 않은 전역 이름 '{node.id}'. "
                                   f"사용 가능: {', '.join(sorted(_SAFE_BUILTINS))}",
                                   node.lineno)


def compile_invariant(source: str, func_name: str = "f") -> Callable:
    """제한 문법을 통과한 소스에서 함수 하나를 컴파일해 반환.

    반환된 함수는 `__builtins__` 가 비어 있는 전역에서 실행되므로, 화이트리스트에
    없는 어떤 이름도 런타임에 접근할 수 없다. 대표적인 조합 반복은 전개 크기를
    제한하고, 실제 소요 시간은 invariants.vet_invariant 가 추가로 실측한다."""
    if not isinstance(source, str) or not source.strip():
        raise SandboxError("빈 소스")
    if len(source) > MAX_SOURCE_CHARS:
        raise SandboxError(f"소스 길이 상한 {MAX_SOURCE_CHARS}자 초과")
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as e:
        raise SandboxError(f"문법 오류: {e.msg}", e.lineno) from None
    _check_ast(tree, func_name)
    _check_free_names(tree)

    glb: dict = {"__builtins__": {}}
    glb.update(_SAFE_BUILTINS)
    code = compile(tree, filename=f"<sandbox:{func_name}>", mode="exec")
    exec(code, glb)          # noqa: S102 — 위에서 문법·이름을 전부 검사한 코드만 도달
    raw_fn = glb[func_name]

    def guarded(ch):
        return raw_fn(_ReadOnlyChirotope(ch))

    guarded.sandbox_source = source
    guarded.__name__ = func_name
    return guarded


if __name__ == "__main__":
    from console import enable_utf8_stdout
    enable_utf8_stdout()
    from om_core import Chirotope

    quad = Chirotope.from_points([(0, 0), (2, 0), (2, 2), (0, 2)])

    # (1) 정상 케이스: 실제로 쓸 만한 불변량이 통과하고 올바른 값을 낸다.
    ok_src = (
        "def f(ch):\n"
        "    total = 0\n"
        "    for S in combinations(range(ch.n), ch.r + 1):\n"
        "        C = ch.circuit(S)\n"
        "        pos = sum(1 for v in C.values() if v > 0)\n"
        "        if min(pos, len(C) - pos) <= 1:\n"
        "            total = total + 1\n"
        "    return total\n")
    f = compile_invariant(ok_src)
    assert f(quad) == 0        # 볼록 사각형: unbalanced circuit 없음
    tri = Chirotope.from_points([(0, 0), (4, 0), (0, 4), (1, 1)])
    assert f(tri) == 1         # 내부점 하나 → singleton circuit 하나
    print("정상 불변량 컴파일/실행 OK")

    # (2) 거부 케이스 — 각각 어떤 정책에 걸리는지 고정한다.
    bad_cases = [
        ("import os\ndef f(ch):\n    return 1\n", "문법 요소"),
        ("def f(ch):\n    while True:\n        pass\n    return 1\n", "문법 요소"),
        ("def f(ch):\n    return open('x')\n", "전역 이름"),
        ("def f(ch):\n    return ch.__class__\n", "속성 접근"),
        ("def f(ch):\n    return eval('1')\n", "전역 이름"),
        ("def f(ch):\n    return __import__('os')\n", "'_' 로 시작"),
        ("def f(ch, k):\n    return 1\n", "인자를 정확히 하나"),
        ("def g(ch):\n    return 1\n", "함수 이름"),
        ("def f(ch):\n    return 1\ndef h(ch):\n    return 2\n", "정확히 하나"),
        ("def f(ch):\n    raise ValueError('x')\n", "문법 요소"),
        ("def f(ch):\n    return ch.signs\ndef f2(ch):\n    return 0\n", "정확히 하나"),
    ]
    for src, expect in bad_cases:
        try:
            compile_invariant(src)
        except SandboxError as e:
            assert expect in e.reason, (src, e.reason, expect)
        else:
            raise AssertionError(f"거부되어야 할 코드가 통과: {src!r}")
    print(f"거부 케이스 {len(bad_cases)}종 OK (import/while/eval/dunder/시그니처)")

    # (3) 런타임 격리: 통과한 코드도 builtins 에 닿지 못한다.
    esc = compile_invariant("def f(ch):\n    return len(str(ch.n))\n")
    assert esc(quad) == 1

    # (4) 원본 변조 차단: 직접 대입은 컴파일 단계, alias.update는 facade가 막는다.
    original = quad.signs[(0, 1, 2)]
    try:
        compile_invariant(
            "def f(ch):\n    ch.signs[(0,1,2)] = -ch.signs[(0,1,2)]\n    return 1\n")
        raise AssertionError("signs 직접 변조 코드가 통과함")
    except SandboxError as e:
        assert "변경 금지" in e.reason
    alias_mutation = compile_invariant(
        "def f(ch):\n    d = ch.signs\n    d.update({(0,1,2): -1})\n    return 1\n")
    try:
        alias_mutation(quad)
        raise AssertionError("mapping proxy 변조가 통과함")
    except (AttributeError, TypeError):
        pass
    assert quad.signs[(0, 1, 2)] == original

    # (5) 사후 시간 측정 전에 명백히 거대한 반복을 차단한다.
    huge = compile_invariant("def f(ch):\n    return sum(1 for i in range(1000001))\n")
    try:
        huge(quad)
        raise AssertionError("거대 반복이 통과함")
    except SandboxError as e:
        assert "반복 크기" in e.reason
    print("sandbox core-contract assertions OK (읽기 전용 facade / 반복 상한 포함)")
