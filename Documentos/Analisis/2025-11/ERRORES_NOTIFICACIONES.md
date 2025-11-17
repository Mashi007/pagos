# 🚨 ERRORES CRÍTICOS: Módulo de Notificaciones

**Fecha:** 2025-11-06
**Análisis:** Logs del backend

---

## 🔴 PROBLEMAS DETECTADOS

### **1. Error: Columna 'canal' No Existe en BD**

**Error:**
```
column notificaciones.canal does not exist
LINE 2: ...r_id, notificaciones.tipo AS notificaciones_tipo, notificaci...
```

**Causa:**
- El modelo `Notificacion` tiene definida la columna `canal` en el código
- La base de datos NO tiene esta columna
- Falta migración de Alembic

**Ubicación:**
- Modelo: `backend/app/models/notificacion.py` línea 50
- Endpoint: `backend/app/api/v1/endpoints/notificaciones.py` línea 213

**Impacto:**
- ❌ Endpoint `/api/v1/notificaciones/` retorna error 500
- ❌ No se pueden listar notificaciones
- ❌ No se pueden crear nuevas notificaciones con canal

---

### **2. Error: Routing - Ruta '/plantillas' Capturada por '/{notificacion_id}'**

**Error:**
```
RequestValidationError: [{'type': 'int_parsing', 'loc': ('path', 'notificacion_id'),
'msg': 'Input should be a valid integer, unable to parse string as an integer',
'input': 'plantillas', ...}]
```

**Causa:**
- La ruta `@router.get("/{notificacion_id}")` está ANTES de `/plantillas`
- FastAPI procesa rutas en orden de definición
- Cuando llega `/api/v1/notificaciones/plantillas`, FastAPI lo interpreta como `notificacion_id="plantillas"`
- Intenta convertir "plantillas" a `int`, lo cual falla

**Ubicación:**
- Endpoint: `backend/app/api/v1/endpoints/notificaciones.py`
- Ruta problemática: `@router.get("/{notificacion_id}")` (línea 232)
- Ruta correcta: `@router.get("/plantillas")` (línea 365)

**Impacto:**
- ❌ Endpoint `/api/v1/notificaciones/plantillas` retorna error 500
- ❌ No se pueden listar plantillas
- ❌ No se pueden crear/editar plantillas

---

## ✅ SOLUCIONES IMPLEMENTADAS

### **1. Manejo de Error de Columna Faltante**

**Cambio:**
- Agregado manejo específico para error de columna 'canal' faltante
- Mensaje de error más claro indicando que se requiere migración

**Código:**
```python
except Exception as e:
    logger.error(f"Error listando notificaciones: {e}")
    # Manejar error de columna 'canal' faltante
    if "canal" in str(e).lower() and "does not exist" in str(e).lower():
        logger.warning("Columna 'canal' no existe en BD. Se requiere migración de Alembic.")
        raise HTTPException(
            status_code=500,
            detail="La columna 'canal' no existe en la tabla 'notificaciones'. Ejecute las migraciones de Alembic."
        )
    raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
```

---

### **2. Reordenar Rutas (Pendiente)**

**Problema:**
- La ruta `/{notificacion_id}` debe estar DESPUÉS de todas las rutas específicas

**Solución Requerida:**
1. Mover `@router.get("/{notificacion_id}")` al final del archivo
2. Después de todas las rutas `/plantillas/*`
3. Esto asegura que FastAPI procese rutas específicas primero

**Orden Correcto:**
```python
@router.get("/")  # Listar todas
@router.get("/estadisticas/resumen")  # Estadísticas
@router.get("/plantillas")  # Listar plantillas
@router.get("/plantillas/verificar")  # Verificar plantillas
@router.post("/plantillas")  # Crear plantilla
@router.get("/plantillas/{plantilla_id}")  # Obtener plantilla
@router.put("/plantillas/{plantilla_id}")  # Actualizar plantilla
@router.delete("/plantillas/{plantilla_id}")  # Eliminar plantilla
# ... más rutas de plantillas ...
@router.get("/{notificacion_id}")  # ✅ AL FINAL - Obtener notificación por ID
```

---

## 🔧 ACCIONES REQUERIDAS

### **URGENTE:**

1. **Crear Migración de Alembic para Columna 'canal':**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Agregar columna canal a tabla notificaciones"
   alembic upgrade head
   ```

2. **Reordenar Rutas en `notificaciones.py`:**
   - Mover `@router.get("/{notificacion_id}")` al final del archivo
   - Después de todas las rutas `/plantillas/*`

3. **Verificar que la Migración se Aplicó:**
   - Verificar en BD que la columna `canal` existe
   - Verificar que el endpoint funciona

---

## 📋 CHECKLIST

- [ ] Crear migración de Alembic para columna 'canal'
- [ ] Aplicar migración en base de datos
- [ ] Reordenar rutas en `notificaciones.py`
- [ ] Verificar que `/api/v1/notificaciones/` funciona
- [ ] Verificar que `/api/v1/notificaciones/plantillas` funciona
- [ ] Verificar que `/api/v1/notificaciones/{id}` funciona

---

## 🎯 RESULTADO ESPERADO

**Después de las correcciones:**

✅ `/api/v1/notificaciones/` - Lista notificaciones correctamente
✅ `/api/v1/notificaciones/plantillas` - Lista plantillas correctamente
✅ `/api/v1/notificaciones/{id}` - Obtiene notificación por ID correctamente
✅ Sin errores 500 en endpoints de notificaciones

---

## 📝 NOTAS ADICIONALES

### **Cache Funcionando:**
- ✅ `/api/v1/pagos/kpis` - Cache HIT funcionando correctamente
- ✅ Logs muestran: `✅ [kpis_pagos] Cache HIT para mes 11/2025`

### **Otros Errores:**
- ⚠️ Columna 'leida' también puede no existir (ya manejado con try-except)
- ⚠️ Verificar todas las columnas del modelo vs BD

