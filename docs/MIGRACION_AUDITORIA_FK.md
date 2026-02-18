# Migración: auditoria.usuario_id FK → usuarios

## Problema

Al aprobar manualmente un préstamo (`POST /api/v1/prestamos/{id}/aprobar-manual`), el backend devuelve 500:

```
Key (usuario_id)=(2) is not present in table "users"
```

**Causa:** La FK `auditoria.usuario_id` apunta a la tabla `users`, pero la app usa la tabla `usuarios`.

## Solución

### Opción 1: Endpoint desde la app (más rápido)

1. En **Render Dashboard** → tu servicio **pagos-backend** → **Environment**
2. Añade la variable: `MIGRATION_AUDITORIA_SECRET` = un valor secreto (ej. una cadena aleatoria larga)
3. Guarda y espera a que se redespliegue
4. Ejecuta (reemplaza `TU_SECRETO` y la URL si tu backend está en otro host):

```bash
curl -X POST "https://rapicredit.onrender.com/api/admin/run-migration-auditoria-fk" \
  -H "X-Migration-Secret: TU_SECRETO"
```

5. Deberías recibir: `{"success": true, "message": "Migración auditoria FK completada..."}`
6. (Opcional) Elimina `MIGRATION_AUDITORIA_SECRET` de las variables de entorno tras ejecutar

### Opción 2: Script Python

Desde el directorio `backend/`, con `DATABASE_URL` apuntando a la BD de producción:

```bash
cd backend
# Usar la misma DATABASE_URL que el backend en Render (cópiala del Dashboard)
$env:DATABASE_URL="postgresql://user:pass@host/db"  # PowerShell
# o
export DATABASE_URL="postgresql://user:pass@host/db"  # Bash

python scripts/ejecutar_migracion_auditoria_fk.py
```

### Opción 3: SQL directo en Render

1. En [Render Dashboard](https://dashboard.render.com) → tu base de datos PostgreSQL
2. **Connect** → copia la **External Database URL**
3. Conéctate con `psql` o un cliente (DBeaver, pgAdmin, etc.) y ejecuta:

```sql
ALTER TABLE auditoria DROP CONSTRAINT IF EXISTS auditoria_usuario_id_fkey;
ALTER TABLE auditoria ADD CONSTRAINT auditoria_usuario_id_fkey
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
```

### Opción 4: Render Shell (si está disponible)

Si tu plan de Render incluye Shell:

```bash
cd backend
python scripts/ejecutar_migracion_auditoria_fk.py
```

(La variable `DATABASE_URL` ya está configurada en el servicio.)

## Verificación

Tras ejecutar la migración, intenta de nuevo la aprobación manual del préstamo. Debería completarse sin error 500.
