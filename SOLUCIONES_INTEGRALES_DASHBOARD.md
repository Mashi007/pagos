# 🔧 SOLUCIONES INTEGRALES PARA PROBLEMAS DEL DASHBOARD

**Fecha:** 2025-01-06  
**Análisis:** Investigación exhaustiva con SQL en DBeaver  
**Estado:** CRÍTICO - Problemas de integridad y lógica identificados

---

## 🚨 PROBLEMA CRÍTICO IDENTIFICADO

### **PAGOS NO VINCULADOS A CUOTAS**

**Hallazgo principal:**
- **13,679 pagos** en la base de datos
- **0 pagos** coinciden con cuotas usando `prestamo_id + numero_cuota`
- **100% de los pagos** no tienen información de cuota

**Impacto:**
- Dashboard muestra morosidad pero NO muestra pagos
- `monto_pagado = 0` en todos los meses
- Métricas de pagos completamente desconectadas

**Causa raíz:**
Los pagos se registran pero NO se vinculan correctamente a las cuotas. Los pagos probablemente se registran por `cedula` y `fecha_pago`, no por `prestamo_id + numero_cuota`.

---

## ✅ SOLUCIONES IMPLEMENTADAS

### 1. **Helper de Pagos-Cuotas** (`backend/app/utils/pagos_cuotas_helper.py`)

**Funcionalidad:**
- Busca pagos usando múltiples estrategias:
  1. `prestamo_id + numero_cuota` (ideal)
  2. `cedula + fecha_vencimiento` (aproximación)
  3. `cedula + rango de fechas` (±30 días)
  4. `cedula + monto similar` (última opción)

**Funciones:**
- `obtener_pagos_cuota()` - Obtiene pagos de una cuota
- `calcular_total_pagado_cuota()` - Calcula total pagado de una cuota
- `calcular_monto_pagado_mes()` - Calcula monto pagado en un mes
- `reconciliar_pago_cuota()` - Reconcilia un pago con una cuota

---

### 2. **Script de Reconciliación** (`backend/scripts/reconciliar_pagos_cuotas.py`)

**Funcionalidad:**
- Reconcilia pagos con cuotas automáticamente
- Actualiza `total_pagado` en cuotas
- Corrige estados de cuotas
- Modo dry-run para verificar antes de aplicar

**Uso:**
```bash
# Ver qué haría (sin cambios)
python backend/scripts/reconciliar_pagos_cuotas.py

# Aplicar cambios
python backend/scripts/reconciliar_pagos_cuotas.py --apply
```

---

### 3. **Correcciones en Dashboard** (`backend/app/api/v1/endpoints/dashboard.py`)

**Cambios:**
- ✅ Función `normalize_to_date()` agregada
- ✅ Validación de campos corregida (`mes` no es numérico)
- ✅ Comparación de fechas normalizada
- ✅ Import de `pagos_cuotas_helper` agregado

---

## 📋 PLAN DE IMPLEMENTACIÓN

### FASE 1: RECONCILIACIÓN DE DATOS (Inmediato)

**Paso 1: Ejecutar script de reconciliación (DRY RUN)**
```bash
cd backend
python scripts/reconciliar_pagos_cuotas.py
```

**Paso 2: Revisar resultados**
- Verificar cuántos pagos se reconciliarían
- Verificar cuántas cuotas se corregirían

**Paso 3: Aplicar reconciliación**
```bash
python scripts/reconciliar_pagos_cuotas.py --apply
```

**Paso 4: Verificar en SQL**
```sql
-- Verificar pagos vinculados después de reconciliación
SELECT 
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
    SUM(total_pagado) as monto_total_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';
```

---

### FASE 2: MODIFICAR QUERIES DEL DASHBOARD

**Problema actual:**
El endpoint `/financiamiento-tendencia-mensual` usa `total_pagado` de cuotas, pero está en 0 porque los pagos no están vinculados.

**Solución:**
Modificar la query para usar el helper que busca pagos de múltiples formas.

**Código a modificar:**
```python
# En lugar de usar solo total_pagado de cuotas:
func.sum(Cuota.total_pagado).label("total_pagado")

# Usar helper que busca pagos de múltiples formas:
# (Esto requiere modificar la lógica del endpoint)
```

**Alternativa (más rápida):**
Crear una vista materializada que vincule pagos y cuotas usando múltiples estrategias.

---

### FASE 3: CREAR VISTA MATERIALIZADA (Optimización)

