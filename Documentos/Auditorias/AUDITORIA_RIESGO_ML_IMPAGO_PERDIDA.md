# 🔍 AUDITORÍA INTEGRAL: Pérdida de Información Riesgo ML Impago

**Fecha:** 2025-11-18  
**Problema Reportado:** Con cada actualización se pierde la información de "Riesgo ML Impago" que sale del entrenamiento del modelo de AI en configuración AI.

---

## 📋 RESUMEN EJECUTIVO

### Problema Identificado
Las predicciones de Riesgo ML Impago se **calculan en tiempo real** cada vez que se solicita la información, pero **NO se persisten en la base de datos**. Esto causa que:

1. ❌ Con cada reinicio/actualización del servidor, si el modelo ML no se carga correctamente, todos los clientes muestran "N/A"
2. ❌ Si hay un error temporal en el servicio ML, se pierden todas las predicciones
3. ❌ No hay historial de predicciones anteriores
4. ❌ Se recalcula innecesariamente la misma información en cada request

---

## 🔍 ANÁLISIS DETALLADO

### 1. Flujo Actual de Cálculo de ML Impago

#### Endpoint: `/api/v1/cobranzas/clientes-atrasados`

**Ubicación:** `backend/app/api/v1/endpoints/cobranzas.py:414-800`

**Flujo:**
1. Se carga el modelo ML activo desde la BD (`modelos_impago_cuotas`)
2. Se verifica que el servicio ML esté disponible
3. Para cada préstamo:
   - **Primero verifica valores manuales** (`ml_impago_nivel_riesgo_manual`, `ml_impago_probabilidad_manual`)
   - Si NO hay valores manuales, **calcula en tiempo real** usando el modelo ML
   - **NO guarda el resultado calculado** en la base de datos
   - Solo retorna el resultado en la respuesta JSON

**Código relevante:**
```python
# Líneas 707-742
if prestamo.ml_impago_nivel_riesgo_manual and prestamo.ml_impago_probabilidad_manual is not None:
    # Usar valores manuales (guardados en BD)
    cliente_data["ml_impago"] = {...}
elif ml_service and modelo_cargado:
    # Calcular con ML (NO se guarda en BD)
    features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)
    prediccion = ml_service.predict_impago(features)
    cliente_data["ml_impago"] = {
        "probabilidad_impago": round(prediccion.get("probabilidad_impago", 0.0), 3),
        "nivel_riesgo": prediccion.get("nivel_riesgo", "Desconocido"),
        "prediccion": prediccion.get("prediccion", "Desconocido"),
        "es_manual": False,
    }
    # ❌ PROBLEMA: No se guarda en BD
```

### 2. Estructura de Datos Actual

#### Tabla: `prestamos`

**Campos relacionados a ML Impago:**
- `ml_impago_nivel_riesgo_manual` (String, nullable) - Solo para valores MANUALES
- `ml_impago_probabilidad_manual` (Numeric, nullable) - Solo para valores MANUALES

**❌ FALTA:**
- Campos para guardar predicciones **CALCULADAS** por ML
- Timestamp de última predicción calculada
- ID del modelo ML usado para la predicción

### 3. Puntos de Falla Identificados

#### Falla 1: Modelo ML no se carga
**Ubicación:** `backend/app/api/v1/endpoints/cobranzas.py:550-600`

Si el modelo ML no se carga correctamente:
- `ml_service = None` o `modelo_cargado = False`
- Todos los clientes muestran `ml_impago = None`
- No hay valores guardados como respaldo

#### Falla 2: Error en cálculo de predicción
**Ubicación:** `backend/app/api/v1/endpoints/cobranzas.py:745-750`

Si hay un error al calcular la predicción:
- Se captura la excepción
- Se asigna `cliente_data["ml_impago"] = None`
- No hay valores previos guardados para mostrar

#### Falla 3: Servicio ML no disponible
**Ubicación:** `backend/app/services/ml_impago_cuotas_service.py:21-45`

Si `scikit-learn` no está instalado o hay un error de importación:
- `ML_IMPAGO_SERVICE_AVAILABLE = False`
- `ml_service = None`
- Todos los clientes muestran "N/A"

