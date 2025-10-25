# \nimport Decimal\nfrom typing \nimport Any, Dict, List, Optional\nimport pandas as pd\nfrom fastapi \nimport APIRouter,
# Depends, File, Form, HTTPException, UploadFile\nfrom fastapi.responses \nimport StreamingResponse\nfrom pydantic \nimport
# BaseModel\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom
# app.models.analista \nimport Analista\nfrom app.models.auditoria \nimport Auditoria, TipoAccion\nfrom app.models.cliente
# \nimport Cliente\nfrom app.models.concesionario \nimport Concesionario\nfrom app.models.modelo_vehiculo \nimport
# ModeloVehiculo\nfrom app.models.pago \nimport Pago\nfrom app.models.user \nimport User\nfrom
# app.services.validators_service \nimport ( ValidadorCedula, ValidadorEmail, ValidadorFecha, ValidadorMonto,
# ValidadorTelefono,)logger = logging.getLogger(__name__)router = APIRouter()# ============================================#
# SCHEMAS PARA CARGA MASIVA# ============================================\nclass ErrorCargaMasiva(BaseModel):\n """Error
# encontrado en carga masiva""" fila:\n int cedula:\n str campo:\n str valor_original:\n str error:\n str tipo_error:\n str #
# CRITICO, ADVERTENCIA, DATO_VACIO puede_corregirse:\n bool sugerencia:\n Optional[str] = None\nclass
# RegistroCargaMasiva(BaseModel):\n """Registro procesado en carga masiva""" fila:\n int cedula:\n str nombre_completo:\n str
# cedula:\n str correcciones:\n Dict[str, str]# ============================================# ENDPOINT:\n SUBIR ARCHIVO
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📤 PASO 1:\n Subir archivo Excel
# ADVERTENCIA, DATO_VACÍO) 4. NO guardar nada aún 5. Retornar dashboard con errores para corrección """ try:\n # Validar tipo
# de archivo if not archivo.filename.endswith((".xlsx", ".xls")):\n raise HTTPException( status_code=400, detail="Solo se
# tipo_carga == "clientes":\n resultado = await _analizar_archivo_clientes( contenido, archivo.filename, db, current_user.id
# auditoría auditoria = Auditoria.registrar( usuario_id=current_user.id, accion=TipoAccion.CREAR, tabla="CargaMasiva",
# HTTPException:\n raise except Exception as e:\n raise HTTPException( status_code=500, detail="Error al procesar archivo:\n
# {str(e)}", )# ============================================# FUNCIÓN:\n ANALIZAR ARCHIVO DE CLIENTES#
# ============================================\ndef _mapear_columnas(df:\n pd.DataFrame) -> pd.DataFrame:\n """Mapear
# columnas del Excel al sistema""" mapeo_columnas = { "CEDULA IDENTIDAD":\n "cedula", "CEDULA IDENT":\n "cedula", "CEDULA":\n
# "cedula", "NOMBRE":\n "nombre", "APELLIDO":\n "apellido", "MOVIL":\n "movil", "TELEFONO":\n "movil", "CORREO
# ELECTRONICO":\n "email", "EMAIL":\n "email", "DIRECCION":\n "direccion", "MODELO VEHICULO":\n "modelo_vehiculo",
# "MODELO":\n "modelo_vehiculo", "CONCESIONARIO":\n "concesionario", "TOTAL FINANCIAMIENTO":\n "total_financiamiento", "MONTO
# FINANCIAMIENTO":\n "total_financiamiento", "CUOTA INICIAL":\n "cuota_inicial", "INICIAL":\n "cuota_inicial", "NUMERO
# AMORTIZACIONES":\n "numero_amortizaciones", "AMORTIZACIONES":\n "numero_amortizaciones", "CUOTAS":\n
# "numero_amortizaciones", "MODALIDAD PAGO":\n "modalidad_pago", "MODALIDAD":\n "modalidad_pago", "FECHA ENTREGA":\n
# "fecha_entrega", "ENTREGA":\n "fecha_entrega", "USER":\n "asesor", "USER ASIGNADO":\n "asesor", } return
# df.rename(columns=mapeo_columnas)\ndef _validar_columnas_requeridas(df:\n pd.DataFrame) -> None:\n """Validar que existan
# las columnas requeridas""" columnas_requeridas = ["cedula", "nombre"] columnas_faltantes = [ col for col in
# columnas_requeridas if col not in df.columns ] if columnas_faltantes:\n raise HTTPException( status_code=400, detail="❌
# del DataFrame""" fila_numero = index + 2 # +2 porque Excel empieza en 1 y tiene header cedula = str(row.get("cedula",
# "")).strip() nombre = str(row.get("nombre", "")).strip() apellido = ( str(row.get("apellido", "")).strip() if "apellido" in
# row else "" ) movil = str(row.get("movil", "")).strip() email = str(row.get("email", "")).strip() direccion =
# str(row.get("direccion", "")).strip() modelo_vehiculo = str(row.get("modelo_vehiculo", "")).strip() concesionario =
# str(row.get("concesionario", "")).strip() total_financiamiento = str(row.get("total_financiamiento", "")).strip()
# cuota_inicial = str(row.get("cuota_inicial", "")).strip() numero_amortizaciones = str(row.get("numero_amortizaciones",
# "")).strip() modalidad_pago = str(row.get("modalidad_pago", "")).strip() fecha_entrega = str(row.get("fecha_entrega",
# "")).strip() asesor = str(row.get("asesor", "")).strip() # Si no hay apellido separado, intentar split del nombre if not
# apellido and nombre:\n partes_nombre = nombre.split(" ", 1) if len(partes_nombre) > 1:\n nombre = partes_nombre[0] apellido
# = partes_nombre[1] return ( fila_numero, cedula, nombre, apellido, movil, email, direccion, modelo_vehiculo, concesionario,
# total_financiamiento, cuota_inicial, numero_amortizaciones, modalidad_pago, fecha_entrega, asesor, )\ndef
# errores""" errores = [] # Cédula (CRÍTICO) if not cedula or cedula.upper() == "ERROR":\n errores.append( ErrorCargaMasiva(
# fila=fila_numero, cedula=cedula or "VACÍO", campo="cedula", valor_original=cedula, error="Cédula vacía o marcada como
# ERROR", tipo_error="CRITICO", puede_corregirse=True, sugerencia="Ingrese cédula válida (ej:\n V12345678)", ) ) # Nombre
# (CRÍTICO) if not nombre or nombre.upper() == "ERROR":\n errores.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula
# or "VACÍO", campo="nombre", valor_original=nombre, error="Nombre vacío o marcado como ERROR", tipo_error="CRITICO",
# puede_corregirse=True, sugerencia="Ingrese nombre completo del cliente", ) ) # Total Financiamiento (CRÍTICO si se quiere
# financiamiento) if not total_financiamiento or total_financiamiento.upper() == "ERROR":\n errores.append( ErrorCargaMasiva(
# fila=fila_numero, cedula=cedula, campo="total_financiamiento", valor_original=total_financiamiento, error="Total
# financiamiento vacío o marcado como ERROR", tipo_error="DATO_VACIO", puede_corregirse=True, sugerencia="Ingrese monto del
# financiamiento (ej:\n 50000)", ) ) # Número de Amortizaciones (CRÍTICO si hay financiamiento) if total_financiamiento and (
# not numero_amortizaciones or numero_amortizaciones.upper() == "ERROR" ):\n errores.append( ErrorCargaMasiva(
# fila=fila_numero, cedula=cedula, campo="numero_amortizaciones", valor_original=numero_amortizaciones, error="Número de
# amortizaciones vacío o marcado como ERROR", tipo_error="DATO_VACIO", puede_corregirse=True, sugerencia="Ingrese número de
# cuotas (ej:\n 12, 24, 36)", ) ) # Fecha Entrega (CRÍTICO si hay financiamiento) if total_financiamiento and ( not
# fecha_entrega or fecha_entrega.upper() == "ERROR" ):\n errores.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula,
# campo="fecha_entrega", valor_original=fecha_entrega, error="Fecha de entrega vacía o marcada como ERROR",
# tipo_error="CRITICO", puede_corregirse=True, sugerencia="Ingrese fecha de entrega (ej:\n 2025-01-15)", ) ) return
# erroresasync \ndef _analizar_archivo_clientes( contenido:\n bytes, nombre_archivo:\n str, db:\n Session, usuario_id:\n int)
# try:\n # Leer Excel df = pd.read_excel(io.BytesIO(contenido)) # Mapear columnas df = _mapear_columnas(df) # Validar
# columnas requeridas _validar_columnas_requeridas(df) # ============================================ # PROCESAR CADA
# concesionario, total_financiamiento, cuota_inicial, numero_amortizaciones, modalidad_pago, fecha_entrega, asesor, ) =
# e.tipo_error == "DATO_VACIO" ] ) # ============================================ # VALIDACIÓN 2:\n CAMPOS DE ADVERTENCIA
# VACÍOS # ============================================ # Móvil (ADVERTENCIA) if not movil or movil.upper() == "ERROR":\n
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="movil", valor_original=movil,
# error="Móvil vacío o marcado como ERROR", tipo_error="ADVERTENCIA", puede_corregirse=True, sugerencia="Ingrese número móvil
# (ej:\n 4241234567)", ) ) errores_advertencia += 1 # Email (ADVERTENCIA) if not email or email.upper() == "ERROR":\n
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="email", valor_original=email,
# error="Email vacío o marcado como ERROR", tipo_error="ADVERTENCIA", puede_corregirse=True, sugerencia="Ingrese email válido
# (ej:\n cliente@ejemplo.com)", ) ) errores_advertencia += 1 # Concesionario (DATO_VACIO) if not concesionario:\n
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="concesionario", valor_original="",
# error="Concesionario vacío", tipo_error="DATO_VACIO", puede_corregirse=True, sugerencia="Seleccione un concesionario de la
# ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="modelo_vehiculo", valor_original="", error="Modelo de vehículo
# 1 # Analista (DATO_VACIO) if not asesor:\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula,
# campo="asesor", valor_original="", error="Analista vacío", tipo_error="DATO_VACIO", puede_corregirse=True,
# modalidad_pago:\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="modalidad_pago",
# valor_original="", error="Modalidad de pago vacía", tipo_error="DATO_VACIO", puede_corregirse=True,
# ============================================ # VALIDACIÓN 3:\n FORMATO DE DATOS #
# ============================================ # Validar cédula con validador del sistema if cedula and cedula.upper() !=
# "ERROR":\n resultado_cedula = ValidadorCedula.validar_y_formatear_cedula( cedula, "VENEZUELA" ) if not
# resultado_cedula.get("valido"):\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula,
# campo="cedula", valor_original=cedula, error=resultado_cedula.get( "mensaje", "Formato inválido" ), tipo_error="CRITICO",
# móvil con validador del sistema if movil and movil.upper() != "ERROR":\n resultado_movil = (
# ValidadorTelefono.validar_y_formatear_telefono( movil, "VENEZUELA" ) ) if not resultado_movil.get("valido"):\n
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="movil", valor_original=movil,
# error=resultado_movil.get( "mensaje", "Formato inválido" ), tipo_error="ADVERTENCIA", puede_corregirse=True,
# if email and email.upper() != "ERROR":\n resultado_email = ValidadorEmail.validar_email(email) if not
# resultado_email.get("valido"):\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="email",
# valor_original=email, error=resultado_email.get( "mensaje", "Formato inválido" ), tipo_error="ADVERTENCIA",
# puede_corregirse=True, sugerencia="Formato:\n usuario@dominio.com", ) ) errores_advertencia += 1 # Validar fecha de entrega
# if fecha_entrega and fecha_entrega.upper() != "ERROR":\n resultado_fecha = ValidadorFecha.validar_y_formatear_fecha(
# fecha_entrega ) if not resultado_fecha.get("valido"):\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero,
# cedula=cedula, campo="fecha_entrega", valor_original=fecha_entrega, error=resultado_fecha.get( "mensaje", "Formato
# inválido" ), tipo_error="CRITICO", puede_corregirse=True, sugerencia="Formato:\n DD/MM/YYYY o YYYY-MM-DD", ) )
# "ERROR" ):\n resultado_monto = ValidadorMonto.validar_y_formatear_monto( total_financiamiento ) if not
# resultado_monto.get("valido"):\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula,
# campo="total_financiamiento", valor_original=total_financiamiento, error=resultado_monto.get( "mensaje", "Formato inválido"
# += 1 # ============================================ # VALIDACIÓN 4:\n EXISTENCIA EN BD #
# ============================================ # Verificar si concesionario existe if concesionario:\n concesionario_obj = (
# db.query(Concesionario) .filter( Concesionario.nombre.ilike(f"%{concesionario}%"), Concesionario.activo, ) .first() ) if
# not concesionario_obj:\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="concesionario",
# tipo_error="DATO_VACIO", puede_corregirse=True, sugerencia="Seleccione un concesionario existente o créelo primero en
# db.query(ModeloVehiculo) .filter( ModeloVehiculo.modelo.ilike(f"%{modelo_vehiculo}%"), ModeloVehiculo.activo, ) .first() )
# if not modelo_obj:\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="modelo_vehiculo",
# # Verificar si asesor existe if asesor:\n asesor_obj = ( db.query(Analista) .filter( Analista.nombre.ilike(f"%{asesor}%"),
# Analista.activo ) .first() ) if not asesor_obj:\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero,
# tipo_error="DATO_VACIO", puede_corregirse=True, sugerencia="Seleccione un asesor existente o créelo primero en
# "QUINCENAL", "MENSUAL", "BIMENSUAL", ] if modalidad_pago.upper() not in modalidades_validas:\n errores_registro.append(
# ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="modalidad_pago", valor_original=modalidad_pago, error=f'Modalidad
# "{modalidad_pago}" no es válida', tipo_error="CRITICO", puede_corregirse=True, sugerencia=f'Use:\n {",
# "cedula":\n cedula, "nombre":\n nombre, "apellido":\n apellido, "movil":\n movil, "email":\n email, "direccion":\n
# direccion, "modelo_vehiculo":\n modelo_vehiculo, "concesionario":\n concesionario, "total_financiamiento":\n
# total_financiamiento, "cuota_inicial":\n cuota_inicial, "numero_amortizaciones":\n numero_amortizaciones,
# "modalidad_pago":\n modalidad_pago or "MENSUAL", "fecha_entrega":\n fecha_entrega, "asesor":\n asesor, }, ) ) #
# ============================================ # RETORNAR RESULTADO PARA DASHBOARD #
# usuario_id=usuario_id, ) except Exception as e:\n raise HTTPException( status_code=500, detail="Error analizando archivo
# de clientes:\n {str(e)}", )# ============================================# FUNCIÓN:\n ANALIZAR ARCHIVO DE PAGOS#
# "CEDULA IDENTIDAD":\n "cedula", "CEDULA":\n "cedula", "FECHA PAGO":\n "fecha_pago", "FECHA":\n "fecha_pago", "MONTO
# PAGADO":\n "monto_pagado", "MONTO":\n "monto_pagado", "NUMERO CUOTA":\n "numero_cuota", "CUOTA":\n "numero_cuota",
# "DOCUMENTO PAGO":\n "documento_pago", "DOCUMENTO":\n "documento_pago", "REFERENCIA":\n "documento_pago", "METODO PAGO":\n
# "metodo_pago", "METODO":\n "metodo_pago", } df = df.rename(columns=mapeo_columnas) # Validar columnas requeridas
# columnas_requeridas = ["cedula", "fecha_pago", "monto_pagado"] columnas_faltantes = [ col for col in columnas_requeridas if
# col not in df.columns ] if columnas_faltantes:\n raise HTTPException( status_code=400, detail="❌ Faltan columnas
# fila_numero = index + 2 errores_registro = [] cedula = str(row.get("cedula", "")).strip() fecha_pago =
# str(row.get("fecha_pago", "")).strip() monto_pagado = str(row.get("monto_pagado", "")).strip() numero_cuota =
# str(row.get("numero_cuota", "")).strip() documento_pago = str(row.get("documento_pago", "")).strip() metodo_pago =
# str(row.get("metodo_pago", "")).strip() # ============================================ # VALIDACIÓN:\n ARTICULACIÓN CON
# CLIENTE # ============================================ # Buscar cliente por cédula cliente = None if cedula and
# cedula.upper() != "ERROR":\n cliente = ( db.query(Cliente).filter(Cliente.cedula == cedula).first() ) if not cliente:\n
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="cedula", valor_original=cedula,
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula or "VACÍO", campo="cedula",
# valor_original=cedula, error="Cédula vacía o marcada como ERROR", tipo_error="CRITICO", puede_corregirse=True,
# fecha_pago.upper() == "ERROR":\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula,
# campo="fecha_pago", valor_original=fecha_pago, error="Fecha de pago vacía o marcada como ERROR", tipo_error="CRITICO",
# resultado_fecha = ValidadorFecha.validar_y_formatear_fecha( fecha_pago ) if not resultado_fecha.get("valido"):\n
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="fecha_pago", valor_original=fecha_pago,
# error=resultado_fecha.get( "mensaje", "Formato inválido" ), tipo_error="CRITICO", puede_corregirse=True,
# monto_pagado.upper() == "ERROR":\n errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula,
# campo="monto_pagado", valor_original=monto_pagado, error="Monto pagado vacío o marcado como ERROR", tipo_error="CRITICO",
# resultado_monto = ValidadorMonto.validar_y_formatear_monto( monto_pagado ) if not resultado_monto.get("valido"):\n
# errores_registro.append( ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="monto_pagado",
# valor_original=monto_pagado, error=resultado_monto.get( "mensaje", "Formato inválido" ), tipo_error="CRITICO",
# (ADVERTENCIA si vacío) if not documento_pago or documento_pago.upper() == "ERROR":\n errores_registro.append(
# ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="documento_pago", valor_original=documento_pago, error="Documento
# de pago vacío", tipo_error="ADVERTENCIA", puede_corregirse=True, sugerencia="Ingrese número de referencia o documento", ) )
# errores_advertencia += 1 # Método de pago (DATO_VACIO si vacío) if not metodo_pago:\n errores_registro.append(
# ErrorCargaMasiva( fila=fila_numero, cedula=cedula, campo="metodo_pago", valor_original="", error="Método de pago vacío",
# tipo_error="DATO_VACIO", puede_corregirse=True, sugerencia="Seleccione:\n TRANSFERENCIA, EFECTIVO, CHEQUE, etc.", ) )
# "cedula":\n cedula, "fecha_pago":\n fecha_pago, "monto_pagado":\n monto_pagado, "numero_cuota":\n numero_cuota,
# "documento_pago":\n documento_pago, "metodo_pago":\n metodo_pago, "cliente_id":\n cliente.id if cliente else None,
# "cliente_nombre":\n ( cliente.nombre_completo if cliente else None ), }, ) ) return ResultadoCargaMasiva(
# usuario_id=usuario_id, ) except Exception as e:\n raise HTTPException( status_code=500, detail="Error analizando archivo
# ============================================\ndef _validar_correccion_cedula(valor:\n str) -> tuple[bool, str, str]:\n
# """Validar corrección de cédula""" resultado = ValidadorCedula.validar_y_formatear_cedula(valor, "VENEZUELA") if not
# resultado.get("valido"):\n return False, f"Cédula:\n {resultado.get('mensaje')}", "" return True, "",
# resultado.get("valor_formateado")\ndef _validar_correccion_movil(valor:\n str) -> tuple[bool, str, str]:\n """Validar
# corrección de móvil""" resultado = ValidadorTelefono.validar_y_formatear_telefono( valor, "VENEZUELA" ) if not
# resultado.get("valido"):\n return False, f"Móvil:\n {resultado.get('mensaje')}", "" return True, "",
# resultado.get("valor_formateado")\ndef _validar_correccion_email(valor:\n str) -> tuple[bool, str, str]:\n """Validar
# corrección de email""" resultado = ValidadorEmail.validar_email(valor) if not resultado.get("valido"):\n return False,
# f"Email:\n {resultado.get('mensaje')}", "" return True, "", resultado.get("valor_formateado")\ndef
# _validar_correccion_fecha(valor:\n str) -> tuple[bool, str, str]:\n """Validar corrección de fecha""" resultado =
# ValidadorFecha.validar_y_formatear_fecha(valor) if not resultado.get("valido"):\n return False, "Fecha:\n
# {resultado.get('mensaje')}", "" return True, "", resultado.get("valor_formateado")\ndef _validar_correccion_monto(valor:\n
# str) -> tuple[bool, str, str]:\n """Validar corrección de monto""" resultado =
# ValidadorMonto.validar_y_formatear_monto(valor) if not resultado.get("valido"):\n return False, "Monto:\n
# {resultado.get('mensaje')}", "" return True, "", resultado.get("valor_formateado")\ndef _validar_correccion_concesionario(
# valor:\n str, db:\n Session) -> tuple[bool, str, str, int]:\n """Validar corrección de concesionario""" concesionario = (
# db.query(Concesionario) .filter(Concesionario.nombre.ilike(f"%{valor}%"), Concesionario.activo) .first() ) if not
# concesionario:\n return False, f"Concesionario '{valor}' no existe en la BD", "", 0 return True, "", valor,
# concesionario.id\ndef _validar_correccion_modelo_vehiculo( valor:\n str, db:\n Session) -> tuple[bool, str, str, int]:\n
# """Validar corrección de modelo de vehículo""" modelo = ( db.query(ModeloVehiculo) .filter(
# ModeloVehiculo.modelo.ilike(f"%{valor}%"), ModeloVehiculo.activo ) .first() ) if not modelo:\n return False, f"Modelo
# '{valor}' no existe en la BD", "", 0 return True, "", valor, modelo.id\ndef _validar_correccion_asesor( valor:\n str, db:\n
# Session) -> tuple[bool, str, str, int]:\n """Validar corrección de asesor""" asesor = ( db.query(Analista)
# .filter(Analista.nombre.ilike(f"%{valor}%"), Analista.activo) .first() ) if not asesor:\n return False, f"Analista
# '{valor}' no existe en la BD", "", 0 return True, "", valor, asesor.id\ndef _validar_correccion_modalidad_pago(valor:\n
# str) -> tuple[bool, str, str]:\n """Validar corrección de modalidad de pago""" modalidades_validas = ["SEMANAL",
# "QUINCENAL", "MENSUAL", "BIMENSUAL"] if valor.upper() not in modalidades_validas:\n return ( False, f"Modalidad '{valor}'
# no es válida. Use:\n " f"{', '.join(modalidades_validas)}", "", ) return True, "", valor.upper()\ndef
# _procesar_correccion_campo( campo:\n str, valor:\n str, db:\n Session) -> tuple[bool, str, dict]:\n """Procesar corrección
# "modelo_vehiculo":\n valido, error, valor_formateado, modelo_id = ( _validar_correccion_modelo_vehiculo(valor, db) ) if
# corregir_registro_en_linea( correccion:\n CorreccionRegistro, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ ✏️ PASO 2:\n Corregir un registro con errores en línea (VERSIÓN REFACTORIZADA)
# Proceso:\n 1. Recibir correcciones del usuario 2. Validar con validadores del sistema 3. Si pasa validación, marcar como
# retornar sin guardar if errores_validacion:\n return { "success":\n False, "errores":\n errores_validacion,
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error corrigiendo registro:\n {str(e)}", )#
# ============================================# ENDPOINT:\n GUARDAR REGISTROS CORREGIDOS#
# except Exception as e:\n errores_guardado.append( {"cedula":\n registro.get("cedula"), "error":\n str(e)} ) db.commit() #
# Registrar en auditoría auditoria = Auditoria.registrar( usuario_id=current_user.id, accion=TipoAccion.CREAR,
# ============================================# FUNCIÓN:\n GUARDAR CLIENTE DESDE CARGA MASIVA#
# Concesionario.activo, ) .first() ) return concesionario_obj.id if concesionario_obj else None\ndef
# ForeignKeys "concesionario_id":\n concesionario_id, "modelo_vehiculo_id":\n modelo_vehiculo_id, "asesor_id":\n asesor_id, #
# """Guardar nuevo cliente o actualizar existente""" cliente_existente = ( db.query(Cliente).filter(Cliente.cedula ==
# if key not in ["cedula", "fecha_registro"]:\n setattr(cliente_existente, key, value) cliente_existente.fecha_actualizacion
# cliente nuevo_cliente = Cliente(**cliente_data) db.add(nuevo_cliente) db.flush() logger.info( "Cliente creado:\n
# """Registrar operación en auditoría""" auditoria = Auditoria.registrar( usuario_id=usuario_id, accion=TipoAccion.ACTUALIZAR
# if es_actualizacion else TipoAccion.CREAR, tabla="Cliente", registro_id=cliente.id, descripcion=f"Cliente {'actualizado' if
# """ Guardar cliente usando MISMO proceso que crear_cliente (VERSIÓN REFACTORIZADA) """ try:\n # 1. Buscar ForeignKeys
# modelo_vehiculo_id, asesor_id, usuario_id ) # 3. Verificar si existe y guardar/actualizar cliente_existente = (
# {str(e)}" )# ============================================# FUNCIÓN:\n GUARDAR PAGO DESDE CARGA MASIVA#
# usuario_id:\n int):\n """ Guardar pago articulado con cliente por cédula """ try:\n #
# ============================================ # ARTICULACIÓN:\n Buscar cliente por cédula #
# ============================================ cliente = ( db.query(Cliente).filter(Cliente.cedula ==
# ============================================ # CREAR PAGO # ============================================ pago_data = {
# Registrar en auditoría auditoria = Auditoria.registrar( usuario_id=usuario_id, accion=TipoAccion.CREAR, tabla="Pago",
# DESCARGAR TEMPLATE EXCEL# ============================================@router.get("/template-excel/{tipo}")async \ndef
# descargar_template_excel( tipo:\n str, db:\n Session = Depends(get_db), current_user:\n User =
# columnas requeridas df = pd.DataFrame( columns=[ "CEDULA IDENTIDAD", "NOMBRE", "APELLIDO", "MOVIL", "CORREO ELECTRONICO",
# "DIRECCION", "MODELO VEHICULO", "CONCESIONARIO", "TOTAL FINANCIAMIENTO", "CUOTA INICIAL", "NUMERO AMORTIZACIONES",
# "MODALIDAD PAGO", "FECHA ENTREGA", "USER", ] ) # Agregar fila de ejemplo df.loc[0] = [ "V12345678", "Juan", "Pérez",
# "4241234567", "juan.perez@ejemplo.com", "Av. Principal, Caracas", "Toyota Corolla", "AutoCenter Caracas", "50000.00",
# "10000.00", "24", "MENSUAL", "2025-01-15", "Roberto Martínez", ] nombre_archivo = "template_clientes.xlsx" elif tipo ==
# "NUMERO CUOTA", "DOCUMENTO PAGO", "METODO PAGO", ] ) # Agregar fila de ejemplo df.loc[0] = [ "V12345678", "2025-01-15",
# return StreamingResponse( output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={
# status_code=500, detail=f"Error generando template:\n {str(e)}", )# ============================================#
# ENDPOINT:\n OBTENER LISTAS DE CONFIGURACIÓN#
# ============================================@router.get("/opciones-configuracion")async \ndef
# obtener_opciones_configuracion( db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """
# db.query(ModeloVehiculo).filter(ModeloVehiculo.activo).all() # Modalidades de pago configurables modalidades_pago = [
# {"value":\n "SEMANAL", "label":\n "Semanal"}, {"value":\n "QUINCENAL", "label":\n "Quincenal"}, {"value":\n "MENSUAL",
# modalidades_pago, } except Exception as e:\n raise HTTPException( status_code=500, detail=f"Error obteniendo opciones:\n
# {str(e)}", )# ============================================# ENDPOINT:\n DASHBOARD DE CARGA MASIVA#
# ============================================@router.get("/dashboard")async \ndef dashboard_carga_masiva( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Dashboard de carga masiva Muestra:\n -
# usuario auditorias = ( db.query(Auditoria) .filter( Auditoria.usuario_id == current_user.id, Auditoria.tabla ==
# "CargaMasiva", ) .order_by(Auditoria.fecha.desc()) .limit(10) .all() ) return { "titulo":\n "📊 Dashboard de Carga Masiva",
# "usuario":\n f"{current_user.nombre} {current_user.apellido}".strip(), "historial_cargas":\n [ { "fecha":\n a.fecha,
# "instrucciones":\n { "paso_1":\n "📤 Subir archivo Excel con formato establecido", "paso_2":\n "🔍 Revisar dashboard de
# raise HTTPException( status_code=500, detail=f"Error obteniendo dashboard:\n {str(e)}", )
