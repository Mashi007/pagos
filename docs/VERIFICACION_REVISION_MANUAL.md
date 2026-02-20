# Verificación Backend y Frontend - Revisión Manual

## Backend

### Endpoints (`/api/v1/revision-manual/...`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/prestamos` | Lista préstamos para revisión (filtro: pendiente/revisando/revisado) |
| PUT | `/prestamos/{id}/confirmar` | Marca como revisado |
| PUT | `/prestamos/{id}/iniciar-revision` | Inicia revisión (estado → revisando) |
| PUT | `/prestamos/{id}/finalizar-revision` | Finaliza revisión (Guardar y Cerrar) |
| PUT | `/clientes/{id}` | Edita cliente |
| PUT | `/prestamos/{id}` | Edita préstamo |
| DELETE | `/prestamos/{id}` | Elimina préstamo |
| GET | `/pagos/{cedula}` | Pagos por cédula |
| PUT | `/cuotas/{id}` | Edita cuota |
| GET | `/resumen-rapido` | Resumen pendientes/revisando |
| GET | `/prestamos/{id}/detalle` | Detalle completo para edición |

### Modelo BD: `revision_manual_prestamos`

- `prestamo_id`, `estado_revision` (pendiente/revisando/revisado)
- `usuario_revision_email`, `fecha_revision`
- `cliente_editado`, `prestamo_editado`, `pagos_editados`

### Listado de préstamos (`prestamos.py`)

- Incluye `revision_manual_estado` por préstamo (desde `revision_manual_prestamos`)

---

## Frontend

### Servicio `revisionManualService.ts`

- `baseUrl`: `/api/v1/revision-manual`
- Métodos: `getPreslamosRevision`, `confirmarPrestamoRevisado`, `iniciarRevision`, `finalizarRevision`, `editarCliente`, `editarPrestamo`, `eliminarPrestamo`, `getPagosPorCedula`, `getDetallePrestamoRevision`, `getResumenRapidoRevision`, `editarCuota`

### Rutas

- `/revision-manual` → Lista de revisión
- `/revision-manual/editar/:prestamoId` → Editor de revisión

### Iconos en Acciones (PrestamosList)

| Estado | Icono | Significado |
|--------|-------|-------------|
| pendiente / null | ⚠ Triángulo | No ha sido revisado |
| revisando | ? Info | Está siendo revisado |
| revisado | (ninguno) | Ya se revisó |

### Botón "Revisión Manual"

- En barra de acciones de lista de préstamos (junto a Actualizar y Nuevo Préstamo)

---

## Correcciones aplicadas

1. **Rutas backend**: Las rutas tenían `/revision-manual` duplicado (prefix + ruta). Se cambiaron de `/revision-manual/prestamos` a `/prestamos` para que la URL final sea `/api/v1/revision-manual/prestamos`.

2. **Endpoint finalizar-revision**: Se añadió el decorador `@router.put("/prestamos/{prestamo_id}/finalizar-revision")` que faltaba en la función `finalizar_revision_prestamo`.
