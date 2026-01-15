# 📚 Dónde se Almacenan los Aprendizajes del Entrenamiento AI

**Fecha:** 2025-01-14  
**Sistema:** RAPICREDIT - Inteligencia Artificial

---

## 📊 RESUMEN EJECUTIVO

Todos los aprendizajes producto del entrenamiento del AI se almacenan en **PostgreSQL** en las siguientes tablas especializadas:

1. **Conversaciones de entrenamiento** → `conversaciones_ai`
2. **Jobs de fine-tuning** → `fine_tuning_jobs`
3. **Documentos procesados** → `documentos_ai`
4. **Embeddings vectoriales** → `documento_ai_embeddings`
5. **Diccionario semántico** → `ai_diccionario_semantico`
6. **Definiciones de campos** → `ai_definiciones_campos`
7. **Calificaciones del chat** → `ai_calificaciones_chat`
8. **Modelos de riesgo** → `modelos_riesgo`
9. **Modelos de impago** → `modelos_impago_cuotas`

---

## 🗄️ TABLAS DE ALMACENAMIENTO

### 1. **Conversaciones de Entrenamiento** 
**Tabla:** `conversaciones_ai`  
**Modelo:** `ConversacionAI`  
**Ubicación:** `backend/app/models/conversacion_ai.py`

**Qué almacena:**
- ✅ Preguntas y respuestas del chat AI
- ✅ Contexto usado para generar la respuesta
- ✅ Documentos usados (IDs)
- ✅ Modelo usado (gpt-3.5-turbo, gpt-4, etc.)
- ✅ Tokens consumidos
- ✅ Tiempo de respuesta
- ✅ Calificación (1-5 estrellas)
- ✅ Feedback del usuario
- ✅ Relaciones con tablas base (cliente_id, prestamo_id, pago_id, cuota_id)

**Propósito:** Almacena todas las conversaciones para:
- Fine-tuning de modelos
- Análisis de calidad de respuestas
- Mejora continua del sistema
- Entrenamiento con datos reales

**Ejemplo de uso:**
```python
# Las conversaciones se guardan automáticamente cuando el usuario usa el chat
# Se pueden filtrar por calificación para usar solo las mejores en fine-tuning
```

---

### 2. **Jobs de Fine-Tuning**
**Tabla:** `fine_tuning_jobs`  
**Modelo:** `FineTuningJob`  
**Ubicación:** `backend/app/models/fine_tuning_job.py`

**Qué almacena:**
- ✅ ID del job en OpenAI
- ✅ Estado del job (pending, running, succeeded, failed)
- ✅ Modelo base usado (gpt-4o, etc.)
- ✅ Modelo entrenado resultante (ID en OpenAI)
- ✅ Archivo de entrenamiento (ID en OpenAI)
- ✅ Total de conversaciones usadas
- ✅ Progreso del entrenamiento (0-100%)
- ✅ Errores si falla
- ✅ Parámetros (epochs, learning_rate)

**Propósito:** Rastrea todos los procesos de fine-tuning:
- Historial de entrenamientos
- Modelos generados
- Estado de cada job
- Métricas de éxito/fallo

**Ejemplo de uso:**
```python
# Se crea un job cuando inicias un fine-tuning desde la UI
# El sistema consulta periódicamente el estado en OpenAI
# Al completarse, se guarda el modelo entrenado para usar
```

---

### 3. **Documentos Procesados**
**Tabla:** `documentos_ai`  
**Modelo:** `DocumentoAI`  
**Ubicación:** `backend/app/models/documento_ai.py`

**Qué almacena:**
- ✅ Título y descripción del documento
- ✅ Nombre del archivo original
- ✅ Tipo de archivo (PDF, TXT, DOCX)
- ✅ Ruta donde se almacena físicamente
- ✅ Tamaño en bytes
- ✅ Contenido extraído (texto plano)
- ✅ Estado de procesamiento (procesado o no)
- ✅ Estado activo/inactivo

**Propósito:** Almacena documentos subidos para contexto:
- Políticas y procedimientos
- Manuales del sistema
- Información de referencia
- Contexto adicional para el AI

**Ejemplo de uso:**
```python
# Cuando subes un PDF en Configuración > AI > Documentos
# Se extrae el texto y se guarda aquí
# El AI puede usar estos documentos para responder preguntas
```

---

