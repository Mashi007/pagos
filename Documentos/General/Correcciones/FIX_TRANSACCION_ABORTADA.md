# 🔧 FIX: Error "current transaction is aborted"

**Fecha**: 2025-11-04  
**Error**: `sqlalchemy.exc.InternalError: (psycopg2.errors.InFailedSqlTransaction) current transaction is aborted, commands ignored until end of transaction block`

---

## 🔍 PROBLEMA

Cuando una query falla dentro de una transacción en PostgreSQL, la transacción se marca como "abortada". Todas las queries subsecuentes fallan hasta que se hace `ROLLBACK` o `COMMIT`.

**Síntoma:**
```
File "dashboard.py", line 1111, in dashboard_administrador
    total_financiamiento_operaciones = float(total_financiamiento_query.scalar() or Decimal("0"))
sqlalchemy.exc.InternalError: (psycopg2.errors.InFailedSqlTransaction) 
current transaction is aborted, commands ignored until end of transaction block
```

**Causa raíz:**
- Un error en el bloque `try-except` de evolución mensual (líneas 995-1098) abortó la transacción
- El `except` capturó el error pero NO hizo `rollback()`
- Cuando se intentó ejecutar la siguiente query (línea 1111), PostgreSQL rechazó la query porque la transacción estaba abortada

---

## ✅ SOLUCIÓN IMPLEMENTADA

### 1. Rollback en bloque except de evolución mensual

```python
except Exception as e:
    logger.warning(f"Error calculando evolución mensual: {e}")
    try:
        db.rollback()  # ✅ Restaurar transacción después de error
    except Exception:
        pass
    evolucion_mensual = []
```

### 2. Protección de queries críticas

Envolvimos las queries críticas en `try-except` con `rollback()`:

- **`total_financiamiento_query`** (línea 1106-1123)
- **`cartera_cobrada_query`** (línea 1141-1154)
- **`query_meta_mensual`** (línea 1167-1187)

### 3. Rollback en try-except global

```python
except Exception as e:
    logger.error(f"Error en dashboard admin: {e}", exc_info=True)
    try:
        db.rollback()  # ✅ Restaurar transacción después de error
    except Exception:
        pass
    raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
```

---

## 📊 IMPACTO

### Antes:
- ❌ Error 500 cuando cualquier query fallaba
- ❌ Transacción abortada bloqueaba todas las queries subsecuentes
- ❌ No se podía recuperar de errores parciales

### Después:
- ✅ Rollback automático restaura la transacción
- ✅ Queries subsecuentes pueden ejecutarse normalmente
- ✅ Valores por defecto (0.0) cuando falla una query específica
- ✅ Endpoint más resiliente a errores parciales

---

## 🔄 COMPORTAMIENTO

1. **Si una query falla en evolución mensual:**
   - Se hace `rollback()`
   - `evolucion_mensual = []` (array vacío)
   - El resto del endpoint continúa normalmente

2. **Si `total_financiamiento_query` falla:**
   - Se hace `rollback()`
   - `total_financiamiento_operaciones = 0.0`
   - Las queries subsecuentes funcionan normalmente

3. **Si cualquier query crítica falla:**
   - Se hace `rollback()`
   - Se usa valor por defecto seguro
   - El endpoint responde con datos parciales (mejor que error 500)

---

## ✅ VERIFICACIÓN

Después del deploy, verificar que:
- ✅ `/api/v1/dashboard/admin?periodo=mes` responde exitosamente
- ✅ No aparecen errores de "transaction is aborted" en logs
- ✅ Si hay errores parciales, el endpoint responde con valores por defecto

---

## 📝 NOTAS TÉCNICAS

- **Rollback anidado**: El `rollback()` dentro de `try-except` está protegido porque si el rollback mismo falla, no queremos que rompa el flujo
- **Valores por defecto**: Usamos `0.0` para cálculos numéricos y `[]` para arrays vacíos
- **Logging**: Se mantiene logging detallado para diagnóstico pero no bloquea la ejecución

---

**Commit**: `7844fe10` - fix: Agregar rollback de transacción en dashboard_administrador

