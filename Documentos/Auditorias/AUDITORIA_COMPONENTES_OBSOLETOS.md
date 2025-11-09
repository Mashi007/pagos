# 🔍 AUDITORÍA DE COMPONENTES OBSOLETOS

**Fecha:** 2025-01-27  
**Auditor:** Sistema de Auditoría Automatizada  
**Objetivo:** Identificar y documentar componentes obsoletos, deprecados o legacy en el proyecto

---

## 📊 RESUMEN EJECUTIVO

### Componentes Obsoletos Identificados

- **🔴 CRÍTICO:** 2 funciones DEPRECATED en uso activo
- **🟡 MEDIO:** 3 métodos legacy mantenidos por compatibilidad
- **🟢 BAJO:** Múltiples referencias a código comentado/deshabilitado
- **🟢 BAJO:** Módulo Aprobaciones deshabilitado pero código presente

---

## 🔴 PRIORIDAD ALTA - Componentes DEPRECATED en Uso

### 1. **Funciones DEPRECATED en `dashboard.py`**

**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py` (líneas 1148-1171)

**Funciones identificadas:**
- `aplicar_filtros_prestamo()` - Línea 1150
- `aplicar_filtros_pago()` - Línea 1162

**Estado:** ✅ **VERIFICADO - NO EN USO - LISTO PARA ELIMINAR**

**Análisis de uso:**
- ✅ **Verificado:** Ninguna llamada directa a estas funciones deprecated
- ✅ **Todas las llamadas** usan `FiltrosDashboard.aplicar_filtros_prestamo()` y `FiltrosDashboard.aplicar_filtros_pago()` directamente
- ✅ Las funciones deprecated son solo wrappers que redirigen a la implementación nueva

**Recomendación:**
```python
# DEPRECATED: Usar FiltrosDashboard desde app.utils.filtros_dashboard
# Estas funciones se mantienen por compatibilidad pero se recomienda usar la clase centralizada
```

**Acción requerida:**
1. ✅ **VERIFICADO:** No hay llamadas a estas funciones
2. ✅ **SEGURO ELIMINAR:** Las funciones pueden ser eliminadas sin impacto
3. ✅ **ELIMINADO:** Las funciones deprecated fueron eliminadas de `dashboard.py` - 2025-01-27

**Impacto:** Ninguno - No estaban en uso, eran solo wrappers no utilizados

**Estado:** ✅ **COMPLETADO** - Funciones eliminadas exitosamente

---

### 2. **Métodos Legacy en `notificacion_automatica_service.py`**

**Ubicación:** `backend/app/services/notificacion_automatica_service.py`

#### 2.1. `obtener_cuotas_pendientes()` - Línea 76

**Estado:** ✅ **VERIFICADO - NO EN USO - LISTO PARA ELIMINAR**

```python
def obtener_cuotas_pendientes(self) -> List[Cuota]:
    """
    Obtener todas las cuotas pendientes (método legacy - mantener para compatibilidad)
    DEPRECATED: Usar obtener_cuotas_pendientes_optimizado() en su lugar
    """
