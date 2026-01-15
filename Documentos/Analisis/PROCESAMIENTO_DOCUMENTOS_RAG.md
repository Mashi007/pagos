# 📄 Procesamiento de Documentos en el Sistema RAG

**Fecha:** 2025-01-XX  
**Sistema:** RAPICREDIT - Chat AI

---

## 🔍 Ubicación del Procesamiento

El procesamiento de documentos (extracción de texto) **NO está en los endpoints de RAG**, sino en los **endpoints de configuración de AI**.

### **Ubicación Principal:**

**Archivo:** `backend/app/api/v1/endpoints/configuracion.py`

---

## 📍 Endpoints de Procesamiento

### **1. Procesamiento Automático al Subir**

**Endpoint:** `POST /api/v1/configuracion/ai/documentos`

**Ubicación en código:** Línea ~3615-3639

**Proceso:**
```python
# Al subir un documento:
1. Se guarda el archivo físico
2. Se crea registro en documentos_ai
3. Se llama automáticamente a _procesar_documento_creado()
4. Se extrae el texto del archivo
5. Se guarda contenido_texto en BD
6. Se marca contenido_procesado = true
```

**Función:** `_procesar_documento_creado()` (línea ~3389)

---

### **2. Procesamiento Manual**

**Endpoint:** `POST /api/v1/configuracion/ai/documentos/{documento_id}/procesar`

**Ubicación en código:** Línea ~4136-4230

**Proceso:**
```python
# Cuando el usuario hace clic en "Procesar":
1. Verifica si ya está procesado (contenido en BD)
2. Busca el archivo físico
3. Llama a _procesar_y_guardar_documento()
4. Extrae texto del archivo
5. Guarda contenido_texto en BD
6. Marca contenido_procesado = true
```

**Función:** `_procesar_y_guardar_documento()` (línea ~4074)

---

## 🔧 Funciones de Extracción de Texto

### **Función Principal:**

**`_extraer_texto_documento(ruta_archivo, tipo_archivo)`** (línea ~3432)

**Proceso:**
1. Detecta el tipo de archivo (PDF, TXT, DOCX)
2. Llama a la función específica de extracción
3. Limpia y normaliza el texto
4. Retorna texto extraído

---

### **Funciones Específicas por Tipo:**

#### **1. TXT - `_extraer_texto_txt()`** (línea ~3089)
```python
- Lee archivo con encoding UTF-8
- Si falla, intenta con: latin-1, cp1252, iso-8859-1
- Retorna texto completo
```

#### **2. PDF - `_extraer_texto_pdf()`** (línea ~3166)
```python
- Intenta primero con PyPDF2
- Si falla, intenta con pdfplumber (fallback)
- Extrae texto de todas las páginas
- Retorna texto concatenado
```

**Funciones auxiliares:**
- `_extraer_texto_pdf_pypdf2()` (línea ~3110)
- `_extraer_texto_pdf_pdfplumber()` (línea ~3143)

#### **3. DOCX - `_extraer_texto_docx()`** (línea ~3187)
```python
- Usa biblioteca python-docx
- Extrae texto de todos los párrafos
- Retorna texto concatenado
```

---

### **Función de Limpieza:**

**`_limpiar_y_normalizar_texto(texto)`** (línea ~3209)

**Proceso:**
1. Elimina espacios múltiples (más de 2 seguidos)
2. Normaliza saltos de línea (máximo 2 seguidos)
3. Elimina caracteres de control no visibles
4. Retorna texto limpio y normalizado

---

## 🔄 Flujo Completo de Procesamiento

### **Escenario 1: Subir Documento Nuevo**

```
Usuario sube PDF/TXT/DOCX
    ↓
POST /api/v1/configuracion/ai/documentos
    ↓
Backend: Guarda archivo físico en uploads/documentos_ai/
    ↓
Backend: Crea registro en documentos_ai (contenido_procesado = false)
    ↓
Backend: Llama automáticamente a _procesar_documento_creado()
    ↓
Backend: _extraer_texto_documento() según tipo:
    - PDF → _extraer_texto_pdf() → PyPDF2 o pdfplumber
    - TXT → _extraer_texto_txt() → lectura directa
    - DOCX → _extraer_texto_docx() → python-docx
    ↓
Backend: _limpiar_y_normalizar_texto() → limpia y normaliza
    ↓
Backend: Guarda contenido_texto en BD
    ↓
Backend: Marca contenido_procesado = true
    ↓
✅ Documento listo para generar embeddings
```

