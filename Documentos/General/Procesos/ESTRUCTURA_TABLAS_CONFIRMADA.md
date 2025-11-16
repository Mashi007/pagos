# 📋 ESTRUCTURA DE TABLAS CONFIRMADA - Base de Datos

## Fecha de Confirmación
Verificado desde DBeaver y código backend

---

## 📊 TABLA: `prestamos`

### Campos Principales

| Campo | Tipo | Nullable | Default | Descripción | Uso en Dashboard |
|-------|------|----------|---------|-------------|------------------|
| `id` | INTEGER | NO | `nextval('prestamos_id_seq'::regclass)` | ✅ ID único con autoincremento | ✅ Clave primaria |
| `cliente_id` | INTEGER | NO | - | ✅ Foreign Key a `clientes.id` | ✅ JOIN con clientes |
| `cedula` | VARCHAR(20) | NO | - | Cédula del cliente | ✅ Búsqueda y filtros |
| `nombres` | VARCHAR(100) | NO | - | Nombre del cliente | ✅ Visualización |
| `total_financiamiento` | NUMERIC | NO | - | Monto total del préstamo | ✅ KPIs y gráficos |
| `fecha_requerimiento` | DATE | NO | - | Fecha que necesita el préstamo | ✅ Filtros de fecha |
| `modalidad_pago` | VARCHAR(20) | NO | - | MENSUAL, QUINCENAL, SEMANAL | ✅ Cálculos de cuotas |
| `numero_cuotas` | INTEGER | NO | - | Número de cuotas | ✅ Validación |
| `cuota_periodo` | NUMERIC | NO | - | Monto por cuota | ✅ Cálculos |
| `tasa_interes` | NUMERIC | NO | `0.00` | Tasa de interés | ✅ Cálculos financieros |
| `fecha_base_calculo` | DATE | YES | - | ✅ **Fecha base para generar tabla de amortización** | ✅ Generación de cuotas |
| `producto` | VARCHAR(100) | NO | - | Modelo de vehículo | ✅ Filtros |
| `producto_financiero` | VARCHAR(100) | NO | - | Analista asignado | ✅ Filtros |
| `estado` | VARCHAR(20) | NO | `'DRAFT'` | ✅ **Estado del préstamo (DRAFT, APROBADO, etc.)** | ✅ Filtros y KPIs |
| `usuario_proponente` | VARCHAR(100) | NO | `'itmaster@rapicreditca.com'` | Email del analista | ✅ Auditoría |
| `usuario_aprobador` | VARCHAR(100) | YES | - | Email del admin | ✅ Auditoría |
| `fecha_registro` | TIMESTAMP | NO | `'2025-10-31 00:00:00'` | Fecha de creación | ✅ Filtros de fecha |
| `fecha_aprobacion` | TIMESTAMP | YES | - | ✅ **Fecha cuando se aprueba el préstamo** | ✅ Filtros y KPIs |
| `fecha_actualizacion` | TIMESTAMP | NO | `CURRENT_TIMESTAMP` | Fecha de última actualización | ✅ Auditoría |
| `concesionario` | VARCHAR(100) | YES | - | Concesionario | ✅ Filtros |
| `analista` | VARCHAR(100) | YES | - | Analista | ✅ Filtros |
| `modelo_vehiculo` | VARCHAR(100) | YES | - | Modelo del vehículo | ✅ Filtros |
| `usuario_autoriza` | VARCHAR(100) | YES | `'operaciones@rapicreditca.com'` | Usuario que autoriza | ✅ Auditoría |
| `observaciones` | TEXT | YES | `'No observaciones'` | Observaciones | - |
| `informacion_desplegable` | BOOLEAN | NO | `false` | Si ha desplegado info adicional | - |

### Relaciones

- ✅ `cliente_id` → `clientes.id` (Foreign Key: `fk_prestamos_cliente`)
- ✅ `prestamo.cliente` → Objeto Cliente (SQLAlchemy relationship)
- ✅ `cliente.prestamos` → Lista de préstamos del cliente (backref)

### Índices

- ✅ `id` (Primary Key, indexado)
- ✅ `cliente_id` (Foreign Key, indexado)
- ✅ `cedula` (indexado)
- ✅ `estado` (indexado)
- ✅ `fecha_registro` (indexado)

---

## 📊 TABLA: `cuotas`

