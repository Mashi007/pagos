# Solución: Error 500 en GET `/api/v1/prestamos/{id}/cuotas`

## Problema

El endpoint `GET /api/v1/prestamos/4615/cuotas` retornaba un error 500:

```
Error 500 del servidor: 
Object { detail: "Error interno del servidor", message: undefined, ... }
```

### Causa Raíz

PostgreSQL error durante el `flush()` de SQLAlchemy:

```
psycopg2.errors.ObjectNotInPrerequisiteState: 
cannot refresh materialized view "public.clientes_retrasados_mv" concurrently

HINT: Create a unique index with no WHERE clause on one or more columns 
of the materialized view.
```

**Origen del error:**

1. Al llamar `GET /prestamos/4615/cuotas`, la función `_listado_cuotas_prestamo_dicts()` llama a `sincronizar_pagos_pendientes_a_prestamos(db, [4615])`
2. Esta función ejecuta `reset_y_reaplicar_cascada_prestamo()` que actualiza las cuotas
3. Al hacer `db.flush()`, SQLAlchemy ejecuta un UPDATE en la tabla `cuotas`
4. Esto dispara el trigger `trigger_actualizar_retraso_snapshot` (creado en Phase 2)
5. El trigger intenta hacer `REFRESH MATERIALIZED VIEW CONCURRENTLY clientes_retrasados_mv`
6. PostgreSQL rechaza esto porque la vista no tiene un índice único sin WHERE

### Requisito PostgreSQL

Para usar `REFRESH MATERIALIZED VIEW CONCURRENTLY`, PostgreSQL requiere:
- Un índice UNIQUE en la vista materializada
- Sin cláusula WHERE (debe ser un índice simple)
- Permite refrescar la vista sin bloquear lecturas concurrentes

Sin el índice, la única opción es `REFRESH MATERIALIZED VIEW` (bloqueante).

## Solución

Crear dos índices únicos en las vistas materializadas:

```sql
-- En clientes_retrasados_mv, el campo `id` es único (es cliente_id)
CREATE UNIQUE INDEX idx_clientes_retrasados_mv_id 
ON clientes_retrasados_mv (id);

-- En pagos_kpis_mv, el campo `fecha_snapshot` es único (snapshot por día)
CREATE UNIQUE INDEX idx_pagos_kpis_mv_fecha
ON pagos_kpis_mv (fecha_snapshot);
```

### Archivos Modificados/Creados

1. **`alembic/versions/035_fix_materialized_views_indices.py`** (nueva migración)
   - Crea los índices en upgrade
   - Los elimina en downgrade

2. **`backend/sql/035_FIX_MV_INDICES.sql`** (SQL raw para ejecución directa)
   - SQL para crear los índices
   - Consulta de verificación

3. **Error handling en `prestamos.py`**
   - Agregado `try-except` en `_listado_cuotas_prestamo_dicts()` para capturar y loguear errores
   - Devuelve HTTPException 500 con mensaje descriptivo

## Cómo Aplicar

### Opción 1: Migración Alembic (Recomendado)

```bash
cd backend
alembic upgrade head
```

### Opción 2: SQL Directo

Ejecutar `sql/035_FIX_MV_INDICES.sql`:

```bash
psql $DATABASE_URL < sql/035_FIX_MV_INDICES.sql
```

### Opción 3: Python Script

```python
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_clientes_retrasados_mv_id ON clientes_retrasados_mv (id)"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_pagos_kpis_mv_fecha ON pagos_kpis_mv (fecha_snapshot)"
    ))
    conn.commit()
```

## Verificación

Después de aplicar la solución:

```bash
# Probar el endpoint nuevamente
curl "http://localhost:8000/api/v1/prestamos/4615/cuotas" \
  -H "Authorization: Bearer $TOKEN"

# Debe retornar 200 con la lista de cuotas
```

Script de prueba Python:

```python
from app.api.v1.endpoints.prestamos import _listado_cuotas_prestamo_dicts
from app.core.database import SessionLocal

db = SessionLocal()
resultado = _listado_cuotas_prestamo_dicts(db, 4615)
print(f"OK: Se obtuvieron {len(resultado)} cuotas")
db.close()
```

## Impacto

- ✅ Resuelve el error 500 del endpoint de cuotas
- ✅ Permite que el trigger `actualizar_retraso_snapshot` funcione correctamente
- ✅ Permite refrescar las vistas materializadas sin bloquear lecturas
- ✅ Mejora la concurrencia en operaciones de actualización de cuotas

## Referencias

- [PostgreSQL: REFRESH MATERIALIZED VIEW](https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html)
- [PostgreSQL: Materialized Views](https://www.postgresql.org/docs/current/rules-materializedviews.html)
