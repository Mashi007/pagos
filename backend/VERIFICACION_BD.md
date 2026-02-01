# Verificación: conexión a la base de datos

## Estado actual

| Componente | Estado | Detalle |
|------------|--------|---------|
| **Config** | ✅ | `app/core/config.py` define `DATABASE_URL` (obligatorio). |
| **Dependencias** | ✅ | `requirements.txt` incluye `sqlalchemy`, `psycopg2-binary`, `alembic`. |
| **Módulo de BD** | ✅ | `app/core/database.py`: engine, `SessionLocal`, `get_db()`, y normalización `postgres://` → `postgresql://`. |
| **Verificación** | ✅ | `GET /health/db`: ejecuta `SELECT 1` contra la BD; 200 = conectada, 503 = error. |
| **Modelos** | ✅ | `app/models/cliente.py`: modelo **Cliente** con campos alineados al frontend. |
| **Schemas** | ✅ | `app/schemas/cliente.py`: ClienteCreate, ClienteUpdate, ClienteResponse. |
| **Tablas** | ✅ | `main.py` startup: `Base.metadata.create_all(bind=engine)` crea tabla `clientes`. |
| **Endpoints clientes** | ✅ | Conectados a BD: listado (paginado, search, estado), stats, GET/POST/PUT/DELETE/PATCH estado. |

## Tabla `clientes` (campos)

- id, cedula, nombres, telefono, email, direccion, fecha_nacimiento, ocupacion  
- total_financiamiento, cuota_inicial, monto_financiado, fecha_entrega, numero_amortizaciones, modalidad_pago  
- estado, activo, estado_financiero, dias_mora  
- fecha_registro, fecha_actualizacion, usuario_registro, notas  

## Conclusión

- **Conexión**: Engine y sesión configurados; `GET /health/db` verifica la conexión.
- **Clientes**: Modelo, schemas y endpoints de clientes usan la BD real.
- **Otros**: Dashboard, pagos, etc. siguen como stubs hasta añadir sus modelos.
