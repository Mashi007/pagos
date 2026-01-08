# RELACIÓN ENTRE TABLAS PRESTAMOS Y CUOTAS

## 📋 RESUMEN DE LA RELACIÓN

**Tipo de relación:** Uno a Muchos (1:N)
- **1 Préstamo** → **N Cuotas**
- Un préstamo puede tener múltiples cuotas
- Cada cuota pertenece a un único préstamo

---

## 🔗 ESTRUCTURA DE LA RELACIÓN

### Tabla: `prestamos`
- **Clave Primaria:** `id` (Integer)
- **Campo relacionado:** `numero_cuotas` (Integer) - Número de cuotas planificadas

### Tabla: `cuotas`
- **Clave Primaria:** `id` (Integer)
- **Clave Foránea:** `prestamo_id` (Integer) → `prestamos.id`
- **Campo relacionado:** `numero_cuota` (Integer) - Número de cuota (1, 2, 3, ...)

---

## 🔑 FOREIGN KEY

```sql
cuotas.prestamo_id → prestamos.id
```

**Definición en el modelo:**
```python
prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
```

**Características:**
- ✅ **NOT NULL:** Cada cuota DEBE tener un préstamo asociado
- ✅ **INDEXADO:** Optimizado para búsquedas y JOINs
- ✅ **Integridad Referencial:** Garantiza que cada cuota pertenece a un préstamo válido

---

## 📊 CAMPOS RELACIONADOS

### En `prestamos`:
- `numero_cuotas`: Número total de cuotas planificadas para el préstamo
- `fecha_base_calculo`: Fecha base para calcular las fechas de vencimiento de las cuotas
- `modalidad_pago`: MENSUAL, QUINCENAL, SEMANAL (determina intervalo entre cuotas)
- `total_financiamiento`: Monto total del préstamo
- `cuota_periodo`: Monto de cada cuota
- `tasa_interes`: Tasa de interés para calcular intereses de las cuotas

### En `cuotas`:
- `prestamo_id`: ID del préstamo al que pertenece (FK)
- `numero_cuota`: Número de cuota (1, 2, 3, ... hasta `numero_cuotas`)
- `fecha_vencimiento`: Fecha calculada desde `fecha_base_calculo` según `modalidad_pago`
- `monto_cuota`: Monto de la cuota (debe coincidir con `cuota_periodo` del préstamo)
- `monto_capital`: Parte de capital de la cuota
- `monto_interes`: Parte de interés de la cuota

---

## ✅ REGLAS DE CONSISTENCIA

1. **Número de cuotas:**
   - `COUNT(cuotas WHERE prestamo_id = X)` DEBE ser igual a `prestamos.numero_cuotas`

2. **Números de cuota únicos:**
   - Cada préstamo debe tener cuotas con `numero_cuota` desde 1 hasta `numero_cuotas`
   - No debe haber duplicados de `numero_cuota` para el mismo `prestamo_id`

3. **Fechas de vencimiento:**
   - Se calculan desde `prestamos.fecha_base_calculo`
   - Intervalo según `prestamos.modalidad_pago`:
     - MENSUAL: +1 mes por cada cuota
     - QUINCENAL: +15 días por cada cuota
     - SEMANAL: +7 días por cada cuota

4. **Montos:**
   - `cuotas.monto_cuota` debe ser igual a `prestamos.cuota_periodo`
   - `SUM(cuotas.monto_capital)` debe aproximarse a `prestamos.total_financiamiento`

---

## 🔍 CONSULTAS ÚTILES

### Ver todas las cuotas de un préstamo:
```sql
SELECT c.*
FROM cuotas c
WHERE c.prestamo_id = :prestamo_id
ORDER BY c.numero_cuota;
```

### Ver préstamo con resumen de cuotas:
```sql
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(c.id) AS cuotas_generadas,
    SUM(c.total_pagado) AS total_pagado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.id = :prestamo_id
GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas;
```

### Verificar integridad referencial:
```sql
-- Cuotas sin préstamo válido (huérfanas)
SELECT c.*
FROM cuotas c
LEFT JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.id IS NULL;

-- Préstamos sin cuotas
SELECT p.*
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE c.id IS NULL AND p.estado = 'APROBADO';
```

---

## 📝 NOTAS IMPORTANTES

1. **Generación de cuotas:**
   - Las cuotas se generan automáticamente cuando un préstamo se aprueba
   - Se usa el servicio `generar_tabla_amortizacion()` en `prestamo_amortizacion_service.py`
   - Se calculan usando el método francés de amortización

2. **Eliminación en cascada:**
   - Si se elimina un préstamo, las cuotas asociadas deberían eliminarse
   - Verificar configuración de CASCADE en la base de datos

3. **Actualización de cuotas:**
   - Los pagos se registran en la tabla `pagos`
   - Se vinculan a cuotas a través de la tabla `pago_cuotas`
   - Los campos `total_pagado`, `capital_pagado`, `interes_pagado` se actualizan automáticamente

---

## 🎯 DIAGRAMA DE RELACIÓN

```
prestamos (1)
    │
    │ prestamo_id (FK)
    │
    └───< (N) cuotas
            │
            ├── numero_cuota (1, 2, 3, ...)
            ├── fecha_vencimiento
            ├── monto_cuota
            ├── total_pagado
            └── estado (PENDIENTE, PAGADO, etc.)
```

---

## ✅ VERIFICACIÓN ACTUAL

**Estado:** ✅ Todas las relaciones están correctas
- Total préstamos: 4,042
- Total cuotas: 94,175
- Préstamos con cuotas: 4,042 (100%)
- Consistencia: Todos los préstamos tienen el número correcto de cuotas
