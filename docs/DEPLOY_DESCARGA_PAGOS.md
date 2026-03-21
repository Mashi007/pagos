## Despliegue: Descarga de Pagos Aprobados

### Pasos de Despliegue

#### Opción A: Despliegue Automatizado (Recomendado)

```bash
cd /ruta/proyecto/pagos
python tools/_deploy_descarga_pagos.py
```

Este script hace 3 cosas automáticamente:
1. ✅ Aplica migración Alembic (crear tabla `pagos_pendiente_descargar`)
2. ✅ Migra todos los pagos aprobados existentes a la tabla
3. ✅ Verifica integridad de los datos

---

#### Opción B: Despliegue Manual por Pasos

**Paso 1: Aplicar Migración Alembic**

En el directorio `backend`:
```bash
cd backend
alembic upgrade head
```

Debería ver algo como:
```
INFO  [alembic.runtime.migration] Running upgrade 020_pagos_reportados_exportados 
-> 021_pagos_pendiente_descargar
INFO  [alembic.runtime.migration] Running upgrade 021_pagos_pendiente_descargar -> head
```

**Paso 2: Migrar Datos Existentes**

Opción B1 - Con Python:
```bash
python tools/_migrate_pagos_aprobados_a_tabla_temporal.py
```

Opción B2 - Con SQL Directo (PostgreSQL):
```bash
psql -U usuario -d rapicredit_db -f backend/sql_migrate_pagos_aprobados.sql
```

**Paso 3: Verificar**

En Python:
```bash
python -c "
import sys
sys.path.insert(0, 'backend')
from app.core.database import SessionLocal
from app.models import PagoPendienteDescargar
db = SessionLocal()
count = db.query(PagoPendienteDescargar).count()
print(f'Total pagos en tabla temporal: {count}')
db.close()
"
```

En SQL:
```sql
SELECT COUNT(*) as total_en_tabla_temporal FROM pagos_pendiente_descargar;
```

---

#### Opción C: Despliegue en Producción (Render/Docker)

**Método 1: Pre-deploy Script (Recomendado)**

Agregar a `render.yaml` o configuración de despliegue:

```yaml
preDeployCommand: "cd backend && alembic upgrade head && cd ../backend && python tools/_migrate_pagos_aprobados_a_tabla_temporal.py"
```

**Método 2: Ejecutar Manualmente en la Consola del Servidor**

1. Conectar a la consola del servidor Render
2. Ejecutar:
   ```bash
   cd /app
   python tools/_deploy_descarga_pagos.py
   ```

**Método 3: Ejecutar en Contenedor Docker**

```bash
docker exec -it contenedor_pagos python tools/_deploy_descarga_pagos.py
```

---

### Verificación Post-Despliegue

1. **Verificar tabla creada:**
   ```sql
   \dt pagos_pendiente_descargar
   ```

2. **Contar pagos migrados:**
   ```sql
   SELECT COUNT(*) FROM pagos_pendiente_descargar;
   ```

3. **Ver detalle de pagos:**
   ```sql
   SELECT 
       ppd.id,
       pr.referencia_interna,
       pr.nombres,
       pr.apellidos,
       pr.monto,
       pr.moneda,
       ppd.created_at
   FROM pagos_pendiente_descargar ppd
   JOIN pagos_reportados pr ON pr.id = ppd.pago_reportado_id
   ORDER BY ppd.created_at DESC
   LIMIT 10;
   ```

4. **Prueba en la UI:**
   - Ir a `https://rapicredit.onrender.com/pagos/cobros/pagos-reportados`
   - Debería haber un botón "Descargar de Tabla Temporal"
   - Si hay pagos aprobados migrados, el botón debería estar habilitado
   - Hacer click para descargar Excel

---

### Rollback (En caso de error)

**Opción 1: Revertir migración Alembic**

```bash
cd backend
alembic downgrade -1
```

Esto deshace la creación de la tabla `pagos_pendiente_descargar`.

**Opción 2: Limpiar tabla sin eliminarla**

```sql
DELETE FROM pagos_pendiente_descargar;
```

**Opción 3: Eliminar tabla completamente**

```sql
DROP TABLE pagos_pendiente_descargar;
DROP INDEX ix_pagos_pendiente_descargar_id;
DROP INDEX ix_pagos_pendiente_descargar_pago_reportado_id;
```

---

### Troubleshooting

**Problema: "Table pagos_pendiente_descargar does not exist"**

**Solución:**
- La migración Alembic no se ha aplicado
- Ejecutar: `cd backend && alembic upgrade head`

---

**Problema: "Duplicate key value violates unique constraint"**

**Solución:**
- Hay pagos duplicados en la tabla
- Limpiar y reintentar:
  ```sql
  DELETE FROM pagos_pendiente_descargar WHERE id IN (
    SELECT id FROM pagos_pendiente_descargar 
    ORDER BY created_at DESC OFFSET 1
  );
  ```

---

**Problema: "No module named app"**

**Solución:**
- Asegurarse de ejecutar scripts desde la raíz del proyecto
- Verificar que existe `backend/app/`

---

**Problema: El botón no aparece en la UI**

**Solución:**
- Limpiar caché del navegador (Ctrl+Shift+Del)
- Recargar la página (Ctrl+R o F5)
- Si persiste, verificar consola del navegador (F12 → Console) para errores

---

### Monitoreo

**Verificar que todo está funcionando:**

```bash
# Contar pagos disponibles para descargar
SELECT COUNT(*) FROM pagos_pendiente_descargar;

# Ver última descarga
SELECT 
    MAX(created_at) as ultima_actualizacion,
    COUNT(*) as pagos_disponibles
FROM pagos_pendiente_descargar;

# Auditoría: ver qué pagos se migaron
SELECT 
    pr.referencia_interna,
    pr.estado,
    pr.nombres,
    ppd.created_at
FROM pagos_pendiente_descargar ppd
JOIN pagos_reportados pr ON pr.id = ppd.pago_reportado_id
WHERE ppd.created_at > NOW() - INTERVAL '1 day'
ORDER BY ppd.created_at DESC;
```

---

### Preguntas Frecuentes

**P: ¿Se eliminarán los pagos de la tabla al descargar?**
R: Sí. Una vez que hagas click en "Descargar de Tabla Temporal", la tabla se vacía completamente.

**P: ¿Se pierden los datos de los pagos aprobados?**
R: No. Los datos siguen en la tabla `pagos_reportados` (permanente). Solo se eliminan de la tabla temporal.

**P: ¿Puedo descargar nuevamente los mismos pagos?**
R: Solo si vuelves a aprobarlos o agregas nuevos. Una vez descargados, solo nuevos pagos aprobados aparecerán.

**P: ¿Qué pasa si la migración falla a mitad?**
R: Los cambios se revierten automáticamente (transacción ACID). Puedes reintentar sin riesgo.

**P: ¿Cuánto tiempo toma migrar millones de pagos?**
R: Depende de la BD, pero típicamente < 1 segundo por cada 10,000 pagos.
