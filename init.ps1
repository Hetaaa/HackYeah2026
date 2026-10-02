<#
.SYNOPSIS
    Sets up the backend environment: uv, Python 3.12, dependencies, .env, then runs lint + tests.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\init.ps1
    powershell -ExecutionPolicy Bypass -File .\init.ps1 -SkipChecks
#>
param(
    [switch]$SkipChecks
)

$ErrorActionPreference = "Stop"
$Backend = Join-Path $PSScriptRoot "backend"

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Native([scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command"
    }
}

Write-Step "Checking uv"
$UvDir = Join-Path $env:USERPROFILE ".local\bin"
$UvWasOnPath = [bool](Get-Command uv -ErrorAction SilentlyContinue)
if (-not $UvWasOnPath) {
    if (-not (Test-Path (Join-Path $UvDir "uv.exe"))) {
        Write-Step "uv not found, installing with the official installer"
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
    # Make uv usable in this session; the user PATH only reaches newly started apps.
    $env:Path = "$UvDir;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv not found in $UvDir after installation."
    }
}

# Persist uv's directory in the user PATH (the installer normally does this; make sure).
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $UvWasOnPath -and ($UserPath -split ";") -notcontains $UvDir) {
    Write-Step "Adding $UvDir to the user PATH"
    [Environment]::SetEnvironmentVariable("Path", "$UvDir;$UserPath", "User")
}
Invoke-Native { uv --version }

Push-Location $Backend
try {
    Write-Step "Installing Python 3.12 and dependencies (uv sync)"
    Invoke-Native { uv sync }

    if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
        Write-Step "Creating backend/.env from .env.example"
        Copy-Item ".env.example" ".env"
    }

    if (-not $SkipChecks) {
        Write-Step "Running lint and tests"
        Invoke-Native { uv run ruff check . }
        Invoke-Native { uv run pytest -q }
    }
}
finally {
    Pop-Location
}

Write-Step "Optional tools"
foreach ($tool in @("docker", "node")) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) {
        Write-Host "    $tool found"
    }
    else {
        Write-Host "    $tool not found (optional: docker for image builds, node for the frontend)" -ForegroundColor Yellow
    }
}

if (-not $UvWasOnPath) {
    Write-Host ""
    Write-Host "uv is in your user PATH, but this terminal still has the old PATH." -ForegroundColor Yellow
    Write-Host "Restart VS Code completely (all windows), or run in this terminal:" -ForegroundColor Yellow
    Write-Host "    `$env:Path = `"`$env:USERPROFILE\.local\bin;`$env:Path`""
}

Write-Host ""
Write-Host "Done. Start the API:" -ForegroundColor Green
Write-Host "    cd backend; uv run uvicorn app.main:app --reload"
Write-Host "    http://localhost:8000/docs"
