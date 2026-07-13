@echo off
REM run_dashboard.bat — 바탕화면 바로가기로 더블클릭 한 번에 대시보드를 여는 스크립트.
REM 이 파일이 있는 위치(scripts\)의 부모 폴더가 저장소 루트라고 가정한다.
REM docs/AI_WORKFLOW.md §13 참고.

setlocal
cd /d "%~dp0.."

echo McMullen-OM Lab 대시보드를 시작합니다...
echo (이 창을 닫으면 대시보드도 함께 종료됩니다.)

streamlit run dashboard.py
if errorlevel 1 (
    echo.
    echo 실행에 실패했습니다. 아래를 확인하세요:
    echo   1^) Python이 설치되어 있고 PATH에 등록되어 있는지
    echo   2^) 저장소 폴더에서 "pip install -e .[ui]" 를 한 번 실행했는지
    pause
)
