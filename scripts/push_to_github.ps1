param(
    [Parameter(Mandatory = $true, HelpMessage = "GitHub repository HTTPS URL, e.g. https://github.com/username/qazaq-loc-qa.git")]
    [string]$RepoUrl,

    [string]$CommitMessage = "feat: Qazaq Loc QA full-stack localization QA platform"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git was not found! Install Git via 'winget install --id Git.Git -e' or https://git-scm.com/download/win"
}

if (-not (Test-Path ".git")) {
    Write-Host "[1/5] Initializing Git repository..." -ForegroundColor Cyan
    git init
    git branch -M main
}

Write-Host "[2/5] Staging files (.gitignore protects .env, *.db, and logs/)..." -ForegroundColor Cyan
git add .

# Safety check: ensure no .env or .db files are staged
$staged = git diff --cached --name-only
$forbidden = $staged | Where-Object { $_ -match "(^|/)\.env($|\.)" -and $_ -notmatch "\.env\.example$" -or $_ -match "\.(db|sqlite|sqlite3)$" }
if ($forbidden) {
    git reset
    Write-Error "SECURITY HALT: Secret or database file detected in staging: $($forbidden -join ', ')"
}

Write-Host "[3/5] Creating commit..." -ForegroundColor Cyan
$hasChanges = git status --porcelain
if ($hasChanges) {
    git commit -m $CommitMessage
} else {
    Write-Host "No uncommitted changes; using current HEAD." -ForegroundColor Yellow
}

Write-Host "[4/5] Configuring GitHub remote ($RepoUrl)..." -ForegroundColor Cyan
$existingRemote = git remote
if ($existingRemote -contains "origin") {
    git remote set-url origin $RepoUrl
} else {
    git remote add origin $RepoUrl
}

Write-Host "[5/5] Pushing to GitHub (main)..." -ForegroundColor Cyan
git push -u origin main
Write-Host "SUCCESS: Project pushed to GitHub!" -ForegroundColor Green
