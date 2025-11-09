# Análisis de Endpoints Obsoletos

**Fecha de Análisis:** 2025-01-XX

---

## 📊 Resumen Ejecutivo

Se identificaron **3 archivos de endpoints** que están definidos pero **NO están registrados** en `main.py`, lo que significa que sus endpoints no son accesibles a través de la API.

---

## 🔴 Endpoints NO Registrados (Críticos)

### 1. **`carga_masiva.py`** ⚠️ USADO EN FRONTEND

**Estado:** Definido pero NO registrado en `main.py`

**Endpoints definidos:**
- `POST /subir-archivo` - Subir archivo Excel para carga masiva
- `GET /dashboard` - Dashboard de carga masiva

**Uso en Frontend:**
- ✅ **USADO** en `frontend/src/services/clienteService.ts` (línea 146)
- Ruta: `/api/v1/carga-masiva/clientes`

**Impacto:** 🔴 **ALTO** - El frontend intenta usar este endpoint pero no está disponible

**Recomendación:** 
- **REGISTRAR** en `main.py` con:
  ```python
  app.include_router(carga_masiva.router, prefix="/api/v1/carga-masiva", tags=["carga-masiva"])
  ```

---

### 2. **`conciliacion_bancaria.py`** ⚠️ USADO EN FRONTEND

**Estado:** Definido pero NO registrado en `main.py`

**Endpoints definidos:**
- `GET /template-conciliacion` - Generar template Excel para conciliación
- `POST /procesar-conciliacion` - Procesar archivo Excel de conciliación
- `POST /desconciliar-pago` - Desconciliar un pago
- `GET /estado-conciliacion` - Obtener estado general de conciliación

**Uso en Frontend:**
- ✅ **USADO** en `frontend/src/components/pagos/ConciliacionExcelUploader.tsx`

**Impacto:** 🔴 **ALTO** - El frontend intenta usar estos endpoints pero no están disponibles

**Recomendación:**
- **REGISTRAR** en `main.py` con:
  ```python
  app.include_router(conciliacion_bancaria.router, prefix="/api/v1/conciliacion", tags=["conciliacion"])
  ```

---

### 3. **`scheduler_notificaciones.py`** ⚠️ ARCHIVO CORRUPTO

**Estado:** Archivo corrupto (sintaxis incorrecta) y NO registrado

**Problemas detectados:**
- ❌ Archivo con formato incorrecto (todo en una línea)
- ❌ Imports mal formateados
- ❌ Código ilegible

**Endpoints que debería tener (según estructura):**
- `GET /configuracion` - Obtener configuración del scheduler
- `PUT /configuracion` - Configurar scheduler
- `GET /logs` - Obtener logs del scheduler
- `POST /ejecutar-manual` - Ejecutar scheduler manualmente
- `GET /estado` - Obtener estado del scheduler
- `GET /verificacion-completa` - Verificación completa del sistema

**Uso en Frontend:**
- ⚠️ **POSIBLE USO** - Hay referencia a `/scheduler` en el sidebar (línea 149)

**Impacto:** 🟠 **MEDIO** - Funcionalidad de scheduler no disponible

**Recomendación:**
- **OPCIÓN 1:** Corregir el archivo y registrar
- **OPCIÓN 2:** Eliminar si no se usa (verificar primero en frontend)

---

## 📋 Endpoints Registrados (Activos)

Los siguientes endpoints **SÍ están registrados** y funcionan correctamente:

1. ✅ `auth.router` - `/api/v1/auth`
2. ✅ `users.router` - `/api/v1/usuarios`
3. ✅ `clientes.router` - `/api/v1/clientes`
4. ✅ `prestamos.router` - `/api/v1/prestamos`
5. ✅ `pagos.router` - `/api/v1/pagos`
6. ✅ `pagos_upload.router` - `/api/v1/pagos`
7. ✅ `pagos_conciliacion.router` - `/api/v1/pagos`
8. ✅ `amortizacion.router` - `/api/v1/amortizacion`
9. ✅ `solicitudes.router` - `/api/v1/solicitudes`
10. ✅ `aprobaciones.router` - `/api/v1/aprobaciones`
11. ✅ `notificaciones.router` - `/api/v1/notificaciones`
12. ✅ `reportes.router` - `/api/v1/reportes`
13. ✅ `cobranzas.router` - `/api/v1/cobranzas`
14. ✅ `dashboard.router` - `/api/v1/dashboard`
15. ✅ `kpis.router` - `/api/v1/kpis`
16. ✅ `auditoria.router` - `/api/v1`
17. ✅ `configuracion.router` - `/api/v1/configuracion`
18. ✅ `modelos_vehiculos.router` - `/api/v1/modelos-vehiculos`
19. ✅ `analistas.router` - `/api/v1/analistas`
20. ✅ `concesionarios.router` - `/api/v1/concesionarios`
21. ✅ `validadores.router` - `/api/v1/validadores`
22. ✅ `health.router` - `/api/v1`
23. ✅ `monitoring.router` - `/api/v1/monitoring`

---

## 🔍 Endpoints Potencialmente Obsoletos

### Endpoints de Diagnóstico/Health Check Duplicados

Algunos módulos tienen endpoints de health check que podrían ser redundantes:

1. **`/api/v1/cobranzas/health`** - Health check de cobranzas
2. **`/api/v1/reportes/health`** - Health check de reportes
3. **`/api/v1/pagos/health`** - Health check de pagos
4. **`/api/v1/pagos/diagnostico`** - Diagnóstico de pagos
5. **`/api/v1/cobranzas/diagnostico`** - Diagnóstico de cobranzas

**Recomendación:** 
- Evaluar si estos endpoints son necesarios o si se puede usar el health check general
- Si son solo para desarrollo, considerar moverlos a un router de desarrollo

---

## 📝 Plan de Acción

### Prioridad ALTA (Corregir Inmediatamente)

1. **Registrar `carga_masiva.router`**
   - Agregar en `main.py`:
     ```python
     app.include_router(carga_masiva.router, prefix="/api/v1/carga-masiva", tags=["carga-masiva"])
     ```

2. **Registrar `conciliacion_bancaria.router`**
   - Agregar en `main.py`:
     ```python
     app.include_router(conciliacion_bancaria.router, prefix="/api/v1/conciliacion", tags=["conciliacion"])
     ```

### Prioridad MEDIA

3. **Corregir o eliminar `scheduler_notificaciones.py`**
   - Verificar si se usa en frontend
   - Si se usa: Corregir formato del archivo y registrar
   - Si no se usa: Eliminar o mover a archivos obsoletos

### Prioridad BAJA

4. **Evaluar endpoints de diagnóstico duplicados**
   - Decidir si mantener o consolidar en health check general

---

## ✅ Verificación Post-Corrección

Después de registrar los endpoints faltantes, verificar:

1. ✅ Que el frontend pueda acceder a `/api/v1/carga-masiva/*`
2. ✅ Que el frontend pueda acceder a `/api/v1/conciliacion/*`
3. ✅ Que no haya errores 404 en las rutas del frontend
4. ✅ Que los tests de integración pasen

---

## 📊 Estadísticas

- **Total de routers definidos:** 26
- **Total de routers registrados:** 23
- **Routers NO registrados:** 3
- **Routers con problemas:** 1 (scheduler_notificaciones.py corrupto)

---

**Nota:** Este análisis se basa en la comparación entre los archivos en `backend/app/api/v1/endpoints/` y los routers registrados en `backend/app/main.py`.

