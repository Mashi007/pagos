# 📚 Estructura del Sistema RAG (Retrieval-Augmented Generation)

**Fecha:** 2025-01-XX  
**Sistema:** RAPICREDIT - Chat AI

---

## 🏗️ Arquitectura General

El sistema RAG está estructurado en **3 capas principales**:

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React/TypeScript)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  RAGTab Component                                    │   │
│  │  - Gestión de Documentos                            │   │
│  │  - Generación de Embeddings                         │   │
│  │  - Búsqueda Semántica                               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI/Python)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Endpoints (/api/v1/ai/training/rag/*)               │   │
│  │  - GET  /rag/estado                                   │   │
│  │  - POST /rag/generar-embeddings                      │   │
│  │  - POST /rag/buscar                                  │   │
│  │  - POST /rag/documentos/{id}/embeddings             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  RAGService (rag_service.py)                         │   │
│  │  - Generación de embeddings                          │   │
│  │  - Búsqueda semántica                                │   │
│  │  - División en chunks                                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ SQLAlchemy ORM
┌─────────────────────────────────────────────────────────────┐
│                    BASE DE DATOS (PostgreSQL)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  documentos_ai (tabla)                               │   │
│  │  - Almacena documentos PDF/TXT/DOCX                 │   │
│  │  - Contenido extraído                                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  documento_ai_embeddings (tabla)                     │   │
│  │  - Embeddings vectoriales (JSON)                     │   │
│  │  - Chunks de texto                                   │   │
│  │  - Metadatos                                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ OpenAI API
┌─────────────────────────────────────────────────────────────┐
│                    OPENAI API                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  text-embedding-ada-002                              │   │
│  │  - Genera embeddings de 1536 dimensiones             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Componentes del Sistema

### 1. **Frontend: RAGTab Component**

**Ubicación:** `frontend/src/components/configuracion/RAGTab.tsx`

**Funcionalidades:**

#### **Pestaña 1: Gestión de Documentos**
- ✅ **Subir Documentos**
  - Formatos: PDF, TXT, DOCX
  - Tamaño máximo: 10MB
  - Campos: título, descripción, archivo
  
- ✅ **Listar Documentos**
  - Estado: Activo/Inactivo
  - Procesamiento: Procesado/Sin procesar
  - Información: nombre, tipo, tamaño, fecha
  
- ✅ **Procesar Documentos**
  - Extrae texto del archivo
  - Guarda contenido en BD
  - Marca como `contenido_procesado = true`
  
- ✅ **Editar Documentos**
  - Modificar título y descripción
  - Activar/Desactivar
  
- ✅ **Eliminar Documentos**
  - Elimina documento y embeddings asociados

#### **Pestaña 2: Embeddings y Búsqueda**
- ✅ **Estado de Embeddings**
  - Total documentos
  - Documentos con embeddings
  - Total embeddings generados
  - Progreso de procesamiento
  
- ✅ **Generar Embeddings**
  - Para todos los documentos procesados
  - O para documentos específicos
  - Divide en chunks automáticamente
  
- ✅ **Búsqueda Semántica**
  - Ingresar pregunta/consulta
  - Configurar Top K (1-10)
  - Buscar documentos relevantes
  - Mostrar similitud y chunks encontrados

---

### 2. **Backend: Endpoints RAG**

**Ubicación:** `backend/app/api/v1/endpoints/ai_training.py`

#### **GET `/api/v1/ai/training/rag/estado`**
```python
Retorna:
{
  "total_documentos": int,
  "documentos_con_embeddings": int,
  "total_embeddings": int,
  "ultima_actualizacion": "ISO datetime"
}
```

#### **POST `/api/v1/ai/training/rag/generar-embeddings`**
```python
Request:
{
  "documento_ids": [int] | null  # null = todos los documentos
}

Retorna:
{
  "documentos_procesados": int,
  "total_embeddings": int
}
```

**Proceso:**
1. Obtiene documentos procesados (`contenido_procesado = true`)
2. Divide cada documento en chunks (1000 caracteres, overlap 200)
3. Genera embeddings batch para todos los chunks
4. Elimina embeddings existentes del documento
5. Guarda nuevos embeddings en BD

#### **POST `/api/v1/ai/training/rag/buscar`**
```python
Request:
{
  "pregunta": str,
  "top_k": int  # Default: 3
}

Retorna:
{
  "documentos": [
    {
      "documento_id": int,
      "chunk_index": int,
      "texto_chunk": str,
      "similitud": float  # 0-1
    }
  ],
  "query_embedding": [float]  # Para debugging
}
```

**Proceso:**
1. Genera embedding de la pregunta usando OpenAI
2. Obtiene todos los embeddings de la BD
3. Calcula similitud coseno con cada embedding
4. Filtra por umbral (default: 0.7)
5. Ordena por similitud descendente
6. Retorna top_k documentos más relevantes

#### **POST `/api/v1/ai/training/rag/documentos/{documento_id}/embeddings`**
```python
Actualiza embeddings de un documento específico
Retorna: {"embeddings_generados": int}
```

---

### 3. **Backend: RAGService**

**Ubicación:** `backend/app/services/rag_service.py`

**Clase:** `RAGService`

**Configuración:**
- **Modelo:** `text-embedding-ada-002`
- **Dimensiones:** 1536
- **API:** OpenAI Embeddings API

**Métodos Principales:**

#### **`generar_embedding(texto: str) -> List[float]`**
- Genera embedding para un texto individual
- Limita a 8000 caracteres
- Timeout: 30 segundos

#### **`generar_embeddings_batch(textos: List[str]) -> List[List[float]]`**
- Genera embeddings para múltiples textos (más eficiente)
- Timeout: 60 segundos
- Retorna lista de embeddings

#### **`calcular_similitud_coseno(embedding1, embedding2) -> float`**
- Calcula similitud coseno entre dos embeddings
- Usa NumPy para cálculos vectoriales
- Retorna valor entre 0 y 1

#### **`buscar_documentos_relevantes(query_embedding, documento_embeddings, top_k, umbral_similitud) -> List[Dict]`**
- Busca documentos más relevantes
- Calcula similitud con cada embedding
- Filtra por umbral (default: 0.7)
- Ordena por similitud descendente
- Retorna top_k resultados

#### **`dividir_texto_en_chunks(texto, chunk_size=1000, overlap=200) -> List[str]`**
- Divide texto en chunks de tamaño fijo
- Overlap de 200 caracteres entre chunks
- Intenta cortar en puntos naturales (espacios, puntos)

---

### 4. **Base de Datos: Modelos**

#### **DocumentoAI** (`documentos_ai`)

**Ubicación:** `backend/app/models/documento_ai.py`

**Campos:**
```python
id: int (PK)
titulo: str
descripcion: str | null
nombre_archivo: str
tipo_archivo: str  # PDF, TXT, DOCX
tamaño_bytes: int | null
contenido_texto: Text  # Texto extraído del archivo
contenido_procesado: bool  # Si ya se extrajo el texto
activo: bool  # Si está disponible para el AI
ruta_archivo: str  # Ruta física del archivo
creado_en: datetime
actualizado_en: datetime
```

#### **DocumentoEmbedding** (`documento_ai_embeddings`)

**Ubicación:** `backend/app/models/documento_embedding.py`

**Campos:**
```python
id: int (PK)
documento_id: int (FK -> documentos_ai.id)
embedding: JSON  # Lista de 1536 números flotantes
chunk_index: int  # Índice del chunk (0, 1, 2...)
texto_chunk: Text  # Texto del chunk
modelo_embedding: str  # "text-embedding-ada-002"
dimensiones: int  # 1536
creado_en: datetime
actualizado_en: datetime
```

**Relación:**
- Un `DocumentoAI` puede tener múltiples `DocumentoEmbedding` (uno por chunk)
- Relación: `DocumentoAI` 1:N `DocumentoEmbedding`

---

## 🔄 Flujo de Trabajo Completo

### **1. Subir y Procesar Documento**

```
Usuario sube PDF/TXT/DOCX
    ↓
Frontend: POST /api/v1/configuracion/ai/documentos
    ↓
Backend: Guarda archivo físico y registro en documentos_ai
    ↓
Usuario hace clic en "Procesar"
    ↓
Backend: Extrae texto del archivo (PDF/TXT/DOCX)
    ↓
Backend: Guarda contenido_texto en BD
    ↓
Backend: Marca contenido_procesado = true
```

### **2. Generar Embeddings**

```
Usuario hace clic en "Generar Embeddings"
    ↓
Frontend: POST /api/v1/ai/training/rag/generar-embeddings
    ↓
Backend: Obtiene documentos con contenido_procesado = true
    ↓
Para cada documento:
    ↓
    RAGService: divide_texto_en_chunks(contenido_texto)
    ↓
    RAGService: generar_embeddings_batch(chunks)
    ↓
    OpenAI API: Genera embeddings (1536 dimensiones cada uno)
    ↓
    Backend: Elimina embeddings existentes del documento
    ↓
    Backend: Guarda nuevos embeddings en documento_ai_embeddings
    ↓
    (Un registro por chunk)
```

### **3. Búsqueda Semántica**

```
Usuario ingresa pregunta: "¿Cuáles son las políticas de préstamos?"
    ↓
Frontend: POST /api/v1/ai/training/rag/buscar
    ↓
Backend: RAGService.generar_embedding(pregunta)
    ↓
OpenAI API: Genera embedding de la pregunta (1536 dimensiones)
    ↓
Backend: Obtiene todos los embeddings de documento_ai_embeddings
    ↓
Para cada embedding:
    ↓
    RAGService: calcular_similitud_coseno(query_embedding, doc_embedding)
    ↓
    Si similitud >= 0.7:
        Agregar a resultados
    ↓
Backend: Ordena resultados por similitud descendente
    ↓
Backend: Retorna top_k documentos más relevantes
    ↓
Frontend: Muestra documentos con similitud y texto del chunk
```

---

## 📊 Características Técnicas

### **Chunking (División de Texto)**
- **Tamaño de chunk:** 1000 caracteres
- **Overlap:** 200 caracteres
- **Estrategia:** Intenta cortar en puntos naturales (espacios, puntos, saltos de línea)

### **Embeddings**
- **Modelo:** `text-embedding-ada-002`
- **Dimensiones:** 1536
- **Límite de texto:** 8000 caracteres por embedding
- **Formato:** Lista de números flotantes (JSON en BD)

### **Búsqueda Semántica**
- **Métrica:** Similitud coseno
- **Umbral mínimo:** 0.7 (70% de similitud)
- **Top K:** Configurable (default: 3)
- **Algoritmo:** Cálculo vectorial con NumPy

### **Almacenamiento**
- **Embeddings:** Almacenados como JSON en PostgreSQL
- **Chunks:** Texto completo del chunk guardado junto al embedding
- **Metadatos:** Modelo usado, dimensiones, fecha de creación

---

## 🔗 Integración con Chat AI

El sistema RAG se integra con el Chat AI de la siguiente manera:

1. **Cuando el usuario hace una pregunta en el Chat AI:**
   - El sistema genera embedding de la pregunta
   - Busca documentos relevantes usando RAG
   - Incluye los chunks más relevantes en el contexto del prompt
   - El AI genera respuesta usando el contexto encontrado

2. **Ventajas:**
   - ✅ Respuestas más precisas (contexto relevante)
   - ✅ Reduce costos de tokens (solo contexto necesario)
   - ✅ Mejora con más documentos
   - ✅ Búsqueda semántica (no solo palabras clave)

---

## 📈 Métricas y Estado

El sistema proporciona métricas en tiempo real:

- **Total Documentos:** Todos los documentos subidos
- **Documentos con Embeddings:** Documentos que ya tienen embeddings generados
- **Total Embeddings:** Número total de chunks con embeddings
- **Progreso:** Porcentaje de documentos procesados
- **Última Actualización:** Fecha/hora de última generación de embeddings

---

## ✅ Estado Actual del Sistema

### **Componentes Implementados:**
- ✅ Frontend completo (RAGTab)
- ✅ Backend endpoints funcionales
- ✅ RAGService implementado
- ✅ Modelos de BD creados
- ✅ Integración con OpenAI API
- ✅ Búsqueda semántica funcional
- ✅ Gestión completa de documentos

### **Características:**
- ✅ Soporte para PDF, TXT, DOCX
- ✅ Procesamiento automático de texto
- ✅ Generación de embeddings batch
- ✅ Búsqueda semántica con similitud coseno
- ✅ División inteligente en chunks
- ✅ Interfaz de usuario completa

---

## 🎯 Resumen Ejecutivo

El sistema RAG está **completamente estructurado y funcional** con:

1. **Frontend:** Interfaz completa para gestión y búsqueda
2. **Backend:** Endpoints RESTful bien definidos
3. **Servicio:** RAGService con todas las funcionalidades necesarias
4. **Base de Datos:** Modelos relacionales correctamente diseñados
5. **Integración:** Conectado con OpenAI API para embeddings
6. **Búsqueda:** Algoritmo de similitud coseno implementado

**El sistema está listo para producción y uso en el Chat AI.**
