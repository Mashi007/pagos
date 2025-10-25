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
# '.join(columnas_faltantes)}", )\ndef _extraer_datos_fila(row:\n pd.Series, fila_numero:\n int) -> Dict[str, str]:\n
# """Extraer y limpiar datos de una fila""" cedula = str(row.get("cedula", "")).strip() nombre = str(row.get("nombre",
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
# fecha_entrega, "asesor":\n asesor, "fila_numero":\n fila_numero, }\ndef _validar_campos_criticos( datos:\n Dict[str, str],)
# -> Tuple[List[ErrorCargaMasiva], int]:\n """Validar campos críticos y generar errores""" errores = [] errores_criticos = 0
# # Cédula (CRÍTICO) if not datos["cedula"] or datos["cedula"].upper() == "ERROR":\n errores.append( ErrorCargaMasiva(
# fila=datos["fila_numero"], cedula=datos["cedula"] or "VACÍO", campo="cedula", valor_original=datos["cedula"], error="Cédula
# vacía o marcada como ERROR", tipo_error="CRITICO", puede_corregirse=True, sugerencia="Ingrese cédula válida (ej:\n
# V12345678)", ) ) errores_criticos += 1 # Nombre (CRÍTICO) if not datos["nombre"] or datos["nombre"].upper() == "ERROR":\n
# errores.append( ErrorCargaMasiva( fila=datos["fila_numero"], cedula=datos["cedula"] or "VACÍO", campo="nombre",
# valor_original=datos["nombre"], error="Nombre vacío o marcado como ERROR", tipo_error="CRITICO", puede_corregirse=True,
# sugerencia="Ingrese nombre completo del cliente", ) ) errores_criticos += 1 # Total Financiamiento (CRÍTICO si se quiere
# financiamiento) if ( not datos["total_financiamiento"] or datos["total_financiamiento"].upper() == "ERROR" ):\n
# errores.append( ErrorCargaMasiva( fila=datos["fila_numero"], cedula=datos["cedula"], campo="total_financiamiento",
# valor_original=datos["total_financiamiento"], error="Total financiamiento vacío o marcado como ERROR",
# tipo_error="CRITICO", puede_corregirse=True, sugerencia="Ingrese monto válido (ej:\n 5000000)", ) ) errores_criticos += 1
# return errores, errores_criticosasync \ndef _analizar_archivo_clientes_refactored( contenido:\n bytes, nombre_archivo:\n
# str, db:\n Session, usuario_id:\n int) -> ResultadoCargaMasiva:\n """ Analizar archivo de clientes sin guardar (VERSIÓN
# REFACTORIZADA) Detectar TODOS los errores y clasificarlos """ try:\n # Leer Excel df = pd.read_excel(io.BytesIO(contenido))
# # Mapear columnas y validar estructura mapeo_columnas = _obtener_mapeo_columnas() df = df.rename(columns=mapeo_columnas)
# _validar_columnas_requeridas(df) # Procesar cada registro registros_procesados = [] total_registros = len(df)
# registros_con_errores = 0 errores_criticos = 0 errores_advertencia = 0 datos_vacios = 0 todos_los_errores = [] for index,
# row in df.iterrows():\n fila_numero = ( index + 2 ) # +2 porque Excel empieza en 1 y tiene header # Extraer datos de la
# fila datos = _extraer_datos_fila(row, fila_numero) # Validar campos críticos errores_registro, criticos =
# _validar_campos_criticos(datos) errores_criticos += criticos # TODO:\n Agregar más validaciones aquí... # - Validación de
# formato de cédula # - Validación de email # - Validación de teléfono # - Validación de montos # - Validación de fechas if
# errores_registro:\n registros_con_errores += 1 todos_los_errores.extend(errores_registro) else:\n
# registros_procesados.append(datos) return ResultadoCargaMasiva( archivo=nombre_archivo, total_registros=total_registros,
# registros_procesados=len(registros_procesados), registros_con_errores=registros_con_errores,
# errores_criticos=errores_criticos, errores_advertencia=errores_advertencia, datos_vacios=datos_vacios, tasa_exito=(
# round(len(registros_procesados) / total_registros * 100, 1) if total_registros > 0 else 0 ),
# errores_detallados=todos_los_errores, registros_validos=registros_procesados, ) except HTTPException:\n raise except
# Exception as e:\n logger.error(f"Error analizando archivo de clientes:\n {e}") raise HTTPException(status_code=500,
# detail=f"Error interno:\n {str(e)}")
