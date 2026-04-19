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
| Plantilla PDF (ReportLab) | `app/services/cobros/recibo_pdf.py` → `generar_recibo_pago_reportado` |

**Regla de tasa en el recibo:** moneda BS → tasa oficial del **dia `fecha_pago`** si existe; si no hay fecha, **tasa de hoy** (Caracas). Coherente con el listado/detalle de pagos reportados.

Endpoints que generan o persisten este PDF deben llamar solo al centro (no duplicar `_generar_recibo_desde_pago` en routers).

## Otros PDFs de recibo

| Caso | Modulo | Notas |
|------|--------|--------|
| Cuota (tabla de amortizacion) | `recibo_cuota_amortizacion.py` | Misma plantilla que `recibo_pdf`; datos vienen del prestamo/cuota, no de `PagoReportado`. |
| Pago reconocido en cartera | `recibo_pago_cartera_pdf.py` | Layout distinto; reutiliza branding de `recibo_pdf`. Si se cruza con montos/tasas de listados, alinear reglas con este documento. |

## Import sugerido

Para nuevos servicios que necesiten ambos mundos:

- **Un solo modulo (re-export):** `app.services.documentos_cliente_centro`.
- Estado de cuenta (implementacion): `estado_cuenta_datos` / `estado_cuenta_pdf`.
- Recibo reportado (implementacion): `recibo_pago_reportado_centro.generar_recibo_pdf_desde_pago_reportado`.
