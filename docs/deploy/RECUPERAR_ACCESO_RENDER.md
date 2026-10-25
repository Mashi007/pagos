# Recuperación de Acceso - No Puedo Ingresar

Si no puedes ingresar porque no hay usuarios en la BD, sigue estos pasos:

---

## 📋 Prerrequisitos

1. **Acceso a Render Dashboard**
   - URL: https://dashboard.render.com
   - Encuentra tu base de datos PostgreSQL

2. **Python 3.7+** instalado localmente

3. **Acceso a la carpeta `backend` del proyecto**

---

## 🔑 Paso 1: Obtener DATABASE_URL de Render

### En Render Dashboard:

1. Ve a **Databases**
2. Selecciona tu base de datos
3. Busca **Internal Database URL**
4. Copia la URL (algo como):
   ```
   postgresql://user:password@host:5432/dbname
   ```

### ⚠️ Importante:
- Usa la **Internal Database URL** (no External)
- Debe comenzar con `postgresql://`
- Contiene: usuario, password, host, puerto, nombre BD

---

## 🚀 Paso 2: Ejecutar Script de Recuperación

### En tu terminal local:

```bash
cd backend
python recuperar_acceso.py
```

### El script pedirá:

1. **DATABASE_URL** - Pega la URL que copiaste
2. **Email del admin** - ej: admin@empresa.com
3. **Cédula** - ej: 99999999-9
4. **Nombre** - ej: Admin Sistema
5. **Password** - Mínimo 6 caracteres

---

## 📝 Ejemplo de Ejecución

```
======================================================================
  RECUPERACIÓN DE ACCESO - CREAR ADMIN
======================================================================

📍 Necesitas la URL de conexión a PostgreSQL en Render
   Encuentra en: Dashboard Render → Base de datos → Internal Database URL

🔗 Pega aquí la DATABASE_URL: postgresql://user:pass@db.render.com:5432/pagos_db

✅ Conectado a Render PostgreSQL

======================================================================
  DATOS DEL ADMIN DE RECUPERACIÓN
======================================================================

📧 Email del admin (ej: admin@empresa.com): miladmin@empresa.com
🆔 Cédula (ej: 99999999-9): 12345678-9
👤 Nombre completo (ej: Admin Sistema): Admin Recuperación
🔑 Password (mínimo 6 caracteres): AdminPass123

🔐 Generando hash bcrypt...

✅ Usuario admin creado exitosamente!
   ID: 1
   Email: miladmin@empresa.com
   Nombre: Admin Recuperación
   Rol: admin

======================================================================
  ✅ ¡ACCESO RECUPERADO!
======================================================================

Ya puedes ingresar con:
  Email: miladmin@empresa.com
  Password: AdminPass123

⚠️  CAMBIA ESTE PASSWORD INMEDIATAMENTE después de ingresar:
    Menu → Perfil/Usuarios → Cambiar Password
```

---

## 🔐 Paso 3: Ingresar en la Aplicación

1. Ve a: `https://pagos-f2qf.onrender.com` (o tu URL)
2. Login con:
   - Email: El que usaste en el script
   - Password: El que configuraste
3. ¡Ya tienes acceso! ✅

---

## 🚨 Errores Comunes

### Error: "Falta instalar psycopg2"

```bash
pip install psycopg2-binary
```

### Error: "No se puede importar get_password_hash"

Asegúrate de estar en la carpeta `backend` y tener `requirements.txt` instalado:

```bash
cd backend
pip install -r requirements.txt
```

### Error: "Email/Cédula ya existen"

Usa otros valores:
- Email diferente
- Cédula diferente

### Error de conexión

Verifica:
- ✅ DATABASE_URL es correcta
- ✅ Red permite conexión a Render (algunos WiFi bloquean)
- ✅ La BD está activa en Render

---

## 📌 Alternativa: Crear manualmente en Render

Si el script no funciona, crea directamente en Render:

### 1. Abre Render Dashboard → Data Store → Query

### 2. Ejecuta este SQL:

```sql
-- Primero, generar el hash bcrypt en Python:
-- python -c "from app.core.security import get_password_hash; print(get_password_hash('TuPassword'))"

INSERT INTO usuarios (
    email,
    cedula,
    password_hash,
    nombre,
    rol,
    is_active,
    created_at,
    updated_at
) VALUES (
    'admin@empresa.com',
    '12345678-9',
    '$2b$12$... PEG A AQUI EL HASH ...',
    'Admin Recuperación',
    'admin',
    true,
    NOW(),
    NOW()
);
```

---

## ✅ Verificación

Después de crear el usuario, verifica en Render:

```sql
SELECT id, email, nombre, rol, is_active FROM usuarios;
```

Deberías ver el usuario admin que creaste.

---

## 🔒 Seguridad Post-Recuperación

Después de recuperar acceso:

1. ✅ **Cambia el password inmediatamente**
   - Ingresar → Perfil → Cambiar Password

2. ✅ **Crea otros usuarios normales**
   - Usa el endpoint `/api/v1/usuarios` o el script interactivo

3. ✅ **Revisa el log de auditoría**
   - Para ver cuándo se creó el admin de recuperación

4. ✅ **Activa autenticación 2FA** (si es disponible)

---

## 📞 Si sigue sin funcionar

Verifica:

1. ¿La BD en Render está activa?
   ```bash
   psql postgresql://user:pass@host/db -c "SELECT 1;"
   ```

2. ¿Puedes conectar desde tu máquina?
   ```bash
   psql postgresql://user:pass@host/db
   ```

3. ¿La tabla `usuarios` existe?
   ```sql
   \dt usuarios;
   ```

4. ¿Hay constrains de unique que bloqueaban?
   ```sql
   SELECT * FROM usuarios LIMIT 1;
   ```

---

## 🎯 Próximos Pasos

Después de recuperar acceso:

1. Usa el script `crear_usuario.py` para agregar más usuarios
2. Configura otros admins según sea necesario
3. Implementa backup automático de usuarios

¡Listo! 🚀
