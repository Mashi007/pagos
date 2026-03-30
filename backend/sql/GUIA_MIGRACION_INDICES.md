# 📋 GUÍA DE MIGRACIÓN: Índices para APIs Públicas

## 🎯 Resumen

Crear 5 índices compuestos en BD para optimizar endpoints públicos lentos:
- `/validar-cedula`: 271ms → ~50ms
- `/recibo-cuota`: 1170ms → ~300ms
- `/pagos-reportados/listado-y-kpis`: 918ms → ~300ms

**Tiempo estimado:** 2-5 minutos (depende del tamaño de BD)
**Risk level:** ⚠️ BAJO (CREATE INDEX IF NOT EXISTS es idempotente)

---

## 📁 Archivos

```
backend/sql/
├── 033_MIGRACION_INDICES_PUBLICOS_2026_03_30.sql  (SQL puro)
├── aplicar_migracion.sh                            (Bash/Linux/Mac)
└── aplicar_migracion.ps1                           (PowerShell/Windows)
```

---

## 🚀 OPCIÓN 1: SQL Puro (Recomendado)

### Prerequisitos
- Cliente PostgreSQL conectado a BD de producción
- Permisos: CREATE INDEX

### Ejecución

```bash
# Linux/Mac
psql $DATABASE_URL < backend/sql/033_MIGRACION_INDICES_PUBLICOS_2026_03_30.sql

# Windows (PowerShell)
Get-Content backend/sql/033_MIGRACION_INDICES_PUBLICOS_2026_03_30.sql | psql $env:DATABASE_URL

# O en DBeaver/pgAdmin: Copy-paste el contenido del archivo en Query Editor
```

### Verificación

```sql
-- Ejecutar en BD después de migración:
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE indexname IN (
    'idx_cliente_cedula',
    'idx_estado_cuenta_codigo_cedula_activo',
    'idx_prestamo_cliente_estado',
    'idx_pago_reportado_cedula_estado',
    'idx_cuota_prestamo'
)
ORDER BY tablename;

-- Resultado esperado: 5 filas (5 índices creados)
```

---

## 🚀 OPCIÓN 2: Script Bash (Linux/Mac)

### Prerequisitos
- `bash` disponible
- `psql` instalado
- `DATABASE_URL` configurada

### Ejecución

```bash
# 1. Hacer script ejecutable
chmod +x backend/sql/aplicar_migracion.sh

# 2. Ejecutar
cd backend/sql
./aplicar_migracion.sh

# O con variable explícita
DATABASE_URL="postgresql://user:pass@host/db" ./aplicar_migracion.sh
```

### Output esperado
```
═══════════════════════════════════════════════════════════
MIGRACIÓN: Crear índices para optimizar APIs públicas
Fecha: 2026-03-30
═══════════════════════════════════════════════════════════

✓ DATABASE_URL detectada

Ejecutando migración de índices...

idx_cliente_cedula creado
idx_estado_cuenta_codigo_cedula_activo creado
idx_prestamo_cliente_estado creado
idx_pago_reportado_cedula_estado creado
idx_cuota_prestamo creado

═══════════════════════════════════════════════════════════
✓ MIGRACIÓN COMPLETADA EXITOSAMENTE
═══════════════════════════════════════════════════════════
```

---

## 🚀 OPCIÓN 3: Script PowerShell (Windows)

### Prerequisitos
- PowerShell 5.0+
- `psql` instalado en PATH
- `DATABASE_URL` configurada

### Ejecución

```powershell
# 1. Permitir ejecución de scripts (si no está permitido)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 2. Ejecutar script
.\backend\sql\aplicar_migracion.ps1

# O con Database URL explícita
.\backend\sql\aplicar_migracion.ps1 -DatabaseUrl "postgresql://user:pass@host/db"

# Dry-run (mostrar SQL sin ejecutar)
.\backend\sql\aplicar_migracion.ps1 -DryRun
```

---

## ✅ VERIFICACIÓN POST-MIGRACIÓN

### 1. Verificar índices creados

```sql
SELECT 
    indexname,
    tablename,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename;
```

### 2. Verificar performance con EXPLAIN

```sql
-- Test 1: Búsqueda de cliente por cédula
EXPLAIN ANALYZE
SELECT * FROM clientes 
WHERE cedula = 'V12345678';

-- Esperado: Index Scan (no Seq Scan)
-- Time: < 1ms

-- Test 2: Búsqueda de códigos activos
EXPLAIN ANALYZE
SELECT * FROM estado_cuenta_codigos 
WHERE cedula_normalizada = 'V12345678' 
  AND usado = FALSE 
  AND expira_en > NOW();

-- Esperado: Index Scan (composite index)

-- Test 3: Validación de préstamos
EXPLAIN ANALYZE
SELECT * FROM prestamos 
WHERE cliente_id = 123 
  AND estado = 'APROBADO';

-- Esperado: Index Scan

-- Test 4: Pagos reportados
EXPLAIN ANALYZE
SELECT * FROM pagos_reportados 
WHERE tipo_cedula = 'V' 
  AND numero_cedula = '12345678' 
  AND estado = 'aprobado';

-- Esperado: Index Scan

-- Test 5: Cuotas de préstamo
EXPLAIN ANALYZE
SELECT * FROM cuotas 
WHERE prestamo_id = 456 
  AND estado != 'CANCELADA'
ORDER BY numero_cuota;

-- Esperado: Index Scan
```

