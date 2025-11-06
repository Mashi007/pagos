# 🔍 ANÁLISIS EXHAUSTIVO DE PROBLEMAS DEL DASHBOARD

**Fecha:** 2025-01-06  
**Fuente:** Investigación SQL en DBeaver  
**Estado:** CRÍTICO - Múltiples problemas de integridad y lógica

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. **PROBLEMA CRÍTICO #1: PAGOS NO VINCULADOS A CUOTAS**

**Hallazgo:**
- **Total pagos:** 13,679
- **Pagos con información de cuota (prestamo_id + numero_cuota):** 0
- **Pagos sin información de cuota:** 13,679 (100%)

**Impacto:**
- El dashboard muestra morosidad pero NO muestra pagos
- Las queries que buscan pagos por `prestamo_id + numero_cuota` retornan 0 resultados
- La morosidad mensual muestra `monto_pagado = 0` en todos los meses
- Las métricas de pagos están completamente desconectadas de las cuotas

**Causa raíz:**
Los pagos se registran pero NO se vinculan correctamente a las cuotas usando `prestamo_id` y `numero_cuota`.

---

### 2. **PROBLEMA CRÍTICO #2: INTEGRIDAD REFERENCIAL ROTA**

**Hallazgos:**
- **327 cuotas sin préstamo asociado** (prestamo_id no existe en tabla prestamos)
- **13,679 pagos sin préstamo asociado** (prestamo_id es NULL o no existe)

**Impacto:**
- Datos huérfanos en la base de datos
- Queries con JOINs fallan o retornan resultados incorrectos
- Imposible calcular métricas precisas

---

### 3. **PROBLEMA CRÍTICO #3: CUOTAS MARCADAS COMO PAGADO SIN PAGOS**

**Hallazgo:**
- **389 cuotas marcadas como PAGADO** pero sin pagos registrados que coincidan
- Monto total: $48,032.60

**Impacto:**
- Inconsistencia en el estado de las cuotas
- El dashboard puede mostrar información incorrecta
- Imposible rastrear qué pagos corresponden a qué cuotas

---

### 4. **PROBLEMA #4: INCOMPATIBILIDAD DE TIPOS DE DATOS (datetime vs date)**

**Hallazgo:**
- `prestamos.fecha_aprobacion`: `timestamp without time zone` (3,681 registros)
- `cuotas.fecha_vencimiento`: `date` (45,059 registros)
- `pagos.fecha_pago`: `timestamp without time zone` (13,679 registros)

**Nota:** Aunque todas las fechas TIMESTAMP tienen hora 00:00:00, el tipo sigue siendo TIMESTAMP, causando problemas al comparar con DATE.

**Impacto:**
- Error: "can't compare datetime.datetime to datetime.date"
- Necesidad de normalizar tipos antes de comparar

**Solución aplicada:** ✅ Función `normalize_to_date()` implementada

---

### 5. **PROBLEMA #5: FECHAS FUTURAS EN PRÉSTAMOS**

**Hallazgo:**
- Última aprobación: `2027-07-07` (fecha futura)
- Nuevos financiamientos muestran meses hasta 2027-07
- Cuotas programadas hasta 2029-11

**Análisis:**
- Las fechas futuras en cuotas son normales (préstamos a largo plazo)
- Pero la última aprobación en 2027 es sospechosa (posible error de datos)

---

## 📊 ANÁLISIS DE DATOS

### Métricas del Dashboard (Verificadas en SQL):

| Métrica | Valor SQL | Estado |
|---------|-----------|--------|
| Cartera Total | $5,157,582.00 | ✅ Correcto |
| Cartera Vencida | $637,599.00 | ✅ Correcto |
| Cartera al Día | $4,519,983.00 | ✅ Correcto |
| Porcentaje Mora | 12.36% | ✅ Correcto |
| Préstamos Mes Actual | 133 ($182,292.00) | ✅ Correcto |
| Clientes Activos | 3,674 | ✅ Correcto |
| Morosidad Total | $637,599.00 | ✅ Correcto |

**Conclusión:** Las métricas básicas del dashboard son correctas según SQL.

---

### Problema Principal: Desconexión Pagos-Cuotas

