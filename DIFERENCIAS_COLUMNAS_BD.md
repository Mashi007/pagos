# 🔍 DIFERENCIAS DE COLUMNAS ENTRE MODELOS Y CÓDIGO

## ❌ PROBLEMAS ENCONTRADOS

### 1. **MODELO `Prestamo`**

#### ❌ Campo `activo` - NO EXISTE
**Usado en:**
- `backend/app/api/v1/endpoints/dashboard.py` (líneas 496, 502, 511, 612, 670)
- `backend/app/api/v1/endpoints/kpis.py` (líneas 54, 63)
- `backend/app/utils/filtros_dashboard.py` (línea 36)

**Campo real:** `estado` (String) con valores: "DRAFT", "EN_REVISION", "APROBADO", "RECHAZADO"

**Solución:** Reemplazar `Prestamo.activo.is_(True)` por `Prestamo.estado == "APROBADO"`

#### ❌ Campo `fecha_creacion` - NO EXISTE
**Usado en:**
- `backend/app/api/v1/endpoints/dashboard.py` (línea 670)

**Campo real:** `fecha_registro` (TIMESTAMP)

**Solución:** Reemplazar `Prestamo.fecha_creacion` por `Prestamo.fecha_registro`

---

### 2. **MODELO `Cliente`**

#### ❌ Campo `dias_mora` - NO EXISTE
**Usado en:**
- `backend/app/api/v1/endpoints/dashboard.py` (líneas 632, 857, 878, 913)

**Solución:** Calcular `dias_mora` desde `Cuota` o eliminar estas referencias

#### ❌ Campo `analista_id` - NO EXISTE
**Usado en:**
- `backend/app/api/v1/endpoints/dashboard.py` (línea 836)
- `backend/app/api/v1/endpoints/kpis.py` (línea 112)

**Solución:** Usar `Prestamo.usuario_proponente` o `Prestamo.analista` (String) mediante JOIN

#### ❌ Campo `total_financiamiento` - NO EXISTE
**Usado en:**
- `backend/app/api/v1/endpoints/dashboard.py` (líneas 854, 867, 877, 907)
- `backend/app/api/v1/endpoints/kpis.py` (línea 136)

**Solución:** Usar `Prestamo.total_financiamiento` mediante JOIN con `Prestamo`

#### ❌ Campo `nombre` - NO EXISTE
**Usado en:**
- `backend/app/api/v1/endpoints/dashboard.py` (línea 876)

**Campo real:** `nombres` (String)

**Solución:** Reemplazar `cliente.nombre` por `cliente.nombres`

---

## ✅ COLUMNAS CORRECTAS

### `Prestamo` (Modelo correcto):
- ✅ `estado` (String) - Usar: `Prestamo.estado == "APROBADO"`
- ✅ `fecha_registro` (TIMESTAMP) - Usar: `Prestamo.fecha_registro`
- ✅ `analista` (String) - Existe como campo opcional
- ✅ `concesionario` (String) - Existe como campo opcional
- ✅ `producto_financiero` (String) - Existe
- ✅ `total_financiamiento` (Numeric) - Existe

### `Cliente` (Modelo correcto):
- ✅ `activo` (Boolean) - Existe
- ✅ `estado` (String) - Existe
- ✅ `nombres` (String) - Existe
- ✅ `fecha_registro` (TIMESTAMP) - Existe

---

## 🔧 CORRECCIONES NECESARIAS

### Archivos a corregir:
1. `backend/app/api/v1/endpoints/dashboard.py`
2. `backend/app/api/v1/endpoints/kpis.py`
3. `backend/app/utils/filtros_dashboard.py`

### Cambios requeridos:
1. Reemplazar `Prestamo.activo` → `Prestamo.estado == "APROBADO"`
2. Reemplazar `Prestamo.fecha_creacion` → `Prestamo.fecha_registro`
3. Eliminar o calcular `Cliente.dias_mora` desde `Cuota`
4. Cambiar `Cliente.analista_id` → JOIN con `Prestamo.usuario_proponente`
5. Cambiar `Cliente.total_financiamiento` → JOIN con `Prestamo.total_financiamiento`
6. Reemplazar `Cliente.nombre` → `Cliente.nombres`

