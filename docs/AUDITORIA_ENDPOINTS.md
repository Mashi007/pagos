# Auditoría de endpoints API – RAPICREDIT

**Fecha:** 2025-03-18  
**Base URL:** `/api/v1` (config: `settings.API_V1_STR`)  
**Documentación:** `/docs` (Swagger), `/redoc` (ReDoc)

---

## 1. Resumen ejecutivo

| Aspecto | Valor |
|--------|--------|
| Prefijo global | `/api/v1` |
| Routers principales | 28 (incl. sub-routers de reportes, config, dashboard) |
| Endpoints públicos (sin JWT) | ~20 (health, auth login/refresh/forgot, cobros público, estado cuenta público, WhatsApp webhook, logo, migración admin) |
| Endpoints protegidos (JWT) | Resto (~200+) |
| Rutas en `main.py` (fuera de api_router) | `/`, `/health`, `/health/db`, `/health/gemini`, `/api/admin/run-migration-auditoria-fk` |

**Seguridad:** Los routers con `dependencies=[Depends(get_current_user)]` exigen JWT. Los públicos están concentrados en auth, cobros público, estado de cuenta público, health y WhatsApp webhook.

---

## 2. Estructura de montaje (api_router)

Definida en `backend/app/api/v1/__init__.py`. Orden relevante: `pagos_con_errores` se incluye **antes** que `pagos` para que `GET /pagos/con-errores` no colisione con `GET /pagos/{pago_id}`.

| Prefix | Router | Auth |
|--------|--------|------|
| (sin prefix) | health | No |
| `/auth` | auth | No (login, refresh, me, forgot-password, admin/reset-password con header) |
| `/whatsapp` | whatsapp | No (webhook GET/POST) |
| `/configuracion` | configuracion.router_logo | No (logo público) |
| `/configuracion/informe-pagos` | configuracion_informe_pagos.router_google_callback | No (OAuth callback) |
| `/cobros/public` | cobros_publico | No |
| `/estado-cuenta/public` | estado_cuenta_publico | No |
| `/cobros` | cobros | Sí |
| `/configuracion` | configuracion | Sí |
| `/pagos/con-errores` | pagos_con_errores | Sí |
| `/pagos` | pagos | Sí |
| `/pagos/gmail` | pagos_gmail | Sí |
| `/prestamos` | prestamos | Sí |
| `/notificaciones` | notificaciones | Sí |
| `/notificaciones-previas` | notificaciones_tabs (previas) | Sí |
| `/notificaciones-dia-pago` | notificaciones_tabs (dia pago) | Sí |
| `/notificaciones-retrasadas` | notificaciones_tabs (retrasadas) | Sí |
| `/notificaciones-prejudicial` | notificaciones_tabs (prejudicial) | Sí |
| `/notificaciones-mora-90` | notificaciones_tabs (mora 90) | Sí |
| `/dashboard` | dashboard | Sí |
| `/kpis` | kpis (dashboard) | Sí |
| `/auditoria` | auditoria | Sí |
| `/reportes` | reportes_router (varios sub-routers) | Sí |
| `/clientes` | clientes | Sí |
| `/tickets` | tickets | Sí |
| `/crm/campanas` | crm_campanas | Sí |
| `/comunicaciones` | comunicaciones | Sí |
| `/validadores` | validadores | Sí |
| `/usuarios` | usuarios | Sí |
| `/modelos-vehiculos` | modelos_vehiculos | Sí |
| `/concesionarios` | concesionarios | Sí |
| `/analistas` | analistas | Sí |
| `/ai/training` | ai_training | Sí |
| `/revision-manual` | revision_manual | Sí |

---

## 3. Inventario por módulo

### 3.1 Health (sin prefix en api_router, sin auth)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health/` | Health básico |
| GET | `/api/v1/health/db` | Conexión BD |
| GET | `/api/v1/health/gemini` | Disponibilidad Gemini |
| GET | `/api/v1/health/clientes-stats-diagnostico` | Diagnóstico clientes |
| GET | `/api/v1/health/cobros` | Diagnóstico cobros |
| GET | `/api/v1/health/integrity` | Integridad préstamos/cuotas/pagos |
| GET | `/api/v1/health/detailed` | Detalle ampliado |

