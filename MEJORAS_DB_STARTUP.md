# Mejoras Implementadas: Startup de Base de Datos y Health Check

## Problema Original
El error `SQL Error [42P01]: ERROR: relation "prestamo" does not exist` en Render indicaba que la tabla `prestamos` no estaba siendo creada correctamente durante el startup de la aplicación.

## Causas Identificadas
1. **Retry logic insuficiente**: Solo 5 intentos con delay de 2 segundos podrían no ser suficientes
2. **Sin verificación de tablas críticas**: El startup completaba "exitosamente" aunque las tablas no existieran
3. **Sin logging detallado**: Difícil debuggear problemas en Render
4. **Timeout de conexión no configurado**: PostgreSQL en Render podía no responder rápido

## Mejoras Implementadas

### 1. **`app/main.py` - Función `_startup_db_with_retry` Mejorada**

```python
def _startup_db_with_retry(engine, max_attempts: int = 10, delay_sec: float = 3.0):
    """
    Cambios:
    - max_attempts: 5 → 10 (mayor tolerancia a retrasos)
    - delay_sec: 2.0 → 3.0 (más tiempo inicial)
    - Backoff exponencial: 3s, 4.5s, 6.75s, ... (no espera fija)
    - Verificación explícita de tabla 'prestamos'
    - Logging detallado con [DB Startup] prefix para fácil grep en Render
    - Retorna RuntimeError con mensaje claro en caso de fallo
    """
```

**Mejoras clave:**
- **10 intentos en lugar de 5**: Total ~45 segundos de tolerancia (vs ~10 segundos antes)
- **Backoff exponencial**: Evita saturar la BD con reconexiones rápidas
- **Verificación explícita**: Usa `inspector.get_table_names()` para confirmar que `prestamos` existe
- **Validación de acceso**: `SELECT COUNT(*) FROM prestamos` confirma acceso actual
- **Logging [DB Startup]**: Fácil de filtrar en los logs de Render

### 2. **`app/core/database.py` - Configuración de Engine Mejorada**

```python
engine = create_engine(
    _db_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "connect_timeout": 10,  # ← NUEVO: timeout inicial de 10s
        "application_name": "rapicredit_backend",
    },
    echo=False,  # Cambiar a True para debug SQL
)
```

**Mejoras:**
- **`connect_timeout: 10`**: PostgreSQL tiene 10 segundos para responder (vs default del driver)
- **`application_name`**: Identifica la aplicación en logs de PostgreSQL

### 3. **Endpoint `/health/db` Nuevo**

```
GET /health/db
```

**Verifica:**
- Conexión a BD
- Existencia de 5 tablas críticas (clientes, prestamos, cuotas, pagos_whatsapp, tickets)
- Acceso a tabla prestamos
- Cantidad de registros

**Retorna:**
```json
{
  "status": "ok",
  "db_connected": true,
  "tables_exist": {
    "clientes": true,
    "prestamos": true,
    "cuotas": true,
    "pagos_whatsapp": true,
    "tickets": true
  },
  "prestamos_count": 1250,
  "error": null
}
```

**Configurado en `render.yaml`:**
```yaml
healthCheckPath: /health/db
```

Render hace healthchecks periódicos. Si falla, reinicia el servicio automáticamente.

### 4. **Endpoint `/health/detailed` Nuevo**

```
GET /health/detailed
```

Para desarrollo y debugging. Retorna:
- Todas las tablas en la BD
- Counts de tablas principales
- Estado del pool de conexiones
- URL de BD (sin credenciales)
- Ambiente actual

### 5. **Script `scripts/health_check_db.py` Nuevo**

```bash
python scripts/health_check_db.py
```

Verificación local antes de deploy. Retorna código 0 si todo está bien, 1 si hay errores.

## Cómo Usar

### Test Local
```bash
cd backend
python scripts/health_check_db.py
```

### Test en Render
```bash
curl https://rapicredit.onrender.com/health/db
# Retorna JSON con estado de la BD
```

### Debug Detallado (dev mode)
```bash
curl https://rapicredit.onrender.com/health/detailed
```

## Flujo de Startup Mejorado

```
1. FastAPI inicia (@app.on_event("startup"))
2. on_startup() ejecuta _startup_db_with_retry()
3. Intento 1: Conecta, crea tablas, verifica tabla 'prestamos'
   - Si falla, espera 3 segundos
4. Intento 2: Reintenta (espera 4.5 segundos si falla)
5. ... (hasta 10 intentos, con backoff exponencial)
6. Si todos fallan: RuntimeError + logging del error final
7. Si éxito: Base de datos lista para requests

Logs visibles:
[DB Startup 1/10] Conectando a base de datos...
[DB Startup] Tablas creadas o ya existentes.
[DB Startup] Conexión básica verificada.
[DB Startup] Tablas en BD: [...]
[DB Startup] ✅ Tabla 'prestamos' verificada exitosamente.
[DB Startup] ✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE
```

## Esperado en Production

- **Startup más robusto**: Tolera retrasos de BD hasta ~45 segundos
- **Monitoreo automático**: Render hace healthchecks en `/health/db`
- **Debugging más fácil**: Logs con [DB Startup] prefix claro
- **Fallback inteligente**: Backoff exponencial evita saturar la BD
- **Validación de tabla crítica**: No arranca si tabla `prestamos` no existe

## Si Aún Hay Errores

1. Verificar `curl https://rapicredit.onrender.com/health/db` → debe retornar `"status": "ok"`
2. Si falla, revisar logs de Render (Console > pagos-backend > Logs)
3. Buscar `[DB Startup]` en los logs para ver el historial de intentos
4. Si sigue siendo `relation "prestamo" does not exist`: 
   - La BD está vacía (nuevo Render PostgreSQL no creó tablas)
   - **Solución**: Ejecutar manualmente:
     ```bash
     # En Render terminal o localmente
     python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine); print('✅ Tablas creadas')"
     ```

## Testing
- [ ] Deploy en Render
- [ ] Verificar `GET /health/db` retorna `status: ok`
- [ ] Cargar Excel en reporte de conciliación
- [ ] Generar y descargar reporte (Excel y PDF)
- [ ] Monitoreo por 5+ minutos sin errores 500

## Próximos Pasos (Opcional)
- [ ] Agregar métrica de "tiempo de startup" en observabilidad
- [ ] Alertas automáticas si healthcheck falla 3+ veces
- [ ] Database seeding inicial (datos default) si BD está vacía
