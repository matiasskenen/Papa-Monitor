# build.ps1
# ============================================================
# Script de build completo para PapaMonitor
# Uso: .\build.ps1 [version]
# Ejemplo: .\build.ps1 1.0.5
# Si no pasas version, hace bump automático del patch
# ============================================================

param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

# ----- Leer versión actual -----
$VersionFile = Join-Path $Root "public\version.txt"
$CurrentVersion = (Get-Content $VersionFile -Raw).Trim()
Write-Host "Versión actual: $CurrentVersion" -ForegroundColor Cyan

# ----- Determinar nueva versión -----
if ($Version -eq "") {
    $parts = $CurrentVersion.Split(".")
    $patch = [int]$parts[2] + 1
    $Version = "$($parts[0]).$($parts[1]).$patch"
}

Write-Host "Nueva versión: $Version" -ForegroundColor Green

# ----- Actualizar version.txt (fuente de verdad para el monitor) -----
Set-Content -Path $VersionFile -Value $Version -NoNewline
Write-Host "[1/5] version.txt actualizado a $Version" -ForegroundColor Yellow

# ----- Copiar version.txt a la carpeta del paquete para que PyInstaller lo incluya -----
$BundledVersionFile = Join-Path $Root "version.txt"
Set-Content -Path $BundledVersionFile -Value $Version -NoNewline
Write-Host "[2/5] version.txt copiado a raíz del proyecto" -ForegroundColor Yellow

# ----- Compilar con PyInstaller -----
Write-Host "[3/5] Compilando con PyInstaller..." -ForegroundColor Yellow
$SpecFile = Join-Path $Root "monitor.spec"

# Actualizar el .spec para incluir version.txt desde la raíz
& pyinstaller $SpecFile --noconfirm --clean

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller falló." -ForegroundColor Red
    exit 1
}

# ----- Verificar que el exe existe -----
$ExePath = Join-Path $Root "dist\monitor.exe"
if (-not (Test-Path $ExePath)) {
    Write-Host "ERROR: dist\monitor.exe no encontrado." -ForegroundColor Red
    exit 1
}

$ExeSize = (Get-Item $ExePath).Length / 1MB
Write-Host "[4/5] monitor.exe compilado correctamente ($([math]::Round($ExeSize, 1)) MB)" -ForegroundColor Yellow

# ----- Copiar exe compilado a public/ -----
$PublicExePath = Join-Path $Root "public\monitor.exe"
Copy-Item -Path $ExePath -Destination $PublicExePath -Force
Write-Host "[5/5] monitor.exe copiado a public\ (listo para deploy en Vercel)" -ForegroundColor Yellow

# ----- Limpiar el version.txt temporal de raíz -----
Remove-Item -Path $BundledVersionFile -Force -ErrorAction SilentlyContinue

# ----- Resumen -----
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " BUILD COMPLETO: v$Version" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host " public\version.txt -> $Version"
Write-Host " public\monitor.exe -> $([math]::Round($ExeSize, 1)) MB"
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Cyan
Write-Host "  1. git add public\version.txt public\monitor.exe"
Write-Host "  2. git commit -m 'build: v$Version'"
Write-Host "  3. git push  (Vercel auto-deploya)"
Write-Host ""
Write-Host "Para testear sin deployar, entrá al admin y apretá 'Simular actualización disponible'" -ForegroundColor Cyan
