# Auditoría completa: conexión BD, endpoints y código

**Fecha:** 18 de febrero de 2025  
**Aplicación:** RapiCredit - Sistema de Préstamos y Cobranza  
**URL producción:** https://rapicredit.onrender.com/pagos/prestamos

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| Conexión BD | ✅ Correcta | PostgreSQL con pool, `pool_pre_ping`, conversión `postgres://` → `postgresql://` |
| Endpoints con datos reales | ✅ Cumple | Préstamos, pagos, clientes, dashboard, KPIs usan `Depends(get_db)` |
| Health check BD | ✅ Implementado | `GET /health/db` verifica conexión |
| Configuración proxy | ✅ Mejorado | `render.yaml` usa `fromService` para inyectar URL del backend automáticamente |

### Checklist de verificación post-deploy

- [ ] `GET /health` responde 200
- [ ] `GET /health/db` responde `{"database":"connected"}`
- [ ] Login funciona (frontend → backend)
- [ ] Listado de préstamos carga datos reales

---

## 2. Conexión a base de datos

### 2.1 Configuración (`backend/app/core/config.py`)

- **`DATABASE_URL`**: Obligatoria (`Field(..., description="URL de conexión a PostgreSQL")`).
- Carga desde `.env` o variables de entorno.
- Sin valor por defecto: la aplicación no arranca sin BD configurada.

### 2.2 Motor y sesión (`backend/app/core/database.py`)

```python
# Conversión postgres:// → postgresql:// (compatibilidad Render)
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    _db_url,
    pool_pre_ping=True,      # Verifica conexión antes de usar
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Evita F405 en serialización
)
```

**Evaluación:** Configuración adecuada para producción (pool, pre-ping, compatibilidad con Render).

### 2.3 Dependencia `get_db`

- Generador que crea una sesión por request y la cierra al terminar.
- Usada en todos los endpoints que acceden a BD.

### 2.4 Inicio con reintentos (`main.py`)

- `_startup_db_with_retry()`: hasta 5 intentos con 2 s de espera.
- Crea tablas con `Base.metadata.create_all()` si no existen.
- Evita fallos por BD aún no lista en Render.

### 2.5 Health check BD

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | Estado general del servicio |
| `GET /health/db` | Verifica BD con `SELECT 1`; 503 si falla |

---

## 3. Endpoints y uso de BD

### 3.1 Préstamos (`/api/v1/prestamos`)

| Método | Ruta | BD | Descripción |
|--------|------|-----|-------------|
| GET | `/` | ✅ | Listado paginado con join Cliente |
| GET | `/stats` | ✅ | Estadísticas mensuales (clientes ACTIVOS) |
| GET | `/cedula/{cedula}` | ✅ | Préstamos por cédula |
| GET | `/cedula/{cedula}/resumen` | ✅ | Resumen por cédula |
| GET | `/{prestamo_id}` | ✅ | Detalle con join Cliente |
| GET | `/{prestamo_id}/cuotas` | ✅ | Cuotas del préstamo |
| GET | `/{prestamo_id}/evaluacion-riesgo` | ✅ | Datos de evaluación de riesgo |
| GET | `/{prestamo_id}/auditoria` | ✅ | Registros de auditoría |
| POST | `/` | ✅ | Crear préstamo |
| POST | `/{prestamo_id}/generar-amortizacion` | ✅ | Generar tabla de amortización |
| POST | `/{prestamo_id}/aplicar-condiciones-aprobacion` | ✅ | Aplicar condiciones |
| POST | `/{prestamo_id}/evaluar-riesgo` | ✅ | Evaluar riesgo |
| POST | `/{prestamo_id}/asignar-fecha-aprobacion` | ✅ | Asignar fecha aprobación |
| POST | `/{prestamo_id}/aprobar-manual` | ✅ | Aprobación manual (admin) |
| PATCH | `/{prestamo_id}/marcar-revision` | ✅ | Marcar requiere_revision |
| PUT | `/{prestamo_id}` | ✅ | Actualizar préstamo |
| DELETE | `/{prestamo_id}` | ✅ | Eliminar (borra cuotas antes) |

Todos usan `Depends(get_db)` y consultas reales a BD.

### 3.2 Pagos (`/api/v1/pagos`)

| Método | Ruta | BD | Descripción |
|--------|------|-----|-------------|
| GET | `/` | ✅ | Listado paginado |
| GET | `/ultimos` | ✅ | Últimos pagos por cédula |
| GET | `/kpis` | ✅ | KPIs del mes (clientes ACTIVOS) |
| GET | `/stats` | ✅ | Estadísticas |
| GET | `/{pago_id}` | ✅ | Detalle de pago |
| GET | `/exportar/errores` | ✅ | Excel de pagos con errores |
| POST | `/` | ✅ | Crear pago |
| POST | `/upload` | ✅ | Carga masiva Excel |
| POST | `/conciliacion/upload` | ✅ | Conciliación Excel |
| POST | `/{pago_id}/aplicar-cuotas` | ✅ | Aplicar pago a cuotas |
| PUT | `/{pago_id}` | ✅ | Actualizar pago |
| DELETE | `/{pago_id}` | ✅ | Eliminar pago |

### 3.3 Dashboard (`/api/v1/dashboard`)

