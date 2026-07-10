# scripts/setup.ps1
# Windows PowerShell 용 최초 설치 스크립트.
# 저장소 루트에서 실행:  .\scripts\setup.ps1
#
# 하는 일: (1) 가상환경 .venv 생성  (2) 패키지 + 전체 옵션 의존성 설치
#         (3) 코어 검증기 자체 테스트로 설치 확인

$ErrorActionPreference = "Stop"

Write-Host "== 1) 가상환경 생성 (.venv) ==" -ForegroundColor Cyan
python -m venv .venv

Write-Host "== 2) 가상환경 활성화 ==" -ForegroundColor Cyan
. .\.venv\Scripts\Activate.ps1

Write-Host "== 3) pip 업그레이드 ==" -ForegroundColor Cyan
python -m pip install --upgrade pip

Write-Host "== 4) 패키지 설치 (UI + config + z3 + llm 전부 포함) ==" -ForegroundColor Cyan
pip install -e ".[all]"

Write-Host "== 5) 설치 확인: 코어 검증기 자체 테스트 ==" -ForegroundColor Cyan
python om_core.py

Write-Host ""
Write-Host "설치 완료." -ForegroundColor Green
Write-Host "다음에 새 터미널을 열 때는 이 명령으로 가상환경만 다시 켜면 됩니다:"
Write-Host "    .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "바로 실행해 보려면:"
Write-Host "    python run.py --config config.example.yaml"
Write-Host "    streamlit run dashboard.py"
