# Documentación Pagos (RapiCredit)

Índice lean tras limpieza de notas/auditorías históricas. Todo lo operativo vive bajo `docs/`.

## Deploy y entorno

| Documento | Descripción |
|-----------|-------------|
| [env/ENV_VARIABLES_DEPLOY.md](env/ENV_VARIABLES_DEPLOY.md) | Variables de entorno (Render / producción) |
| [env/VALIDACION_VARIABLES_RENDER.md](env/VALIDACION_VARIABLES_RENDER.md) | Validación de variables en Render |
| [deploy/RENDER_DEPLOY_NOTES.md](deploy/RENDER_DEPLOY_NOTES.md) | Notas de deploy Gunicorn / timeouts |
| [deploy/RENDER_CONFIGURACION.md](deploy/RENDER_CONFIGURACION.md) | Configuración Render |
| [deploy/RECUPERAR_ACCESO_RENDER.md](deploy/RECUPERAR_ACCESO_RENDER.md) | Recuperar acceso |
| [deploy/CREAR_USUARIO_README.md](deploy/CREAR_USUARIO_README.md) | Crear usuario admin |
| [deploy/CHECKLIST_DESPLIEGUE_COBROS.md](deploy/CHECKLIST_DESPLIEGUE_COBROS.md) | Checklist despliegue cobros |
| [env/GOOGLE_CLOUD_OCR_DRIVE_SHEETS.md](env/GOOGLE_CLOUD_OCR_DRIVE_SHEETS.md) | Google Cloud OCR / Drive / Sheets |
| [env/CONFIGURAR_GOOGLE_SHEET_PAPELETAS.md](env/CONFIGURAR_GOOGLE_SHEET_PAPELETAS.md) | Sheet papeletas |

## Email y notificaciones

| Documento | Descripción |
|-----------|-------------|
| [email/CONFIGURACION_EMAIL_4_CUENTAS.md](email/CONFIGURACION_EMAIL_4_CUENTAS.md) | 4 cuentas SMTP |
| [email/FLUJO_CONFIGURACION_EMAIL.md](email/FLUJO_CONFIGURACION_EMAIL.md) | Flujo configuración email |
| [email/POLITICAS_CREDENCIALES_GMAIL_WHATSAPP.md](email/POLITICAS_CREDENCIALES_GMAIL_WHATSAPP.md) | Políticas credenciales |
| [email/LIMITE_EMAIL_GMAIL.md](email/LIMITE_EMAIL_GMAIL.md) | Límites Gmail |
| [email/GMAIL_535_EMAIL_NO_ENVIA.md](email/GMAIL_535_EMAIL_NO_ENVIA.md) | Diagnóstico 535 |

## Scheduler y seguridad

| Documento | Descripción |
|-----------|-------------|
| [scheduler/PROGRAMACION_JOBS_SCHEDULER.md](scheduler/PROGRAMACION_JOBS_SCHEDULER.md) | Jobs APScheduler |
| [scheduler/INFORMES_ACTUALIZACION_PERIODICA.md](scheduler/INFORMES_ACTUALIZACION_PERIODICA.md) | Informes periódicos |
| [security/SEGURIDAD_ENLACES_PUBLICOS.md](security/SEGURIDAD_ENLACES_PUBLICOS.md) | Enlaces públicos |

## Arquitectura / flujos

| Documento | Descripción |
|-----------|-------------|
| [architecture/auditoria-api-cartera.md](architecture/auditoria-api-cartera.md) | API auditoría cartera |
| [architecture/CAMINOS_CARGA_PAGOS_APLICAR_CUOTAS.md](architecture/CAMINOS_CARGA_PAGOS_APLICAR_CUOTAS.md) | Carga pagos → cuotas |
| [architecture/PAGOS_GMAIL_FLUJO_COMPLETO.md](architecture/PAGOS_GMAIL_FLUJO_COMPLETO.md) | Flujo pagos Gmail |
| [architecture/ESTADO_CUENTA_PUBLICO_FLUJO_COMPLETO.md](architecture/ESTADO_CUENTA_PUBLICO_FLUJO_COMPLETO.md) | Estado de cuenta público |
| [architecture/ESTADO_CUENTA_FUENTE_UNICA.md](architecture/ESTADO_CUENTA_FUENTE_UNICA.md) | Fuente única estado de cuenta |
| [architecture/DOCUMENTOS_CLIENTE_CENTRO_UNICO.md](architecture/DOCUMENTOS_CLIENTE_CENTRO_UNICO.md) | Centro documentos cliente |

## Reglas de negocio y operación

| Documento | Descripción |
|-----------|-------------|
| [reglas/REGLAS_NEGOCIO_ESTADOS_CUOTA.md](reglas/REGLAS_NEGOCIO_ESTADOS_CUOTA.md) | Estados de cuota |
| [reglas/REGLAS_NEGOCIO_APLICACION_PAGOS_CUOTAS.md](reglas/REGLAS_NEGOCIO_APLICACION_PAGOS_CUOTAS.md) | Aplicación pagos → cuotas |
| [reglas/REGLAS_NEGOCIO_CLIENTES.md](reglas/REGLAS_NEGOCIO_CLIENTES.md) | Clientes |
| [reglas/REGLAS_NEGOCIO_DUPLICADOS.md](reglas/REGLAS_NEGOCIO_DUPLICADOS.md) | Duplicados |
| [reglas/PERMISOS_USUARIOS.md](reglas/PERMISOS_USUARIOS.md) | Permisos |
| [operacion/operacion-checklist-huella-pagos.md](operacion/operacion-checklist-huella-pagos.md) | Checklist huella pagos |

## Otros (fuera de `docs/`)

- [`../README.md`](../README.md) — overview del repo
- [`../frontend/README.md`](../frontend/README.md) — frontend
- [`../frontend/docs/runbook-502-proxy.md`](../frontend/docs/runbook-502-proxy.md) — 502 proxy
- [`../sql/README.md`](../sql/README.md) — scripts SQL
- [`../tests/README.md`](../tests/README.md) — tests
- [`../backend/app/services/prestamos/ARCHITECTURE.md`](../backend/app/services/prestamos/ARCHITECTURE.md) — arquitectura préstamos

Stubs de compatibilidad en `backend/docs/` apuntan a las rutas canónicas de arriba.
