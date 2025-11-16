# 📋 Cumplimiento con Políticas de Meta WhatsApp Business API

## ✅ Mejoras Implementadas

### 1. **Rate Limiting** ✅
- **Implementado**: Sistema de rate limiting que respeta los límites de Meta
- **Límites configurados**:
  - 1000 mensajes/día (por defecto, según tier de cuenta)
  - 80 mensajes/segundo (por defecto)
- **Funcionamiento**: Verifica límites ANTES de enviar cada mensaje
- **Nota**: Actualmente usa memoria compartida. Para producción distribuida, se recomienda usar Redis.

### 2. **Manejo de Errores Específicos de Meta** ✅
- **Códigos manejados**:
  - `429` (Rate Limit): Detecta y maneja rate limits de Meta
  - `403` (Forbidden): Políticas violadas, token inválido
  - `400` (Bad Request): Validación fallida
  - `401` (Unauthorized): Token inválido o expirado
  - `500+` (Server Error): Errores temporales del servidor de Meta
- **Respuestas estructuradas**: Cada error incluye código de error, mensaje y si es retryable

### 3. **Retry con Backoff Exponencial** ✅
- **Implementado**: Reintentos automáticos para errores temporales
- **Configuración**:
  - Máximo 3 reintentos
  - Backoff exponencial: 2^intento segundos (2s, 4s, 8s)
  - Respeta `retry_after` de Meta cuando está disponible
- **Solo reintenta**: Errores 429 y 500+ (errores temporales)

### 4. **Timeout Configurable** ✅
- **Implementado**: Timeout de 30 segundos por defecto para requests HTTP
- **Configurable**: Se puede ajustar según necesidades
- **Manejo**: Detecta timeouts y los registra apropiadamente

### 5. **Logging de Compliance** ✅
- **Implementado**: Logging estructurado con etiqueta `[COMPLIANCE]`
- **Registra**:
  - Envíos exitosos (con ID de mensaje y tiempo)
  - Errores (con código y tipo)
  - Uso de templates vs mensajes libres
  - Timeouts y excepciones
- **Formato**: Incluye timestamps, IDs de mensaje, tiempos de ejecución

### 6. **Validación de Mensajes** ✅
- **Longitud**: Valida que mensajes no excedan 4096 caracteres (límite de Meta)
- **Números de teléfono**: Valida formato internacional
- **Configuración**: Verifica credenciales antes de enviar

## ⚠️ Mejoras Pendientes (Recomendadas)

### 1. **Opt-in/Opt-out (Consentimiento)** ⚠️
- **Estado**: No implementado
- **Requerido por Meta**: Sí, es obligatorio obtener consentimiento antes de enviar
- **Recomendación**: 
  - Agregar campo `whatsapp_consent` en tabla de clientes
  - Registrar fecha y método de consentimiento
  - Verificar consentimiento antes de enviar
  - Implementar endpoint para opt-out

### 2. **Validación de Templates Aprobados** ⚠️
- **Estado**: No implementado
- **Requerido por Meta**: Sí, solo se pueden usar templates aprobados
- **Recomendación**:
  - Consultar API de Meta para verificar templates aprobados
  - Validar template antes de enviar
  - Cachear lista de templates aprobados

### 3. **Ventana de 24 Horas** ⚠️
- **Estado**: No implementado
- **Requerido por Meta**: Sí, mensajes libres solo dentro de 24h desde último mensaje del usuario
- **Recomendación**:
  - Registrar última interacción del usuario
  - Verificar ventana antes de enviar mensaje libre
  - Forzar uso de template si ventana expiró

### 4. **Webhooks de Meta** ⚠️
- **Estado**: No implementado
- **Requerido por Meta**: Recomendado para recibir actualizaciones
- **Recomendación**:
  - Implementar endpoint para recibir webhooks
  - Verificar `webhook_verify_token`
  - Procesar actualizaciones (mensajes recibidos, entregados, leídos, errores)
  - Actualizar estado de notificaciones según webhooks

### 5. **Rate Limiting Distribuido** ⚠️
- **Estado**: Implementado en memoria (no distribuido)
- **Requerido para**: Producción con múltiples instancias
- **Recomendación**: Migrar a Redis para rate limiting compartido

## 📊 Políticas de Meta Cumplidas

### ✅ Políticas Técnicas
- [x] Rate limiting (1000/día, 80/segundo)
- [x] Manejo de errores específicos
- [x] Retry con backoff exponencial
- [x] Timeout configurable
- [x] Validación de longitud de mensajes
- [x] Validación de números de teléfono
- [x] Logging estructurado

### ⚠️ Políticas de Negocio (Pendientes)
- [ ] Opt-in/Opt-out (consentimiento)
- [ ] Validación de templates aprobados
- [ ] Manejo de ventana de 24 horas
- [ ] Webhooks para actualizaciones

### ✅ Políticas de Configuración
- [x] Configuración desde base de datos
- [x] Modo de pruebas
- [x] Validación de credenciales
- [x] Test de conexión

## 🔍 Códigos de Error Implementados

| Código | Descripción | Retryable |
|--------|-------------|-----------|
| `RATE_LIMIT_DAILY` | Límite diario alcanzado | No |
| `RATE_LIMIT_SECOND` | Límite por segundo alcanzado | No |
| `META_RATE_LIMIT` | Rate limit de Meta (429) | Sí |
| `META_FORBIDDEN` | Acceso prohibido (403) | No |
| `META_BAD_REQUEST` | Solicitud inválida (400) | No |
| `META_UNAUTHORIZED` | Token inválido (401) | No |
| `META_SERVER_ERROR` | Error del servidor (500+) | Sí |
| `CONFIG_MISSING` | Credenciales no configuradas | No |
| `INVALID_PHONE` | Número de teléfono inválido | No |
| `MESSAGE_TOO_LONG` | Mensaje excede 4096 caracteres | No |
| `TIMEOUT` | Timeout en request | Sí |
| `EXCEPTION` | Excepción no manejada | Depende |

## 📝 Notas Importantes

1. **Rate Limiting en Memoria**: El sistema actual usa memoria compartida. Para producción con múltiples instancias, se recomienda migrar a Redis.

2. **Templates**: Actualmente no se valida si un template está aprobado. Se recomienda implementar validación antes de usar templates.

3. **Consentimiento**: Meta requiere consentimiento explícito antes de enviar mensajes. Esto debe implementarse a nivel de aplicación.

4. **Ventana de 24 Horas**: Los mensajes libres (sin template) solo se pueden enviar dentro de 24 horas desde el último mensaje del usuario. Fuera de esta ventana, se debe usar un template aprobado.

5. **Webhooks**: Meta envía webhooks con actualizaciones de estado. Se recomienda implementar endpoints para recibir y procesar estos webhooks.

## 🚀 Próximos Pasos Recomendados

1. **Implementar Opt-in/Opt-out**:
   - Agregar campo en tabla de clientes
   - Verificar antes de enviar
   - Endpoint para gestionar consentimiento

2. **Validar Templates**:
   - Consultar API de Meta para templates aprobados
   - Cachear resultados
   - Validar antes de enviar

3. **Implementar Webhooks**:
   - Endpoint para recibir webhooks
   - Verificar token
   - Actualizar estado de notificaciones

4. **Migrar Rate Limiting a Redis**:
   - Para producción distribuida
   - Mejor escalabilidad

5. **Manejar Ventana de 24 Horas**:
   - Registrar última interacción
   - Verificar antes de enviar mensaje libre
   - Forzar template si ventana expiró

