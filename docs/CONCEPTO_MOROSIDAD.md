# Concepto de Pago vencido y Moroso

**Documento de referencia para Backend y Frontend.**

## Terminología

- **Pago vencido** = Cuotas vencidas y no pagadas (fecha_vencimiento < hoy). En UI se usa en lugar de "Morosidad".
- **Vencido** = Si debo pagar hasta el 23 feb, NO estoy vencido hasta el 24 feb. Desde el 24 = vencido (1-89 días de atraso).
- **Moroso** = 90 o más días de atraso (se declara como moroso desde el día 90).

## Definición de Pago vencido

Una cuota está **vencida** solo cuando:
1. `fecha_vencimiento < hoy` (la fecha de vencimiento ya pasó)
2. `fecha_pago IS NULL` (no se ha pagado)

## Ejemplo

- Cuota con vencimiento **23 de febrero**
- Hoy es **18 de febrero** → **NO** está vencida (aún no vence)
- Hoy es **24 de febrero** y no he pagado → **SÍ** está vencida (venció ayer)
- Hoy es **25 de mayo** (día 90+) y no he pagado → **Moroso** (90+ días de atraso)

## Aplicación en el sistema (Pago vencido)

| Componente | Condición aplicada |
|------------|--------------------|
| KPIs principales (total_morosidad_usd) | `fecha_vencimiento < hoy` |
| Composición de pago vencido | `dias_atraso >= 1` (equivale a `fecha_vencimiento < hoy`) |
| Pago vencido por analista | `fecha_vencimiento < hoy` |
| Pago vencido por día | `fecha_vencimiento < d` y no pagada al cierre del día d |
| Evolución pago vencido | `fecha_vencimiento < ref` (ref = min(fin_mes, hoy)) |
| Dashboard admin evolucion | `fecha_vencimiento < ref_moro` (ref_moro = min(fin_d, hoy)) |
| Pagos KPIs (morosidadMensualPorcentaje) | `fecha_vencimiento < hoy` |
| Reportes pago vencido | `fecha_vencimiento < fecha_corte` |

## Regla unificada

En todos los cálculos de pago vencido se usa:

```
fecha_vencimiento < fecha_referencia
AND fecha_pago IS NULL
```

(o equivalente: `fecha_pago IS NULL OR fecha_pago > fecha_referencia` cuando se evalúa "al cierre de" una fecha)
