# Revisión integral del sistema

**Fecha:** 2026-03-10  
**Alcance:** Conexión BD, endpoints, tablas, procesos, reglas de negocio, linter.

---

## 1. Conexión a base de datos

### 1.1 Configuración

- **`app/core/database.py`**: Engine con `pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, timezone `America/Caracas` por conexión.
- **URL**: `settings.DATABASE_URL` (postgres:// se reemplaza por postgresql://).
- **Sesión**: `SessionLocal` con `expire_on_commit=False` (evita errores F405 en serialización).
- **Dependencia**: `get_db()` cede una sesión por request y cierra en `finally`.

### 1.2 Uso en endpoints

- Los endpoints que necesitan BD inyectan `db: Session = Depends(get_db)`.
- **Auth**: login, refresh, me, forgot_password, admin/reset-password usan `get_db` y tabla `usuarios` (modelo `User`).
- **Deps**: `get_current_user` y `get_current_user_optional` usan `get_db` para resolver usuario por email desde `usuarios`.
- **Módulos revisados** (todos usan get_db donde corresponde):
  - clientes, prestamos, pagos, pagos_con_errores, revisar_pagos, cuota_pagos
  - cobros, cobros_publico (formulario público)
  - usuarios, auth, configuracion, configuracion_email, configuracion_whatsapp, configuracion_informe_pagos, configuracion_ai
  - tickets, comunicaciones, notificaciones, notificaciones_tabs
  - dashboard/kpis, dashboard/graficos
  - reportes (morosidad, pagos, contable, cartera, etc.)
  - revision_manual, analistas, concesionarios, modelos_vehiculos
  - validadores (lee `configuracion` para configuración de validadores)
  - health (db, cobros, detailed)
  - auditoria, pagos_gmail

**Conclusión:** La conexión a BD está centralizada y los endpoints que requieren datos reales usan la sesión inyectada correctamente.

---

## 2. Endpoints y tablas requeridas

### 2.1 Tablas críticas (health/db)

| Tabla               | Uso principal                                      | Endpoints / modelos que la usan                          |
|---------------------|----------------------------------------------------|----------------------------------------------------------|
| clientes            | CRUD clientes, préstamos, reportes, comunicaciones | clientes, prestamos, comunicaciones, cobros_publico, dashboard, reportes, revision_manual |
| prestamos           | Préstamos, cuotas, pagos, KPIs                     | prestamos, pagos, cuotas, dashboard, reportes, revision_manual, analistas, concesionarios |
| cuotas              | Morosidad, aplicación de pagos, reportes           | pagos, cuota_pagos, dashboard, reportes                  |
| pagos               | Registro de pagos, conciliación                    | pagos, pagos_con_errores, revisar_pagos, cuota_pagos, reportes |
| pagos_con_errores   | Revisar pagos (carga masiva con error)             | pagos_con_errores, pagos (importar desde Cobros)         |
| revisar_pagos       | Pagos exportados a Excel para revisión             | pagos, pagos_con_errores                                 |
| cuota_pagos         | Historial de aplicación pago → cuota              | pagos (aplicar cuotas)                                   |
| pagos_whatsapp      | Imágenes recibidas por WhatsApp                    | whatsapp, comunicaciones, pagos_informes                 |
| tickets             | CRM                                                | tickets                                                  |
| pagos_reportados    | Módulo Cobros (reporte público + admin)            | cobros, cobros_publico                                   |
| usuarios            | Auth y gestión de usuarios                         | auth, usuarios, deps (get_current_user), cobros (usuario_gestion_id) |

### 2.2 Configuración y otras tablas

- **configuracion**: config general, logo, email, validadores, WhatsApp, informe-pagos, AI (configuracion.py, configuracion_*.py, validadores).
- **pagos_reportados_historial**: historial de cambios de estado en Cobros (cobros.py).
- **User** (tabla `usuarios`): auth, usuarios, get_current_user.

**Conclusión:** Todas las tablas listadas en health/db están referenciadas por modelos y endpoints. No se detectan endpoints que deban usar BD y no la usen.

---

## 3. Procesos coherentes

- **Cobros (público):** validar cédula → enviar reporte → Gemini compara formulario vs imagen → aprobado (recibo por correo) o en_revision. Usa `clientes`, `prestamos`, `pagos_reportados`; búsqueda de cliente por cédula normalizada (con/sin guión).
- **Cobros (admin):** listado, detalle, aprobar/rechazar con envío de correo; historial en `pagos_reportados_historial`.
- **Pagos:** listado, CRUD, carga masiva, importar desde Cobros (solo aprobados); regla de no duplicados por `numero_documento`; aplicación a cuotas vía `cuota_pagos`.
- **Revisar pagos:** exportar a Excel → registros en `revisar_pagos`; mover a pagos desde revisar_pagos.
- **Auth:** login contra `usuarios`; refresh y me con token; forgot_password notifica; admin reset-password alinea BD con ADMIN_PASSWORD.
- **Dashboard/KPIs:** datos desde clientes, prestamos, cuotas, pagos; filtros por analista, concesionario, modelo; caché local con TTL.

**Conclusión:** Los flujos revisados son coherentes con el uso de las tablas y dependencias entre módulos.

---

## 4. Reglas de negocio existentes y coherencia

### 4.1 Clientes

- **Cédula:** Única salvo valor especial `Z999999999` (migración `migracion_cedula_z999999999_repetible.sql`). En código: no duplicar cédula (ni nombre completo, ni email, ni teléfono) con otro cliente distinto; 409 si duplicado.
- **Comunicaciones / alta desde Comunicaciones:** Misma lógica de duplicados (cédula, email, teléfono); normalización y reemplazo a valores por defecto si vacío o inválido (ej. +589999999999, revisar@email.com).
- **Búsqueda cédula:** En Cobros y en importar-desde-Cobros se usa búsqueda normalizada (REPLACE(cedula,'-','')) para aceptar con o sin guión en BD.

### 4.2 Pagos

- **Nº documento:** Regla general: no duplicados en todo el sistema. En BD: columna `numero_documento` con `unique=True` en modelo. En carga masiva e importar desde Cobros: validación explícita contra BD y dentro del lote; 409 si duplicado.
- **Formato:** Se aceptan todos los formatos (BNC/, BINANCE, REF, etc.); límite 100 caracteres; clave canónica vía `normalize_documento` (core/documento.py) para comparación.
- **Cédula en pagos:** En importar desde Cobros y carga masiva se normaliza (strip, uppercase); búsqueda de cliente por cédula normalizada (con/sin guión). Coherente con regla de clientes.

### 4.3 Préstamos y cuotas

- **Prestamos:** FK a clientes; estados (DRAFT, APROBADO, DESEMBOLSADO, etc.); filtros por analista, concesionario, modelo.
- **Cuotas:** FK a prestamos, pagos, clientes; aplicación de pagos vía `cuota_pagos` con orden FIFO; reglas de mora y estados.

### 4.4 Cobros (pagos_reportados)

- Solo reportes **aprobados** se importan a Pagos; mismos criterios que carga masiva (documento único, 1 crédito activo por cédula, etc.). Los que no cumplen van a pagos_con_errores con observación "Cobros (reportados aprobados)".
- Referencia interna única (RPC-YYYYMMDD-XXXXX); estado (pendiente, en_revision, aprobado, rechazado); Gemini (coincide_exacto, comentario).

**Conclusión:** Las reglas de negocio revisadas son coherentes entre clientes, pagos, préstamos, cuotas y Cobros; duplicados y normalización están alineados.

---

## 5. Linter

- **Herramienta:** Linter del IDE (Cursor/VSCode) sobre `backend/app`.
- **Resultado:** No se reportan errores de linter en los archivos revisados.
- **Sintaxis:** `python -m py_compile app/main.py` ejecutado correctamente en backend.

**Recomendación:** Incluir en CI (si existe) un paso tipo `ruff check` o `flake8` sobre `backend/app` para mantener estilo y detección de errores estáticos.

---

## 6. Resumen y recomendaciones

| Área              | Estado   | Nota                                                                 |
|-------------------|----------|----------------------------------------------------------------------|
| Conexión BD       | Correcto | get_db inyectado donde corresponde; pool y timezone configurados.    |
| Endpoints ↔ BD    | Correcto | Endpoints que requieren datos usan sesión y modelos correctos.      |
| Tablas requeridas | Correcto | Las 11 tablas de health/db están usadas por la API.                  |
| Procesos          | Coherente| Flujos Cobros, Pagos, Auth, Dashboard alineados con las tablas.     |
| Reglas de negocio | Coherente| Cédula, documento único, duplicados y normalización consistentes.    |
| Linter            | Sin errores | Revisión estática sin hallazgos.                                  |

### Acciones opcionales

1. **CI:** Añadir paso de lint (ruff/flake8) y, si se desea, tests de integración contra health/db y health/cobros.
2. **Documentación:** Mantener este documento actualizado cuando se añadan tablas críticas o reglas de negocio nuevas.
3. **Monitoreo:** Usar GET /api/v1/health/db y GET /api/v1/health/cobros en alertas (Render, Uptime Robot, etc.) para detectar caídas de BD o configuración incompleta.
