# 🔧 Comparación: Gunicorn vs Uvicorn

## Resumen de la Decisión

**Recomendación: Gunicorn con workers Uvicorn** para producción.

## Comparación Detallada

### Gunicorn + Uvicorn Workers (Recomendado para Producción)

**Ventajas:**
- ✅ **Múltiples workers**: Maneja múltiples requests simultáneos
- ✅ **Mejor rendimiento**: Distribuye la carga entre workers
- ✅ **Más robusto**: Mejor manejo de errores y reinicio automático
- ✅ **Escalable**: Fácil agregar más workers según necesidad
- ✅ **Estándar de producción**: Usado en aplicaciones de alto tráfico

**Desventajas:**
- ⚠️ Configuración ligeramente más compleja
- ⚠️ Consume más memoria (cada worker es un proceso)

**Comando:**
```bash
gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

**Cuándo usar:**
- ✅ Producción con tráfico real
- ✅ Necesitas manejar múltiples usuarios simultáneos
- ✅ Quieres mejor rendimiento y estabilidad

### Uvicorn Solo (Para Desarrollo/Cargas Ligeras)

**Ventajas:**
- ✅ **Simple**: Configuración mínima
- ✅ **Rápido de iniciar**: Menos overhead
- ✅ **Bueno para desarrollo**: Hot reload automático
- ✅ **Menor consumo de memoria**: Un solo proceso

**Desventajas:**
- ❌ **Un solo worker**: No maneja bien múltiples requests simultáneos
- ❌ **Menos robusto**: Si falla, todo el servicio cae
- ❌ **No escalable**: No puedes agregar workers fácilmente

**Comando:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Cuándo usar:**
- ✅ Desarrollo local
- ✅ Testing
- ✅ Aplicaciones con muy poco tráfico
- ✅ Prototipos rápidos

## Configuración Recomendada

### Para Producción (Render.com)

**En `render.yaml`:**
```yaml
startCommand: gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --worker-class uvicorn.workers.UvicornWorker
```

**Parámetros explicados:**
- `--bind 0.0.0.0:$PORT`: Escucha en todas las interfaces en el puerto especificado
- `--workers 2`: Usa 2 procesos worker (ajusta según recursos disponibles)
- `--timeout 120`: Timeout de 120 segundos para requests largos
- `--worker-class uvicorn.workers.UvicornWorker`: Usa Uvicorn como worker (necesario para FastAPI)

### Para Desarrollo Local

**En terminal:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## Cálculo de Workers

**Fórmula recomendada:**
```
Workers = (2 × CPU cores) + 1
```

**Ejemplos:**
- 1 CPU core → 3 workers
- 2 CPU cores → 5 workers
- 4 CPU cores → 9 workers

**Para Render.com:**
- Plan gratuito: 1-2 workers (limitado por memoria)
- Plan estándar: 2-4 workers según plan

## Verificación

Después de cambiar a Gunicorn, verifica en los logs:

```
[INFO] Starting gunicorn 23.0.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: uvicorn.workers.UvicornWorker
[INFO] Booting worker with pid: [número]
[INFO] Booting worker with pid: [número]
```

Deberías ver múltiples workers iniciándose.

## Migración

### Paso 1: Actualizar render.yaml
Ya está actualizado con Gunicorn.

### Paso 2: Verificar en Render Dashboard
1. Ve a tu servicio backend en Render
2. Verifica que el Start Command coincida con `render.yaml`
3. Si hay diferencia, actualiza manualmente en el dashboard

### Paso 3: Hacer Deploy
```bash
git add render.yaml
git commit -m "Actualizar a Gunicorn para producción"
git push
```

### Paso 4: Verificar Logs
Después del deploy, revisa los logs para confirmar que Gunicorn está corriendo con múltiples workers.

## Troubleshooting

### Error: "No module named 'uvicorn.workers'"
**Solución**: Asegúrate de que `uvicorn[standard]` esté en `requirements.txt`

### Error: "Address already in use"
**Solución**: Verifica que no haya otro proceso usando el puerto

### Workers no inician
**Solución**: Reduce el número de workers si hay limitaciones de memoria

---

*Documento creado el 2026-02-01*
