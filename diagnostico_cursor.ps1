# ============================================
# Script de Diagnóstico y Corrección: Error ECONNRESET en Cursor
# ============================================
# Este script ayuda a diagnosticar y resolver problemas de conexión en Cursor
# Request ID: 44a14c0d-8459-429c-bec5-8079c2840d8f
# ============================================

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "🔍 Diagnóstico de Error ECONNRESET en Cursor" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Cursor está ejecutándose
Write-Host "📋 Paso 1: Verificando procesos de Cursor..." -ForegroundColor Yellow
$cursorProcesses = Get-Process -Name "Cursor" -ErrorAction SilentlyContinue
if ($cursorProcesses) {
    Write-Host "⚠️  Cursor está ejecutándose. Por favor, ciérralo antes de continuar." -ForegroundColor Red
    Write-Host "   Presiona Enter después de cerrar Cursor para continuar..." -ForegroundColor Yellow
    Read-Host
} else {
    Write-Host "✅ Cursor no está ejecutándose. Continuando..." -ForegroundColor Green
}

Write-Host ""

# Verificar conexión a Internet
Write-Host "📋 Paso 2: Verificando conexión a Internet..." -ForegroundColor Yellow
try {
    $ping = Test-Connection -ComputerName "8.8.8.8" -Count 2 -Quiet
    if ($ping) {
        Write-Host "✅ Conexión a Internet: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Problemas de conectividad detectados" -ForegroundColor Red
    }
} catch {
    Write-Host "⚠️  No se pudo verificar la conexión: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""

# Verificar rutas de Cursor
Write-Host "📋 Paso 3: Verificando instalación de Cursor..." -ForegroundColor Yellow
$cursorAppData = "$env:APPDATA\Cursor"
$cursorLocalAppData = "$env:LOCALAPPDATA\Programs\cursor"

if (Test-Path $cursorAppData) {
    Write-Host "✅ Carpeta AppData encontrada: $cursorAppData" -ForegroundColor Green
} else {
    Write-Host "⚠️  Carpeta AppData no encontrada" -ForegroundColor Yellow
}

if (Test-Path $cursorLocalAppData) {
    Write-Host "✅ Carpeta de instalación encontrada: $cursorLocalAppData" -ForegroundColor Green
} else {
    Write-Host "⚠️  Carpeta de instalación no encontrada" -ForegroundColor Yellow
}

Write-Host ""

# Limpiar cache de Cursor
Write-Host "📋 Paso 4: Limpiando cache de Cursor..." -ForegroundColor Yellow
$cachePaths = @(
    "$env:APPDATA\Cursor\Cache",
    "$env:APPDATA\Cursor\Code Cache",
    "$env:APPDATA\Cursor\CachedData",
    "$env:APPDATA\Cursor\GPUCache",
    "$env:APPDATA\Cursor\ShaderCache"
)

$cleanedCount = 0
foreach ($path in $cachePaths) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction Stop
            Write-Host "✅ Limpiado: $path" -ForegroundColor Green
            $cleanedCount++
        } catch {
            Write-Host "⚠️  No se pudo limpiar: $path - $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

if ($cleanedCount -eq 0) {
    Write-Host "ℹ️  No se encontraron carpetas de cache para limpiar" -ForegroundColor Cyan
} else {
    Write-Host "✅ Se limpiaron $cleanedCount carpetas de cache" -ForegroundColor Green
}

Write-Host ""

# Verificar configuración de firewall
Write-Host "📋 Paso 5: Verificando reglas de firewall..." -ForegroundColor Yellow
try {
    $firewallRules = Get-NetFirewallApplicationFilter -Program "Cursor.exe" -ErrorAction SilentlyContinue
    if ($firewallRules) {
        Write-Host "ℹ️  Se encontraron reglas de firewall para Cursor" -ForegroundColor Cyan
        foreach ($rule in $firewallRules) {
            Write-Host "   - $($rule.DisplayName): $($rule.Action)" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️  No se encontraron reglas específicas de firewall para Cursor" -ForegroundColor Yellow
        Write-Host "   Considera agregar una excepción en Windows Defender" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  No se pudo verificar firewall (requiere permisos de administrador)" -ForegroundColor Yellow
}

Write-Host ""

# Verificar configuración de red
Write-Host "📋 Paso 6: Información de red..." -ForegroundColor Yellow
try {
    $networkAdapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
    Write-Host "✅ Adaptadores de red activos:" -ForegroundColor Green
    foreach ($adapter in $networkAdapters) {
        Write-Host "   - $($adapter.Name): $($adapter.LinkSpeed)" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  No se pudo obtener información de red" -ForegroundColor Yellow
}

Write-Host ""

# Verificar DNS
Write-Host "📋 Paso 7: Verificando DNS..." -ForegroundColor Yellow
try {
    $dnsServers = Get-DnsClientServerAddress | Where-Object { $_.AddressFamily -eq "IPv4" }
    Write-Host "✅ Servidores DNS configurados:" -ForegroundColor Green
    foreach ($dns in $dnsServers) {
        if ($dns.ServerAddresses) {
            Write-Host "   - $($dns.InterfaceAlias): $($dns.ServerAddresses -join ', ')" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "⚠️  No se pudo verificar DNS" -ForegroundColor Yellow
}

Write-Host ""

# Resumen y recomendaciones
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "📊 RESUMEN Y RECOMENDACIONES" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ Acciones Completadas:" -ForegroundColor Green
Write-Host "   - Verificación de procesos de Cursor" -ForegroundColor Gray
Write-Host "   - Verificación de conexión a Internet" -ForegroundColor Gray
Write-Host "   - Limpieza de cache ($cleanedCount carpetas)" -ForegroundColor Gray
Write-Host "   - Verificación de firewall" -ForegroundColor Gray
Write-Host ""

Write-Host "📝 Próximos Pasos Recomendados:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 🔴 IMPORTANTE: Deshabilitar HTTP/2 en Cursor" -ForegroundColor Red
Write-Host "   - Abre Cursor" -ForegroundColor Gray
Write-Host "   - Ve a Settings > Network" -ForegroundColor Gray
Write-Host "   - Deshabilita la opción 'HTTP/2'" -ForegroundColor Gray
Write-Host "   - Reinicia Cursor" -ForegroundColor Gray
Write-Host ""

Write-Host "2. Verificar que Windows Defender no esté bloqueando Cursor" -ForegroundColor Yellow
Write-Host ""

Write-Host "3. Si el problema persiste:" -ForegroundColor Yellow
Write-Host "   - Probar en otra red (hotspot móvil)" -ForegroundColor Gray
Write-Host "   - Actualizar Cursor a la última versión" -ForegroundColor Gray
Write-Host "   - Contactar soporte con Request ID: 44a14c0d-8459-429c-bec5-8079c2840d8f" -ForegroundColor Gray
Write-Host ""

Write-Host "4. Monitorear el error:" -ForegroundColor Yellow
Write-Host "   - Documentar frecuencia del error" -ForegroundColor Gray
Write-Host "   - Notar si ocurre en operaciones específicas" -ForegroundColor Gray
Write-Host ""

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "✅ Diagnóstico completado" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Preguntar si desea abrir el archivo de auditoría
$openAudit = Read-Host "¿Deseas abrir el archivo de auditoría detallada? (S/N)"
if ($openAudit -eq "S" -or $openAudit -eq "s") {
    $auditFile = Join-Path $PSScriptRoot "AUDITORIA_ERROR_CURSOR.md"
    if (Test-Path $auditFile) {
        Start-Process notepad.exe -ArgumentList $auditFile
    } else {
        Write-Host "⚠️  Archivo de auditoría no encontrado en: $auditFile" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Presiona Enter para salir..." -ForegroundColor Gray
Read-Host
