# 🔍 REVISIÓN COMPLETA: Modelos de Código vs Estructura Real de BD

**Fecha de Revisión:** 2025-10-31
**Objetivo:** Verificar que todos los campos usados en el código existan realmente en los modelos y en la BD

---

## ✅ CORRECCIONES YA APLICADAS

### 1. **`Prestamo.activo`** ❌ NO EXISTE → ✅ CORREGIDO

**Ubicación del error:**
- `backend/app/api/v1/endpoints/dashboard.py` (líneas 191, 496, 502, 511, 612, 670)
- `backend/app/api/v1/endpoints/kpis.py` (líneas 54, 63)
- `backend/app/utils/filtros_dashboard.py` (línea 36)

**Campo real:** `Prestamo.estado` (String) con valores: "DRAFT", "EN_REVISION", "APROBADO", "RECHAZADO"

**Solución aplicada:** Reemplazado `Prestamo.activo.is_(True)` por `Prestamo.estado == "APROBADO"`

**Estado:** ✅ CORREGIDO

---

## ❌ ERRORES ENCONTRADOS Y CORREGIDOS

### 1. **`Cliente.analista_id`** ❌ NO EXISTE → ✅ CORREGIDO

**Ubicación del error:**
- `backend/app/api/v1/endpoints/kpis.py` (línea 112)

**Problema:**
- El modelo `Cliente` NO tiene campo `analista_id`
- La relación entre `Cliente` y `Analista` NO existe directamente

**Solución aplicada:**
- Usar `Prestamo.analista` (String) mediante JOIN con `Prestamo`
- Agregado filtro para excluir valores NULL/vacíos

**Código corregido:**
```python
analistas_clientes = (
    db.query(
        Prestamo.analista.label("nombre_analista"),
        func.count(func.distinct(Cliente.id)).label("total_clientes")
    )
    .join(Cliente, Prestamo.cedula == Cliente.cedula)
    .filter(Prestamo.analista.isnot(None), Prestamo.analista != "")
    .group_by(Prestamo.analista)
    .order_by(func.count(func.distinct(Cliente.id)).desc())
    .limit(10)
    .all()
)
```

**Estado:** ✅ CORREGIDO

---

### 2. **`Cliente.total_financiamiento`** ❌ NO EXISTE → ✅ CORREGIDO

**Ubicación del error:**
- `backend/app/api/v1/endpoints/kpis.py` (línea 136)

**Problema:**
- El modelo `Cliente` NO tiene campo `total_financiamiento`
- Este campo existe en `Prestamo.total_financiamiento`

**Solución aplicada:**
- Usar JOIN con `Prestamo` y sumar `Prestamo.total_financiamiento`
- Filtrar solo préstamos aprobados

**Código corregido:**
```python
cartera_estado = (
    db.query(Cliente.estado, func.sum(Prestamo.total_financiamiento).label("total"))
    .join(Prestamo, Cliente.cedula == Prestamo.cedula)
    .filter(Prestamo.estado == "APROBADO")
    .group_by(Cliente.estado)
    .all()
)
```

**Estado:** ✅ CORREGIDO

---

### 3. **`Prestamo.dias_mora`** ❌ NO EXISTE → ✅ CORREGIDO

**Ubicación del error:**
- `backend/app/api/v1/endpoints/notificaciones.py` (líneas 136, 139)
- `backend/app/api/v1/endpoints/reportes.py` (líneas 168, 169, 176, 177)

**Problema:**
- El modelo `Prestamo` NO tiene campo `dias_mora`
- Este campo existe en `Cuota.dias_mora` (tabla `cuotas`)

**Solución aplicada:**
- Agregado import de `Cuota` en ambos archivos
- Cambiado JOIN para usar `Cuota.dias_mora` y `Cuota.monto_mora`
- Agregado `distinct()` para evitar duplicados en notificaciones

**Código corregido en notificaciones.py:**
```python
from app.models.amortizacion import Cuota

query = (
    db.query(Cliente)
    .join(Prestamo, Cliente.id == Prestamo.cliente_id)
    .join(Cuota, Prestamo.id == Cuota.prestamo_id)
)

if request.tipo_cliente == "MOROSO":
    query = query.filter(Cuota.dias_mora > 0)

if request.dias_mora_min:
    query = query.filter(Cuota.dias_mora >= request.dias_mora_min)

# Obtener clientes únicos (puede haber múltiples cuotas por cliente)
clientes = query.distinct(Cliente.id).all()
```

**Código corregido en reportes.py:**
```python
from app.models.amortizacion import Cuota

cantidad = (
    db.query(func.count(func.distinct(Prestamo.id)))
    .join(Cuota, Prestamo.id == Cuota.prestamo_id)
    .filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA,
        Cuota.dias_mora >= rango["min"],
        Cuota.dias_mora <= rango["max"],
    )
    .scalar()
) or 0

monto_mora = (
    db.query(func.sum(Cuota.monto_mora))
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .filter(
        Prestamo.estado == EstadoPrestamo.EN_MORA,
        Cuota.dias_mora >= rango["min"],
        Cuota.dias_mora <= rango["max"],
    )
    .scalar()
) or Decimal("0")
```

