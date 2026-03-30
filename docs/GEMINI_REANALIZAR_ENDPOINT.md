# Endpoint: Re-analizar Pago Reportado con Gemini

## Overview

Nuevo endpoint que permite al admin **forzar un nuevo escaneo con Gemini** de un comprobante que ya fue analizado.

**URL**: `POST /api/v1/cobros/pagos-reportados/{pago_id}/re-analizar-gemini`

**Autenticación**: Requerida (solo admins)

---

## Casos de Uso

### Caso 1: Gemini No Pasó al Principio (Error 503)
```
Historial:
├─ Primer envío: Gemini 503 → Se guardó "error"
├─ Admin ve: Estado "en_revision" + Observación "Error Gemini..."
└─ Admin ahora quiere: Volver a intentar
    └─ Clic en "Re-analizar"
        ├─ Gemini intenta nuevamente
        ├─ Si disponible → Se aprueba automáticamente
        └─ Si sigue con error → Se guarda nuevo error
```

### Caso 2: Gemini Rechazó pero Admin Sospecha Error
```
Historial:
├─ Primer envío: Gemini dice "Monto no coincide"
├─ Admin revisa imagen y piensa: "En realidad SÍ coincide"
└─ Admin quiere: Volver a analizar (quizás Gemini estaba confundido)
    └─ Clic en "Re-analizar"
        ├─ Gemini intenta nuevamente
        └─ Si esta vez dice "coincide" → Admin ve el nuevo resultado
```

### Caso 3: Verificación Manual del Admin
```
Historial:
├─ Primer envío: Gemini aprobó
├─ Admin revisa el dashboard y ve la aprobación
└─ Admin quiere: Verificar que Gemini hizo un buen análisis
    └─ Clic en "Re-analizar"
        ├─ Se obtiene nuevo análisis
        └─ Si el resultado es distinto → Admin investiga por qué
```

---

## API Endpoint

### Solicitud

```bash
POST /api/v1/cobros/pagos-reportados/1191/re-analizar-gemini

# Header requerido:
Authorization: Bearer <token_jwt>
Content-Type: application/json
```

### Respuesta Exitosa (200 OK)

**Si Gemini está disponible:**
```json
{
  "ok": true,
  "pago_id": 1191,
  "referencia_interna": "REF-2026-03-30-001",
  "gemini_coincide_exacto": "true",
  "gemini_comentario": "Los datos coinciden exactamente con el comprobante",
  "mensaje": "Comprobante re-analizado. Verifica la observación antes de aprobar o rechazar."
}
```

**Si Gemini falla tras reintentos (503):**
```json
{
  "ok": true,
  "pago_id": 1191,
  "referencia_interna": "REF-2026-03-30-001",
  "gemini_coincide_exacto": "error",
  "gemini_comentario": "Error Gemini en re-análisis (reintentado): 503 UNAVAILABLE. This model is currently experiencing high demand...",
  "mensaje": "Comprobante re-analizado. Verifica la observación antes de aprobar o rechazar."
}
```

### Respuesta de Error

**404 - Pago no encontrado:**
```json
{
  "detail": "Pago reportado no encontrado."
}
```

**400 - No hay comprobante:**
```json
{
  "detail": "No hay comprobante guardado para este pago. No se puede re-analizar."
}
```

---

## Comportamiento del Sistema

### Flujo de Re-análisis

```
[Admin hace clic "Re-analizar"]
         ↓
[POST /pagos-reportados/{pago_id}/re-analizar-gemini]
         ↓
[Se obtiene el comprobante guardado en BD]
         ↓
[Se extrae los datos originales del pago]
         ↓
[Se llama a compare_form_with_image() nuevamente]
    ├─ Reintento 1 (15s): 503?
    ├─ Reintento 2 (20s): 503?
    ├─ Reintento 3 (25s): 503?
    └─ Reintento 4 (30s): 503?
         ↓
[Se actualiza en BD:]
    ├─ gemini_coincide_exacto: (nuevo resultado)
    ├─ gemini_comentario: (nueva observación)
    └─ El ESTADO NO cambia (admin decide manualmente)
         ↓
[Se retorna el resultado al frontend]
         ↓
[Admin VE el nuevo análisis y decide:]
    ├─ "Ahora dice que coincide" → Clic Aprobar
    ├─ "Sigue diciendo error" → Rechaza o deja para revisar
    └─ "Cambió de opinión" → Investiga por qué
```

---

## Datos Usados en Re-análisis

El endpoint **recrea exactamente** los datos originales del pago:

```python
form_data = {
    "fecha_pago": "2026-03-30",
    "institucion_financiera": "Banco Nacional",
    "numero_operacion": "123456789",
    "monto": "1000.00",
    "moneda": "USD",
    "tipo_cedula": "V",
    "numero_cedula": "12345678",
}

image_bytes = pr.comprobante  # Imagen original guardada
```

**Importante**: Usa la **imagen original**, no una nueva. Si el admin quiere analizar con una imagen diferente, debe crear un nuevo reporte.

