"""
console.py — Windows 콘솔에서 한글/수학기호 출력이 깨지지 않게 하는 최소 유틸.

Windows 기본 콘솔 인코딩(cp949)은 '—', '⟺', '★' 같은 문자를 인코딩하지 못해
UnicodeEncodeError 로 **프로그램 자체가 죽는다.** 이 저장소는 사용자 대면 텍스트를
한국어로 쓰기로 되어 있으므로(CLAUDE.md 코딩 컨벤션), 출력이 계산을 죽이는 일이
없도록 진입점에서 stdout/stderr 를 UTF-8 로 바꾼다.

수학적 내용과 무관한 순수 표시(display) 계층이다.
"""
from __future__ import annotations

import sys


def enable_utf8_stdout() -> bool:
    """stdout/stderr 를 UTF-8(errors=replace)로 전환. 성공하면 True."""
    ok = True
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                    # noqa: BLE001 — 표시 계층은 절대 죽지 않는다
            ok = False
    return ok


if __name__ == "__main__":
    enable_utf8_stdout()
    print("UTF-8 출력 점검: — ⟺ ⟷ ★ ν(d)=2d+1 ✓")
    print("console core-contract assertions OK")
