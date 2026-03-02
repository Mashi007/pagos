# Guía de Testing: Mejoras de Startup BD y Health Check

## 1. Testing Local

### Requisitos
- Backend en `backend/` con Python 3.11+
- `.env` configurado con `DATABASE_URL`
- PostgreSQL accesible

### 1.1 Verificar Sintaxis Python
```bash
cd backend
python -m py_compile app/main.py app/core/database.py app/api/v1/endpoints/health.py
# Sin errores = ✅
```

### 1.2 Ejecutar Health Check Script
```bash
cd backend
python scripts/health_check_db.py
```

**Salida exitosa:**
```
2026-03-02 14:30:45,123 - __main__ - INFO - Conectando a: postgresql://user@...
2026-03-02 14:30:46,234 - __main__ - INFO - ✅ Conexión a BD verificada
2026-03-02 14:30:46,340 - __main__ - INFO - ✅ Todas las tablas críticas existen: [...]
2026-03-02 14:30:46,400 - __main__ - INFO - ✅ Tabla 'prestamos' accesible (1250 registros)
============================================================
✅ HEALTH CHECK EXITOSO: Base de datos lista
============================================================
```

**Código de retorno:** 0

### 1.3 Iniciar Backend Localmente
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

En los logs deberías ver:
```
[DB Startup 1/10] Conectando a base de datos...
[DB Startup] Tablas creadas o ya existentes.
[DB Startup] Conexión básica verificada.
[DB Startup] Tablas en BD: [...]
[DB Startup] ✅ Tabla 'prestamos' verificada exitosamente.
[DB Startup] Tabla 'prestamos' contiene 1250 registros.
[DB Startup] ✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE
```

### 1.4 Testear Endpoints Health
```bash
# Health check básico
curl http://localhost:8000/health/
# Retorna: {"status":"ok","message":"API is running"}

# Health check BD
curl http://localhost:8000/health/db
# Retorna: 
# {
#   "status": "ok",
#   "db_connected": true,
#   "tables_exist": {...},
#   "prestamos_count": 1250,
#   "error": null
# }

# Health check detallado
curl http://localhost:8000/health/detailed
# Retorna: tabla counts, pool stats, etc.
```

**Comportamiento esperado:**
- `/health/db` retorna `"status": "ok"` si todo está bien
- `"tables_exist": {"prestamos": true, ...}`
- `"prestamos_count"` > 0 (existe data)

### 1.5 Flujo Completo
1. ✅ Backend startup con [DB Startup] logs
2. ✅ Endpoints health accesibles
3. ✅ Cargar Excel en reporte de conciliación
4. ✅ Generar reporte (Excel o PDF)
5. ✅ Descargar exitosamente

## 2. Testing en Render (Pre-Deploy)

### 2.1 En Local con ENV de Render

Simular el ambiente de Render:
```bash
cd backend

# Exportar ENV variables (copiar desde Render dashboard)
export DATABASE_URL="postgresql://..."
export WHATSAPP_ACCESS_TOKEN="..."
# ... más variables

# Verificar script
python scripts/health_check_db.py

# Debería funcionar sin errores
```

### 2.2 Build Local (Simular Build de Render)

```bash
cd backend

# Instalar dependencies
pip install -r requirements.txt

# Sintaxis check
python -m py_compile app/main.py app/core/database.py

# Health check
python scripts/health_check_db.py

# Si todo pasa: ✅ listo para deploy
```

## 3. Testing en Render (Post-Deploy)

### 3.1 Verificar Deploy Exitoso

Dentro de 5 minutos del deploy:
```bash
# Desde cualquier terminal
curl https://rapicredit.onrender.com/health/db

# Debería retornar:
# {"status":"ok","db_connected":true,"tables_exist":{"prestamos":true,...},...}
```

### 3.2 Revisar Logs en Render Dashboard

Console > pagos-backend > Logs

**Buscar:**
1. `[DB Startup 1/10]` - Inicio del startup
2. `[DB Startup] ✅ Tabla 'prestamos' verificada exitosamente` - ✅ Éxito
3. `[DB Startup] ❌ FALLO CRÍTICO` - ❌ Error (ver línea siguiente para detalle)

**Ejemplos de buenos logs:**
```
[DB Startup 1/10] Conectando a base de datos...
[DB Startup] Tablas creadas o ya existentes.
[DB Startup] Conexión básica verificada.
[DB Startup] Tablas en BD: ['clientes', 'prestamos', 'cuotas', ...]
[DB Startup] ✅ Tabla 'prestamos' verificada exitosamente.
[DB Startup] Tabla 'prestamos' contiene 847 registros.
[DB Startup] ✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE
```

