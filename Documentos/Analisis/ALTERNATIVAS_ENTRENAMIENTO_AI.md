# 🧠 Alternativas para Entrenar el AI - Análisis del Código Actual

## 📋 Resumen Ejecutivo

Este documento analiza el código actual del sistema de AI y propone alternativas para mejorar el entrenamiento y capacidades del asistente inteligente.

---

## 🔍 Análisis del Código Actual

### 1. **Sistema de Chat AI (OpenAI API)**

**Ubicación**: `backend/app/api/v1/endpoints/configuracion.py`

**Estado Actual**:
- ✅ Usa OpenAI API (GPT-3.5/GPT-4)
- ✅ Sistema de prompts personalizables
- ✅ Integración con base de datos para contexto
- ✅ Validación de preguntas relacionadas con BD
- ✅ Sistema de documentos AI para contexto adicional

**Características**:
- Endpoint: `/ai/chat`
- Acceso restringido a administradores
- Incluye resumen de BD, esquema, y documentos de contexto
- Sistema de palabras clave para validar preguntas

### 2. **Servicio de Machine Learning**

**Ubicación**: `backend/app/services/ml_service.py`

**Estado Actual**:
- ⚠️ Método `train_risk_model()` es solo un placeholder
- ✅ Estructura básica para cargar/guardar modelos
- ✅ Método `predict_risk()` implementado pero requiere modelo entrenado
- ✅ Usa pickle para serialización
- ✅ Scikit-learn disponible en dependencias

**Limitaciones**:
- No hay implementación real de entrenamiento
- No hay recolección de datos históricos para entrenamiento
- No hay pipeline de feature engineering

### 3. **Sistema de Documentos AI**

**Ubicación**: `backend/app/models/documento_ai.py`

**Estado Actual**:
- ✅ Tabla `documentos_ai` para almacenar documentos
- ✅ Extracción de texto de PDF, TXT, DOCX
- ✅ Procesamiento automático de contenido
- ✅ Integración con Chat AI para contexto

**Características**:
- Soporta: PDF, TXT, DOCX
- Almacena contenido extraído en BD
- Sistema de activación/desactivación
- Límite de 3 documentos por consulta

### 4. **Configuración de Prompts**

**Ubicación**: `frontend/src/components/configuracion/AIConfig.tsx`

**Estado Actual**:
- ✅ Editor de prompts personalizados
- ✅ Template con placeholders dinámicos
- ✅ Sistema de guardado en configuración

---

## 🚀 Alternativas de Entrenamiento

### **Opción 1: Fine-tuning con OpenAI (Recomendada para Chat AI)**

#### Descripción
Entrenar un modelo personalizado de OpenAI usando datos históricos de conversaciones y respuestas del sistema.

#### Ventajas
- ✅ Mejora directa del comportamiento del Chat AI
- ✅ Mantiene compatibilidad con la infraestructura actual
- ✅ No requiere infraestructura adicional
- ✅ OpenAI maneja el entrenamiento

#### Implementación
1. **Recolección de datos**:
   - Guardar conversaciones exitosas
   - Crear tabla `conversaciones_ai` con:
     - Pregunta del usuario
     - Respuesta del AI
     - Contexto usado (resumen BD, documentos)
     - Calificación/feedback del usuario
     - Timestamp

2. **Preparación de datos**:
   - Formato JSONL para OpenAI
   - Estructura: `{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}`

3. **Entrenamiento**:
   - Usar OpenAI Fine-tuning API
   - Modelos soportados: `gpt-4o` (recomendado), `gpt-4o-2024-08-06` (versión específica)
   - Nota: `gpt-3.5-turbo` y `gpt-4o-mini` NO están disponibles para fine-tuning
   - Costo: ~$0.008 por 1K tokens de entrenamiento (gpt-4o)

4. **Integración**:
   - Actualizar endpoint para usar modelo fine-tuned
   - Mantener fallback al modelo base

