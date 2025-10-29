# 🔍 Verificación de Aprobación Automática en DBeaver

## Guía para Verificar el Proceso Completo

### 🎯 Objetivo
Verificar que el préstamo #9 (Juan García) se aprobó automáticamente después de la evaluación de riesgo.

---

## 📊 PASO 1: Verificar Estado del Préstamo

Ejecuta esta query en DBeaver:

```sql
SELECT 
    id,
    cedula,
    nombres,
    estado,                    -- ← DEBE SER: 'APROBADO'
    total_financiamiento,
    numero_cuotas,
    tasa_interes,
    fecha_aprobacion,          -- ← DEBE TENER FECHA
    fecha_base_calculo,        -- ← DEBE TENER FECHA (hoy + 1 mes)
    usuario_aprobador,         -- ← DEBE TENER EMAIL
    observaciones              -- ← DEBE CONTENER "Aprobación automática"
FROM 
    prestamos 
WHERE 
    id = 9;
```

### ✅ Resultado Esperado:
- `estado`: `'APROBADO'` (NO "Borrador")
- `fecha_aprobacion`: `2025-10-28` o fecha actual
- `fecha_base_calculo`: `2025-11-28` (aproximadamente 1 mes después)
- `usuario_aprobador`: Email del usuario que evaluó
- `observaciones`: Contiene "Aprobación automática"

---

## 📋 PASO 2: Verificar Evaluación de Riesgo

```sql
SELECT 
    id,
    prestamo_id,
    puntuacion_total,          -- ← DEBE SER: 96.50
    clasificacion_riesgo,      -- ← DEBE SER: 'A'
    decision_final,            -- ← DEBE SER: 'APROBADO_AUTOMATICO'
    tasa_interes_aplicada,
    plazo_maximo,
    requisitos_adicionales,
    created_at
FROM 
    prestamos_evaluacion 
WHERE 
    prestamo_id = 9
ORDER BY 
    created_at DESC
LIMIT 1;
```

### ✅ Resultado Esperado:
- `decision_final`: `'APROBADO_AUTOMATICO'`
- `clasificacion_riesgo`: `'A'`
- `puntuacion_total`: `96.50` (o similar)
- `plazo_maximo`: Mayor a 0

---

## 💰 PASO 3: Verificar Tabla de Amortización

```sql
SELECT 
    id,
    numero_cuota,
    fecha_vencimiento,
    monto_cuota,
    monto_capital,
    monto_interes,
    saldo_capital_inicial,
    saldo_capital_final,
    estado
FROM 
    cuotas 
WHERE 
    prestamo_id = 9
ORDER BY 
    numero_cuota;
```

### ✅ Resultado Esperado:
- **Total de filas**: 12 (debe haber 12 cuotas)
- `estado`: `'PENDIENTE'` para todas
- `fecha_vencimiento`: Fechas futuras (mes a mes)

---

## 📝 PASO 4: Verificar Auditoría

```sql
SELECT 
    id,
    usuario,
    accion,
    campo_modificado,
    estado_anterior,
    estado_nuevo,
    created_at
FROM 
    prestamo_auditoria 
WHERE 
    prestamo_id = 9
ORDER BY 
    created_at DESC
LIMIT 10;
```

### ✅ Resultado Esperado:
- Debe haber un registro con:
  - `estado_anterior`: `'BORRADOR'` o `'DRAFT'`
  - `estado_nuevo`: `'APROBADO'`
  - `accion`: `'CAMBIAR_ESTADO'` o `'APLICAR_CONDICIONES'`

---

## 🔧 PASO 5: Query de Diagnóstico Completo

Ejecuta esta query final para ver TODO en una vista:

```sql
SELECT 
    'Préstamo' as componente,
    p.id,
    p.estado,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    NULL as puntuacion,
    NULL as decision
FROM 
    prestamos p
WHERE 
    p.id = 9

UNION ALL

SELECT 
    'Evaluación' as componente,
    e.prestamo_id as id,
    NULL as estado,
    NULL as fecha_aprobacion,
    NULL as fecha_base_calculo,
    e.puntuacion_total as puntuacion,
    e.decision_final as decision
FROM 
    prestamos_evaluacion e
WHERE 
    e.prestamo_id = 9
    
UNION ALL

SELECT 
    'Cuotas' as componente,
    prestamo_id as id,
    NULL as estado,
    NULL as fecha_aprobacion,
    NULL as fecha_base_calculo,
    COUNT(*) as puntuacion,
    NULL as decision
FROM 
    cuotas
WHERE 
    prestamo_id = 9
GROUP BY 
    prestamo_id;
```

---

## ❌ Si Encuentras Errores

### Caso 1: Estado es "Borrador" o "DRAFT"
**Causa**: El endpoint no actualizó el estado automáticamente
**Solución**: Ver logs del backend o re-ejecutar la evaluación

### Caso 2: No existe fecha_aprobacion
**Causa**: La función `procesar_cambio_estado` no se ejecutó
**Solución**: Verificar que el código de actualización automática está activo

### Caso 3: No se generaron cuotas
**Causa**: Error en `generar_amortizacion()` o falta fecha_base_calculo
**Solución**: Verificar logs de error del backend

### Caso 4: Existe evaluación pero no hay cambios
**Causa**: El código de actualización automática no se ejecutó
**Solución**: Verificar que la decisión es "APROBADO_AUTOMATICO"

---

## 📞 Próximos Pasos

Una vez que ejecutes estas queries en DBeaver:

1. **Copia los resultados** de cada query
2. **Indica qué valores encontraste** (especialmente el estado)
3. **Compárteme los resultados** para ayudarte a diagnosticar

Los archivos generados:
- ✅ `verificar_aprobacion_automatica.sql` - Queries SQL completas
- ✅ `scripts/auditar_proceso_aprobacion.py` - Script Python para ejecutar