**Estado:** ✅ CORREGIDO

---

## ✅ MODELOS CORRECTOS VERIFICADOS

### **`Cliente`** (Modelo correcto)
- ✅ `id` (Integer, PK)
- ✅ `cedula` (String(20), NOT NULL, index)
- ✅ `nombres` (String(100), NOT NULL)
- ✅ `telefono` (String(15), NOT NULL, index)
- ✅ `email` (String(100), NOT NULL, index)
- ✅ `direccion` (Text, NOT NULL)
- ✅ `fecha_nacimiento` (Date, NOT NULL)
- ✅ `ocupacion` (String(100), NOT NULL)
- ✅ `estado` (String(20), NOT NULL, default="ACTIVO")
- ✅ `activo` (Boolean, NOT NULL, default=True)
- ✅ `fecha_registro` (TIMESTAMP, NOT NULL)
- ✅ `fecha_actualizacion` (TIMESTAMP, NOT NULL)
- ✅ `usuario_registro` (String(100), NOT NULL)
- ✅ `notas` (Text, NOT NULL, default="NA")

**Campos que NO existen:**
- ❌ `analista_id` (Integer) - NO EXISTE
- ❌ `total_financiamiento` (Numeric) - NO EXISTE

---

### **`Prestamo`** (Modelo correcto)
- ✅ `id` (Integer, PK)
- ✅ `cliente_id` (Integer, NOT NULL, index)
- ✅ `cedula` (String(20), NOT NULL, index)
- ✅ `nombres` (String(100), NOT NULL)
- ✅ `total_financiamiento` (Numeric(15, 2), NOT NULL)
- ✅ `fecha_requerimiento` (Date, NOT NULL)
- ✅ `modalidad_pago` (String(20), NOT NULL)
- ✅ `numero_cuotas` (Integer, NOT NULL)
- ✅ `cuota_periodo` (Numeric(15, 2), NOT NULL)
- ✅ `tasa_interes` (Numeric(5, 2), NOT NULL, default=0.00)
- ✅ `fecha_base_calculo` (Date, nullable=True)
- ✅ `producto` (String(100), NOT NULL)
- ✅ `producto_financiero` (String(100), NOT NULL)
- ✅ `concesionario` (String(100), nullable=True)
- ✅ `analista` (String(100), nullable=True)
- ✅ `modelo_vehiculo` (String(100), nullable=True)
- ✅ `estado` (String(20), NOT NULL, default="DRAFT")
- ✅ `usuario_proponente` (String(100), NOT NULL)
- ✅ `usuario_aprobador` (String(100), nullable=True)
- ✅ `usuario_autoriza` (String(100), nullable=True)
- ✅ `observaciones` (Text, nullable=True)
- ✅ `fecha_registro` (TIMESTAMP, NOT NULL)
- ✅ `fecha_aprobacion` (TIMESTAMP, nullable=True)
- ✅ `informacion_desplegable` (Boolean, NOT NULL, default=False)
- ✅ `fecha_actualizacion` (TIMESTAMP, NOT NULL)

**Campos que NO existen:**
- ❌ `activo` (Boolean) - NO EXISTE (usar `estado == "APROBADO"`)
- ❌ `dias_mora` (Integer) - NO EXISTE (está en `Cuota.dias_mora`)

---

### **`Cuota`** (Modelo correcto)
- ✅ `id` (Integer, PK)
- ✅ `prestamo_id` (Integer, FK a prestamos.id, NOT NULL, index)
- ✅ `numero_cuota` (Integer, NOT NULL)
- ✅ `fecha_vencimiento` (Date, NOT NULL)
- ✅ `fecha_pago` (Date, nullable=True)
- ✅ `monto_cuota` (Numeric(12, 2), NOT NULL)
- ✅ `monto_capital` (Numeric(12, 2), NOT NULL)
- ✅ `monto_interes` (Numeric(12, 2), NOT NULL)
- ✅ `saldo_capital_inicial` (Numeric(12, 2), NOT NULL)
- ✅ `saldo_capital_final` (Numeric(12, 2), NOT NULL)
- ✅ `capital_pagado` (Numeric(12, 2), default=0.00)
- ✅ `interes_pagado` (Numeric(12, 2), default=0.00)
- ✅ `mora_pagada` (Numeric(12, 2), default=0.00)
- ✅ `total_pagado` (Numeric(12, 2), default=0.00)
- ✅ `capital_pendiente` (Numeric(12, 2), NOT NULL)
- ✅ `interes_pendiente` (Numeric(12, 2), NOT NULL)
- ✅ `dias_mora` (Integer, default=0) ✅ **AQUÍ ESTÁ**
- ✅ `monto_mora` (Numeric(12, 2), default=0.00)
- ✅ `tasa_mora` (Numeric(5, 2), default=0.00)
- ✅ `estado` (String(20), NOT NULL, default="PENDIENTE")
- ✅ `observaciones` (String(500), nullable=True)
- ✅ `es_cuota_especial` (Boolean, default=False)

