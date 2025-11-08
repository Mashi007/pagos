# COMANDOS PARA EJECUTAR EN POWERSHELL

## Opción 1: Ejecutar Script Python (Actualiza directamente en BD)

```powershell
cd C:\Users\PORTATIL\Documents\GitHub\pagos\backend
py scripts\cambiar_password_usuario.py itmaster@rapicreditca.com Casa1803+
```

## Opción 2: Generar SQL y ejecutarlo manualmente

### Paso 1: Generar el hash
```powershell
cd C:\Users\PORTATIL\Documents\GitHub\pagos\backend
py scripts\generar_hash_simple.py Casa1803+
```

### Paso 2: Ejecutar el SQL generado en tu base de datos

Copia el SQL que se muestra y ejecútalo en:
- pgAdmin
- DBeaver  
- psql (línea de comandos)
- Cualquier cliente SQL

## Opción 3: Usar el archivo SQL ya generado

El archivo `UPDATE_PASSWORD_FINAL.sql` ya tiene el hash incluido.

1. Abre el archivo: `backend\scripts\UPDATE_PASSWORD_FINAL.sql`
2. Copia todo el contenido
3. Pégalo en tu cliente SQL (pgAdmin, DBeaver, etc.)
4. Ejecuta el script

## Opción 4: Ejecutar SQL desde línea de comandos

```powershell
# Si tienes psql instalado
psql -U tu_usuario -d tu_base_de_datos -f C:\Users\PORTATIL\Documents\GitHub\pagos\backend\scripts\UPDATE_PASSWORD_FINAL.sql
```

---

## Verificación

Después de ejecutar, verifica con:

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

## Credenciales de Acceso

- **Email:** `itmaster@rapicreditca.com`
- **Contraseña:** `Casa1803+`

