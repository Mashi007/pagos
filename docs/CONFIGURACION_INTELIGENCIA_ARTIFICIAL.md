# 🤖 Configuración de Inteligencia Artificial

## 📋 **DESCRIPCIÓN**

Módulo de configuración de Inteligencia Artificial integrado en la sección de Configuración del sistema RapiCredit.

---

## 🎯 **FUNCIONALIDADES DE IA**

### **✅ 1. SCORING CREDITICIO CON IA**
**Descripción:** Analiza automáticamente la capacidad de pago de los clientes
**Funciones:**
- ✅ Evaluación automática de riesgo crediticio
- ✅ Análisis de capacidad de pago
- ✅ Recomendaciones de monto y plazo
- ✅ Scoring basado en datos históricos
- ✅ Predicción de probabilidad de pago

### **✅ 2. PREDICCIÓN DE MORA**
**Descripción:** Predice la probabilidad de mora usando machine learning
**Funciones:**
- ✅ Modelo predictivo de mora
- ✅ Análisis de patrones de pago
- ✅ Alertas tempranas de riesgo
- ✅ Segmentación de clientes por riesgo
- ✅ Optimización de estrategias de cobranza

### **✅ 3. CHATBOT INTELIGENTE**
**Descripción:** Asistente virtual para atención al cliente
**Funciones:**
- ✅ Respuestas automáticas a consultas comunes
- ✅ Asistencia 24/7
- ✅ Escalamiento a agentes humanos
- ✅ Análisis de sentimientos
- ✅ Mejora continua del conocimiento

---

## ⚙️ **CONFIGURACIÓN DE OPENAI**

### **🔑 OpenAI API Key**
```
Formato: sk-[48 caracteres alfanuméricos]
Ejemplo: sk-1234567890abcdef1234567890abcdef1234567890abcdef
Obtener en: https://platform.openai.com/api-keys
```

### **🧠 Modelos Disponibles:**

#### **1. GPT-3.5 Turbo (Recomendado)**
- ✅ **Costo:** Más económico
- ✅ **Velocidad:** Rápido
- ✅ **Precisión:** Buena para la mayoría de casos
- ✅ **Uso recomendado:** Scoring crediticio, chatbot básico

#### **2. GPT-4 (Más potente)**
- ✅ **Costo:** Más caro
- ✅ **Velocidad:** Moderado
- ✅ **Precisión:** Excelente
- ✅ **Uso recomendado:** Análisis complejos, predicciones críticas

#### **3. GPT-4 Turbo (Más rápido)**
- ✅ **Costo:** Intermedio
- ✅ **Velocidad:** Muy rápido
- ✅ **Precisión:** Excelente
- ✅ **Uso recomendado:** Aplicaciones en tiempo real

---

## 🖥️ **INTERFAZ DE CONFIGURACIÓN**

### **Sección OpenAI Configuration:**
```
┌─────────────────────────────────────────┐
│ ⚙️ OpenAI Configuration                 │
├─────────────────────────────────────────┤
│ OpenAI API Key                          │
│ [••••••••••••••••••••••••••••••••••] 👁️ │
│ Obtén tu API Key en:                    │
│ https://platform.openai.com/api-keys    │
│                                         │
│ Modelo de OpenAI                        │
│ [GPT-3.5 Turbo (Recomendado) ▼]        │
│ GPT-3.5 Turbo es más económico,        │
│ GPT-4 es más preciso                    │
└─────────────────────────────────────────┘
```

### **Sección Funcionalidades de IA:**
```
┌─────────────────────────────────────────┐
│ 🧠 Funcionalidades de IA                │
├─────────────────────────────────────────┤
│ Scoring Crediticio con IA               │
│ Analiza automáticamente la capacidad    │
│ de pago de los clientes                 │
│                                         │
│ Predicción de Mora                      │
│ Predice la probabilidad de mora usando  │
│ machine learning                         │
│                                         │
│ Chatbot Inteligente                     │
│ Asistente virtual para atención al      │
│ cliente                                  │
└─────────────────────────────────────────┘
```