### 4. **Embeddings Vectoriales**
**Tabla:** `documento_ai_embeddings`  
**Modelo:** `DocumentoEmbedding`  
**Ubicación:** `backend/app/models/documento_embedding.py`

**Qué almacena:**
- ✅ Embedding vectorial (array de números flotantes)
- ✅ ID del documento relacionado
- ✅ Índice del chunk (si el documento se dividió)
- ✅ Texto del chunk
- ✅ Modelo usado (text-embedding-ada-002)
- ✅ Dimensiones del vector (1536 para ada-002)

**Propósito:** Almacena representaciones vectoriales para búsqueda semántica:
- Permite búsqueda por significado, no solo palabras exactas
- Usado en el sistema RAG (Retrieval-Augmented Generation)
- Mejora la precisión de respuestas basadas en documentos

**Ejemplo de uso:**
```python
# Cuando procesas un documento, se generan embeddings
# Cada chunk del documento tiene su propio embedding
# El AI busca chunks similares usando cosine similarity
```

---

### 5. **Diccionario Semántico**
**Tabla:** `ai_diccionario_semantico`  
**Modelo:** `AIDiccionarioSemantico`  
**Ubicación:** `backend/app/models/ai_diccionario_semantico.py`

**Qué almacena:**
- ✅ Palabra o término
- ✅ Definición de la palabra
- ✅ Categoría (identificacion, pagos, prestamos, etc.)
- ✅ Campo relacionado en BD (ej: "cedula", "nombres")
- ✅ Tabla relacionada (ej: "clientes", "pagos")
- ✅ Sinónimos (JSON array)
- ✅ Ejemplos de uso (JSON array)
- ✅ Estado activo/inactivo

**Propósito:** Entrena al AI para entender palabras comunes:
- Mapea lenguaje natural a campos técnicos
- Mejora comprensión de sinónimos
- Facilita acceso rápido a base de datos

**Ejemplo de uso:**
```python
# Usuario dice "cédula" → AI entiende que se refiere al campo "cedula"
# Usuario dice "nombre" → AI entiende que se refiere a "nombres"
# Se puede procesar con ChatGPT para mejorar definiciones
```

---

### 6. **Definiciones de Campos**
**Tabla:** `ai_definiciones_campos`  
**Modelo:** `AIDefinicionCampo`  
**Ubicación:** `backend/app/models/ai_definicion_campo.py`

**Qué almacena:**
- ✅ Tabla y campo de BD
- ✅ Definición del campo
- ✅ Tipo de dato (VARCHAR, INTEGER, DATE, etc.)
- ✅ Si es obligatorio
- ✅ Si tiene índice
- ✅ Si es clave foránea
- ✅ Tabla y campo referenciados
- ✅ Valores posibles (JSON array)
- ✅ Ejemplos de valores (JSON array)
- ✅ Notas adicionales

**Propósito:** Catálogo completo de campos de BD para el AI:
- Acceso rápido a definiciones técnicas
- Entrenamiento sobre estructura de BD
- Mejora de precisión en consultas

**Ejemplo de uso:**
```python
# El AI consulta esta tabla para entender qué campos existen
# Puede generar consultas más precisas
# Reduce errores por campos inexistentes
```

---

### 7. **Calificaciones del Chat**
**Tabla:** `ai_calificaciones_chat`  
**Modelo:** `AICalificacionChat`  
**Ubicación:** `backend/app/models/ai_calificacion_chat.py`

**Qué almacena:**
- ✅ Pregunta del usuario
- ✅ Respuesta del AI
- ✅ Calificación ("arriba" o "abajo")
- ✅ Email del usuario que calificó
- ✅ Estado de procesamiento
- ✅ Notas de procesamiento
- ✅ Si se mejoró el sistema basado en esto

**Propósito:** Sistema de feedback continuo:
- Identifica respuestas problemáticas
- Permite mejorar definiciones y prompts
- Rastrea calidad de respuestas

**Ejemplo de uso:**
```python
# Usuario califica con pulgar abajo → se guarda aquí
# Administrador revisa en Configuración > AI > Calificaciones
# Se procesa y mejora el sistema
```

---

### 8. **Modelos de Riesgo**
**Tabla:** `modelos_riesgo`  
**Modelo:** `ModeloRiesgo`  
**Ubicación:** `backend/app/models/modelo_riesgo.py`

