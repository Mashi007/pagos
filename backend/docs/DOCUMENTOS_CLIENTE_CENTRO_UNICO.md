# Documentos al cliente: centro unico (estado de cuenta y recibos)

Objetivo: **misma semantica de datos** en API, PDF publico/privado y adjuntos guardados.

## Estado de cuenta

| Capa | Modulo |
|------|--------|
| Datos (BD, cuotas, enlaces a recibos, JSON) | `app/services/estado_cuenta_datos.py` |
| PDF | `app/services/estado_cuenta_pdf.py` → `generar_pdf_estado_cuenta` |

Detalle de consumidores: `backend/docs/ESTADO_CUENTA_FUENTE_UNICA.md`.

## Recibo por pago reportado (Cobros)

| Capa | Modulo |
|------|--------|
| Ensamblaje desde `PagoReportado` + BD (cuotas, saldos, tasa BS/USD) | `app/services/cobros/recibo_pago_reportado_centro.py` → `generar_recibo_pdf_desde_pago_reportado` |
| Texto de cuotas / saldos (mismo enlace pago que importacion) | `app/services/cobros/recibo_cuotas_lookup.py` |
| Plantilla PDF (ReportLab) | `app/services/cobros/recibo_pdf.py` → `generar_recibo_pago_reportado` (si `pagos_reportados.comprobante` tiene imagen, se incrusta; si es PDF, nota de texto) |

**Regla de tasa en el recibo:** misma que API/Excel de pagos reportados (`tasa_y_equivalente_usd_excel`): en BS, tasa del dia **`fecha_pago`** si hay fila en `tasas_cambio_diaria`; si no hay tasa para esa fecha, el recibo no inventa otra (queda sin tasa en el PDF). En USD no aplica tasa Bs.

Endpoints que generan o persisten este PDF deben llamar solo al centro (no duplicar `_generar_recibo_desde_pago` en routers).

## Otros PDFs de recibo

| Caso | Modulo | Notas |
|------|--------|--------|
| Cuota (tabla de amortizacion) | `recibo_cuota_amortizacion.py` | Misma plantilla que `recibo_pdf`; datos vienen del prestamo/cuota, no de `PagoReportado`. |
| Pago reconocido en cartera | `recibo_pago_cartera_pdf.py` | Layout distinto; nota opcional de tasa Bs desde `pagos.tasa_cambio_bs_usd` / `fecha_tasa_referencia` (portal estado de cuenta). |

## Import sugerido

Para nuevos servicios que necesiten ambos mundos:

- **Un solo modulo (re-export):** `app.services.documentos_cliente_centro`.
- **Routers que ya usan el facade:** `estado_cuenta_publico`, `prestamos` (JSON/PDF estado de cuenta), `cobros`, `cobros_publico` (recibo PDF desde pago reportado).
- Estado de cuenta (implementacion interna): `estado_cuenta_datos` / `estado_cuenta_pdf` (el facade re-exporta las mismas funciones).
- Recibo reportado (implementacion interna): `recibo_pago_reportado_centro` (el facade re-exporta `generar_recibo_pdf_desde_pago_reportado`).
