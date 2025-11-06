# 📊 ALMACENAMIENTO DE TABLAS DE AMORTIZACIÓN (CUOTAS)

## 🗄️ UBICACIÓN EN BASE DE DATOS

### Tabla Principal: `cuotas`

**Base de Datos:** PostgreSQL  
**Schema:** `public`  
**Tabla:** `cuotas`

---

## 📋 ESTRUCTURA DE LA TABLA `cuotas`

### Campos de Identificación

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INTEGER (PK) | ✅ ID único con autoincremento |
| `prestamo_id` | INTEGER (FK) | ✅ **Foreign Key a `prestamos.id`** |
| `numero_cuota` | INTEGER | ✅ **Número de cuota (1, 2, 3, ...)** |

### Campos de Fechas

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `fecha_vencimiento` | DATE | ✅ **Fecha límite de pago** (calculada desde `fecha_base_calculo`) | `2025-11-30` |
| `fecha_pago` | DATE (nullable) | Fecha real cuando se pagó (NULL si pendiente) | `2025-11-15` |

### Campos de Montos Programados

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `monto_cuota` | NUMERIC(12,2) | ✅ **Monto total programado de la cuota** | `500.00` |
| `monto_capital` | NUMERIC(12,2) | Monto de capital de esta cuota | `450.00` |
| `monto_interes` | NUMERIC(12,2) | Monto de interés de esta cuota | `50.00` |

### Campos de Saldos

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `saldo_capital_inicial` | NUMERIC(12,2) | Saldo de capital al inicio del período | `10,000.00` |
| `saldo_capital_final` | NUMERIC(12,2) | Saldo de capital al fin del período | `9,550.00` |

### Campos de Montos Pagados

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `capital_pagado` | NUMERIC(12,2) | Capital ya pagado (default: 0.00) | `450.00` |
| `interes_pagado` | NUMERIC(12,2) | Interés ya pagado (default: 0.00) | `50.00` |
| `mora_pagada` | NUMERIC(12,2) | Mora ya pagada (default: 0.00) | `0.00` |
| `total_pagado` | NUMERIC(12,2) | ✅ **Total pagado en esta cuota** (default: 0.00) | `500.00` |

### Campos de Montos Pendientes

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `capital_pendiente` | NUMERIC(12,2) | Capital pendiente de esta cuota | `0.00` |
| `interes_pendiente` | NUMERIC(12,2) | Interés pendiente de esta cuota | `0.00` |

### Campos de Mora

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `dias_mora` | INTEGER | Días de atraso (default: 0) | `15` |
| `monto_mora` | NUMERIC(12,2) | Monto de mora calculado (default: 0.00) | `25.00` |
| `tasa_mora` | NUMERIC(5,2) | Tasa de mora aplicada % (default: 0.00) | `2.50` |

### Campos de Estado

| Campo | Tipo | Descripción | Valores Posibles |
|-------|------|-------------|------------------|
| `estado` | VARCHAR(20) | ✅ **Estado de la cuota** | `PENDIENTE`, `PAGADO`, `ATRASADO`, `PARCIAL`, `ADELANTADO` |

### Campos Adicionales

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `observaciones` | VARCHAR(500) | Observaciones sobre la cuota |
| `es_cuota_especial` | BOOLEAN | Si es una cuota especial (default: false) |
| `creado_en` | TIMESTAMP | Fecha de creación (default: now()) |
| `actualizado_en` | TIMESTAMP | Fecha de última actualización |

---

## 🔗 RELACIONES

### Foreign Keys

```sql
-- Relación con préstamos
prestamo_id → prestamos.id
```

### Tabla de Asociación: `pago_cuotas`

**Propósito:** Vincular pagos con cuotas (relación muchos a muchos)

```sql
CREATE TABLE pago_cuotas (
    pago_id INTEGER REFERENCES pagos(id) ON DELETE CASCADE,
    cuota_id INTEGER REFERENCES cuotas(id) ON DELETE CASCADE,
    monto_aplicado NUMERIC(12,2) NOT NULL,
    aplicado_a_capital NUMERIC(12,2) DEFAULT 0.00,
    aplicado_a_interes NUMERIC(12,2) DEFAULT 0.00,
    aplicado_a_mora NUMERIC(12,2) DEFAULT 0.00,
    PRIMARY KEY (pago_id, cuota_id)
);
```

