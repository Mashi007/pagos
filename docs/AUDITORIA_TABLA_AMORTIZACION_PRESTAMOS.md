# Auditoría: Tabla de Amortización y Detalles del Préstamo

**Fecha:** 2025-03-11  
**Alcance:** Flujo completo desde `/pagos/prestamos` hasta modal "Detalles del Préstamo" y pestaña "Tabla de Amortización" (export Excel/PDF, recibo, estados).

---

## 1. Resumen ejecutivo

| Área            | Estado   | Notas                                                                 |
|-----------------|----------|-----------------------------------------------------------------------|
| Rutas frontend  | OK       | `prestamos` → `Prestamos.tsx`; modal y tabla ubicados y funcionando.  |
| Modal detalle   | OK       | `PrestamoDetalleModal` con pestañas Detalles / Tabla de Amortización. |
| Tabla cuotas    | OK       | `TablaAmortizacionPrestamo`: columnas, estados, export, recibo.       |
| Servicio API    | OK       | `prestamoService`: cuotas, Excel, PDF, generar amortización.          |
| Backend         | OK       | Endpoints cuotas, amortización Excel/PDF y datos desde BD.            |
| Datos reales    | OK       | Sin stubs; uso de `get_db` y consultas a BD.                          |

**Conclusión:** El flujo está correcto y alineado con la regla de "datos reales desde la base de datos". No se detectaron errores de linter en los archivos revisados.

---

## 2. Flujo verificado

### 2.1 Navegación

- **URL:** `https://rapicredit.onrender.com/pagos/prestamos` (o equivalente con `BASE_PATH=/pagos`).
- **Ruta React:** `path="prestamos"` → componente `Prestamos` (`frontend/src/pages/Prestamos.tsx`).
- **Listado:** `PrestamosList` muestra préstamos; al hacer clic en una fila se abre `PrestamoDetalleModal`.

### 2.2 Modal de detalles

- **Componente:** `frontend/src/components/prestamos/PrestamoDetalleModal.tsx`
- **Props:** `prestamo` (inicial), `onClose`.
- **Datos:** Recarga con `usePrestamo(prestamoInitial.id)`; evaluación de riesgo con `prestamoService.getEvaluacionRiesgo`.
- **Pestañas:**
  - **Detalles:** Estado, cliente, préstamo, evaluación de riesgo, predicción impago, producto, usuarios, observaciones.
  - **Tabla de Amortización:** Renderiza `TablaAmortizacionPrestamo` con el mismo préstamo.

### 2.3 Tabla de amortización

- **Componente:** `frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx`
- **Condición:** Solo se muestra para préstamos en estado `APROBADO` o `DESEMBOLSADO`.
- **Datos:** `useQuery` con `prestamoService.getCuotasPrestamo(prestamo.id)` (queryKey: `['cuotas-prestamo', prestamo.id]`).
- **Columnas:** Cuota, Fecha Vencimiento, Capital, Interés, Total, Saldo Pendiente, Pago conciliado, Estado, Recibo.
- **Lógica de estado:** `determinarEstadoReal(cuota)` considera `total_pagado`, `pago_monto_conciliado`, `pago_conciliado`, días de mora (PENDIENTE, PAGADO, CONCILIADO, VENCIDO, MORA, etc.).
- **Acciones:**
  - **Exportar Excel:** `prestamoService.descargarAmortizacionExcel(prestamo.id, prestamo.cedula)`.
  - **Exportar PDF:** `prestamoService.descargarAmortizacionPDF(prestamo.id, prestamo.cedula)`.
  - **Ver Todas (N):** `showFullTable` para mostrar todas las cuotas.
  - **Recibo:** `generarReciboPagoPDF(prestamo, cuota)` desde `utils/reciboPagoPDF.ts`.

---

## 3. Servicio frontend (`prestamoService`)

- **Archivo:** `frontend/src/services/prestamoService.ts`
- **Base URL:** `/api/v1/prestamos`
- **Métodos relevantes:**
  - `getPrestamo(id)` → `GET /api/v1/prestamos/{id}`
  - `getCuotasPrestamo(prestamoId)` → `GET /api/v1/prestamos/{id}/cuotas`
  - `descargarAmortizacionExcel(prestamoId, cedula)` → `GET .../amortizacion/excel` (blob)
  - `descargarAmortizacionPDF(prestamoId, cedula)` → `GET .../amortizacion/pdf` (blob)
  - `generarAmortizacion(prestamoId)` → `POST .../generar-amortizacion`
  - `getEvaluacionRiesgo(prestamoId)` → `GET .../evaluacion-riesgo`

Las descargas Excel/PDF usan `apiClient.getAxiosInstance()` con `responseType: 'blob'` y crean un enlace de descarga con el nombre `Tabla_Amortizacion_{cedula}_{prestamoId}.xlsx/.pdf`. Correcto.