### 3.2 Auth (`/api/v1/auth`) – Público

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/admin/reset-password` | Reset contraseña (header X-Admin-Secret) |
| GET | `/auth/status` | Estado auth |
| POST | `/auth/forgot-password` | Olvido contraseña (rate limit) |
| POST | `/auth/login` | Login (rate limit por IP) |
| POST | `/auth/logout` | Logout |
| POST | `/auth/refresh` | Refresh token |
| GET | `/auth/me` | Usuario actual (requiere JWT en práctica si se usa desde app) |

### 3.3 WhatsApp (`/api/v1/whatsapp`) – Público (webhook)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/whatsapp/webhook` | Verificación webhook |
| POST | `/whatsapp/webhook` | Recepción mensajes |

### 3.4 Cobros público (`/api/v1/cobros/public`) – Público

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/cobros/public/validar-cedula` | Validar cédula para reporte |
| POST | `/cobros/public/enviar-reporte` | Enviar reporte de pago |
| GET | `/cobros/public/recibo` | Recibo por query params |
| POST | `/cobros/public/infopagos/enviar-reporte` | Reporte Infopagos |
| GET | `/cobros/public/infopagos/recibo` | Recibo Infopagos |

### 3.5 Estado de cuenta público (`/api/v1/estado-cuenta/public`) – Público

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/estado-cuenta/public/recibo-cuota` | PDF recibo cuota (token) |
| GET | `/estado-cuenta/public/validar-cedula` | Validar cédula (nombre/email) |
| POST | `/estado-cuenta/public/solicitar-codigo` | Solicitar código email |
| POST | `/estado-cuenta/public/verificar-codigo` | Verificar código → PDF estado cuenta |
| POST | `/estado-cuenta/public/solicitar-estado-cuenta` | PDF estado cuenta + envío email |

### 3.6 Cobros admin (`/api/v1/cobros`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/cobros/pagos-reportados` | Listado paginado |
| GET | `/cobros/pagos-reportados/{pago_id}` | Detalle |
| POST | `/cobros/pagos-reportados/{pago_id}/aprobar` | Aprobar → crea pago y aplica a cuotas |
| POST | `/cobros/pagos-reportados/{pago_id}/rechazar` | Rechazar |
| DELETE | `/cobros/pagos-reportados/{pago_id}` | Eliminar |
| GET | `/cobros/historico-cliente` | Histórico por cédula |
| GET | `/cobros/pagos-reportados/{pago_id}/comprobante` | Comprobante |
| GET | `/cobros/pagos-reportados/{pago_id}/recibo.pdf` | PDF recibo |
| POST | `/cobros/pagos-reportados/{pago_id}/enviar-recibo` | Enviar recibo por correo |
| PATCH | `/cobros/pagos-reportados/{pago_id}` | Actualizar |
| PATCH | `/cobros/pagos-reportados/{pago_id}/estado` | Cambiar estado |

### 3.7 Pagos con errores (`/api/v1/pagos/con-errores`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/pagos/con-errores` | Listado |
| POST | `/pagos/con-errores` | Crear |
| POST | `/pagos/con-errores/batch` | Batch |
| POST | `/pagos/con-errores/eliminar-por-descarga` | Eliminar por descarga |
| GET | `/pagos/con-errores/export` | Export |
| POST | `/pagos/con-errores/mover-a-pagos` | Mover a tabla pagos (aplica cuotas) |
| GET | `/pagos/con-errores/{pago_id}` | Detalle |
| PUT | `/pagos/con-errores/{pago_id}` | Actualizar |
| DELETE | `/pagos/con-errores/{pago_id}` | Eliminar |