**Uso:** Permite que un pago se distribuya entre múltiples cuotas, o que una cuota reciba pagos de múltiples registros.

---

## 💻 MODELO SQLALCHEMY

### Ubicación del Código

**Archivo:** `backend/app/models/amortizacion.py`

```python
class Cuota(Base):
    """
    Modelo para las cuotas de un préstamo
    Representa cada pago periódico que debe hacer el cliente
    """
    
    __tablename__ = "cuotas"
    
    # Claves primarias y foráneas
    id = Column(Integer, primary_key=True, index=True)
    prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
    numero_cuota = Column(Integer, nullable=False)
    
    # Fechas
    fecha_vencimiento = Column(Date, nullable=False, index=True)
    fecha_pago = Column(Date, nullable=True)
    
    # Montos programados
    monto_cuota = Column(Numeric(12, 2), nullable=False)
    monto_capital = Column(Numeric(12, 2), nullable=False)
    monto_interes = Column(Numeric(12, 2), nullable=False)
    
    # ... (resto de campos)
```

---

## 🔧 LÓGICA DE GENERACIÓN

### Servicio de Generación

**Archivo:** `backend/app/services/prestamo_amortizacion_service.py`

**Función Principal:** `generar_tabla_amortizacion()`

### Proceso de Generación

1. **Eliminar cuotas existentes** (si las hay)
   ```python
   db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).delete()
   ```

2. **Validar datos del préstamo**
   - `total_financiamiento > 0`
   - `numero_cuotas > 0`

3. **Calcular intervalo entre cuotas** según modalidad:
   - **MENSUAL:** 30 días (usa `relativedelta` para meses calendario)
   - **QUINCENAL:** 15 días
   - **SEMANAL:** 7 días

4. **Calcular tasa de interés mensual**
   ```python
   tasa_mensual = tasa_interes / 100 / 12
   ```

5. **Generar cada cuota** (loop de 1 a `numero_cuotas`):
   - **Calcular fecha de vencimiento:**
     ```python
     if modalidad == "MENSUAL":
         fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
     else:
         fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)
     ```
   
   - **Calcular montos:**
     ```python
     monto_cuota = prestamo.cuota_periodo  # Cuota fija (Método Francés)
     monto_interes = saldo_capital * tasa_mensual
     monto_capital = monto_cuota - monto_interes
     ```
   
   - **Actualizar saldo:**
     ```python
     saldo_capital_inicial = saldo_capital
     saldo_capital = saldo_capital - monto_capital
     saldo_capital_final = saldo_capital
     ```
   
   - **Crear registro de cuota:**
     ```python
     cuota = Cuota(
         prestamo_id=prestamo.id,
         numero_cuota=numero_cuota,
         fecha_vencimiento=fecha_vencimiento,
         monto_cuota=monto_cuota,
         monto_capital=monto_capital,
         monto_interes=monto_interes,
         saldo_capital_inicial=saldo_capital_inicial,
         saldo_capital_final=saldo_capital_final,
         capital_pagado=Decimal("0.00"),
         interes_pagado=Decimal("0.00"),
         mora_pagada=Decimal("0.00"),
         total_pagado=Decimal("0.00"),
         capital_pendiente=monto_capital,
         interes_pendiente=monto_interes,
         estado="PENDIENTE",
     )
     db.add(cuota)
     ```

6. **Commit a la base de datos**
   ```python
   db.commit()
   ```

---

## 📍 CUÁNDO SE GENERAN LAS CUOTAS

### 1. Automáticamente al Aprobar Préstamo

**Ubicación:** `backend/app/api/v1/endpoints/prestamos.py`

**Función:** `procesar_cambio_estado()`

```python
if nuevo_estado == "APROBADO":
    prestamo.fecha_aprobacion = datetime.now()
    
    # Si tiene fecha_base_calculo, generar tabla de amortización
    if prestamo.fecha_base_calculo:
        generar_amortizacion(prestamo, prestamo.fecha_base_calculo, db)
```

**Condiciones:**
- ✅ Préstamo cambia a estado `APROBADO`
- ✅ Préstamo tiene `fecha_base_calculo` establecida

### 2. Manualmente por Endpoint

**Endpoint:** `POST /api/v1/prestamos/{prestamo_id}/generar-amortizacion`

