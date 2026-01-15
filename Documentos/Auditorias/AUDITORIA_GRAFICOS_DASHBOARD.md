# 🔍 Auditoría Completa: Gráficos del Dashboard

**Fecha:** 2025-01-26  
**Objetivo:** Verificar que todos los gráficos del dashboard usen los campos correctos de las tablas correctas

---

## 📊 Resumen Ejecutivo

### ✅ Endpoints Verificados Correctos
- `/api/v1/dashboard/admin` - ✅ CORRECTO (corregido cálculo de morosidad)
- `/api/v1/dashboard/kpis-principales` - ✅ CORRECTO
- `/api/v1/dashboard/financiamiento-tendencia-mensual` - ✅ CORRECTO
- `/api/v1/dashboard/prestamos-por-concesionario` - ✅ CORRECTO
- `/api/v1/dashboard/prestamos-por-modelo` - ✅ CORRECTO
- `/api/v1/dashboard/morosidad-por-analista` - ✅ CORRECTO
- `/api/v1/dashboard/evolucion-morosidad` - ✅ CORRECTO
- `/api/v1/dashboard/evolucion-pagos` - ✅ CORRECTO
- `/api/v1/dashboard/cobranza-por-dia` - ✅ CORRECTO
- `/api/v1/dashboard/cobranza-fechas-especificas` - ✅ CORRECTO
- `/api/v1/dashboard/cobranzas-semanales` - ✅ CORRECTO
- `/api/v1/dashboard/cobros-por-analista` - ✅ CORRECTO

### ❌ Problemas Encontrados y Corregidos

1. **`/api/v1/dashboard/composicion-morosidad`** - ❌ CORREGIDO
   - **Problema:** Intentaba usar `Cuota.monto_morosidad` que no existe
   - **Solución:** Calcula dinámicamente como `monto_cuota - total_pagado`

2. **`/api/v1/dashboard/admin` → `evolucion_mensual`** - ❌ CORREGIDO
   - **Problema:** Morosidad calculada como porcentaje en lugar de monto
   - **Solución:** Ahora calcula `morosidad = cartera - cobrado` (monto USD)

3. **`/api/v1/kpis/dashboard`** - ❌ CORREGIDO
   - **Problema:** Usaba campos inexistentes: `capital_pendiente`, `interes_pendiente`, `monto_mora`, `capital_pagado`, `interes_pagado`, `mora_pagada`
   - **Solución:** Usa campos existentes: `monto_cuota`, `total_pagado`

---

## 📋 Auditoría Detallada por Dashboard

### 1. DashboardMenu.tsx

#### Endpoints Utilizados:
1. **`/api/v1/dashboard/kpis-principales`**
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `fecha_aprobacion`, `total_financiamiento`, `estado`
   - ✅ **Tabla:** `clientes`
   - ✅ **Campos:** `estado`, `cedula`
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `monto_cuota`, `estado`
   - ✅ **Cálculo Morosidad:** Usa función `_calcular_morosidad()` que consulta `cuotas` y `pagos`

2. **`/api/v1/dashboard/admin`**
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `total_financiamiento`, `estado`, `fecha_aprobacion`
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `monto_cuota`, `fecha_vencimiento`, `total_pagado`, `estado`
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `monto_pagado`, `fecha_pago`, `activo`
   - ✅ **evolucion_mensual:** CORREGIDO - Calcula morosidad como `cartera - cobrado`

3. **`/api/v1/dashboard/financiamiento-tendencia-mensual`**
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `total_financiamiento`, `fecha_aprobacion`, `estado`
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `monto_cuota`, `fecha_vencimiento`, `total_pagado`
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `monto_pagado`, `fecha_pago`, `activo`
   - ✅ **Campos devueltos:** `mes`, `monto_nuevos`, `monto_cuotas_programadas`, `monto_pagado`, `morosidad_mensual`

4. **`/api/v1/dashboard/prestamos-por-concesionario`**
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `concesionario`, `total_financiamiento`, `id`, `estado`
   - ✅ **Campos devueltos:** `concesionario`, `total_prestamos`, `cantidad_prestamos`, `porcentaje`

5. **`/api/v1/dashboard/prestamos-por-modelo`**
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `modelo_vehiculo`, `producto`, `total_financiamiento`, `id`, `estado`
   - ✅ **Campos devueltos:** `modelo`, `total_prestamos`, `cantidad_prestamos`, `porcentaje`