### Campos Principales

| Campo | Tipo | Nullable | Default | Descripción | Uso en Dashboard |
|-------|------|----------|---------|-------------|------------------|
| `id` | INTEGER | NO | `nextval('cuotas_id_seq'::regclass)` | ID único con autoincremento | ✅ Clave primaria |
| `prestamo_id` | INTEGER | NO | - | ✅ **Foreign Key a `prestamos.id`** | ✅ JOIN con préstamos |
| `numero_cuota` | INTEGER | NO | - | ✅ **Número de cuota (1, 2, 3, ...)** | ✅ Ordenamiento |
| `fecha_vencimiento` | DATE | NO | - | ✅ **Fecha calculada desde `fecha_base_calculo`** | ✅ KPIs de morosidad |
| `fecha_pago` | DATE | YES | - | Fecha cuando se pagó | ✅ Cálculos de pagos |
| `monto_cuota` | NUMERIC | NO | - | ✅ **Monto total de la cuota** | ✅ Sumas y promedios |
| `monto_capital` | NUMERIC | NO | - | Monto de capital | ✅ Desglose |
| `monto_interes` | NUMERIC | NO | - | Monto de interés | ✅ Desglose |
| `saldo_capital_inicial` | NUMERIC | NO | - | Saldo inicial | ✅ Cálculos |
| `saldo_capital_final` | NUMERIC | NO | - | Saldo final | ✅ Cálculos |
| `capital_pagado` | NUMERIC | YES | - | Capital pagado | ✅ Cálculos |
| `interes_pagado` | NUMERIC | YES | - | Interés pagado | ✅ Cálculos |
| `mora_pagada` | NUMERIC | YES | - | Mora pagada | ✅ Cálculos |
| `total_pagado` | NUMERIC | YES | - | ✅ **Monto total pagado en esta cuota** | ✅ KPIs principales |
| `capital_pendiente` | NUMERIC | NO | - | Capital pendiente | ✅ Cálculos |
| `interes_pendiente` | NUMERIC | NO | - | Interés pendiente | ✅ Cálculos |
| `dias_mora` | INTEGER | YES | - | Días de mora (calculado cuando hay pago tardío) | ✅ KPIs de mora |
| `monto_mora` | NUMERIC | YES | - | Monto de mora (calculado cuando hay pago tardío) | ✅ KPIs de mora |
| `tasa_mora` | NUMERIC | YES | - | Tasa de mora aplicada | ✅ Cálculos |
| `dias_morosidad` | INTEGER | YES | `0` | ✅ **Días de morosidad calculados automáticamente** | ✅ KPIs de morosidad (optimizado) |
| `monto_morosidad` | NUMERIC(12,2) | YES | `0.00` | ✅ **Monto pendiente: monto_cuota - total_pagado (calculado automáticamente)** | ✅ KPIs de morosidad (optimizado) |
| `estado` | VARCHAR(20) | NO | - | ✅ **Estado (PENDIENTE, PAGADO, PARCIAL, ATRASADO, ADELANTADO)** | ✅ KPIs y filtros |
| `observaciones` | VARCHAR(500) | YES | - | Observaciones | - |
| `es_cuota_especial` | BOOLEAN | YES | - | Si es cuota especial | - |
| `creado_en` | TIMESTAMP | YES | `now()` | Fecha de creación | ✅ Auditoría |
| `actualizado_en` | TIMESTAMP | YES | - | Fecha de actualización | ✅ Auditoría |

### Relaciones

- ✅ `prestamo_id` → `prestamos.id` (Foreign Key implícita)
- ✅ `cuota.prestamo` → Objeto Prestamo (SQLAlchemy relationship)

### Índices

- ✅ `id` (Primary Key, indexado)
- ✅ `prestamo_id` (Foreign Key, indexado)
- ✅ `fecha_vencimiento` (indexado)
- ✅ `estado` (indexado)
- ✅ `dias_morosidad` (indexado) - ✅ **NUEVO: Índice para queries de morosidad optimizadas**
- ✅ `monto_morosidad` (indexado) - ✅ **NUEVO: Índice para queries de morosidad optimizadas**
- ✅ Múltiples índices compuestos para optimización
- ✅ `idx_cuotas_dias_morosidad` (WHERE dias_morosidad > 0) - ✅ **NUEVO: Índice parcial**
- ✅ `idx_cuotas_monto_morosidad` (WHERE monto_morosidad > 0) - ✅ **NUEVO: Índice parcial**
- ✅ `idx_cuotas_morosidad_completo` (dias_morosidad, monto_morosidad, estado) - ✅ **NUEVO: Índice compuesto**

