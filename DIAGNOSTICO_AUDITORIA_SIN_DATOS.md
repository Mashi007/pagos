# 🔍 Diagnóstico: No aparecen datos en /auditoria

## 📋 Problema Identificado

El endpoint `/api/v1/auditoria` no muestra datos porque **faltan tablas de auditoría en la base de datos**.

### Estado Actual de las Tablas

| Tabla | Estado | Registros |
|-------|--------|-----------|
| `auditoria` | ❌ **NO EXISTE** | - |
| `prestamos_auditoria` | ✅ Existe | 0 |
| `pagos_auditoria` | ❌ **NO EXISTE** | - |

## 🔍 Causa Raíz

Las migraciones de Alembic que crean las tablas `auditoria` y `pagos_auditoria` **no se han ejecutado** en la base de datos de producción.

### Migraciones Pendientes

1. **`003_create_auditoria_table.py`** - Crea la tabla `auditoria`
2. **`20251028_actualizar_modelos_pago.py`** - Crea la tabla `pagos_auditoria`
3. **`20251027_create_tablas_prestamos.py`** - Ya ejecutada (tabla `prestamos_auditoria` existe)

## ✅ Solución

### Opción 1: Ejecutar Migraciones en Render (Recomendado)

1. **Acceder a Render Web Shell:**
   - Ve a tu dashboard de Render
   - Selecciona el servicio de backend
   - Abre "Shell" o "Web Shell"

2. **Ejecutar migraciones:**
   ```bash
   cd backend
   alembic upgrade head
   ```

3. **Verificar que se crearon las tablas:**
   ```bash
   python scripts/python/diagnosticar_auditoria.py
   ```

### Opción 2: Ejecutar Migraciones Localmente (si tienes acceso a la BD)

```bash
cd backend
alembic upgrade head
```

### Opción 3: Crear Tablas Manualmente (Solo si las migraciones fallan)

Si las migraciones no funcionan, puedes crear las tablas manualmente ejecutando el SQL directamente:

#### Tabla `auditoria`:
```sql
CREATE TABLE IF NOT EXISTS auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES users(id),
    accion VARCHAR(50) NOT NULL,
    entidad VARCHAR(50) NOT NULL,
    entidad_id INTEGER,
    detalles TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    exito BOOLEAN NOT NULL DEFAULT true,
    mensaje_error TEXT,
    fecha TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_auditoria_id ON auditoria(id);
CREATE INDEX IF NOT EXISTS ix_auditoria_usuario_id ON auditoria(usuario_id);
CREATE INDEX IF NOT EXISTS ix_auditoria_accion ON auditoria(accion);
CREATE INDEX IF NOT EXISTS ix_auditoria_entidad ON auditoria(entidad);
CREATE INDEX IF NOT EXISTS ix_auditoria_entidad_id ON auditoria(entidad_id);
CREATE INDEX IF NOT EXISTS ix_auditoria_fecha ON auditoria(fecha);
```

#### Tabla `pagos_auditoria`:
```sql
CREATE TABLE IF NOT EXISTS pagos_auditoria (
    id SERIAL PRIMARY KEY,
    pago_id INTEGER NOT NULL,
    usuario VARCHAR(100) NOT NULL,
    campo_modificado VARCHAR(100) NOT NULL,
    valor_anterior VARCHAR(500),
    valor_nuevo VARCHAR(500) NOT NULL,
    accion VARCHAR(50) NOT NULL,
    observaciones TEXT,
    fecha_cambio TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_pagos_auditoria_pago_id ON pagos_auditoria(pago_id);
CREATE INDEX IF NOT EXISTS ix_pagos_auditoria_fecha_cambio ON pagos_auditoria(fecha_cambio);
```

## 📊 Verificación Post-Solución

Después de ejecutar las migraciones, verifica que todo funciona:

```bash
python scripts/python/diagnosticar_auditoria.py
```

Deberías ver:
- ✅ Tabla 'auditoria': existe
- ✅ Tabla 'pagos_auditoria': existe
- ✅ Tabla 'prestamos_auditoria': existe

## 💡 Notas Importantes

1. **Datos iniciales:** Inicialmente las tablas estarán vacías. Esto es normal.
2. **Generar datos:** Los registros de auditoría se crearán automáticamente cuando:
   - Se realicen acciones en préstamos (se guardará en `prestamos_auditoria`)
   - Se realicen acciones en pagos (se guardará en `pagos_auditoria`)
   - Se registren eventos genéricos (se guardará en `auditoria`)

3. **El endpoint funciona correctamente:** El código del endpoint está bien implementado. El problema es solo que faltan las tablas.

## 🔧 Mejoras Implementadas

Se ha mejorado el endpoint para:
- Mostrar mensajes más claros cuando las tablas no existen
- Registrar mejor información en los logs
- Manejar mejor los casos donde no hay datos

---

**Fecha del diagnóstico:** 2025-01-27  
**Script de diagnóstico:** `scripts/python/diagnosticar_auditoria.py`