### **Escenario 2: Procesar Documento Existente**

```
Usuario hace clic en "Procesar" en RAGTab
    ↓
POST /api/v1/configuracion/ai/documentos/{id}/procesar
    ↓
Backend: Verifica si ya está procesado
    - Si tiene contenido_texto → Retorna éxito
    ↓
Backend: Busca archivo físico
    ↓
Backend: Llama a _procesar_y_guardar_documento()
    ↓
Backend: _extraer_texto_documento() → extrae texto
    ↓
Backend: Guarda contenido_texto en BD
    ↓
Backend: Marca contenido_procesado = true
    ↓
✅ Documento procesado y listo para embeddings
```

---

## 📊 Diferencias: Procesamiento vs Generación de Embeddings

### **Procesamiento de Documentos** (Extracción de Texto)
- **Ubicación:** `configuracion.py`
- **Endpoint:** `/api/v1/configuracion/ai/documentos/{id}/procesar`
- **Función:** Extraer texto del archivo físico
- **Resultado:** Guarda `contenido_texto` en BD
- **Estado:** Marca `contenido_procesado = true`

### **Generación de Embeddings** (RAG)
- **Ubicación:** `ai_training.py`
- **Endpoint:** `/api/v1/ai/training/rag/generar-embeddings`
- **Función:** Generar embeddings vectoriales del texto
- **Requisito:** Documento debe tener `contenido_procesado = true`
- **Resultado:** Guarda embeddings en `documento_ai_embeddings`

---

## 🎯 Resumen de Ubicaciones

| Proceso | Archivo | Función/Endpoint | Línea |
|---------|---------|------------------|-------|
| **Subir Documento** | `configuracion.py` | `POST /ai/documentos` | ~3550 |
| **Procesar Automático** | `configuracion.py` | `_procesar_documento_creado()` | ~3389 |
| **Procesar Manual** | `configuracion.py` | `POST /ai/documentos/{id}/procesar` | ~4136 |
| **Extraer Texto** | `configuracion.py` | `_extraer_texto_documento()` | ~3432 |
| **Extraer PDF** | `configuracion.py` | `_extraer_texto_pdf()` | ~3166 |
| **Extraer TXT** | `configuracion.py` | `_extraer_texto_txt()` | ~3089 |
| **Extraer DOCX** | `configuracion.py` | `_extraer_texto_docx()` | ~3187 |
| **Limpiar Texto** | `configuracion.py` | `_limpiar_y_normalizar_texto()` | ~3209 |
| **Generar Embeddings** | `ai_training.py` | `POST /rag/generar-embeddings` | ~918 |

---

## ⚠️ Puntos Importantes

### **1. El contenido se guarda en BD**
- ✅ El texto extraído se guarda en `documentos_ai.contenido_texto`
- ✅ No depende del archivo físico después del procesamiento
- ✅ Importante para sistemas efímeros (Render, etc.)

### **2. Procesamiento Automático**
- ✅ Al subir un documento, se procesa automáticamente
- ✅ Si falla, el usuario puede procesarlo manualmente después

### **3. Verificación de Archivo**
- ✅ Si el archivo físico desaparece pero hay contenido en BD, se usa el contenido de BD
- ✅ El sistema es resiliente a archivos efímeros

### **4. Dependencias**
- **PDF:** Requiere `PyPDF2` o `pdfplumber`
- **DOCX:** Requiere `python-docx`
- **TXT:** Sin dependencias adicionales

---

## 🔗 Integración con RAG

El procesamiento de documentos es el **primer paso** antes de generar embeddings:

```
1. Subir Documento → Procesar (extraer texto)
   ↓
2. Contenido en BD (contenido_texto)
   ↓
3. Generar Embeddings (RAG)
   ↓
4. Embeddings en BD (documento_ai_embeddings)
   ↓
5. Búsqueda Semántica disponible
```

---

## ✅ Conclusión

**El procesamiento de documentos está en `configuracion.py`, NO en los endpoints de RAG.**

Los endpoints de RAG (`ai_training.py`) solo generan embeddings de documentos **ya procesados** (que tienen `contenido_procesado = true` y `contenido_texto` en BD).