### 3.8 Pagos (`/api/v1/pagos`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/pagos` | Listado paginado |
| GET | `/pagos/ultimos` | Últimos pagos |
| POST | `/pagos/upload` | Carga Excel (batch) |
| POST | `/pagos/importar-desde-cobros` | Importar reportados aprobados |
| GET | `/pagos/importar-desde-cobros/datos-revisar` | Hay datos a revisar |
| GET | `/pagos/importar-desde-cobros/descargar-excel-errores` | Excel errores |
| POST | `/pagos/validar-filas-batch` | Validar filas batch |
| POST | `/pagos/guardar-fila-editable` | Guardar fila desde preview |
| POST | `/pagos/conciliacion/upload` | Excel conciliación |
| GET | `/pagos/kpis` | KPIs |
| GET | `/pagos/stats` | Estadísticas |
| POST | `/pagos/revisar-pagos/mover` | Mover entre revisar/pagos |
| GET | `/pagos/{pago_id}` | Detalle |
| POST | `/pagos/batch` | Crear lote (preview confirmado) |
| POST | `/pagos` | Crear pago (formulario) |
| PUT | `/pagos/{pago_id}` | Actualizar |
| DELETE | `/pagos/{pago_id}` | Eliminar |
| POST | `/pagos/{pago_id}/aplicar-cuotas` | Aplicar pago a cuotas |

### 3.9 Pagos Gmail (`/api/v1/pagos/gmail`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/pagos/gmail/count-pending` | Pendientes |
| POST | `/pagos/gmail/run-now` | Ejecutar pipeline |
| GET | `/pagos/gmail/status` | Estado sync |
| POST | `/pagos/gmail/confirmar-dia` | Confirmar día |
| GET | `/pagos/gmail/download-excel` | Descargar Excel |
| GET | `/pagos/gmail/download-excel-temporal` | Excel temporal |
| GET | `/pagos/gmail/diagnostico` | Diagnóstico |

### 3.10 Préstamos (`/api/v1/prestamos`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/prestamos` | Listado |
| GET | `/prestamos/stats` | Estadísticas |
| POST | `/prestamos/cedula/batch` | Batch por cédulas |
| GET | `/prestamos/cedula/{cedula}` | Por cédula |
| GET | `/prestamos/cedula/{cedula}/resumen` | Resumen cédula |
| GET | `/prestamos/{prestamo_id}` | Detalle |
| GET | `/prestamos/{prestamo_id}/cuotas` | Cuotas |
| GET | `/prestamos/{prestamo_id}/cuotas/{cuota_id}/recibo.pdf` | PDF recibo cuota |
| GET | `/prestamos/{prestamo_id}/amortizacion/excel` | Excel amortización |
| GET | `/prestamos/{prestamo_id}/amortizacion/pdf` | PDF amortización |
| POST | `/prestamos/{prestamo_id}/generar-amortizacion` | Generar cuotas |
| POST | `/prestamos/{prestamo_id}/aplicar-condiciones-aprobacion` | Aplicar condiciones |
| POST | `/prestamos/{prestamo_id}/evaluar-riesgo` | Evaluar riesgo |
| PATCH | `/prestamos/{prestamo_id}/marcar-revision` | Marcar en revisión |
| POST | `/prestamos/{prestamo_id}/asignar-fecha-aprobacion` | Asignar fecha |
| POST | `/prestamos/{prestamo_id}/aprobar-manual` | Aprobar manual |
| POST | `/prestamos/{prestamo_id}/rechazar` | Rechazar |
| GET | `/prestamos/{prestamo_id}/evaluacion-riesgo` | Ver evaluación |
| GET | `/prestamos/{prestamo_id}/auditoria` | Auditoría |
| POST | `/prestamos/generar-cuotas-aprobados-sin-cuotas` | Generar cuotas masivo |
| POST | `/prestamos` | Crear |
| PUT | `/prestamos/{prestamo_id}` | Actualizar |
| DELETE | `/prestamos/{prestamo_id}` | Eliminar |
| POST | `/prestamos/upload-excel` | Carga Excel |
| POST | `/prestamos/revisar/agregar` | Revisar agregar |
| GET | `/prestamos/revisar/lista` | Revisar lista |
| POST | `/prestamos/revisar/eliminar-por-descarga` | Revisar eliminar por descarga |
| DELETE | `/prestamos/revisar/{error_id}` | Revisar eliminar |