---

## Reintentos Automáticos

El re-análisis **también reintenta automáticamente** si Gemini devuelve 503:

| Intento | Espera | Estado |
|---------|--------|--------|
| 1 | 15s | 503? → Reintenta |
| 2 | 20s | 503? → Reintenta |
| 3 | 25s | 503? → Reintenta |
| 4 | 30s | 503? → Guarda error |

**Duración total**: Hasta ~2 minutos si Gemini está completamente caído.

---

## Cambios en BD

### Antes del Re-análisis
```sql
SELECT 
  id,
  estado,
  gemini_coincide_exacto,
  gemini_comentario
FROM pagos_reportados
WHERE id = 1191;

-- Resultado:
| 1191 | en_revision | error | Error Gemini (reintentado): 503 UNAVAILABLE... |
```

### Después del Re-análisis (Exitoso)
```sql
SELECT 
  id,
  estado,
  gemini_coincide_exacto,
  gemini_comentario
FROM pagos_reportados
WHERE id = 1191;

-- Resultado:
| 1191 | en_revision | true | Los datos coinciden exactamente con el comprobante |
```

**Nota**: El `estado` sigue siendo `en_revision`. El admin debe hacer clic en "Aprobar" manualmente para cambiarlo.

---

## Logs Generados

### En logs cuando se inicia re-análisis
```
[COBROS] Re-analizar con Gemini: pago_id=1191 ref=REF-2026-03-30-001 usuario=admin@rapicredit.com
```

### Cuando Gemini responde correctamente
```
[COBROS] Re-analizar Gemini OK: pago_id=1191 coincide=true
```

### Cuando Gemini falla tras reintentos
```
[COBROS] Re-analizar Gemini error pago_id=1191 tras reintentos: 503 UNAVAILABLE...
```

---

## Integración con Frontend

### Botón en Dashboard

El admin verá un botón "Re-analizar" junto a cada pago en estado `en_revision`:

```typescript
// Pseudocódigo React
<Button 
  onClick={() => reanalizar(pago.id)}
  variant="secondary"
  disabled={loading}
>
  {loading ? 'Re-analizando...' : 'Re-analizar con Gemini'}
</Button>
```

### Lógica del Frontend

```typescript
async function reanalizar(pagoId: number) {
  setLoading(true);
  try {
    const response = await fetch(
      `/api/v1/cobros/pagos-reportados/${pagoId}/re-analizar-gemini`,
      { method: 'POST' }
    );
    
    if (!response.ok) {
      throw new Error(await response.json());
    }
    
    const result = await response.json();
    
    // Mostrar nuevo resultado
    alert(`
      Nuevo análisis:
      - Coincide: ${result.gemini_coincide_exacto}
      - Observación: ${result.gemini_comentario}
    `);
    
    // Recargar datos del pago
    refetchPago(pagoId);
    
  } catch (error) {
    alert(`Error al re-analizar: ${error.message}`);
  } finally {
    setLoading(false);
  }
}
```

---

## Testing

### Test 1: Re-análisis Exitoso

```bash
curl -X POST \
  "http://localhost:8000/api/v1/cobros/pagos-reportados/1191/re-analizar-gemini" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Verificar en BD:**
```sql
SELECT gemini_coincide_exacto, gemini_comentario 
FROM pagos_reportados 
WHERE id = 1191;
```

### Test 2: Pago No Existe

```bash
curl -X POST \
  "http://localhost:8000/api/v1/cobros/pagos-reportados/99999/re-analizar-gemini" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Respuesta esperada: 404
```

### Test 3: Sin Comprobante

Modificar manualmente un pago en BD para que no tenga comprobante:
```sql
UPDATE pagos_reportados SET comprobante = NULL WHERE id = 1191;
```

Luego:
```bash
curl -X POST \
  "http://localhost:8000/api/v1/cobros/pagos-reportados/1191/re-analizar-gemini" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Respuesta esperada: 400 - "No hay comprobante guardado"
```

---

## Notas Importantes

1. **Estado NO cambia automáticamente**: Re-analizar solo actualiza `gemini_coincide_exacto` y `gemini_comentario`. El admin debe decidir manualmente.

2. **Usa la imagen original**: No es posible cambiar la imagen en el re-análisis. Si hay comprobante diferente, crear un nuevo reporte.

3. **Mismo número de reintentos**: El re-análisis usa la misma configuración de reintentos (4 intentos para 503).

4. **Auditoría**: Se registra en logs quién hizo el re-análisis y cuándo.

5. **Comprobante requerido**: No se puede re-analizar si el comprobante fue eliminado de la BD.

---

## Próximos Pasos (Futuro)

- [ ] Agregar endpoint para **re-descargar/subir nueva imagen** si la anterior está dañada
- [ ] Dashboard: mostrar **historial de re-análisis** (cuántas veces se intentó)
- [ ] Notificación al cliente si el resultado cambió después de re-análisis
- [ ] Estadísticas: % de cambios de resultado en re-análisis (para auditar Gemini)