```

**Análisis de uso:**
- ✅ **Verificado:** No hay llamadas a este método deprecated
- ✅ **Nota:** Existen otros métodos con nombres similares en otros archivos (`_obtener_cuotas_pendientes()` en `reportes.py` y `pagos.py`), pero son diferentes y no están relacionados

**Acción requerida:**
1. ✅ **VERIFICADO:** No está en uso
2. ✅ **SEGURO ELIMINAR:** El método puede ser eliminado sin impacto
3. ✅ **ELIMINADO:** El método deprecated fue eliminado de `notificacion_automatica_service.py` - 2025-01-27

**Estado:** ✅ **COMPLETADO** - Método eliminado exitosamente

#### 2.2. Otros métodos legacy mencionados

**Línea 238:** Método `enviar_notificacion()` - legacy  
**Línea 336:** Método `procesar_cuota_individual()` - legacy

**Análisis de uso:**
- ⚠️ **`enviar_notificacion()`:** SÍ está en uso (línea 370 del mismo archivo)
  - Internamente redirige a `enviar_notificacion_optimizada()`
  - Es un wrapper que mantiene compatibilidad
  - **Acción:** Mantener por ahora, pero documentar como legacy

**Acción requerida:**
1. ✅ **`enviar_notificacion()`:** En uso, mantener como wrapper legacy
2. ⏳ **`procesar_cuota_individual()`:** Verificar uso específico
3. Documentar métodos legacy que se mantienen por compatibilidad

---

## 🟡 PRIORIDAD MEDIA - Código Legacy y Variables

### 3. **Variables Legacy en `variables_notificacion_service.py`**

**Ubicación:** `backend/app/services/variables_notificacion_service.py` (línea 286)

**Estado:** Variables legacy para compatibilidad

**Acción requerida:**
- Revisar si estas variables legacy están siendo utilizadas
- Si no, eliminar el código legacy

---

### 4. **Endpoint Legacy en `cobranzas.py`**

**Ubicación:** `backend/app/api/v1/endpoints/cobranzas.py` (línea 1488)

**Estado:** ⚠️ **LEGACY**

```python
"""Informe de distribución de mora por rangos de antigüedad (legacy - usar /por-categoria-dias)"""
```

**Acción requerida:**
- Verificar si este endpoint está siendo utilizado
- Si no, marcarlo como deprecated o eliminarlo
- Documentar la migración a `/por-categoria-dias`

---

### 5. **Campo DEPRECATED en Dashboard**

**Ubicación:** `backend/app/api/v1/endpoints/dashboard.py` (línea 4406)

**Estado:** ⚠️ **DEPRECATED**

```python
# ⚠️ DEPRECATED: Usar morosidad_mensual. Este campo es mensual (NO acumulativo)
```

**Acción requerida:**
- Verificar uso del campo deprecated
- Migrar a `morosidad_mensual` si es necesario
- Documentar el cambio

---

## 🟢 PRIORIDAD BAJA - Código Comentado y Módulos Deshabilitados

### 6. **Módulo Aprobaciones Deshabilitado**

**Ubicación:** `frontend/src/App.tsx` (líneas 33, 180-184)

**Estado:** ✅ **VERIFICADO - NO EN USO - LISTO PARA DECISIÓN**

**Análisis de uso:**
- ✅ **Verificado:** No aparece en el Sidebar ni en ninguna ruta activa
- ✅ **Verificado:** No hay imports ni referencias al componente Aprobaciones en el frontend
- ⚠️ **Backend:** El endpoint `/api/v1/aprobaciones` SÍ está registrado y activo en `main.py`

**Código comentado:**
```typescript
// const Aprobaciones = lazy(() => import('@/pages/Aprobaciones').then(module => ({ default: module.Aprobaciones })))  // MODULO APROBACIONES DESHABILITADO