### **Sección Estado de la Configuración:**
```
┌─────────────────────────────────────────┐
│ ✅ Estado de la Configuración           │
├─────────────────────────────────────────┤
│ API Key configurada:    ✅ Configurada  │
│ Modelo seleccionado:    GPT-3.5 Turbo   │
│ Funcionalidades activas:                │
│ Scoring, Predicción, Chatbot            │
└─────────────────────────────────────────┘
```

---

## 🔧 **CONFIGURACIÓN EN EL BACKEND**

### **Variables de Entorno:**
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo

# AI Features
AI_SCORING_ENABLED=true
AI_PREDICTION_ENABLED=true
AI_CHATBOT_ENABLED=true
```

### **Configuración en Base de Datos:**
```sql
-- Configuraciones de IA en la tabla configuracion_sistema
INSERT INTO configuracion_sistema (categoria, subcategoria, clave, valor, descripcion) VALUES
('AI', 'OPENAI', 'OPENAI_API_KEY', '', 'Token de API de OpenAI'),
('AI', 'OPENAI', 'OPENAI_MODEL', 'gpt-3.5-turbo', 'Modelo de OpenAI'),
('AI', 'FEATURES', 'AI_SCORING_ENABLED', 'true', 'Habilitar scoring crediticio'),
('AI', 'FEATURES', 'AI_PREDICTION_ENABLED', 'true', 'Habilitar predicción de mora'),
('AI', 'FEATURES', 'AI_CHATBOT_ENABLED', 'true', 'Habilitar chatbot');
```

---

## 📡 **ENDPOINTS DEL BACKEND**

### **GET /api/v1/configuracion/ia**
Obtener configuración de IA
```json
Response:
{
  "titulo": "🤖 CONFIGURACIÓN DE INTELIGENCIA ARTIFICIAL",
  "openai_config": {
    "api_key_configured": true,
    "model": "gpt-3.5-turbo"
  },
  "features": {
    "scoring": {
      "habilitado": true,
      "descripcion": "Scoring crediticio con IA"
    },
    "prediction": {
      "habilitado": true,
      "descripcion": "Predicción de mora"
    },
    "chatbot": {
      "habilitado": true,
      "configurado": true,
      "descripcion": "Chatbot inteligente"
    }
  }
}
```

### **PUT /api/v1/configuracion/ia**
Actualizar configuración de IA
```json
Body:
{
  "openai_api_key": "sk-...",
  "openai_model": "gpt-4",
  "ai_scoring_enabled": true,
  "ai_prediction_enabled": true,
  "ai_chatbot_enabled": false
}
```

---

## 🎯 **CASOS DE USO**

### **Caso 1: Configuración Inicial**
```
Situación: Nuevo sistema, configurar IA por primera vez
Acción:
1. Obtener API Key de OpenAI
2. Configurar modelo (recomendado: GPT-3.5 Turbo)
3. Habilitar funcionalidades necesarias
4. Probar configuración
```

### **Caso 2: Migración a GPT-4**
```
Situación: Mejorar precisión de análisis
Acción:
1. Cambiar modelo a GPT-4
2. Verificar que API Key tenga permisos
3. Monitorear costos
4. Evaluar mejora en resultados
```

### **Caso 3: Deshabilitar Funcionalidad**
```
Situación: Mantenimiento o problemas con IA
Acción:
1. Deshabilitar funcionalidad específica
2. Mantener otras funcionalidades activas
3. Notificar a usuarios
4. Rehabilitar cuando se resuelva
```

---

## 💰 **CONSIDERACIONES DE COSTO**

### **OpenAI Pricing (Octubre 2025):**
```
GPT-3.5 Turbo:
- Input: $0.0015 / 1K tokens
- Output: $0.002 / 1K tokens

GPT-4:
- Input: $0.03 / 1K tokens
- Output: $0.06 / 1K tokens

GPT-4 Turbo:
- Input: $0.01 / 1K tokens
- Output: $0.03 / 1K tokens
```

### **Estimación de Uso:**
```
Scoring Crediticio:
- ~500 tokens por análisis
- Costo: $0.001 por análisis (GPT-3.5)

