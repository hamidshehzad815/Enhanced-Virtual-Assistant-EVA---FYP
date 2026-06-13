# Sync Eva_AI_Server into a cloned Hugging Face Space repo, then push from that folder.
# Usage:
#   .\sync-to-space.ps1 -SpaceDir "D:\FYP_20March\eva-ai-server"
param(
    [Parameter(Mandatory = $true)]
    [string]$SpaceDir
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Src = $Root
$Deploy = $PSScriptRoot

if (-not (Test-Path (Join-Path $SpaceDir ".git"))) {
    throw "SpaceDir is not a git repo. Clone first: git clone https://huggingface.co/spaces/hamidshehzad/eva-ai-server"
}

Write-Host "Copying Eva_AI_Server source -> $SpaceDir"
$excludeNames = @(
    ".venv", "__pycache__", "tests", "testModels", "scripts", "docs", "deploy", ".git",
    ".env", ".DS_Store", "models"
)
Get-ChildItem -Path $Src -Force | Where-Object {
    $excludeNames -notcontains $_.Name
} | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $SpaceDir -Recurse -Force
}

# Never ship local secrets into the Space repo
$envFile = Join-Path $SpaceDir ".env"
if (Test-Path $envFile) { Remove-Item $envFile -Force }

Get-ChildItem -Path $SpaceDir -Recurse -Filter "._*" -File -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Force }

Copy-Item (Join-Path $Deploy "start.sh") $SpaceDir -Force
Copy-Item (Join-Path $Deploy "Dockerfile") $SpaceDir -Force
Copy-Item (Join-Path $Deploy "requirements-hf.txt") $SpaceDir -Force
Copy-Item (Join-Path $Deploy "README.md") $SpaceDir -Force
Copy-Item (Join-Path $Deploy ".dockerignore") $SpaceDir -Force
Copy-Item (Join-Path $Deploy ".gitattributes") $SpaceDir -Force
Copy-Item (Join-Path $Deploy ".gitignore") $SpaceDir -Force

# Remove template files from HF default scaffold
$templateApp = Join-Path $SpaceDir "app.py"
if (Test-Path $templateApp) { Remove-Item $templateApp -Force }

Write-Host "Done. Next steps in $SpaceDir :"
Write-Host "  git lfs install"
Write-Host "  git add ."
Write-Host "  git commit -m 'Deploy EVA AI server'"
Write-Host "  git push"
