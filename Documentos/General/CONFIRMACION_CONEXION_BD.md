# ✅ CONFIRMACIÓN: CONEXIÓN DE FORMULARIOS A BASES DE DATOS

## ============================================================================
## TABLAS DE BASE DE DATOS
## ============================================================================

### ✅ TABLA 1: `prestamos`
**Formulario**: Nuevo Préstamo (`CrearPrestamoForm.tsx`)
**Endpoint**: `POST /api/v1/prestamos`
**Campos principales**:
- `id`, `cliente_id`, `cedula`, `nombres`
- `total_financiamiento`, `modalidad_pago`, `numero_cuotas`, `cuota_periodo`
- `tasa_interes`, `producto`, `producto_financiero`
- `estado`, `fecha_solicitud`, `fecha_aprobacion`

### ✅ TABLA 2: `prestamos_evaluacion`  
**Formulario**: Evaluación de Riesgo (`EvaluacionRiesgoForm.tsx`)
**Endpoint**: `POST /api/v1/prestamos/{prestamo_id}/evaluar-riesgo`
**Campos principales**:
- `id`, `prestamo_id` (FK a prestamos.id)
- 7 Criterios de evaluación (100 puntos totales)
- `puntuacion_total`, `clasificacion_riesgo`, `decision_final`
- `tasa_interes_aplicada`, `plazo_maximo`, `enganche_minimo`

## ============================================================================
## CÓDIGO SQL PARA VERIFICAR EN DBEAVER
## ============================================================================

### Consulta 1: Ver todos los préstamos
```sql
SELECT * FROM prestamos ORDER BY id DESC LIMIT 10;
```

### Consulta 2: Ver todas las evaluaciones
```sql
SELECT * FROM prestamos_evaluacion ORDER BY id DESC LIMIT 10;
```

### Consulta 3: Relación entre préstamos y evaluaciones
```sql
SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.nombres,
    p.estado AS estado_prestamo,
    e.id AS evaluacion_id,
    e.puntuacion_total,
    e.clasificacion_riesgo,
    e.decision_final
FROM prestamos p
LEFT JOIN prestamos_evaluacion e ON p.id = e.prestamo_id
ORDER BY p.id DESC;
```

### Consulta 4: Contar registros
```sql
SELECT 
    'prestamos' AS tabla,
    COUNT(*) AS total
FROM prestamos
UNION ALL
SELECT 
    'prestamos_evaluacion' AS tabla,
    COUNT(*) AS total
FROM prestamos_evaluacion;
```

### Consulta 5: Ver estructura de columnas
```sql
-- Para prestamos
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'prestamos'
ORDER BY ordinal_position;

-- Para prestamos_evaluacion
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'prestamos_evaluacion'
ORDER BY ordinal_position;
```

## ============================================================================
## VERIFICACIÓN DE CONEXIÓN
## ============================================================================

### ✅ Confirmado: Formularios conectados a tablas separadas

1. **Formulario "Nuevo Préstamo"** 
   → Guarda en tabla `prestamos`
   → Archivo: `CrearPrestamoForm.tsx`
   → Endpoint: `/api/v1/prestamos`

2. **Formulario "Evaluación de Riesgo"**
   → Guarda en tabla `prestamos_evaluacion`  
   → Archivo: `EvaluacionRiesgoForm.tsx`
   → Endpoint: `/api/v1/prestamos/{id}/evaluar-riesgo`

### ✅ Relación entre tablas
```sql
prestamos_evaluacion.prestamo_id = prestamos.id
```

## ============================================================================
## ARCHIVOS IMPORTANTES CREADOS
## ============================================================================

1. 📄 **`consultas_verificacion_dbeaver.sql`** - Consultas completas para DBeaver
2. 📄 **`RESUMEN_CAMBIOS_EVALUACION_RIESGO.md`** - Documentación completa de cambios

