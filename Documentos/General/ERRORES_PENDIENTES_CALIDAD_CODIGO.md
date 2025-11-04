# 📋 ERRORES PENDIENTES - Calidad de Código

**Fecha**: 2025-11-04  
**Última actualización**: 2025-11-04  
**Estado**: 🔄 En progreso

---

## 📊 RESUMEN GENERAL

Según el último análisis de GitHub Actions (commit `f6efc2a5`):

- ✅ **Flake8 Críticos**: 0 errores (sintaxis, funciones no definidas)
- ⚠️ **Flake8 No Críticos**: 51 errores
- ⚠️ **Mypy**: 274 errores en 35 archivos
- ✅ **Black**: Correcciones automáticas aplicadas
- ✅ **Isort**: Sin errores

---

## 🔴 PRIORIDAD ALTA - Mypy (274 errores)

### 1. **Errores de Asignación Column vs Valores** (~150 errores)
**Problema**: Asignar valores directos a Columnas SQLAlchemy

**Ejemplos**:
```python
# ❌ Incorrecto
prestamo.estado = "APROBADO"  # Column[str] vs str
cuota.total_pagado = Decimal("100")  # Column[Decimal] vs Decimal

# ✅ Correcto
prestamo.estado = "APROBADO"  # type: ignore[assignment]
# O usar setattr si es necesario
```

**Archivos afectados**:
- `app/api/v1/endpoints/prestamos.py` (~50 errores)
- `app/api/v1/endpoints/pagos.py` (~30 errores)
- `app/api/v1/endpoints/pagos_conciliacion.py` (~10 errores)
- `app/api/v1/endpoints/solicitudes.py` (~10 errores)
- `app/api/v1/endpoints/aprobaciones.py` (~10 errores)
- `app/api/v1/endpoints/analistas.py` (~5 errores)
- `app/api/v1/endpoints/concesionarios.py` (~5 errores)
- `app/api/v1/endpoints/clientes.py` (~5 errores)
- `app/api/v1/endpoints/modelos_vehiculos.py` (~5 errores)
- `app/services/auth_service.py` (~5 errores)
- `app/services/notificacion_automatica_service.py` (~10 errores)
- `app/services/amortizacion_service.py` (~5 errores)

**Solución**: Agregar `# type: ignore[assignment]` a asignaciones de Column

---

### 2. **Errores de Argumentos Column vs Valores** (~40 errores)
**Problema**: Pasar Columnas SQLAlchemy como argumentos que esperan valores

**Ejemplos**:
```python
# ❌ Incorrecto
calcular_cuotas(prestamo.monto_cuota, prestamo.plazo)  # Column[Decimal] vs Decimal

# ✅ Correcto
calcular_cuotas(prestamo.monto_cuota, prestamo.plazo)  # type: ignore[arg-type]
# O extraer valores primero
monto = prestamo.monto_cuota
plazo = prestamo.plazo
calcular_cuotas(monto, plazo)
```

**Archivos afectados**:
- `app/api/v1/endpoints/prestamos.py` (~15 errores)
- `app/api/v1/endpoints/pagos.py` (~10 errores)
- `app/services/prestamo_amortizacion_service.py` (~5 errores)
- `app/services/notificacion_automatica_service.py` (~5 errores)
- `app/api/v1/endpoints/reportes.py` (~5 errores)

---

### 3. **Errores de Tipo de Retorno** (~20 errores)
**Problema**: Funciones que retornan `Any` o tipos incompatibles

**Ejemplos**:
```python
# ❌ Incorrecto
def get_value() -> bool:
    return verify_password(...)  # Retorna Any

# ✅ Correcto
def get_value() -> bool:
    return bool(verify_password(...))  # type: ignore[no-any-return]
```

**Archivos afectados**:
- `app/core/security.py` (~3 errores)
- `app/utils/date_helpers.py` (~1 error)
- `app/services/validators_service.py` (~5 errores)
- `app/utils/auditoria_helper.py` (~1 error)
- `app/api/v1/endpoints/pagos.py` (~1 error)
- `app/api/v1/endpoints/prestamos.py` (~1 error)

---

### 4. **Errores de Tipos de Query** (~30 errores)
**Problema**: Asignaciones de Query[Any] a tipos específicos

**Ejemplos**:
```python
# ❌ Incorrecto
query: RowReturningQuery[tuple[int]] = db.query(func.count(...))

# ✅ Correcto
query = db.query(func.count(...))  # type: ignore[assignment]
```

**Archivos afectados**:
- `app/api/v1/endpoints/dashboard.py` (~15 errores)
- `app/api/v1/endpoints/kpis.py` (~10 errores)

---

### 5. **Errores de Anotaciones Faltantes** (~10 errores)
**Problema**: Variables sin anotación de tipo

**Ejemplos**:
```python
# ❌ Incorrecto
documentos_procesados = set()

# ✅ Correcto
documentos_procesados: set[str] = set()
```

**Archivos afectados**:
- `app/api/v1/endpoints/pagos_conciliacion.py` (~1 error)
- `app/api/v1/endpoints/pagos.py` (~1 error)
- `app/api/v1/endpoints/dashboard.py` (~2 errores)
- `app/api/v1/endpoints/configuracion.py` (~1 error)

---

### 6. **Errores de Configuración Pydantic** (~10 errores)
**Problema**: Uso de `env` en Field (Pydantic 2.5.0)

**Archivos afectados**:
- `app/core/config.py` (~6 errores)

