# Script para solucionar problemas de DNS/Streaming de Cursor
# Ejecutar como administrador si es necesario

Write-Host "=== DIAGNOSTICO Y SOLUCION CURSOR DNS/STREAMING ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar DNS básico
Write-Host "1. Verificando DNS..." -ForegroundColor Yellow
try {
    $cursorDns = Resolve-DnsName -Name "cursor.sh" -ErrorAction Stop
    Write-Host "   OK: cursor.sh resuelve a $($cursorDns[0].IPAddress)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: No se puede resolver cursor.sh" -ForegroundColor Red
}

# 2. Verificar conectividad HTTPS
Write-Host "2. Verificando conectividad HTTPS..." -ForegroundColor Yellow
$testConnection = Test-NetConnection -ComputerName "cursor.sh" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
if ($testConnection) {
    Write-Host "   OK: Puerto 443 accesible" -ForegroundColor Green
} else {
    Write-Host "   ERROR: Puerto 443 no accesible" -ForegroundColor Red
}

# 3. Limpiar cache DNS de Windows
Write-Host "3. Limpiando cache DNS de Windows..." -ForegroundColor Yellow
ipconfig /flushdns | Out-Null
Write-Host "   OK: Cache DNS limpiado" -ForegroundColor Green

# 4. Verificar si hay reglas de firewall
Write-Host "4. Verificando firewall..." -ForegroundColor Yellow
$cursorExe = "C:\Program Files\Cursor\Cursor.exe"
if (Test-Path $cursorExe) {
    $firewallRules = Get-NetFirewallApplicationFilter | Where-Object {$_.Program -eq $cursorExe} -ErrorAction SilentlyContinue
    if ($firewallRules) {
        Write-Host "   INFO: Existen reglas de firewall para Cursor" -ForegroundColor Cyan
    } else {
        Write-Host "   INFO: No hay reglas específicas (puede usar reglas generales)" -ForegroundColor Cyan
    }
} else {
    Write-Host "   ADVERTENCIA: No se encontró Cursor.exe en ruta estándar" -ForegroundColor Yellow
}

# 5. Verificar procesos de Cursor
Write-Host "5. Verificando procesos de Cursor..." -ForegroundColor Yellow
$cursorProcesses = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "   INFO: $($cursorProcesses.Count) proceso(s) de Cursor activo(s)" -ForegroundColor Cyan
} else {
    Write-Host "   INFO: No hay procesos de Cursor ejecutándose" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=== SOLUCIONES RECOMENDADAS ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. REINICIAR CURSOR:" -ForegroundColor Yellow
Write-Host "   - Cerrar todas las ventanas de Cursor" -ForegroundColor White
Write-Host "   - Esperar 10 segundos" -ForegroundColor White
Write-Host "   - Abrir Cursor nuevamente" -ForegroundColor White
Write-Host ""
Write-Host "2. VERIFICAR ACTUALIZACION:" -ForegroundColor Yellow
Write-Host "   - Menú Help > Check for Updates" -ForegroundColor White
Write-Host ""
Write-Host "3. VERIFICAR CONEXION DE RED:" -ForegroundColor Yellow
Write-Host "   - Asegurar conexión estable a internet" -ForegroundColor White
Write-Host "   - Verificar que no hay VPN bloqueando" -ForegroundColor White
Write-Host ""
Write-Host "4. SI EL PROBLEMA PERSISTE:" -ForegroundColor Yellow
Write-Host "   - Verificar estado: https://status.cursor.sh" -ForegroundColor White
Write-Host "   - Revisar logs en: %LOCALAPPDATA%\Cursor\logs" -ForegroundColor White
Write-Host ""
Write-Host "=== DIAGNOSTICO COMPLETADO ===" -ForegroundColor Cyan