---

## 📊 TABLA: `clientes`

### Campos Principales

| Campo | Tipo | Nullable | Default | Descripción | Uso en Dashboard |
|-------|------|----------|---------|-------------|------------------|
| `id` | INTEGER | NO | `nextval('clientes_id_seq'::regclass)` | ✅ ID único con autoincremento | ✅ Clave primaria |
| `cedula` | VARCHAR(20) | NO | `'Z999999999'` | ✅ **Cédula del cliente (usado para búsqueda)** | ✅ Búsqueda y filtros |
| `nombres` | VARCHAR(100) | NO | - | Nombres completos | ✅ Visualización |
| `telefono` | VARCHAR(15) | NO | `'+589999999999'` | Teléfono | - |
| `email` | VARCHAR(100) | NO | `'buscaremail@noemail.com'` | Email | - |
| `direccion` | TEXT | NO | `'Actualizar dirección'` | Dirección | - |
| `fecha_nacimiento` | DATE | NO | `'2000-01-01'` | Fecha de nacimiento | - |
| `ocupacion` | VARCHAR(100) | NO | `'Actualizar ocupación'` | Ocupación | - |
| `estado` | VARCHAR(20) | NO | `'ACTIVO'` | ✅ **Estado (ACTIVO, INACTIVO, FINALIZADO)** | ✅ Filtros críticos |
| `activo` | BOOLEAN | NO | `true` | ✅ **Boolean sincronizado con estado** | ✅ Filtros críticos |
| `fecha_registro` | TIMESTAMP | NO | `'2025-10-31 00:00:00'` | Fecha de registro | ✅ Filtros de fecha |
| `fecha_actualizacion` | TIMESTAMP | NO | `CURRENT_TIMESTAMP` | Fecha de actualización | ✅ Auditoría |
| `usuario_registro` | VARCHAR(50) | NO | `'itmaster@rapicreditca.com'` | Usuario que registró | ✅ Auditoría |
| `notas` | TEXT | NO | `'No existe observaciones'` | Notas | - |

### Relaciones

- ✅ `cliente.prestamos` → Lista de préstamos del cliente (backref desde Prestamo)

### Índices

- ✅ `id` (Primary Key, indexado)
- ✅ `cedula` (indexado)
- ✅ `estado` (indexado)
- ✅ `activo` (indexado)
- ✅ `telefono` (indexado)
- ✅ `email` (indexado)

---

## 📊 TABLA: `pagos`

### Campos Principales (Relevantes para Dashboard)

| Campo | Tipo | Nullable | Default | Descripción | Uso en Dashboard |
|-------|------|----------|---------|-------------|------------------|
| `id` | INTEGER | NO | `nextval('pagos_id_seq'::regclass)` | ID único | ✅ Clave primaria |
| `prestamo_id` | INTEGER | YES | - | Foreign Key a `prestamos.id` | ✅ JOIN con préstamos |
| `numero_cuota` | INTEGER | YES | - | Número de cuota | ✅ JOIN con cuotas |
| `cedula` | VARCHAR | YES | - | Cédula del cliente | ✅ Búsqueda y filtros |
| `monto_pagado` | NUMERIC | NO | - | Monto pagado | ✅ KPIs principales |
| `fecha_pago` | TIMESTAMP | NO | - | Fecha del pago | ✅ Filtros de fecha |
| `activo` | BOOLEAN | YES | `true` | Si el pago está activo | ✅ Filtros críticos |
| `conciliado` | BOOLEAN | YES | `false` | Si está conciliado | ✅ KPIs de conciliación |
| `fecha_conciliacion` | TIMESTAMP | YES | - | Fecha de conciliación | ✅ Auditoría |
| `estado` | VARCHAR | YES | `'PAGADO'` | Estado del pago | ✅ Filtros |

### Relaciones

- ✅ `prestamo_id` → `prestamos.id` (Foreign Key)
- ✅ `numero_cuota` + `prestamo_id` → `cuotas` (relación implícita)

### Índices

