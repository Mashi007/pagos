# Auditoría integral: Centro de Reportes

**URL:** https://rapicredit.onrender.com/pagos/reportes  
**Fecha:** 2026-02-19  
**Alcance:** Frontend, backend, seguridad, rendimiento, UX y accesibilidad.

---

## 1. Resumen ejecutivo

| Área | Estado | Prioridad |
|------|--------|-----------|
| Conexión BD | ✅ | — |
| Autenticación | ✅ | — |
| Datos reales | ✅ | — |
| Exportación Excel | ✅ | — |
| Diseño consistente | ✅ | — |
| Rendimiento | ⚠️ | Alta |
| Carga inicial | ⚠️ | Media |
| Accesibilidad | ⚠️ | Media |

---

## 2. Arquitectura y flujo de datos

### 2.1 Frontend

**Ruta:** `/pagos/reportes` → `Reportes.tsx`

**Componentes principales:**
- **Reportes.tsx**: Página principal con KPIs, descarga Excel y orquestación
- **InformePagoVencido**: Morosidad por rangos (1 día, 15, 30, 2 meses, 61+)
- **ReportePagos**: Pagos por mes con pestañas
- **ReporteProductos**: Productos por mes (modelo, 70% ventas)
- **ReporteAsesores**: Asesores por mes (analista, morosidad, préstamos)
- **CuentasPorCobrar**: Cuentas por cobrar por mes y por día
- **TablaAmortizacionCompleta**: Búsqueda por cédula, cuotas y pagos

**Servicios:** `reporteService.ts` → `apiClient` (Axios, timeout 30s)

### 2.2 Backend

**Router:** `app/api/v1/endpoints/reportes.py`  
**Prefijo:** `/api/v1/reportes`  
**Autenticación:** `Depends(get_current_user)` en todo el router

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/dashboard/resumen` | GET | KPIs: cartera, préstamos, mora, pagos mes |
| `/morosidad/por-rangos` | GET | Informe pago vencido por rangos de días |
| `/pagos/por-mes` | GET | Pagos agrupados por mes |
| `/productos/por-mes` | GET | Productos por mes (modelo, ventas) |
| `/asesores/por-mes` | GET | Asesores por mes |
| `/cartera/por-mes` | GET | Cuentas por cobrar por mes y día |
| `/exportar/cartera` | GET | Excel cartera |
| `/exportar/pagos` | GET | Excel pagos |
| `/exportar/morosidad` | GET | Excel morosidad |
| `/exportar/financiero` | GET | Excel financiero |
| `/exportar/asesores` | GET | Excel asesores |
| `/exportar/productos` | GET | Excel productos |

---

## 3. Seguridad

### 3.1 Autenticación y autorización

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Protección de rutas | ✅ | `SimpleProtectedRoute` en Layout |
| Token en requests | ✅ | Interceptor Axios añade `Authorization` |
| Backend | ✅ | `router = APIRouter(dependencies=[Depends(get_current_user)])` |
| Refresh token | ✅ | ApiClient maneja 401 y refresh |

### 3.2 Datos sensibles

- **Filtros BD:** `Cliente.estado == "ACTIVO"`, `Prestamo.estado == "APROBADO"`
- **Datos expuestos:** Cédula, nombres, montos — coherente con negocio
- **SQL injection:** Uso de SQLAlchemy ORM, sin concatenación de SQL crudo

### 3.3 Recomendaciones

- [ ] Validar permisos por rol si hay distintos niveles de acceso
- [ ] Revisar rate limiting en endpoints pesados (exportar Excel)

---

## 4. Base de datos

### 4.1 Conexión

- **Config:** `DATABASE_URL` desde `.env` / variables de entorno
- **Sesión:** `get_db` inyectada en todos los endpoints
- **Regla:** Sin stubs ni datos demo en reportes

### 4.2 Tablas utilizadas

| Tabla | Uso |
|-------|-----|
| `clientes` | Filtro estado, joins |
| `prestamos` | Cartera, morosidad, analista, producto |
| `cuotas` | Montos, fechas vencimiento/pago |
| `pagos` | Referencia en algunos flujos |

### 4.3 Índices sugeridos

Para mejorar tiempos de respuesta (3–10 s en algunos reportes):

```sql
-- Cuotas: filtros frecuentes
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_fecha_pago ON cuotas(prestamo_id, fecha_pago);
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento ON cuotas(fecha_vencimiento) WHERE fecha_pago IS NULL;
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_pago ON cuotas(fecha_pago) WHERE fecha_pago IS NOT NULL;