### 3. Monitorear uso de índices

```sql
-- Después de 1 hora de operación:
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE indexname LIKE 'idx_cliente%' 
   OR indexname LIKE 'idx_estado_cuenta%'
   OR indexname LIKE 'idx_prestamo%'
   OR indexname LIKE 'idx_pago_reportado%'
   OR indexname LIKE 'idx_cuota%'
ORDER BY idx_scan DESC;

-- Esperado: idx_scan > 0 en índices activos
```

---

## 🔧 MANTENIMIENTO

### VACUUM ANALYZE (después de migración)

```sql
-- En la BD
VACUUM ANALYZE;

-- O desde línea de comando
vacuumdb -d nombre_bd -z

-- Desde bash
psql $DATABASE_URL -c 'VACUUM ANALYZE;'
```

### REINDEX (si es necesario)

```sql
-- Si fragmentación es > 20%:
REINDEX INDEX idx_cliente_cedula;
REINDEX INDEX idx_estado_cuenta_codigo_cedula_activo;
REINDEX INDEX idx_prestamo_cliente_estado;
REINDEX INDEX idx_pago_reportado_cedula_estado;
REINDEX INDEX idx_cuota_prestamo;
```

---

## 📊 IMPACTO ESPERADO

| Endpoint | Antes | Después | Mejora |
|----------|-------|---------|--------|
| `/validar-cedula` | 271ms | ~50ms | ↓ 82% |
| `/recibo-cuota` | 1170ms | ~300ms | ↓ 74% |
| `/pagos-reportados/listado-y-kpis` | 918ms | ~300ms | ↓ 67% |
| `/solicitar-codigo` | 500ms* | ~100ms | ↓ 80% |
| `/verificar-codigo` | 1000ms* | ~200ms | ↓ 80% |

*Estimado

---

## ⚠️ TROUBLESHOOTING

### Error: "ya existe índice"
```
ERROR: index "idx_cliente_cedula" already exists
```
**Solución:** Normal, `CREATE INDEX IF NOT EXISTS` es idempotente. Continuar.

### Error: "permiso denegado"
```
ERROR: permission denied for schema public
```
**Solución:** Verificar permisos del usuario. Usar superuser o usuario con CREATE INDEX.

### Error: "tabla no existe"
```
ERROR: relation "clientes" does not exist
```
**Solución:** Verificar que la migración Alembic anterior se ejecutó correctamente.

### Query lenta después de migración
```sql
-- Ejecutar ANALYZE para actualizar estadísticas:
ANALYZE;

-- O específicamente:
ANALYZE clientes;
ANALYZE estado_cuenta_codigos;
ANALYZE prestamos;
ANALYZE pagos_reportados;
ANALYZE cuotas;
```

---

## 📋 CHECKLIST

- [ ] Backup de BD ejecutado (RECOMENDADO)
- [ ] DATABASE_URL configurada correctamente
- [ ] Ejecutar migración SQL (opción 1, 2 o 3)
- [ ] Verificar que 5 índices fueron creados
- [ ] Ejecutar VACUUM ANALYZE
- [ ] Verificar EXPLAIN ANALYZE en queries críticas
- [ ] Monitorear endpoints públicos en próximas 24h
- [ ] Documentar tiempos de respuesta (antes/después)

---

## 📞 SOPORTE

Si algo falla:

1. Verificar en BD:
   ```sql
   SELECT * FROM pg_indexes WHERE indexname LIKE 'idx_%';
   ```

2. Revisar logs de errores:
   ```bash
   tail -n 100 /var/log/postgresql/postgresql.log
   ```

3. Rollback (si es necesario):
   ```sql
   DROP INDEX IF EXISTS idx_cliente_cedula;
   DROP INDEX IF EXISTS idx_estado_cuenta_codigo_cedula_activo;
   DROP INDEX IF EXISTS idx_prestamo_cliente_estado;
   DROP INDEX IF EXISTS idx_pago_reportado_cedula_estado;
   DROP INDEX IF EXISTS idx_cuota_prestamo;
   ```

---

**Generado:** 2026-03-30  
**Commit:** c9fd4f75 (optimización de rendimiento y seguridad)