Predicción de Mora:
- ~300 tokens por predicción
- Costo: $0.0006 por predicción (GPT-3.5)

Chatbot:
- ~200 tokens por mensaje
- Costo: $0.0004 por mensaje (GPT-3.5)
```

---

## 🔐 **SEGURIDAD**

### **API Key:**
- ✅ Almacenada encriptada en base de datos
- ✅ No se muestra en logs
- ✅ Acceso solo a administradores
- ✅ Rotación recomendada cada 90 días

### **Datos:**
- ✅ Información de clientes no se envía a OpenAI
- ✅ Solo se envían datos anonimizados
- ✅ Cumplimiento con políticas de privacidad
- ✅ Audit trail de todas las consultas

---

## 📊 **MONITOREO Y MÉTRICAS**

### **KPIs de IA:**
- 📈 **Precisión de Scoring:** % de predicciones correctas
- 📈 **Tiempo de Respuesta:** Latencia promedio
- 📈 **Uso de Tokens:** Consumo mensual
- 📈 **Satisfacción de Chatbot:** Rating de usuarios
- 📈 **Reducción de Mora:** % de mejora vs. sistema anterior

### **Alertas:**
- ⚠️ API Key expirada o inválida
- ⚠️ Límite de tokens alcanzado
- ⚠️ Errores de conectividad
- ⚠️ Precisión por debajo del umbral

---

## 🚀 **ROADMAP DE MEJORAS**

### **Fase 2:**
- [ ] Análisis de sentimientos en conversaciones
- [ ] Predicción de abandono de clientes
- [ ] Optimización automática de tasas
- [ ] Generación de reportes con IA

### **Fase 3:**
- [ ] Modelos personalizados entrenados
- [ ] Integración con más proveedores de IA
- [ ] Análisis de imágenes de documentos
- [ ] Predicción de tendencias de mercado

---

## 🆘 **TROUBLESHOOTING**

### **Error: "API Key inválida"**
- ✅ Verificar formato: sk-[48 caracteres]
- ✅ Confirmar que la key esté activa
- ✅ Verificar límites de uso
- ✅ Revisar permisos de la key

### **Error: "Modelo no disponible"**
- ✅ Verificar que el modelo esté disponible
- ✅ Confirmar permisos de acceso al modelo
- ✅ Revisar configuración de región

### **Error: "Límite de tokens alcanzado"**
- ✅ Revisar límites de la cuenta
- ✅ Optimizar prompts para usar menos tokens
- ✅ Considerar upgrade de plan
- ✅ Implementar cache de respuestas

---

## 📚 **RECURSOS ADICIONALES**

### **Documentación OpenAI:**
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Modelos disponibles](https://platform.openai.com/docs/models)
- [Guía de mejores prácticas](https://platform.openai.com/docs/guides/prompt-engineering)

### **Ejemplos de Prompts:**
```
Scoring Crediticio:
"Analiza la capacidad de pago de un cliente con ingresos de ${ingresos}, gastos de ${gastos}, historial crediticio de ${score} y {contexto_adicional}. Proporciona un score de 0-100 y recomendación de monto máximo."

Predicción de Mora:
"Basándote en el historial de pagos {historial}, comportamiento de gastos {gastos} y factores externos {contexto}, predice la probabilidad de mora en los próximos 3 meses. Escala de 0-100%."
```

---

## ✅ **CHECKLIST DE IMPLEMENTACIÓN**

### **Configuración Inicial:**
- [ ] Obtener API Key de OpenAI
- [ ] Configurar modelo apropiado
- [ ] Habilitar funcionalidades necesarias
- [ ] Probar configuración
- [ ] Documentar configuración

### **Monitoreo Continuo:**
- [ ] Revisar métricas semanalmente
- [ ] Monitorear costos mensualmente
- [ ] Evaluar precisión de predicciones
- [ ] Actualizar prompts según necesidad
- [ ] Mantener documentación actualizada

**Módulo de IA completamente configurado y listo para producción** ✅
