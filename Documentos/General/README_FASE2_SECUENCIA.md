# 📋 Guía de Ejecución: FASE 2 - Secuencia Completa en DBeaver

> **Instrucciones paso a paso para ejecutar en DBeaver**
> Última actualización: 2026-01-11

---

## 🎯 Objetivo

Activar 182 clientes inactivos que tienen préstamos/pagos activos, resolviendo así:
- 182 cédulas en préstamos sin cliente activo
- 175 cédulas en pagos sin cliente activo (incluidas en las 182)

---

## 📋 Secuencia de Ejecución en DBeaver

### **PASO 0: Diagnóstico** 🔍
**Consulta:** Verificar estado actual del problema

**Qué hacer:**
1. Abrir DBeaver
2. Conectarse a la base de datos
3. Abrir el archivo `FASE2_SECUENCIA_COMPLETA.sql`
4. Seleccionar y ejecutar la consulta del **PASO 0**
5. Revisar los números para entender el estado actual
6. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**
```
paso              |cedulas_en_prestamos_sin_cliente_activo|clientes_inactivos_con_esas_cedulas|clientes_activos_con_esas_cedulas|
-------------------+----------------------------------------+-----------------------------------+----------------------------------+
PASO 0: Diagnóstico|182                                     |182                                |0                                 |
```

**Nota:** Si `clientes_inactivos_con_esas_cedulas` es 0, significa que los clientes ya fueron activados previamente.

---

### **PASO 1: Verificación Previa**
**Consulta:** Ver cuántos clientes se activarían

**Qué hacer:**
1. Ejecutar la consulta del **PASO 1**
2. Revisar el resultado (debe mostrar 182 clientes si no se han activado aún)
3. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**
```
paso                      |clientes_a_activar|registros_clientes_inactivos|instruccion                         |
--------------------------+-----------------+----------------------------+------------------------------------+
PASO 1: Clientes a activar|182              |182                         |Revisar resultado antes de continuar|
```

**Nota:** Si `clientes_a_activar` es 0, verifica el PASO 0 para entender por qué.

---

### **PASO 2A: Diagnóstico Detallado** 🔍
**Consulta:** Ver qué cédulas tienen el problema y su estado

**Qué hacer:**
1. Ejecutar la consulta del **PASO 2A**
2. Revisar las primeras 10 cédulas con problema
3. Verificar si tienen clientes inactivos asociados
4. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**
```
paso                      |cedula|cantidad_prestamos|tiene_cliente_activo|tiene_cliente_inactivo|estados_clientes_inactivos|
--------------------------+------+-----------------+--------------------+----------------------+-------------------------+
PASO 2A: Cédulas con...  |12345 |5                |0                   |1                     |FINALIZADO               |
```

**Nota:** Si `tiene_cliente_inactivo` es 0 para todas las cédulas, significa que los clientes ya fueron activados.

---

### **PASO 2: Ver Detalles**
**Consulta:** Ver detalles de los primeros 20 clientes que se activarán

**Qué hacer:**
1. Ejecutar la consulta del **PASO 2**
2. Revisar los detalles (cliente_id, cédula, nombres, estado actual, cantidad de préstamos y pagos)
3. Si la tabla está vacía, revisar el PASO 2A para entender por qué
4. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**
- Tabla con hasta 20 filas mostrando detalles de clientes
- Todos deben tener `activo = FALSE` y `estado = 'FINALIZADO'` o `'INACTIVO'`
- **Si la tabla está vacía:** Los clientes ya fueron activados previamente

---

### **PASO 3: Verificar Estado Actual**
**Consulta:** Ver el estado actual del problema

**Qué hacer:**
1. Ejecutar la consulta del **PASO 3**
2. Revisar los números (182 cédulas en préstamos, 175 en pagos, etc.)
3. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**