**SQL para crear vista:**
```sql
CREATE MATERIALIZED VIEW pagos_cuotas_reconciliados AS
SELECT 
    c.id as cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.estado as cuota_estado,
    -- Estrategia 1: prestamo_id + numero_cuota
    COALESCE(
        (SELECT SUM(pa.monto_pagado)
         FROM pagos pa
         WHERE pa.prestamo_id = c.prestamo_id
           AND pa.numero_cuota = c.numero_cuota
           AND pa.activo = true),
        0
    ) as total_pagado_estrategia1,
    -- Estrategia 2: cedula + fecha_vencimiento
    COALESCE(
        (SELECT SUM(pa.monto_pagado)
         FROM pagos pa
         INNER JOIN prestamos p ON p.cedula = pa.cedula
         WHERE p.id = c.prestamo_id
           AND DATE(pa.fecha_pago) = c.fecha_vencimiento
           AND pa.activo = true
           AND pa.prestamo_id IS NULL),
        0
    ) as total_pagado_estrategia2,
    -- Total combinado
    COALESCE(
        (SELECT SUM(pa.monto_pagado)
         FROM pagos pa
         INNER JOIN prestamos p ON p.id = c.prestamo_id
         WHERE (
             (pa.prestamo_id = c.prestamo_id AND pa.numero_cuota = c.numero_cuota)
             OR
             (pa.cedula = p.cedula AND DATE(pa.fecha_pago) = c.fecha_vencimiento)
             OR
             (pa.cedula = p.cedula 
              AND DATE(pa.fecha_pago) BETWEEN c.fecha_vencimiento - INTERVAL '30 days' 
              AND c.fecha_vencimiento + INTERVAL '30 days')
         )
           AND pa.activo = true),
        0
    ) as total_pagado_combinado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

CREATE INDEX idx_pagos_cuotas_reconciliados_prestamo 
ON pagos_cuotas_reconciliados(prestamo_id, numero_cuota);

CREATE INDEX idx_pagos_cuotas_reconciliados_fecha 
ON pagos_cuotas_reconciliados(fecha_vencimiento);

-- Actualizar periódicamente (cada hora o después de registrar pagos)
REFRESH MATERIALIZED VIEW CONCURRENTLY pagos_cuotas_reconciliados;
```

---

## 🔍 VERIFICACIÓN POST-IMPLEMENTACIÓN

### Queries SQL de Verificación:

```sql
-- 1. Verificar pagos vinculados después de reconciliación
SELECT 
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
    SUM(total_pagado) as monto_total_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- 2. Verificar morosidad mensual con pagos
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

-- 3. Comparar con vista materializada (si se crea)
SELECT 
    TO_CHAR(DATE_TRUNC('month', fecha_vencimiento), 'YYYY-MM') as mes,
    SUM(monto_cuota) as monto_programado,
    SUM(total_pagado_combinado) as monto_pagado,
    SUM(monto_cuota) - SUM(total_pagado_combinado) as morosidad
FROM pagos_cuotas_reconciliados
WHERE fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', fecha_vencimiento)
ORDER BY mes DESC;
```

---

## 📊 RESULTADOS ESPERADOS

### Antes de las soluciones:
- ❌ 0 pagos vinculados a cuotas
- ❌ `monto_pagado = 0` en todos los meses
- ❌ Morosidad = monto_programado (sin pagos)

### Después de las soluciones:
- ✅ Pagos vinculados usando múltiples estrategias
- ✅ `monto_pagado` muestra valores reales
- ✅ Morosidad = monto_programado - monto_pagado (correcto)

---

## 🎯 PRIORIDADES

### 🔴 CRÍTICO (Hacer Ahora):
1. Ejecutar script de reconciliación (dry-run primero)
2. Aplicar reconciliación si los resultados son correctos
3. Verificar que `total_pagado` se actualiza en cuotas

### 🟡 IMPORTANTE (Esta Semana):
4. Modificar queries del dashboard para usar helper
5. Crear vista materializada para optimización
6. Actualizar endpoint `/financiamiento-tendencia-mensual`

### 🟢 MEJORAS (Próxima Semana):
7. Modificar proceso de registro de pagos para vincular automáticamente
8. Agregar validaciones para prevenir el problema
9. Crear alertas cuando hay inconsistencias

---

## 📝 ARCHIVOS CREADOS/MODIFICADOS

1. ✅ `backend/app/utils/pagos_cuotas_helper.py` (NUEVO)
   - Helper para vincular pagos con cuotas

2. ✅ `backend/scripts/reconciliar_pagos_cuotas.py` (NUEVO)
   - Script de reconciliación automática

3. ✅ `backend/app/api/v1/endpoints/dashboard.py` (MODIFICADO)
   - Función `normalize_to_date()` agregada
   - Validación corregida
   - Import de helper agregado

4. ✅ `backend/app/core/debug_helpers.py` (MODIFICADO)
   - `validate_graph_data()` con `non_numeric_fields`

5. ✅ `ANALISIS_PROBLEMAS_DASHBOARD.md` (NUEVO)
   - Análisis exhaustivo de problemas

6. ✅ `SOLUCIONES_INTEGRALES_DASHBOARD.md` (NUEVO)
   - Este documento

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [ ] Ejecutar script de reconciliación (dry-run)
- [ ] Revisar resultados de reconciliación
- [ ] Aplicar reconciliación (`--apply`)
- [ ] Verificar en SQL que `total_pagado` se actualiza
- [ ] Modificar endpoint `/financiamiento-tendencia-mensual` para usar helper
- [ ] Probar endpoint y verificar que muestra pagos
- [ ] Crear vista materializada (opcional, para optimización)
- [ ] Validar que el dashboard muestra datos correctos

---

**Última actualización:** 2025-01-06

