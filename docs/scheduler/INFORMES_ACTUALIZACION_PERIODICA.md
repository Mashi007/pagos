# Actualización periódica de informes y reportes

Todos los informes y reportes del sistema se actualizan de forma predecible: ya sea por **tareas programadas** o por **consulta en tiempo real** a la base de datos.

## Zona horaria

Las tareas programadas usan **America/Caracas**.

---

## Tareas programadas (scheduler)

| Hora  | Tarea                         | Descripción                                                                 |
|-------|-------------------------------|-----------------------------------------------------------------------------|
| **2:00**  | Notificaciones                | Actualización de datos de mora/notificaciones (cuotas no pagadas).         |
| **6:00**  | Reportes cobranzas            | Resumen (cuotas vencidas, monto adeudado, clientes atrasados) + diagnóstico. |
| **6:00**  | Informe de pagos (email)     | Envío de email con link a Google Sheet del informe de pagos.                |
| **13:00** | Reportes cobranzas            | Mismo resumen + diagnóstico.                                               |
| **13:00** | Informe de pagos (email)     | Envío de email con link a Google Sheet.                                    |
| **16:30** | Informe de pagos (email)     | Envío de email con link a Google Sheet.                                    |

- **Código:** `app/core/scheduler.py` (y en arranque `app/main.py`).
- El **dashboard** tiene su propio hilo que actualiza **caché** a las **6:00, 13:00 y 16:00** (admin, KPIs, gráficos). Ver `app/api/v1/endpoints/dashboard.py` → `start_dashboard_cache_refresh()`.

---

## Informes que se generan bajo demanda

Estos informes **no se precalculan**: cada vez que el usuario solicita JSON, PDF o Excel se consulta la BD en ese momento, por lo que **siempre reflejan datos actuales**.

| Informe                    | Endpoint (ejemplo)                          | Cuándo se “actualiza”        |
|---------------------------|---------------------------------------------|-----------------------------|
| Clientes atrasados        | `GET /api/v1/cobranzas/informes/clientes-atrasados` | Al solicitar el informe     |
| Rendimiento por analista  | `GET /api/v1/cobranzas/informes/rendimiento-analista` | Al solicitar el informe     |
| Montos vencidos por período | `GET /api/v1/cobranzas/informes/montos-vencidos-periodo` | Al solicitar el informe     |
| Antigüedad de saldos      | `GET /api/v1/cobranzas/informes/antiguedad-saldos` | Al solicitar el informe     |
| Resumen ejecutivo         | `GET /api/v1/cobranzas/informes/resumen-ejecutivo` | Al solicitar el informe     |

Los KPIs de la página de Cobranzas (Total cuotas vencidas, Monto total adeudado, Clientes atrasados) se obtienen con `GET /api/v1/cobranzas/resumen`, que también consulta la BD en cada petición.

---

## Resumen

- **Sí se actualizan periódicamente (vía scheduler o hilo de caché):**
  - Notificaciones (2:00).
  - Reportes cobranzas / resumen (6:00 y 13:00).
  - Informe de pagos por email (6:00, 13:00 y 16:30).
  - Caché del dashboard (6:00, 13:00 y 16:00).

- **Se actualizan al solicitarlos (siempre datos actuales):**
  - Todos los informes de Cobranzas (clientes atrasados, rendimiento analista, montos por período, antigüedad de saldos, resumen ejecutivo).
  - Resumen de cobranzas (KPIs) cuando se abre la página.