### 3.3 Verificación Automática

Render hace healthchecks automáticos a `/health/db` cada 10 segundos.

**Si falla 3+ veces:** Reinicia automáticamente el servicio

**Monitoreo:**
- Console > pagos-backend > Health → debe mostrar ✅ Healthy

### 3.4 Flujo Operacional Completo

1. **Upload Excel en Reporte de Conciliación:**
   - Verificar respuesta 200 OK
   - Verificar tabla `conciliacion_temporal` se llena

2. **Generar Reporte:**
   - `GET /api/v1/reportes/exportar/conciliacion?formato=excel`
   - Debería retornar Blob (Excel)
   - NO debe retornar HTTP 500

3. **Descargar Reporte:**
   - Frontend descarga y abre Excel
   - Verificar filas y datos correctos

4. **Generar PDF:**
   - `GET /api/v1/reportes/exportar/conciliacion?formato=pdf`
   - Debería retornar PDF válido
   - NO debe retornar HTTP 500

## 4. Troubleshooting

### Problema: `GET /health/db` retorna `"status": "error"`

**Diagnóstico:**
```bash
# Ver detalle del error
curl https://rapicredit.onrender.com/health/db | jq .error

# Ver logs en Render
```

**Causas posibles:**
1. BD no disponible → revisar PostgreSQL en Render
2. Tabla no existe → revisar logs de [DB Startup]
3. Credenciales incorrectas → revisar `DATABASE_URL` en env

**Solución:**
```bash
# Desde Render terminal
python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine); print('✅ Tablas creadas')"

# Luego:
curl https://rapicredit.onrender.com/health/db
```

### Problema: `[DB Startup] ❌ FALLO CRÍTICO tras 10 intentos`

**Logs a revisar:**
```
[DB Startup 1/10] Error: ConnectionRefused: ...
[DB Startup 2/10] Error: ConnectionRefused: ...
...
[DB Startup 10/10] Error: ConnectionRefused: ...
```

**Causas:**
1. PostgreSQL no inicia en Render
2. DATABASE_URL incorrecta
3. Red/firewall bloqueando conexión

**Solución:**
1. Verificar PostgreSQL en Render está ✅ Running
2. Verificar `DATABASE_URL` en env variables
3. Redeploy completo (forzar rebuild)

### Problema: Tabla 'prestamos' no existe tras startup exitoso

**Nota:** Este escenario es poco probable con la mejora, pero:

**Diagnóstico:**
```bash
curl https://rapicredit.onrender.com/health/db

# Si retorna:
# "tables_exist": {"prestamos": false, ...}
```

**Solución:**
1. Render terminal:
```bash
python -c "
from app.core.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('✅ OK')
"
```

2. Redeploy:
```bash
# Desde Render > Deployments > Deploy Latest Commit
```

## 5. Checklist de Deployement

- [ ] `python scripts/health_check_db.py` retorna código 0 localmente
- [ ] Build en Render pasa sin errores
- [ ] `curl /health/db` retorna `"status": "ok"` en Render
- [ ] `curl /health/detailed` muestra todas las tablas
- [ ] Upload Excel en reporte funciona
- [ ] Generar Excel + PDF sin HTTP 500
- [ ] Descargar archivos correctamente
- [ ] Monitoreo por 5+ minutos sin errores
- [ ] Logs en Render no muestran `FALLO CRÍTICO`

## 6. Rollback Plan

Si algo falla en production:

1. **Revert commit:**
```bash
git revert HEAD
git push
```

2. **Redeploy en Render:**
   - Render > Deployments > Deploy Latest Commit

3. **Verificar:**
```bash
curl https://rapicredit.onrender.com/health/db
```

4. **Investigar:**
   - Revisar logs de ambas versiones
   - Comparar cambios en `main.py`, `database.py`
   - Si es tabla: ejecutar SQL manual en Render

## 7. Métricas de Éxito

- **Startup time:** < 30 segundos
- **Health check response:** < 100ms
- **No more "relation prestamo does not exist"**
- **100% availability de endpoints**

## Contacto / Questions

Si hay dudas durante testing:
1. Revisar `MEJORAS_DB_STARTUP.md` para contexto completo
2. Buscar en logs Render por `[DB Startup]`
3. Comparar con ejemplos en esta guía
