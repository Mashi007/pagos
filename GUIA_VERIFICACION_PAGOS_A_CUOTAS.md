# Verificación: Todos los Pagos Cargados a Cuotas Respectivas

## Archivo SQL disponible

**`sql/verificacion_pagos_a_cuotas.sql`** contiene 10 consultas específicas para validar la carga de pagos a cuotas.

## Las 10 Consultas

| # | Qué verifica | Resultado esperado |
|---|---|---|
| **1** | **Resumen General** | Total pagos vs pagos aplicados |
| **2** | **Pagos no asignados** | 0 filas (todos los pagos asignados) ✅ |
| **3** | **Pagos parcialmente aplicados** | Ver si hay pagos incompletos |
| **4** | **Pagos completamente aplicados** | Suma aplicada = monto pagado ✅ |
| **5** | **Pagos sobre-aplicados** | 0 filas (ERROR si tiene filas) ⚠️ |
| **6** | **Distribución de aplicación** | Estado de cada pago |
| **7** | **Cuotas sin pago aplicado** | 0 filas (todas tienen pagos o PENDIENTE) |
| **8** | **Validación de cada pago** | Verifica integridad de cuota_pagos |
| **9** | **Resumen por préstamo** | Pagos vs aplicaciones por préstamo |
| **10** | **Estadísticas finales** | Totales consolidados |

## Resultados Esperados (ÉXITO) ✅

```
Query #1 (Resumen):
  total_pagos_registrados:      5000+ (ej.)
  suma_pagos_registrados:       7,500,000+ 
  pagos_con_cuotas_asignadas:   = total_pagos_registrados
  pagos_sin_asignar:            0
  diferencia_no_aplicada:       0.00 (o muy cercano a 0)

Query #2 (Pagos no asignados):
  Resultado: 0 filas (Lista vacía) ✅

Query #3 (Parcialmente aplicados):
  Resultado: 0 filas (idealmente)
  Si hay filas: ver % aplicado

Query #4 (Completamente aplicados):
  Resultado: Número similar a total_pagos

Query #5 (Sobre-aplicados):
  Resultado: 0 filas ✅

Query #6 (Distribución):
  "Completamente aplicado": mayoría
  "No aplicado": 0
  "SOBRE-aplicado": 0

Query #10 (Estadísticas):
  Total monto pagado = Total monto aplicado
  Diferencia no aplicada: 0 o muy cercana a 0
```

## Cómo interpretar los resultados

### Query #1: Resumen General
- `pagos_con_cuotas_asignadas` debe = `total_pagos_registrados`
- `diferencia_no_aplicada` debe ser 0 (o < 0.01)

**Si diferencia_no_aplicada > 0:**
- Hay pagos sin aplicar completamente a cuotas
- Necesita investigación o conciliación adicional

### Query #2: Pagos No Asignados
```
Si 0 filas  → ✅ OK: Todos los pagos están en cuota_pagos
Si N filas  → ❌ ERROR: N pagos no están asignados a cuotas
```

### Query #3: Pagos Parcialmente Aplicados
```
Si 0 filas        → ✅ OK: Todos los pagos están 100% o sin aplicar
Si hay filas      → ⚠️  ADVERTENCIA: Ver porcentaje_aplicado
  < 50%           → Aplicación muy incompleta
  > 90%           → Casi completo (revisar decimales)
```

### Query #4: Pagos Completamente Aplicados
```
Cantidad de filas debe ser: total_pagos - (sin asignar) - (sobre-aplicados)
```

### Query #5: Pagos Sobre-Aplicados
```
Si 0 filas  → ✅ OK: No hay errores de sobre-aplicación
Si N filas  → ❌ ERROR CRITICO: Se aplicó más de lo pagado
  Necesita corrección en cuota_pagos
```

### Query #6: Distribución de Aplicación
```
Estado esperado:
  "No aplicado":              0 pagos
  "Completamente aplicado":   N pagos (mayoría)
  "Parcialmente aplicado":    0 pagos (idealmente)
  "SOBRE-aplicado":           0 pagos (ERROR si hay)

porcentaje_total_aplicado debe ser ≈ 100%
```

