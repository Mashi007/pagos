# ⚠️ ADVERTENCIA: ARCHIVOS FUNCIONALES NO REGISTRADOS

**Fecha:** 2025-01-27  
**Estado:** REVISIÓN REQUERIDA ANTES DE ELIMINAR

---

## 📋 ARCHIVOS FUNCIONALES NO REGISTRADOS EN MAIN.PY

Se identificaron **4 archivos funcionales** que NO están registrados en `main.py` pero que **podrían estar en uso**:

### 1. ⚠️ `carga_masiva.py` - **USADO POR FRONTEND**

**Estado:** 🔴 **NO DEBE ELIMINARSE** - Frontend lo llama

**Endpoints definidos:**
- `POST /subir-archivo`
- `GET /dashboard`

**Problema detectado:**
- El frontend llama a `/api/v1/carga-masiva/clientes` (línea 145 de `clienteService.ts`)
- Este endpoint **NO existe** en `carga_masiva.py`
- **Falta implementar** el endpoint `/clientes` o **corregir** la llamada del frontend

**Recomendación:**
- ✅ **REGISTRAR** en `main.py` con prefix `/api/v1/carga-masiva`
- ✅ **Implementar** endpoint `/clientes` o corregir frontend

---

### 2. ⚠️ `conciliacion_bancaria.py` - **ENDPOINTS FUNCIONALES**

**Estado:** 🟡 **REVISAR** - Tiene endpoints funcionales

**Endpoints definidos:**
- `GET /template-conciliacion`
- `POST /procesar-conciliacion`
- `POST /upload` (conciliación)
- `GET /estado-conciliacion`

**Uso en frontend:**
- `pagoService.uploadConciliacion()` llama a `/api/v1/pagos/conciliacion/upload`
- No llama directamente a `/api/v1/conciliacion-bancaria/*`

**Recomendación:**
- Verificar si estos endpoints son necesarios
- Si no se usan, eliminar
- Si se usan, registrar en `main.py`

---

### 3. ✅ `migracion_emergencia.py` - **PUEDE ELIMINARSE**

**Estado:** 🟢 **SEGURO ELIMINAR** - Solo migración de emergencia

**Endpoints definidos:**
- `POST /migracion-emergencia`

**Uso:**
- Solo para migraciones de emergencia
- No usado por frontend
- No usado por otros módulos

**Recomendación:**
- ✅ **ELIMINAR** - Ya no es necesario (migración completada)

---

### 4. ⚠️ `scheduler_notificaciones.py` - **CÓDIGO MALFORMADO**

**Estado:** 🟡 **REVISAR** - Código en una sola línea

**Problema:**
- El archivo tiene código malformado (todo en una línea)
- Parece tener endpoints definidos pero no legible

**Endpoints aparentes:**
- `GET /configuracion`
- `GET /logs`
- `GET /estado`
- `GET /verificacion-completa`
- `POST /ejecutar` (scheduler manual)

**Recomendación:**
- Revisar y corregir formato del archivo
- Si no se usa, eliminar
- Si se usa, registrar en `main.py`

---

## 📊 DECISIÓN RECOMENDADA

### ✅ SEGURO ELIMINAR:
1. ✅ `migracion_emergencia.py` - Solo migración de emergencia

### ⚠️ REQUIERE REVISIÓN:
2. ⚠️ `conciliacion_bancaria.py` - Verificar si se usa
3. ⚠️ `scheduler_notificaciones.py` - Corregir formato y verificar

### 🔴 NO ELIMINAR (REGISTRAR EN MAIN.PY):
4. 🔴 `carga_masiva.py` - Frontend lo llama (falta endpoint `/clientes`)

---

## 🎯 ACCIÓN RECOMENDADA

1. **Inmediato:**
   - ✅ Eliminar `migracion_emergencia.py`
   - ✅ Registrar `carga_masiva.py` en `main.py`
   - ✅ Implementar endpoint `/clientes` en `carga_masiva.py`

2. **Revisar:**
   - ⚠️ Verificar uso de `conciliacion_bancaria.py`
   - ⚠️ Corregir formato de `scheduler_notificaciones.py`

---

**Estado:** ⚠️ ESPERANDO DECISIÓN SOBRE ARCHIVOS FUNCIONALES

