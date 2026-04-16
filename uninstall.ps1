# claude-persona uninstaller (Windows PowerShell)

$SkillDir = Join-Path $env:USERPROFILE ".claude\skills\persona"

Write-Host "This will remove claude-persona from $SkillDir"
$confirm = Read-Host "Continue? [y/N]"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled."
    exit 0
}

if (Test-Path $SkillDir) {
    Remove-Item -Recurse -Force $SkillDir
    Write-Host "[ok] claude-persona removed. Restart Claude Code to complete removal."
} else {
    Write-Host "[warn] claude-persona is not installed at $SkillDir"
}
