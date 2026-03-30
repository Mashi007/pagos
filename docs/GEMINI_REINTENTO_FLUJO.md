# Flujo Completo: Reintentos de Gemini y Actualización de Observaciones

## Respuesta a la Pregunta: "¿Cuando reintenta, vuelve a escanear y actualiza observación?"

**RESPUESTA: SÍ, siempre.** El sistema:
1. ✅ Reintenta automáticamente (hasta 4 veces con backoff exponencial)
2. ✅ Si se recupera → Escanea la imagen Y actualiza observación
3. ✅ Si falla tras reintentos → Guarda observación de error y envía a revisión manual

---

## Flujo Completo (Antes de Cambios)

```
[Usuario envía comprobante]
         ↓
[POST /enviar-reporte]
         ↓
[Se crea PagoReportado estado='pendiente']
         ↓
[Gemini: compare_form_with_image()]
         ├─ Reintento 1 (15s): 503 error
         ├─ Reintento 2 (20s): 503 error
         ├─ Reintento 3 (25s): 503 error
         ├─ Reintento 4 (30s): 503 error
         └─ Lanza Exception ❌

[Exception capturada en try-except del endpoint]
         ↓
[❌ PROBLEMA: db.rollback() - TODO SE PIERDE]
         ├─ PagoReportado no se actualiza
         ├─ Observación no se guarda
         └─ Usuario ve error en frontend

[Usuario nunca ve qué pasó]
```

---

## Flujo MEJORADO (Después de Cambios)

### Escenario A: Gemini SE RECUPERA en reintento

```
[Usuario envía comprobante]
         ↓
[POST /enviar-reporte]
         ↓
[Se crea PagoReportado estado='pendiente']
         ↓
[Gemini: compare_form_with_image()]
         ├─ Reintento 1 (15s): 503 error
         │
         ├─ Reintento 2 (20s): ✅ DISPONIBLE
         │   └─ Escanea comprobante
         │   └─ Retorna coincide_exacto=True
         │
         ├─ Logging: "[COBROS_PUBLIC] Gemini OK tras reintento 2"
         │
         └─ Continúa con resultado exitoso

[tr.gemini_coincide_exacto = "true"]
[pr.gemini_comentario = "coincide exactamente"]
[pr.estado = "aprobado"]
         ↓
[db.commit()] ✅ Se guarda todo
         ↓
[Se genera recibo PDF]
[Se envía por correo]
         ↓
[Usuario recibe: "Tu reporte fue aprobado automáticamente"]
```

### Escenario B: Gemini FALLA tras 4 reintentos (NUEVO MANEJO)

```
[Usuario envía comprobante]
         ↓
[POST /enviar-reporte]
         ↓
[Se crea PagoReportado estado='pendiente']
         ↓
[try: Gemini: compare_form_with_image()]
         ├─ Reintento 1 (15s): 503 error
         ├─ Reintento 2 (20s): 503 error
         ├─ Reintento 3 (25s): 503 error
         ├─ Reintento 4 (30s): 503 error
         └─ Lanza Exception "503 UNAVAILABLE"

[except Exception as gemini_err:] ✅ CAPTURADO
         ↓
[Logging: "[COBROS_PUBLIC] Gemini error tras reintentos, enviando a revisión manual"]
         ↓
[pr.gemini_coincide_exacto = "error"]
[pr.gemini_comentario = "Error Gemini (reintentado): 503 UNAVAILABLE..."]
[pr.estado = "en_revision"] ← ⚠️ REVISIÓN MANUAL
[coincide = False] ← Seguridad: no aprobar si hay error
         ↓
[db.commit()] ✅ Se guarda TODO
         ├─ Estado guardado
         ├─ Observación guardada (con detalles del error)
         └─ Referencia guardada

[Usuario recibe: "Tu reporte fue recibido. Será revisado manualmente"]

[Admin ve en Dashboard:]
┌─ Referencia: REF-2026-03-30-001
├─ Estado: en_revision
├─ Gemini: error
├─ Observación: "Error Gemini (reintentado): 503 UNAVAILABLE..."
└─ [Botón: Aprobar/Rechazar]
```

