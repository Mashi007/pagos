# Auditoría integral del módulo Cobranzas

**Fecha:** 2025-02-02  
**Alcance:** Backend `app/api/v1/endpoints/cobranzas.py`, scheduler de reportes, uso de `get_db`.

---

## 1. Uso de `get_db` (sesión de BD)

Todos los endpoints del módulo Cobranzas inyectan la sesión de BD con `Depends(get_db)`.

| Endpoint | Método | `get_db` | Notas |
|----------|--------|----------|--------|
| `/resumen` | GET | ✅ `db: Session = Depends(get_db)` | Resumen desde Cuota/Prestamo/Cliente |
| `/diagnostico` | GET | ✅ | Diagnóstico desde cuotas |
| `/clientes-atrasados` | GET | ✅ | Lista clientes con cuotas atrasadas |
| `/clientes-por-cantidad-pagos` | GET | ✅ | Clientes con N cuotas atrasadas |
| `/por-analista` | GET | ✅ | Cobranzas agrupadas por analista |
| `/por-analista/{analista}/clientes` | GET | ✅ | Clientes atrasados de un analista |
| `/montos-por-mes` | GET | ✅ | Montos vencidos por mes |
| `/informes/clientes-atrasados` | GET | ✅ | Informe clientes atrasados (JSON/PDF/Excel) |
| `/informes/rendimiento-analista` | GET | ✅ | Informe rendimiento analista |
| `/informes/montos-vencidos-periodo` | GET | ✅ | Informe montos por período |
| `/informes/antiguedad-saldos` | GET | ✅ | Informe antigüedad saldos |
| `/informes/resumen-ejecutivo` | GET | ✅ | Resumen ejecutivo |
| `/notificaciones/atrasos` | POST | ✅ | Procesar notificaciones atrasos |
| `PUT /prestamos/{prestamo_id}/ml-impago` | PUT | ✅ | Marcar ML impago manual |
| `DELETE /prestamos/{prestamo_id}/ml-impago` | DELETE | ✅ | Quitar ML impago manual |

**Conclusión:** El módulo cumple la regla de datos reales desde BD y uso de `get_db` en todos los endpoints.

---

## 2. Datos reales desde BD

- **Tablas usadas:** `cuotas`, `prestamos`, `clientes`.
- **Conexión:** `app/core/database.py` con `settings.DATABASE_URL` (`.env` o variables de entorno).
- No hay stubs ni datos demo en los endpoints de cobranzas; las respuestas se calculan con consultas SQL/SQLAlchemy.

---

## 3. Actualización automática de reportes (6:00 y 13:00)

Se implementó un scheduler con **APScheduler** que ejecuta la actualización de reportes de cobranzas a las **6:00** y **13:00** (zona horaria `America/Caracas`).

### Archivos implicados

- **`app/core/scheduler.py`**
  - `BackgroundScheduler` con dos jobs `CronTrigger(hour=6, minute=0)` y `CronTrigger(hour=13, minute=0)`.
  - Job `_job_actualizar_reportes_cobranzas`: abre sesión con `SessionLocal()`, llama a `cobranzas.ejecutar_actualizacion_reportes(db)` y cierra la sesión.
- **`app/api/v1/endpoints/cobranzas.py`**
  - Función **`ejecutar_actualizacion_reportes(db: Session)`**: ejecuta la lógica de actualización de reportes (resumen + diagnóstico) usando la sesión recibida; pensada para ser llamada por el scheduler (no es un endpoint).
- **`app/main.py`**
  - En `on_startup`: se llama a `start_scheduler()` después de crear tablas y verificar BD.
  - En `on_shutdown`: se llama a `stop_scheduler()`.

### Comportamiento del job

1. Crear sesión con `SessionLocal()`.
2. Llamar a `cobranzas.ejecutar_actualizacion_reportes(db)` (resumen + diagnóstico desde BD).
3. Registrar en log el resultado (cuotas vencidas, monto adeudado, clientes atrasados).
4. Cerrar la sesión en `finally`.

La zona horaria por defecto es `America/Caracas`. Si se desea otra zona, se puede añadir en el futuro una variable de entorno (por ejemplo `SCHEDULER_TZ`) y usarla en `app/core/scheduler.py`.

---

## 4. Recomendaciones menores

- **Informe clientes atrasados:** El endpoint `/informes/clientes-atrasados` recibe el query param `analista` pero no lo usa al llamar a `get_clientes_atrasados`. Si se quiere filtrar por analista, habría que pasar ese filtro (por ejemplo filtrando por `Prestamo.analista`).
- **ML impago:** `PUT /prestamos/{prestamo_id}/ml-impago` usa `body: dict`; conviene definir un modelo Pydantic para el body (`nivel_riesgo`, `probabilidad_impago`) y usarlo en el endpoint.

---

## 5. Resumen

| Requisito | Estado |
|-----------|--------|
| Todos los endpoints con `get_db` | ✅ Cumplido |
| Datos reales desde BD (no stubs) | ✅ Cumplido |
| Reportes actualizados a las 6:00 | ✅ Scheduler configurado |
| Reportes actualizados a las 13:00 | ✅ Scheduler configurado |
