# 📋 INSTRUCCIONES: RECONCILIACIÓN DE PAGOS EN DBEAVER

## 🎯 Objetivo

Vincular pagos con cuotas usando múltiples estrategias directamente en DBeaver, evitando problemas de encoding de Python.

---

## 🚀 PASO 1: Preparar DBeaver

### 1.1 Abrir DBeaver y conectar a la base de datos

1. Abre DBeaver
2. Conecta a tu base de datos PostgreSQL
3. Verifica que tienes permisos de escritura (UPDATE, INSERT)

### 1.2 Configurar modo TRANSACCIÓN (IMPORTANTE)

**Opción A: Desactivar Auto-commit**
1. Click derecho en la conexión
2. Selecciona "Edit Connection"
3. Pestaña "Connection settings"
4. **Desmarca "Auto-commit"** (esto permite hacer ROLLBACK si hay problemas)

**Opción B: Usar BEGIN/COMMIT manualmente**
- El script SQL ya incluye `BEGIN;` al inicio
- Al final, ejecutarás `COMMIT;` o `ROLLBACK;` según los resultados

---

## 📝 PASO 2: Ejecutar el Script SQL

### 2.1 Abrir el script

1. En DBeaver, abre el archivo: `backend/scripts/RECONCILIAR_PAGOS_CUOTAS.sql`
2. O copia y pega el contenido en una nueva ventana SQL

### 2.2 Ejecutar sección por sección (Recomendado)

**IMPORTANTE:** Ejecuta el script sección por sección para revisar los resultados:

1. **Sección 1.1:** Ver cuántos pagos tienen información
   - Ejecuta y revisa el resultado
   - Deberías ver cuántos pagos tienen `prestamo_id` y `numero_cuota`

2. **Sección 1.2:** Actualizar cuotas (Estrategia 1)
   - ⚠️ Esta es una operación de escritura
   - Ejecuta y revisa cuántas filas se actualizaron

3. **Sección 1.3:** Verificar resultados
   - Ejecuta y revisa cuántas cuotas se actualizaron

4. **Sección 2.1:** Ver pagos sin información
   - Ejecuta y revisa cuántos pagos NO tienen `prestamo_id` o `numero_cuota`

5. **Sección 2.2:** Vincular pagos (Estrategia 2A - fecha exacta)
   - ⚠️ Esta es una operación de escritura
   - Ejecuta y revisa cuántas filas se actualizaron

6. **Sección 2.3:** Vincular pagos (Estrategia 2B - rango de fechas)
   - ⚠️ Esta es una operación de escritura
   - Ejecuta y revisa cuántas filas se actualizaron

7. **Sección 2.4:** Actualizar cuotas después de vincular
   - ⚠️ Esta es una operación de escritura
   - Ejecuta y revisa cuántas filas se actualizaron

8. **Sección 3.1:** Ver cuotas pagadas sin pagos
   - Ejecuta y revisa cuántas cuotas están marcadas como PAGADO sin pagos

9. **Sección 3.2:** Corregir cuotas pagadas sin pagos
   - ⚠️ Esta es una operación de escritura
   - Ejecuta y revisa cuántas filas se actualizaron

10. **Sección 4:** Resumen final
    - Ejecuta todas las queries de resumen
    - Revisa los resultados cuidadosamente

---

## ✅ PASO 3: Decidir COMMIT o ROLLBACK

### 3.1 Revisar resultados

Antes de hacer COMMIT, verifica:

- ✅ ¿Los pagos se vincularon correctamente?
- ✅ ¿Las cuotas tienen `total_pagado` actualizado?
- ✅ ¿Los estados de las cuotas son correctos?
- ✅ ¿La morosidad mensual tiene sentido?

### 3.2 Si los resultados son correctos:

```sql
COMMIT;
```

### 3.3 Si hay problemas o quieres revertir:

```sql
ROLLBACK;
```

---

## 🔍 VERIFICACIÓN POST-RECONCILIACIÓN

### Query 1: Verificar pagos vinculados

```sql
SELECT
    COUNT(*) as total_pagos_vinculados,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados,
    SUM(monto_pagado) as monto_total
FROM pagos
WHERE activo = true
  AND prestamo_id IS NOT NULL
  AND numero_cuota IS NOT NULL
  AND monto_pagado > 0;
```

**Resultado esperado:**
- Deberías ver un número significativo de pagos vinculados (no 0)

### Query 2: Verificar cuotas con pagos

```sql
SELECT
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
    SUM(total_pagado) as monto_total_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';
```

**Resultado esperado:**
- `cuotas_con_pagos` debería ser > 0
- `monto_total_pagado` debería ser > 0

### Query 3: Verificar morosidad mensual

```sql
SELECT
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'YYYY-MM') as mes,
    SUM(c.monto_cuota) as monto_programado,
    SUM(COALESCE(c.total_pagado, 0)) as monto_pagado,
    SUM(c.monto_cuota) - SUM(COALESCE(c.total_pagado, 0)) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes DESC;
```

**Resultado esperado:**
- `monto_pagado` debería mostrar valores > 0 (no todos en 0)
- `morosidad` debería ser `monto_programado - monto_pagado`

---

## ⚠️ IMPORTANTE

1. **Siempre ejecuta en modo TRANSACCIÓN** para poder hacer ROLLBACK
2. **Revisa los resultados** de cada sección antes de continuar
3. **Haz backup** de la base de datos antes de ejecutar (si es posible)
4. **Ejecuta sección por sección** para identificar problemas temprano

---

## 🆘 Si algo sale mal

1. **Ejecuta ROLLBACK inmediatamente:**
   ```sql
   ROLLBACK;
   ```

2. **Revisa los logs de DBeaver** para ver qué query falló

3. **Verifica permisos** de la base de datos

4. **Revisa constraints** de la base de datos (foreign keys, etc.)

---

## 📊 Resultados Esperados

Después de la reconciliación exitosa:

- ✅ **Pagos vinculados:** > 0 (idealmente la mayoría de los 13,679 pagos)
- ✅ **Cuotas con pagos:** > 0 (idealmente miles de cuotas)
- ✅ **Monto total pagado:** > 0 (debería ser significativo)
- ✅ **Morosidad mensual:** Muestra valores reales de pagos (no todos en 0)

---

## ✅ Checklist Final

- [ ] Script ejecutado sección por sección
- [ ] Resultados revisados en cada sección
- [ ] Queries de verificación ejecutadas
- [ ] Resultados son correctos
- [ ] COMMIT ejecutado (o ROLLBACK si hay problemas)
- [ ] Dashboard verificado (debería mostrar pagos ahora)

---

**Última actualización:** 2025-01-06

