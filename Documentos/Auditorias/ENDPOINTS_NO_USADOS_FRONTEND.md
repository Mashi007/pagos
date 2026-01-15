# 📋 DOCUMENTACIÓN: ENDPOINTS NO USADOS EN FRONTEND

**Fecha:** 2026-01-15  
**Propósito:** Documentar endpoints del backend que no son utilizados directamente por el frontend

---

## 📊 RESUMEN EJECUTIVO

- **Total de endpoints auditados:** 314
- **Endpoints no detectados como usados:** ~241
- **Categorías:** Administrativos, Monitoreo, Integración, Obsoletos

---

## 🔍 ANÁLISIS POR CATEGORÍA

### 1. Endpoints Administrativos (Uso Interno)

Estos endpoints están diseñados para uso administrativo y no requieren interfaz frontend:

#### **Configuración del Sistema**
- `GET /api/v1/configuracion/sistema/completa` - Configuración completa del sistema
- `GET /api/v1/configuracion/sistema/{clave}` - Obtener configuración específica
- `PUT /api/v1/configuracion/sistema/{clave}` - Actualizar configuración
- `DELETE /api/v1/configuracion/sistema/{clave}` - Eliminar configuración
- `GET /api/v1/configuracion/sistema/categoria/{categoria}` - Configuración por categoría
- `GET /api/v1/configuracion/sistema/estadisticas` - Estadísticas de configuración

**Propósito:** Gestión administrativa del sistema, configuración avanzada

#### **AI Training y Machine Learning**
- `GET /api/v1/ai/training/conversaciones` - Listar conversaciones de entrenamiento
- `POST /api/v1/ai/training/conversaciones` - Crear conversación de entrenamiento
- `PUT /api/v1/ai/training/conversaciones/{id}` - Actualizar conversación
- `POST /api/v1/ai/training/conversaciones/mejorar` - Mejorar conversaciones
- `POST /api/v1/ai/training/conversaciones/{id}/calificar` - Calificar conversación
- `POST /api/v1/ai/training/fine-tuning/preparar` - Preparar datos para fine-tuning
- `POST /api/v1/ai/training/fine-tuning/iniciar` - Iniciar fine-tuning
- `GET /api/v1/ai/training/fine-tuning/jobs` - Listar jobs de fine-tuning
- `GET /api/v1/ai/training/fine-tuning/jobs/{id}` - Estado de job
- `POST /api/v1/ai/training/fine-tuning/jobs/{id}/cancelar` - Cancelar job
- `DELETE /api/v1/ai/training/fine-tuning/jobs/{id}` - Eliminar job
- `DELETE /api/v1/ai/training/fine-tuning/jobs` - Eliminar todos los jobs
- `POST /api/v1/ai/training/fine-tuning/activar` - Activar modelo fine-tuned
- `GET /api/v1/ai/training/rag/estado` - Estado de embeddings
- `POST /api/v1/ai/training/rag/generar-embeddings` - Generar embeddings
- `POST /api/v1/ai/training/rag/buscar` - Búsqueda semántica
- `POST /api/v1/ai/training/rag/documentos/{id}/embeddings` - Actualizar embeddings
- `GET /api/v1/ai/training/ml-riesgo/modelos` - Listar modelos de riesgo
- `GET /api/v1/ai/training/ml-riesgo/modelo-activo` - Modelo activo
- `POST /api/v1/ai/training/ml-riesgo/entrenar` - Entrenar modelo
- `GET /api/v1/ai/training/ml-riesgo/jobs/{id}` - Estado de entrenamiento
- `POST /api/v1/ai/training/ml-riesgo/activar` - Activar modelo
- `POST /api/v1/ai/training/ml-riesgo/predecir` - Predecir riesgo
- `POST /api/v1/ai/training/ml-impago/entrenar` - Entrenar modelo de impago
- `POST /api/v1/ai/training/ml-impago/corregir-activos` - Corregir modelos activos
- `POST /api/v1/ai/training/ml-impago/activar` - Activar modelo de impago
- `GET /api/v1/ai/training/ml-impago/calcular-detalle-cedula/{cedula}` - Detalle por cédula
- `GET /api/v1/ai/training/ml-impago/calcular-detalle/{prestamo_id}` - Detalle por préstamo
- `POST /api/v1/ai/training/ml-impago/predecir` - Predecir impago
- `DELETE /api/v1/ai/training/ml-impago/modelos/{id}` - Eliminar modelo
- `GET /api/v1/ai/training/ml-impago/modelos` - Listar modelos
- `GET /api/v1/ai/training/verificar-bd` - Verificar base de datos
- `GET /api/v1/ai/training/metricas` - Métricas de entrenamiento

**Propósito:** Gestión avanzada de modelos de ML y entrenamiento de AI

