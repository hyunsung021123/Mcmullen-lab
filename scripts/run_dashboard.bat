@echo off
chcp 65001 >nul
REM run_dashboard.bat — 바탕화면 바로가기로 더블클릭 한 번에 대시보드를 여는 스크립트.
REM 이 파일이 있는 위치(scripts\)의 부모 폴더가 저장소 루트라고 가정한다.
REM docs/AI_WORKFLOW.md §13 참고.
REM
REM chcp 65001: 콘솔 코드페이지를 UTF-8로 전환 — 이 파일이 UTF-8(BOM 없음)로
REM 저장돼 있어, 코드페이지를 안 바꾸면 한글이 깨진다(cmd.exe는 .bat 파일에
REM BOM이 있으면 첫 줄을 명령으로 잘못 파싱해 오류가 나므로 BOM 대신 이 방법을 쓴다).
REM
REM streamlit 대신 python -m streamlit: pip이 설치한 streamlit.exe가 있는 Scripts
REM 폴더가 PATH에 없어도, python 자체만 PATH에 있으면 동작한다.

setlocal
cd /d "%~dp0.."

echo McMullen-OM Lab 대시보드를 시작합니다...
echo (이 창을 닫으면 대시보드도 함께 종료됩니다.)

python -m streamlit run dashboard.py
if errorlevel 1 (
    echo.
    echo 실행에 실패했습니다. 아래를 확인하세요:
    echo   1^) Python이 설치되어 있고 PATH에 등록되어 있는지 ^(터미널에서 python --version^)
    echo   2^) 이 폴더에서 "python -m pip install streamlit pandas" 를 한 번 실행했는지
    pause
)
