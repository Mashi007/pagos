# 🔍 Análisis: Problema con Columna "Riesgo ML Impago" en Módulo Cobranza

**Fecha:** 2025-01-17  
**Problema:** La columna "Riesgo ML Impago" no muestra datos, aparece como "N/A" para todos los clientes.

---

## 📋 Resumen del Problema

La columna "Riesgo ML Impago" en el módulo de cobranza muestra "N/A" para todos los clientes, a pesar de que existe un sistema de ML para calcular predicciones de impago.

---

## 🔍 Análisis del Flujo de Carga del Modelo ML

### 1. **Endpoint: `/api/v1/cobranzas/clientes-atrasados`**

El endpoint intenta cargar el modelo ML en las siguientes etapas:

#### Etapa 1: Verificar Modelo Activo en BD
```python
modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()
```

**Posibles problemas:**
- ❌ No hay modelo activo en la base de datos
- ❌ El modelo existe pero `activo = False`
- ❌ Error al consultar la tabla `modelos_impago_cuotas`

#### Etapa 2: Verificar Servicio ML Disponible
```python
from app.services.ml_impago_cuotas_service import ML_IMPAGO_SERVICE_AVAILABLE, MLImpagoCuotasService

if not ML_IMPAGO_SERVICE_AVAILABLE:
    # scikit-learn no está disponible
    ml_service = None
```

**Posibles problemas:**
- ❌ `scikit-learn` no está instalado
- ❌ `ML_IMPAGO_SERVICE_AVAILABLE = False`

#### Etapa 3: Cargar Modelo desde Archivo
```python
ml_service = MLImpagoCuotasService()
if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
    ml_service = None
```

**Posibles problemas:**
- ❌ El archivo del modelo no existe en la ruta especificada
- ❌ El archivo existe pero no es accesible (permisos)
- ❌ El archivo está corrupto
- ❌ La ruta está mal configurada en la BD

#### Etapa 4: Verificar Modelo en Memoria
```python
if "impago_cuotas_model" in ml_service.models:
    modelo_cargado = True
else:
    ml_service = None
```

**Posibles problemas:**
- ❌ El modelo no se cargó correctamente en memoria
- ❌ Error al deserializar el archivo pickle

---

## 🔍 Análisis del Flujo de Predicción

Una vez que el modelo está cargado, se intenta calcular la predicción para cada cliente:

### Paso 1: Verificar Valores Manuales
```python
if prestamo.ml_impago_nivel_riesgo_manual and prestamo.ml_impago_probabilidad_manual is not None:
    # Usar valores manuales
    cliente_data["ml_impago"] = {...}
```

### Paso 2: Calcular con ML (si no hay valores manuales)
```python
elif ml_service and modelo_cargado:
    cuotas = cuotas_dict.get(prestamo.id, [])
    if cuotas:
        features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)
        prediccion = ml_service.predict_impago(features)
        
        if prediccion.get("prediccion") == "Error" or prediccion.get("prediccion") == "Desconocido":
            cliente_data["ml_impago"] = None
        else:
            cliente_data["ml_impago"] = {...}
```

**Posibles problemas:**
- ❌ No hay cuotas para el préstamo (`cuotas_dict` vacío)
- ❌ Error al extraer features (`extract_payment_features` falla)
- ❌ Error en la predicción (`predict_impago` retorna "Error" o "Desconocido")
- ❌ El modelo no está en memoria cuando se intenta predecir

---

## 🐛 Problemas Identificados

### 1. **Logging Insuficiente**
- Los errores se registran con `logger.debug()` que puede no estar visible en producción
- No hay logs claros cuando `ml_service` es `None`
- No se registra por qué el modelo no se cargó

### 2. **Manejo Silencioso de Errores**
- Cuando `ml_impago` es `None`, no se registra la razón específica
- Los errores en `predict_impago` se capturan pero no se propagan

### 3. **Falta de Validación de Estado**
- No se verifica si el modelo está realmente disponible antes de intentar usarlo
- No hay validación de que el archivo del modelo existe antes de intentar cargarlo

### 4. **Cache Puede Ocultar Problemas**
- El endpoint tiene cache de 5 minutos (`@cache_result(ttl=300)`)
- Si el modelo falla al cargar, el error se cachea y no se reintenta

---

## ✅ Soluciones Propuestas

### 1. **Mejorar Logging**
- Cambiar `logger.debug()` a `logger.warning()` o `logger.error()` para errores críticos
- Agregar logs informativos cuando el modelo no está disponible
- Registrar la razón específica por la que `ml_impago` es `None`

### 2. **Agregar Diagnóstico en Respuesta**
- Incluir información de diagnóstico en la respuesta cuando `diagnostico_ml=true`
- Mostrar estado del modelo, errores encontrados, y razones de fallo

### 3. **Validación Temprana**
- Verificar que el modelo existe antes de intentar cargarlo
- Validar que el archivo es accesible antes de intentar deserializarlo

### 4. **Manejo de Errores Mejorado**
- Capturar y registrar todos los errores específicos
- Proporcionar mensajes de error más descriptivos

---

## 🔧 Cambios Necesarios

1. **Mejorar logging en `obtener_clientes_atrasados`**
2. **Agregar validación de modelo antes de usar**
3. **Mejorar manejo de errores en `predict_impago`**
4. **Agregar información de diagnóstico en la respuesta**

---

## 📊 Verificación

Para verificar el problema, se puede:

1. Llamar al endpoint de diagnóstico: `GET /api/v1/cobranzas/diagnostico-ml`
2. Llamar al endpoint con diagnóstico: `GET /api/v1/cobranzas/clientes-atrasados?diagnostico_ml=true`
3. Verificar logs del backend para mensajes relacionados con ML
4. Verificar en la BD si hay un modelo activo: `SELECT * FROM modelos_impago_cuotas WHERE activo = true`

