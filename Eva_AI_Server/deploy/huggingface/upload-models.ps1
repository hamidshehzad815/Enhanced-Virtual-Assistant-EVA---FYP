# Upload Eva ML weights to a Hugging Face *Model* repo (separate from the Space).
# Model repos allow much larger files than the 1 GB Space repo limit.
#
# 1. Create repo: https://huggingface.co/new  -> name: eva-models, type: Model, Public
# 2. hf auth login   (paste your write token)
# 3. .\upload-models.ps1

param(
    [string]$ModelRepo = "hamidshehzad/eva-models",
    [string]$ModelsDir = "D:\FYP_20March\Eva_AI_Server\models"
)

$ErrorActionPreference = "Stop"

$hf = (Get-Command hf -ErrorAction SilentlyContinue)?.Source
if (-not $hf) {
    $hfDefault = Join-Path $env:USERPROFILE ".local\bin\hf.exe"
    if (Test-Path $hfDefault) {
        $hf = $hfDefault
    } else {
        Write-Host "Installing Hugging Face CLI..."
        powershell -ExecutionPolicy ByPass -c "irm https://hf.co/cli/install.ps1 | iex"
        $hf = Join-Path $env:USERPROFILE ".local\bin\hf.exe"
    }
}

if (-not (Test-Path $hf)) {
    throw "hf CLI not found. Close and reopen PowerShell, or run: & `"$env:USERPROFILE\.local\bin\hf.exe`" auth login"
}

Write-Host "Using hf: $hf"
Write-Host "Uploading $ModelsDir -> $ModelRepo"
Write-Host "Removing legacy folders: clf1, intent_classifier, ner_model, learning_ner"
& $hf upload $ModelRepo $ModelsDir . --repo-type model `
    --delete "clf1/**" `
    --delete "intent_classifier/**" `
    --delete "ner_model/**" `
    --delete "learning_ner/**" `
    --commit-message "Update EVA models (uncased distilbert) and remove legacy folders"

Write-Host "Done. Models URL: https://huggingface.co/$ModelRepo"