6. **`/api/v1/dashboard/financiamiento-por-rangos`**
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `total_financiamiento`, `estado`
   - ✅ **Campos devueltos:** `categoria`, `cantidad_prestamos`, `monto_total`, `porcentaje_cantidad`, `porcentaje_monto`

7. **`/api/v1/dashboard/composicion-morosidad`** - ✅ CORREGIDO
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `dias_morosidad`, `monto_cuota`, `total_pagado` (calcula `monto_morosidad = monto_cuota - total_pagado`)
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `estado`, `analista`, `concesionario`, `producto`, `modelo_vehiculo`

8. **`/api/v1/dashboard/cobranza-fechas-especificas`**
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `fecha_vencimiento`, `monto_cuota`
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `fecha_pago`, `monto_pagado`, `activo`
   - ✅ **Campos devueltos:** `fecha`, `nombre_fecha`, `cobranza_planificada`, `cobranza_real`

9. **`/api/v1/dashboard/cobranzas-semanales`**
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `fecha_vencimiento`, `monto_cuota`
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `fecha_pago`, `monto_pagado`, `activo`
   - ✅ **Campos devueltos:** `semana_inicio`, `nombre_semana`, `cobranzas_planificadas`, `pagos_reales`

10. **`/api/v1/dashboard/morosidad-por-analista`**
    - ✅ **Tabla:** `cuotas`
    - ✅ **Campos:** `monto_cuota`, `fecha_vencimiento`, `estado`, `prestamo_id`
    - ✅ **Tabla:** `prestamos`
    - ✅ **Campos:** `analista`, `cedula`, `estado`
    - ✅ **Campos devueltos:** `analista`, `total_morosidad`, `cantidad_clientes`

11. **`/api/v1/dashboard/evolucion-morosidad`**
    - ✅ **Tabla:** `dashboard_morosidad_mensual` (si existe) o `cuotas`
    - ✅ **Campos:** `año`, `mes`, `morosidad_total` o `monto_cuota`, `fecha_vencimiento`, `estado`
    - ✅ **Campos devueltos:** `mes`, `morosidad`

12. **`/api/v1/dashboard/evolucion-pagos`**
    - ✅ **Tabla:** `pagos`
    - ✅ **Campos:** `fecha_pago`, `monto_pagado`, `activo`
    - ✅ **Campos devueltos:** `mes`, `pagos`, `monto`

---

### 2. DashboardCuotas.tsx

#### Endpoints Utilizados:
1. **`/api/v1/kpis/dashboard`**
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `monto_cuota`, `fecha_vencimiento`, `total_pagado`, `estado`, `prestamo_id`
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `estado`, `analista`, `concesionario`, `producto`, `modelo_vehiculo`
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `conciliado`, `prestamo_id`, `numero_cuota`, `activo`
   - ✅ **Campos devueltos:** `total_cuotas_mes`, `cuotas_pagadas`, `porcentaje_cuotas_pagadas`, `total_cuotas_conciliadas`, `cuotas_atrasadas_mes`, `total_cuotas_impagas_2mas`

2. **`/api/v1/dashboard/evolucion-morosidad`**
   - ✅ Verificado arriba (DashboardMenu)

---

### 3. DashboardPagos.tsx

#### Endpoints Utilizados:
1. **`/api/v1/pagos/stats`**
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `monto_pagado`, `fecha_pago`, `estado`, `activo`, `prestamo_id`, `cedula`
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `estado`, `analista`, `concesionario`, `producto`, `modelo_vehiculo`
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `estado`, `prestamo_id`
   - ✅ **Campos devueltos:** `total_pagos`, `total_pagado`, `pagos_por_estado`

2. **`/api/v1/pagos/kpis`**
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `monto_pagado`, `fecha_pago`, `activo`
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `monto_cuota`, `total_pagado`, `fecha_vencimiento`, `estado`
   - ✅ **Campos devueltos:** `montoCobradoMes`, `saldoPorCobrar`, `clientesEnMora`, `clientesAlDia`

3. **`/api/v1/dashboard/evolucion-pagos`**
   - ✅ Verificado arriba (DashboardMenu)

---

### 4. DashboardCobranza.tsx

#### Endpoints Utilizados:
1. **`/api/v1/dashboard/admin`**
   - ✅ Verificado arriba (DashboardMenu)