### Query #9: Resumen por Préstamo
```
validacion = 'OK: Pagos = Aplicados'  → ✅ Correcto
= 'ERROR: Pagos > Aplicados'         → ❌ Hay pagos sin aplicar
= 'ERROR: Pagos < Aplicados'         → ❌ Hay sobre-aplicación
```

## Problemas comunes y soluciones

### Problema: Pagos sin asignar (Query #2)
**Síntomas:**
- Query #2 devuelve filas
- Pagos_sin_asignar > 0 en Query #1

**Causas posibles:**
- Pagos registrados pero no reconciliados
- No se ejecutó `conciliar_amortizacion_masiva.py`

**Solución:**
```sql
-- Ver pagos sin asignar
SELECT * FROM pagos pg
WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pg.id);

-- Necesita ejecución del script de conciliación masiva
```

### Problema: Pagos parcialmente aplicados (Query #3)
**Síntomas:**
- Query #3 tiene muchas filas
- Porcentaje aplicado < 100%

**Causas posibles:**
- Cuotas no suficientes para aplicar todo el pago
- Error en la lógica de aplicación FIFO

**Solución:**
```sql
-- Ver cuáles cuotas faltan por aplicar
SELECT pg.id, pg.monto_pagado, SUM(cp.monto_aplicado) FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id
WHERE pg.id IN (SELECT id FROM [resultados Query #3])
GROUP BY pg.id, pg.monto_pagado;
```

### Problema: Pagos sobre-aplicados (Query #5)
**Síntomas:** ❌ CRITICO
- Query #5 devuelve filas
- exceso_aplicado > 0

**Causa:**
- Error de datos en cuota_pagos
- Se aplicó más monto del que se pagó

**Solución:**
```sql
-- Corregir: reducir monto_aplicado en cuota_pagos
-- Requiere investigación caso a caso
SELECT * FROM cuota_pagos cp
WHERE cp.pago_id IN (SELECT id FROM [resultados Query #5]);
```

## Cómo ejecutar

### Opción 1: DBeaver
1. Abre: `sql/verificacion_pagos_a_cuotas.sql`
2. Ejecuta cada query con Ctrl+Enter
3. Revisa resultados

### Opción 2: Terminal
```bash
psql -U usuario -d pagos_db < sql/verificacion_pagos_a_cuotas.sql
```

### Opción 3: Query rápida (resumen ejecutivo)
```sql
-- Rápida confirmación
SELECT 
  COUNT(*) AS total_pagos,
  COUNT(DISTINCT pago_id) AS pagos_asignados,
  COUNT(*) - COUNT(DISTINCT pago_id) AS pagos_sin_asignar,
  ROUND((SUM(monto_pagado) - COALESCE(SUM(monto_aplicado), 0))::numeric, 2) AS diferencia
FROM pagos pg
LEFT JOIN cuota_pagos cp ON pg.id = cp.pago_id;
```

## Próximos pasos

1. Ejecuta `sql/verificacion_pagos_a_cuotas.sql`
2. Comparte los resultados de:
   - Query #1 (Resumen general)
   - Query #2 (Pagos sin asignar)
   - Query #5 (Sobre-aplicados)
   - Query #10 (Estadísticas finales)

3. Si alguna query muestra problemas, reporta qué query y qué resultado inesperado obtuvo

## Interpretación rápida

```
✅ EXITO:
  Query #2 = 0 filas
  Query #5 = 0 filas
  diferencia_no_aplicada ≈ 0
  porcentaje_total_aplicado ≈ 100%

⚠️ ADVERTENCIA:
  Query #3 tiene filas (pagos parciales)
  Revisar porcentaje_aplicado

❌ ERROR:
  Query #5 tiene filas (sobre-aplicación)
  diferencia_no_aplicada >> 0
  "ERROR: Pagos > Aplicados" en múltiples préstamos
```
