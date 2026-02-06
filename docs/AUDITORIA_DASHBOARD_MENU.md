# Auditoría integral: Dashboard Menu
## https://rapicredit.onrender.com/pagos/dashboard/menu

**Fecha:** 2025-02-05  
**Alcance:** Ruta `/pagos/dashboard/menu` (Dashboard Ejecutivo) — frontend, backend, seguridad, UX y datos.

---

## 1. Resumen ejecutivo

El Dashboard Menu es la vista principal post-login de RapiCredit. Consume múltiples endpoints del backend (`/api/v1/dashboard/*` y KPIs), usa caché en backend (3 veces al día) y en frontend (React Query), y está protegido por autenticación. La auditoría identifica puntos fuertes y mejoras en seguridad, rendimiento, mantenibilidad y experiencia de usuario.

---

## 2. Arquitectura y flujo

| Capa | Componente | Ubicación |
|------|------------|-----------|
| Ruta | `/dashboard/menu` | `App.tsx` → `DashboardMenu` |
| Layout | Protegido por `SimpleProtectedRoute` dentro de `RootLayoutWrapper` | `App.tsx`, `SimpleProtectedRoute.tsx` |
| Página | `DashboardMenu` | `frontend/src/pages/DashboardMenu.tsx` |
| API | Prefijo `/api/v1/dashboard` | `backend/app/api/v1/endpoints/dashboard.py` |
| Auth | `Depends(get_current_user)` en router dashboard | Todos los endpoints requieren usuario autenticado |

**Flujo:** Usuario autenticado → Layout con sidebar → DashboardMenu carga en paralelo: opciones-filtros, kpis-principales, dashboard/admin, morosidad-por-dia, financiamiento-por-rangos, composicion-morosidad, cobranzas-semanales, morosidad-por-analista, monto-programado-proxima-semana, prestamos-por-modelo.

---

## 3. Seguridad

### 3.1 Autenticación y autorización

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Protección de ruta | ✅ | `SimpleProtectedRoute` redirige a `/login` si no hay `user` o `!isAuthenticated`. |
| Protección API | ✅ | Router dashboard: `APIRouter(dependencies=[Depends(get_current_user)])`. Todos los GET requieren token válido. |
| Token en requests | ✅ | `apiClient` (Axios) añade token en interceptor; refresh automático configurado. |
| Roles | ⚠️ | Dashboard no exige rol `administrador`; cualquier usuario autenticado accede. Si el negocio requiere solo admin, hay que usar `requireAdmin` en ruta o en backend. |

### 3.2 Validación de entradas (backend)

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Fechas | ✅ | Uso de `date.fromisoformat()` con `try/except ValueError`; en morosidad-por-dia se acota a fechas válidas. |
| Parámetro `dias` | ✅ | `Query(30, ge=7, le=90)` en morosidad-por-dia. |
| Parámetro `semanas` | ⚠️ | `Query(12)` sin `ge`/`le`; un valor muy grande podría generar consultas pesadas. |
| Parámetro `meses` | ⚠️ | En varios endpoints `meses: Optional[int] = Query(12)` sin cota máxima. |
| Strings (analista, concesionario, modelo) | ⚠️ | `Optional[str] = Query(None)` sin longitud máxima; strings muy largos podrían impactar logs/BD. Recomendación: limitar longitud (ej. 200 caracteres) o validar contra valores conocidos. |

### 3.3 Otros

- **CORS:** Depende de la configuración global de FastAPI (no revisada en esta auditoría).
- **Rate limiting:** No aplicado específicamente al dashboard; podría considerarse para evitar abuso de “Actualizar” o de muchos filtros.
- **Datos sensibles:** Los endpoints devuelven agregados (KPIs, gráficos); no se exponen datos personales en esta vista.

---

## 4. Backend (FastAPI)

### 4.1 Endpoints utilizados por Dashboard Menu

| Endpoint | Uso en frontend | Caché backend | Observación |
|----------|------------------|---------------|-------------|
| `GET /dashboard/opciones-filtros` | Filtros (analistas, concesionarios, modelos) | No | Solo lectura desde BD. |
| `GET /dashboard/kpis-principales` | 4 KPI cards | Sí (6:00, 13:00, 16:00) | Cache cuando no hay filtros. |
| `GET /dashboard/admin` | Gráfico evolución mensual | Sí (6:00, 13:00, 16:00) | Cache cuando no hay fecha_inicio/fecha_fin. |
| `GET /dashboard/morosidad-por-dia` | Gráfico morosidad por día | Sí | Cache cuando no hay fechas. |
| `GET /dashboard/financiamiento-por-rangos` | Bandas $200 | Sí | Cache sin filtros. |
| `GET /dashboard/composicion-morosidad` | Composición morosidad | Sí | Cache sin filtros. |
| `GET /dashboard/cobranzas-semanales` | Cobranzas semanales | Sí | Cache sin filtros. |
| `GET /dashboard/morosidad-por-analista` | Radar y barras por analista | Sí | Cache sin filtros. |
| `GET /dashboard/monto-programado-proxima-semana` | Monto programado 7 días | No | Consulta directa. |
| `GET /dashboard/prestamos-por-modelo` | Gráfico por modelo | No (usa fechas/filtros) | — |

