# Script Interactivo para Crear Usuarios

Scripts para crear usuarios de forma interactiva y generar SQL directamente.

## Archivos

- `crear_usuario.py` - Script Python (multiplataforma)
- `crear_usuario.ps1` - Script PowerShell (Windows)

---

## Opción 1: Python (Recomendado - Multiplataforma)

### Requisitos
- Python 3.7+
- Acceso a la carpeta `backend`

### Uso

```bash
cd backend
python crear_usuario.py
```

### Flujo
1. El script te pregunta interactivamente por cada campo
2. Valida cada entrada
3. Genera el hash de password (te pide copiar/pegar desde Python)
4. Crea archivo SQL automáticamente
5. Muestra instrucciones para ejecutar en BD

### Ejemplo de ejecución

```
============================================================================
  CREAR USUARIO - FORMULARIO INTERACTIVO
============================================================================

--- USUARIO #1 ---

📧 Email (ej: usuario@empresa.com): juan@empresa.com
🆔 Cédula (ej: 12345678-9): 12345678-9
👤 Nombre Completo (Nombre y Apellido, ej: Juan Pérez García): Juan Pérez García
💼 Cargo (opcional, Enter para omitir): Operario
🔐 Roles disponibles:
   - admin     : Acceso total
   - manager   : Gestión operativa
   - operator  : Operaciones básicas
   - viewer    : Solo lectura (default)
Selecciona rol (admin/manager/operator/viewer): operator
🔑 Password (mínimo 6 caracteres): Password123

🔐 Generando hash de password...
⚠️  IMPORTANTE: El password debe ser hasheado con bcrypt
   Ejecuta esto en terminal Python:
   python -c "from app.core.security import get_password_hash; print(get_password_hash('Password123'))"

Pega aquí el hash generado: $2b$12$abcdef...

✅ Usuario 'juan@empresa.com' agregado

¿Agregar otro usuario? (s/n): n

✅ Total de usuarios: 1

============================================================================
  SQL GENERADO
============================================================================

-- Usuario: juan@empresa.com
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
    'juan@empresa.com',
    '12345678-9',
    '$2b$12$abcdef...',
    'Juan Pérez García',
    'Operario',
    'operator',
    true,
    '2026-04-01T15:30:00',
    '2026-04-01T15:30:00'
);

✅ Archivo guardado: crear_usuarios_20260401_153000.sql

============================================================================
  INSTRUCCIONES DE EJECUCIÓN
============================================================================

1️⃣  Archivo SQL creado: crear_usuarios_20260401_153000.sql

2️⃣  Ejecuta en PostgreSQL:
    psql -U usuario -d base_datos -f crear_usuarios_20260401_153000.sql

3️⃣  O copia y pega el SQL anterior directamente en tu cliente SQL

4️⃣  Verifica que se crearon los usuarios:
    SELECT email, nombre, rol FROM usuarios WHERE created_at >= NOW() - INTERVAL '1 minute';

✅ ¡Listo! Los usuarios están listos en la BD
```

---

## Opción 2: PowerShell (Windows)

### Requisitos
- PowerShell 5.0+
- Windows

### Uso

```powershell
cd backend
.\crear_usuario.ps1
```

**Si tienes error de ejecución de scripts**, ejecuta esto primero:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Diferencias vs Python
- La interfaz es similar pero con colores para Windows
- Genera el mismo SQL

---

## Paso Clave: Generar Hash de Password

Ambos scripts te pedirán que generes el hash del password. Debes hacerlo así:

### 1. Abre terminal Python en la carpeta `backend`:

```bash
cd backend
python
```

### 2. Dentro de Python:

```python
from app.core.security import get_password_hash
hash_resultado = get_password_hash('TuPassword123')
print(hash_resultado)
```

### 3. Copia el hash y pégalo en el script

El hash será algo como:
```
$2b$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcg7b3XeKeUxWdeS86.CHyVx9eK
```

---

## Validaciones

El script valida automáticamente:

✅ **Email**
- Formato válido
- Único en el sistema

✅ **Cédula**
- 1-50 caracteres
- Única en el sistema

✅ **Nombre**
- 1-255 caracteres (nombre completo)

✅ **Cargo**
- Opcional
- Máximo 100 caracteres

✅ **Rol**
- Debe ser: `admin`, `manager`, `operator`, `viewer`

✅ **Password**
- Mínimo 6 caracteres

---

## Generar SQL sin Script (Manual)

Si prefieres hacer todo manual:

```sql
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
    'usuario@empresa.com',
    '12345678-9',
    '$2b$12$hash_aqui',
    'Juan Pérez García',
    'Operario',
    'operator',
    true,
    NOW(),
    NOW()
);
```

---

## Archivos Generados

El script crea un archivo `crear_usuarios_YYYYMMDD_HHMMSS.sql` con:

- ✅ BEGIN; al inicio (transacción)
- ✅ INSERT de cada usuario
- ✅ Verificación de usuarios creados
- ✅ COMMIT; al final

Ejemplo de nombre: `crear_usuarios_20260401_153000.sql`

---

## Ejecución en BD

### PostgreSQL

```bash
psql -U nombre_usuario -d nombre_bd -f crear_usuarios_20260401_153000.sql
```

### O en cliente SQL (pgAdmin, DBeaver, etc.)
- Abre el archivo SQL
- Ejecuta todo

### Verificación

```sql
-- Ver usuarios creados en el último minuto
SELECT email, nombre, rol, is_active FROM usuarios 
WHERE created_at >= NOW() - INTERVAL '1 minute'
ORDER BY created_at DESC;
```

---

## Troubleshooting

### Error: "Email ya existe"
- Ese email ya está registrado en la BD
- Usa otro email

### Error: "Cédula ya existe"
- Esa cédula ya está registrada
- Usa otra cédula

### Error: "Hash inválido"
- El hash debe tener al menos 50 caracteres
- Genera de nuevo el hash en Python

### El script se cierra
- Presionaste Ctrl+C
- Vuelve a ejecutar

---

## Roles Explicados

| Rol | Descripción | Caso de Uso |
|-----|-------------|-----------|
| **admin** | Acceso total | Administrador del sistema |
| **manager** | Gestión operativa | Gerente, Supervisor |
| **operator** | Operaciones básicas | Ejecutivo de cuenta, Operario |
| **viewer** | Solo lectura | Consultor, Auditor |

---

## Agregar Múltiples Usuarios

El script permite agregar varios usuarios en una sesión:

1. Completa un usuario
2. Responde "s" cuando pregunte "¿Agregar otro usuario?"
3. Repite el proceso
4. Al final genera un SQL con todos juntos

---

## Notas Importantes

1. **Transacciones**: El SQL generado usa `BEGIN;` y `COMMIT;` para garantizar que todos los usuarios se crean o ninguno
2. **Seguridad**: Los passwords se hashean siempre con bcrypt
3. **Validación**: Se validan duplicados antes de insertar
4. **Logs**: Cada creación se registra con timestamp exacto

---

## Soporte

Si encuentras problemas:
1. Verifica que el password tenga al menos 6 caracteres
2. Asegúrate de generar el hash correctamente en Python
3. Verifica que el archivo SQL se creó en la carpeta backend
4. Revisa los errores SQL en la BD

¡Listo!