**Evidencia:**
1. Query "PAGOS VS CUOTAS": 0 pagos coinciden con cuotas
2. Query "Pagos por mes": Tabla vacía (0 resultados)
3. Morosidad mensual: `monto_pagado = 0` en todos los meses
4. 13,679 pagos sin `prestamo_id` o `numero_cuota`

**Causa probable:**
- Los pagos se registran pero no se asocian correctamente a las cuotas
- Puede ser un problema en el proceso de registro de pagos
- O los pagos se registran de forma diferente (por cédula, no por préstamo)

---

## 🔧 SOLUCIONES INTEGRALES

### SOLUCIÓN 1: VINCULAR PAGOS A CUOTAS (CRÍTICO)

**Problema:** Los pagos no están vinculados a cuotas usando `prestamo_id + numero_cuota`.

**Solución:**

#### Opción A: Script de Reconciliación Automática

```python
def reconciliar_pagos_con_cuotas(db: Session):
    """
    Reconcilia pagos con cuotas basándose en:
    1. prestamo_id + numero_cuota (si están disponibles)
    2. cedula + fecha_pago (aproximación)
    3. monto_pagado (coincidencia)
    """
    # 1. Pagos con prestamo_id y numero_cuota pero sin verificar
    pagos_con_info = db.query(Pago).filter(
        Pago.activo == True,
        Pago.prestamo_id.isnot(None),
        Pago.numero_cuota.isnot(None)
    ).all()
    
    reconciliados = 0
    for pago in pagos_con_info:
        # Verificar que la cuota existe
        cuota = db.query(Cuota).filter(
            Cuota.prestamo_id == pago.prestamo_id,
            Cuota.numero_cuota == pago.numero_cuota
        ).first()
        
        if cuota:
            # Actualizar total_pagado de la cuota
            if cuota.total_pagado is None:
                cuota.total_pagado = Decimal("0")
            cuota.total_pagado += pago.monto_pagado
            
            # Actualizar estado si está completamente pagada
            if cuota.total_pagado >= cuota.monto_cuota:
                cuota.estado = "PAGADO"
                cuota.fecha_pago = pago.fecha_pago.date()
            
            reconciliados += 1
    
    # 2. Pagos sin prestamo_id - intentar reconciliar por cédula y fecha
    pagos_sin_prestamo = db.query(Pago).filter(
        Pago.activo == True,
        or_(Pago.prestamo_id.is_(None), Pago.numero_cuota.is_(None))
    ).all()
    
    for pago in pagos_sin_prestamo:
        # Buscar préstamos por cédula
        prestamos = db.query(Prestamo).filter(
            Prestamo.cedula == pago.cedula,
            Prestamo.estado == "APROBADO"
        ).all()
        
        for prestamo in prestamos:
            # Buscar cuota que coincida con fecha de pago
            cuota = db.query(Cuota).filter(
                Cuota.prestamo_id == prestamo.id,
                Cuota.fecha_vencimiento <= pago.fecha_pago.date(),
                Cuota.estado != "PAGADO"
            ).order_by(Cuota.fecha_vencimiento).first()
            
            if cuota:
                # Vincular pago a cuota
                pago.prestamo_id = prestamo.id
                pago.numero_cuota = cuota.numero_cuota
                
                # Actualizar cuota
                if cuota.total_pagado is None:
                    cuota.total_pagado = Decimal("0")
                cuota.total_pagado += pago.monto_pagado
                
                if cuota.total_pagado >= cuota.monto_cuota:
                    cuota.estado = "PAGADO"
                    cuota.fecha_pago = pago.fecha_pago.date()
                
                reconciliados += 1
                break
    
    db.commit()
    return reconciliados
```

#### Opción B: Modificar Queries para Usar Cédula

Si los pagos se registran por cédula y no por préstamo, modificar las queries:

```python
# En lugar de:
LEFT JOIN pagos pa ON pa.prestamo_id = c.prestamo_id 
    AND pa.numero_cuota = c.numero_cuota

# Usar:
LEFT JOIN pagos pa ON pa.cedula = p.cedula
    AND pa.fecha_pago::date BETWEEN c.fecha_vencimiento - INTERVAL '30 days' 
    AND c.fecha_vencimiento + INTERVAL '30 days'
```

---

### SOLUCIÓN 2: CORREGIR INTEGRIDAD REFERENCIAL

