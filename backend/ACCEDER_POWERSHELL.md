# 🔑 Acceder a Render - Guía PowerShell Paso a Paso

## ❌ Problema

- Error 429 (rate limit bloqueado)
- Credenciales de Render (ADMIN_EMAIL/ADMIN_PASSWORD) no funcionan
- Usuario en BD está causando problemas

## ✅ Solución: 2 Opciones

---

## OPCIÓN 1: Limpiar Rate Limit (5 minutos)

### Paso 1️⃣: Abre PowerShell

```powershell
# En Windows, presiona: Win + R
# Escribe: powershell
# Enter
```

### Paso 2️⃣: Necesitas el secreto

En **Render Dashboard** → **Environment**:
- Busca: `ADMIN_SECRET_CLEAR_LIMITS`
- Copia el valor

### Paso 3️⃣: Limpia el rate limit

```powershell
$secret = "TU_ADMIN_SECRET_AQUI"
$headers = @{
    "X-Admin-Secret" = $secret
    "Content-Type" = "application/json"
}

$response = Invoke-RestMethod `
    -Uri "https://pagos-f2qf.onrender.com/api/v1/auth/clear-rate-limits" `
    -Method POST `
    -Headers $headers

Write-Host $response
```

**Resultado esperado:**
```
message                 ips_login_cleared ips_forgot_cleared
-------                 --------- ------
Rate limits limpiados            1                0
```

### Paso 4️⃣: Ahora sí intenta login

Ve a: `https://pagos-f2qf.onrender.com`

Ingresa tu email y password

---

## OPCIÓN 2: Crear Usuario Admin en BD (10 minutos)

Si aún no tienes usuario en BD.

### Paso 1️⃣: Abre PowerShell

```powershell
# Win + R → powershell
```

### Paso 2️⃣: Obtén la DATABASE_URL de Render

En **Render Dashboard** → **Data Store**:
- Busca: **Internal Database URL**
- Copia completa

### Paso 3️⃣: Copia este código completo

```powershell
# ============================================================================
# CREAR ADMIN EN RENDER - COPIA TODO ESTO EN POWERSHELL
# ============================================================================

# CAMBIAR ESTOS VALORES:
$DatabaseUrl = "postgresql://user:pass@host:5432/db"
$AdminEmail = "admin@empresa.com"
$AdminCedula = "99999999-9"
$AdminNombre = "Admin Recuperación"
$AdminPassword = "AdminPass123"

# Instalar psycopg2 si no lo tienes
Write-Host "🔍 Verificando Python..." -ForegroundColor Cyan
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python no instalado. Descárgalo de https://python.org" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Python encontrado: $pythonCheck" -ForegroundColor Green

# Instalar psycopg2
Write-Host "`n📦 Instalando psycopg2..." -ForegroundColor Cyan
pip install psycopg2-binary -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error instalando psycopg2" -ForegroundColor Red
    exit 1
}

# Crear script Python temporal
$pythonScript = @"
import psycopg2
from urllib.parse import urlparse
from datetime import datetime
import sys

# Configuración
db_url = r'$DatabaseUrl'
email = r'$AdminEmail'.lower().strip()
cedula = r'$AdminCedula'.strip()
nombre = r'$AdminNombre'.strip()
password = r'$AdminPassword'

print(f"\n📧 Email: {email}")
print(f"🆔 Cédula: {cedula}")
print(f"👤 Nombre: {nombre}")

# Validar
if len(password) < 6:
    print("❌ Password debe tener al menos 6 caracteres")
    sys.exit(1)

# Conectar
try:
    parsed = urlparse(db_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password,
        sslmode='require'
    )
    print("✅ Conectado a Render DB")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    sys.exit(1)

# Generar hash (bcrypt manual)
# Para usar: python -c "from app.core.security import get_password_hash; print(get_password_hash('password'))"
# Por ahora, usar plaintext (NO SEGURO - solo para recuperación)

