#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve project root
$Root = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
Set-Location $Root

# Backend build
if (Get-Command uv -ErrorAction SilentlyContinue) {
  Write-Host '[1/5] Building backend wheel'
  Push-Location backend
  uv sync
  uv build --wheel -o dist
  Pop-Location
} else {
  Write-Warning 'uv is not installed; skipping backend build'
}

# Frontend build
if (Get-Command npm -ErrorAction SilentlyContinue) {
  Write-Host '[2/5] Building frontend assets'
  Push-Location frontend
  npm install
  npm run build
  Pop-Location
} else {
  Write-Warning 'npm is not installed; skipping frontend build'
}

# g2-ssr dependencies
if (Get-Command npm -ErrorAction SilentlyContinue) {
  Write-Host '[3/5] Installing g2-ssr dependencies'
  Push-Location g2-ssr
  npm install
  Pop-Location
}

# Collect artifacts
Write-Host '[4/5] Collecting build artifacts'
$Stage = Join-Path 'package' 'opt/sqlbot'
Remove-Item package -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path (Join-Path $Stage 'backend') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Stage 'frontend') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Stage 'g2-ssr') | Out-Null
Copy-Item backend/dist/*.whl (Join-Path $Stage 'backend') -ErrorAction SilentlyContinue
Copy-Item -Recurse frontend/dist (Join-Path $Stage 'frontend') -ErrorAction SilentlyContinue
Copy-Item -Recurse g2-ssr (Join-Path $Stage 'g2-ssr')
Copy-Item start.sh $Stage

# Build RPM if fpm is available
if (Get-Command fpm -ErrorAction SilentlyContinue) {
  Write-Host '[5/5] Building RPM via fpm'
  fpm -s dir -t rpm -n sqlbot -v 1.0.0 -C package opt/sqlbot
} else {
  Write-Warning 'fpm not found; skipping RPM build'
}

# Build Docker image
if (Get-Command docker -ErrorAction SilentlyContinue) {
  Write-Host 'Building Docker image sqlbot:latest'
  docker build -t sqlbot:latest .
} else {
  Write-Warning 'docker not installed; skipping image build'
}

Write-Host 'Done'
