# ============================================================================
# Script interactivo para crear usuarios en Windows PowerShell
# Uso: .\crear_usuario.ps1
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  CREAR USUARIO - FORMULARIO INTERACTIVO" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

$usuarios = @()

function Test-Email {
    param([string]$email)
    return $email -match '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
}

function Test-Cedula {
    param([string]$cedula)
    return $cedula.Length -gt 0 -and $cedula.Length -le 50
}

function Test-Nombre {
    param([string]$nombre)
    return $nombre.Length -gt 0 -and $nombre.Length -le 255
}

function Test-Password {
    param([string]$password)
    return $password.Length -ge 6
}

function Test-Rol {
    param([string]$rol)
    return $rol -in @('admin', 'manager', 'operator', 'viewer')
}

function Hacer-Pregunta {
    param(
        [string]$pregunta,
        [scriptblock]$validador,
        [string]$tipo = 'string'
    )
    
    while ($true) {
        $respuesta = Read-Host "`n$pregunta"
        
        if ([string]::IsNullOrWhiteSpace($respuesta)) {
            Write-Host "❌ Campo obligatorio, no puede estar vacío" -ForegroundColor Red
            continue
        }
        
        if (-not (& $validador $respuesta)) {
            switch ($tipo) {
                'email' { Write-Host "❌ Email inválido. Use formato: usuario@empresa.com" -ForegroundColor Red }
                'password' { Write-Host "❌ Password debe tener al menos 6 caracteres" -ForegroundColor Red }
                'cedula' { Write-Host "❌ Cédula debe tener 1-50 caracteres" -ForegroundColor Red }
                'nombre' { Write-Host "❌ Nombre debe tener 1-255 caracteres" -ForegroundColor Red }
                'rol' { Write-Host "❌ Rol inválido. Debe ser: admin, manager, operator o viewer" -ForegroundColor Red }
            }
            continue
        }
        
        return $respuesta.Trim()
    }
}

function Generar-Hash-Password {
    param([string]$password)
    
    Write-Host "`n⚠️  IMPORTANTE: El password debe ser hasheado con bcrypt" -ForegroundColor Yellow
    Write-Host "   Ejecuta esto en terminal Python:" -ForegroundColor Yellow
    Write-Host "   python -c `"from app.core.security import get_password_hash; print(get_password_hash('$password'))`"" -ForegroundColor Yellow
    
    $hash = Read-Host "`nPega aquí el hash generado"
    
    if ([string]::IsNullOrWhiteSpace($hash) -or $hash.Length -lt 50) {
        Write-Host "❌ Hash inválido o incompleto" -ForegroundColor Red
        return Generar-Hash-Password $password
    }
    
    return $hash
}

# Ciclo de usuarios
while ($true) {
    $numeroUsuario = $usuarios.Count + 1
    Write-Host "`n--- USUARIO #$numeroUsuario ---" -ForegroundColor Cyan
    
    # Email
    $email = Hacer-Pregunta "📧 Email (ej: usuario@empresa.com)" { param($e) Test-Email $e } 'email'
    $email = $email.ToLower()
    
    # Cédula
    $cedula = Hacer-Pregunta "🆔 Cédula (ej: 12345678-9)" { param($c) Test-Cedula $c } 'cedula'
    
    # Nombre
    $nombre = Hacer-Pregunta "👤 Nombre Completo (Nombre y Apellido, ej: Juan Pérez García)" { param($n) Test-Nombre $n } 'nombre'
    
    # Cargo (opcional)
    Write-Host "`n💼 Cargo (opcional, Enter para omitir): " -NoNewline
    $cargoInput = Read-Host
    $cargo = if ([string]::IsNullOrWhiteSpace($cargoInput)) { $null } else { $cargoInput.Trim() }
    
    # Rol
    Write-Host "`n🔐 Roles disponibles:"
    Write-Host "   - admin     : Acceso total"
    Write-Host "   - manager   : Gestión operativa"
    Write-Host "   - operator  : Operaciones básicas"
    Write-Host "   - viewer    : Solo lectura (default)"
    
    $rol = (Hacer-Pregunta "Selecciona rol (admin/manager/operator/viewer)" { param($r) Test-Rol $r } 'rol').ToLower()
    
    # Password
    $password = Hacer-Pregunta "🔑 Password (mínimo 6 caracteres)" { param($p) Test-Password $p } 'password'
    
    # Generar hash
    Write-Host "`n🔐 Generando hash de password..." -ForegroundColor Yellow
    $passwordHash = Generar-Hash-Password $password
    
    # Agregar usuario
    $usuario = @{
        email = $email
        cedula = $cedula
        nombre = $nombre
        cargo = $cargo
        rol = $rol
        password_hash = $passwordHash
    }
    $usuarios += $usuario
    
    Write-Host "`n✅ Usuario '$email' agregado" -ForegroundColor Green
    
    # Preguntar si agregar otro
    $otro = Read-Host "`n¿Agregar otro usuario? (s/n)"
    if ($otro -ne 's' -and $otro -ne 'si') {
        break
    }
}