# Verificar duplicados
cursor = conn.cursor()
try:
    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    if cursor.fetchone():
        print(f"⚠️  Email {email} ya existe")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    cursor.execute("SELECT id FROM usuarios WHERE cedula = %s", (cedula,))
    if cursor.fetchone():
        print(f"⚠️  Cédula {cedula} ya existe")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    # Para recuperación, vamos a usar hash simple
    # En producción, generar con get_password_hash()
    print("\n⚠️  IMPORTANTE: Este script crea password sin hashear.")
    print("   DEBES generar el hash bcrypt correctamente:")
    print(f"   python -c \"from app.core.security import get_password_hash; print(get_password_hash('{password}'))\"")
    print("\n   Esperando que pegues el hash...")
    
    hash_input = input("Pega aquí el hash bcrypt (o Enter para cancelar): ").strip()
    if not hash_input or len(hash_input) < 50:
        print("❌ Hash inválido")
        cursor.close()
        conn.close()
        sys.exit(1)
    
    # Insertar usuario
    now = datetime.utcnow().isoformat()
    sql = """
    INSERT INTO usuarios (email, cedula, password_hash, nombre, rol, is_active, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, true, %s, %s)
    RETURNING id;
    """
    
    cursor.execute(sql, (email, cedula, hash_input, nombre, 'admin', now, now))
    user_id = cursor.fetchone()[0]
    conn.commit()
    
    print(f"\n✅ Usuario admin creado!")
    print(f"   ID: {user_id}")
    print(f"   Email: {email}")
    print(f"   Nombre: {nombre}")
    print(f"   Rol: admin")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    cursor.close()
    conn.close()
    sys.exit(1)
"@

# Guardar script Python
$scriptPath = "$env:TEMP\crear_admin_render.py"
$pythonScript | Out-File -FilePath $scriptPath -Encoding UTF8 -Force

Write-Host "`n🔐 Generando hash bcrypt..." -ForegroundColor Yellow
Write-Host "Copia esto en terminal Python:" -ForegroundColor Yellow
Write-Host "python -c `"from app.core.security import get_password_hash; print(get_password_hash('$AdminPassword'))`"" -ForegroundColor Cyan

# Ejecutar script Python
Write-Host "`n🚀 Ejecutando script..." -ForegroundColor Cyan
python $scriptPath

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ ¡Usuario creado exitosamente!" -ForegroundColor Green
    Write-Host "Ahora puedes ingresar en: https://pagos-f2qf.onrender.com" -ForegroundColor Green
    Write-Host "Email: $AdminEmail" -ForegroundColor Green
    Write-Host "Password: $AdminPassword" -ForegroundColor Green
} else {
    Write-Host "`n❌ Error creando usuario" -ForegroundColor Red
}

# Limpiar archivo temporal
Remove-Item $scriptPath -Force -ErrorAction SilentlyContinue
```

### Paso 4️⃣: Ejecuta el código

1. Selecciona TODO el código anterior (desde `# ============================================================================` hasta el final)
2. Copia (Ctrl+C)
3. Pega en PowerShell (Ctrl+V)
4. Presiona Enter

### Paso 5️⃣: El script pedirá hash bcrypt

Abre **otra ventana** de Python:

```bash
python
```

Dentro de Python:

```python
from app.core.security import get_password_hash
print(get_password_hash('AdminPass123'))
```

Copia el resultado (será largo, tipo `$2b$12$...`) y pégalo en PowerShell.

### Paso 6️⃣: ¡Listo! Ingresar

Ve a: `https://pagos-f2qf.onrender.com`
- Email: admin@empresa.com
- Password: AdminPass123

---

## OPCIÓN 3: Esperar 60 segundos (La Más Simple)

```powershell
# Simplemente espera
Write-Host "⏳ Esperando 60 segundos para que rate limit se limpie..." -ForegroundColor Yellow
Start-Sleep -Seconds 60
Write-Host "✅ Ya puedes intentar login de nuevo" -ForegroundColor Green
```

---

## 🆘 Si Sigue Sin Funcionar

### Verificar conexión a BD desde PowerShell

```powershell
$db = "postgresql://user:pass@host:5432/db"
$db
```

### Verificar que usuarios existan en BD

En Render Dashboard → Query:

```sql
SELECT email, nombre, rol FROM usuarios LIMIT 5;
```

### Ver logs de Render

En Render Dashboard → Logs, busca "login" o "error"

---

## 📝 Checklist Final

- [ ] ¿Limpiaste el rate limit O esperaste 60 segundos?
- [ ] ¿Email y password correctos?
- [ ] ¿Usuario existe en BD?
- [ ] ¿Rol es 'admin'?
- [ ] ¿Usuario está is_active = true?

---

## ✅ ¡Listo!

Ya deberías poder ingresar. Si sigue habiendo problemas,:

1. Revisa los logs en Render
2. Verifica que la BD tenga el usuario
3. Intenta desde otra red (desactiva VPN)

¡Éxito! 🚀