### Escenario C: Gemini RECHAZA la coincidencia (Sin Error)

```
[Gemini: compare_form_with_image()]
         ↓
[Retorna: coincide_exacto=False, comentario="Monto no coincide"]
         ↓
[pr.gemini_coincide_exacto = "false"]
[pr.gemini_comentario = "Monto no coincide"]
[pr.estado = "en_revision"]
[db.commit()]
         ↓
[Usuario recibe: "Tu reporte fue recibido. Será revisado manualmente"]

[Admin ve en Dashboard:]
├─ Gemini: false
├─ Observación: "Monto no coincide"
└─ [Revisar manualmente]
```

---

## Cambios de Código

### En `cobros_publico.py` - línea ~1079

**ANTES:**
```python
gemini_result = compare_form_with_image(form_data, content, filename)
coincide = gemini_result.get("coincide_exacto", False)
pr.gemini_coincide_exacto = "true" if coincide else "false"
pr.gemini_comentario = gemini_result.get("comentario")

if coincide:
    pr.estado = "aprobado"
else:
    pr.estado = "en_revision"

db.commit()
```

**DESPUÉS:**
```python
try:
    gemini_result = compare_form_with_image(form_data, content, filename)
    coincide = gemini_result.get("coincide_exacto", False)
    pr.gemini_coincide_exacto = "true" if coincide else "false"
    pr.gemini_comentario = gemini_result.get("comentario")

except Exception as gemini_err:
    # Si Gemini falla (incluso tras reintentos), enviar a revisión manual
    logger.warning(
        "[COBROS_PUBLIC] Gemini error para ref=%s tras reintentos, enviando a revisión manual: %s",
        referencia, str(gemini_err)
    )
    pr.gemini_coincide_exacto = "error"
    pr.gemini_comentario = f"Error Gemini (reintentado): {str(gemini_err)[:200]}"
    coincide = False  # Por seguridad, no aprobar si hay error

if coincide:
    pr.estado = "aprobado"
else:
    pr.estado = "en_revision"

db.commit()  # ✅ SIEMPRE se ejecuta (no en rollback)
```

**Cambios adicionales aplicados en:**
- `cobros_publico.py` línea ~1584 (endpoint INFOPAGOS)

---

## Garantías

### Antes (sin cambios)

| Situación | Resultado | Observación |
|-----------|-----------|-------------|
| Gemini 503 | 🔴 Falla | Nada se guarda |
| Gemini disponible | ✅ Ok | Se guarda |
| Gemini rechaza | ✅ Ok | Se guarda |

### Después (con cambios)

| Situación | Resultado | Observación | Estado | Acción |
|-----------|-----------|-------------|--------|--------|
| Gemini 503 x4 | 🟡 Error guardado | Se guarda motivo del error | en_revision | Admin revisa |
| Gemini disponible en reintento | ✅ Ok | Se aprueba automáticamente | aprobado | Recibo enviado |
| Gemini rechaza | ✅ Ok | Se guarda motivo | en_revision | Admin revisa |

---

## Mejoras de Observabilidad

### Logs Generados

**Cuando se recupera:**
```
[COBROS_PUBLIC] Gemini 503 (high demand) en comparar, reintento 2/4 en 20s
[COBROS_PUBLIC] Gemini OK: coincide_exacto=True ...
```

**Cuando falla tras reintentos:**
```
[COBROS_PUBLIC] Gemini 503 (high demand) en comparar, reintento 1/4 en 15s
[COBROS_PUBLIC] Gemini 503 (high demand) en comparar, reintento 2/4 en 20s
[COBROS_PUBLIC] Gemini 503 (high demand) en comparar, reintento 3/4 en 25s
[COBROS_PUBLIC] Gemini 503 (high demand) en comparar, reintento 4/4 en 30s
[COBROS_PUBLIC] Gemini error para ref=REF-2026-03-30-001 tras reintentos, enviando a revisión manual: 503 UNAVAILABLE...
```

