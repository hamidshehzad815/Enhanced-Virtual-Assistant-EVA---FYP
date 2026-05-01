param(
    [switch]$Start
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name, [string]$InstallHint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command '$Name'. $InstallHint"
    }
}

function Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "Eva_Backend_Server"
$aiDir = Join-Path $root "Eva_AI_Server"
$aiVenvDir = Join-Path $aiDir ".venv"
$aiVenvPython = Join-Path $aiVenvDir "Scripts\python.exe"

Step "Checking required tools"
Require-Command -Name "node" -InstallHint "Install Node.js 18+."
Require-Command -Name "npm" -InstallHint "Install npm with Node.js."
Require-Command -Name "python" -InstallHint "Install Python 3.11+ and add it to PATH."
Require-Command -Name "docker" -InstallHint "Install Docker Desktop for Duckling."

Step "Installing backend dependencies"
Push-Location $backendDir
if (Test-Path "package-lock.json") {
    npm ci
} else {
    npm install
}
Pop-Location

Step "Preparing AI virtual environment"
if (-not (Test-Path $aiVenvPython)) {
    Push-Location $aiDir
    python -m venv .venv
    Pop-Location
}

Step "Installing AI dependencies"
& $aiVenvPython -m pip install --upgrade pip
& $aiVenvPython -m pip install -r (Join-Path $aiDir "requirements.txt")

Step "Environment file check"
if (-not (Test-Path (Join-Path $backendDir ".env"))) {
    Write-Warning "Eva_Backend_Server/.env is missing."
}
if (-not (Test-Path (Join-Path $aiDir ".env"))) {
    Write-Warning "Eva_AI_Server/.env is missing."
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "Start commands:"
Write-Host "1) MongoDB: mongod --dbpath <YOUR_DB_PATH>"
Write-Host "2) Duckling: docker run --rm -p 8000:8000 rasa/duckling"
Write-Host "3) Backend:  cd Eva_Backend_Server; npm run dev"
Write-Host "4) AI:       cd Eva_AI_Server; .\.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload"

if ($Start) {
    Step "Starting Duckling, Backend, and AI in separate windows"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "docker run --rm -p 8000:8000 rasa/duckling"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backendDir'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$aiDir'; .\.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload"
    Write-Host "Services started. Make sure MongoDB is running."
}
