# 🚀 Guía de Uso: Sistema Híbrido de IA y Variables Personalizadas

## 📋 Tabla de Contenidos

1. [Gestión de Variables Personalizadas](#gestión-de-variables-personalizadas)
2. [Fine-tuning](#fine-tuning)
3. [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
4. [ML Riesgo](#ml-riesgo)
5. [Ejemplos Prácticos Completos](#ejemplos-prácticos-completos)

---

## 🎯 Gestión de Variables Personalizadas

### ¿Qué son las Variables Personalizadas?

Las variables personalizadas son placeholders que puedes usar en las plantillas de notificaciones. Por ejemplo:
- `{resumen_bd}` → Resumen de la base de datos
- `{nombre_cliente}` → Nombre del cliente
- `{monto_total}` → Monto total del préstamo

### Cómo Crear una Variable Personalizada

**Paso 1:** Ve a **Plantillas** → Pestaña **"Variables Personalizadas"**

**Paso 2:** Haz clic en **"Nueva Variable"**

**Paso 3:** Completa el formulario:

```
Nombre de Variable: resumen_bd
Tabla: clientes
Campo BD: nombres
Descripción: Resumen de la base de datos del cliente
Estado: ✅ Activa
```

**Paso 4:** Haz clic en **"Guardar"**

### Ejemplo Práctico: Crear Variable `{resumen_bd}`

1. **Nombre de Variable:** `resumen_bd`
   - Se usará como `{{resumen_bd}}` en las plantillas
   - Solo letras minúsculas, números y guiones bajos

2. **Tabla:** Selecciona `clientes` (o la tabla que corresponda)

3. **Campo BD:** `nombres` (el campo de la base de datos)

4. **Descripción:** "Resumen de la base de datos del cliente"

5. **Estado:** Activa ✅

### Usar la Variable en una Plantilla

Una vez creada, puedes usarla en cualquier plantilla:

```
Asunto: Recordatorio de Pago - {{resumen_bd}}

Cuerpo:
Estimado/a {{resumen_bd}},

Le recordamos que tiene un pago pendiente de {{monto}} VES 
con fecha de vencimiento {{fecha_vencimiento}}.
```

### Operaciones Disponibles

- ✅ **Crear:** Nueva variable personalizada
- ✏️ **Editar:** Modificar variable existente
- 🗑️ **Eliminar:** Eliminar variable (con confirmación)
- 🔍 **Buscar:** Filtrar por nombre, tabla o campo
- 📊 **Filtrar:** Por tabla o estado (activa/inactiva)

---

## 🧠 Fine-tuning

### ¿Qué es Fine-tuning?

Fine-tuning es el proceso de entrenar un modelo de IA con conversaciones específicas de tu negocio para mejorar sus respuestas.

### Flujo de Trabajo

#### 1. **Calificar Conversaciones**

Las conversaciones con el chat de IA se guardan automáticamente. Debes calificarlas:

**Ejemplo:**
```
Conversación 1:
Pregunta: "¿Cuánto debo pagar este mes?"
Respuesta: "Según nuestros registros, tu pago mensual es de 500 VES"
Calificación: ⭐⭐⭐⭐⭐ (5 estrellas) - Excelente respuesta
```

**Cómo calificar:**
1. Ve a **Configuración** → **IA** → **Sistema Híbrido** → **Fine-tuning**
2. Revisa las conversaciones listadas
3. Haz clic en las estrellas (1-5) para calificar
4. Opcional: Agrega feedback escrito

#### 2. **Preparar Datos para Entrenamiento**

**Requisitos:**
- Mínimo 10 conversaciones calificadas con 4+ estrellas
- Las conversaciones deben ser relevantes y de calidad

**Proceso:**
1. Filtra conversaciones con calificación ≥ 4 estrellas
2. Haz clic en **"Preparar Datos para Entrenamiento"**
3. El sistema creará un archivo JSON con las conversaciones seleccionadas

**Ejemplo de datos preparados:**
```json
{
  "conversaciones": [
    {
      "pregunta": "¿Cuánto debo pagar este mes?",
      "respuesta": "Según nuestros registros, tu pago mensual es de 500 VES",
      "calificacion": 5
    },
    {
      "pregunta": "¿Cuándo vence mi próxima cuota?",
      "respuesta": "Tu próxima cuota vence el 15 de noviembre de 2025",
      "calificacion": 5
    }
  ]
}
```

#### 3. **Iniciar Entrenamiento**

1. Selecciona el **Modelo Base** (ej: `gpt-3.5-turbo`)
2. Configura parámetros opcionales:
   - **Epochs:** Número de iteraciones (recomendado: 3-5)
   - **Learning Rate:** Tasa de aprendizaje (recomendado: dejar por defecto)
3. Haz clic en **"Iniciar Fine-tuning"**

**Ejemplo de configuración:**
```
Modelo Base: gpt-3.5-turbo
Epochs: 3
Learning Rate: (por defecto)
```

#### 4. **Monitorear Progreso**

El sistema mostrará:
- **Estado:** pending → running → succeeded/failed
- **Progreso:** Porcentaje completado
- **Modelo Entrenado:** ID del modelo resultante

#### 5. **Activar Modelo**

Una vez completado:
1. Haz clic en **"Activar Modelo"** en el job completado
2. El modelo se activará automáticamente
3. Las nuevas conversaciones usarán este modelo

---

## 🔍 RAG (Retrieval-Augmented Generation)

### ¿Qué es RAG?

RAG mejora las respuestas de la IA buscando información relevante en tus documentos antes de responder.

### Flujo de Trabajo

#### 1. **Subir Documentos**

Ve a **Configuración** → **IA** → **Documentos** y sube documentos relevantes:

**Ejemplos de documentos útiles:**
- Manuales de procedimientos
- Políticas de la empresa
- FAQs (Preguntas Frecuentes)
- Información sobre productos/servicios
- Reglamentos y normativas

#### 2. **Generar Embeddings**

Los embeddings son representaciones vectoriales que permiten búsqueda semántica:

1. Ve a **Sistema Híbrido** → **RAG**
2. Haz clic en **"Generar Embeddings para Todos los Documentos"**
3. Espera a que se complete el proceso

**Estado esperado:**
```
Total Documentos: 10
Documentos con Embeddings: 10
Total Embeddings: 45
Última Actualización: 14/11/2025 16:30
```

#### 3. **Buscar Documentos Relevantes**

Puedes probar la búsqueda semántica:

**Ejemplo de búsqueda:**
```
Pregunta: "¿Cuál es la política de mora?"
Resultados:
1. Documento: "Políticas de Cobranza" (Similitud: 0.92)
2. Documento: "Reglamento de Préstamos" (Similitud: 0.85)
3. Documento: "FAQ Clientes" (Similitud: 0.78)
```

#### 4. **Usar RAG en el Chat**

Cuando un usuario hace una pregunta:
1. El sistema busca documentos relevantes usando embeddings
2. Incluye el contexto encontrado en la pregunta al modelo
3. El modelo responde con información precisa basada en tus documentos

**Ejemplo de uso automático:**
```
Usuario: "¿Cuántos días de gracia tengo para pagar?"

Sistema RAG:
1. Busca en documentos: "Políticas de Pago"
2. Encuentra: "Los clientes tienen 5 días de gracia después del vencimiento"
3. Responde: "Según nuestras políticas, tienes 5 días de gracia después 
   de la fecha de vencimiento de tu cuota."
```

---

## 🎯 ML Riesgo

### ¿Qué es ML Riesgo?

Es un modelo de Machine Learning que predice el riesgo crediticio de los clientes.

### Flujo de Trabajo

#### 1. **Entrenar Modelo**

1. Ve a **Sistema Híbrido** → **ML Riesgo**
2. Configura parámetros:
   - **Algoritmo:** Random Forest, Logistic Regression, etc.
   - **Test Size:** Porcentaje para prueba (recomendado: 0.2 = 20%)
3. Haz clic en **"Entrenar Modelo"**

**Ejemplo de configuración:**
```
Algoritmo: Random Forest
Test Size: 0.2 (20% para pruebas)
```

#### 2. **Monitorear Entrenamiento**

El sistema mostrará:
- **Estado:** training → completed
- **Progreso:** Porcentaje
- **Métricas:** Accuracy, Precision, Recall, F1-Score

**Ejemplo de resultados:**
```
Accuracy: 0.87 (87%)
Precision: 0.85
Recall: 0.89
F1-Score: 0.87
```

#### 3. **Activar Modelo**

1. Una vez completado, el modelo aparecerá en la lista
2. Haz clic en **"Activar"** en el modelo deseado
3. Confirma la activación

#### 4. **Probar Predicción**

Puedes probar el modelo con datos de ejemplo:

**Ejemplo de prueba:**
```
Edad: 35
Ingreso: 5000
Deuda Total: 2000
Ratio Deuda/Ingreso: 0.4
Historial Pagos: 0.95
Días Último Préstamo: 30
Número Préstamos Previos: 2

Resultado:
Riesgo: BAJO
Confianza: 0.92 (92%)
Recomendación: "Cliente con bajo riesgo crediticio"
```

#### 5. **Usar en Producción**

Una vez activado, el modelo se usa automáticamente al:
- Evaluar nuevas solicitudes de préstamo
- Calcular riesgo crediticio
- Generar recomendaciones

---

## 📚 Ejemplos Prácticos Completos

### Ejemplo 1: Crear Variable y Usarla en Plantilla

**Paso 1: Crear Variable**
```
Nombre: resumen_bd
Tabla: clientes
Campo: nombres
Descripción: Resumen de la base de datos
```

**Paso 2: Usar en Plantilla**
```
Asunto: Recordatorio - {{resumen_bd}}

Cuerpo:
Estimado/a {{resumen_bd}},

Su pago de {{monto}} VES vence el {{fecha_vencimiento}}.
```

**Resultado:**
```
Asunto: Recordatorio - Juan Pérez

Cuerpo:
Estimado/a Juan Pérez,

Su pago de 500.00 VES vence el 15/11/2025.
```

### Ejemplo 2: Entrenar Modelo con Fine-tuning

**Paso 1: Calificar 15 conversaciones**
- 10 con 5 estrellas
- 5 con 4 estrellas

**Paso 2: Preparar Datos**
- Sistema selecciona las 15 conversaciones
- Crea archivo de entrenamiento

**Paso 3: Entrenar**
- Modelo Base: gpt-3.5-turbo
- Epochs: 3
- Tiempo estimado: 10-15 minutos

**Paso 4: Activar**
- Modelo entrenado: `ft:gpt-3.5-turbo:empresa:abc123`
- Se activa automáticamente

**Resultado:** El chat ahora responde mejor a preguntas similares a las entrenadas.

### Ejemplo 3: Configurar RAG Completo

**Paso 1: Subir Documentos**
- "Políticas de Cobranza.pdf"
- "FAQ Clientes.docx"
- "Manual de Procedimientos.txt"

**Paso 2: Generar Embeddings**
- 3 documentos procesados
- 12 embeddings generados

**Paso 3: Probar Búsqueda**
```
Pregunta: "¿Cuál es la tasa de interés?"
Resultado: Encuentra información en "Manual de Procedimientos"
```

**Resultado:** El chat ahora puede responder preguntas basadas en tus documentos.

### Ejemplo 4: Sistema Completo de ML Riesgo

**Paso 1: Entrenar con Datos Históricos**
- 1000 préstamos históricos
- Algoritmo: Random Forest
- Accuracy: 87%

**Paso 2: Activar Modelo**
- Modelo activado: "RF_v1.0_2025-11-14"

**Paso 3: Evaluar Nuevo Cliente**
```
Datos Cliente:
- Edad: 30
- Ingreso: 4000
- Deuda: 1500
- Historial: 0.90

Predicción:
- Riesgo: MEDIO
- Confianza: 0.78
- Recomendación: "Aprobar con condiciones"
```

---

## 💡 Consejos y Mejores Prácticas

### Variables Personalizadas
- ✅ Usa nombres descriptivos y consistentes
- ✅ Agrupa variables por tabla
- ✅ Mantén descripciones claras
- ❌ No uses espacios en nombres de variables

### Fine-tuning
- ✅ Califica al menos 20-30 conversaciones de calidad
- ✅ Incluye variedad de preguntas y respuestas
- ✅ Revisa y mejora conversaciones antes de entrenar
- ❌ No entrenes con conversaciones de baja calidad

### RAG
- ✅ Sube documentos actualizados y relevantes
- ✅ Regenera embeddings cuando actualices documentos
- ✅ Organiza documentos por categorías
- ❌ No subas documentos duplicados o obsoletos

### ML Riesgo
- ✅ Entrena con al menos 500-1000 registros históricos
- ✅ Valida métricas antes de activar
- ✅ Prueba con casos reales antes de producción
- ❌ No actives modelos con accuracy < 70%

---

## 🆘 Solución de Problemas

### Variables no se muestran en plantillas
- Verifica que la variable esté **activa**
- Revisa que el nombre esté correcto: `{{nombre_variable}}`
- Confirma que la tabla y campo existan en la BD

### Fine-tuning falla
- Verifica que tengas al menos 10 conversaciones calificadas
- Revisa que las conversaciones tengan calificación ≥ 4
- Confirma que la API key de OpenAI sea válida

### RAG no encuentra documentos
- Verifica que los embeddings estén generados
- Confirma que los documentos estén activos
- Revisa que la pregunta sea clara y específica

### ML Riesgo tiene baja accuracy
- Aumenta el tamaño del dataset de entrenamiento
- Prueba diferentes algoritmos
- Revisa la calidad de los datos de entrada

---

## 📞 Soporte

Para más ayuda, consulta:
- Documentación técnica en el código
- Logs del sistema en la consola del navegador
- Endpoints de API en `/api/v1/ai/training/`

