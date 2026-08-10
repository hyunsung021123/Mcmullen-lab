# Claude Code 부트스트랩 프롬프트

아래 내용을 그대로 복사해서, 저장소 폴더(`mcmullen_lab`)에서 `claude` 를 실행한 뒤
붙여넣으세요. (Claude Code 가 설치돼 있고, `gh` CLI 로 GitHub 로그인이 돼 있다고 가정합니다.
안 돼 있으면 Claude Code 가 먼저 `gh auth login` 을 안내할 것입니다.)

---

이 폴더(`mcmullen_lab/`)를 GitHub 저장소로 만들고, 로컬에서 바로 실행 가능한 상태로
세팅해줘. 순서대로 진행해줘:

1. **저장소 확인**: 이미 `CLAUDE.md`, `pyproject.toml`, `.gitignore`, `LICENSE`,
   `.github/workflows/ci.yml`, `scripts/setup.ps1`, `scripts/setup.sh` 가 들어있어.
   먼저 `CLAUDE.md` 를 읽고 이 프로젝트의 신뢰 모델(불변 조건)을 파악해줘. 이후 모든 작업에서
   이 불변 조건을 지켜줘.

2. **git 초기화 + 첫 커밋**:
   - 이미 `.git` 이 있으면 상태만 확인, 없으면 `git init`
   - `git add -A && git commit -m "Initial commit: McMullen-OM research lab"`
   - 커밋 전에 `.gitignore` 가 `results*.json`, `memory*.json`, `.venv/` 를 제대로
     걸러내는지 `git status` 로 확인해줘 (실행 산출물이 커밋되면 안 됨).

3. **GitHub 저장소 생성 + 푸시**:
   - `gh repo create` 로 새 저장소를 만들어줘 (이름은 나한테 물어보거나 `mcmullen-om-lab`
     같은 이름을 제안해줘). private/public 여부도 나한테 물어봐줘.
   - 만든 뒤 `git remote add origin ...` 하고 `git push -u origin main`.

4. **설치 검증**: 방금 만든 클론이 실제로 동작하는지, 별도 임시 디렉터리에 저장소를
   `git clone` 한 뒤 `scripts/setup.sh`(또는 내가 Windows 라면 그 안의 명령을 bash 로
   재현)를 실행해서 `pip install -e ".[all]"` 이 성공하고 `python om_core.py` 자체
   테스트가 통과하는지 확인해줘. 문제가 있으면 고쳐줘.

5. **CI 확인**: 푸시 후 GitHub Actions(`ci.yml`)가 실제로 통과하는지
   `gh run list` / `gh run watch` 로 확인해줘. 실패하면 로그를 보고 고쳐줘.

6. **README 최상단에 배지 추가**: CI 배지와 "Clone 후 3줄로 실행" 요약을
   README.md 맨 위에 추가해줘 (아래 로컬 실행 섹션과 중복되지 않게 짧게).

7. 다 되면 나한테 저장소 URL 과, 내가 다른 PC(Windows/PowerShell)에서 실행할 때
   그대로 칠 명령 3~4줄을 요약해줘.

작업 중 애매한 부분(저장소 이름, public/private, 원격 이름 등)은 진행하기 전에
반드시 나한테 먼저 물어봐줘.

---

## 이후 이 저장소에서 Claude Code 에게 자주 시킬 만한 작업 예시

- "criteria.py 에 새 이론적 성질을 추가하고, README §7 표에도 반영해줘"
- "d=5 탐색을 위해 om_classes.py 의 lawrence 소켓에 내 REOM 생성기를 연결해줘.
  생성기 코드는 이 파일이야: (붙여넣기)"
- "지난 실행의 memory.json 을 보고, 실패한 편향 중 재검토할 만한 게 있는지 분석해줘"
- "research_cycle.py 의 보고서에 라운드별 실패 사유 요약을 추가해줘"

Claude Code 는 `CLAUDE.md` 를 자동으로 읽으므로, 매번 신뢰 모델을 다시 설명할 필요는 없습니다.
