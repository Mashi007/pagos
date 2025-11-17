# 🔍 Auditoría: Endpoint financiamiento-por-rangos

## 📊 Tabla y Campos Utilizados

### Tabla Principal
**Tabla:** `prestamos`
**Modelo:** `Prestamo` (backend/app/models/prestamo.py)

### Campos Utilizados

#### 1. Filtro Principal (OBLIGATORIO)
- **Campo:** `estado`
- **Tipo:** `String(20)`
- **Valor requerido:** `"APROBADO"`
- **Uso:** Filtra solo préstamos aprobados
```python
query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
```

#### 2. Campo Principal para Cálculo (OBLIGATORIO)
- **Campo:** `total_financiamiento`
- **Tipo:** `Numeric(15, 2)`
- **Condición:** `IS NOT NULL AND > 0`
- **Uso:** Monto total del préstamo para distribución por rangos
```python
query_base = query_base.filter(
    and_(
        Prestamo.total_financiamiento.isnot(None),
        Prestamo.total_financiamiento > 0
    )
)
```

#### 3. Campos de Filtros de Fecha (OPCIONAL - OR entre ellos)
El endpoint usa **OR** entre estos 3 campos para filtrar por fecha:

- **Campo 1:** `fecha_registro`
  - **Tipo:** `TIMESTAMP`
  - **Uso:** Fecha de registro del préstamo

- **Campo 2:** `fecha_aprobacion`
  - **Tipo:** `TIMESTAMP`
  - **Uso:** Fecha de aprobación del préstamo

- **Campo 3:** `fecha_base_calculo`
  - **Tipo:** `Date`
  - **Uso:** Fecha base para cálculo de amortizaciones

**Lógica:** Un préstamo se incluye si **AL MENOS UNA** de estas fechas está en el rango especificado.

#### 4. Campos de Filtros Adicionales (OPCIONAL)

- **Campo:** `analista`
  - **Tipo:** `String(100)`
  - **Uso:** Filtrar por analista asignado
  - **Búsqueda:** También busca en `producto_financiero`

- **Campo:** `concesionario`
  - **Tipo:** `String(100)`
  - **Uso:** Filtrar por concesionario

- **Campo:** `modelo`
  - **Tipo:** `String(100)`
  - **Uso:** Filtrar por modelo de vehículo
  - **Búsqueda:** Busca en `producto` y `modelo_vehiculo`

#### 5. Campo para Agrupación
- **Campo:** `id`
  - **Tipo:** `Integer` (Primary Key)
  - **Uso:** Para contar préstamos y agrupar por rangos

## 📋 Estructura de la Query SQL

### Query Base
```sql
SELECT * FROM prestamos
WHERE estado = 'APROBADO'
```

### Con Filtros de Fecha (OR entre fechas)
```sql
SELECT * FROM prestamos
WHERE estado = 'APROBADO'
AND (
    (fecha_registro IS NOT NULL AND fecha_registro >= :fecha_inicio AND fecha_registro <= :fecha_fin)
    OR
    (fecha_aprobacion IS NOT NULL AND fecha_aprobacion >= :fecha_inicio AND fecha_aprobacion <= :fecha_fin)
    OR
    (fecha_base_calculo IS NOT NULL AND fecha_base_calculo >= :fecha_inicio AND fecha_base_calculo <= :fecha_fin)
)
```

### Con Filtro de Monto Válido
```sql
SELECT * FROM prestamos
WHERE estado = 'APROBADO'
AND total_financiamiento IS NOT NULL
AND total_financiamiento > 0
```

### Query Final para Rangos
```sql
SELECT
    CASE
        WHEN total_financiamiento >= 0 AND total_financiamiento < 300 THEN '0-300'
        WHEN total_financiamiento >= 300 AND total_financiamiento < 600 THEN '300-600'
        -- ... más rangos
        WHEN total_financiamiento >= 50000 THEN '50000+'
    END AS rango,
    COUNT(*) AS cantidad_prestamos,
    SUM(total_financiamiento) AS monto_total
FROM prestamos
WHERE estado = 'APROBADO'
AND total_financiamiento IS NOT NULL
AND total_financiamiento > 0
GROUP BY rango
```

## 🔍 Campos Críticos para el Problema

### Si el endpoint retorna 0 préstamos, verificar:

1. **`estado` = 'APROBADO'**
   - ¿Hay préstamos con estado='APROBADO'?
   ```sql
   SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO';
   ```

2. **`total_financiamiento` > 0**
   - ¿Hay préstamos con monto válido?
   ```sql
   SELECT COUNT(*) FROM prestamos
   WHERE estado = 'APROBADO'
   AND total_financiamiento IS NOT NULL
   AND total_financiamiento > 0;
   ```

3. **Fechas en rango**
   - ¿Hay préstamos con fechas en el rango especificado?
   ```sql
   SELECT COUNT(*) FROM prestamos
   WHERE estado = 'APROBADO'
   AND total_financiamiento > 0
   AND (
       (fecha_registro >= '2025-01-01' AND fecha_registro <= '2026-01-01')
       OR
       (fecha_aprobacion >= '2025-01-01' AND fecha_aprobacion <= '2026-01-01')
       OR
       (fecha_base_calculo >= '2025-01-01' AND fecha_base_calculo <= '2026-01-01')
   );
   ```

## 📊 Resumen de Conexiones

| Tabla | Campo | Tipo | Uso | Obligatorio |
|-------|-------|------|-----|-------------|
| `prestamos` | `estado` | String(20) | Filtrar aprobados | ✅ Sí |
| `prestamos` | `total_financiamiento` | Numeric(15,2) | Monto para rangos | ✅ Sí |
| `prestamos` | `fecha_registro` | TIMESTAMP | Filtro de fecha (OR) | ❌ No |
| `prestamos` | `fecha_aprobacion` | TIMESTAMP | Filtro de fecha (OR) | ❌ No |
| `prestamos` | `fecha_base_calculo` | Date | Filtro de fecha (OR) | ❌ No |
| `prestamos` | `analista` | String(100) | Filtro opcional | ❌ No |
| `prestamos` | `concesionario` | String(100) | Filtro opcional | ❌ No |
| `prestamos` | `modelo_vehiculo` | String(100) | Filtro opcional | ❌ No |
| `prestamos` | `producto` | String(100) | Filtro opcional (modelo) | ❌ No |
| `prestamos` | `producto_financiero` | String(100) | Filtro opcional (analista) | ❌ No |
| `prestamos` | `id` | Integer | Conteo y agrupación | ✅ Sí |

## 🔧 Scripts de Verificación

### Verificar datos en la tabla
```bash
cd backend
python scripts/auditoria_financiamiento_rangos.py
```

### Verificar directamente en SQL
```sql
-- Total préstamos aprobados
SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO';

-- Préstamos con monto válido
SELECT COUNT(*) FROM prestamos
WHERE estado = 'APROBADO'
AND total_financiamiento IS NOT NULL
AND total_financiamiento > 0;

-- Préstamos en rango del año 2025
SELECT COUNT(*) FROM prestamos
WHERE estado = 'APROBADO'
AND total_financiamiento > 0
AND (
    (fecha_registro >= '2025-01-01' AND fecha_registro <= '2025-12-31')
    OR
    (fecha_aprobacion >= '2025-01-01' AND fecha_aprobacion <= '2025-12-31')
    OR
    (fecha_base_calculo >= '2025-01-01' AND fecha_base_calculo <= '2025-12-31')
);
```