### 3.11 Notificaciones (`/api/v1/notificaciones`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/notificaciones/plantillas` | Listado plantillas |
| GET | `/notificaciones/plantillas/{plantilla_id}` | Detalle plantilla |
| POST | `/notificaciones/plantillas` | Crear plantilla |
| PUT | `/notificaciones/plantillas/{plantilla_id}` | Actualizar plantilla |
| DELETE | `/notificaciones/plantillas/{plantilla_id}` | Eliminar plantilla |
| GET | `/notificaciones/plantilla-pdf-cobranza` | PDF cobranza |
| GET | `/notificaciones/plantilla-pdf-cobranza/preview` | Preview |
| PUT | `/notificaciones/plantilla-pdf-cobranza` | Actualizar |
| GET | `/notificaciones/plantilla-estado-cuenta-codigo-email` | Plantilla código estado cuenta |
| PUT | `/notificaciones/plantilla-estado-cuenta-codigo-email` | Actualizar |
| GET | `/notificaciones/adjunto-fijo-cobranza` | Adjunto fijo |
| GET | `/notificaciones/adjunto-fijo-cobranza/verificar` | Verificar |
| PUT | `/notificaciones/adjunto-fijo-cobranza` | Actualizar |
| GET | `/notificaciones/adjuntos-fijos-cobranza` | Listado adjuntos |
| POST | `/notificaciones/adjuntos-fijos-cobranza/upload` | Subir |
| DELETE | `/notificaciones/adjuntos-fijos-cobranza/{doc_id}` | Eliminar |
| GET | `/notificaciones/plantillas/{plantilla_id}/export` | Export |
| POST | `/notificaciones/plantillas/{plantilla_id}/enviar` | Enviar |
| GET | `/notificaciones/variables` | Variables |
| GET | `/notificaciones/variables/{variable_id}` | Variable |
| POST | `/notificaciones/variables` | Crear variable |
| PUT | `/notificaciones/variables/{variable_id}` | Actualizar |
| DELETE | `/notificaciones/variables/{variable_id}` | Eliminar |
| POST | `/notificaciones/variables/inicializar-precargadas` | Inicializar |
| GET | `/notificaciones` | Resumen tabs |
| POST | `/notificaciones/enviar-todas` | Enviar todas |
| GET | `/notificaciones/estadisticas/resumen` | Resumen |
| GET | `/notificaciones/estadisticas-por-tab` | Por tab |
| GET | `/notificaciones/rebotados-por-tab` | Rebotados |
| GET | `/notificaciones/rebotados-por-tab/excel` | Excel rebotados |
| GET | `/notificaciones/historial-por-cedula` | Historial cédula |
| GET | `/notificaciones/historial-por-cedula/excel` | Excel historial |
| GET | `/notificaciones/historial-por-cedula/{envio_id}/comprobante` | Comprobante |
| GET | `/notificaciones/clientes-retrasados` | Clientes retrasados |
| POST | `/notificaciones/actualizar` | Actualizar (recalcular mora) |

### 3.12 Notificaciones tabs (previas, día pago, retrasadas, prejudicial, mora-90) – Auth

Cada uno expone GET (y en algunos casos POST) bajo su prefix; ver `notificaciones_tabs.py` y `__init__.py`.

### 3.13 Dashboard y KPIs – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/dashboard/...` | (sub-routers graficos, etc.) |
| GET | `/kpis/opciones-filtros` | Opciones filtros |
| GET | `/kpis/kpis-principales` | KPIs principales |
| GET | `/kpis/admin` | Admin |
| GET | `/dashboard/.../financiamiento-tendencia-mensual` | Gráfico |
| GET | `/dashboard/.../morosidad-por-dia` | Gráfico |
| GET | `/dashboard/.../proyeccion-cobro-30-dias` | Gráfico |