| Método | Ruta | BD | Descripción |
|--------|------|-----|-------------|
| GET | `/opciones-filtros` | ✅ | Analistas, concesionarios, modelos |
| GET | `/kpis-principales` | ✅ | KPIs principales |
| GET | `/admin` | ✅ | Datos admin (caché 6h, 13h, 16h) |
| GET | `/cobros-diarios` | ✅ | Cobros diarios |
| GET | `/morosidad-por-dia` | ✅ | Morosidad por día |
| GET | `/evolucion-morosidad` | ✅ | Evolución morosidad |
| GET | `/financiamiento-por-rangos` | ✅ | Financiamiento por rangos |
| GET | `/prestamos-por-modelo` | ✅ | Préstamos por modelo |
| GET | `/composicion-morosidad` | ✅ | Composición morosidad |
| GET | `/cobranzas-semanales` | ✅ | Cobranzas semanales |
| GET | `/morosidad-por-analista` | ✅ | Morosidad por analista |
| GET | `/monto-programado-proxima-semana` | ✅ | Monto programado |
| GET | `/cobranza-por-dia` | ✅ | Cobranza por día |
| GET | `/metricas-acumuladas` | ✅ | Métricas acumuladas |

Todos usan datos reales de BD (clientes ACTIVOS, préstamos APROBADOS).

### 3.4 Otros módulos con BD

| Módulo | Prefijo | BD |
|--------|---------|-----|
| Auth | `/api/v1/auth` | ✅ (usuarios, tokens) |
| Clientes | `/api/v1/clientes` | ✅ |
| Tickets | `/api/v1/tickets` | ✅ |
| Comunicaciones | `/api/v1/comunicaciones` | ✅ |
| Reportes | `/api/v1/reportes` | ✅ |
| Cobranzas | `/api/v1/cobranzas` | ✅ |
| Auditoría | `/api/v1/auditoria` | ✅ |
| KPIs | `/api/v1/kpis` | ✅ |
| Configuración | `/api/v1/configuracion` | ✅ |
| Modelos vehículos | `/api/v1/modelos-vehiculos` | ✅ |
| Concesionarios | `/api/v1/concesionarios` | ✅ |
| Analistas | `/api/v1/analistas` | ✅ |

---

## 4. Arquitectura frontend–backend

### 4.1 Flujo de peticiones

```
Usuario → https://rapicredit.onrender.com/pagos/prestamos (frontend SPA)
                ↓
         Petición /api/v1/prestamos (con Bearer token)
                ↓
         server.js (Express) → proxy /api/* → API_BASE_URL
                ↓
         Backend FastAPI (URL configurada en API_BASE_URL)
```

### 4.2 Configuración actual

**Blueprint raíz (`render.yaml`):** El frontend obtiene `API_BASE_URL` automáticamente desde el backend:

```yaml
envVars:
  - key: API_BASE_URL
    fromService:
      name: pagos-backend
      type: web
      envVarKey: RENDER_EXTERNAL_URL
```

Render inyecta `RENDER_EXTERNAL_URL` en cada servicio web con su URL pública. Así el frontend siempre apunta al backend correcto sin configuración manual.

**Despliegue standalone (`frontend/render.yaml`):** Si se despliega solo el frontend, configurar `API_BASE_URL` en Render Dashboard con la URL del backend (ej. `https://pagos-backend.onrender.com`).

---

## 5. Autenticación y seguridad

- Endpoints protegidos usan `Depends(get_current_user)`.
- `get_current_user` valida Bearer JWT y consulta tabla `usuarios` o usa admin desde env.
- Préstamos, pagos, dashboard, clientes, etc. requieren token válido.

---

## 6. Regla de datos reales

Según `.cursor/rules/datos-reales-bd.mdc`:

- No usar stubs ni datos demo en endpoints que deban mostrar información real.
- Usar siempre `Depends(get_db)` en endpoints que lean o escriban datos.
- La auditoría confirma que los endpoints principales cumplen esta regla.

---

## 7. Verificación en producción

### Comandos sugeridos

```bash
# Script de verificación (health + BD)
./scripts/verificar-backend.sh https://pagos-backend.onrender.com

# O manualmente:
curl https://<BACKEND_URL>/health
curl https://<BACKEND_URL>/health/db

# Préstamos (requiere token)
curl -H "Authorization: Bearer <TOKEN>" "https://<BACKEND_URL>/api/v1/prestamos?page=1&per_page=5"
```

### Nota sobre la URL

- `https://rapicredit.onrender.com/pagos/prestamos` sirve la SPA (login si no hay sesión).
- Las llamadas API van a `/api/v1/*` y son reenviadas por el proxy al backend.
- Si el backend está en otro host, usar su URL en las pruebas con `curl`.

---

## 8. Conclusiones

| Aspecto | Resultado |
|---------|-----------|
| Conexión BD | Correcta: pool, pre-ping, reintentos en startup |
| Endpoints | Usan datos reales y `get_db` |
| Health check | Implementado para BD |
| Proxy frontend | `fromService` inyecta URL del backend automáticamente |
| Seguridad | JWT y `get_current_user` en endpoints protegidos |

---

## 9. Acciones recomendadas

1. **Blueprint raíz:** Si usas `render.yaml` en la raíz, `API_BASE_URL` se inyecta automáticamente desde `pagos-backend`.
2. **Probar `/health/db`:** Confirmar que el backend responde tras el deploy: `curl https://<BACKEND_URL>/health/db`
3. **Despliegue standalone:** Si despliegas solo el frontend, configurar `API_BASE_URL` en Render Dashboard.
