# Verificación: Todos los Pagos Están Conciliados

## Archivo SQL disponible

**`sql/verificacion_pagos_conciliados.sql`** contiene 8 consultas para validar:

### Las 8 consultas verifican:

```
1. RESUMEN GENERAL
   Total pagos vs cuotas pagadas vs prestamos liquidados

2. PAGOS NO CONCILIADOS
   Pagos que NO están aplicados a ninguna cuota

3. CUOTAS PAGADAS vs ESTADO EN BD
   Verifica que estado='PAGADO' coincida con pagos aplicados

4. CUOTAS CON DISCREPANCIAS (CRITICAS)
   - Cuota PAGADO sin monto completo
   - Cuota PENDIENTE pero 100% pagada
   - Pagos que exceden monto de cuota

5. PRESTAMOS: Pagos vs Capital
   - Total pagado vs capital de prestamo
   - Validación de estado LIQUIDADO vs 100% pago

6. DISTRIBUCION: Estados de conciliacion
   - OK: Correctamente conciliados
   - CRITICO: LIQUIDADO sin 100% pago
   - WARNING: Debe actualizarse a LIQUIDADO

7. PAGOS: Resumen por prestamo
   - Pagos registrados vs pagos aplicados a cuotas

8. ESTADISTICAS FINALES
   - Totales consolidados de cuotas, pagos, prestamos
```

## Resultados esperados (ÉXITO)

```
✅ Query #2: 0 filas (Ningún pago sin conciliar)
✅ Query #4: 0 filas (Ninguna discrepancia)
✅ Query #6: Solo "OK" (Todos correctamente conciliados)
✅ Query #7: 0 filas (Pagos y aplicaciones coinciden)

Estado esperado:
  - Total Cuotas: ~62,599
  - Cuotas PAGADAS: Aumentó después de conciliación masiva
  - Cuotas PENDIENTES: Disminuyó
  - Prestamos LIQUIDADO: ~109-115 (después de auto-actualización)
  - Prestamos 100% Pagados: Coincide con LIQUIDADO
```

## Cómo ejecutar

### Opción 1: DBeaver (Visual)
1. Abre DBeaver
2. Conecta a la BD
3. Abre: `sql/verificacion_pagos_conciliados.sql`
4. Ejecuta cada query (Ctrl+Enter)

### Opción 2: Terminal
```bash
psql -U usuario -d pagos_db < sql/verificacion_pagos_conciliados.sql
```

### Opción 3: Query rápida
```sql
-- Resumen rápido
SELECT 
  COUNT(DISTINCT c.id) AS total_cuotas,
  COUNT(DISTINCT c.id) FILTER (WHERE c.estado = 'PAGADO') AS cuotas_pagadas,
  COUNT(DISTINCT c.id) FILTER (WHERE c.estado = 'PENDIENTE') AS cuotas_pendientes,
  COUNT(DISTINCT p.id) AS prestamos_totales,
  COUNT(DISTINCT p.id) FILTER (WHERE p.estado = 'LIQUIDADO') AS prestamos_liquidados
FROM cuotas c
CROSS JOIN prestamos p;
```

## Interpretación de resultados

### Query #1: Resumen General
```
total_pagos              → Número de registros en tabla pago
cuotas_con_pagos         → Cuotas que tienen al menos 1 pago aplicado
cuotas_pagadas           → Cuotas donde estado = 'PAGADO'
total_pagado             → Suma de todos los montos pagados
prestamos_liquidados     → Prestamos donde estado = 'LIQUIDADO'
```

**Esperado:**
- `cuotas_pagadas` ≈ `cuotas_con_pagos` (deberían ser muy similares)
- `prestamos_liquidados` ≈ 109-115

### Query #2: Pagos No Conciliados
```
Si esta vacío (0 filas)  → ✅ OK: Todos los pagos están aplicados
Si tiene filas           → ⚠️ ERROR: Hay pagos sin aplicar a cuotas
```

### Query #3: Cuotas Pagadas vs Estado
```
validacion = 'OK'        → ✅ Cuota correctamente conciliada
validacion = 'ERROR'     → ❌ CRITICO: Estado no coincide con pagos
```

