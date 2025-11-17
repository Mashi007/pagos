# Actualizar Contraseña en Base de Datos

## Opción 1: Script Python (Recomendado - Genera el hash automáticamente)

### Generar SQL con hash correcto:

```bash
cd backend
python scripts/actualizar_password_sql.py itmaster@rapicreditca.com Casa1803+ update_password.sql
```

Esto generará un archivo `update_password.sql` con el hash correcto listo para ejecutar.

### Ejecutar el SQL generado:

```bash
# Desde línea de comandos PostgreSQL
psql -U tu_usuario -d tu_base_de_datos -f update_password.sql

# O desde psql interactivo
psql -U tu_usuario -d tu_base_de_datos
\i update_password.sql
```

## Opción 2: Script Python directo (Actualiza directamente en BD)

```bash
cd backend
python scripts/cambiar_password_usuario.py itmaster@rapicreditca.com Casa1803+
```

Este script actualiza directamente en la base de datos sin necesidad de SQL.

## Opción 3: SQL Manual (Requiere generar hash primero)

### Paso 1: Generar el hash de la contraseña

```bash
cd backend
python scripts/generar_hash_password.py Casa1803+
```

Esto mostrará el hash y el SQL completo.

### Paso 2: Ejecutar el SQL en tu base de datos

Copia el SQL generado y ejecútalo en tu cliente SQL (pgAdmin, DBeaver, etc.)

## Opción 4: Usar el script de actualización admin

```bash
cd backend
python scripts/actualizar_admin.py
```

Este script actualiza automáticamente el usuario admin con la contraseña `Casa1803+`.

## Verificación

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

## Notas de Seguridad

- La contraseña se almacena como hash (bcrypt) en la base de datos
- Nunca se almacena la contraseña en texto plano
- El hash es único para cada contraseña
- Si olvidas la contraseña, debes usar este script para cambiarla

