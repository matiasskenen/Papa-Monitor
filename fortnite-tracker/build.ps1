# build.ps1
# Wrapper para mantener compatibilidad del comando histórico.

param(
    [string]$Version = ""
)

$Script = Join-Path $PSScriptRoot "packaging\build-monitor.ps1"
if (-not (Test-Path $Script)) {
    throw "No se encontró $Script"
}

& $Script -Version $Version
