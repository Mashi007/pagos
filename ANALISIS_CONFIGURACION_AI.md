# Análisis: Configuración AI vs https://rapicredit.onrender.com/pagos/configuracion?tab=ai

**Fecha:** 2025-02-19  
**Alcance:** Eficiencia en configuración, entrenamiento, conexión real con backend.

---

## 1. Resumen ejecutivo

| Área | Estado | Hallazgos principales |
|------|--------|------------------------|
| **Configuración** | ⚠️ Parcial | Config real en BD; documentos y recolección no implementados |
| **Entrenamiento** | ⚠️ Mixto | Métricas y conversaciones reales; fine-tuning/RAG stubs |
| **Conexión real** | ⚠️ Inconsistente | Varios endpoints frontend → 404/ignorados en backend |

---

## 2. Eficiencia en configuración

### 2.1 Flujo actual al cargar `/configuracion?tab=ai`

| Request | Endpoint | Backend | Eficiencia |
|---------|----------|---------|------------|
| 1 | `GET /api/v1/configuracion/ai/configuracion` | ✅ BD real | OK |
| 2 | `GET /api/v1/configuracion/ai/documentos` | ✅ Stub (lista vacía) | Request innecesario si siempre vacío |
| 3 | PromptEditor (si visible) | `GET /api/v1/configuracion/ai/prompt` | ✅ BD real | OK |
| 4 | PromptEditor | `GET /api/v1/configuracion/ai/prompt/variables` | ✅ BD real | OK |

**Problemas:**
- **Carga paralela:** `cargarConfiguracion()` y `cargarDocumentos()` se ejecutan en paralelo en `useEffect` — correcto.
- **Documentos siempre vacíos:** El backend devuelve `{"total": 0, "documentos": []}` siempre. El frontend hace la petición aunque no haya documentos; podría omitirse o cachear.
- **PromptEditor:** Carga prompt y variables en montaje; si el usuario no abre la pestaña "Prompt", se hacen 2 requests extra.

### 2.2 Guardado de configuración

| Acción | Endpoint | Backend | Observación |
|--------|----------|---------|-------------|
| Guardar config | `PUT /api/v1/configuracion/ai/configuracion` | ✅ BD real | OK |
| Toggle activo | `PUT` (mismo) | ✅ BD real | Guarda automáticamente si hay token |
| Verificar y guardar | `POST /probar` + `PUT configuracion` | ✅ | OK |

**Problema:**
- **`recoleccion_automatica_activa`:** EntrenamientoMejorado hace `PUT` con `recoleccion_automatica_activa: "true"`. El backend `AIConfigUpdate` **no incluye este campo** y lo ignora (`extra="ignore"`). El valor no se persiste.

### 2.3 Chat de prueba (dentro de Configuración)

| Request | Endpoint | Backend | Observación |
|---------|----------|---------|-------------|
| Probar | `POST /api/v1/configuracion/ai/probar` | ✅ OpenRouter real | OK |

**Problema:**
- **`usar_documentos`:** El frontend envía `usar_documentos: true/false`, pero el backend **no lo usa**. El endpoint `/probar` siempre usa un prompt fijo ("Responde SIEMPRE en español") y no consulta documentos. El checkbox "Usar documentos de contexto" no tiene efecto.

---

## 3. Entrenamiento

### 3.1 Endpoints reales (conexión BD)

| Endpoint | Método | Descripción | BD |
|----------|--------|-------------|-----|
| `/api/v1/ai/training/metricas` | GET | Métricas (conversaciones, fine-tuning, RAG, ML) | ✅ `conversaciones_ai` |
| `/api/v1/ai/training/conversaciones` | GET | Lista paginada | ✅ |
| `/api/v1/ai/training/conversaciones` | POST | Crear conversación | ✅ |
| `/api/v1/ai/training/conversaciones/{id}/calificar` | POST | Calificar | ✅ |
| `/api/v1/ai/training/recolectar-automatico` | POST | Recolectar desde calificaciones | ⚠️ Stub (0 nuevas) |
| `/api/v1/ai/training/analizar-calidad` | POST | Análisis de calidad | ⚠️ Stub |
| `/api/v1/ai/training/fine-tuning/preparar` | POST | Preparar datos | ✅ BD |
| `/api/v1/ai/training/fine-tuning/iniciar` | POST | Iniciar job | ⚠️ Stub |
| `/api/v1/ai/training/rag/generar-embeddings` | POST | Embeddings | ⚠️ Stub |
| `/api/v1/configuracion/ai/tablas-campos` | GET | Esquema BD | ✅ Inspector |

### 3.2 Desconexión frontend–backend

