# 🔍 Verificación de Modelo ML Impago Activo

**Fecha:** 2025-01-17  
**Objetivo:** Verificar si hay un modelo ML de impago activo y si el archivo .pkl existe

---

## 📋 Métodos de Verificación

### Método 1: Usar Endpoint de API (Recomendado)

#### Endpoint: `/api/v1/ai/training/ml-impago/modelos`

Este endpoint retorna información sobre todos los modelos y el modelo activo.

**Ejemplo de uso:**
```bash
GET https://rapicredit.onrender.com/api/v1/ai/training/ml-impago/modelos
```

**Respuesta esperada:**
```json
{
  "modelos": [
    {
      "id": 1,
      "nombre": "Modelo Impago Cuotas 20251117_015506",
      "version": "1.0.0",
      "algoritmo": "random_forest",
      "activo": true,
      "ruta_archivo": "impago_cuotas_model_20251117_015506.pkl",
      "accuracy": 1.0,
      "entrenado_en": "2025-11-17T01:55:06",
      ...
    }
  ],
  "modelo_activo": {
    "id": 1,
    "nombre": "Modelo Impago Cuotas 20251117_015506",
    "activo": true,
    "ruta_archivo": "impago_cuotas_model_20251117_015506.pkl",
    ...
  },
  "total": 1
}
```

**Interpretación:**
- ✅ Si `modelo_activo` no es `null`: Hay un modelo activo
- ❌ Si `modelo_activo` es `null`: No hay modelo activo

---

### Método 2: Usar Endpoint de Diagnóstico (Mejorado)

#### Endpoint: `/api/v1/cobranzas/diagnostico-ml`

Este endpoint verifica el estado completo del modelo, incluyendo si el archivo .pkl existe.

**Ejemplo de uso:**
```bash
GET https://rapicredit.onrender.com/api/v1/cobranzas/diagnostico-ml
```

**Respuesta esperada:**
```json
{
  "ml_service_available": true,
  "modelo_en_bd": {
    "id": 1,
    "nombre": "Modelo Impago Cuotas 20251117_015506",
    "ruta_archivo": "impago_cuotas_model_20251117_015506.pkl",
    "algoritmo": "random_forest",
    "accuracy": 1.0
  },
  "modelo_cargado": true,
  "archivo_existe": true,
  "archivo_valido": true,
  "ruta_absoluta_encontrada": "/ruta/completa/al/archivo.pkl",
  "tamaño_archivo_kb": 1234.56,
  "tipo_modelo": "RandomForestClassifier",
  "archivos_pkl_disponibles": [
    {
      "nombre": "impago_cuotas_model_20251117_015506.pkl",
      "ruta": "/ruta/completa",
      "tamaño_kb": 1234.56
    }
  ],
  "errores": []
}
```

**Interpretación:**
- ✅ `modelo_en_bd` no es `null`: Hay modelo en BD
- ✅ `archivo_existe: true`: El archivo .pkl existe
- ✅ `archivo_valido: true`: El archivo es válido
- ✅ `modelo_cargado: true`: El modelo se cargó en memoria
- ❌ Si hay errores en `errores[]`: Revisar los mensajes de error

---

### Método 3: Consulta SQL Directa

Ejecutar el script SQL: `scripts/sql/verificar_modelo_activo.sql`

**Consulta principal:**
```sql
SELECT 
    id,
    nombre,
    algoritmo,
    activo,
    ruta_archivo,
    accuracy,
    entrenado_en,
    activado_en
FROM modelos_impago_cuotas
WHERE activo = true;
```

**Interpretación:**
- Si retorna filas: Hay modelo activo
- Si no retorna filas: No hay modelo activo

---

## 🔍 Verificación del Archivo .pkl

Una vez confirmado que hay un modelo activo, verificar que el archivo .pkl existe:

### Ubicaciones donde se busca el archivo:

1. **Ruta original** (como está en la BD)
2. **`ml_models/`** (directorio de modelos en el directorio actual)
3. **`ml_models/filename`** (solo el nombre del archivo)
4. **`project_root/ml_models/`** (directorio raíz del proyecto)
5. **`cwd/`** (directorio de trabajo actual)

### Verificación manual:

1. Obtener la ruta del archivo desde la BD o el endpoint
2. Buscar el archivo en las ubicaciones mencionadas
3. Verificar permisos de lectura
4. Intentar cargar el archivo con pickle para verificar que es válido

---

## 📊 Estado Actual (Según UI)

Según la imagen proporcionada:
- ✅ **Modelo Activo:** "Modelo Impago Cuotas 20251117_015506"
- ✅ **Algoritmo:** random_forest
- ✅ **Métricas:** 100.0% en todas (Accuracy, Precision, Recall, F1)
- ⚠️ **Fecha de entrenamiento:** 17/11/2025 (fecha futura - posible error)

---

## 🐛 Problemas Comunes

### 1. Modelo activo en BD pero archivo no existe
**Solución:** 
- Verificar la ruta en la BD
- Buscar el archivo en las ubicaciones alternativas
- Si el archivo fue movido, actualizar la ruta en la BD

### 2. Archivo existe pero no se carga
**Solución:**
- Verificar permisos de lectura
- Verificar que el archivo no esté corrupto
- Revisar logs del backend para errores específicos

### 3. No hay modelo activo
**Solución:**
- Entrenar un nuevo modelo desde la UI
- O activar un modelo existente desde la UI

---

## ✅ Checklist de Verificación

- [ ] Verificar modelo activo en BD (usar endpoint o SQL)
- [ ] Verificar que el archivo .pkl existe
- [ ] Verificar que el archivo es válido (se puede cargar)
- [ ] Verificar que el servicio ML está disponible
- [ ] Verificar que el modelo se carga en memoria
- [ ] Probar una predicción para confirmar que funciona

---

## 🔗 Endpoints Útiles

1. **Listar modelos:** `GET /api/v1/ai/training/ml-impago/modelos`
2. **Diagnóstico ML:** `GET /api/v1/cobranzas/diagnostico-ml`
3. **Clientes atrasados con diagnóstico:** `GET /api/v1/cobranzas/clientes-atrasados?diagnostico_ml=true`