---

### **`Pago`** (Modelo correcto)
- ✅ `id` (Integer, PK)
- ✅ `cedula_cliente` (String(20), NOT NULL, index)
- ✅ `prestamo_id` (Integer, nullable=True, index)
- ✅ `numero_cuota` (Integer, nullable=True)
- ✅ `fecha_pago` (DateTime, NOT NULL)
- ✅ `fecha_registro` (DateTime, NOT NULL)
- ✅ `monto_pagado` (Numeric(12, 2), NOT NULL)
- ✅ `numero_documento` (String(100), NOT NULL, index) ⚠️ **ALTERADO A VARCHAR(255)**
- ✅ `institucion_bancaria` (String(100), nullable=True)
- ✅ `documento_nombre` (String(255), nullable=True)
- ✅ `documento_tipo` (String(10), nullable=True)
- ✅ `documento_tamaño` (Integer, nullable=True)
- ✅ `documento_ruta` (String(500), nullable=True)
- ✅ `conciliado` (Boolean, NOT NULL, default=False)
- ✅ `fecha_conciliacion` (DateTime, nullable=True)
- ✅ `estado` (String(20), NOT NULL, default="PAGADO")
- ✅ `activo` (Boolean, NOT NULL, default=True)
- ✅ `notas` (Text, nullable=True)
- ✅ `usuario_registro` (String(100), NOT NULL)
- ✅ `fecha_actualizacion` (DateTime, NOT NULL)

---

## 📋 RESUMEN DE ACCIONES REQUERIDAS

### **Archivos corregidos:**
1. ✅ `backend/app/api/v1/endpoints/dashboard.py` - CORREGIDO (`Prestamo.activo`)
2. ✅ `backend/app/api/v1/endpoints/kpis.py` - CORREGIDO (`Prestamo.activo`, `Cliente.analista_id`, `Cliente.total_financiamiento`)
3. ✅ `backend/app/api/v1/endpoints/notificaciones.py` - CORREGIDO (`Prestamo.dias_mora`)
4. ✅ `backend/app/api/v1/endpoints/reportes.py` - CORREGIDO (`Prestamo.dias_mora`, `Prestamo.monto_mora`)

### **Cambios aplicados:**
1. ✅ Reemplazar `Prestamo.activo` → `Prestamo.estado == "APROBADO"` - HECHO
2. ✅ Eliminar `Cliente.analista_id` → JOIN con `Prestamo.analista` - HECHO
3. ✅ Eliminar `Cliente.total_financiamiento` → JOIN con `Prestamo.total_financiamiento` - HECHO
4. ✅ Cambiar `Prestamo.dias_mora` → JOIN con `Cuota.dias_mora` - HECHO
5. ✅ Cambiar `Prestamo.monto_mora` → `Cuota.monto_mora` - HECHO

---

## 🔍 MÉTODO DE VERIFICACIÓN

Para verificar que todos los campos existen:

1. **Revisar modelos en `backend/app/models/`:**
   ```bash
   grep -r "Column" backend/app/models/*.py | grep "="
   ```

2. **Revisar uso de campos en endpoints:**
   ```bash
   grep -r "\.activo\|\.analista_id\|\.total_financiamiento\|\.dias_mora" backend/app/api/
   ```

3. **Verificar estructura real de BD en PostgreSQL:**
   ```sql
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_name = 'clientes'
   ORDER BY ordinal_position;
   ```

---

## 📝 NOTAS FINALES

- **Estado general:** ✅ TODOS LOS ERRORES CORREGIDOS
- **Impacto:** Errores corregidos en endpoints de KPIs, notificaciones y reportes
- **Prioridad:** RESUELTO - Los `AttributeError` en producción han sido eliminados
- **Fecha de corrección:** 2025-10-31

---

## ✅ VERIFICACIÓN FINAL

Todos los campos usados en el código ahora coinciden con los modelos y la estructura real de la BD:

- ✅ `Prestamo.activo` → `Prestamo.estado == "APROBADO"`
- ✅ `Cliente.analista_id` → `Prestamo.analista` (via JOIN)
- ✅ `Cliente.total_financiamiento` → `Prestamo.total_financiamiento` (via JOIN)
- ✅ `Prestamo.dias_mora` → `Cuota.dias_mora` (via JOIN)
- ✅ `Prestamo.monto_mora` → `Cuota.monto_mora` (via JOIN)