### 4.2 Caché backend

- **Horarios:** 6:00, 13:00 y 16:00 (hora local del servidor).
- **Worker:** `_dashboard_cache_worker` en hilo daemon; inicia con `start_dashboard_cache_refresh()` en `main.py`.
- **Bloqueo:** `threading.Lock()` para acceso a diccionarios de caché.
- **Caché por endpoint:** `_DASHBOARD_ADMIN_CACHE`, `_CACHE_KPIS`, `_CACHE_MOROSIDAD_DIA`, etc.; se rellenan en `_refresh_all_dashboard_caches()`.

### 4.3 Datos reales

- Los endpoints usan `get_db` y consultas a modelos (Prestamo, Cuota, Cliente). Alineado con la regla de “datos reales desde BD” (no stubs en endpoints que deben reflejar datos reales).
- Algunos endpoints siguen documentados como stub (p. ej. cobranza-fechas-especificas, cobranza-por-dia); si el menú no los usa, el impacto es bajo.

### 4.4 Robustez

- Uso de `try/except` en parsing de fechas y en `get_opciones_filtros`; errores no dejan el servidor caído.
- En frontend, la query de `dashboard/admin` en caso de error devuelve `{} as DashboardAdminResponse`, evitando romper la página pero ocultando el fallo; conviene al menos log o toast en desarrollo.

---

## 5. Frontend (React)

### 5.1 Estructura y estado

- **Estado local:** `filtros`, `periodo`, `periodoPorGrafico` (período por gráfico).
- **Hook:** `useDashboardFiltros(filtros)` centraliza `construirParams`, `construirFiltrosObject`, `tieneFiltrosActivos`, `cantidadFiltrosActivos`.
- **Queries:** React Query con `queryKey` que incluyen período y `JSON.stringify(filtros)` para refetch al cambiar filtros.

### 5.2 Caché y estrategia de datos

| Query | staleTime | refetchOnMount | refetchOnWindowFocus | Observación |
|-------|-----------|----------------|----------------------|-------------|
| opciones-filtros | 30 min | default | false | Adecuado. |
| kpis-principales | 4 h | false | false | Alineado con refresh backend. |
| dashboard-menu (admin) | 4 h | default | false | Timeout 60 s. |
| morosidad-por-dia | 4 h | default | false | — |
| financiamiento-rangos | 4 h | default | false | Retorna fallback vacío en errores no 5xx/red. |
| cobranzas-semanales | 15 min | default | false | — |
| monto-programado-proxima-semana | 5 min | default | false | — |

### 5.3 Botón “Actualizar”

- `handleRefresh` invalida y refetch de: `kpis-principales-menu`, `dashboard-menu`, `morosidad-por-dia`, `financiamiento-rangos`, `composicion-morosidad`, `cobranzas-mensuales`, `cobranzas-semanales`, `morosidad-analista`, `monto-programado-proxima-semana`.
- **Inconsistencia:** Se invalida `cobranzas-mensuales` pero en la página no se ve una query con esa key; la vista usa `cobranzas-semanales`. Revisar si `cobranzas-mensuales` se usa en otro componente o es key obsoleta.

### 5.4 Manejo de errores

- **Críticos:** Si `errorOpcionesFiltros` o `errorKPIs`, se muestra banner amarillo: “Algunos datos no se pudieron cargar…”.
- **KPIs:** Si `errorKPIs`, se muestra card roja con mensaje y no se renderizan las 4 tarjetas.
- **Dashboard admin:** En `queryFn` se captura error y se devuelve `{}`; no hay toast ni mensaje específico para el usuario cuando falla solo este endpoint.
- **Financiamiento por rangos:** Se distingue 5xx/red (reintento) de otros errores (respuesta vacía); el resto de gráficos no tienen esta lógica unificada.

### 5.5 UX y accesibilidad

