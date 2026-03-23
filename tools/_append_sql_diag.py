from pathlib import Path

p = Path(__file__).resolve().parents[1] / "sql" / "2026-03-23_diagnostico_cuotas_pagos_integridad.sql"
text = p.read_text(encoding="utf-8")
if "-- 3) Detalle" in text:
    raise SystemExit("already extended")

append = r"""

-- 3) Detalle: cada fila de cuota_pagos del prestamo
SELECT
  cp.id AS cuota_pago_id,
  cp.cuota_id,
  c.numero_cuota,
  cp.pago_id,
  cp.monto_aplicado,
  cp.fecha_aplicacion,
  cp.es_pago_completo
FROM cuota_pagos cp
JOIN cuotas c ON c.id = cp.cuota_id
WHERE c.prestamo_id = 983
ORDER BY c.numero_cuota, cp.pago_id, cp.id;

-- 4) Mismo pago_id repetido en la misma cuota (no deberia)
SELECT cp.cuota_id, cp.pago_id, COUNT(*) AS veces, SUM(cp.monto_aplicado) AS suma_montos
FROM cuota_pagos cp
JOIN cuotas c ON c.id = cp.cuota_id
WHERE c.prestamo_id = 983
GROUP BY cp.cuota_id, cp.pago_id
HAVING COUNT(*) > 1;

-- 5) Balance global: pagos conciliados vs suma cuota_pagos
SELECT
  (SELECT COALESCE(SUM(p.monto_pagado), 0)
   FROM pagos p
   WHERE p.prestamo_id = 983
     AND p.monto_pagado > 0
     AND (
       p.conciliado = TRUE
       OR upper(trim(coalesce(p.verificado_concordancia, ''))) = 'SI'
     )
  ) AS sum_monto_pagos,
  (SELECT COALESCE(SUM(cp.monto_aplicado), 0)
   FROM cuota_pagos cp
   JOIN cuotas c ON c.id = cp.cuota_id
   WHERE c.prestamo_id = 983
  ) AS sum_monto_cuota_pagos;

/*
Interpretacion de diffs negativos grandes:
- total_pagado < sum(cuota_pagos): mas dinero en cuota_pagos que en la columna cuotas (doble registro o
  reaplicacion sin reset; o total_pagado no actualizado).
Correccion integral: POST /api/v1/prestamos/983/reaplicar-fifo-aplicacion (admin).
*/
"""
p.write_text(text.rstrip() + append + "\n", encoding="utf-8")
print("ok")