#### **Configuración de AI**
- `GET /api/v1/configuracion/ai/configuracion` - Configuración de AI
- `PUT /api/v1/configuracion/ai/configuracion` - Actualizar configuración de AI
- `GET /api/v1/configuracion/ai/documentos` - Listar documentos AI
- `POST /api/v1/configuracion/ai/documentos` - Crear documento AI
- `POST /api/v1/configuracion/ai/documentos/{id}/procesar` - Procesar documento
- `DELETE /api/v1/configuracion/ai/documentos/{id}` - Eliminar documento
- `GET /api/v1/configuracion/ai/documentos/{id}` - Obtener documento
- `PUT /api/v1/configuracion/ai/documentos/{id}` - Actualizar documento
- `PATCH /api/v1/configuracion/ai/documentos/{id}/activar` - Activar documento
- `GET /api/v1/configuracion/ai/prompt/variables` - Variables de prompt
- `POST /api/v1/configuracion/ai/prompt/variables` - Crear variable
- `PUT /api/v1/configuracion/ai/prompt/variables/{id}` - Actualizar variable
- `DELETE /api/v1/configuracion/ai/prompt/variables/{id}` - Eliminar variable
- `GET /api/v1/configuracion/ai/prompt` - Obtener prompt
- `PUT /api/v1/configuracion/ai/prompt` - Actualizar prompt
- `GET /api/v1/configuracion/ai/prompt/default` - Prompt por defecto
- `GET /api/v1/configuracion/ai/metricas` - Métricas de AI
- `GET /api/v1/configuracion/ai/metricas/chat` - Métricas de chat
- `GET /api/v1/configuracion/ai/tablas-campos` - Tablas y campos disponibles
- `POST /api/v1/configuracion/ai/probar` - Probar configuración
- `POST /api/v1/configuracion/ai/chat` - Chat con AI

**Propósito:** Configuración avanzada de AI y prompts

### 2. Endpoints de Monitoreo y Health Checks

Estos endpoints son para monitoreo del sistema y no requieren interfaz frontend:

#### **Health Checks**
- `GET /api/v1/health` - Health check básico
- `GET /api/v1/health/ready` - Health check de readiness
- `GET /api/v1/health/live` - Health check de liveness
- `GET /api/v1/health/render` - Health check específico para Render
- `GET /api/v1/cors-debug` - Debug de CORS

#### **Monitoreo de Performance**
- `GET /api/v1/performance/summary` - Resumen de performance
- `GET /api/v1/performance/slow` - Queries lentas
- `GET /api/v1/performance/endpoint/{method}/{path}` - Performance de endpoint específico
- `GET /api/v1/performance/recent` - Performance reciente
- `GET /api/v1/monitoring/queries/slow` - Queries lentas
- `GET /api/v1/monitoring/queries/stats/{query_name}` - Estadísticas de query
- `GET /api/v1/monitoring/queries/summary` - Resumen de queries
- `GET /api/v1/monitoring/alerts/recent` - Alertas recientes
- `GET /api/v1/monitoring/dashboard/performance` - Dashboard de performance
- `GET /api/v1/monitoring/database/info` - Información de BD
- `GET /api/v1/monitoring/database/tables/{table_name}/columns` - Columnas de tabla
- `GET /api/v1/monitoring/database/tables/{table_name}/indexes` - Índices de tabla

#### **Cache y Base de Datos**
- `GET /api/v1/cache/status` - Estado del cache
- `GET /api/v1/database/indexes` - Listar índices
- `GET /api/v1/database/indexes/performance` - Performance de índices
- `POST /api/v1/database/indexes/create` - Crear índice
- `GET /api/v1/database/tabla-documentos-ai` - Información de tabla documentos_ai
- `GET /api/v1/processes/pending` - Procesos pendientes
- `GET /api/v1/files/duplicates` - Archivos duplicados

**Propósito:** Monitoreo del sistema, diagnóstico y mantenimiento

### 3. Endpoints de Integración Externa

Estos endpoints son para integraciones externas y webhooks:

#### **Webhooks**
- `GET /api/v1/whatsapp/webhook` - Webhook de WhatsApp (verificación)
- `POST /api/v1/whatsapp/webhook` - Webhook de WhatsApp (mensajes)
- `GET /api/v1/whatsapp/webhook/info` - Información del webhook

**Propósito:** Integración con servicios externos (WhatsApp, etc.)

### 4. Endpoints de Auditoría y Reportes Avanzados

Estos endpoints proporcionan información detallada para auditoría:

#### **Auditoría**
- `GET /api/v1/auditoria` - Listar auditorías
- `GET /api/v1/auditoria/exportar` - Exportar auditorías
- `GET /api/v1/auditoria/stats` - Estadísticas de auditoría
- `POST /api/v1/auditoria/registrar` - Registrar auditoría
- `GET /api/v1/prestamos/auditoria/{prestamo_id}` - Auditoría de préstamo
- `GET /api/v1/pagos/auditoria/{pago_id}` - Auditoría de pago