(Detalle exacto de paths de dashboard en `dashboard/__init__.py` y `graficos.py`.)

### 3.14 Auditoría (`/api/v1/auditoria`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/auditoria` | Listado |
| GET | `/auditoria/stats` | Estadísticas |
| GET | `/auditoria/exportar` | Exportar |
| GET | `/auditoria/{auditoria_id}` | Detalle |
| POST | `/auditoria/registrar` | Registrar |

### 3.15 Reportes (`/api/v1/reportes`) – Auth

Sub-routers sin prefix adicional; rutas relativas al prefix `/reportes`:

- **Dashboard:** GET `/reportes/dashboard/resumen`
- **Cliente:** GET `/reportes/cliente/{cedula}/pendientes.pdf`, GET `.../amortizacion.pdf`
- **Cartera:** GET `/reportes/cartera/por-mes`, GET `/reportes/cartera`, GET `/reportes/exportar/cartera`
- **Pagos:** GET `/reportes/pagos`, `/reportes/pagos/por-dia-mes`, `/reportes/pagos/por-mes`, GET `/reportes/exportar/pagos`
- **Morosidad:** GET `/reportes/morosidad/clientes`, `/reportes/exportar/morosidad-clientes`, `/reportes/morosidad`, `/reportes/morosidad/por-mes`, `/reportes/morosidad/por-rangos`, GET `/reportes/exportar/morosidad`
- **Financiero:** GET `/reportes/financiero`, GET `/reportes/exportar/financiero`
- **Asesores:** GET `/reportes/asesores/por-mes`, GET `/reportes/asesores`
- **Productos:** GET `/reportes/productos/por-mes`, GET `/reportes/productos`, GET `/reportes/exportar/productos`
- **Por cédula:** GET `/reportes/por-cedula`, GET `/reportes/exportar/cedula`
- **Contable:** GET `/reportes/contable/cedulas`, GET `/reportes/exportar/contable`
- **Conciliación:** POST `/reportes/conciliacion/cargar`, `.../cargar-excel-debug`, `.../cargar-excel`, GET `/reportes/exportar/conciliacion`, GET `/reportes/conciliacion/resumen`

### 3.16 Clientes (`/api/v1/clientes`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/clientes/estados` | Estados para dropdown |
| GET | `/clientes` | Listado paginado |
| GET | `/clientes/stats` | Estadísticas |
| GET | `/clientes/stats/diagnostico` | Diagnóstico |
| GET | `/clientes/casos-a-revisar` | Casos a revisar |
| POST | `/clientes/actualizar-lote` | Actualizar lote |
| POST | `/clientes/check-cedulas` | Verificar cédulas |
| POST | `/clientes/check-emails` | Verificar emails |
| PATCH | `/clientes/{cliente_id}/estado` | Cambiar estado |
| GET | `/clientes/{cliente_id}` | Detalle |
| POST | `/clientes` | Crear |
| PUT | `/clientes/{cliente_id}` | Actualizar |
| DELETE | `/clientes/{cliente_id}` | Eliminar |
| POST | `/clientes/upload-excel` | Carga Excel |
| GET | `/clientes/revisar/lista` | Revisar lista |
| POST | `/clientes/revisar/agregar` | Revisar agregar |
| DELETE | `/clientes/revisar/{error_id}` | Revisar eliminar |
| POST | `/clientes/revisar/eliminar-por-descarga` | Revisar eliminar por descarga |

### 3.17 Tickets (`/api/v1/tickets`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/tickets` | Listado |
| GET | `/tickets/{ticket_id}` | Detalle |
| POST | `/tickets` | Crear |
| PUT | `/tickets/{ticket_id}` | Actualizar |

