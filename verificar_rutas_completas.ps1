Write-Host "=== VERIFICACIÓN COMPLETA DE RUTAS ===" -ForegroundColor Green

# Lista de todas las rutas del sidebar
$rutas = @(
    "/dashboard",
    "/clientes", 
    "/prestamos",
    "/pagos",
    "/amortizacion",
    "/conciliacion", 
    "/reportes",
    "/aprobaciones",
    "/carga-masiva",
    "/notificaciones",
    "/scheduler",
    "/auditoria",
    "/configuracion"
)

Write-Host "`n🔍 Verificando páginas implementadas..." -ForegroundColor Yellow

$paginas = @(
    "Dashboard.tsx",
    "Clientes.tsx",
    "Prestamos.tsx", 
    "Pagos.tsx",
    "Amortizacion.tsx",
    "Conciliacion.tsx",
    "Reportes.tsx",
    "Aprobaciones.tsx",
    "CargaMasiva.tsx",
    "Notificaciones.tsx",
    "Programador.tsx",
    "Auditoria.tsx",
    "Configuracion.tsx"
)

foreach ($pagina in $paginas) {
    $ruta = "frontend\src\pages\$pagina"
    if (Test-Path $ruta) {
        Write-Host "✅ $pagina - OK" -ForegroundColor Green
    } else {
        Write-Host "❌ $pagina - FALTANTE" -ForegroundColor Red
    }
}

Write-Host "`n🔍 Verificando importaciones en App.tsx..." -ForegroundColor Yellow

$appContent = Get-Content "frontend\src\App.tsx" -Raw

$imports = @(
    "Login",
    "Dashboard", 
    "Clientes",
    "Prestamos",
    "Pagos",
    "Amortizacion",
    "Conciliacion",
    "Reportes",
    "Aprobaciones",
    "Auditoria",
    "Notificaciones",
    "Programador",
    "Configuracion",
    "CargaMasiva",
    "VisualizacionBD"
)

foreach ($import in $imports) {
    if ($appContent -match "import.*$import") {
        Write-Host "✅ Import $import - OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Import $import - FALTANTE" -ForegroundColor Red
    }
}

Write-Host "`n🔍 Verificando rutas en App.tsx..." -ForegroundColor Yellow

foreach ($ruta in $rutas) {
    $rutaClean = $ruta.Replace("/", "")
    if ($appContent -match "path=`"$ruta`"") {
        Write-Host "✅ Ruta $ruta - OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Ruta $ruta - FALTANTE" -ForegroundColor Red
    }
}

Write-Host "`n🔍 Verificando componentes del sidebar..." -ForegroundColor Yellow

$sidebarContent = Get-Content "frontend\src\components\layout\Sidebar.tsx" -Raw

$sidebarItems = @(
    "Dashboard",
    "Clientes",
    "Préstamos", 
    "Pagos",
    "Amortización",
    "Conciliación",
    "Reportes",
    "Aprobaciones",
    "Carga Masiva",
    "Notificaciones",
    "Programador",
    "Auditoría",
    "Configuración"
)

foreach ($item in $sidebarItems) {
    if ($sidebarContent -match "title.*$item") {
        Write-Host "✅ Sidebar $item - OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Sidebar $item - FALTANTE" -ForegroundColor Red
    }
}

Write-Host "`n🎊 VERIFICACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
