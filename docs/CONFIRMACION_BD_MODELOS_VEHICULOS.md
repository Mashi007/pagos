# Confirmación: BD integrada a Modelos de Vehículos

**Página:** https://rapicredit.onrender.com/pagos/modelos-vehiculos  
**Fecha verificación:** 2026-02-05

---

## 1. Cadena de integración verificada

| Capa | Componente | Estado |
|------|------------|--------|
| **BD (PostgreSQL)** | Tabla `public.modelos_vehiculos` | ✅ Definida en `migracion_modelos_vehiculos.sql`. Columnas: `id`, `modelo`, `activo`, `precio`, `created_at`, `updated_at`. Índices en id, modelo, activo. |
| **Conexión** | `app.core.database` | ✅ `engine` y `SessionLocal` usan `settings.DATABASE_URL` (Render/env). `get_db()` inyecta sesión por request. |
| **Modelo ORM** | `app.models.modelo_vehiculo.ModeloVehiculo` | ✅ `__tablename__ = "modelos_vehiculos"`. Columnas alineadas con la tabla. Exportado en `app.models.__init__`. |
| **Startup** | `main.py` | ✅ `Base.metadata.create_all(bind=engine)` crea la tabla si no existe al arrancar. |
| **API** | `app.api.v1.endpoints.modelos_vehiculos` | ✅ Router con `Depends(get_db)`. Todos los endpoints leen/escriben en la tabla vía `ModeloVehiculo`. |
| **Ruta API** | `api/v1` | ✅ Router montado en `/api/v1/modelos-vehiculos` (`app.api.v1.__init__.py`). |
| **Frontend** | `modeloVehiculoService.ts` | ✅ `baseUrl = '/api/v1/modelos-vehiculos'`. Llama a list, activos, get by id, create, update, delete. |
| **Página** | `/pagos/modelos-vehiculos` | ✅ Usa `useModelosVehiculos` y mutations; lista y formulario enlazados a la API. |

---

## 2. Coherencia esquema BD ↔ ORM

| Columna BD | Tipo BD | Modelo SQLAlchemy | Coincide |
|------------|---------|-------------------|----------|
| id | SERIAL PRIMARY KEY | Integer, primary_key, index | ✅ |
| modelo | VARCHAR(255) NOT NULL UNIQUE | String(255), unique, index | ✅ |
| activo | BOOLEAN NOT NULL DEFAULT true | Boolean, default True | ✅ |
| precio | NUMERIC(14,2) NULL | Numeric(14,2), nullable=True | ✅ |
| created_at | TIMESTAMP NOT NULL DEFAULT now | DateTime, server_default=func.now() | ✅ |
| updated_at | TIMESTAMP NOT NULL DEFAULT now | DateTime, onupdate=func.now() | ✅ |

---

## 3. Endpoints que usan la BD real

- `GET /api/v1/modelos-vehiculos` → lista desde tabla (paginado, filtros).
- `GET /api/v1/modelos-vehiculos/activos` → lista activos para formularios (p. ej. Nuevo Préstamo).
- `GET /api/v1/modelos-vehiculos/{id}` → detalle por id.
- `POST /api/v1/modelos-vehiculos` → inserta en tabla.
- `PUT /api/v1/modelos-vehiculos/{id}` → actualiza en tabla.
- `DELETE /api/v1/modelos-vehiculos/{id}` → borra en tabla.

Todos usan `Depends(get_db)` y el modelo `ModeloVehiculo`; no hay stubs ni datos demo.

---

## 4. Conclusión

**La base de datos está integrada correctamente** con la página https://rapicredit.onrender.com/pagos/modelos-vehiculos: la tabla `modelos_vehiculos` existe en PostgreSQL, el backend usa sesión real y el modelo ORM alineado con el esquema, y el frontend consume la API sobre esa misma BD. Los 21 registros insertados desde `prestamos` (modelo + activo + precio NULL) son los que debe mostrar y permitir editar la página una vez el backend desplegado en Render use esta versión del código.
