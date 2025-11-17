# Cambios Temporales: Usar `fecha_aprobacion` en lugar de `fecha_registro`

## Problema Identificado
La columna `fecha_registro` en la tabla `prestamos` no migró correctamente. Todos los 3,681 registros tienen la misma fecha: `2025-10-31`, lo que hace imposible filtrar o agrupar por fecha real.

## Solución Temporal
Se modificó el backend para usar `fecha_aprobacion` en lugar de `fecha_registro` en los endpoints críticos del dashboard. La columna `fecha_aprobacion` tiene **218 fechas únicas** desde `2024-01-11` hasta `2027-07-07`, lo que permite operaciones correctas.

## Endpoints Modificados

### 1. `/api/v1/dashboard/kpis-principales`
**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py` (líneas ~1531-1577)

**Cambios:**
- `total_prestamos`: Ahora usa `fecha_aprobacion` para filtrar por mes actual y mes anterior
- `creditos_nuevos_mes`: Ahora usa `fecha_aprobacion` para filtrar por mes actual y mes anterior

**Código modificado:**
```python
# Antes:
Prestamo.fecha_registro >= fecha_inicio_mes_actual

# Después:
Prestamo.fecha_aprobacion >= fecha_inicio_mes_actual
```

### 2. `/api/v1/dashboard/financiamiento-tendencia-mensual`
**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py` (líneas ~2980-2998)

**Cambios:**
- Query de GROUP BY ahora usa `fecha_aprobacion` para extraer año y mes
- Filtros de fecha ahora usan `fecha_aprobacion` en lugar de `fecha_registro`

**Código modificado:**
```python
# Antes:
func.extract("year", Prestamo.fecha_registro).label("año")
filtros_base.append(Prestamo.fecha_registro >= fecha_inicio_query)

# Después:
func.extract("year", Prestamo.fecha_aprobacion).label("año")
filtros_base.append(Prestamo.fecha_aprobacion >= fecha_inicio_query)
```

### 3. `/api/v1/dashboard/evolucion-general-mensual`
**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py` (líneas ~2660-2665)

**Cambios:**
- Query de financiamiento por mes ahora usa `fecha_aprobacion`

**Código modificado:**
```python
# Antes:
Prestamo.fecha_registro >= primer_dia_mes

# Después:
Prestamo.fecha_aprobacion >= primer_dia_mes
```

## KPIs y Gráficos Afectados

### ✅ Funcionan Correctamente Ahora:
1. **KPI "Total Financiamiento de Préstamos Concedidos en el Mes en Curso"**
   - Usa `fecha_aprobacion` para calcular el mes actual
   - Compara con el mes anterior correctamente

2. **Gráfico "Financiamiento Aprobado por Mes"**
   - Agrupa por `fecha_aprobacion` (año y mes)
   - Muestra los últimos 6 meses correctamente

3. **Gráfico "Evolución General Mensual"**
   - Calcula financiamiento por mes usando `fecha_aprobacion`

## Notas Importantes

1. **⚠️ TEMPORAL:** Estos cambios son temporales hasta que se corrija la migración de `fecha_registro`

2. **Marcadores en el código:** Todos los cambios están marcados con:
   ```python
   # ⚠️ TEMPORAL: Usar fecha_aprobacion porque fecha_registro no migró correctamente
   ```

3. **Otros endpoints:** Algunos endpoints pueden seguir usando `fecha_registro` si no son críticos para el dashboard principal

4. **Backup disponible:** Existe un script `SCRIPT_COPIAR_FECHA_APROBACION_A_REGISTRO.sql` para corregir `fecha_registro` cuando se decida hacerlo

## Cuando se Corrija `fecha_registro`

1. Ejecutar el script SQL para copiar `fecha_aprobacion` a `fecha_registro`
2. Revertir estos cambios en el backend
3. Cambiar todas las referencias de `fecha_aprobacion` de vuelta a `fecha_registro`
4. Eliminar los comentarios `⚠️ TEMPORAL`

## Verificación

Para verificar que los cambios funcionan correctamente:

```sql
-- Verificar que fecha_aprobacion tiene fechas variadas
SELECT
    COUNT(DISTINCT fecha_aprobacion::date) AS fechas_unicas,
    MIN(fecha_aprobacion::date) AS fecha_min,
    MAX(fecha_aprobacion::date) AS fecha_max
FROM prestamos
WHERE estado = 'APROBADO' AND fecha_aprobacion IS NOT NULL;
```

**Resultado esperado:** 218 fechas únicas (rango: 2024-01-11 a 2027-07-07)

---

**Fecha de creación:** Noviembre 2025
**Estado:** Activo (temporal)
**Última revisión:** Noviembre 2025