#### Código de Ejemplo
```python
# backend/app/services/ai_training_service.py
import openai
from typing import List, Dict
import json

class AITrainingService:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    def preparar_datos_entrenamiento(
        self,
        conversaciones: List[Dict]
    ) -> str:
        """Preparar datos en formato JSONL para fine-tuning"""
        datos = []
        for conv in conversaciones:
            datos.append({
                "messages": [
                    {"role": "system", "content": conv["system_prompt"]},
                    {"role": "user", "content": conv["pregunta"]},
                    {"role": "assistant", "content": conv["respuesta"]}
                ]
            })

        # Guardar como JSONL
        archivo_jsonl = "training_data.jsonl"
        with open(archivo_jsonl, "w") as f:
            for item in datos:
                f.write(json.dumps(item) + "\n")

        return archivo_jsonl

    def crear_archivo_entrenamiento(self, archivo_jsonl: str):
        """Subir archivo a OpenAI"""
        with open(archivo_jsonl, "rb") as f:
            file = self.client.files.create(
                file=f,
                purpose="fine-tune"
            )
        return file.id

    def iniciar_entrenamiento(
        self,
        file_id: str,
        modelo_base: str = "gpt-4o"  # gpt-4o-mini no está disponible para fine-tuning
    ):
        """Iniciar job de fine-tuning"""
        job = self.client.fine_tuning.jobs.create(
            training_file=file_id,
            model=modelo_base
        )
        return job.id

    def verificar_estado(self, job_id: str):
        """Verificar estado del entrenamiento"""
        job = self.client.fine_tuning.jobs.retrieve(job_id)
        return {
            "status": job.status,
            "model": job.fine_tuned_model if hasattr(job, 'fine_tuned_model') else None,
            "error": job.error if hasattr(job, 'error') else None
        }
```

#### Requisitos
- OpenAI API Key con acceso a fine-tuning
- Mínimo 10 conversaciones de ejemplo (recomendado: 50+)
- Presupuesto para entrenamiento (~$10-50 por modelo)

---

### **Opción 2: RAG (Retrieval-Augmented Generation) Mejorado**

#### Descripción
Mejorar el sistema actual de documentos AI con embeddings y búsqueda semántica para encontrar contexto más relevante.

#### Ventajas
- ✅ Mejora la precisión sin reentrenar modelos
- ✅ Escalable con más documentos
- ✅ Reduce costos de tokens (menos contexto innecesario)
- ✅ Respuestas más relevantes

#### Implementación
1. **Generar embeddings**:
   - Usar OpenAI Embeddings API o modelos locales (sentence-transformers)
   - Crear embeddings para cada documento y chunk de texto

2. **Almacenamiento**:
   - Opción A: Vector database (Pinecone, Weaviate, Qdrant)
   - Opción B: PostgreSQL con pgvector (extensión)
   - Opción C: Almacenar en tabla `documento_ai_embeddings`

3. **Búsqueda semántica**:
   - Convertir pregunta del usuario a embedding
   - Buscar documentos más similares (cosine similarity)
   - Incluir solo documentos relevantes en el prompt

4. **Chunking inteligente**:
   - Dividir documentos grandes en chunks de ~500 tokens
   - Mantener contexto entre chunks relacionados

#### Código de Ejemplo
```python
# backend/app/services/rag_service.py
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import openai

class RAGService:
    def __init__(self, use_openai: bool = True):
        self.use_openai = use_openai
        if not use_openai:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        else:
            self.client = openai.OpenAI()

    def generar_embedding(self, texto: str) -> List[float]:
        """Generar embedding para un texto"""
        if self.use_openai:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texto
            )
            return response.data[0].embedding
        else:
            return self.model.encode(texto).tolist()

    def buscar_documentos_relevantes(
        self,
        pregunta: str,
        documentos: List[Dict],
        top_k: int = 3
    ) -> List[Dict]:
        """Buscar documentos más relevantes usando embeddings"""
        pregunta_embedding = self.generar_embedding(pregunta)

        # Calcular similitud con cada documento
        scores = []
        for doc in documentos:
            if doc.get("embedding"):
                doc_embedding = doc["embedding"]
                # Cosine similarity
                similarity = np.dot(pregunta_embedding, doc_embedding) / (
                    np.linalg.norm(pregunta_embedding) * np.linalg.norm(doc_embedding)
                )
                scores.append((similarity, doc))

        # Ordenar por similitud y retornar top_k
        scores.sort(reverse=True, key=lambda x: x[0])
        return [doc for _, doc in scores[:top_k]]
```

