-- Intercambio PERMANENTE de listas: Yohana Landaeta <-> Glainet Dudamel.
-- Idempotente: si la flag ya existe, no-op (NO revierte).
-- Tambien lo aplica el backend al arranque y al abrir Gestores.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM configuracion
    WHERE clave = 'cobranza_gestores_swap_yohana_glainet_v1'
      AND lower(trim(valor)) IN ('1', 'true', 'si', 'yes')
  ) THEN
    RAISE NOTICE 'Swap permanente Yohana/Glainet ya aplicado; no-op.';
    RETURN;
  END IF;

  -- Asignaciones (listas)
  UPDATE cobranza_gestor_asignaciones
  SET gestor_slug = CASE
    WHEN gestor_slug = 'yohana-landaeta' THEN 'glainet-dudamel'
    WHEN gestor_slug = 'glainet-dudamel' THEN 'yohana-landaeta'
    ELSE gestor_slug
  END
  WHERE gestor_slug IN ('yohana-landaeta', 'glainet-dudamel');

  -- Historial diario (graficos); usa slug temporal por PK (fecha, gestor_slug)
  UPDATE cobranza_gestor_desempeno_diario
  SET gestor_slug = '__swap_tmp_yohana_glainet__'
  WHERE gestor_slug = 'yohana-landaeta';

  UPDATE cobranza_gestor_desempeno_diario
  SET gestor_slug = 'yohana-landaeta'
  WHERE gestor_slug = 'glainet-dudamel';

  UPDATE cobranza_gestor_desempeno_diario
  SET gestor_slug = 'glainet-dudamel'
  WHERE gestor_slug = '__swap_tmp_yohana_glainet__';

  INSERT INTO configuracion (clave, valor)
  VALUES ('cobranza_gestores_swap_yohana_glainet_v1', 'true')
  ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;

  RAISE NOTICE 'Swap permanente Yohana <-> Glainet aplicado.';
END $$;
