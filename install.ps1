# claude-persona installer (Windows PowerShell)
# Installs the persona research skill to ~/.claude/skills/persona/
#
# One-command install:
#   irm https://raw.githubusercontent.com/takechanman1228/claude-persona/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$Version = "0.1.0"
$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\persona"
$RepoUrl = "https://github.com/takechanman1228/claude-persona"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=============================================="
Write-Host "  claude-persona installer"
Write-Host "  Decision-focused persona research for Claude Code"
Write-Host "=============================================="
Write-Host ""

# Check prerequisites
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Error: git is required but not installed." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "Error: python3 is required but not installed." -ForegroundColor Red
        exit 1
    }
}

$PythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

try {
    & $PythonCmd -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
} catch {
    $PyVer = & $PythonCmd --version 2>&1
    Write-Host "Error: Python 3.10+ is required. Found: $PyVer" -ForegroundColor Red
    exit 1
}

# Determine source directory (local clone or piped from web)
if ($ScriptDir -and (Test-Path (Join-Path $ScriptDir "skills\persona\SKILL.md"))) {
    $Src = $ScriptDir
    Write-Host "[ok] Installing from local source"
} else {
    $TempDir = Join-Path ([System.IO.Path]::GetTempPath()) "claude-persona-install"
    if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
    Write-Host "[..] Downloading $RepoUrl"
    git clone --depth 1 $RepoUrl $TempDir 2>$null
    $Src = $TempDir
    Write-Host "[ok] Downloaded repository"
}

# Install files
Write-Host "[..] Installing files into $SkillDir"
if (Test-Path $SkillDir) { Remove-Item -Recurse -Force $SkillDir }
New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null

Copy-Item "$Src\skills\persona\SKILL.md" "$SkillDir\SKILL.md" -Force
Copy-Item "$Src\CLAUDE.md" "$SkillDir\CLAUDE.md" -Force
Copy-Item "$Src\README.md" "$SkillDir\README.md" -Force
Copy-Item "$Src\CHANGELOG.md" "$SkillDir\CHANGELOG.md" -Force
Copy-Item "$Src\requirements.txt" "$SkillDir\requirements.txt" -Force
Copy-Item "$Src\scripts" "$SkillDir\scripts" -Recurse -Force
Copy-Item "$Src\references" "$SkillDir\references" -Recurse -Force
Copy-Item "$Src\templates" "$SkillDir\templates" -Recurse -Force
Copy-Item "$Src\demo" "$SkillDir\demo" -Recurse -Force
Copy-Item "$Src\docs" "$SkillDir\docs" -Recurse -Force
Copy-Item "$Src\assets" "$SkillDir\assets" -Recurse -Force

# Install Python dependencies
Write-Host "[..] Installing Python dependencies (best effort)"
try {
    & $PythonCmd -m pip install --user -r "$SkillDir\requirements.txt" 2>$null | Out-Null
    Write-Host "[ok] Python dependencies installed"
} catch {
    Write-Host "[warn] Could not install Python dependencies automatically." -ForegroundColor Yellow
    Write-Host "       Run manually:" -ForegroundColor Yellow
    Write-Host "       $PythonCmd -m pip install --user -r $SkillDir\requirements.txt" -ForegroundColor Yellow
}

# Cleanup temp directory
if ($TempDir -and (Test-Path $TempDir)) {
    Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[ok] claude-persona $Version installed"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Code"
Write-Host "  2. Run /persona concept-test Running shoes: 3 concepts"
Write-Host ""
Write-Host "Plugin users can also add the marketplace entry with:"
Write-Host "  /plugin marketplace add takechanman1228/claude-persona"
Write-Host "  /plugin install claude-persona@claude-persona"
