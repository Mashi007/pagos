-- =============================================================================
-- VERIFICAR INCREMENTO EN CLIENTES (ejecutar en DBeaver)
-- INSTRUCCIÓN: Ejecutar SOLO hasta la línea "FIN". Cuando veas total_clientes,
--             primer_registro y ultimo_registro, escribe "fin" y después
--             ejecuta el resto (después de FIN).
-- Usa fecha_registro para ver altas por período y tendencia.
-- =============================================================================

-- 1) Total actual y rango de fechas de registro
SELECT COUNT(*) AS total_clientes,
       MIN(fecha_registro)::date AS primer_registro,
       MAX(fecha_registro)::date AS ultimo_registro
FROM public.clientes;

-- FIN
-- ========== No proceses el resto hasta ver el resultado anterior y escribir fin ==========


-- 2) Incremento por día (últimos 30 días o todos si hay menos historia)
SELECT fecha_registro::date AS fecha,
       COUNT(*) AS clientes_altas
FROM public.clientes
WHERE fecha_registro >= (SELECT MAX(fecha_registro)::date - 30 FROM public.clientes)
GROUP BY fecha_registro::date
ORDER BY fecha DESC;

-- 3) Incremento por mes (todos los meses con datos)
SELECT date_trunc('month', fecha_registro)::date AS mes,
       COUNT(*) AS clientes_altas
FROM public.clientes
GROUP BY date_trunc('month', fecha_registro)
ORDER BY mes DESC;

-- 4) Acumulado por mes (clientes registrados hasta el fin de cada mes)
SELECT mes,
       SUM(clientes_altas) OVER (ORDER BY mes) AS clientes_acumulados
FROM (
  SELECT date_trunc('month', fecha_registro)::date AS mes,
         COUNT(*) AS clientes_altas
  FROM public.clientes
  GROUP BY date_trunc('month', fecha_registro)
) t
ORDER BY mes;

-- 5) Resumen últimos 7 días (incremento reciente)
SELECT COUNT(*) AS altas_ultimos_7_dias
FROM public.clientes
WHERE fecha_registro >= CURRENT_DATE - 7;