**Si hay ERRORs, significa:**
- Una cuota está marcada PAGADO pero no tiene pagos
- O está PENDIENTE pero tiene 100% de pagos aplicados

### Query #4: Cuotas con Discrepancias
```
Si esta vacío (0 filas)  → ✅ OK: Todas las cuotas conciliadas
Si tiene filas           → ❌ ERROR: Hay inconsistencias
```

**Tipos de inconsistencias:**
- `CRITICO: Marcada PAGADO pero no tiene monto completo`
- `ERROR: Marcada PENDIENTE pero está 100% pagada`
- `ERROR: Pagos exceden monto de cuota`

### Query #5: Prestamos - Validación de conciliacion
```
validacion_conciliacion = 'OK'                    → ✅ Correcto
= 'ERROR: LIQUIDADO pero no 100% pagado'        → ❌ CRITICO
= 'WARNING: APROBADO pero 100% pagado'           → ⚠️  Puede autofixearse
```

### Query #6: Distribucion
```
estado_conciliacion = 'OK'                       → ✅ Correctos
= 'CRITICO: LIQUIDADO sin 100% pago'            → ❌ Problemas
= 'WARNING: Debe actualizarse a LIQUIDADO'      → ⚠️  Auto-fix pending
```

### Query #8: Estadisticas
**Verificar que:**
```
Cuotas PAGADAS + Cuotas PENDIENTES = Total Cuotas

Suma Pagos Aplicados a Cuotas ≈ Suma Total de Pagos
(pueden diferir ligeramente si hay pagos parciales)

Prestamos 100% Pagados ≈ Prestamos LIQUIDADO
(deberían ser muy similares después de auto-actualización)
```

## Si hay problemas

### Problema: Pagos no conciliados (Query #2)
**Causa:** Pagos registrados pero no aplicados a cuotas
**Solución:**
```sql
-- Ver pagos sin aplicación
SELECT pago_id, COUNT(*) FROM cuota_pago GROUP BY pago_id;

-- Verificar tabla pago
SELECT * FROM pago WHERE id NOT IN (SELECT DISTINCT pago_id FROM cuota_pago);
```

### Problema: Cuotas con discrepancias (Query #4)
**Causa:** Estado de cuota no coincide con pagos aplicados
**Solución:**
```sql
-- Ver cuotas problemáticas
SELECT * FROM cuotas c
LEFT JOIN cuota_pago cp ON c.id = cp.cuota_id
WHERE (c.estado = 'PAGADO' AND cp.monto_cuota IS NULL)
   OR (c.estado = 'PENDIENTE' AND cp.monto_cuota IS NOT NULL);

-- Actualizar estado de cuota si está 100% pagada:
UPDATE cuotas SET estado = 'PAGADO'
WHERE id IN (
  SELECT c.id FROM cuotas c
  WHERE SUM(COALESCE(cp.monto_cuota, 0)) >= c.monto_cuota - 0.01
);
```

### Problema: LIQUIDADO sin 100% pago (Query #6)
**Causa:** Préstamo marcado LIQUIDADO pero pagos incompletos
**Solución:**
```sql
-- Ver préstamos problemáticos
SELECT p.id, p.estado, 
       COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) AS pagado
FROM prestamos p LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'LIQUIDADO'
GROUP BY p.id, p.estado
HAVING COALESCE(SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PAGADO'), 0) 
       < p.total_financiamiento - 0.01;

-- Revertir a APROBADO si es necesario:
UPDATE prestamos SET estado = 'APROBADO'
WHERE id IN (...) AND estado = 'LIQUIDADO';
```

## Próximo paso

Ejecuta `sql/verificacion_pagos_conciliados.sql` y comparte:

1. **Query #1 (Resumen):**
   - Total pagos: ?
   - Cuotas pagadas: ?
   - Prestamos liquidados: ?

2. **Query #2 (No conciliados):**
   - ¿Hay filas? Sí/No

3. **Query #4 (Discrepancias):**
   - ¿Hay filas? Sí/No

4. **Query #6 (Distribucion):**
   - Estados de conciliacion: ?

5. **Query #8 (Totales):**
   - Cuotas PAGADAS vs PENDIENTES
   - Prestamos LIQUIDADO
   - Prestamos 100% Pagados