| Funcionalidad frontend | Backend | Resultado |
|------------------------|---------|-----------|
| Recolección automática ON/OFF | No persiste `recoleccion_automatica_activa` | El toggle no se guarda |
| Usar documentos en Chat de prueba | `/probar` ignora `usar_documentos` | Checkbox sin efecto |
| Subir documento RAG | No existe `POST /documentos` | 404 |
| Procesar documento | No existe `POST /documentos/{id}/procesar` | 404 |
| Activar/desactivar documento | No existe `PATCH /documentos/{id}/activar` | 404 |

---

## 4. Conexión real: mapeo completo

### 4.1 Configuración AI (tab principal)

| UI | Endpoint | Estado |
|----|----------|--------|
| Cargar config | GET `/configuracion/ai/configuracion` | ✅ BD |
| Guardar config | PUT `/configuracion/ai/configuracion` | ✅ BD |
| Verificar conexión | POST `/configuracion/ai/probar` | ✅ OpenRouter |
| Chat de prueba | POST `/configuracion/ai/probar` | ✅ (sin documentos) |

### 4.2 Documentos RAG (dentro de Config)

| UI | Endpoint | Estado |
|----|----------|--------|
| Listar documentos | GET `/configuracion/ai/documentos` | ✅ Stub vacío |
| Subir documento | POST `/configuracion/ai/documentos` | ❌ No existe |
| Procesar documento | POST `/configuracion/ai/documentos/{id}/procesar` | ❌ No existe |
| Editar documento | PUT `/configuracion/ai/documentos/{id}` | ❌ No existe |
| Eliminar documento | DELETE `/configuracion/ai/documentos/{id}` | ❌ No existe |
| Activar/desactivar | PATCH `/configuracion/ai/documentos/{id}/activar` | ❌ No existe |

### 4.3 Prompt y variables

| UI | Endpoint | Estado |
|----|----------|--------|
| Cargar prompt | GET `/configuracion/ai/prompt` | ✅ BD |
| Guardar prompt | PUT `/configuracion/ai/prompt` | ✅ BD |
| Variables | GET/POST/PUT/DELETE `/configuracion/ai/prompt/variables` | ✅ BD |

### 4.4 Entrenamiento (tab Entrenamiento + Sistema Híbrido)

| UI | Endpoint | Estado |
|----|----------|--------|
| Métricas | GET `/ai/training/metricas` | ✅ BD |
| Recolección automática | PUT config con `recoleccion_automatica_activa` | ❌ Ignorado |
| Recolectar automático | POST `/ai/training/recolectar-automatico` | ⚠️ Stub |
| Analizar calidad | POST `/ai/training/analizar-calidad` | ⚠️ Stub |
| Fine-tuning, RAG, Calificaciones | Varios | ✅ Parcial (ver ai_training.py) |

---

## 5. Recomendaciones

### 5.1 Prioridad alta

1. **Persistir `recoleccion_automatica_activa`**
   - Añadir el campo a `AIConfigUpdate` y guardarlo en la fila `configuracion_ai` (JSON).
   - Devolverlo en GET `/configuracion`.

2. **Documentos: implementar o ocultar**
   - Opción A: Implementar CRUD de documentos (tabla, upload, procesar).
   - Opción B: Ocultar la sección de documentos en la UI hasta que exista backend.

3. **Chat de prueba y `usar_documentos`**
   - Opción A: Implementar uso de documentos en `/probar` (contexto RAG).
   - Opción B: Ocultar el checkbox "Usar documentos de contexto" si no hay soporte.

### 5.2 Prioridad media

4. **Carga diferida del PromptEditor**
   - Cargar prompt/variables solo cuando el usuario abra la pestaña o sección correspondiente.

5. **Evitar request de documentos si siempre vacío**
   - No llamar `cargarDocumentos()` al montar, o cachear el resultado cuando `total === 0`.

### 5.3 Prioridad baja

6. **Unificar fuentes de métricas**
   - Las métricas de conversaciones vienen de `conversaciones_ai`; las calificaciones del Chat AI están en `configuracion.chat_ai_calificaciones`. La recolección automática debería conectar ambas.

---

## 6. Resumen de archivos clave

| Archivo | Rol |
|---------|-----|
| `frontend/src/components/configuracion/AIConfig.tsx` | UI principal Config AI |
| `frontend/src/components/configuracion/EntrenamientoMejorado.tsx` | Tab Entrenamiento, recolección |
| `backend/app/api/v1/endpoints/configuracion_ai.py` | Config, probar, documentos (stub), prompt |
| `backend/app/api/v1/endpoints/ai_training.py` | Métricas, conversaciones, fine-tuning, RAG |
