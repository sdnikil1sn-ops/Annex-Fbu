# =====================================================================
# ANNEX — release script (Phase 11)
# Windows mirror of scripts/release.sh: validate semver, bump the
# CHANGELOG.md [Unreleased] section into a dated section, commit, and
# create the annotated tag v<version>.
#
# Usage:
#   scripts\release.ps1 0.2.0             # bump + commit + tag v0.2.0
#   scripts\release.ps1 0.2.0 -DryRun     # preview only, changes nothing
#   scripts\release.ps1 0.2.0 -NoTag      # changelog bump only
# =====================================================================
param(
  [string]$Version = "",
  [switch]$DryRun,
  [switch]$NoTag
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not $Version) {
  Write-Error "version required (e.g. scripts\release.ps1 0.2.0)"
  exit 2
}

if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$') {
  Write-Error "invalid version '$Version' (expected semver, e.g. 0.2.0)"
  exit 2
}

$tag = "v$Version"
$today = Get-Date -Format "yyyy-MM-dd"
$changelog = "CHANGELOG.md"

# A release must point at a reproducible tree and a unique tag.
if (git status --porcelain) {
  Write-Error "working tree is not clean; commit or stash first"
  exit 1
}
if (git rev-parse --verify --quiet $tag) {
  Write-Error "tag '$tag' already exists"
  exit 1
}
if (-not (Test-Path $changelog) -or -not (Select-String -Path $changelog -Pattern '^## \[Unreleased\]' -Quiet)) {
  Write-Error "$changelog missing a [Unreleased] section"
  exit 1
}

Write-Host "ANNEX release $Version ($today)"

if ($DryRun) {
  Write-Host "[dry-run] would rewrite $changelog: [Unreleased] -> [$Version] - $today (+ new [Unreleased])"
  if (-not $NoTag) { Write-Host "[dry-run] would commit the bump and create annotated tag $tag" }
  exit 0
}

# Move [Unreleased] -> [<version>] - <date> and prepend a fresh section.
$content = [System.IO.File]::ReadAllText((Resolve-Path $changelog))
$pattern = '(?m)^## \[Unreleased\]'
$replacement = "## [Unreleased]`n`n## [$Version] - $today"
if ($content -notmatch $pattern) {
  Write-Error "unexpected changelog shape; [Unreleased] section not found"
  exit 1
}
$content = $content -replace $pattern, $replacement
[System.IO.File]::WriteAllText(
  (Resolve-Path $changelog),
  $content,
  (New-Object System.Text.UTF8Encoding($false))
)
Write-Host "[ok] $changelog updated"

if (-not $NoTag) {
  git add $changelog
  git commit -m "chore(repo): release $tag"
  git tag -a $tag -m "ANNEX release $tag"
  Write-Host "[ok] committed bump and created tag $tag"
}

Write-Host ""
Write-Host "Next steps (the release pipeline runs on the tag push):"
Write-Host "  git push origin main"
Write-Host "  git push origin $tag"