**Problema:** 327 cuotas y 13,679 pagos sin préstamo válido.

**Solución:**

```sql
-- 1. Identificar cuotas huérfanas
SELECT c.id, c.prestamo_id, c.numero_cuota
FROM cuotas c
LEFT JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.id IS NULL;

-- 2. Identificar pagos huérfanos
SELECT pa.id, pa.prestamo_id, pa.cedula, pa.fecha_pago
FROM pagos pa
LEFT JOIN prestamos p ON pa.prestamo_id = p.id
WHERE pa.prestamo_id IS NOT NULL AND p.id IS NULL;

-- 3. Script de corrección (ejecutar con precaución)
-- Opción A: Eliminar registros huérfanos (si son errores)
-- Opción B: Intentar vincular por cédula y fecha
-- Opción C: Marcar como "PENDIENTE_RECONCILIACION"
```

---

### SOLUCIÓN 3: CORREGIR CUOTAS PAGADAS SIN PAGOS

**Problema:** 389 cuotas marcadas como PAGADO sin pagos registrados.

**Solución:**

```python
def corregir_cuotas_pagadas_sin_pagos(db: Session):
    """Corrige cuotas marcadas como PAGADO pero sin pagos"""
    cuotas_pagadas = db.query(Cuota).join(
        Prestamo, Cuota.prestamo_id == Prestamo.id
    ).filter(
        Cuota.estado == "PAGADO",
        Prestamo.estado == "APROBADO"
    ).all()
    
    corregidas = 0
    for cuota in cuotas_pagadas:
        # Buscar pagos por prestamo_id + numero_cuota
        pagos = db.query(Pago).filter(
            Pago.prestamo_id == cuota.prestamo_id,
            Pago.numero_cuota == cuota.numero_cuota,
            Pago.activo == True
        ).all()
        
        if not pagos:
            # Buscar pagos por cédula y fecha
            prestamo = db.query(Prestamo).filter(
                Prestamo.id == cuota.prestamo_id
            ).first()
            
            if prestamo:
                pagos_cedula = db.query(Pago).filter(
                    Pago.cedula == prestamo.cedula,
                    Pago.fecha_pago::date == cuota.fecha_vencimiento,
                    Pago.activo == True
                ).all()
                
                if not pagos_cedula:
                    # Si no hay pagos, cambiar estado a PENDIENTE
                    cuota.estado = "PENDIENTE"
                    cuota.fecha_pago = None
                    corregidas += 1
        else:
            # Hay pagos, verificar que sumen al menos monto_cuota
            total_pagado = sum(p.monto_pagado for p in pagos)
            if total_pagado < cuota.monto_cuota:
                cuota.estado = "PARCIAL"
                corregidas += 1
    
    db.commit()
    return corregidas
```

---

### SOLUCIÓN 4: MODIFICAR QUERIES DEL DASHBOARD

**Problema:** Las queries asumen que pagos están vinculados por `prestamo_id + numero_cuota`, pero no lo están.

**Solución:** Crear función helper que busque pagos de múltiples formas:

```python
def obtener_pagos_cuota(
    db: Session,
    prestamo_id: int,
    numero_cuota: int,
    cedula: str,
    fecha_vencimiento: date
) -> List[Pago]:
    """
    Obtiene pagos de una cuota usando múltiples estrategias:
    1. prestamo_id + numero_cuota (ideal)
    2. cedula + fecha_vencimiento (aproximación)
    3. cedula + rango de fechas (última opción)
    """
    # Estrategia 1: prestamo_id + numero_cuota
    pagos = db.query(Pago).filter(
        Pago.prestamo_id == prestamo_id,
        Pago.numero_cuota == numero_cuota,
        Pago.activo == True
    ).all()
    
    if pagos:
        return pagos
    
    # Estrategia 2: cedula + fecha_vencimiento (exacta)
    pagos = db.query(Pago).filter(
        Pago.cedula == cedula,
        func.date(Pago.fecha_pago) == fecha_vencimiento,
        Pago.activo == True
    ).all()
    
    if pagos:
        return pagos
    
    # Estrategia 3: cedula + rango de fechas (±30 días)
    fecha_inicio = fecha_vencimiento - timedelta(days=30)
    fecha_fin = fecha_vencimiento + timedelta(days=30)
    
    pagos = db.query(Pago).filter(
        Pago.cedula == cedula,
        func.date(Pago.fecha_pago) >= fecha_inicio,
        func.date(Pago.fecha_pago) <= fecha_fin,
        Pago.activo == True
    ).order_by(Pago.fecha_pago).all()
    
    return pagos
```

