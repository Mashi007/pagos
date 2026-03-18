# Verificación: módulos públicos y datos de BD (fechas y cuotas)

Tras aplicar las correcciones en BD (intercambio fecha_requerimiento/fecha_aprobacion y actualización de vencimientos de cuotas), se verificó si los módulos públicos de la app usan datos actualizados.

## Rutas y componentes

| URL (ej. https://rapicredit.onrender.com/pagos/...) | Ruta frontend | Componente |
|-----------------------------------------------------|---------------|------------|
| `/pagos/rapicredit-cobros` | `rapicredit-cobros` | `ReportePagoPage` (variant cobros) |
| `/pagos/rapicredit-estadocuenta` | `rapicredit-estadocuenta` | `EstadoCuentaPublicoPage` |
| `/pagos/informes` | `informes` | `EstadoCuentaPublicoPage` (origen informes) |
| `/pagos/infopagos` | `infopagos` | `InfopagosPage` → `ReportePagoPage` (variant infopagos) |

## Fuente de datos

- **rapicredit-cobros** y **infopagos**: formulario público para **reportar un pago** (cédula, monto, comprobante). No muestran tabla de amortización ni listado de cuotas; envían el reporte al backend. Cualquier dato que el usuario vea después (p. ej. en estado de cuenta) viene de la BD en la siguiente consulta.
- **rapicredit-estadocuenta** e **informes**: consulta de **estado de cuenta** por cédula. El backend:
  - Valida cédula y (en flujo con código) envía código por email.
  - Al verificar código o al solicitar estado de cuenta (informes), llama a `generar_pdf_estado_cuenta()` en `app/services/estado_cuenta_pdf.py`.
  - Los datos del PDF (préstamos, cuotas pendientes, amortización) se **obtienen de la BD en el momento de la petición** (endpoints en `estado_cuenta_publico.py`).

No hay caché de préstamos/cuotas/fechas en el frontend para estas pantallas; cada consulta de estado de cuenta o generación de PDF usa la BD actual.

## Conclusión

**Los cuatro módulos están alineados con la BD.** No requieren cambios de código para reflejar las correcciones ya aplicadas:

1. **Intercambio de fechas** en `prestamos` (fecha_requerimiento / fecha_aprobacion).
2. **Actualización de `cuotas.fecha_vencimiento`** según `prestamos.fecha_aprobacion`.

Al abrir o refrescar:

- **Estado de cuenta** (rapicredit-estadocuenta o informes): el PDF y los datos se generan con los préstamos y cuotas actuales (fechas y vencimientos ya corregidos).
- **Reporte de pago** (rapicredit-cobros, infopagos): siguen siendo formularios de envío; los datos de cuotas/préstamos que se vean en otras pantallas siguen saliendo de la BD actualizada.

Si el frontend está desplegado en Render y la BD es la misma donde se ejecutaron los SQL, no hace falta redesplegar ni “actualizar” estos módulos; solo asegurarse de que el backend apunte a esa BD y de que no exista caché intermedio (p. ej. CDN) que sirva respuestas viejas.
