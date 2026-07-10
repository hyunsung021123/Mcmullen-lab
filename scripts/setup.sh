#!/usr/bin/env bash
# scripts/setup.sh — macOS/Linux 용 최초 설치 스크립트.
# 저장소 루트에서 실행:  bash scripts/setup.sh
set -euo pipefail

echo "== 1) 가상환경 생성 (.venv) =="
python3 -m venv .venv

echo "== 2) 가상환경 활성화 =="
source .venv/bin/activate

echo "== 3) pip 업그레이드 =="
python -m pip install --upgrade pip

echo "== 4) 패키지 설치 (UI + config + z3 + llm 전부 포함) =="
pip install -e ".[all]"

echo "== 5) 설치 확인: 코어 검증기 자체 테스트 =="
python om_core.py

echo ""
echo "설치 완료."
echo "다음에 새 터미널을 열 때는 이 명령으로 가상환경만 다시 켜면 됩니다:"
echo "    source .venv/bin/activate"
echo ""
echo "바로 실행해 보려면:"
echo "    python run.py --config config.example.yaml"
echo "    streamlit run dashboard.py"