- **Loading:** Skeletons para KPIs y para el bloque de gráficos principales; textos “Cargando…” en gráficos secundarios.
- **Empty state:** Mensajes claros (“No hay datos para el período seleccionado”, “No hay datos para mostrar”) y aviso cuando no hay préstamos/cuotas.
- **Aviso datos demo:** Si `evolucion_origen === 'demo'` se muestra badge “Datos de ejemplo”.
- **Accesibilidad:** No se ha verificado ARIA en gráficos (Recharts), roles de región ni contraste; recomendable revisar con linter a11y y pruebas con lector de pantalla.

### 5.6 Tipos

- Tipos en `frontend/src/types/dashboard.ts` alineados con respuestas del backend (KpisPrincipalesResponse, DashboardAdminResponse, etc.); buena trazabilidad.

---

## 6. Proxy y cabeceras HTTP (server.js)

- Para rutas que contienen `/api/v1/dashboard` o `/api/v1/kpis`:  
  `Cache-Control: private, max-age=30, stale-while-revalidate=10`.
- Reduce carga en backend con caché corta en cliente/proxy; coherente con datos que se refrescan en backend 3 veces al día.

---

## 7. Rendimiento

- **Carga inicial:** Múltiples requests en paralelo (React Query); el backend usa caché en muchos casos, lo que reduce tiempo de respuesta.
- **Timeouts:** dashboard/admin y financiamiento-por-rangos con 60 s; adecuado para consultas pesadas.
- **Componente pesado:** `DashboardMenu.tsx` es muy grande (~1127 líneas); dificulta mantenimiento y podría beneficiarse de extracción de secciones (KPIs, Evolución, Morosidad, etc.) en subcomponentes o lazy loading de bloques menos críticos.

---

## 8. Mantenibilidad y pruebas

- **Tests:** No se encontraron tests específicos para el dashboard (`*dashboard*test*`). Recomendación: al menos tests de integración para endpoints críticos y tests de componente para DashboardMenu (render con datos mock).
- **Documentación:** Comentarios en código (batches, caché 6/13/16) ayudan; el presente documento sirve como referencia de diseño y decisiones.

---

## 9. Resumen de hallazgos y recomendaciones

### Críticos / Alta prioridad

1. **Validación backend:** ~~Añadir límite de longitud~~ **Implementado:** `_sanitize_filter_string()` en `dashboard.py` (max 200 caracteres) aplicado en todos los endpoints que reciben analista/concesionario/modelo.
2. **Manejo de error dashboard/admin:** ~~No devolver solo `{}` en silencio~~ **Implementado:** La query lanza el error; se muestra toast, banner de error y tarjeta roja en la zona del gráfico principal cuando falla.

### Media prioridad

3. **Refresco manual:** **Implementado:** Eliminada invalidación de `cobranzas-mensuales`; añadido refetch de `cobranzas-semanales` en `handleRefresh`.
4. **Parámetros numéricos:** **Implementado:** `meses`: `Query(12, ge=1, le=24)` en financiamiento-tendencia-mensual, evolucion-morosidad, evolucion-pagos; `semanas`: `Query(12, ge=1, le=52)` en cobranzas-semanales.
5. **Rol del dashboard:** Si solo administradores deben ver el dashboard, proteger ruta con `requireAdmin` o equivalente en backend.

### Baja prioridad / Mejora continua

6. **Refactorizar DashboardMenu:** Dividir en subcomponentes por sección (Header, Filtros, KPIs, Evolución, Morosidad, etc.) para mejorar legibilidad y posibilidad de tests.
7. **Tests:** Añadir tests E2E o de integración para flujo login → dashboard y tests unitarios de hooks y componentes del dashboard.
8. **Accesibilidad:** Revisar ARIA y contraste en gráficos y en botones/filtros.

---

## 10. Checklist rápido

| Área | Ítem | OK |
|------|------|-----|
| Auth | Ruta protegida | ✅ |
| Auth | API con get_current_user | ✅ |
| Backend | Datos reales desde BD | ✅ |
| Backend | Caché documentada y predecible | ✅ |
| Backend | Validación fechas | ✅ |
| Backend | Límite parámetros numéricos/string | ⚠️ |
| Frontend | Errores críticos visibles | ✅ |
| Frontend | Error gráfico principal visible | ❌ |
| Frontend | Tipos alineados con API | ✅ |
| UX | Loading y empty states | ✅ |
| Mantenibilidad | Tamaño componente | ⚠️ |
| Tests | Cobertura dashboard | ❌ |

---

*Documento generado en el marco de la auditoría integral del dashboard RapiCredit.*