#### Requisitos
- Instalar: `sentence-transformers` o usar OpenAI Embeddings API
- Extensión pgvector si se usa PostgreSQL
- Procesar documentos existentes para generar embeddings

---

### **Opción 3: Entrenamiento de Modelo de Riesgo Crediticio (ML)**

#### Descripción
Implementar el método `train_risk_model()` para crear un modelo predictivo de riesgo crediticio.

#### Ventajas
- ✅ Predicciones automáticas de riesgo
- ✅ Aprendizaje de patrones históricos
- ✅ Mejora con más datos
- ✅ Decisiones más objetivas

#### Implementación
1. **Recolección de datos**:
   - Histórico de préstamos aprobados/rechazados
   - Características: edad, ingreso, deuda, historial de pagos, etc.
   - Variable objetivo: morosidad, default, aprobación

2. **Feature Engineering**:
   - Variables numéricas: edad, ingreso, ratio deuda/ingreso
   - Variables categóricas: tipo de préstamo, concesionario
   - Variables temporales: días desde último préstamo
   - Variables agregadas: historial de pagos, morosidad previa

3. **Modelo**:
   - Algoritmo: Random Forest, XGBoost, o Neural Network
   - Validación: train/test split, cross-validation
   - Métricas: accuracy, precision, recall, F1, ROC-AUC

4. **Entrenamiento**:
   - Pipeline automatizado
   - Reentrenamiento periódico (mensual/trimestral)
   - Versionado de modelos

#### Código de Ejemplo
```python
# backend/app/services/ml_service.py (completar train_risk_model)
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import pandas as pd

def train_risk_model(self, training_data: list) -> bool:
    """
    Entrenar modelo de riesgo crediticio

    Args:
        training_data: Lista de diccionarios con datos históricos

    Returns:
        bool: True si se entrenó exitosamente
    """
    try:
        # Convertir a DataFrame
        df = pd.DataFrame(training_data)

        # Definir características (features)
        feature_columns = [
            'edad', 'ingreso', 'deuda_total', 'ratio_deuda_ingreso',
            'historial_pagos', 'dias_ultimo_prestamo', 'numero_prestamos_previos'
        ]

        # Variable objetivo
        target_column = 'riesgo'  # 'bajo', 'medio', 'alto'

        # Preparar datos
        X = df[feature_columns]
        y = df[target_column].map({'bajo': 0, 'medio': 1, 'alto': 2})

        # Dividir en train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Escalar características
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Entrenar modelo
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        model.fit(X_train_scaled, y_train)

        # Evaluar
        y_pred = model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        logger.info(f"✅ Modelo entrenado. Accuracy: {accuracy:.2%}")
        logger.info(f"\n{classification_report(y_test, y_pred)}")

        # Guardar modelo y scaler
        self.models["risk_model"] = model
        self.scalers["risk_scaler"] = scaler

        # Guardar en archivo
        self.save_models()

        return True

    except Exception as e:
        logger.error(f"Error entrenando modelo: {e}", exc_info=True)
        return False
```

#### Requisitos
- Datos históricos suficientes (mínimo 100-200 casos)
- Variables objetivo claramente definidas
- Pipeline de recolección de datos

---

### **Opción 4: Sistema Híbrido: Fine-tuning + RAG + ML**

#### Descripción
Combinar las tres opciones anteriores para un sistema completo y robusto.

#### Arquitectura
```
Usuario pregunta
    ↓
RAG Service → Buscar documentos relevantes
    ↓
ML Service → Predecir riesgo si aplica
    ↓
Fine-tuned Chat AI → Generar respuesta con contexto
    ↓
Respuesta final
```