---

## 4. Backend (FastAPI)

- **Router:** `backend/app/api/v1/endpoints/prestamos.py`
- **Autenticación:** `router = APIRouter(dependencies=[Depends(get_current_user)])` en todos los endpoints.

### Endpoints auditados

| Método | Ruta | Función | Comentario |
|--------|------|---------|------------|
| GET | `/{prestamo_id}` | `get_prestamo` | Join con `Cliente`; devuelve `nombres` y `cedula` en la respuesta. |
| GET | `/{prestamo_id}/cuotas` | `get_cuotas_prestamo` | Lista de cuotas con `pago_conciliado`, `pago_monto_conciliado`, montos y estados. |
| GET | `/{prestamo_id}/amortizacion/excel` | `exportar_amortizacion_excel` | `Response(content=..., media_type=xlsx, Content-Disposition)`. |
| GET | `/{prestamo_id}/amortizacion/pdf` | `exportar_amortizacion_pdf` | `Response(content=..., media_type=pdf, Content-Disposition)`. |
| POST | `/{prestamo_id}/generar-amortizacion` | `generar_amortizacion` | No crea cuotas si ya existen; usa `_generar_cuotas_amortizacion` y BD. |

- **Datos:** Todos usan `Depends(get_db)` y consultas a modelos `Prestamo`, `Cuota`, `Cliente`, `Pago`. Sin stubs.
- **Respuesta de cuotas:** Incluye `id`, `numero_cuota`, `fecha_vencimiento`, `monto_cuota`, `monto_capital`, `monto_interes`, `saldo_capital_inicial`, `saldo_capital_final`, `total_pagado`, `pago_conciliado`, `pago_monto_conciliado`, `estado`, etc., alineado con el tipo `Cuota` del frontend.

---

## 5. Hooks y caché

- **Archivo:** `frontend/src/hooks/usePrestamos.ts`
- **usePrestamo(id):** Usado en el modal para recargar el préstamo.
- **useCuotasPrestamo(prestamoId):** Disponible; en `TablaAmortizacionPrestamo` se usa `useQuery` directo con key `['cuotas-prestamo', prestamo.id]` y `enabled` según estado del préstamo. Es una decisión válida (evita solicitudes cuando el préstamo no está aprobado/desembolsado). Opcional: unificar en el futuro con `useCuotasPrestamo` pasando `enabled` para compartir caché.

---

## 6. Util recibo PDF

- **Archivo:** `frontend/src/utils/reciboPagoPDF.ts`
- **Interfaces:** `ReciboPrestamoData`, `ReciboCuotaData` coherentes con los datos del préstamo y de la cuota.
- **Uso:** `TablaAmortizacionPrestamo` llama a `generarReciboPagoPDF(prestamo, cuota)` para la columna Recibo cuando la cuota está pagada.

---

## 7. Recomendaciones (opcionales)

1. **Caché de cuotas:** Valorar usar `useCuotasPrestamo` en `TablaAmortizacionPrestamo` con `enabled: (prestamo.estado === 'APROBADO' || prestamo.estado === 'DESEMBOLSADO')` para alinear keys de React Query y reutilizar caché en otras vistas.
2. **Manejo de 404:** El modal ya usa `prestamoData = prestamo || prestamoInitial`; si `getPrestamo` falla (p. ej. 404), se sigue mostrando el préstamo inicial. Comportamiento aceptable.
3. **Codificación:** En algunos entornos (p. ej. terminal Windows) los archivos con tildes pueden verse con caracteres raros; los fuentes revisados están en UTF-8 y los textos en UI (Préstamo, Amortización, etc.) son correctos en el código.

---

## 8. Archivos revisados

| Archivo | Revisión |
|---------|----------|
| `frontend/src/pages/Prestamos.tsx` | Página y uso del listado/modal. |
| `frontend/src/components/prestamos/PrestamosList.tsx` | Apertura del modal. |
| `frontend/src/components/prestamos/PrestamoDetalleModal.tsx` | Tabs, datos, TablaAmortizacionPrestamo. |
| `frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx` | Cuotas, estados, Excel, PDF, recibo. |
| `frontend/src/services/prestamoService.ts` | Llamadas a la API. |
| `frontend/src/hooks/usePrestamos.ts` | usePrestamo, useCuotasPrestamo. |
| `frontend/src/utils/reciboPagoPDF.ts` | Tipos y generación de recibo. |
| `frontend/src/App.tsx` | Ruta `prestamos`. |
| `backend/app/api/v1/endpoints/prestamos.py` | Endpoints cuotas, amortización, get_prestamo. |

---

**Auditoría completada. Todo OK para el flujo de tabla de amortización y detalles del préstamo.**
