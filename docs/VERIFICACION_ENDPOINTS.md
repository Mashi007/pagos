# Verificación de configuración de endpoints

## Backend (FastAPI)

- **Prefijo global:** `settings.API_V1_STR` = `/api/v1` (en `main.py`: `app.include_router(api_router, prefix=settings.API_V1_STR)`).
- **Routers** registrados en `app/api/v1/__init__.py` con sus prefijos:

| Prefijo backend      | Módulo / Uso                          |
|----------------------|----------------------------------------|
| (sin prefijo)        | health                                 |
| `/auth`              | login, refresh, me, logout, forgot-password |
| `/whatsapp`          | webhook, etc.                          |
| `/configuracion`     | logo, upload-logo, ai, email, whatsapp |
| `/configuracion/informe-pagos` | Google callback (público)     |
| `/cobros/public`     | formulario público (sin auth)          |
| `/estado-cuenta/public` | estado de cuenta público (sin auth) |
| `/cobros`            | pagos-reportados, aprobar, rechazar, etc. |
| `/pagos/con-errores` | Revisar Pagos (antes de /pagos)        |
| `/pagos`             | CRUD pagos, stats, kpis, upload, batch |
| `/pagos/gmail`       | pipeline Gmail                         |
| `/prestamos`         | CRUD, cuotas, amortización, aprobar-manual |
| `/notificaciones`    | plantillas, envíos                     |
| `/notificaciones-previas`, etc. | Tabs notificaciones           |
| `/dashboard`         | kpis-principales, admin, gráficos      |
| `/kpis`              | dashboard                              |
| `/auditoria`         | listado, exportar                      |
| `/reportes`         | cartera, pagos, conciliación, etc.     |
| `/clientes`          | CRUD clientes                          |
| `/tickets`           | CRM tickets                            |
| `/crm/campanas`      | campañas                               |
| `/comunicaciones`    | WhatsApp/Email                         |
| `/validadores`       | validar-campo, configuracion           |
| `/usuarios`          | listado, toggle                        |
| `/modelos-vehiculos` | CRUD modelos                           |
| `/concesionarios`    | listado, activos                       |
| `/analistas`         | listado, activos                       |
| `/ai/training`       | conversaciones, ML, RAG                |
| `/revision-manual`   | préstamos post-migración               |

Todas las rutas quedan bajo **`/api/v1/{prefijo}/...`**.

---

## Frontend (axios + servicios)

- **Base URL:** `env.API_URL` (VITE_API_URL en producción cuando front y back están en dominios distintos; vacío cuando el proxy sirve todo en el mismo origen).
- **Rutas:** Los servicios usan rutas absolutas desde raíz de la API: `/api/v1/...`.

### Correspondencia Backend ↔ Frontend

| Área           | Backend (prefijo) | Frontend (baseUrl o constante)     | ¿Coincide? |
|----------------|-------------------|------------------------------------|------------|
| Auth           | `/auth`           | `/api/v1/auth/login`, `.../refresh`, `.../me` | Sí |
| Préstamos      | `/prestamos`      | `prestamoService`: `/api/v1/prestamos`       | Sí |
| Cobros         | `/cobros`         | `cobrosService`: `API + '/api/v1/cobros'`    | Sí |
| Pagos          | `/pagos`          | `pagoService`: `/api/v1/pagos`               | Sí |
| Pagos con errores | `/pagos/con-errores` | `pagoConErrorService`: `/api/v1/pagos/con-errores` | Sí |
| Gmail          | `/pagos/gmail`    | `pagoService`: `${baseUrl}/gmail/...`        | Sí |
| Reportes       | `/reportes`      | `reporteService`: `/api/v1/reportes`          | Sí |
| Clientes       | `/clientes`       | (hooks/API bajo `/api/v1/clientes`)          | Sí |
| Dashboard      | `/dashboard`      | llamadas directas `/api/v1/dashboard/...`    | Sí |
| KPIs           | `/kpis`           | `/api/v1/kpis/dashboard`                     | Sí |
| Validadores    | `/validadores`    | `validadoresService`: `/api/v1/validadores` | Sí |
| Usuarios       | `/usuarios`       | `Usuarios.tsx`: `/api/v1/usuarios`           | Sí |
| Modelos vehículo | `/modelos-vehiculos` | `modeloVehiculoService`: `/api/v1/modelos-vehiculos` | Sí |
| Concesionarios | `/concesionarios` | `concesionarioService`: `/api/v1/concesionarios` | Sí |
| Analistas      | `/analistas`      | `analistaService`: `/api/v1/analistas`       | Sí |
| AI Training    | `/ai/training`    | `aiTrainingService`: `/api/v1/ai/training`   | Sí |
| Configuración  | `/configuracion`  | varios: `/api/v1/configuracion/ai/...`, etc. | Sí |
| CRM Campañas   | `/crm/campanas`   | `campanasService`: `/api/v1/crm/campanas`   | Sí |
| Tickets        | `/tickets`        | `ticketsService`: `/api/v1/tickets`          | Sí |
| Comunicaciones | `/comunicaciones` | `comunicacionesService`: `/api/v1/comunicaciones` | Sí |
| Notificaciones | `/notificaciones` | `notificacionService`: `${API_V1}/notificaciones` | Sí |

---

## Conclusión

- **Prefijo único:** Toda la API está bajo `/api/v1`.
- **Nombres de recurso:** Los prefijos de backend coinciden con las rutas usadas en el frontend (`/auth`, `/prestamos`, `/cobros`, `/pagos`, etc.).
- **Orden de routers:** En backend, `/pagos/con-errores` se registra **antes** que `/pagos` para evitar que `GET /pagos/con-errores` se interprete como `GET /pagos/{pago_id}`.
- **Públicos sin auth:** `cobros/public`, `estado-cuenta/public`, `configuracion/informe-pagos` (callback Google), health y auth (login, refresh) no exigen token.
- **Autenticación:** El resto de endpoints usan `Depends(get_current_user)` en el router o en el endpoint.

**Los endpoints están bien configurados y alineados entre backend y frontend.**