**Si el problema NO está resuelto:**
```
paso              |cedulas_en_prestamos_sin_cliente_activo|cedulas_en_pagos_sin_cliente_activo|total_pagos_afectados|monto_total_afectado|estado                                                      |
------------------+----------------------------------------+----------------------------------+---------------------+--------------------+------------------------------------------------------------+
PASO 3: Estado...|182                                     |175                                |2308                 |237888.00           |⚠️ PROBLEMA PENDIENTE: Existen 182 cédulas sin cliente...|
```

**Si el problema YA está resuelto:**
```
paso              |cedulas_en_prestamos_sin_cliente_activo|cedulas_en_pagos_sin_cliente_activo|total_pagos_afectados|monto_total_afectado|estado                                                      |
------------------+----------------------------------------+----------------------------------+---------------------+--------------------+------------------------------------------------------------+
PASO 3: Estado...|0                                       |0                                  |0                    |                    |✅ PROBLEMA RESUELTO: Todos los clientes están activos   |
```

**⚠️ IMPORTANTE:** Si el PASO 3 muestra 0 en todos los campos, **NO ejecutes el PASO 4**. Los clientes ya fueron activados previamente.

---

### **VERIFICACIÓN PRE-ACTIVACIÓN** 🔍
**Consulta:** Verificar si es necesario ejecutar el PASO 4

**Qué hacer:**
1. Ejecutar la consulta de **VERIFICACIÓN PRE-ACTIVACIÓN** (después del PASO 3)
2. Revisar la recomendación
3. Si dice "NO ES NECESARIO", saltar al PASO 6
4. Si dice "EJECUTAR PASO 4", continuar con el PASO 4

**Resultado esperado si el problema ya fue resuelto:**
```
paso                      |recomendacion                                                      |
--------------------------+-------------------------------------------------------------------+
VERIFICACIÓN PRE-ACTIV...|✅ NO ES NECESARIO EJECUTAR PASO 4: El problema ya fue resuelto    |
```

---

### **PASO 4: EJECUTAR ACTIVACIÓN** ⚠️ **ACCIÓN CRÍTICA**
**⚠️ SOLO EJECUTAR SI EL PASO 3 MUESTRA NÚMEROS > 0**
**Consulta:** Activar los 182 clientes inactivos

**Qué hacer:**
1. **IMPORTANTE:** Solo ejecutar si el PASO 3 muestra números > 0
2. **IMPORTANTE:** Revisar que los pasos anteriores muestren los resultados esperados
3. Ejecutar la consulta del **PASO 4** (incluye `BEGIN;` y `COMMIT;`)
4. Revisar el resultado del `RETURNING` (debe mostrar 182 filas con `activo = TRUE` y `estado = 'ACTIVO'`)
5. Confirmar que el `COMMIT` se ejecutó correctamente
6. Escribir "FIN" cuando termines de revisar

**⚠️ NO EJECUTAR si el PASO 3 muestra 0 en todos los campos - los clientes ya fueron activados**

**Resultado esperado:**
- 182 filas en el resultado del `RETURNING`
- Todas con `activo = TRUE` y `estado = 'ACTIVO'`
- Mensaje de confirmación del `COMMIT`

---

### **PASO 5: Verificación Post-Activación**
**Consulta:** Confirmar que se activaron los clientes

**Qué hacer:**
1. Ejecutar la consulta del **PASO 5**
2. Revisar que muestre "OK: Se activaron 182 clientes"
3. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**

**Si se activaron clientes:**
```
paso                          |clientes_activados|resultado                    |
------------------------------+------------------+-----------------------------+
PASO 5: Verificación post...  |182               |✅ OK: Se activaron 182 clientes|
```

**Si el problema ya estaba resuelto:**
```
paso                          |clientes_activados|resultado                                                                    |
------------------------------+------------------+---------------------------------------------------------------------------+
PASO 5: Verificación post...  |0                 |✅ OK: No se activaron clientes porque el problema ya estaba resuelto|
```

---

### **PASO 6: Verificación Final - Préstamos**
**Consulta:** Verificar que no queden cédulas en préstamos sin cliente activo

