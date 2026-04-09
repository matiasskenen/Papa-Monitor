# packaging/build-monitor.ps1
# ============================================================
# Build de monitor.exe con estructura organizada
# Uso: .\packaging\build-monitor.ps1 [version]
# ============================================================

param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

$VersionFile = Join-Path $Root "public\version.txt"
$CurrentVersion = (Get-Content $VersionFile -Raw).Trim()
Write-Host "Versión actual: $CurrentVersion" -ForegroundColor Cyan

if ($Version -eq "") {
    $parts = $CurrentVersion.Split(".")
    $patch = [int]$parts[2] + 1
    $Version = "$($parts[0]).$($parts[1]).$patch"
}

Write-Host "Nueva versión: $Version" -ForegroundColor Green

Set-Content -Path $VersionFile -Value $Version -NoNewline
Write-Host "[1/5] version.txt actualizado a $Version" -ForegroundColor Yellow

$BundledVersionFile = Join-Path $Root "version.txt"
Set-Content -Path $BundledVersionFile -Value $Version -NoNewline
Write-Host "[2/5] version.txt copiado a raíz del proyecto" -ForegroundColor Yellow

Write-Host "[3/5] Compilando con PyInstaller..." -ForegroundColor Yellow
$SpecFile = Join-Path $Root "packaging\specs\monitor.spec"
& pyinstaller $SpecFile --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller falló." -ForegroundColor Red
    exit 1
}

$ExePath = Join-Path $Root "dist\monitor.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: dist\monitor.exe no encontrado." -ForegroundColor Red
    exit 1
}

$ExeSize = (Get-Item $ExePath).Length / 1MB
Write-Host "[4/5] monitor.exe compilado correctamente ($([math]::Round($ExeSize, 1)) MB)" -ForegroundColor Yellow

$PublicExePath = Join-Path $Root "public\monitor.exe"
Copy-Item -Path $ExePath -Destination $PublicExePath -Force
Write-Host "[5/5] monitor.exe copiado a public\ (listo para deploy en Vercel)" -ForegroundColor Yellow

Remove-Item -Path $BundledVersionFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " BUILD COMPLETO: v$Version" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host " public\version.txt -> $Version"
Write-Host " public\monitor.exe -> $([math]::Round($ExeSize, 1)) MB"