**Ubicación:** `backend/app/api/v1/endpoints/prestamos.py`

**Función:** `generar_amortizacion_prestamo()`

**Uso:**
```bash
curl -X POST "http://localhost:8000/api/v1/prestamos/3708/generar-amortizacion" \
  -H "Authorization: Bearer TOKEN"
```

### 3. Por Script Python

**Script:** `backend/scripts/generar_cuotas_faltantes.py`

**Uso:**
```bash
py scripts/generar_cuotas_faltantes.py --prestamo-id 3708
```

---

## 📊 EJEMPLO DE DATOS ALMACENADOS

### Préstamo de Ejemplo

**Préstamo:**
- ID: 3708
- Total Financiamiento: $12,000.00
- Número de Cuotas: 12
- Modalidad: MENSUAL
- Tasa de Interés: 0% (o 12% anual)
- Fecha Base Cálculo: 2025-10-31

### Cuotas Generadas (Primeras 3)

| id | prestamo_id | numero_cuota | fecha_vencimiento | monto_cuota | monto_capital | monto_interes | total_pagado | estado |
|----|-------------|--------------|-------------------|-------------|---------------|---------------|--------------|--------|
| 1 | 3708 | 1 | 2025-11-30 | 1,000.00 | 1,000.00 | 0.00 | 0.00 | PENDIENTE |
| 2 | 3708 | 2 | 2025-12-31 | 1,000.00 | 1,000.00 | 0.00 | 0.00 | PENDIENTE |
| 3 | 3708 | 3 | 2026-01-31 | 1,000.00 | 1,000.00 | 0.00 | 0.00 | PENDIENTE |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
| 12 | 3708 | 12 | 2026-10-31 | 1,000.00 | 1,000.00 | 0.00 | 0.00 | PENDIENTE |

---

## 🔍 CONSULTAS ÚTILES

### Ver todas las cuotas de un préstamo

```sql
SELECT 
    numero_cuota,
    fecha_vencimiento,
    monto_cuota,
    total_pagado,
    estado
FROM cuotas
WHERE prestamo_id = 3708
ORDER BY numero_cuota;
```

### Ver cuotas vencidas

```sql
SELECT 
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.estado,
    CURRENT_DATE - c.fecha_vencimiento as dias_vencido
FROM cuotas c
WHERE c.prestamo_id = 3708
  AND c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO'
ORDER BY c.fecha_vencimiento;
```

### Ver resumen de cuotas por préstamo

```sql
SELECT 
    prestamo_id,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) as cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) as cuotas_pendientes,
    SUM(monto_cuota) as monto_total_programado,
    SUM(total_pagado) as monto_total_pagado
FROM cuotas
WHERE prestamo_id = 3708
GROUP BY prestamo_id;
```

---

## ✅ RESUMEN

### Dónde se Almacenan

1. **Base de Datos:** Tabla `cuotas` en PostgreSQL
2. **Modelo:** `Cuota` en `backend/app/models/amortizacion.py`
3. **Relación:** Foreign Key `prestamo_id → prestamos.id`

### Qué se Almacena

1. **Fechas:** `fecha_vencimiento` (programada), `fecha_pago` (real)
2. **Montos Programados:** `monto_cuota`, `monto_capital`, `monto_interes`
3. **Montos Pagados:** `total_pagado`, `capital_pagado`, `interes_pagado`, `mora_pagada`
4. **Montos Pendientes:** `capital_pendiente`, `interes_pendiente`
5. **Estado:** `PENDIENTE`, `PAGADO`, `ATRASADO`, `PARCIAL`, `ADELANTADO`
6. **Saldos:** `saldo_capital_inicial`, `saldo_capital_final`

### Cómo se Generan

1. **Automáticamente:** Al aprobar préstamo (si tiene `fecha_base_calculo`)
2. **Manual:** Por endpoint API o script Python
3. **Lógica:** Método Francés (cuota fija), calcula desde `fecha_base_calculo`

### Cuándo se Actualizan

1. **Al registrar pagos:** Se actualiza `total_pagado`, `capital_pagado`, etc.
2. **Al calcular mora:** Se actualiza `dias_mora`, `monto_mora`
3. **Al cambiar estado:** Se actualiza `estado` (PENDIENTE → PAGADO, etc.)

---

**Estado:** ✅ **DOCUMENTACIÓN COMPLETA**