#### Falla 4: Archivo del modelo no existe
**Ubicación:** `backend/app/services/ml_impago_cuotas_service.py:load_model_from_path()`

Si el archivo `.pkl` del modelo no existe o está corrupto:
- `ml_service.load_model_from_path()` retorna `False`
- `modelo_cargado = False`
- No hay predicciones guardadas como respaldo

---

## 🎯 SOLUCIÓN PROPUESTA

### Opción 1: Guardar Predicciones Calculadas (RECOMENDADA)

**Ventajas:**
- ✅ Las predicciones persisten entre reinicios
- ✅ Se puede mostrar información incluso si el modelo ML falla temporalmente
- ✅ Permite comparar predicciones históricas
- ✅ Reduce carga computacional (no recalcula si ya existe)

**Implementación:**
1. Agregar campos a tabla `prestamos`:
   - `ml_impago_nivel_riesgo_calculado` (String, nullable)
   - `ml_impago_probabilidad_calculada` (Numeric, nullable)
   - `ml_impago_calculado_en` (TIMESTAMP, nullable)
   - `ml_impago_modelo_id` (Integer, ForeignKey, nullable)

2. Modificar lógica de cálculo:
   - Primero verificar si hay predicción calculada reciente (ej: < 7 días)
   - Si existe y es reciente, usar esa
   - Si no existe o es antigua, calcular nueva y guardarla
   - Siempre priorizar valores manuales sobre calculados

3. Agregar job scheduler para recalcular periódicamente:
   - Recalcular predicciones cada X días
   - Actualizar solo si el modelo activo cambió

### Opción 2: Cache en Redis

**Ventajas:**
- ✅ Implementación más rápida
- ✅ No requiere cambios en esquema de BD

**Desventajas:**
- ❌ Se pierde con reinicio de Redis
- ❌ No hay historial permanente

---

## 📝 PLAN DE IMPLEMENTACIÓN

### Fase 1: Migración de Base de Datos
1. Crear migración Alembic para agregar campos
2. Ejecutar migración en desarrollo
3. Verificar que no rompe código existente

### Fase 2: Modificar Lógica de Cálculo
1. Modificar `obtener_clientes_atrasados()` para leer predicciones guardadas
2. Modificar cálculo para guardar resultados
3. Agregar lógica de actualización condicional

### Fase 3: Agregar Job de Actualización
1. Crear job en scheduler para recalcular predicciones
2. Configurar frecuencia de actualización
3. Agregar logs de monitoreo

### Fase 4: Testing y Validación
1. Probar que las predicciones se guardan correctamente
2. Probar que se leen correctamente después de reinicio
3. Probar que los valores manuales tienen prioridad
4. Probar que se actualizan cuando cambia el modelo activo

---

## 🔧 CÓDIGO DE REFERENCIA

### Campos Actuales en `prestamos`:
```python
# backend/app/models/prestamo.py:86-87
ml_impago_nivel_riesgo_manual = Column(String(20), nullable=True)
ml_impago_probabilidad_manual = Column(Numeric(5, 3), nullable=True)
```

### Lógica Actual de Cálculo:
```python
# backend/app/api/v1/endpoints/cobranzas.py:707-742
if prestamo.ml_impago_nivel_riesgo_manual and prestamo.ml_impago_probabilidad_manual:
    # Usar manuales
    cliente_data["ml_impago"] = {...}
elif ml_service and modelo_cargado:
    # Calcular (NO se guarda)
    prediccion = ml_service.predict_impago(features)
    cliente_data["ml_impago"] = {...}
```

---

## ✅ CONCLUSIÓN

El problema es que **las predicciones ML se calculan en tiempo real pero NO se persisten**. La solución es **guardar las predicciones calculadas en la base de datos** para que persistan entre actualizaciones y reinicios del servidor.

**Prioridad:** ALTA  
**Impacto:** Los usuarios pierden información importante con cada actualización  
**Esfuerzo:** MEDIO (requiere migración de BD y cambios en lógica)

