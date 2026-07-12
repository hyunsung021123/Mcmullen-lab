<#
.SYNOPSIS
    로컬 Windows 클론을 GitHub `develop` 브랜치 기준으로 주기적으로 최신화한다.

.DESCRIPTION
    Windows 작업 스케줄러(Task Scheduler)에 등록해 사용하도록 만든 스크립트다
    (docs/AI_WORKFLOW.md §12 참고). Claude Code(클라우드)나 다른 AI가 GitHub의
    `develop`에 병합한 변경이, 사람이 수동으로 pull하기 전까지는 이 로컬 클론에
    반영되지 않는다는 문제(0007)를 완화한다.

    안전 보장 (아래 조건 중 하나라도 걸리면 아무 것도 바꾸지 않고 조용히 넘어간다):
    - fetch + `git pull --ff-only`만 수행한다. merge/rebase/force는 절대 쓰지 않는다.
    - 현재 체크아웃된 브랜치가 `develop`이 아니면 건드리지 않는다(다른 작업 브랜치에서
      작업 중일 때 임의로 브랜치를 바꾸지 않기 위함).
    - 커밋되지 않은 변경(untracked 포함)이 있으면 건드리지 않는다.
    - fast-forward가 불가능하면(로컬 develop이 origin/develop과 갈라져 있으면) 건드리지
      않는다 — 이 경우는 사람이 직접 봐야 하는 상황이라 스크립트가 임의로 처리하지 않는다.

.PARAMETER RepoPath
    로컬 클론 폴더의 전체 경로.

.PARAMETER LogPath
    실행 로그를 남길 파일 경로. 생략하면 RepoPath\autopull.log 를 사용한다.

.EXAMPLE
    powershell.exe -ExecutionPolicy Bypass -File local-autopull.ps1 -RepoPath "C:\Users\me\Mcmullen-lab"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [string]$LogPath = (Join-Path $RepoPath "autopull.log")
)

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

if (-not (Test-Path $RepoPath)) {
    Write-Log "error: RepoPath가 존재하지 않음 ($RepoPath)"
    exit 1
}

Set-Location $RepoPath

$currentBranch = (git rev-parse --abbrev-ref HEAD 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $currentBranch) {
    Write-Log "error: git 저장소가 아니거나 브랜치를 확인할 수 없음"
    exit 1
}
if ($currentBranch -ne "develop") {
    Write-Log "skip: 현재 브랜치가 develop이 아님 ($currentBranch)"
    exit 0
}

$dirty = git status --porcelain
if ($dirty) {
    Write-Log "skip: 커밋되지 않은 변경이 있어 건너뜀"
    exit 0
}

git fetch origin develop 2>&1 | Out-Null

$result = git pull --ff-only origin develop 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Log "ok: $result"
} else {
    Write-Log "skip: fast-forward 불가(로컬 develop이 origin/develop과 갈라짐) - $result"
}