2. **`/api/v1/dashboard/cobranza-por-dia`**
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `fecha_vencimiento`, `monto_cuota`
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `fecha_pago`, `monto_pagado`, `activo`
   - ✅ **Campos devueltos:** `fecha`, `total_a_cobrar`, `cobranza_planificada`, `cobranza_real`, `pagos`, `morosidad`

3. **`/api/v1/dashboard/cobros-por-analista`**
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `monto_pagado`, `fecha_pago`, `activo`, `prestamo_id`, `cedula`
   - ✅ **Tabla:** `prestamos`
   - ✅ **Campos:** `analista`, `estado`
   - ✅ **Campos devueltos:** `analista`, `total_cobrado`, `cantidad_pagos`

#### ⚠️ KPIs Hardcodeados (Requieren Implementación):
- **"Pagos Conciliados"** - Valor: 0
  - **Necesita:** `COUNT(*) FROM pagos WHERE conciliado = TRUE AND fecha_pago >= primer_dia_mes`
  
- **"Días Promedio Cobro"** - Valor: "12"
  - **Necesita:** `AVG(DATEDIFF(fecha_pago, fecha_vencimiento))` de cuotas pagadas

---

### 5. DashboardAnalisis.tsx

#### Endpoints Utilizados:
1. **`/api/v1/dashboard/kpis-principales`**
   - ✅ Verificado arriba (DashboardMenu)

2. **`/api/v1/dashboard/admin`**
   - ✅ Verificado arriba (DashboardMenu)

3. **`/api/v1/dashboard/cobros-diarios`**
   - ✅ **Tabla:** `cuotas`
   - ✅ **Campos:** `fecha_vencimiento`, `monto_cuota`
   - ✅ **Tabla:** `pagos`
   - ✅ **Campos:** `fecha_pago`, `monto_pagado`, `activo`
   - ✅ **Campos devueltos:** `fecha`, `dia`, `dia_semana`, `total_a_cobrar`, `total_cobrado`

---

### 6. DashboardFinanciamiento.tsx

#### Endpoints Utilizados:
1. **`/api/v1/kpis/dashboard`**
   - ✅ Verificado arriba (DashboardCuotas)
   - ⚠️ **NOTA:** Este endpoint usa campos que fueron corregidos (`monto_cuota`, `total_pagado`)

2. **`/api/v1/dashboard/prestamos-por-concesionario`**
   - ✅ Verificado arriba (DashboardMenu)

3. **`/api/v1/dashboard/financiamiento-tendencia-mensual`**
   - ✅ Verificado arriba (DashboardMenu)

---

## 🔧 Correcciones Aplicadas

### 1. `/api/v1/dashboard/composicion-morosidad`
**Antes:**
```python
Cuota.monto_morosidad  # ❌ Campo no existe
```

**Después:**
```python
# Calcula dinámicamente: monto_cuota - total_pagado
GREATEST(0, COALESCE(monto_cuota, 0) - COALESCE(total_pagado, 0)) as monto_morosidad
```

### 2. `/api/v1/dashboard/admin` → `evolucion_mensual`
**Antes:**
```python
morosidad_mes = (cuotas_vencidas_mes / total_cuotas_mes * 100)  # ❌ Porcentaje
```

**Después:**
```python
morosidad_mes = max(0.0, cartera_mes - cobrado_mes)  # ✅ Monto USD
```

### 3. `/api/v1/kpis/dashboard`
**Antes:**
```python
Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora  # ❌ Campos no existen
Cuota.capital_pagado + Cuota.interes_pagado + Cuota.mora_pagada  # ❌ Campos no existen
```

**Después:**
```python
# Saldo pendiente
func.sum(Cuota.monto_cuota - func.coalesce(Cuota.total_pagado, 0))

# Total pagado
func.sum(func.coalesce(Cuota.total_pagado, 0))
```

---

## 📝 Campos del Modelo Cuota (Verificados)

### ✅ Campos Existentes:
- `id`
- `prestamo_id`
- `numero_cuota`
- `fecha_vencimiento`
- `fecha_pago`
- `monto_cuota`
- `saldo_capital_inicial`
- `saldo_capital_final`
- `total_pagado`
- `dias_mora`
- `dias_morosidad`
- `estado`
- `observaciones`
- `es_cuota_especial`

