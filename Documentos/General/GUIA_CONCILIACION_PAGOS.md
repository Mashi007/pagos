# 📋 Guía: Manejo de Conciliación de Pagos

## 🔍 Situación Actual

### Problema Identificado
El sistema tiene **diferentes tablas de pagos** y **la conciliación está en diferentes tablas**:

1. **Tabla `pagos`**: 
   - Tabla principal para pagos registrados manualmente
   - **✅ SÍ tiene columna `conciliado`** (Boolean)
   - **✅ SÍ tiene columna `fecha_conciliacion`** (DateTime)
   - Se usa para operaciones de creación/actualización y conciliación

2. **Tabla `pagos_staging`**:
   - **Tabla donde están los datos reales** (carga masiva desde Excel)
   - **❌ NO tiene columna `conciliado`** (solo 5 columnas básicas)
   - Se usa para consultas principales (listar, stats, KPIs, dashboard)
   - Columnas actuales: `id_stg`, `cedula_cliente`, `fecha_pago`, `monto_pagado`, `numero_documento`
   - **⚠️ PROBLEMA: Los datos están aquí pero no se pueden marcar como conciliados**

### Código Python vs Base de Datos Real

**Modelo `Pago` (backend/app/models/pago.py)**:
- Define `conciliado = Column(Boolean, default=False)`
- Define `fecha_conciliacion = Column(DateTime, nullable=True)`
- **PERO**: La migración puede no haberse ejecutado o la columna puede no existir

**Modelo `PagoStaging` (backend/app/models/pago_staging.py)**:
- **NO tiene columna `conciliado`**
- Solo tiene 5 columnas básicas
- Se usa para la mayoría de consultas del sistema

## 🛠️ Solución: Scripts SQL Creados

### 1. **Verificar_Estado_Conciliacion_Pagos.sql**
**Propósito**: Diagnosticar qué tablas y columnas existen

**Qué hace**:
- Verifica si existen las tablas `pagos` y `pagos_staging`
- Verifica si existe la columna `conciliado` en cada tabla
- Muestra todas las columnas de ambas tablas
- Da recomendaciones basadas en los resultados

**Cuándo usar**: **PRIMERO** - Para entender el estado actual de la BD

### 2. **Agregar_Columna_Conciliado_Pagos_Staging.sql** ⭐ **IMPORTANTE**
**Propósito**: Agregar las columnas de conciliación a `pagos_staging` (donde están los datos)

**Qué hace**:
- Verifica si la columna `conciliado` existe en `pagos_staging`
- Si no existe, la agrega con `DEFAULT FALSE`
- Verifica si la columna `fecha_conciliacion` existe
- Si no existe, la agrega como `TEXT NULL` (por consistencia con `fecha_pago`)
- Muestra estadísticas después de agregar

**Cuándo usar**: **SEGUNDO** - Si los datos están en `pagos_staging` (caso actual)

### 3. **Marcar_Todos_Pagos_Staging_Como_Conciliados.sql** ⭐ **IMPORTANTE**
**Propósito**: Marcar todos los registros de `pagos_staging` como conciliados

**Qué hace**:
- Verifica que la columna `conciliado` existe (si no, lanza error)
- Muestra estadísticas antes de actualizar
- Actualiza **TODOS** los registros en `pagos_staging`:
  - `conciliado = TRUE`
  - `fecha_conciliacion = fecha_pago` (o fecha actual si no hay fecha_pago)
- Muestra estadísticas después de actualizar

**Cuándo usar**: **TERCERO** - Después de agregar columnas a `pagos_staging`

### 4. **Agregar_Columna_Conciliado_Si_No_Existe.sql** (Opcional)
**Propósito**: Agregar las columnas de conciliación a `pagos` si no existen

**Cuándo usar**: Solo si también necesitas marcar pagos en la tabla `pagos`

### 5. **Marcar_Todos_Pagos_Como_Conciliados.sql** (Opcional)
**Propósito**: Marcar todos los pagos en `pagos` como conciliados

**Cuándo usar**: Solo si también necesitas marcar pagos en la tabla `pagos`

## 📝 Proceso Recomendado (PARA PAGOS_STAGING - DONDE ESTÁN LOS DATOS)

### Paso 1: Diagnóstico
```sql
-- Ejecutar primero
\i scripts/sql/Verificar_Estado_Conciliacion_Pagos.sql
```

**Resultados esperados**:
- Debe mostrar que `pagos_staging` NO tiene columna `conciliado`
- Debe mostrar que `pagos` SÍ tiene columna `conciliado`

### Paso 2: Agregar Columnas a pagos_staging ⭐
```sql
-- Ejecutar esto porque los datos están en pagos_staging
\i scripts/sql/Agregar_Columna_Conciliado_Pagos_Staging.sql
```

**Verificar**:
- Debe mostrar "✅ Columna conciliado EXISTE en pagos_staging" al final
- Debe mostrar estadísticas iniciales (todos en FALSE)

### Paso 3: Marcar Todos como Conciliados en pagos_staging ⭐
```sql
-- Después de agregar columnas
\i scripts/sql/Marcar_Todos_Pagos_Staging_Como_Conciliados.sql
```

**Verificar**:
- Debe mostrar "100.00%" de registros conciliados al final
- Debe mostrar todos los registros con `conciliado = TRUE`

## 🔧 Manejo de Errores

### Error: "La columna conciliado NO EXISTE"
**Solución**: Ejecutar `Agregar_Columna_Conciliado_Si_No_Existe.sql` primero

### Error: "La tabla pagos NO EXISTE"
**Solución**: Verificar la estructura de la BD. Puede que el sistema use solo `pagos_staging`

### Error: "No se puede actualizar porque la tabla está vacía"
**Solución**: Verificar que hay registros en la tabla `pagos` con `activo = TRUE`

## 📊 Notas Importantes

1. **Tabla `pagos_staging` NO tiene conciliación**:
   - Esta tabla es para datos temporales
   - La conciliación solo se aplica a `pagos`
   - Los pagos en `pagos_staging` deben migrarse a `pagos` primero

2. **Endpoints de Conciliación**:
   - `pagos_conciliacion.py` usa tabla `pagos` (no `pagos_staging`)
   - `conciliacion_bancaria.py` usa tabla `pagos` (no `pagos_staging`)
   - Si la columna no existe, estos endpoints fallarán

3. **Migraciones Alembic**:
   - La migración `013_create_pagos_table.py` debería crear la columna
   - Verificar si las migraciones se ejecutaron: `alembic current`
   - Si no, ejecutar: `alembic upgrade head`

## ✅ Checklist Final

- [ ] Verificar estado de tablas y columnas
- [ ] Agregar columnas si faltan
- [ ] Marcar todos los pagos como conciliados
- [ ] Verificar que los endpoints de conciliación funcionan
- [ ] Verificar que el dashboard muestra datos correctos

