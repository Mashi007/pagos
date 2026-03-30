## 🐛 ERROR CORREGIDO

### El Problema
```
SQL Error [42703]: ERROR: column "tablename" does not exist
Position: 296
```

### La Causa
La columna `tablename` no existe en las vistas de PostgreSQL:
- `pg_indexes` → NO tiene `tablename` 
- `pg_stat_user_indexes` → NO tiene `tablename`

### La Solución
Remover referencias a `tablename` y usar solo:
- `schemaname` ✅
- `indexname` ✅
- `idx_scan` ✅

### Cambios
```sql
-- ❌ ANTES (ERROR)
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE indexname IN (...)

-- ✅ DESPUÉS (CORRECTO)
SELECT schemaname, indexname, indexdef
FROM pg_indexes
WHERE indexname IN (...)
```

### Commit
```
3a864159 fix: corregir SQL - remover columna 'tablename'
```

---

## ✅ YA PUEDES EJECUTAR EL SQL

```bash
# SQL puro
psql $DATABASE_URL < backend/sql/033_MIGRACION_INDICES_PUBLICOS_2026_03_30.sql

# O con PowerShell
Get-Content backend/sql/033_MIGRACION_INDICES_PUBLICOS_2026_03_30.sql | psql $env:DATABASE_URL
```

---

## 📝 VERIFICACIÓN RÁPIDA

```sql
-- Debería crear 5 índices sin errores
SELECT COUNT(*) FROM pg_indexes 
WHERE indexname LIKE 'idx_%';

-- Resultado esperado: 5 ✅
```

¡Ahora sí está listo! 🚀