- ✅ `id` (Primary Key, indexado)
- ✅ `prestamo_id` (indexado)
- ✅ `cedula` (indexado)
- ✅ `fecha_pago` (indexado)
- ✅ `activo` (indexado)
- ✅ Múltiples índices compuestos para optimización

---

## 🔗 RELACIONES CONFIRMADAS

### Foreign Keys

| Tabla Origen | Columna Origen | Tabla Destino | Columna Destino | Constraint |
|--------------|----------------|--------------|-----------------|------------|
| `prestamos` | `cliente_id` | `clientes` | `id` | `fk_prestamos_cliente` |
| `cuotas` | `prestamo_id` | `prestamos` | `id` | (implícita) |
| `pagos` | `prestamo_id` | `prestamos` | `id` | (implícita) |

### Relaciones SQLAlchemy

```python
# Prestamo → Cliente
prestamo.cliente  # Accede al objeto Cliente
cliente.prestamos  # Lista de préstamos del cliente (backref)

# Cuota → Prestamo
cuota.prestamo  # Accede al objeto Prestamo
prestamo.cuotas  # Lista de cuotas del préstamo (backref)
```

---

## ✅ REGLAS DE NEGOCIO CONFIRMADAS

### 1. Creación de Préstamos

- ✅ Cliente debe existir
- ✅ Cliente debe estar ACTIVO (`cliente.estado = 'ACTIVO'`)
- ✅ Se asigna `cliente_id = cliente.id` automáticamente
- ✅ Todos los préstamos tienen ID (autoincremento)
- ✅ Estado inicial: `'DRAFT'`

### 2. Aprobación de Préstamos

- ✅ Al aprobar: `fecha_aprobacion = datetime.now()`
- ✅ Si tiene `fecha_base_calculo`: se genera tabla de amortización automáticamente
- ✅ Estado cambia a: `'APROBADO'`

### 3. Generación de Tabla de Amortización

- ✅ Usa `prestamos.fecha_base_calculo` como fecha base
- ✅ Calcula `cuotas.fecha_vencimiento` desde `fecha_base_calculo`
- ✅ Modalidad MENSUAL: usa `relativedelta(months=numero_cuota)`
- ✅ Modalidad QUINCENAL/SEMANAL: usa `timedelta(days=intervalo * numero_cuota)`

### 4. Filtros de Clientes

- ✅ Solo clientes ACTIVOS pueden crear préstamos
- ✅ Backend: `obtener_datos_cliente()` filtra `estado = 'ACTIVO'`
- ✅ Frontend: `searchClientes()` filtra `estado: 'ACTIVO'`

### 5. Estados de Cuotas

- ✅ `PENDIENTE`: `total_pagado = 0`
- ✅ `PARCIAL`: `0 < total_pagado < monto_cuota` y `fecha_vencimiento <= CURRENT_DATE`
- ✅ `ADELANTADO`: `0 < total_pagado < monto_cuota` y `fecha_vencimiento > CURRENT_DATE`
- ✅ `PAGADO`: `total_pagado >= monto_cuota`
- ✅ `ATRASADO`: `fecha_vencimiento < CURRENT_DATE` y `estado != 'PAGADO'`

---

## 📊 CAMPOS CLAVE PARA DASHBOARD

### KPIs Principales

| KPI | Tabla | Campo(s) | Filtros Aplicados |
|-----|-------|----------|-------------------|
| Total Préstamos | `prestamos` | `COUNT(id)` | `estado = 'APROBADO'` |
| Total Cartera | `prestamos` | `SUM(total_financiamiento)` | `estado = 'APROBADO'` |
| Cartera Vencida | `cuotas` | `SUM(monto_morosidad)` | ✅ **Usar columna calculada automáticamente** | `dias_morosidad > 0`, `monto_morosidad > 0` |
| Total Pagado | `pagos` | `SUM(monto_pagado)` | `activo = true` |
| Total Pagado (Cuotas) | `cuotas` | `SUM(total_pagado)` | - |
| Clientes Activos | `prestamos` | `COUNT(DISTINCT cedula)` | `estado = 'APROBADO'` |
| Clientes en Mora | `cuotas` + `prestamos` | `COUNT(DISTINCT prestamo.cedula)` | ✅ **Usar columna calculada automáticamente** | `dias_morosidad > 0`, `monto_morosidad > 0` |

### Filtros Comunes

