# Funciones refactorizadas para carga masiva de clientes\nfrom typing \nimport Dict, List, Tuple\nimport pandas as pd\nimport
# io\nfrom fastapi \nimport HTTPException\nfrom sqlalchemy.orm \nimport Session\nimport logging\nfrom
# app.schemas.carga_masiva \nimport ErrorCargaMasiva, ResultadoCargaMasivalogger = logging.getLogger(__name__)\ndef
# _obtener_mapeo_columnas() -> Dict[str, str]:\n """Obtener mapeo de columnas Excel a sistema""" return 
# "asesor", }\ndef _validar_columnas_requeridas(df:\n pd.DataFrame) -> None:\n """Validar que existan las columnas
# requeridas""" columnas_requeridas = ["cedula", "nombre"] columnas_faltantes = [ col for col in columnas_requeridas if col
# not in df.columns ] if columnas_faltantes:\n raise HTTPException
# "")).strip() apellido = ( str(row.get("apellido", "")).strip() if "apellido" in row else "" ) movil = str
# "")).strip() email = str(row.get("email", "")).strip() direccion = str(row.get("direccion", "")).strip() modelo_vehiculo =
# str(row.get("modelo_vehiculo", "")).strip() concesionario = str(row.get("concesionario", "")).strip() total_financiamiento
# = str(row.get("total_financiamiento", "")).strip() cuota_inicial = str(row.get("cuota_inicial", "")).strip()
# numero_amortizaciones = str(row.get("numero_amortizaciones", "")).strip() modalidad_pago = str
# "")).strip() fecha_entrega = str(row.get("fecha_entrega", "")).strip() asesor = str(row.get("asesor", "")).strip() # Si no
# hay apellido separado, intentar split del nombre if not apellido and nombre:\n partes_nombre = nombre.split(" ", 1) if
# len(partes_nombre) > 1:\n nombre = partes_nombre[0] apellido = partes_nombre[1] return 
# Exception as e:\n logger.error(f"Error analizando archivo de clientes:\n {e}") raise HTTPException
# detail=f"Error interno:\n {str(e)}")

"""
"""