Write-Host "`n✅ Total de usuarios: $($usuarios.Count)" -ForegroundColor Green

# Generar SQL
Write-Host "`n" + ("="*70) -ForegroundColor Cyan
Write-Host "  SQL GENERADO" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Cyan

$ahora = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss")
$sqlContent = "-- ============================================================================`n"
$sqlContent += "-- Script de inserción de usuarios`n"
$sqlContent += "-- Generado automáticamente`n"
$sqlContent += "-- ============================================================================`n`n"
$sqlContent += "BEGIN;`n`n"

foreach ($usuario in $usuarios) {
    $cargoValue = if ($null -eq $usuario.cargo) { "NULL" } else { "'$($usuario.cargo)'" }
    
    $sql = @"
INSERT INTO usuarios (
    email,
    cedula,
    password_hash,
    nombre,
    cargo,
    rol,
    is_active,
    created_at,
    updated_at
) VALUES (
    '$($usuario.email)',
    '$($usuario.cedula)',
    '$($usuario.password_hash)',
    '$($usuario.nombre)',
    $cargoValue,
    '$($usuario.rol)',
    true,
    '$ahora',
    '$ahora'
);
"@
    
    Write-Host "`n-- Usuario: $($usuario.email)" -ForegroundColor Yellow
    Write-Host $sql
    
    $sqlContent += $sql + "`n`n"
}

$sqlContent += "-- Verificar usuarios creados`n"
$sqlContent += "SELECT email, nombre, rol, is_active FROM usuarios WHERE created_at >= NOW() - INTERVAL '1 minute';`n`n"
$sqlContent += "COMMIT;`n"

# Guardar archivo
$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$nombreArchivo = "crear_usuarios_$timestamp.sql"

try {
    $sqlContent | Out-File -FilePath $nombreArchivo -Encoding UTF8
    Write-Host "`n✅ Archivo guardado: $nombreArchivo" -ForegroundColor Green
} catch {
    Write-Host "`n❌ Error guardando archivo: $_" -ForegroundColor Red
    exit 1
}

# Mostrar instrucciones
Write-Host "`n" + ("="*70) -ForegroundColor Cyan
Write-Host "  INSTRUCCIONES DE EJECUCIÓN" -ForegroundColor Cyan
Write-Host ("="*70) -ForegroundColor Cyan

Write-Host @"

1️⃣  Archivo SQL creado: $nombreArchivo

2️⃣  Ejecuta en PostgreSQL:
    psql -U usuario -d base_datos -f $nombreArchivo

3️⃣  O copia y pega el SQL anterior directamente en tu cliente SQL

4️⃣  Verifica que se crearon los usuarios:
    SELECT email, nombre, rol FROM usuarios WHERE created_at >= NOW() - INTERVAL '1 minute';

✅ ¡Listo! Los usuarios están listos en la BD
"@ -ForegroundColor Green