### 3.18 CRM Campañas (`/api/v1/crm/campanas`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/crm/campanas/preview-destinatarios` | Preview |
| GET | `/crm/campanas` | Listado |
| POST | `/crm/campanas` | Crear |
| GET | `/crm/campanas/{campana_id}` | Detalle |
| PATCH | `/crm/campanas/{campana_id}` | Actualizar |
| POST | `/crm/campanas/{campana_id}/parar` | Parar |
| DELETE | `/crm/campanas/{campana_id}` | Eliminar |
| POST | `/crm/campanas/{campana_id}/programar` | Programar |
| POST | `/crm/campanas/{campana_id}/iniciar-envio` | Iniciar envío |
| GET | `/crm/campanas/{campana_id}/envios` | Envíos |

### 3.19 Comunicaciones (`/api/v1/comunicaciones`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/comunicaciones` | Resumen |
| GET | `/comunicaciones/mensajes` | Mensajes |
| GET | `/comunicaciones/por-responder` | Por responder |
| POST | `/comunicaciones/enviar-whatsapp` | Enviar WhatsApp |
| POST | `/comunicaciones/crear-cliente-automatico` | Crear cliente |

### 3.20 Validadores (`/api/v1/validadores`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/validadores/configuracion-validadores` | Configuración |
| POST | `/validadores/...` | (probar validadores, etc.) |

### 3.21 Usuarios (`/api/v1/usuarios`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/usuarios` | Listado |
| GET | `/usuarios/verificar-admin` | ¿Hay admin? |
| GET | `/usuarios/{user_id}` | Detalle |
| POST | `/usuarios` | Crear |
| PUT | `/usuarios/{user_id}` | Actualizar |
| DELETE | `/usuarios/{user_id}` | Eliminar |
| POST | `/usuarios/{user_id}/activate` | Activar |
| POST | `/usuarios/{user_id}/deactivate` | Desactivar |

### 3.22 Modelos vehículos, Concesionarios, Analistas – Auth

- **Modelos:** GET/POST/PUT/DELETE `/modelos-vehiculos`, GET `/modelos-vehiculos/activos`, GET `/{modelo_id}`, POST `/importar`
- **Concesionarios:** GET/POST/PUT/DELETE, GET `/activos`, GET `/{id}`
- **Analistas:** GET `/analistas/activos`

### 3.23 AI Training (`/api/v1/ai/training`) – Auth

Métricas, conversaciones, calificar, fine-tuning, RAG, ML impago (múltiples GET/POST/PUT/DELETE). Ver `ai_training.py`.

### 3.24 Revisión manual (`/api/v1/revision-manual`) – Auth

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/revision-manual/prestamos` | Resumen |
| PUT | `/revision-manual/prestamos/{prestamo_id}/confirmar` | Confirmar |
| PUT | `/revision-manual/prestamos/{prestamo_id}/iniciar-revision` | Iniciar revisión |
| PUT | `/revision-manual/clientes/{cliente_id}` | Actualizar cliente |
| PUT | `/revision-manual/prestamos/{prestamo_id}` | Actualizar préstamo |
| DELETE | `/revision-manual/prestamos/{prestamo_id}` | Eliminar |
| GET | `/revision-manual/pagos/{cedula}` | Pagos por cédula |
| PUT | `/revision-manual/cuotas/{cuota_id}` | Editar cuota |
| GET | `/revision-manual/resumen-rapido` | Resumen rápido |
| GET | `/revision-manual/prestamos/{prestamo_id}/detalle` | Detalle préstamo |
| PUT | `/revision-manual/prestamos/{prestamo_id}/finalizar-revision` | Finalizar revisión |

### 3.25 Configuración (`/api/v1/configuracion`) – Auth (+ router_logo público)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/configuracion/general` | General |
| PUT | `/configuracion/general` | Actualizar general |
| POST | `/configuracion/upload-logo` | Subir logo |
| DELETE | `/configuracion/logo` | Eliminar logo |
| GET | `/configuracion/notificaciones/envios` | Envíos notificaciones |
| PUT | `/configuracion/notificaciones/envios` | Actualizar |
| POST | `/configuracion/validadores/probar` | Probar validadores |
| GET | `/configuracion/sistema/completa` | Config sistema completa |
| GET | `/configuracion/sistema/categoria/{categoria}` | Por categoría |

