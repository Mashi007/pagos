# Alineación de Notificaciones con tablas prestamos, pagos y cuotas

Verificación realizada para que la pantalla **Notificaciones** (`/pagos/notificaciones`) y sus APIs usen y actualicen correctamente las tablas según las últimas implementaciones (estado LIQUIDADO, batch de pagos, cuotas con `fecha_pago`/`total_pagado`).

## 1. Tabla **cuotas**

- **Criterio de “cuota pendiente”**: en todo el flujo de notificaciones se usa **`Cuota.fecha_pago.is_(None)`**.
- **Dónde**:
  - `app.services.notificacion_service.get_cuotas_pendientes_con_cliente()`: fuente única para listados y envíos.
  - `app.api.v1.endpoints.notificaciones.build_contexto_cobranza_para_item()`: cuotas vencidas no pagadas (`fecha_pago` nula, `fecha_vencimiento <= hoy`).
  - `get_notificaciones_tabs_data()` y `get_clientes_retrasados()`: usan esa misma fuente.
- **Conclusión**: alineado con el modelo de cuotas y con la lógica de aplicación de pagos (cuando se aplica un pago a cuotas se rellena `fecha_pago` y `total_pagado`). No se usa un campo obsoleto tipo `pagado` booleano.

## 2. Tabla **prestamos** (estado LIQUIDADO)

- Según `LIQUIDADO_Y_BATCH_TRANSACCION.md`, cuando todas las cuotas están pagadas el préstamo se marca como **LIQUIDADO** (`estado = 'LIQUIDADO'`).
- **Recomendación**: en la consulta de cuotas pendientes para notificaciones, excluir explícitamente préstamos liquidados para evitar notificar por préstamos ya cerrados (p. ej. por datos legacy o inconsistencias).
- **Cambio sugerido** en `app.services.notificacion_service.get_cuotas_pendientes_con_cliente()`:

```python
q = (
    select(Cuota, Cliente)
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .join(Cliente, Prestamo.cliente_id == Cliente.id)
    .where(Cuota.fecha_pago.is_(None))
    .where(Prestamo.estado != "LIQUIDADO")  # añadir esta línea
)
```

- Actualizar también el docstring de la función indicando que se excluyen préstamos en estado LIQUIDADO.

## 3. Tabla **pagos** y batch

- Los endpoints de notificaciones **no escriben** en la tabla `pagos`.
- La tabla **`envios_notificacion`** solo registra envíos de correos (éxito/fallo, tipo_tab, prestamo_id, correlativo, etc.) para estadísticas y rebotados.
- El batch de pagos (`POST /api/v1/pagos/batch`) y la aplicación a cuotas actualizan `pagos`, `cuotas` y, al liquidar, `prestamos.estado`. Las notificaciones solo **leen** cuotas/prestamos/clientes para decidir a quién notificar y **escriben** en `envios_notificacion`.
- **Conclusión**: no hay desalineación; las notificaciones no deben actualizar `pagos` ni `cuotas`.

## 4. Resumen

| Área              | Estado     | Acción |
|-------------------|------------|--------|
| Cuotas (pendiente)| Alineado   | Ninguna; ya se usa `fecha_pago.is_(None)`. |
| Prestamos (LIQUIDADO) | Recomendado | Añadir filtro `Prestamo.estado != "LIQUIDADO"` en `get_cuotas_pendientes_con_cliente`. |
| Pagos / envios_notificacion | Correcto | Notificaciones solo leen prestamos/cuotas y escriben en envios_notificacion. |

Fecha de verificación: 2025-03-18.