// MODULO APROBACIONES DESHABILITADO
// <Route
//   path="aprobaciones"
//   element={<Aprobaciones />}
// />
```

**Acción requerida:**
- ✅ **ELIMINADO:** Código comentado eliminado de `App.tsx` - 2025-01-27
- ✅ **ELIMINADO:** Archivo `frontend/src/pages/Aprobaciones.tsx` eliminado - 2025-01-27
- ✅ **DESHABILITADO:** Endpoint backend comentado en `main.py` - 2025-01-27
  - Import comentado (línea 43)
  - Router comentado (línea 300)
  - El archivo `backend/app/api/v1/endpoints/aprobaciones.py` se mantiene por si se reactiva en el futuro

**Estado:** ✅ **COMPLETADO** - Módulo deshabilitado completamente

---

### 7. **Componente Dashboard Antiguo Eliminado**

**Ubicación:** `frontend/src/App.tsx` (línea 27)

**Estado:** ✅ **Ya eliminado, solo comentario**

```typescript
// Componente Dashboard antiguo eliminado - Usar DashboardMenu en su lugar
```

**Acción requerida:**
- Verificar que no existan referencias al componente antiguo
- El comentario puede mantenerse como documentación histórica

---

### 8. **Submenús Eliminados**

**Ubicación:** `frontend/src/pages/DashboardMenu.tsx` (línea 55)

**Estado:** ✅ **Comentario informativo**

```typescript
// Submenús eliminados: financiamiento, cuotas, cobranza, analisis, pagos
```

**Acción requerida:**
- Verificar que estos submenús no existan en otros lugares
- El comentario puede mantenerse como documentación

---

## 📦 DEPENDENCIAS - Revisión de Versiones

### Backend (Python)

**Archivo:** `backend/requirements/base.txt`

| Dependencia | Versión Actual | Estado | Notas |
|------------|----------------|--------|-------|
| fastapi | 0.104.1 | ⚠️ Revisar | Verificar versión más reciente |
| uvicorn | 0.24.0 | ⚠️ Revisar | Verificar versión más reciente |
| sqlalchemy | 2.0.23 | ⚠️ Revisar | Verificar versión más reciente |
| pydantic | 2.5.0 | ⚠️ Revisar | Verificar versión más reciente |
| python-jose | 3.3.0 | ⚠️ Revisar | Verificar versión más reciente |
| passlib | 1.7.4 | ⚠️ Revisar | Verificar versión más reciente |
| pytz | 2023.3 | ⚠️ Revisar | Verificar versión más reciente |

**Acción requerida:**
- Ejecutar `pip list --outdated` para verificar versiones desactualizadas
- Revisar changelogs de dependencias críticas
- Planificar actualizaciones con pruebas exhaustivas

### Frontend (Node.js)

**Archivo:** `frontend/package.json`

| Dependencia | Versión Actual | Estado | Notas |
|------------|----------------|--------|-------|
| react | ^18.2.0 | ✅ Actual | Versión estable |
| react-dom | ^18.2.0 | ✅ Actual | Versión estable |
| react-router-dom | ^6.20.1 | ⚠️ Revisar | Verificar versión más reciente |
| axios | ^1.6.2 | ⚠️ Revisar | Verificar versión más reciente |
| @tanstack/react-query | ^5.8.4 | ⚠️ Revisar | Verificar versión más reciente |
| typescript | ^5.2.2 | ⚠️ Revisar | Verificar versión más reciente |
| vite | ^7.2.1 | ⚠️ Revisar | Verificar versión más reciente |

**Acción requerida:**
- Ejecutar `npm outdated` para verificar versiones desactualizadas
- Revisar breaking changes antes de actualizar
- Actualizar dependencias de forma incremental

---

## 🔧 CONFIGURACIONES OBSOLETAS

### 9. **Configuración de CryptContext**

**Ubicación:** `backend/app/core/security.py` (línea 20)

**Estado:** ⚠️ **Deprecated scheme**

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**Nota:** El parámetro `deprecated="auto"` está marcado como deprecated en passlib.  
**Acción requerida:**
- Revisar documentación de passlib para la configuración correcta
- Actualizar si es necesario

---

## 📋 PLAN DE ACCIÓN RECOMENDADO

### Fase 1: Eliminación de Código DEPRECATED (Alta Prioridad) ✅ VERIFICADO

1. ✅ **Auditar uso de funciones deprecated:** COMPLETADO
   - ✅ Verificado: `aplicar_filtros_prestamo()` y `aplicar_filtros_pago()` NO están en uso
   - ✅ Verificado: `obtener_cuotas_pendientes()` NO está en uso

2. ✅ **Migración no requerida:** Todas las llamadas ya usan las versiones nuevas

3. ✅ **ELIMINADO funciones deprecated:**
   - ✅ **COMPLETADO:** Eliminadas `aplicar_filtros_prestamo()` y `aplicar_filtros_pago()` de `dashboard.py` - 2025-01-27
   - ✅ **COMPLETADO:** Eliminado `obtener_cuotas_pendientes()` de `notificacion_automatica_service.py` - 2025-01-27

### Fase 2: Limpieza de Código Legacy (Media Prioridad)

1. **Revisar y eliminar variables legacy** en `variables_notificacion_service.py`
2. **Decidir sobre endpoint legacy** en `cobranzas.py` (eliminar o documentar)
3. **Migrar campo deprecated** en dashboard a `morosidad_mensual`

### Fase 3: Limpieza de Código Comentado (Baja Prioridad) ✅ COMPLETADO

1. ✅ **Módulo Aprobaciones eliminado:**
   - ✅ Eliminado código comentado de `App.tsx`
   - ✅ Eliminado archivo `frontend/src/pages/Aprobaciones.tsx`
   - ✅ Deshabilitado endpoint backend en `main.py`
   - ✅ Archivo backend mantenido por si se reactiva en el futuro

2. **Limpiar comentarios informativos** que ya no son relevantes (pendiente)

### Fase 4: Actualización de Dependencias (Media Prioridad)

1. **Backend:**
   - Ejecutar `pip list --outdated`
   - Revisar changelogs
   - Actualizar dependencias críticas con pruebas

2. **Frontend:**
   - Ejecutar `npm outdated`
   - Actualizar dependencias de forma incremental
   - Ejecutar tests después de cada actualización

---

## ✅ CHECKLIST DE VERIFICACIÓN

### Código DEPRECATED
- [x] ✅ Verificar uso de `aplicar_filtros_prestamo()` y `aplicar_filtros_pago()` - NO EN USO
- [x] ✅ Verificar uso de `obtener_cuotas_pendientes()` - NO EN USO
- [x] ✅ **ELIMINADO** funciones deprecated de `dashboard.py` (líneas 1148-1171) - 2025-01-27
- [x] ✅ **ELIMINADO** método deprecated de `notificacion_automatica_service.py` (líneas 76-87) - 2025-01-27

### Código Legacy
- [ ] Revisar variables legacy en `variables_notificacion_service.py`
- [ ] Decidir sobre endpoint legacy en `cobranzas.py`
- [ ] Migrar campo deprecated en dashboard

### Código Comentado
- [x] ✅ Decidir sobre módulo Aprobaciones - ELIMINADO - 2025-01-27
- [x] ✅ Limpiar código comentado innecesario - COMPLETADO - 2025-01-27

### Dependencias
- [ ] Verificar versiones desactualizadas en backend
- [ ] Verificar versiones desactualizadas en frontend
- [ ] Planificar actualizaciones

---

## 📝 NOTAS ADICIONALES

1. **Archivos ya eliminados:** Según documentación previa, ya se eliminaron 24 archivos obsoletos de diagnóstico/analíticos (ver `ARCHIVOS_ELIMINADOS.md`)

2. **Documentación de migración:** Existe documentación sobre migraciones previas en `backend/docs/CONFIRMACION_MIGRACION_PAGOS.md`

3. **Scripts de verificación:** Existen scripts legacy en `scripts/` que pueden necesitar revisión

---

## 🎯 CONCLUSIÓN

El proyecto tiene **componentes obsoletos identificados** que requieren atención:

- **2 funciones DEPRECATED** que deben ser eliminadas o migradas
- **3 métodos legacy** que deben ser reemplazados por versiones optimizadas
- **Módulo deshabilitado** que requiere decisión (eliminar o reactivar)
- **Dependencias** que requieren revisión de versiones actuales

**Recomendación:** Ejecutar la Fase 1 (eliminación de código DEPRECATED) como prioridad alta para mantener el código limpio y evitar confusión futura.

---

**Próximos pasos:**
1. Ejecutar búsquedas para verificar uso de funciones deprecated
2. Crear plan de migración si hay uso activo
3. Ejecutar eliminación de código deprecated
4. Actualizar esta auditoría con resultados

