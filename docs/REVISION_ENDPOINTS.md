# Revisión de endpoints – API v1

**Fecha:** 2026-02-25  
**Prefijo base:** `API_V1_STR` (ej. `/api/v1`)

---

## 1. Estructura de routers

| Prefijo | Origen | Auth | Uso BD |
|--------|--------|------|--------|
| `/auth` | auth.py | No (login público) | Sí (User) |
| `/whatsapp` | whatsapp.py | No (webhook) | Sí |
| `/configuracion` | configuracion.py + sub-routers | Sí (excepto logo) | Sí |
| `/configuracion/ai` | configuracion_ai (vía configuracion) | Sí | Sí |
| `/configuracion/email` | configuracion_email | Sí | Sí |
| `/configuracion/whatsapp` | configuracion_whatsapp | Sí | Sí |
| `/configuracion/informe-pagos` | configuracion_informe_pagos | Sí (callback Google público) | Sí |
| `/pagos` | pagos.py | Sí | Sí |
| `/pagos/con-errores` | pagos_con_errores.py | Sí | Sí |
| `/prestamos` | prestamos.py | Sí | Sí |
| `/notificaciones` | notificaciones.py | Sí | Sí |
| `/notificaciones-previas`, `-dia-pago`, `-retrasadas`, `-prejudicial`, `-mora-90` | notificaciones_tabs | Sí | Sí |
| `/dashboard` | dashboard (kpis + graficos) | Sí | Sí (algunos stubs) |
| `/kpis` | kpis.py | Sí | Sí |
| `/auditoria` | auditoria.py | Sí | Sí |
| `/reportes` | reportes/* (dashboard, cliente, cartera, pagos, morosidad, financiero, asesores, productos, cedula, contable) | Sí | Sí |
| `/clientes` | clientes.py | Sí | Sí |
| `/tickets` | tickets.py | Sí | Sí |
| `/comunicaciones` | comunicaciones.py | Sí | Sí |
| `/validadores` | validadores.py | Sí | Sí |
| `/usuarios` | usuarios.py | Sí | Sí (tabla users) |
| `/modelos-vehiculos` | modelos_vehiculos.py | Sí | Sí |
| `/concesionarios` | concesionarios.py | Sí | Sí (solo lectura; CRUD → 501) |
| `/analistas` | analistas.py | Sí | Sí |
| `/ai/training` | ai_training.py | Sí | Sí |
| `/revision-manual` | revision_manual.py | Por endpoint (get_current_user) | Sí |

**No hay router HTTP para `cobranzas.py`**: es un módulo de lógica (`ejecutar_actualizacion_reportes`) usado por el scheduler; no expone endpoints.

---

## 2. Uso de `get_db` y datos reales

- **Regla del proyecto:** los endpoints deben mostrar **datos reales** desde la BD, inyectando `Depends(get_db)` y usando la sesión para las consultas.
- **Estado:** Los archivos bajo `api/v1/endpoints` que leen/escriben datos tienen `get_db` inyectado donde corresponde.
- **Excepciones esperadas:** auth (login/refresh), whatsapp webhook, y rutas públicas como `/configuracion/logo/{filename}` y callback Google; el resto está protegido y usa BD.

---

## 3. Endpoints marcados como [Stub] en dashboard/graficos

En `backend/app/api/v1/endpoints/dashboard/graficos.py`:

| Endpoint | Resumen | Estado |
|----------|--------|--------|
| `GET /cobranza-fechas-especificas` | Requiere tabla pagos/cobranzas | Devuelve `{"dias": []}`; tiene `get_db` pero no consulta. |
| `GET /cobranzas-semanales` | Valores fijos hasta tabla pagos | **Ya usa BD**: `_compute_cobranzas_semanales` usa Cuota/Prestamo. El summary "[Stub]" está desactualizado. |
| `GET /evolucion-pagos` | Datos demo hasta tener tabla pagos | **Ya usa BD**: cuenta y suma por `Cuota.fecha_pago`. El summary "[Stub]" está desactualizado. |
| `GET /cobranza-por-dia` | Días vacíos hasta pagos/cobranzas | Devuelve `{"dias": []}`; se podría rellenar con Cuota (fecha_pago, monto). |
| `GET /cobranzas-mensuales` | Meses vacíos | Devuelve `{"meses": []}`; idem. |
| `GET /cobros-por-analista` | Analistas vacíos | Devuelve `{"analistas": []}`; se podría derivar de Cuota+Prestamo.analista. |
| `GET /cobros-diarios` | Días vacíos | Devuelve `{"dias": []}`; idem. |
| `GET /cuentas-cobrar-tendencias` | Tendencias vacías | Devuelve `{"tendencias": []}`. |
| `GET /distribucion-prestamos` | Distribución vacía | Devuelve `{"distribucion": []}`. |
| `GET /metricas-acumuladas` | Métricas vacías | Devuelve `{"metricas": []}`. |

**Recomendación:**  
- Quitar el texto "[Stub]" en **cobranzas-semanales** y **evolucion-pagos** (ya usan datos reales).  
- Opcional: implementar datos reales para cobranza-por-dia, cobranzas-mensuales, cobros-por-analista y cobros-diarios usando `Cuota` + `Prestamo` (y filtros por analista/concesionario/modelo como en el resto del dashboard).

---

## 4. Otros puntos revisados

- **Concesionarios:** GET list/activos desde `Prestamo.concesionario` (distinct). GET/POST/PUT/DELETE por ID devuelven **501** (documentado).
- **Modelos de vehículos:** CRUD completo; lectura desde distinct + tabla si aplica.
- **Analistas:** Solo lectura desde distinct.
- **Revision manual:** Auth por endpoint con `get_current_user`; todos los que modifican datos están protegidos y usan `get_db`.
- **Health:** `GET /`, `GET /health`, `GET /health/db` en `main.py`; `/api/admin/run-migration-auditoria-fk` para uso interno.

---

## 5. Resumen de acciones sugeridas

1. **Documentación:** Actualizar el summary de `GET /cobranzas-semanales` y `GET /evolucion-pagos` en `dashboard/graficos.py` (quitar "[Stub]").
2. **Opcional:** Implementar respuestas con datos reales en los endpoints que hoy devuelven listas vacías (cobranza-por-dia, cobranzas-mensuales, cobros-por-analista, cobros-diarios) usando `Cuota` y `Prestamo`.
3. **Sin cambios necesarios:** Estructura de routers, uso de `get_db` y protección por auth están coherentes con la regla de “datos reales desde BD”.
