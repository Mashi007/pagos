# Auditoría integral: conexión a BD y regla "no mock data"

**Fecha:** 2025-02-02  
**Regla:** La aplicación debe mostrar **datos reales** desde la base de datos. No stubs ni datos de demostración en endpoints de negocio.

## 1. Infraestructura de BD

| Componente | Estado | Detalle |
|------------|--------|---------|
| **Config** | OK | `DATABASE_URL` en `app/core/config.py` (obligatorio). |
| **Engine/Session** | OK | `app/core/database.py`: `engine`, `SessionLocal`, `get_db()`. |
| **Health BD** | OK | `GET /health/db` verifica conexión; 503 si falla. |
| **Startup** | OK | `main.py` crea tablas (`Base.metadata.create_all`) e importa todos los modelos, incluido `Auditoria`. |

## 2. Endpoints auditados: uso de `get_db` y datos reales

### 2.1 Con datos reales desde BD (cumplen regla)

| Módulo | Endpoints | Fuente de datos |
|--------|-----------|-----------------|
| **clientes** | CRUD, stats | Tabla `clientes`. |
| **tickets** | CRUD | Tabla `tickets`. |
| **configuracion** | general, logo, notificaciones/envios, sistema/completa, sistema/categoria | Tabla `configuracion` (clave-valor). |
| **configuracion_email** | GET/PUT, estado, probar | Tabla `configuracion` + sync con stub en memoria. |
| **configuracion_whatsapp** | GET/PUT | Tabla `configuracion`. |
| **notificaciones** | clientes-retrasados, actualizar | Tablas `cuotas`, `clientes`. |
| **notificaciones_tabs** | Todos (previas, día pago, retrasadas, etc.) | Tablas `cuotas`, `clientes`. |
| **comunicaciones** | listado, por-responder, crear-cliente | BD; listados vacíos si no hay datos. |
| **whatsapp** | webhook | BD. |
| **pagos** | /kpis, /stats | Tablas `cuotas`, `prestamos`, `clientes`. |
| **kpis** | /dashboard | Tablas `prestamos`, `cuotas`. |
| **cobranzas** | Todos (resumen, diagnostico, clientes-atrasados, por-analista, montos-por-mes, informes, notificaciones/atrasos, ml-impago) | Tablas `cuotas`, `prestamos`, `clientes`. |
| **auditoria** | listado, stats, exportar, GET /{id}, POST /registrar | Tabla `auditoria`. |
| **dashboard** | opciones-filtros, kpis-principales, admin, financiamiento-tendencia, morosidad-por-dia, prestamos-por-concesionario/modelo, cobranza-fechas-especificas, cobranzas-semanales, morosidad-por-analista, evolucion-morosidad, evolucion-pagos, cobranza-por-dia, cobranzas-mensuales, cobros-por-analista, cobros-diarios, cuentas-cobrar-tendencias, distribucion-prestamos, metricas-acumuladas | Todos con `get_db`; datos desde `clientes`, `prestamos`, `cuotas` o listas/ceros cuando no aplica. |
| **validadores** | /configuracion-validadores | Tabla `configuracion` (clave `configuracion_validadores`) o estructura por defecto (definición de reglas, no mock). |

### 2.2 Auth y usuarios (diseño sin tabla users)

| Módulo | Comportamiento |
|--------|----------------|
| **auth** | Login con `ADMIN_EMAIL`/`ADMIN_PASSWORD` (env). `get_current_user` devuelve usuario derivado del token (no consulta BD de usuarios). |
| **usuarios** | Listado devuelve un único usuario admin desde env para asignación en Tickets/Comunicaciones. Sin tabla `users`. |

No se consideran "mock data" porque el diseño es auth sin BD de usuarios.

### 2.3 Configuración AI

| Módulo | Comportamiento |
|--------|----------------|
| **configuracion_ai** | Stub en memoria para modelo/temperatura/max_tokens; la API key **nunca** se guarda en backend. Opcional persistir en tabla `configuracion` en el futuro. |

## 3. Cambios realizados en esta auditoría

1. **Modelo Auditoria**  
   - Creado `app/models/auditoria.py` y tabla `auditoria`.  
   - Registrado en `app/models/__init__.py` y en `main.py` (startup).

2. **pagos.py**  
   - Inyección de `get_db` en `/kpis` y `/stats`.  
   - KPIs y estadísticas desde tablas `Cuota`, `Prestamo`, `Cliente`. Ceros cuando no hay datos.

3. **kpis.py**  
   - Inyección de `get_db` en `/dashboard`.  
   - Datos desde `Prestamo` y `Cuota`.

4. **cobranzas.py**  
   - Inyección de `get_db` en todos los endpoints.  
   - Resumen, diagnóstico, clientes atrasados, por analista, montos por mes, informes y notificaciones/atrasos desde `Cuota`, `Prestamo`, `Cliente`.  
   - PUT/DELETE ml-impago verifican préstamo en BD (404 si no existe).

5. **auditoria.py**  
   - Listado, stats, exportar (Excel con openpyxl o mínimo sin dependencia), GET por id y POST registrar usan tabla `auditoria` y `get_db`.  
   - Eliminados stubs y respuestas vacías/404 por diseño.

6. **configuracion.py**  
   - `/notificaciones/envios`: GET/PUT leen y escriben en tabla `configuracion` (clave `notificaciones_envios`).  
   - `/sistema/completa` y `/sistema/categoria/{categoria}`: cargan desde BD vía `_load_general_from_db(db)`.  
   - `/validadores/probar`: añadido `get_db` por consistencia.

7. **dashboard.py**  
   - Sustituido `_ultimos_12_meses()` (datos demo) por `_etiquetas_12_meses()` (solo etiquetas, valores en cero).  
   - Fallbacks de errores devuelven estructuras con ceros, no datos inventados.  
   - `evolucion-pagos`: datos reales desde `Cuota` (fecha_pago por mes).  
   - `cobranzas-semanales`: datos reales desde `Cuota` (pagos por semana).  
   - Añadido `get_db` a: cobranza-por-dia, cobranzas-mensuales, cobros-por-analista, cobros-diarios, cuentas-cobrar-tendencias, distribucion-prestamos, metricas-acumuladas.  
   - `opciones-filtros`: rellenado desde BD con `Prestamo` (analistas, concesionarios, modelos distintos).

8. **validadores.py**  
   - Inyección de `get_db` en `/configuracion-validadores`.  
   - Lectura desde tabla `configuracion` (clave `configuracion_validadores`) si existe; si no, estructura por defecto (reglas de validación, no datos de negocio mock).

## 4. Resumen de cumplimiento

- **Conexión:** `engine` y `SessionLocal` usan `settings.DATABASE_URL`.  
- **Endpoints de negocio:** Usan `Depends(get_db)` y consultas a BD.  
- **Sin mock data:** Las respuestas provienen de consultas reales; ceros o listas vacías cuando no hay datos, no valores inventados.  
- **Health:** `GET /health/db` sirve para validar la conexión a la BD.