#### **Reportes Avanzados**
- `GET /api/v1/reportes/exportar/cartera` - Exportar reporte de cartera
- `GET /api/v1/reportes/dashboard/resumen` - Resumen del dashboard
- `GET /api/v1/reportes/cliente/{cedula}/pendientes.pdf` - PDF de pendientes
- `GET /api/v1/reportes/diferencias-abonos` - Diferencias de abonos
- `PUT /api/v1/reportes/diferencias-abonos/{prestamo_id}/ajustar` - Ajustar diferencia
- `PUT /api/v1/reportes/diferencias-abonos/actualizar-valor-imagen` - Actualizar valor de imagen

**Propósito:** Auditoría detallada y reportes avanzados

### 5. Endpoints de Notificaciones Automáticas

Estos endpoints gestionan notificaciones automáticas:

#### **Notificaciones Automáticas**
- `POST /api/v1/notificaciones/automaticas/procesar` - Procesar notificaciones automáticas
- `POST /api/v1/notificaciones-previas/calcular` - Calcular notificaciones previas
- `POST /api/v1/notificaciones-retrasadas/calcular` - Calcular notificaciones retrasadas
- `POST /api/v1/notificaciones-prejudicial/calcular` - Calcular notificaciones prejudiciales
- `POST /api/v1/cobranzas/notificaciones/atrasos` - Procesar notificaciones de atrasos

**Propósito:** Procesamiento automático de notificaciones

### 6. Endpoints de Scheduler y Tareas Programadas

#### **Scheduler**
- `GET /api/v1/scheduler/configuracion` - Configuración del scheduler
- `PUT /api/v1/scheduler/configuracion` - Actualizar configuración
- `GET /api/v1/scheduler/logs` - Logs del scheduler
- `POST /api/v1/scheduler/ejecutar-manual` - Ejecutar manualmente
- `GET /api/v1/scheduler/estado` - Estado del scheduler
- `GET /api/v1/scheduler/tareas` - Listar tareas
- `GET /api/v1/scheduler/verificacion-completa` - Verificación completa

**Propósito:** Gestión de tareas programadas

### 7. Endpoints de Validadores

#### **Validadores**
- `GET /api/v1/validadores/configuracion-validadores` - Configuración de validadores
- `POST /api/v1/validadores/probar-validador` - Probar validador
- `POST /api/v1/validadores/validar-campo` - Validar campo

**Propósito:** Validación de datos

### 8. Endpoints de Configuración de Email y WhatsApp

#### **Email**
- `GET /api/v1/configuracion/email/configuracion` - Configuración de email
- `PUT /api/v1/configuracion/email/configuracion` - Actualizar configuración
- `GET /api/v1/configuracion/email/estado` - Estado de email
- `POST /api/v1/configuracion/email/probar` - Probar email
- `GET /api/v1/configuracion/notificaciones/envios` - Configuración de envíos
- `PUT /api/v1/configuracion/notificaciones/envios` - Actualizar envíos

#### **WhatsApp**
- `GET /api/v1/configuracion/whatsapp/configuracion` - Configuración de WhatsApp
- `PUT /api/v1/configuracion/whatsapp/configuracion` - Actualizar configuración
- `POST /api/v1/configuracion/whatsapp/probar` - Probar WhatsApp
- `GET /api/v1/configuracion/whatsapp/test-completo` - Test completo

**Propósito:** Configuración de canales de comunicación

---

## ✅ RECOMENDACIONES

### Endpoints que DEBEN mantenerse (Administrativos/Monitoreo)

✅ **Mantener todos los endpoints de:**
- Health checks y monitoreo
- Configuración del sistema
- AI Training y ML
- Auditoría
- Webhooks
- Scheduler

**Razón:** Son esenciales para el funcionamiento del sistema y gestión administrativa

### Endpoints que PODRÍAN documentarse mejor

⚠️ **Mejorar documentación de:**
- Endpoints de configuración avanzada
- Endpoints de AI Training
- Endpoints de monitoreo

**Razón:** Facilitar uso por administradores y desarrolladores

### Endpoints que PODRÍAN deprecarse (Revisar)

❓ **Revisar si son necesarios:**
- Algunos endpoints de reportes muy específicos
- Endpoints de diagnóstico muy detallados

**Razón:** Reducir superficie de API si no se usan

---

## 📝 CONCLUSIÓN

La mayoría de los endpoints "no usados" en frontend son **intencionalmente administrativos o de monitoreo**. Esto es correcto y esperado:

- ✅ **Separación de responsabilidades:** Frontend para usuarios finales, endpoints administrativos para gestión
- ✅ **Seguridad:** Endpoints administrativos no expuestos en frontend público
- ✅ **Monitoreo:** Health checks y métricas para sistemas de monitoreo externos

**Recomendación:** Mantener estos endpoints y mejorar su documentación en lugar de eliminarlos.

---

**Última actualización:** 2026-01-15