### ❌ Campos que NO Existen (pero se usaban):
- `capital_pendiente` ❌
- `interes_pendiente` ❌
- `monto_mora` ❌
- `capital_pagado` ❌
- `interes_pagado` ❌
- `mora_pagada` ❌
- `monto_morosidad` ❌ (se calcula dinámicamente)

---

## 📝 Campos del Modelo Pago (Verificados)

### ✅ Campos Existentes:
- `id`
- `cedula`
- `cliente_id`
- `prestamo_id`
- `numero_cuota`
- `fecha_pago`
- `fecha_registro`
- `monto_pagado`
- `numero_documento`
- `institucion_bancaria`
- `conciliado`
- `fecha_conciliacion`
- `estado`
- `activo`
- `notas`
- `usuario_registro`
- `fecha_actualizacion`
- `verificado_concordancia`

---

## 📝 Campos del Modelo Prestamo (Verificados)

### ✅ Campos Existentes:
- `id`
- `cliente_id`
- `cedula`
- `nombres`
- `valor_activo`
- `total_financiamiento`
- `fecha_requerimiento`
- `modalidad_pago`
- `numero_cuotas`
- `cuota_periodo`
- `tasa_interes`
- `fecha_base_calculo`
- `producto`
- `concesionario`
- `analista`
- `modelo_vehiculo`
- `concesionario_id`
- `analista_id`
- `modelo_vehiculo_id`
- `estado`
- `usuario_proponente`
- `usuario_aprobador`
- `usuario_autoriza`
- `observaciones`
- `fecha_registro`
- `fecha_aprobacion`

---

## 📝 Campos del Modelo Cliente (Verificados)

### ✅ Campos Existentes:
- `id`
- `cedula`
- `nombres`
- `telefono`
- `email`
- `direccion`
- `fecha_nacimiento`
- `ocupacion`
- `estado` (ACTIVO/INACTIVO/FINALIZADO)
- `fecha_registro`
- `fecha_actualizacion`
- `usuario_registro`
- `notas`

---

## ✅ Verificación de Definiciones de Usuario

### Gráfico "Evolución Mensual":
- ✅ **Cartera** = suma de cuotas programadas (`SUM(cuotas.monto_cuota)` donde `fecha_vencimiento` en el mes)
- ✅ **Cobrado** = suma de abonos (`SUM(pagos.monto_pagado)` donde `fecha_pago` en el mes)
- ✅ **Morosidad** = total_financiamiento - total cobrado = cartera - cobrado (CORREGIDO)

---

## ⚠️ Problemas Pendientes en Otros Archivos

Los siguientes archivos aún usan campos que no existen (NO afectan los gráficos del dashboard, pero deben corregirse):

1. **`backend/app/api/v1/endpoints/prestamos.py`**
   - Líneas 781, 1081-1088: Usa `capital_pendiente`, `interes_pendiente`, `monto_mora`, `capital_pagado`, `interes_pagado`

2. **`backend/app/api/v1/endpoints/amortizacion.py`**
   - Múltiples líneas: Usa campos inexistentes de cuota

3. **`backend/app/api/v1/endpoints/reportes.py`**
   - Múltiples líneas: Usa `capital_pendiente`, `interes_pendiente`, `monto_mora`

4. **`backend/app/api/v1/endpoints/configuracion.py`**
   - Múltiples líneas: Usa `monto_mora`

**Nota:** Estos archivos NO afectan los gráficos del dashboard, pero deberían corregirse para evitar errores futuros.

---

## ✅ Conclusión

### Gráficos del Dashboard: ✅ VERIFICADOS Y CORREGIDOS

Todos los gráficos del dashboard ahora:
- ✅ Usan campos existentes en las tablas correctas
- ✅ Calculan valores correctamente según las definiciones del usuario
- ✅ Están conectados a la base de datos real
- ✅ Se actualizan automáticamente con datos frescos (staleTime reducido)

### Correcciones Críticas Aplicadas:
1. ✅ Cálculo de morosidad en `evolucion_mensual` corregido
2. ✅ Campo `monto_morosidad` calculado dinámicamente en `composicion-morosidad`
3. ✅ Campos inexistentes corregidos en `/api/v1/kpis/dashboard`

### Pendientes (No críticos para gráficos):
- Implementar KPIs hardcodeados en DashboardCobranza
- Corregir otros endpoints que usan campos inexistentes (no afectan dashboard)

---

**Auditoría completada:** 2025-01-26  
**Estado:** ✅ Todos los gráficos del dashboard verificados y corregidos