---

### SOLUCIÓN 5: CREAR VISTA MATERIALIZADA PARA PAGOS-CUOTAS

**Problema:** Las queries son lentas porque buscan pagos de múltiples formas.

**Solución:** Crear vista materializada que vincule pagos y cuotas:

```sql
CREATE MATERIALIZED VIEW pagos_cuotas_vista AS
SELECT 
    c.id as cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.cedula,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.estado as cuota_estado,
    COALESCE(SUM(pa.monto_pagado), 0) as total_pagado,
    COUNT(pa.id) as cantidad_pagos
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
LEFT JOIN pagos pa ON (
    -- Estrategia 1: prestamo_id + numero_cuota
    (pa.prestamo_id = c.prestamo_id AND pa.numero_cuota = c.numero_cuota)
    OR
    -- Estrategia 2: cedula + fecha_vencimiento
    (pa.cedula = p.cedula AND DATE(pa.fecha_pago) = c.fecha_vencimiento)
    OR
    -- Estrategia 3: cedula + rango de fechas
    (pa.cedula = p.cedula 
     AND DATE(pa.fecha_pago) BETWEEN c.fecha_vencimiento - INTERVAL '30 days' 
     AND c.fecha_vencimiento + INTERVAL '30 days')
)
WHERE pa.activo = true OR pa.id IS NULL
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.cedula, 
         c.fecha_vencimiento, c.monto_cuota, c.estado;

CREATE INDEX idx_pagos_cuotas_vista_prestamo ON pagos_cuotas_vista(prestamo_id, numero_cuota);
CREATE INDEX idx_pagos_cuotas_vista_fecha ON pagos_cuotas_vista(fecha_vencimiento);

-- Actualizar periódicamente
REFRESH MATERIALIZED VIEW CONCURRENTLY pagos_cuotas_vista;
```

---

## 📋 PLAN DE ACCIÓN PRIORIZADO

### FASE 1: CORRECCIONES CRÍTICAS (Inmediato)

1. **Crear script de reconciliación de pagos**
   - Vincular pagos a cuotas usando múltiples estrategias
   - Actualizar `total_pagado` en cuotas
   - Corregir estados de cuotas

2. **Modificar queries del dashboard**
   - Usar función `obtener_pagos_cuota()` que busca de múltiples formas
   - Actualizar endpoint `/financiamiento-tendencia-mensual`
   - Actualizar endpoint `/cobranzas-mensuales`

3. **Corregir cuotas pagadas sin pagos**
   - Ejecutar script de corrección
   - Verificar integridad

### FASE 2: OPTIMIZACIONES (Esta semana)

4. **Crear vista materializada**
   - Vincular pagos y cuotas de forma eficiente
   - Actualizar periódicamente

5. **Corregir integridad referencial**
   - Identificar y corregir registros huérfanos
   - Agregar constraints si es necesario

### FASE 3: PREVENCIÓN (Próxima semana)

6. **Modificar proceso de registro de pagos**
   - Asegurar que siempre se vincule a cuota
   - Validar prestamo_id y numero_cuota

7. **Agregar validaciones**
   - Verificar integridad antes de marcar cuota como PAGADO
   - Alertas cuando hay inconsistencias

---

## 🔍 QUERIES SQL DE VERIFICACIÓN POST-CORRECCIÓN

```sql
-- Verificar pagos vinculados después de reconciliación
SELECT 
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
    SUM(total_pagado) as monto_total_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- Verificar morosidad mensual con pagos
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

---

## ✅ RESULTADO ESPERADO

Después de implementar las soluciones:

1. ✅ Pagos vinculados correctamente a cuotas
2. ✅ Morosidad mensual muestra pagos reales
3. ✅ Cuotas con estados consistentes
4. ✅ Dashboard muestra datos precisos
5. ✅ Queries optimizadas y rápidas

---

**Última actualización:** 2025-01-06

