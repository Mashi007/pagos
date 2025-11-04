# 🔍 VERIFICACIÓN DE DEPLOY EN PROCESO

## ✅ Estado del Repositorio

**Último commit pusheado:**
- Commit: `7d0bd5a7`
- Mensaje: "docs: Análisis de riesgos de migración de índices funcionales"
- Fecha: Reciente
- Estado: ✅ Sincronizado con `origin/main`

**Migración pendiente:**
- `20251104_add_group_by_indexes` - Índices funcionales para GROUP BY

---

## 📋 CÓMO VERIFICAR EL DEPLOY EN RENDER

### Paso 1: Acceder a Render Dashboard

1. **Ir a**: https://dashboard.render.com
2. **Iniciar sesión** con tus credenciales
3. **Seleccionar servicio**: `pagos-backend` (o `pagos-f2qf`)

---

### Paso 2: Verificar Estado del Deploy

En la página principal del servicio, busca:

#### ✅ DEPLOY EN PROCESO:
```
Status: Deploying...
Commit: 7d0bd5a7
Message: docs: Análisis de riesgos...
Started: [timestamp]
```

#### ✅ DEPLOY COMPLETADO:
```
Status: Live
Commit: 7d0bd5a7
Message: docs: Análisis de riesgos...
Deployed: [timestamp] ago
```

#### ⚠️ DEPLOY FALLIDO:
```
Status: Deploy failed
Commit: 7d0bd5a7
Error: [mensaje de error]
```

---

### Paso 3: Revisar Logs del Release Command

En la pestaña **"Logs"** del servicio, busca la sección **"Release"**:

#### ✅ LOGS ESPERADOS (ÉXITO):

```
Running release command: cd backend && alembic upgrade heads

🚀 Iniciando migración de índices funcionales para GROUP BY...
✅ Índice funcional 'idx_pagos_staging_extract_year' creado para GROUP BY YEAR
✅ Índice compuesto funcional 'idx_pagos_staging_extract_year_month' creado para GROUP BY YEAR, MONTH
✅ Índice compuesto funcional 'idx_cuotas_extract_year_month' creado para GROUP BY YEAR, MONTH

📊 Actualizando estadísticas de tablas...
✅ ANALYZE ejecutado en 'pagos_staging'
✅ ANALYZE ejecutado en 'cuotas'

✅ Migración de índices funcionales para GROUP BY completada
📈 Impacto esperado: Reducción de tiempos de GROUP BY de 17-31s a <2s
```

#### ⚠️ LOGS DE ADVERTENCIA (Aceptables):

Si ves estos mensajes, es normal (significa que el índice ya existía):

```
ℹ️ Índice 'idx_pagos_staging_extract_year_month' ya existe, omitiendo...
ℹ️ Columna 'fecha_pago' no existe en 'pagos_staging', omitiendo...
```

#### ❌ LOGS DE ERROR (PROBLEMA):

```
⚠️ Advertencia: No se pudo crear índice 'idx_xxx': [error]
❌ Error ejecutando migración: [error]
```

**Si ves errores**, revisar:
- Permisos de la base de datos
- Conexión a PostgreSQL
- Tamaño de la tabla (puede requerir más tiempo)

---

### Paso 4: Verificar Logs del Servidor

Después del deploy, en los logs del servidor, busca:

#### ✅ LOGS ESPERADOS (ÉXITO):

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
✅ Todos los routers registrados correctamente
Database connection successful
```

---

## 🔍 VERIFICACIÓN RÁPIDA (SIN ACCESO A RENDER DASHBOARD)

### Opción 1: Health Check

```bash
curl https://pagos-f2qf.onrender.com/api/v1/health/render
```

**Esperado**: `{"status": "healthy", "service": "pagos-api"}`

**Si responde**: ✅ El servidor está activo

---

### Opción 2: Verificar Tiempos de Respuesta

Probar endpoints que deberían mejorar después de la migración:

```bash
# Antes: 9-32 segundos
# Después (esperado): <2 segundos

curl -X GET "https://pagos-f2qf.onrender.com/api/v1/dashboard/evolucion-pagos?meses=6" \
  -H "Authorization: Bearer [TOKEN]"
```

**Si responde en <2s**: ✅ Índices funcionando
**Si responde en >10s**: ⚠️ Índices no se crearon o no se están usando

---

## 📊 ESTIMACIÓN DE TIEMPO

### Timeline Esperado:

1. **Git Push**: ✅ Completado (commit `7d0bd5a7`)
2. **Render detecta cambio**: ⏳ Inmediato (auto-deploy activado)
3. **Build Phase**: ⏳ 2-5 minutos
4. **Release Phase (Migración)**: ⏳ 2-5 minutos
   - Crear índices: 2-5 minutos
   - ANALYZE tablas: 30-60 segundos
5. **Start Phase**: ⏳ 1-2 minutos
6. **Total**: ⏳ 5-12 minutos desde el push

**Tiempo transcurrido desde push**: Verificar en Render Dashboard

---

## 🎯 SEÑALES DE ÉXITO

### ✅ Deploy Exitoso:

1. ✅ Status: "Live" en Render Dashboard
2. ✅ Logs muestran creación de índices
3. ✅ Health check responde 200 OK
4. ✅ Endpoints responden más rápido (<2s)

### ⚠️ Deploy en Proceso:

1. ⏳ Status: "Deploying..." en Render Dashboard
2. ⏳ Logs muestran "Building..." o "Running release command..."
3. ⏳ Health check puede no responder aún

### ❌ Deploy Fallido:

1. ❌ Status: "Deploy failed" en Render Dashboard
2. ❌ Logs muestran errores específicos
3. ❌ Health check no responde

---

## 🚨 PLAN DE CONTINGENCIA

### Si el Deploy Falla:

1. **Revisar logs de error** en Render Dashboard
2. **Verificar variables de entorno** (DATABASE_URL, etc.)
3. **Reintentar deploy**:
   - Manual Deploy → "Clear build cache & deploy"
4. **Si falla la migración**:
   - Verificar permisos de BD
   - Verificar tamaño de tablas
   - Ejecutar migración manualmente si es necesario

### Si los Índices No Se Crean:

1. **Verificar en PostgreSQL**:
   ```sql
   SELECT indexname, indexdef 
   FROM pg_indexes 
   WHERE tablename IN ('pagos_staging', 'cuotas')
   AND indexname LIKE 'idx_%_extract%';
   ```

2. **Crear manualmente** (si es necesario):
   ```sql
   CREATE INDEX CONCURRENTLY idx_pagos_staging_extract_year_month
   ON pagos_staging USING btree (
     EXTRACT(YEAR FROM fecha_pago::timestamp),
     EXTRACT(MONTH FROM fecha_pago::timestamp)
   )
   WHERE fecha_pago IS NOT NULL AND fecha_pago != '';
   ```

---

## 📝 CHECKLIST DE VERIFICACIÓN

- [ ] Verificar estado en Render Dashboard (Live/Deploying/Failed)
- [ ] Revisar logs del Release Command (buscar mensajes de índices)
- [ ] Verificar Health Check responde
- [ ] Probar endpoint `/dashboard/evolucion-pagos` y medir tiempo
- [ ] Si todo OK, marcar como completado ✅

---

**Última actualización**: Verificando deploy del commit `7d0bd5a7`