#### Ventajas
- ✅ Máxima precisión y relevancia
- ✅ Múltiples fuentes de información
- ✅ Aprendizaje continuo
- ✅ Escalable y mantenible

#### Implementación por Fases

**Fase 1: RAG Mejorado (2-3 semanas)**
- Implementar embeddings
- Mejorar búsqueda semántica
- Procesar documentos existentes

**Fase 2: Fine-tuning (1-2 semanas)**
- Recolectar conversaciones
- Preparar datos de entrenamiento
- Entrenar modelo inicial

**Fase 3: ML de Riesgo (2-4 semanas)**
- Recolectar datos históricos
- Feature engineering
- Entrenar modelo de riesgo
- Integrar con Chat AI

**Fase 4: Optimización (continuo)**
- Monitoreo de métricas
- Reentrenamiento periódico
- A/B testing de modelos

---

## 📊 Comparación de Alternativas

| Criterio | Fine-tuning | RAG Mejorado | ML Riesgo | Híbrido |
|----------|-------------|--------------|-----------|---------|
| **Costo** | Medio ($10-50) | Bajo ($0-20/mes) | Bajo (gratis) | Alto ($50-100+) |
| **Tiempo Implementación** | 1-2 semanas | 2-3 semanas | 2-4 semanas | 6-8 semanas |
| **Complejidad** | Media | Media | Alta | Muy Alta |
| **Mejora Inmediata** | Alta | Alta | Media | Muy Alta |
| **Mantenimiento** | Bajo | Medio | Alto | Muy Alto |
| **Escalabilidad** | Alta | Muy Alta | Media | Muy Alta |
| **Requisitos Datos** | 50+ conversaciones | Documentos existentes | 100+ préstamos | Todos |

---

## 🎯 Recomendación

### **Corto Plazo (1-2 meses)**
1. **Implementar RAG Mejorado** (Opción 2)
   - Mejor ROI inmediato
   - Mejora la precisión sin grandes cambios
   - Aprovecha documentos existentes

2. **Iniciar recolección de datos para Fine-tuning**
   - Crear tabla `conversaciones_ai`
   - Guardar conversaciones exitosas
   - Sistema de feedback de usuarios

### **Mediano Plazo (3-6 meses)**
3. **Fine-tuning del Chat AI** (Opción 1)
   - Una vez tengas 50+ conversaciones de calidad
   - Entrenar modelo personalizado
   - A/B testing con modelo base

4. **ML de Riesgo Básico** (Opción 3)
   - Si hay suficientes datos históricos
   - Modelo simple inicial (Random Forest)
   - Integrar con proceso de aprobación

### **Largo Plazo (6+ meses)**
5. **Sistema Híbrido Completo** (Opción 4)
   - Integrar todas las mejoras
   - Pipeline automatizado de reentrenamiento
   - Monitoreo y optimización continua

---

## 📝 Próximos Pasos

1. **Decidir enfoque**: Elegir entre las opciones según recursos y objetivos
2. **Crear plan de implementación**: Detallar tareas y timeline
3. **Preparar infraestructura**: Dependencias, almacenamiento, APIs
4. **Recolección de datos**: Iniciar proceso de recopilación
5. **Prototipo**: Implementar versión mínima viable
6. **Testing**: Validar con datos reales
7. **Despliegue**: Lanzar a producción con monitoreo

---

## 🔗 Referencias

- [OpenAI Fine-tuning Guide](https://platform.openai.com/docs/guides/fine-tuning)
- [RAG Best Practices](https://www.pinecone.io/learn/retrieval-augmented-generation/)
- [Scikit-learn Documentation](https://scikit-learn.org/stable/)
- [PostgreSQL pgvector](https://github.com/pgvector/pgvector)

---

**Fecha de Análisis**: 2025-01-XX
**Versión**: 1.0
**Autor**: Análisis Automático del Código