| Filtro | Tabla | Campo | Valores |
|--------|-------|-------|---------|
| Estado Préstamo | `prestamos` | `estado` | `'APROBADO'`, `'DRAFT'`, etc. |
| Estado Cliente | `clientes` | `estado` | `'ACTIVO'`, `'INACTIVO'`, `'FINALIZADO'` |
| Analista | `prestamos` | `analista` o `producto_financiero` | - |
| Concesionario | `prestamos` | `concesionario` | - |
| Modelo | `prestamos` | `modelo_vehiculo` o `producto` | - |
| Fecha Aprobación | `prestamos` | `fecha_aprobacion` | Rango de fechas |
| Fecha Vencimiento | `cuotas` | `fecha_vencimiento` | Rango de fechas |
| Fecha Pago | `pagos` | `fecha_pago` | Rango de fechas |

---

## ⚠️ VALIDACIONES CRÍTICAS PARA DASHBOARD

### 1. Filtro de Clientes ACTIVOS

**REQUERIDO EN:**
- ✅ Todas las consultas de préstamos
- ✅ Todas las consultas de cuotas
- ✅ Todas las consultas de pagos

**IMPLEMENTACIÓN:**
```sql
INNER JOIN clientes cl ON cl.id = p.cliente_id AND cl.estado != 'INACTIVO'
```

### 2. Filtro de Préstamos APROBADOS

**REQUERIDO EN:**
- ✅ KPIs de cartera
- ✅ KPIs de morosidad
- ✅ Gráficos de tendencia

**IMPLEMENTACIÓN:**
```sql
WHERE p.estado = 'APROBADO'
```

### 3. Filtro de Pagos Activos

**REQUERIDO EN:**
- ✅ KPIs de pagos
- ✅ Cálculos de total pagado

**IMPLEMENTACIÓN:**
```sql
WHERE pa.activo = true
```

### 4. Normalización de Fechas

**REQUERIDO EN:**
- ✅ Comparaciones entre `fecha_aprobacion` (TIMESTAMP) y fechas (DATE)
- ✅ Comparaciones entre `fecha_pago` (TIMESTAMP) y `fecha_vencimiento` (DATE)

**IMPLEMENTACIÓN:**
```python
# En Python
DATE(fecha_aprobacion)  # Convertir TIMESTAMP a DATE
DATE(fecha_pago)  # Convertir TIMESTAMP a DATE
```

---

## 🎯 CONFIGURACIÓN REQUERIDA PARA DASHBOARD

### Módulos a Actualizar

1. **Dashboard Principal** (`dashboard.py`)
   - ✅ Agregar filtro `cliente.estado != 'INACTIVO'` en todas las queries
   - ✅ Validar normalización de fechas (TIMESTAMP vs DATE)
   - ✅ Usar `prestamos.fecha_aprobacion` para filtros de fecha
   - ✅ Usar `cuotas.fecha_vencimiento` para cálculos de morosidad
   - ✅ **NUEVO: Usar `cuotas.dias_morosidad` y `cuotas.monto_morosidad` para KPIs optimizados** (en lugar de calcular en tiempo real)
   - ✅ Usar `pagos.fecha_pago` para cálculos de pagos

2. **Módulo de Préstamos**
   - ✅ Ya implementado: filtro de clientes ACTIVOS
   - ✅ Ya implementado: asignación de `cliente_id`

3. **Módulo de Pagos**
   - ✅ Agregar filtro `cliente.estado != 'INACTIVO'` en queries
   - ✅ Validar `pago.activo = true`

4. **Módulo de Cobranzas**
   - ✅ Agregar filtro `cliente.estado != 'INACTIVO'`
   - ✅ Usar `cuotas.fecha_vencimiento` para morosidad
   - ✅ **NUEVO: Usar `cuotas.dias_morosidad` y `cuotas.monto_morosidad` para queries optimizadas**

5. **Módulo de Reportes**
   - ✅ Agregar filtro `cliente.estado != 'INACTIVO'`
   - ✅ Validar normalización de fechas

---

## 📝 NOTAS IMPORTANTES

### Campos Críticos para Dashboard

1. **`prestamos.fecha_aprobacion`** (TIMESTAMP)
   - Usar para: Filtros de fecha, KPIs de nuevos préstamos
   - Normalizar a DATE para comparaciones

