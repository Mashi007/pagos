# Auditoría paso a paso del proyecto Pagos (2026)

Auditoría técnica realizada para detectar problemas de seguridad, configuración, flujos críticos y buenas prácticas.

---

## 1. Estructura y configuración

| Revisión | Estado | Detalle |
|----------|--------|---------|
| Configuración central | ✅ | `app/core/config.py`: Pydantic Settings, carga desde `.env`, validación de SECRET_KEY (≥32 caracteres, no valores débiles). |
| Base de datos | ✅ | `postgres://` reemplazado por `postgresql://`; pool con pool_pre_ping, pool_recycle; timezone America/Caracas por conexión. |
| Variables obligatorias | ✅ | DATABASE_URL y SECRET_KEY obligatorias; ENCRYPTION_KEY opcional para valores sensibles en BD. |
| Documentación env | ✅ | Existen `backend/.env.example`, `backend/.env.ejemplo`, `frontend/.env.example`. README referencia .env. |

**Recomendación**: Mantener `.env` fuera de control de versiones; usar solo `.env.example` como plantilla.

---

## 2. Backend: API y seguridad

### 2.1 Autenticación en routers

| Router | Antes | Después / Notas |
|--------|--------|------------------|
| `revision_manual` | ❌ Sin auth a nivel router | ✅ **Corregido**: `APIRouter(dependencies=[Depends(get_current_user)])`. Todos los endpoints de Revisión Manual exigen login. |
| `configuracion_email` / `configuracion_whatsapp` | — | Incluidos bajo `configuracion.router`, que sí tiene `get_current_user`. OK. |
| `whatsapp` | Público | OK: webhook y verificación deben ser públicos. |
| `estado_cuenta_publico`, `cobros_publico` | Públicos por diseño | OK. |
| `auth`, `health` | Públicos | OK. |
| `router_logo`, `router_google_callback` | Públicos | OK (logo y OAuth callback). |

### 2.2 Health check y datos sensibles

| Revisión | Estado | Detalle |
|----------|--------|---------|
| GET /health/detailed | ✅ Corregido | Antes exponía `database_url[:80]` a cualquiera. Ahora solo muestra la URL cuando `DEBUG=True`; en producción devuelve `"[oculto en producción]"`. |
| GET /health/, /health/db | OK | No exponen secretos. |

### 2.3 SQL e inyección

| Revisión | Estado | Detalle |
|----------|--------|---------|
| Consultas con ORM/select() | ✅ | Uso generalizado de SQLAlchemy select() con parámetros; no se detectó concatenación de SQL con input de usuario. |
| health_check_detailed | ✅ | `table` en el bucle viene de lista fija `table_counts`, no de entrada del usuario. |
| configuracion_ai | OK | `statement_timeout` usa constante numérica. |

### 2.4 Errores y respuestas HTTP

| Revisión | Estado | Detalle |
|----------|--------|---------|
| Formato de error | ✅ | `app/core/exceptions.py`: mapeo status → code; handler global en `main.py` para HTTPException con `detail` + `code`. |
| Uso de get_db | ✅ | Endpoints que necesitan BD usan `Depends(get_db)` de forma consistente. |

---

## 3. Frontend

| Revisión | Estado | Detalle |
|----------|--------|---------|
| Rutas protegidas | ✅ | `RootLayoutWrapper` comprueba `isAuthenticated`; rutas no públicas redirigen a `/login`. |
| SimpleProtectedRoute | ✅ | Rutas administrativas con `requireAdmin={true}` donde corresponde. |
| Cliente API | ✅ | Axios con interceptors: token, refresh, manejo de 401 y mensajes por código (`getErrorCode`, `ERROR_CODE_MESSAGES`). |
| Tipos de error | ✅ | `getErrorMessage`, `getErrorCode`, manejo de `detail` array (422). |

---

## 4. Flujos críticos (notificaciones, email, PDF)

| Revisión | Estado | Detalle |
|----------|--------|---------|
| Configuración de envíos | ✅ | `notificaciones_envios` en BD; por tipo: habilitado, plantilla_id, incluir_pdf_anexo, incluir_adjuntos_fijos. |
| Contexto cobranza para PDF | ✅ | Se construye cuando `incluir_pdf_anexo` está marcado aunque no haya plantilla (Texto por defecto). |
| Variables en PDF variable | ✅ | `carta_cobranza_pdf._dict_reemplazo_pdf` incluye CUOTAS_VENCIDAS, FECHAS_CUOTAS_PENDIENTES, ENCABEZADO_END. |
| Adjuntos fijos en Render | ⚠️ Conocido | Los PDF subidos por caso se leen de disco; en Render el disco es efímero. Aviso limitado a una vez por caso por proceso para no saturar logs. |
| Body HTML en correos | ✅ | Se envía HTML cuando el cuerpo contiene etiquetas (table, div, p, etc.), no solo para plantillas tipo COBRANZA. |

---

## 5. Resumen de problemas detectados y correcciones

### Crítico (corregido)

1. **Revisión Manual sin autenticación**  
   Los endpoints bajo `/api/v1/revision-manual/` (lista de préstamos, resumen, detalle, etc.) eran accesibles sin token.  
   **Corrección**: `router = APIRouter(dependencies=[Depends(get_current_user)])` en `revision_manual.py`.

### Medio (corregido)

2. **Health detailed exponía parte de DATABASE_URL**  
   Cualquiera podía llamar a GET `/api/v1/health/detailed` y ver los primeros 80 caracteres de la cadena de conexión.  
   **Corrección**: Solo se devuelve la URL cuando `DEBUG=True`; en producción se devuelve `"[oculto en producción]"`.

### Bajo / recomendaciones

3. **Routers sin auth a nivel global**  
   `revision_manual` y `configuracion_ai` no tenían `dependencies` en el router; la protección dependía de cada endpoint. Revisión Manual ya está corregida; en configuracion_ai los endpoints sensibles siguen llevando `Depends(get_current_user)` en la ruta. Recomendación: valorar añadir auth a nivel router también en configuracion_ai.

4. **Logs de adjuntos fijos**  
   En entornos sin disco persistente (p. ej. Render) el aviso de “adjuntos fijos no encontrado” se emitía por cada ítem. Ya se limita a una vez por tipo de caso y por ruta faltante por proceso.

5. **Tests y cobertura**  
   Existen tests (pytest, Vitest); no se ha revisado cobertura. Recomendación: ejecutar cobertura y priorizar tests en flujos críticos (auth, notificaciones, PDF).

---

## 6. Checklist rápido post-auditoría

- [x] Revisión Manual exige autenticación (router con `get_current_user`).
- [x] Health detailed no expone DATABASE_URL en producción.
- [x] Errores HTTP unificados con `detail` + `code`.
- [x] Variables de plantilla PDF (CUOTAS_VENCIDAS, FECHAS_CUOTAS_PENDIENTES, ENCABEZADO_END) aplicadas.
- [x] Contexto de cobranza para Carta_Cobranza.pdf aunque no haya plantilla asignada.
- [x] Reducción de ruido en logs de adjuntos fijos.
- [ ] Revisar cobertura de tests y añadir donde sea crítico.
- [ ] Mantener `.env.example` actualizado con todas las variables necesarias para despliegue.

---

*Documento generado a partir de la auditoría paso a paso. Fecha: marzo 2026.*
