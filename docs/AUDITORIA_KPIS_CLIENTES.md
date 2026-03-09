# Auditoría integral: KPIs de Clientes (por qué no se actualizan)

**Fecha:** 2025-03-08  
**Alcance:** Flujo completo de estadísticas de clientes (Total, Activos, Finalizados, **Nuevos Clientes en este mes**) desde BD → API → Frontend → UI.

---

## 1. Flujo de datos

```
┌─────────────────┐     GET /api/v1/clientes/stats      ┌──────────────────┐
│  Tabla clientes │ ──────────────────────────────────► │  Backend FastAPI  │
│  (fecha_registro│                                    │  get_clientes_   │
│   CURRENT_TS)   │ ◄────────────────────────────────── │  stats()         │
└─────────────────┘     JSON: total, activos,          └────────┬─────────┘
                                finalizados, nuevos_este_mes     │
                                                                  │
┌─────────────────┐     useClientesStats()                       │
│  ClientesKPIs   │ ◄── queryKey: ['clientes-stats'] ◄──────────┤
│  (4 tarjetas)   │     clienteService.getStats() ──────────────┘
└─────────────────┘     apiClient.get('/api/v1/clientes/stats')
```

---

## 2. Puntos verificados

### 2.1 Backend

| Punto | Estado | Detalle |
|------|--------|---------|
| Ruta registrada | ✅ | `api_router.include_router(clientes.router, prefix="/clientes")` → GET `/api/v1/clientes/stats` |
| Dependencia BD | ✅ | `get_db` inyectado; consultas contra tabla `clientes` |
| Cálculo `nuevos_este_mes` | ✅ | SQL: `date_trunc('month', fecha_registro) = date_trunc('month', CURRENT_TIMESTAMP)` |
| Respuesta JSON | ✅ | Devuelve `total`, `activos`, `inactivos`, `finalizados`, `nuevos_este_mes` |
| Tipo de dato | ⚠️ | Asegurar que `nuevos_este_mes` sea `int` (PostgreSQL puede devolver tipo que serializa mal) |

### 2.2 Base de datos

| Punto | Estado | Cómo verificar |
|------|--------|----------------|
| Columna `fecha_registro` | ⚠️ | Debe existir y tener `DEFAULT CURRENT_TIMESTAMP` en INSERT |
| Valores NULL | ⚠️ | Si hay filas con `fecha_registro IS NULL`, no cuentan para nuevos_este_mes |
| Zona horaria del servidor | ⚠️ | En Render suele ser UTC; `CURRENT_TIMESTAMP` y la comparación usan la misma referencia |

**Consulta de diagnóstico (ejecutar en la BD):**

```sql
-- Mes actual según la BD
SELECT date_trunc('month', CURRENT_TIMESTAMP) AS mes_actual_bd;

-- Cuántos clientes tienen fecha_registro no nula
SELECT COUNT(*) AS total_con_fecha FROM clientes WHERE fecha_registro IS NOT NULL;

-- Cuántos caen en el mes actual (misma lógica que el endpoint)
SELECT COUNT(*)::int AS nuevos_este_mes
FROM clientes
WHERE fecha_registro IS NOT NULL
  AND date_trunc('month', fecha_registro) = date_trunc('month', CURRENT_TIMESTAMP);

-- Una muestra de fecha_registro (últimos 3)
SELECT id, fecha_registro, date_trunc('month', fecha_registro) AS mes
FROM clientes
ORDER BY fecha_registro DESC NULLS LAST
LIMIT 3;
```

### 2.3 Frontend

| Punto | Estado | Detalle |
|------|--------|---------|
| URL del servicio | ✅ | `clienteService.baseUrl = '/api/v1/clientes'` → GET `/api/v1/clientes/stats` |
| Uso de la respuesta | ✅ | `apiClient.get()` devuelve `response.data` (objeto con nuevos_este_mes) |
| Paso a ClientesKPIs | ✅ | `nuevosEsteMes={statsData?.nuevos_este_mes ?? 0}` |
| Invalidación tras crear/editar | ✅ | `queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })` en onSuccess / onClienteCreated |
| Refetch explícito | ⚠️ | Conviene llamar `refetchStats()` tras crear/editar y esperar para que la UI actualice de inmediato |
| Caché (staleTime) | ✅ | 30 s; refetch cada 1 min |

### 2.4 Proxy / Despliegue

| Punto | Estado | Nota |
|------|--------|------|
| Producción (Render) | ⚠️ | En producción `API_URL = ''` → peticiones relativas al mismo origen; el mismo servidor debe servir API y SPA |
| Base path /pagos | ✅ | Rutas del front son `/pagos/clientes`; la API sigue siendo `/api/v1/clientes/stats` (sin /pagos en la ruta de API) |

---

## 3. Causas probables de que “no se actualicen” los KPIs

1. **Backend no desplegado** con la lógica actual de `nuevos_este_mes` (SQL con `date_trunc`).
2. **`fecha_registro` NULL o antigua** en la BD (migración, datos legacy): la cuenta del mes actual sale 0.
3. **Zona horaria:** servidor en UTC y usuarios en Venezuela; si en algún momento se guardó “hora local” sin timezone, la comparación por mes puede fallar (ya mitigado usando el mes de la BD).
4. **Caché del navegador o CDN** devolviendo una respuesta antigua de `/api/v1/clientes/stats`.
5. **Invalidación sin refetch inmediato:** la query se marca stale pero el componente no vuelve a pedir datos hasta que se remonta o cambia el foco; el usuario no ve el cambio al instante.

---

## 4. Acciones correctivas aplicadas en código

1. **Backend:** respuesta de stats con todos los conteos como `int`; log debug de la respuesta; endpoint **GET /api/v1/clientes/stats/diagnostico** que devuelve `mes_actual_bd`, `total_con_fecha_registro`, `nuevos_este_mes`, `ejemplo_ultimo_registro`.
2. **Frontend:** en onSuccess / onClienteCreated (crear y editar) y tras eliminar o carga Excel, se llama a `refetchStats()` y se espera para que los KPIs se actualicen de inmediato.
3. **Documentación:** este documento y consultas SQL de diagnóstico (sección 2.2).

---

## 5. Cómo comprobar en producción

1. **Logs del backend (Render):** al llamar a `GET /api/v1/clientes/stats`, revisar que no haya excepciones y que la respuesta incluya `nuevos_este_mes`.
2. **Red (DevTools):** en la pestaña Clientes, ver la petición a `.../api/v1/clientes/stats` y el cuerpo de la respuesta.
3. **Base de datos:** ejecutar las consultas de la sección 2.2 y comprobar que `nuevos_este_mes` y las fechas tienen sentido.
4. **Despliegue:** confirmar que el backend desplegado es el que contiene el cálculo actual de `nuevos_este_mes` (SQL con `date_trunc`).