2. **`prestamos.fecha_base_calculo`** (DATE)
   - Usar para: Generación de cuotas
   - Base para calcular `cuotas.fecha_vencimiento`

3. **`cuotas.fecha_vencimiento`** (DATE)
   - Usar para: KPIs de morosidad, cálculos de días de atraso
   - Comparar con `CURRENT_DATE`
   - ✅ **Base para calcular `dias_morosidad` automáticamente**

4. **`cuotas.dias_morosidad`** (INTEGER) - ✅ **NUEVO**
   - Usar para: KPIs de morosidad (optimizado)
   - Calculado automáticamente: `(fecha_pago - fecha_vencimiento).days` o `(CURRENT_DATE - fecha_vencimiento).days`
   - Se actualiza automáticamente al registrar pagos o actualizar estado

5. **`cuotas.monto_morosidad`** (NUMERIC(12,2)) - ✅ **NUEVO**
   - Usar para: KPIs de morosidad (optimizado)
   - Calculado automáticamente: `MAX(0, monto_cuota - total_pagado)`
   - Se actualiza automáticamente al registrar pagos o actualizar estado

6. **`pagos.fecha_pago`** (TIMESTAMP)
   - Usar para: KPIs de pagos, filtros de fecha
   - Normalizar a DATE para comparaciones

7. **`clientes.estado`** (VARCHAR)
   - Usar para: Filtro crítico - excluir INACTIVOS
   - Valores: `'ACTIVO'`, `'INACTIVO'`, `'FINALIZADO'`

---

## ✅ CHECKLIST DE CONFIGURACIÓN

### Backend

- [ ] Agregar filtro `cliente.estado != 'INACTIVO'` en todas las queries de dashboard
- [ ] Validar normalización de fechas (TIMESTAMP → DATE)
- [ ] Usar `prestamos.fecha_aprobacion` correctamente
- [ ] Usar `cuotas.fecha_vencimiento` para morosidad
- [x] ✅ **Usar `cuotas.dias_morosidad` y `cuotas.monto_morosidad` para KPIs optimizados** (IMPLEMENTADO en `/composicion-morosidad`)
- [ ] Actualizar otros endpoints del dashboard para usar columnas calculadas
- [ ] Usar `pagos.fecha_pago` correctamente
- [ ] Validar `pago.activo = true` en todas las queries

### Frontend

- [ ] Validar que solo se muestran clientes ACTIVOS en búsqueda
- [ ] Validar que solo se pueden crear préstamos para clientes ACTIVOS
- [ ] Mostrar mensajes de error apropiados

---

---

## ✅ NUEVAS COLUMNAS: Morosidad Calculada Automáticamente

### Fecha de Implementación
2025-11-06

### Columnas Agregadas en `cuotas`

1. **`dias_morosidad`** (INTEGER, default: 0, indexado)
   - **Descripción:** Días de morosidad calculados automáticamente
   - **Lógica:**
     - Si pagada tardíamente: `(fecha_pago - fecha_vencimiento).days`
     - Si no pagada: `(CURRENT_DATE - fecha_vencimiento).days`
     - Si pagada a tiempo: `0`
   - **Actualización:** Automática al registrar pagos o actualizar estado
   - **Uso:** KPIs de morosidad optimizados (mejor rendimiento)

2. **`monto_morosidad`** (NUMERIC(12,2), default: 0.00, indexado)
   - **Descripción:** Monto pendiente calculado automáticamente
   - **Fórmula:** `MAX(0, monto_cuota - total_pagado)`
   - **Actualización:** Automática al registrar pagos o actualizar estado
   - **Uso:** KPIs de morosidad optimizados (mejor rendimiento)

### Beneficios

- ✅ **Rendimiento mejorado:** Queries más rápidas usando valores pre-calculados
- ✅ **Índices optimizados:** Filtros más eficientes con índices parciales
- ✅ **Actualización automática:** Se actualiza al registrar pagos
- ✅ **Consistencia:** Valores siempre sincronizados

### Migración

**Script SQL:** `backend/scripts/migrations/AGREGAR_COLUMNAS_MOROSIDAD_CUOTAS.sql`

**Documentación completa:** `backend/docs/COLUMNAS_MOROSIDAD_AUTOMATICA.md`

---

**Estado:** ✅ **ESTRUCTURA CONFIRMADA Y ACTUALIZADA - LISTA PARA CONFIGURACIÓN**

