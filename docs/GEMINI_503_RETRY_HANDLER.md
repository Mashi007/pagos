# Manejo de Errores 503 de Gemini - Reintentos Automáticos

## Problema

El servicio Google Gemini ocasionalmente devuelve errores **503 UNAVAILABLE** cuando está bajo alta demanda:

```json
{
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.",
    "status": "UNAVAILABLE"
  }
}
```

Esto afecta a:
- **Pagos Gmail**: Extracción de datos de comprobantes de pago
- **Cobranza**: Validación de papeletas/informes de depósito
- **Cobros**: Comparación automática de datos del formulario vs imagen del comprobante

## Solución Implementada

### Cambios en `backend/app/services/pagos_gmail/gemini_service.py`

#### 1. Constantes de Configuración
```python
GEMINI_RATE_LIMIT_RETRY_DELAY = 45        # Para 429 rate limit
GEMINI_RATE_LIMIT_MAX_RETRIES = 2         # Max 2 reintentos para 429
GEMINI_SERVER_ERROR_RETRY_DELAY = 15      # Para 503 Server Unavailable
GEMINI_SERVER_ERROR_MAX_RETRIES = 4       # Max 4 reintentos para 503
```

**Justificación del backoff**: 
- 429 (Rate Limit): El servidor especifica cuánto esperar → 2 reintentos
- 503 (High Demand): Esperas variables → 4 reintentos con backoff exponencial (15s + N*5s)
  - Intento 1: 15 segundos
  - Intento 2: 20 segundos
  - Intento 3: 25 segundos
  - Intento 4: 30 segundos

#### 2. Función de Detección de 503
```python
def _is_server_error_503(exc: Exception) -> bool:
    """Detecta errores 503 UNAVAILABLE (ServerError de Gemini por alta demanda)."""
    msg = (getattr(exc, "message", "") or str(exc)) if exc else ""
    return "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg.lower()
```

#### 3. Reintentos en Funciones Críticas

**`extract_payment_data()`** - Extrae datos de correos (fecha_pago, cedula, monto, numero_referencia)
```python
except Exception as e:
    last_error = e
    # Reintentos para 429 (rate limit)
    if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
        delay = _extract_retry_seconds(e)
        logger.warning("[PAGOS_GMAIL] Gemini 429 (cuota), reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_RATE_LIMIT_MAX_RETRIES + 1)
        time.sleep(delay)
    # Reintentos para 503 (server unavailable / high demand)
    elif _is_server_error_503(e) and attempt < GEMINI_SERVER_ERROR_MAX_RETRIES:
        delay = GEMINI_SERVER_ERROR_RETRY_DELAY + (attempt * 5)
        logger.warning("[PAGOS_GMAIL] Gemini 503 (high demand), reintento en %ds (%d/%d)", delay, attempt + 1, GEMINI_SERVER_ERROR_MAX_RETRIES + 1)
        time.sleep(delay)
    else:
        raise
```

**Misma lógica en**:
- `extract_cobranza_from_image()` - Valida papeletas de cobranza
- `compare_form_with_image()` - Compara datos del formulario vs imagen de comprobante
- `check_gemini_available()` - Health check del servicio Gemini

### Comportamiento

| Error | Reintentos | Estrategia | Resultado |
|-------|-----------|-----------|-----------|
| 429 Rate Limit | 2 | Esperar tiempo indicado por servidor | Si persiste: lanza excepción |
| 503 High Demand | 4 | Backoff exponencial (15s, 20s, 25s, 30s) | Si persiste: lanza excepción |
| Otros | 0 | Lanza inmediatamente | Excepción capturada y logueada |

### Logs Generados

**Intento exitoso tras 503**:
```
[COBROS] Gemini 503 (high demand) en comparar, reintento 1/4 en 15s
[COBROS] Gemini OK: coincide_exacto=True ...
```

**503 persiste após 4 intentos**:
```
[COBROS] Gemini 503 (high demand) en comparar, reintento 4/4 en 30s
ERROR - [notif_envio_persistencia] Comparación fallida: 503 UNAVAILABLE
```

## Impacto

### Anterior (Sin Reintentos)
- 503 Error → **Falla inmediata**
- Usuario ve: "Error interno del servidor"
- Reporte requiere **revisión manual**

### Actual (Con Reintentos)
- 503 Error → **Espera inteligente**
- Reintenta hasta 4 veces (máx ~2 minutos)
- Si Gemini se recupera → **Aprobación automática**
- Si persiste tras 4 intentos → **Revisión manual** (último recurso)

## Casos de Uso

### Pagos Gmail
```
Email con comprobante → Gemini extrae fecha/cedula/monto
503 Error → Reintenta 15s después
Si disponible → Guarda en BD automáticamente
```

### Cobranza
```
Papeleta subida → Validar con Gemini
503 Error → Reintenta 20s después
Si disponible → Registra depósito
```

### Cobros - Reporte Público
```
Usuario sube comprobante → Comparar con datos del formulario
503 Error → Reintenta 25s después
Si disponible → Aprueba o rechaza automáticamente
```

## Monitoreo

### Métricas a Vigilar

1. **Frecuencia de 503**
   ```sql
   SELECT COUNT(*) FROM logs WHERE message LIKE '%503 (high demand)%' AND timestamp > NOW() - INTERVAL '1 day';
   ```

2. **Tasa de Recuperación**
   ```sql
   SELECT 
     COUNT(CASE WHEN reintento = 1 THEN 1 END) as recuperados_1,
     COUNT(CASE WHEN reintento = 2 THEN 1 END) as recuperados_2,
     COUNT(CASE WHEN reintento = 3 THEN 1 END) as recuperados_3,
     COUNT(CASE WHEN reintento = 4 THEN 1 END) as recuperados_4,
     COUNT(CASE WHEN reintento > 4 THEN 1 END) as fallos
   FROM gemini_errors;
   ```

### Alertas Recomendadas

- **Alerta ROJA**: > 10 errores 503 en 1 hora
- **Alerta AMARILLA**: Mismo error 503 durante 5+ minutos
- **Escalamiento**: Si persiste > 30 minutos, contactar soporte Gemini

## Testing

### Test Manual - Simular 503

1. Inyectar error en logs:
```python
# Temporalmente en extract_payment_data()
if attempt == 0:
    raise Exception("503 UNAVAILABLE: This model is currently experiencing high demand")
```

2. Ejecutar: `POST /api/v1/pagos-gmail/webhook`
3. Verificar logs: Debe ver 4 reintentos con backoff

### Test de Carga

```bash
# Generar múltiples requests simultáneamente
for i in {1..20}; do
  curl -X POST "http://localhost:8000/api/v1/cobros/pagos-reportados/1191/comparar" \
    -H "Content-Type: application/json" \
    -d '{"imagen": "...base64..."}' &
done
```

## Referencias

- [Google Gemini API - Error Handling](https://ai.google.dev/tutorials/python_quickstart)
- [HTTP 503 Service Unavailable](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503)
- [Exponential Backoff Pattern](https://en.wikipedia.org/wiki/Exponential_backoff)

## Próximos Pasos (Futuro)

- [ ] Implementar circuit breaker si 503 persiste > 30 minutos
- [ ] Usar Redis para caché de respuestas de Gemini (evitar requests duplicados)
- [ ] Webhook alternativo con proveedor de IA (OpenAI, Anthropic) como fallback