-- Préstamos
CREATE INDEX IF NOT EXISTS idx_prestamos_cliente_estado ON prestamos(cliente_id, estado);
CREATE INDEX IF NOT EXISTS idx_prestamos_analista ON prestamos(analista);
```

---

## 5. Rendimiento

### 5.1 Observaciones (logs Render)

| Endpoint | Tiempo típico | Observación |
|----------|---------------|-------------|
| `/reportes/dashboard/resumen` | 3–6 s | Aceptable |
| `/reportes/morosidad/por-rangos` | 4–5 s | Aceptable |
| `/reportes/pagos/por-mes` | 5–6 s | Lento |
| `/reportes/productos/por-mes` | 5–6 s | Lento |
| `/reportes/asesores/por-mes` | 6–7 s | Lento |
| `/reportes/cartera/por-mes` | 6–8 s | Lento |
| Timeouts (29 bytes) | 30+ s | Posible límite Render |

### 5.2 Carga inicial

- **6 queries en paralelo** al entrar a la página
- Todos los reportes se cargan a la vez
- Cold start de Render puede sumar latencia

### 5.3 Recomendaciones

1. **Lazy loading:** Cargar solo KPIs + Informe Pago Vencido al inicio; el resto al hacer scroll o al abrir sección
2. **Índices BD:** Aplicar los índices sugeridos
3. **Timeout:** Revisar `DEFAULT_TIMEOUT_MS` (30s) y `SLOW_ENDPOINT_TIMEOUT_MS` (60s) en `api.ts`
4. **Caché:** `staleTime` 2 min y `refetchInterval` 30 min ya configurados

---

## 6. UX y diseño

### 6.1 Estructura

- Header con título y descripción
- 4 KPIs (Cartera, Mora, Préstamos, Pagos mes)
- 6 bloques de reportes con diseño unificado
- Sección de descarga Excel por tipo de reporte

### 6.2 Consistencia

- Cards con `border-l-4` por color (ámbar, azul, púrpura, índigo, verde)
- Tabs por mes en ReportePagos, Productos, Asesores, CuentasPorCobrar
- Botón "Actualizar" en cada reporte
- Selector de meses (3, 6, 12, 24)

### 6.3 Estados

- Loading: spinner y mensaje
- Error: mensaje + botón Reintentar
- Vacío: mensaje "No hay datos"

### 6.4 Mejoras sugeridas

- [ ] Indicador de "Última actualización" por reporte
- [ ] Skeleton loaders en lugar de spinner genérico
- [ ] Scroll suave al hacer clic en un reporte colapsado

---

## 7. Actualización automática

### 7.1 Backend (scheduler)

- **Horarios:** 1:00 y 13:00 (America/Caracas)
- **Jobs:** Reportes cobranzas, informe pagos email
- **Dashboard cache:** 1:00 y 13:00

### 7.2 Frontend (useReportesRefreshSchedule)

- Invalidación de queries a la 1:00 y 13:00 (hora local)
- Intervalo de comprobación: 1 minuto
- Query keys: reportes-resumen, morosidad-por-rangos, pagos-por-mes, productos-por-mes, asesores-por-mes, cartera-por-mes

---

## 8. Accesibilidad

| Aspecto | Estado | Nota |
|---------|--------|------|
| Contraste | ✅ | Texto legible sobre fondo |
| Navegación teclado | ⚠️ | Botones y tabs accesibles; revisar orden de tabulación |
| ARIA | ⚠️ | Tabs con `role="tab"`; falta `aria-label` en iconos |
| Screen readers | ⚠️ | Mejorar etiquetas en botones de descarga |

### Recomendaciones

- Añadir `aria-label="Descargar reporte de Cuentas por cobrar"` en botones de descarga
- Revisar `title` en iconos para que sean descriptivos

---

## 9. Errores y resiliencia

### 9.1 Frontend

- `getErrorMessage` y `getErrorDetail` para mensajes de error
- Toasts para éxito, error y loading
- Reintentos en `useQuery` (retry: 2)
- Manejo de 500, 404 y timeout con mensajes específicos

### 9.2 Backend

- `_safe_float` para valores numéricos
- `_parse_fecha` para fechas con fallback a hoy
- Excepciones HTTP estándar (404, etc.)

---

## 10. Checklist de verificación

| Ítem | Estado |
|------|--------|
| Todos los endpoints usan `get_db` | ✅ |
| Sin datos mock en reportes | ✅ |
| Autenticación en backend | ✅ |
| Exportación Excel para los 6 tipos | ✅ |
| Diseño consistente en reportes | ✅ |
| Manejo de errores en frontend | ✅ |
| Actualización 1 AM / 1 PM configurada | ✅ |
| Índices BD para reportes | ⚠️ Pendiente |
| Lazy loading de reportes | ⚠️ Pendiente |
| Timeouts en producción | ⚠️ Revisar |

---

## 11. Conclusiones

El Centro de Reportes está bien integrado con la BD, usa autenticación y ofrece datos reales. Los puntos a priorizar son:

1. **Rendimiento:** Índices en BD y posible lazy loading
2. **Timeouts:** Revisar límites en Render y en el cliente
3. **Accesibilidad:** Mejorar etiquetas ARIA y navegación por teclado

---

*Documento generado como parte de la auditoría integral del sistema RapiCredit.*
