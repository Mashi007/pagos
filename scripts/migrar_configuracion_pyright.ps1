# Script para migrar configuracion de cursorpyright a pyrightconfig.json
# Busca la configuracion en multiples ubicaciones

Write-Host "[*] Buscando configuracion de cursorpyright..." -ForegroundColor Cyan

$found = $false
$configValue = $null

# 1. Buscar en configuracion global de Cursor
$cursorGlobalSettings = "$env:APPDATA\Cursor\User\settings.json"
if (Test-Path $cursorGlobalSettings) {
    Write-Host "`n[*] Revisando: $cursorGlobalSettings" -ForegroundColor Yellow
    $content = Get-Content $cursorGlobalSettings -Raw -Encoding UTF8
    if ($content -match '"cursorpyright\.analysis\.diagnosticSeverityOverrides"\s*:\s*({[^}]+})') {
        $configValue = $matches[1]
        Write-Host "[OK] Configuracion encontrada en Cursor global" -ForegroundColor Green
        Write-Host "Configuracion: $configValue" -ForegroundColor Gray
        $found = $true
    }
}

# 2. Buscar en configuracion global de VS Code
$vscodeGlobalSettings = "$env:APPDATA\Code\User\settings.json"
if (-not $found -and (Test-Path $vscodeGlobalSettings)) {
    Write-Host "`n[*] Revisando: $vscodeGlobalSettings" -ForegroundColor Yellow
    $content = Get-Content $vscodeGlobalSettings -Raw -Encoding UTF8
    if ($content -match '"cursorpyright\.analysis\.diagnosticSeverityOverrides"\s*:\s*({[^}]+})') {
        $configValue = $matches[1]
        Write-Host "[OK] Configuracion encontrada en VS Code global" -ForegroundColor Green
        Write-Host "Configuracion: $configValue" -ForegroundColor Gray
        $found = $true
    }
}

# 3. Buscar en configuracion del workspace (si existe)
$workspaceSettings = ".vscode\settings.json"
if (-not $found -and (Test-Path $workspaceSettings)) {
    Write-Host "`n[*] Revisando: $workspaceSettings" -ForegroundColor Yellow
    $content = Get-Content $workspaceSettings -Raw -Encoding UTF8
    if ($content -match '"cursorpyright\.analysis\.diagnosticSeverityOverrides"\s*:\s*({[^}]+})') {
        $configValue = $matches[1]
        Write-Host "[OK] Configuracion encontrada en workspace" -ForegroundColor Green
        Write-Host "Configuracion: $configValue" -ForegroundColor Gray
        $found = $true
    }
}

if (-not $found) {
    Write-Host "`n[!] No se encontro la configuracion 'cursorpyright.analysis.diagnosticSeverityOverrides'" -ForegroundColor Yellow
    Write-Host "`nEsto puede significar que:" -ForegroundColor Gray
    Write-Host "  1. La configuracion no existe (la advertencia puede ser preventiva)" -ForegroundColor Gray
    Write-Host "  2. La configuracion esta en otro archivo de configuracion" -ForegroundColor Gray
    Write-Host "`nSolucion: Puedes agregar la configuracion directamente en pyrightconfig.json" -ForegroundColor Cyan
    Write-Host "   usando el formato de Pyright (reportDiagnostics)" -ForegroundColor Gray
    exit 0
}

# Si encontramos la configuracion, mostrar como migrarla
Write-Host "`n[*] Instrucciones para migrar:" -ForegroundColor Cyan
Write-Host "`nLa configuracion encontrada necesita convertirse al formato de Pyright." -ForegroundColor Gray
Write-Host "`nFormato VS Code/Cursor:" -ForegroundColor Yellow
Write-Host "  cursorpyright.analysis.diagnosticSeverityOverrides: $configValue" -ForegroundColor Gray
Write-Host "`nFormato Pyright (para pyrightconfig.json):" -ForegroundColor Yellow
Write-Host "  reportDiagnostics: { ... }" -ForegroundColor Gray
Write-Host "`nNota: Los codigos de diagnostico pueden diferir entre formatos." -ForegroundColor Yellow
Write-Host "   Revisa la documentacion de Pyright para mapear correctamente." -ForegroundColor Gray

