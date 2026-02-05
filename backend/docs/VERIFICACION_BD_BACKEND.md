# Verificación: lógica y conexión integral del backend con la BD

## 1. Conexión a la base de datos

| Componente | Ubicación | Descripción |
|------------|-----------|-------------|
| **URL** | `app/core/config.py` | `DATABASE_URL` (obligatorio), cargado desde `.env` o variables de entorno |
| **Engine** | `app/core/database.py` | `create_engine(DATABASE_URL)` con `pool_pre_ping=True`, `postgres://` → `postgresql://` |
| **Sesión** | `app/core/database.py` | `SessionLocal`, `expire_on_commit=False` |
| **Dependencia** | `app/core/database.py` | `get_db()` inyecta una sesión por request y la cierra al terminar |

## 2. Health check de BD

- **GET /health** → estado de la app (sin BD).
- **GET /health/db** → ejecuta `SELECT 1` contra el engine; devuelve `database: "connected"` o 503 si falla.

Usar `GET /health/db` para comprobar que la BD configurada responde.

## 3. Uso de `get_db` en endpoints

Todos los endpoints que leen o escriben datos usan `Depends(get_db)` e inyectan `db: Session`:

- **auth** – login, refresh, forgot_password (usuarios/tokens en BD).
- **pagos** – listado, crear, actualizar, eliminar (tabla `pagos`); KPIs y stats desde BD.
- **comunicaciones** – listado desde `conversacion_cobranza`; mensajes desde `mensaje_whatsapp`; crear cliente.
- **whatsapp** – POST /webhook recibe mensajes y pasa `db` a `whatsapp_service.process_incoming_message()` (ConversacionCobranza, PagosInforme, PagosWhatsapp, etc.).
- **configuracion**, **configuracion_informe_pagos**, **configuracion_whatsapp**, **clientes**, **prestamos**, **tickets**, **reportes**, **dashboard**, **cobranzas**, **notificaciones**, **usuarios**, etc. – todos con `db: Session = Depends(get_db)`.

No hay stubs de datos en endpoints que deban mostrar información real; la regla del proyecto es usar la BD configurada.

## 4. Flujos clave que tocan BD

| Flujo | Tablas / uso de BD |
|-------|--------------------|
| **Pagos (módulo /pagos/pagos)** | Tabla `pagos`: listado, GET por id, POST, PUT, DELETE. Modelo alineado con columnas reales (cedula, fecha_pago, referencia_pago, etc.). |
| **Comunicaciones** | `conversacion_cobranza` (listado), `mensaje_whatsapp` (historial), `Cliente` (por teléfono / nombre). |
| **WhatsApp webhook** | `ConversacionCobranza` (estado, cedula, nombre_cliente), `PagosWhatsapp`, `PagosInforme` (OCR + columnas nombre_cliente, estado_conciliacion, telefono), `MensajeWhatsapp`. |
| **Informe de pagos / Sheets** | `pagos_informes` (lectura/escritura con columnas A–J); configuración en tabla `configuracion`. |
| **Dashboard / reportes / KPIs** | Consultas reales a `prestamos`, `cuotas`, `clientes`, `pagos`, etc. |

## 5. Modelos y tablas

- **PagosInforme** (`pagos_informes`): incluye `nombre_cliente`, `estado_conciliacion`, `telefono` (columnas G, H, J del Sheet).
- **Pago** (`pagos`): mapeo a columnas reales (p. ej. `cedula_cliente` → columna `cedula`).
- **ConversacionCobranza**, **PagosWhatsapp**, **MensajeWhatsapp**, **Cliente**, **Prestamo**, etc. – definidos en `app/models/` y usados con la sesión inyectada.

## 6. Cómo comprobar en entorno

1. **Conexión**: `GET https://<host>/health/db` → debe devolver `"database": "connected"`.
2. **Columnas**: ejecutar `backend/sql/verificar_columnas_creadas.sql` en DBeaver para confirmar que existen `nombre_cliente`, `estado_conciliacion`, `telefono` en `pagos_informes`.
3. **Reglas de negocio**: no hay datos demo en endpoints de listados/reportes; todo viene de la BD configurada vía `get_db`.

Resumen: el backend tiene lógica y conexión integral con la BD: configuración desde `DATABASE_URL`, sesión por request con `get_db`, y endpoints y servicios usando esa sesión para leer y escribir en las tablas correspondientes.