**Qué almacena:**
- ✅ Predicciones de riesgo de préstamos
- ✅ Factores de riesgo identificados
- ✅ Métricas de precisión
- ✅ Fecha de evaluación

**Propósito:** Almacena predicciones de Machine Learning:
- Evaluación de riesgo de préstamos
- Análisis predictivo
- Historial de evaluaciones

---

### 9. **Modelos de Impago**
**Tabla:** `modelos_impago_cuotas`  
**Modelo:** `ModeloImpagoCuotas`  
**Ubicación:** `backend/app/models/modelo_impago_cuotas.py`

**Qué almacena:**
- ✅ Predicciones de impago de cuotas
- ✅ Probabilidades calculadas
- ✅ Factores identificados
- ✅ Métricas de precisión

**Propósito:** Predicción de cuotas que no se pagarán:
- Análisis predictivo de morosidad
- Identificación temprana de riesgo
- Historial de predicciones

---

## 🔗 RELACIONES ENTRE TABLAS

### Flujo de Entrenamiento:

```
1. Usuario usa Chat AI
   ↓
2. Conversación guardada en `conversaciones_ai`
   ↓
3. Usuario califica respuesta → `ai_calificaciones_chat`
   ↓
4. Administrador revisa calificaciones negativas
   ↓
5. Mejora diccionario semántico → `ai_diccionario_semantico`
   ↓
6. Mejora definiciones de campos → `ai_definiciones_campos`
   ↓
7. Recolecta conversaciones para fine-tuning
   ↓
8. Crea job de fine-tuning → `fine_tuning_jobs`
   ↓
9. Usa modelo entrenado en nuevas conversaciones
```

### Sistema RAG (Retrieval-Augmented Generation):

```
1. Documento subido → `documentos_ai`
   ↓
2. Texto extraído y dividido en chunks
   ↓
3. Embeddings generados → `documento_ai_embeddings`
   ↓
4. Usuario hace pregunta
   ↓
5. Sistema busca chunks similares usando embeddings
   ↓
6. Chunks encontrados se incluyen en contexto
   ↓
7. AI genera respuesta usando contexto
```

---

## 📍 UBICACIÓN FÍSICA DE ARCHIVOS

### Archivos de Documentos:
- **Ruta:** Configurable en `ConfiguracionSistema` (clave: `ruta_documentos_ai`)
- **Por defecto:** `backend/uploads/documentos_ai/`
- **Formato:** Se almacenan físicamente en el servidor

### Archivos de Entrenamiento (OpenAI):
- **Ubicación:** En OpenAI (no en servidor local)
- **Acceso:** Via API de OpenAI usando `openai_job_id`
- **Formato:** JSONL con conversaciones formateadas

---

## 🔍 CONSULTAS ÚTILES

### Ver todas las conversaciones de entrenamiento:
```sql
SELECT * FROM conversaciones_ai 
WHERE calificacion >= 4 
ORDER BY creado_en DESC;
```

### Ver jobs de fine-tuning activos:
```sql
SELECT * FROM fine_tuning_jobs 
WHERE status IN ('pending', 'running')
ORDER BY creado_en DESC;
```

### Ver documentos procesados:
```sql
SELECT * FROM documentos_ai 
WHERE contenido_procesado = true 
AND activo = true;
```

### Ver calificaciones negativas pendientes:
```sql
SELECT * FROM ai_calificaciones_chat 
WHERE calificacion = 'abajo' 
AND procesado = false
ORDER BY creado_en DESC;
```

### Contar embeddings por documento:
```sql
SELECT documento_id, COUNT(*) as total_chunks
FROM documento_ai_embeddings
GROUP BY documento_id;
```

---

## ✅ CONCLUSIÓN

Todos los aprendizajes del entrenamiento se almacenan de forma **estructurada y relacionada** en PostgreSQL:

- ✅ **Conversaciones** → Para fine-tuning y análisis
- ✅ **Jobs** → Para rastrear entrenamientos
- ✅ **Documentos** → Para contexto RAG
- ✅ **Embeddings** → Para búsqueda semántica
- ✅ **Diccionario** → Para comprensión de lenguaje
- ✅ **Definiciones** → Para acceso a BD
- ✅ **Calificaciones** → Para mejora continua
- ✅ **Modelos ML** → Para predicciones

El sistema está diseñado para **aprender continuamente** de las interacciones y mejorar con el tiempo.

---

**Última actualización:** 2025-01-14