**Qué hacer:**
1. Ejecutar la consulta del **PASO 6**
2. Revisar que muestre "OK: Todas las cédulas tienen cliente activo"
3. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**
```
paso                    |cedulas_en_prestamos_sin_cliente_activo|resultado                                    |
------------------------+----------------------------------------+---------------------------------------------+
PASO 6: Verificación... |0                                       |OK: Todas las cédulas tienen cliente activo|
```

---

### **PASO 7: Verificación Final - Pagos**
**Consulta:** Verificar que no queden cédulas en pagos sin cliente activo

**Qué hacer:**
1. Ejecutar la consulta del **PASO 7**
2. Revisar que muestre "OK: Todas las cédulas en pagos tienen cliente activo"
3. Escribir "FIN" cuando termines de revisar

**Resultado esperado:**
```
paso                    |cedulas_en_pagos_sin_cliente_activo|total_pagos_afectados|resultado                                    |
------------------------+-----------------------------------+---------------------+---------------------------------------------+
PASO 7: Verificación... |0                                  |0                    |OK: Todas las cédulas en pagos tienen...|
```

---

### **PASO 8: Resumen Final**
**Consulta:** Ver resumen completo de todas las verificaciones

**Qué hacer:**
1. Ejecutar la consulta del **PASO 8**
2. Revisar que todas las verificaciones muestren "OK"
3. Guardar los resultados para referencia

**Resultado esperado:**
```
tipo         |verificacion                    |valor|estado|
-------------+--------------------------------+-----+------+
RESUMEN FINAL|Cédulas en préstamos sin cliente|0    |OK    |
RESUMEN FINAL|Cédulas en pagos sin cliente     |0    |OK    |
RESUMEN FINAL|Total préstamos                 |4419 |INFO  |
RESUMEN FINAL|Préstamos con cliente activo    |4419 |INFO  |
RESUMEN FINAL|Total pagos activos             |19087|INFO  |
RESUMEN FINAL|Pagos activos con cliente activo|19087|INFO  |
```

**Nota:** Los números de "Préstamos con cliente activo" y "Pagos activos con cliente activo" deben ser iguales o menores que los totales. Si son mayores, podría indicar duplicados en la tabla de clientes (múltiples registros con la misma cédula activa).

---

## ⚠️ Advertencias Importantes

1. **Backup:** Hacer backup de la base de datos antes de ejecutar el PASO 4
2. **Revisar resultados:** Siempre revisar los resultados de cada paso antes de continuar
3. **Escribir "FIN":** Escribir "FIN" después de cada paso para confirmar que revisaste los resultados
4. **PASO 4 es crítico:** El PASO 4 modifica datos, asegúrate de revisar bien los pasos anteriores

---

## 🔄 Si algo sale mal

### **Rollback (si es necesario):**
```sql
BEGIN;

WITH cedulas_problema AS (
    SELECT DISTINCT p.cedula
    FROM prestamos p
    LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
    WHERE c.id IS NULL
)
UPDATE clientes 
SET activo = FALSE, 
    fecha_actualizacion = CURRENT_TIMESTAMP,
    estado = 'FINALIZADO'
WHERE cedula IN (SELECT cedula FROM cedulas_problema)
  AND activo = TRUE
  AND estado = 'ACTIVO';

COMMIT;
```

---

## 📝 Checklist de Ejecución

- [ ] PASO 0 ejecutado y revisado (diagnóstico inicial)
- [ ] PASO 1 ejecutado y revisado (verificar que muestre 182 clientes)
- [ ] PASO 2A ejecutado y revisado (diagnóstico detallado de cédulas)
- [ ] PASO 2 ejecutado y revisado
- [ ] PASO 3 ejecutado y revisado
- [ ] Backup de base de datos realizado
- [ ] PASO 4 ejecutado (activación de 182 clientes)
- [ ] PASO 5 ejecutado y verificado (182 clientes activados)
- [ ] PASO 6 ejecutado y verificado (0 cédulas sin cliente activo en préstamos)
- [ ] PASO 7 ejecutado y verificado (0 cédulas sin cliente activo en pagos)
- [ ] PASO 8 ejecutado (resumen final con todos los OK)

---

**Última revisión:** 2026-01-11
