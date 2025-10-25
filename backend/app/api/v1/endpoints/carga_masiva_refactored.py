# Funciones refactorizadas para carga masiva de clientes\nfrom typing \nimport Dict, List, Tuple\nimport pandas as pd\nimport
# io\nfrom fastapi \nimport HTTPException\nfrom sqlalchemy.orm \nimport Session\nimport logging\nfrom
# app.schemas.carga_masiva \nimport ErrorCargaMasiva, ResultadoCargaMasivalogger = logging.getLogger(__name__)\ndef
# _obtener_mapeo_columnas() -> Dict[str, str]:\n """Obtener mapeo de columnas Excel a sistema""" return { "CEDULA
# IDENTIDAD":\n "cedula", "CEDULA IDENT":\n "cedula", "CEDULA":\n "cedula", "NOMBRE":\n "nombre", "APELLIDO":\n "apellido",
# "MOVIL":\n "movil", "TELEFONO":\n "movil", "CORREO ELECTRONICO":\n "email", "EMAIL":\n "email", "DIRECCION":\n "direccion",
# "MODELO VEHICULO":\n "modelo_vehiculo", "MODELO":\n "modelo_vehiculo", "CONCESIONARIO":\n "concesionario", "TOTAL
# FINANCIAMIENTO":\n "total_financiamiento", "MONTO FINANCIAMIENTO":\n "total_financiamiento", "CUOTA INICIAL":\n
# "cuota_inicial", "INICIAL":\n "cuota_inicial", "NUMERO AMORTIZACIONES":\n "numero_amortizaciones", "AMORTIZACIONES":\n
# "numero_amortizaciones", "CUOTAS":\n "numero_amortizaciones", "MODALIDAD PAGO":\n "modalidad_pago", "MODALIDAD":\n
# "modalidad_pago", "FECHA ENTREGA":\n "fecha_entrega", "ENTREGA":\n "fecha_entrega", "USER":\n "asesor", "USER ASIGNADO":\n
# "asesor", }\ndef _validar_columnas_requeridas(df:\n pd.DataFrame) -> None:\n """Validar que existan las columnas
# requeridas""" columnas_requeridas = ["cedula", "nombre"] columnas_faltantes = [ col for col in columnas_requeridas if col
# not in df.columns ] if columnas_faltantes:\n raise HTTPException( status_code=400, detail=f"Faltan columnas:\n {',
# "")).strip() apellido = ( str(row.get("apellido", "")).strip() if "apellido" in row else "" ) movil = str(row.get("movil",
# "")).strip() email = str(row.get("email", "")).strip() direccion = str(row.get("direccion", "")).strip() modelo_vehiculo =
# str(row.get("modelo_vehiculo", "")).strip() concesionario = str(row.get("concesionario", "")).strip() total_financiamiento
# = str(row.get("total_financiamiento", "")).strip() cuota_inicial = str(row.get("cuota_inicial", "")).strip()
# numero_amortizaciones = str(row.get("numero_amortizaciones", "")).strip() modalidad_pago = str(row.get("modalidad_pago",
# "")).strip() fecha_entrega = str(row.get("fecha_entrega", "")).strip() asesor = str(row.get("asesor", "")).strip() # Si no
# hay apellido separado, intentar split del nombre if not apellido and nombre:\n partes_nombre = nombre.split(" ", 1) if
# len(partes_nombre) > 1:\n nombre = partes_nombre[0] apellido = partes_nombre[1] return { "cedula":\n cedula, "nombre":\n
# nombre, "apellido":\n apellido, "movil":\n movil, "email":\n email, "direccion":\n direccion, "modelo_vehiculo":\n
# modelo_vehiculo, "concesionario":\n concesionario, "total_financiamiento":\n total_financiamiento, "cuota_inicial":\n
# cuota_inicial, "numero_amortizaciones":\n numero_amortizaciones, "modalidad_pago":\n modalidad_pago, "fecha_entrega":\n
# vacía o marcada como ERROR", tipo_error="CRITICO", puede_corregirse=True, sugerencia="Ingrese cédula válida (ej:\n
# str, db:\n Session, usuario_id:\n int) -> ResultadoCargaMasiva:\n """ Analizar archivo de clientes sin guardar (VERSIÓN
# # Mapear columnas y validar estructura mapeo_columnas = _obtener_mapeo_columnas() df = df.rename(columns=mapeo_columnas)
# Exception as e:\n logger.error(f"Error analizando archivo de clientes:\n {e}") raise HTTPException(status_code=500,
# detail=f"Error interno:\n {str(e)}")
