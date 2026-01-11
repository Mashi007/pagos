# ============================================================================
# Script PowerShell: Ejecutar Migración ML Impago Calculado
# ============================================================================
# 
# Este script ejecuta la migración SQL para agregar columnas ML a prestamos
# 
# Fecha: 2026-01-11
# ============================================================================

param(
    [string]$DatabaseHost = "localhost",
    [string]$DatabaseName = "",
    [string]$DatabaseUser = "",
    [SecureString]$DatabasePassword,
    [int]$DatabasePort = 5432,
    [string]$SqlFile = "scripts/sql/MIGRACION_ML_IMPAGO_CALCULADO.sql"
)

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "MIGRACIÓN ML IMPAGO CALCULADO - Ejecución Manual" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que el archivo SQL existe
if (-not (Test-Path $SqlFile)) {
    Write-Host "❌ ERROR: No se encuentra el archivo SQL: $SqlFile" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Archivo SQL encontrado: $SqlFile" -ForegroundColor Green

# Solicitar credenciales si no se proporcionaron
if ([string]::IsNullOrEmpty($DatabaseName)) {
    $DatabaseName = Read-Host "Ingresa el nombre de la base de datos"
}

if ([string]::IsNullOrEmpty($DatabaseUser)) {
    $DatabaseUser = Read-Host "Ingresa el usuario de la base de datos"
}

# Convertir SecureString a texto plano solo cuando sea necesario
$plainPassword = $null
if ($null -eq $DatabasePassword) {
    $DatabasePassword = Read-Host "Ingresa la contraseña" -AsSecureString
}

# Convertir SecureString a texto plano para uso en conexión
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DatabasePassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)

Write-Host ""
Write-Host "Parámetros de conexión:" -ForegroundColor Yellow
Write-Host "  Host: $DatabaseHost" -ForegroundColor Gray
Write-Host "  Puerto: $DatabasePort" -ForegroundColor Gray
Write-Host "  Base de datos: $DatabaseName" -ForegroundColor Gray
Write-Host "  Usuario: $DatabaseUser" -ForegroundColor Gray
Write-Host ""

$confirm = Read-Host "¿Continuar con la migración? (S/N)"
if ($confirm -ne "S" -and $confirm -ne "s") {
    Write-Host "❌ Migración cancelada por el usuario" -ForegroundColor Yellow
    # Limpiar contraseña de memoria antes de salir
    if ($null -ne $plainPassword) {
        $plainPassword = $null
    }
    exit 0
}

Write-Host ""
Write-Host "Ejecutando migración..." -ForegroundColor Cyan
Write-Host ""

# Construir cadena de conexión (usando contraseña en texto plano solo para la conexión)
$connectionString = "host=$DatabaseHost port=$DatabasePort dbname=$DatabaseName user=$DatabaseUser password=$plainPassword"

try {
    # Intentar usar psql si está disponible
    $psqlPath = Get-Command psql -ErrorAction SilentlyContinue
    
    if ($psqlPath) {
        Write-Host "Usando psql para ejecutar la migración..." -ForegroundColor Gray
        
        # Establecer variable de entorno con contraseña (solo para la ejecución)
        $env:PGPASSWORD = $plainPassword
        
        $arguments = @(
            "-h", $DatabaseHost,
            "-p", $DatabasePort.ToString(),
            "-U", $DatabaseUser,
            "-d", $DatabaseName,
            "-f", $SqlFile,
            "-v", "ON_ERROR_STOP=1"
        )
        
        $result = & psql $arguments 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Migración ejecutada exitosamente!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Resultado:" -ForegroundColor Yellow
            Write-Host $result -ForegroundColor Gray
        } else {
            Write-Host ""
            Write-Host "❌ ERROR al ejecutar la migración" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            exit 1
        }
        
        # Limpiar contraseña de memoria y variable de entorno
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
        if ($null -ne $plainPassword) {
            $plainPassword = $null
        }
    } else {
        Write-Host "⚠️ psql no está disponible. Opciones:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. Instalar PostgreSQL client tools (psql)" -ForegroundColor Gray
        Write-Host "2. Ejecutar manualmente el script SQL en DBeaver o tu cliente SQL preferido" -ForegroundColor Gray
        Write-Host "3. Usar Python con psycopg2 (ver README_MIGRACION_ML_IMPAGO.md)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Archivo SQL: $SqlFile" -ForegroundColor Cyan
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    # Limpiar contraseña de memoria y variable de entorno en caso de error
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    if ($null -ne $plainPassword) {
        $plainPassword = $null
    }
    exit 1
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Migración completada" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "1. Verificar que las columnas se crearon correctamente" -ForegroundColor Gray
Write-Host "2. Ejecutar: python scripts/python/comparar_bd_con_orm.py" -ForegroundColor Gray
Write-Host "3. Confirmar que las 4 discrepancias críticas desaparecieron" -ForegroundColor Gray
Write-Host ""

# Limpieza final de credenciales sensibles
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
if ($null -ne $plainPassword) {
    $plainPassword = $null
}