**Solución**: Cambiar a `Field(..., validation_alias=Env(...))` o usar `pydantic_settings`

---

### 7. **Errores Específicos de Módulos** (~14 errores)
**Problema**: Errores diversos en módulos específicos

**Archivos afectados**:
- `app/api/v1/endpoints/health.py` (~10 errores)
- `app/api/v1/endpoints/conciliacion_bancaria.py` (~4 errores)
- `app/api/v1/endpoints/cobranzas.py` (~1 error)
- `app/utils/filtros_dashboard.py` (~6 errores)
- `app/utils/pagos_staging_helper.py` (~1 error)
- `app/services/prestamo_evaluacion_service.py` (~3 errores)
- `app/api/v1/endpoints/amortizacion.py` (~20 errores)

---

## 🟡 PRIORIDAD MEDIA - Flake8 (51 errores)

### 1. **Complejidad de Funciones** (13 errores)
**Código**: `C901` - Funciones demasiado complejas

**Archivos afectados**:
- `app/api/v1/endpoints/dashboard.py`: `dashboard_administrador` (complejidad 33)
- `app/api/v1/endpoints/pagos.py`: `listar_pagos_staging` (24), `migrar_pago_staging_a_pagos` (12), `verificar_conexion_pagos_staging` (16)
- `app/api/v1/endpoints/pagos_upload.py`: `_procesar_fila_pago` (18)
- `app/api/v1/endpoints/configuracion.py`: `_validar_logo` (14), `upload_logo` (13)
- `app/core/cache.py`: `TryExcept` (19), `cache_result` (11)
- `app/core/config.py`: `Settings.validate_admin_credentials` (12)
- `app/services/email_service.py`: `EmailService._cargar_configuracion` (14)
- `app/utils/filtros_dashboard.py`: `_detectar_tabla_pago` (13), `aplicar_filtros_cuota` (11)

**Solución**: Refactorizar funciones grandes en funciones más pequeñas

---

### 2. **Variables No Usadas** (6 errores)
**Código**: `F841` - Variables asignadas pero nunca usadas

**Archivos afectados**:
- `app/api/v1/endpoints/dashboard.py`: `all_values`, `total_cobrado_query`, `fecha_inicio_mes`
- `app/api/v1/endpoints/kpis.py`: `fecha_corte_dt`
- `app/api/v1/endpoints/pagos_upload.py`: `e`
- `app/core/config.py`: `e2`

**Solución**: Eliminar variables no usadas o usar `_` como prefijo

---

### 3. **Espacios en Blanco** (26 errores)
**Código**: `W291` (trailing whitespace), `W293` (blank line contains whitespace)

**Archivos afectados**:
- `app/api/v1/endpoints/dashboard.py`: 7 errores
- `app/api/v1/endpoints/pagos.py`: 10 errores
- `app/api/v1/endpoints/pagos_conciliacion.py`: 5 errores
- `app/api/v1/endpoints/pagos_upload.py`: 5 errores
- `app/api/v1/endpoints/reportes.py`: 1 error

**Solución**: Ejecutar Black o eliminar espacios manualmente

---

### 4. **Imports No al Inicio** (4 errores)
**Código**: `E402` - Module level import not at top of file

**Archivos afectados**:
- `app/api/v1/endpoints/aprobaciones.py`: 4 errores (líneas 10-13)

**Solución**: Mover imports al inicio del archivo

---

### 5. **Errores Menores** (2 errores)
- `F541`: f-string sin placeholders (`app/api/v1/endpoints/dashboard.py:2365`)
- `W605`: Invalid escape sequence (`app/utils/pagos_staging_helper.py:28`)

**Solución**: Corregir f-string y usar raw string para regex

---

## 🟢 PRIORIDAD BAJA - Mejoras Opcionales

### 1. **Documentación**
- Agregar docstrings faltantes
- Mejorar type hints en funciones públicas

### 2. **Refactorización**
- Simplificar funciones complejas
- Extraer lógica duplicada

### 3. **Optimización**
- Revisar queries N+1
- Optimizar consultas complejas

---

## 📝 PLAN DE ACCIÓN SUGERIDO

### Fase 1: Correcciones Rápidas (1-2 horas)
1. ✅ Errores de imports no tipados (COMPLETADO)
2. ⏳ Espacios en blanco (Black puede corregir automáticamente)
3. ⏳ Variables no usadas
4. ⏳ Imports no al inicio

### Fase 2: Correcciones de Tipo (4-6 horas)
1. ⏳ Agregar `# type: ignore[assignment]` a asignaciones Column
2. ⏳ Agregar `# type: ignore[arg-type]` a argumentos Column
3. ⏳ Corregir anotaciones faltantes
4. ⏳ Corregir tipos de retorno

### Fase 3: Refactorización (8-12 horas)
1. ⏳ Simplificar funciones complejas
2. ⏳ Corregir errores de Query
3. ⏳ Corregir errores de Pydantic

### Fase 4: Errores Específicos (4-6 horas)
1. ⏳ Corregir errores en módulos específicos
2. ⏳ Revisar y corregir errores de health.py
3. ⏳ Corregir errores de amortizacion.py

---

## 🎯 ESTADO ACTUAL

- ✅ **Completado**: Errores de imports no tipados
- 🔄 **En progreso**: Análisis de errores pendientes
- ⏳ **Pendiente**: 274 errores de Mypy
- ⏳ **Pendiente**: 51 errores de Flake8

---

**Nota**: Este documento se actualiza automáticamente después de cada análisis de calidad de código.

