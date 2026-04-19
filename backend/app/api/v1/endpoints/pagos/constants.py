"""Constantes del dominio pagos (endpoints)."""

# Límite de la columna numero_documento y referencia_pago en tabla pagos (String(100))
_MAX_LEN_NUMERO_DOCUMENTO = 100

# Validación de monto para NUMERIC(14, 2): máximo ~999,999,999,999.99 (12 dígitos antes del decimal)
_MAX_MONTO_PAGADO = 999_999_999_999.99
_MIN_MONTO_PAGADO = 0.01  # Monto mínimo válido (> 0)

_PRESTAMO_ID_MAX = 2_147_483_647  # INT max en BD (32-bit signed)

# Marca de sistema para auditoría cuando JWT no trae email (evita usuario_registro vacío en BD).
_USUARIO_REGISTRO_FALLBACK = "import-masivo@sistema.rapicredit.com"

# Zona horaria del negocio para "hoy" e "inicio_mes" (Monto cobrado mes, Pagos hoy)
TZ_NEGOCIO = "America/Caracas"
