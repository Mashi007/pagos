# 🔐 INSTRUCCIONES PARA ACTUALIZAR CONTRASEÑA EN BASE DE DATOS

## Usuario: itmaster@rapicreditca.com
## Nueva contraseña: Casa1803+

---

## ✅ OPCIÓN 1: Script Python Directo (MÁS FÁCIL - RECOMENDADO)

Este método actualiza directamente en la base de datos sin necesidad de SQL manual.

### Windows:
```cmd
cd backend
python scripts\cambiar_password_usuario.py itmaster@rapicreditca.com Casa1803+
```

### Linux/Mac:
```bash
cd backend
python scripts/cambiar_password_usuario.py itmaster@rapicreditca.com Casa1803+
```

### O usar el script batch/shell:
```cmd
# Windows
scripts\ejecutar_actualizacion_password.bat itmaster@rapicreditca.com Casa1803+

# Linux/Mac
chmod +x scripts/ejecutar_actualizacion_password.sh
./scripts/ejecutar_actualizacion_password.sh itmaster@rapicreditca.com Casa1803+
```

---

## ✅ OPCIÓN 2: Generar SQL Completo con Hash Incluido

Este método genera un archivo SQL listo para ejecutar con el hash ya incluido.

### Paso 1: Generar el SQL
```bash
cd backend
python scripts/generar_sql_completo.py itmaster@rapicreditca.com Casa1803+
```

Esto creará un archivo `UPDATE_PASSWORD_FINAL.sql` con todo listo.

### Paso 2: Ejecutar el SQL generado

**Desde línea de comandos:**
```bash
psql -U tu_usuario -d tu_base_de_datos -f UPDATE_PASSWORD_FINAL.sql
```

**O desde psql interactivo:**
```sql
psql -U tu_usuario -d tu_base_de_datos
\i UPDATE_PASSWORD_FINAL.sql
```

**O copiar y pegar en pgAdmin/DBeaver:**
- Abre el archivo `UPDATE_PASSWORD_FINAL.sql`
- Copia todo el contenido
- Pégalo en tu cliente SQL y ejecuta

---

## ✅ OPCIÓN 3: SQL Manual (Requiere obtener hash primero)

### Paso 1: Generar el hash
```bash
cd backend
python scripts/generar_hash_password.py Casa1803+
```

Esto mostrará el hash y el SQL completo.

### Paso 2: Ejecutar el SQL mostrado

Copia el SQL generado y ejecútalo en tu base de datos.

---

## ✅ OPCIÓN 4: Usar script de actualización admin

```bash
cd backend
python scripts/actualizar_admin.py
```

Este script actualiza automáticamente el usuario admin con la contraseña `Casa1803+`.

---

## 📋 Verificación

Después de ejecutar cualquiera de los métodos, verifica que funcionó:

```sql
SELECT
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    updated_at
FROM users
WHERE email = 'itmaster@rapicreditca.com';
```

El campo `updated_at` debe mostrar la fecha/hora actual.

---

## 🔑 Credenciales de Acceso

Después de actualizar, puedes iniciar sesión con:

- **Email:** `itmaster@rapicreditca.com`
- **Contraseña:** `Casa1803+`

---

## ⚠️ Notas Importantes

1. **La contraseña se almacena como hash** (bcrypt) - nunca en texto plano
2. **El hash es único** para cada contraseña
3. **Si olvidas la contraseña**, debes usar este script para cambiarla
4. **Todos los scripts validan** que la contraseña cumpla con los requisitos de seguridad

---

## 🆘 Solución de Problemas

### Error: "Usuario no encontrado"
- Verifica que el email sea exactamente: `itmaster@rapicreditca.com`
- Verifica que el usuario exista en la base de datos

### Error: "La contraseña no cumple con los requisitos"
- La contraseña debe tener:
  - Mínimo 8 caracteres
  - Al menos una mayúscula
  - Al menos una minúscula
  - Al menos un número
  - Al menos un símbolo

### Error de conexión a la base de datos
- Verifica que `DATABASE_URL` esté configurada correctamente
- Verifica que la base de datos esté accesible
- Verifica las credenciales de la base de datos

