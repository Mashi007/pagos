# Revisión Integral - Centro de Reportes

**URL:** https://rapicredit.onrender.com/pagos/reportes  
**Fecha revisión:** 2025-02-21

---

## 1. Arquitectura

### Frontend
| Componente | Ruta | Función |
|------------|------|---------|
| Reportes.tsx | `frontend/src/pages/Reportes.tsx` | Página principal: KPIs, grid de reportes, diálogos |
| DialogReporteFiltros | `frontend/src/components/reportes/DialogReporteFiltros.tsx` | Filtros año/mes (Cartera, Pagos, Vencimiento, Pago vencido) |
| DialogReporteContableFiltros | `frontend/src/components/reportes/DialogReporteContableFiltros.tsx` | Filtros año/mes/cédulas (Contable) |
| reporteService | `frontend/src/services/reporteService.ts` | Llamadas API |

### Backend
| Módulo | Ruta | Endpoints principales |
|--------|------|------------------------|
| reportes_dashboard | `reportes/reportes_dashboard.py` | `GET /dashboard/resumen` |
| reportes_cartera | `reportes/reportes_cartera.py` | `GET /cartera`, `GET /exportar/cartera` |
| reportes_pagos | `reportes/reportes_pagos.py` | `GET /pagos`, `GET /exportar/pagos` |
| reportes_morosidad | `reportes/reportes_morosidad.py` | `GET /exportar/morosidad`, `GET /exportar/morosidad-clientes` |
| reportes_contable | `reportes/reportes_contable.py` | `GET /contable/cedulas`, `GET /exportar/contable` |
| reportes_cedula | `reportes/reportes_cedula.py` | `GET /exportar/cedula` |

### Rutas API (prefijo `/api/v1/reportes`)
- `GET /dashboard/resumen` → KPIs (cartera, pagos vencidos, total préstamos, pagos mes)
- `GET /exportar/cartera?formato=excel&años=&meses_list=` → Excel cartera
- `GET /exportar/pagos?formato=excel&meses=&años=&meses_list=` → Excel pagos
- `GET /exportar/morosidad?formato=excel&fecha_corte=&años=&meses_list=` → Excel morosidad/vencimiento
- `GET /exportar/morosidad-clientes?fecha_corte=` → Excel morosidad clientes
- `GET /exportar/contable?años=&meses=&cedulas=` → Excel contable
- `GET /exportar/cedula` → Excel por cédula

---

## 2. Mejoras implementadas

### 2.1 Timeout y cold start (Render)
- **Problema:** Render cold start puede tardar 30–60s; timeout 60s insuficiente.
- **Solución:** Timeout 120s para `/reportes/dashboard/resumen` en `api.ts`.

### 2.2 Diálogos de filtros
- **Problema:** Cierre accidental al hacer clic en años/meses.
- **Solución:** `stopPropagation` en contenido del Dialog; z-index explícito overlay (9998) vs contenido (9999).
- **Problema:** Estado del diálogo no se reseteaba al cambiar tipo de reporte.
- **Solución:** `key={reporteSeleccionado}` en DialogReporteFiltros para forzar remount.

### 2.3 Carga y errores
- **Reintentos:** 3 reintentos con backoff exponencial (2s, 4s, 8s, máx 15s).
- **Botón Reintentar:** Visible cuando falla la carga de KPIs.
- **Mensaje de error:** Indica posible cold start del servidor.
- **Botón Actualizar KPIs:** Deshabilitado durante `loadingResumen` y `fetchingResumen` para evitar doble clic.

### 2.4 Interface ResumenDashboard
- Corregido: `pagos_vencidos` (alineado con backend) en lugar de `prestamos_mora`.

---

## 3. Tipos de reporte

| value | label | Filtros | Endpoint |
|-------|-------|---------|----------|
| CARTERA | Cuentas por cobrar | Año, Mes | exportar/cartera |
| MOROSIDAD | Morosidad | — | exportar/morosidad-clientes |
| VENCIMIENTO | Vencimiento | Año, Mes | exportar/morosidad |
| PAGOS | Pagos | Año, Mes | exportar/pagos |
| ASESORES | Pago vencido | Año, Mes | exportar/morosidad |
| CONTABLE | Contable | Año, Mes, Cédulas | exportar/contable |
| CEDULA | Por cédula | — | exportar/cedula |

---

## 4. Permisos

- **canViewReports():** Solo ADMIN puede ver la página.
- **canDownloadReports():** Solo ADMIN puede descargar.
- **canAccessReport(tipo):** ADMIN tiene todos; OPERATIVO: PAGOS, MOROSIDAD, VENCIMIENTO, CEDULA.

---

## 5. Datos reales

Todos los endpoints usan `Depends(get_db)` y consultan BD real. No hay datos demo.

---

## 6. Verificación

1. KPIs cargan con datos reales.
2. Diálogos de filtros permiten seleccionar años/meses sin cerrarse.
3. Descarga de Excel funciona para cada tipo.
4. Error en carga muestra mensaje y botón Reintentar.
5. Cold start: esperar hasta 60–90s tras inactividad; timeout 120s.