### En BD - Tabla `pagos_reportados`

```sql
SELECT 
  id, 
  referencia_interna, 
  estado, 
  gemini_coincide_exacto,
  gemini_comentario
FROM pagos_reportados
WHERE gemini_coincide_exacto = 'error'
ORDER BY created_at DESC
LIMIT 10;
```

**Resultado esperado:**
```
| id | referencia_interna | estado | gemini_coincide_exacto | gemini_comentario |
|----|--------------------|--------|----------------------|-------------------|
| 1191 | REF-2026-03-30-001 | en_revision | error | Error Gemini (reintentado): 503 UNAVAILABLE... |
```

---

## Diagrama de Estados

```
                           ┌─────────────────┐
                           │   pendiente     │
                           │  (se crea en    │
                           │  la request)    │
                           └────────┬────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │                               │
            ┌───────▼────────┐          ┌──────────▼──────┐
            │   Llamar a     │          │   Llamar a      │
            │   Gemini sin   │          │   Gemini con    │
            │   error        │          │   503 error     │
            └───────┬────────┘          └──────────┬──────┘
                    │                              │
                    │                         Reintentar
                    │                         x4 (30s)
                    │                              │
        ┌───────────┼──────────────┐        ┌──────▼──────┐
        │                          │        │             │
    ┌───▼─────┐           ┌───────▼──┐   ┌─▼────┐    ┌──▼───┐
    │Coincide │           │No Coincide   │Ok    │    │Error │
    │= True   │           │= False  │   │      │    │      │
    └───┬─────┘           └───┬────┘    └──────┘    └──┬───┘
        │                     │                        │
    ┌───▼──────────┐      ┌────▼──────┐         ┌──────▼────┐
    │  aprobado    │      │en_revision │        │en_revision │
    │              │      │            │        │            │
    │-Recibo PDF   │      │-Admin      │        │-Admin      │
    │-Enviar email │      │ revisa     │        │ revisa     │
    │-Auto import  │      │-Manual     │        │-Manual     │
    └──────────────┘      │ decision   │        │ decision   │
                          └────────────┘        └────────────┘
```

---

## Testing

### Test 1: Verificar que se guarda en error

```bash
curl -X POST "http://localhost:8000/api/v1/cobros/public/enviar-reporte" \
  -H "Content-Type: multipart/form-data" \
  -F "tipo_cedula=V" \
  -F "numero_cedula=12345678" \
  -F "fecha_pago=2026-03-30" \
  -F "institucion_financiera=Banco" \
  -F "numero_operacion=123" \
  -F "monto=100" \
  -F "archivo=@comprobante.jpg"
```

**Verificar en BD:**
```sql
SELECT estado, gemini_coincide_exacto, gemini_comentario 
FROM pagos_reportados 
WHERE referencia_interna = 'REF-2026-03-30-001';
```

**Resultado esperado:**
- estado: `en_revision` (NO NULL, NO 'pendiente')
- gemini_coincide_exacto: `error` (guardado)
- gemini_comentario: `Error Gemini (reintentado): ...` (guardado)

---

## Próximos Pasos Recomendados

1. **[OPCIONAL] Circuit Breaker**: Si Gemini falla > 5 veces en 1 hora, marcar como "no disponible" y auto-enviar a revisión
2. **[OPCIONAL] Webhook Alternativo**: Usar OpenAI si Gemini falla persistentemente
3. **[RECOMENDADO] Dashboard Alert**: Mostrar contador de "Gemini errors" en dashboard de admins
4. **[RECOMENDADO] Caché Local**: Almacenar últimas 1000 validaciones Gemini para evitar re-procesar

