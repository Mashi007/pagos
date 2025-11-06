# 📋 INSTRUCCIONES: Ejecutar Optimizaciones

## ✅ Estado Actual

**Todas las optimizaciones de código han sido implementadas:**
- ✅ Eliminado N+1 queries
- ✅ Combinadas queries múltiples
- ✅ Optimizadas queries SQL directas

**Pendiente:** Ejecutar script de índices de BD

---

## 🚀 PASO 1: Ejecutar Script de Índices

### Opción A: Desde psql (Recomendado)

```bash
# Conectar a la base de datos
psql -U tu_usuario -d tu_base_datos

# Ejecutar script
\i backend/scripts/migracion_indices_dashboard.sql

# Verificar índices creados
\di idx_*_dashboard*
```

### Opción B: Desde línea de comandos

```bash
psql -U tu_usuario -d tu_base_datos -f backend/scripts/migracion_indices_dashboard.sql
```

### Opción C: Desde Python (si tienes acceso)

```python
from app.db.session import engine

with open('backend/scripts/migracion_indices_dashboard.sql', 'r') as f:
    sql = f.read()
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
```

---

## ⚠️ IMPORTANTE

1. **Ejecutar durante horario de bajo tráfico** - Los índices pueden tardar varios minutos
2. **Verificar espacio en disco** - Los índices ocupan espacio adicional
3. **Monitorear durante creación** - Verificar que no haya bloqueos

---

## 🔍 PASO 2: Verificar que los Índices Funcionen

```sql
-- Verificar que PostgreSQL use los índices
EXPLAIN ANALYZE 
SELECT 
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    COUNT(*)
FROM prestamos
WHERE estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion);
```

**Resultado esperado:** Debe mostrar `Index Scan using idx_prestamos_fecha_aprobacion_ym`

---

## 🧪 PASO 3: Probar Endpoints Optimizados

### 1. Probar resumen de préstamos (N+1 eliminado):
```bash
curl -X GET "http://localhost:8000/api/v1/prestamos/cedula/1234567890/resumen" \
  -H "Authorization: Bearer tu_token"
```

**Antes:** 500-1000ms  
**Después:** 100-200ms (esperado)

### 2. Probar KPIs principales (queries combinadas):
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/kpis-principales" \
  -H "Authorization: Bearer tu_token"
```

**Antes:** 2000-3000ms  
**Después:** 500-800ms (esperado)

### 3. Probar tendencia mensual (SQL optimizado):
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/financiamiento-tendencia-mensual?meses=12" \
  -H "Authorization: Bearer tu_token"
```

**Antes:** 2000-5000ms  
**Después:** 300-600ms (esperado)

---

## 📊 PASO 4: Monitorear Mejoras

### Ver logs de rendimiento:
```bash
# Los logs mostrarán tiempos mejorados
grep "Completado en" logs/app.log
grep "Query completada en" logs/app.log
```

### Comparar antes/después:
- Anotar tiempos antes de optimizaciones
- Anotar tiempos después de optimizaciones
- Calcular mejora porcentual

---

## ✅ Checklist Final

- [ ] Script de índices ejecutado
- [ ] Índices verificados con EXPLAIN ANALYZE
- [ ] Endpoints probados y funcionando
- [ ] Tiempos de respuesta mejorados
- [ ] Sin errores en logs
- [ ] Resultados idénticos a antes (validación)

---

## 🆘 Troubleshooting

### Si los índices no se crean:
```sql
-- Verificar si ya existen
SELECT indexname FROM pg_indexes WHERE indexname LIKE 'idx_%_dashboard%';

-- Si existen, eliminarlos primero
DROP INDEX IF EXISTS idx_prestamos_fecha_aprobacion_ym;
-- Luego ejecutar script nuevamente
```

### Si los índices no se usan:
```sql
-- Actualizar estadísticas
ANALYZE prestamos;
ANALYZE cuotas;
ANALYZE pagos;

-- Verificar configuración
SHOW enable_seqscan;  -- Debe ser ON (por defecto)
```

### Si hay errores de sintaxis:
- Verificar versión de PostgreSQL (debe ser 9.5+)
- Verificar que las funciones EXTRACT estén disponibles

---

## 📝 Notas

- Los índices se crean automáticamente si no existen (`IF NOT EXISTS`)
- Los índices no afectan la lógica de negocio, solo mejoran rendimiento
- Si necesitas revertir, puedes eliminar los índices sin afectar datos

---

## 🎉 Resultado Esperado

Después de ejecutar todas las optimizaciones:

- ✅ Dashboard carga 3-5x más rápido
- ✅ Menos carga en base de datos
- ✅ Mejor experiencia de usuario
- ✅ Código más mantenible y eficiente

