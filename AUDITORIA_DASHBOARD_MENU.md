# Auditoría integral: Dashboard Menu
**URL:** https://rapicredit.onrender.com/pagos/dashboard/menu  
**Fecha:** Marzo 2026

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Conexión API** | OK | API respondiendo en `/api/v1/health/` |
| **Conexión BD** | OK | `db_connected: true`, tablas críticas presentes |
| **Endpoints Dashboard** | OK | 10 endpoints consumidos, todos con `Depends(get_db)` |
| **Datos reales** | OK | Sin stubs: datos desde PostgreSQL |
| **Autenticación** | OK | Endpoints protegidos con `get_current_user` |

---

## 2. Verificación de conexión

### 2.1 Health check API
```
GET https://rapicredit.onrender.com/api/v1/health/
→ {"status":"ok","message":"API is running"}
```

### 2.2 Health check Base de datos
```
GET https://rapicredit.onrender.com/api/v1/health/db
→ {
  "status": "ok",
  "db_connected": true,
  "tables_exist": {
    "clientes": true,
    "prestamos": true,
    "cuotas": true,
    "pagos_whatsapp": true,
    "tickets": true
  },
  "prestamos_count": 4908,
  "error": null
}
```

### 2.3 Configuración BD (backend)
- **Fuente:** `app/core/config.py` → `settings.DATABASE_URL`
- **Origen:** variables de entorno (`.env` o Render)
- **Motor:** PostgreSQL (conversión automática `postgres://` → `postgresql://`)
- **Pool:** `pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`, `pool_recycle=1800`

### 2.4 Frontend → API
- **Producción:** rutas relativas (proxy en `server.js` resuelve `/api/*`)
- **Config:** `frontend/src/config/env.ts` → `API_URL = ''` en production

---

## 3. Inventario de endpoints del Dashboard Menu

| # | Endpoint | Método | Query Key | Tablas BD | Caché backend |
|---|----------|--------|-----------|-----------|---------------|
| 1 | `/api/v1/dashboard/opciones-filtros` | GET | opciones-filtros | prestamos, clientes, modelos_vehiculo | 5 min |
| 2 | `/api/v1/dashboard/kpis-principales` | GET | kpis-principales-menu | clientes, prestamos, cuotas | 2x/día* |
| 3 | `/api/v1/dashboard/admin` | GET | dashboard-menu | cuotas, prestamos, clientes, pagos | 2x/día* |
| 4 | `/api/v1/dashboard/morosidad-por-dia` | GET | morosidad-por-dia | cuotas, prestamos, clientes | 2x/día* |
| 5 | `/api/v1/dashboard/financiamiento-por-rangos` | GET | financiamiento-rangos | prestamos, clientes | 2x/día* |
| 6 | `/api/v1/dashboard/prestamos-por-modelo` | GET | prestamos-por-modelo | prestamos, clientes | No |
| 7 | `/api/v1/dashboard/composicion-morosidad` | GET | composicion-morosidad | cuotas, prestamos, clientes | 2x/día* |
| 8 | `/api/v1/dashboard/cobranzas-semanales` | GET | cobranzas-semanales | cuotas, prestamos, clientes | 2x/día* |
| 9 | `/api/v1/dashboard/morosidad-por-analista` | GET | morosidad-analista | cuotas, prestamos, clientes | 2x/día* |
| 10 | `/api/v1/dashboard/monto-programado-proxima-semana` | GET | monto-programado-proxima-semana | cuotas, prestamos, clientes | No |

\* Caché solo cuando **no** se envían filtros (fecha_inicio, fecha_fin, analista, concesionario, modelo).  
Con filtros, siempre se calcula en tiempo real.

---

## 4. Tablas de BD utilizadas

| Tabla | Uso en Dashboard |
|-------|------------------|
| **clientes** | Filtro `estado=ACTIVO`, joins con préstamos |
| **prestamos** | KPIs, gráficos, filtros por analista/concesionario/modelo |
| **cuotas** | Morosidad, cuotas programadas, cobranzas, evolución |
| **pagos** | Evolución mensual (cobrado por mes) en dashboard/admin |
| **modelos_vehiculo** | Opciones de filtro (opcional, outer join) |

**Nota:** El health check no incluye la tabla `pagos` en CRITICAL_TABLES.  
El dashboard/admin usa `Pago` para `cobrado` en evolución mensual.  
Recomendación: añadir `pagos` a la verificación si el dashboard/admin depende de ella.

---

## 5. Flujo de datos (KPIs principales)

```
Frontend (DashboardMenu.tsx)
  └─ useQuery(['kpis-principales-menu', ...])
       └─ GET /api/v1/dashboard/kpis-principales?fecha_inicio=...&fecha_fin=...
            └─ Backend (kpis.py)
                 └─ get_kpis_principales(Depends(get_db))
                      └─ _compute_kpis_principales(db, ...)
                           └─ SQLAlchemy: Cliente, Prestamo, Cuota
                                └─ PostgreSQL
```

**Cálculo de KPIs (resumen):**
- **total_prestamos:** COUNT de Prestamo (estado=APROBADO, fecha_registro en mes)
- **creditos_nuevos_mes:** SUM(total_financiamiento) de préstamos aprobados en mes
- **cuotas_programadas:** SUM(monto) de Cuota con vencimiento en mes
- **total_morosidad_usd:** SUM(monto) de Cuota vencida, no pagada (fecha_pago IS NULL)
- **porcentaje_cuotas_pagadas:** cuotas con fecha_pago / total cuotas del mes

---

## 6. Consideraciones de caché

### Backend
- **kpis-principales:** Con `fecha_inicio` y `fecha_fin` (enviados por DashboardMenu con periodo 'mes'), se **bypasea** la caché y se calcula en tiempo real.
- **opciones-filtros:** TTL 5 minutos.
- **Worker de refresco:** Hilo que actualiza cachés a las 1:00 y 13:00 (hora local servidor).

### Frontend (tras mejoras recientes)
- **kpis-principales-menu:** `staleTime` 5 min, `refetchOnMount: true`, `refetchInterval` 10 min.
- Otras queries: `staleTime` 4 h (gráficos menos críticos).

---

## 7. Recomendaciones

1. **Health check:** Incluir tabla `pagos` en CRITICAL_TABLES si el dashboard/admin la usa.
2. **Monitoreo:** Usar `GET /api/v1/health/db` para alertas de disponibilidad de BD.
3. **KPIs en cero:** Si Préstamos/Créditos nuevos aparecen en 0, verificar que existan préstamos con `estado='APROBADO'` y `fecha_registro` o `fecha_aprobacion` en el mes actual.
4. **Invalidación:** Las mutaciones (crear préstamo, registrar pago, etc.) ya invalidan `kpis-principales-menu` para refrescar datos.

---

## 8. Conclusión

La conexión entre el Dashboard Menu, los endpoints del backend y la base de datos está correctamente configurada. Los datos mostrados provienen de consultas reales a PostgreSQL. El health check confirma que la BD está accesible y las tablas críticas existen.