Sub-routers: `/configuracion/ai`, `/configuracion/email`, `/configuracion/whatsapp`, `/configuracion/informe-pagos` (estado, config, Google OAuth). Configuración AI: muchos endpoints (config, prompt, variables, chat, calificaciones, tablas-campos, definiciones-campos, diccionario-semantico).

---

## 4. Rutas en main.py (fuera de api_router)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/` | No | Bienvenida + version + docs |
| HEAD | `/` | No | Health |
| GET | `/health` | No | Salud |
| GET | `/health/db` | No | BD conectada |
| GET | `/health/gemini` | No | Gemini disponible |
| HEAD | `/health` | No | Health HEAD |
| POST | `/api/admin/run-migration-auditoria-fk` | Header X-Migration-Secret | Migración FK auditoría |

---

## 5. Observaciones de seguridad

| Punto | Estado | Comentario |
|-------|--------|------------|
| Endpoints públicos acotados | OK | Solo health, auth, cobros público, estado cuenta público, WhatsApp webhook, logo, OAuth callback, migración admin (con secreto). |
| Rate limiting | Parcial | Login y forgot-password tienen rate limit en memoria; estado cuenta público tiene rate limit por IP (validar, solicitar, verificar). Cobros público puede tener límites en módulo de rate limit. |
| JWT en routers | OK | Routers de negocio usan `dependencies=[Depends(get_current_user)]`. |
| Secretos administrativos | OK | Reset password y migración exigen header con secreto de env. |
| CORS | OK | Configurado en main con allow_credentials y orígenes desde settings. |
| Auditoría de mutaciones | OK | AuditMiddleware registra POST/PUT/DELETE/PATCH. |

---

## 6. Consistencia y buenas prácticas

| Aspecto | Observación |
|---------|-------------|
| Prefijo único | Todo bajo `/api/v1` salvo raíz y health en main. |
| Orden de rutas | `/pagos/con-errores` antes de `/pagos` evita que `con-errores` sea interpretado como `{pago_id}`. |
| Datos reales | Regla de proyecto: endpoints de negocio usan BD (get_db), no stubs. |
| response_model | Mayoría de endpoints con response_model o dict/list; algunos streams (Excel, PDF) sin response_model. |
| Códigos HTTP | 201 en creación, 204 en delete, 4xx/5xx coherentes. |
| Documentación | Swagger en `/docs`; descripciones en muchos endpoints; algunos podrían mejorar summary/detail. |

---

## 7. Recomendaciones

1. **Documentar rate limits:** Indicar en OpenAPI (summary/description) qué endpoints tienen rate limit (login, forgot-password, estado cuenta público).
2. **Health en un solo lugar:** Unificar criterio: o todo bajo `/api/v1/health` o documentar que `/health` y `/health/db` están en main para monitoreo externo.
3. **Auditoría de accesos a datos sensibles:** Revisar que endpoints que devuelven datos por cédula (estado cuenta, reportes) solo expongan datos del cliente autorizado (estado cuenta público ya restringido por cédula + código).
4. **Idempotencia en aplicar-cuotas:** Mantener documentada o garantizada la idempotencia de `POST /pagos/{pago_id}/aplicar-cuotas` para evitar doble aplicación.
5. **Listado único de endpoints:** Este documento puede generarse o validarse con un script que recorra los routers de FastAPI y extraiga método, path y tags (por ejemplo desde `app.openapi()`).

---

## 8. Referencias de código

- Montaje de routers: `backend/app/api/v1/__init__.py`
- Aplicación y prefix global: `backend/app/main.py` (`app.include_router(api_router, prefix=settings.API_V1_STR)`)
- Configuración: `backend/app/core/config.py` (`API_V1_STR = "/api/v1"`)
- Dependencia de auth: `backend/app/core/deps.py` (`get_current_user`)
- Auditoría: `backend/app/middleware/audit_middleware.py`
