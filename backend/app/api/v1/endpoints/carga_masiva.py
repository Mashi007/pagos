# \nimport Decimal\nfrom typing \nimport Any, Dict, List, Optional\nimport pandas as pd\nfrom fastapi \nimport APIRouter,
# Depends, File, Form, HTTPException, UploadFile\nfrom fastapi.responses \nimport StreamingResponse\nfrom pydantic \nimport
# BaseModel\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom
# app.models.analista \nimport Analista\nfrom app.models.auditoria \nimport Auditoria, TipoAccion\nfrom app.models.cliente
# \nimport Cliente\nfrom app.models.concesionario \nimport Concesionario\nfrom app.models.modelo_vehiculo \nimport
# ModeloVehiculo\nfrom app.models.pago \nimport Pago\nfrom app.models.user \nimport User\nfrom
# app.services.validators_service \nimport 
# ValidadorTelefono,)logger = logging.getLogger(__name__)router = APIRouter()# ============================================#
# SCHEMAS PARA CARGA MASIVA# ============================================\nclass ErrorCargaMasiva(BaseModel):\n """Error
# encontrado en carga masiva""" fila:\n int cedula:\n str campo:\n str valor_original:\n str error:\n str tipo_error:\n str #
# CRITICO, ADVERTENCIA, DATO_VACIO puede_corregirse:\n bool sugerencia:\n Optional[str] = None\nclass
# RegistroCargaMasiva(BaseModel):\n """Registro procesado en carga masiva""" fila:\n int cedula:\n str nombre_completo:\n str
# cedula:\n str correcciones:\n Dict[str, str]# ============================================# ENDPOINT:\n SUBIR ARCHIVO
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📤 PASO 1:\n Subir archivo Excel
# ADVERTENCIA, DATO_VACÍO) 4. NO guardar nada aún 5. Retornar dashboard con errores para corrección """ try:\n # Validar tipo
# de archivo if not archivo.filename.endswith((".xlsx", ".xls")):\n raise HTTPException
# {str(e)}", )# ============================================# FUNCIÓN:\n ANALIZAR ARCHIVO DE CLIENTES#
# ============================================\ndef _mapear_columnas(df:\n pd.DataFrame) -> pd.DataFrame:\n """Mapear
# columnas del Excel al sistema""" mapeo_columnas = 
# "fecha_entrega", "ENTREGA":\n "fecha_entrega", "USER":\n "asesor", "USER ASIGNADO":\n "asesor", } return
# df.rename(columns=mapeo_columnas)\ndef _validar_columnas_requeridas(df:\n pd.DataFrame) -> None:\n """Validar que existan
# las columnas requeridas""" columnas_requeridas = ["cedula", "nombre"] columnas_faltantes = [ col for col in
# columnas_requeridas if col not in df.columns ] if columnas_faltantes:\n raise HTTPException
# "")).strip() nombre = str(row.get("nombre", "")).strip() apellido = ( str(row.get("apellido", "")).strip() if "apellido" in
# row else "" ) movil = str(row.get("movil", "")).strip() email = str(row.get("email", "")).strip() direccion =
# str(row.get("direccion", "")).strip() modelo_vehiculo = str(row.get("modelo_vehiculo", "")).strip() concesionario =
# str(row.get("concesionario", "")).strip() total_financiamiento = str(row.get("total_financiamiento", "")).strip()
# cuota_inicial = str(row.get("cuota_inicial", "")).strip() numero_amortizaciones = str
# "")).strip() modalidad_pago = str(row.get("modalidad_pago", "")).strip() fecha_entrega = str
# "")).strip() asesor = str(row.get("asesor", "")).strip() # Si no hay apellido separado, intentar split del nombre if not
# apellido and nombre:\n partes_nombre = nombre.split(" ", 1) if len(partes_nombre) > 1:\n nombre = partes_nombre[0] apellido
# = partes_nombre[1] return 
# total_financiamiento, cuota_inicial, numero_amortizaciones, modalidad_pago, fecha_entrega, asesor, )\ndef
# errores""" errores = [] # Cédula (CRÍTICO) if not cedula or cedula.upper() == "ERROR":\n errores.append
# ERROR", tipo_error="CRITICO", puede_corregirse=True, sugerencia="Ingrese cédula válida (ej:\n V12345678)", ) ) # Nombre
# (CRÍTICO) if not nombre or nombre.upper() == "ERROR":\n errores.append
# puede_corregirse=True, sugerencia="Ingrese nombre completo del cliente", ) ) # Total Financiamiento 
# financiamiento) if not total_financiamiento or total_financiamiento.upper() == "ERROR":\n errores.append
# financiamiento (ej:\n 50000)", ) ) # Número de Amortizaciones (CRÍTICO si hay financiamiento) if total_financiamiento and 
# not numero_amortizaciones or numero_amortizaciones.upper() == "ERROR" ):\n errores.append
# cuotas (ej:\n 12, 24, 36)", ) ) # Fecha Entrega (CRÍTICO si hay financiamiento) if total_financiamiento and 
# fecha_entrega or fecha_entrega.upper() == "ERROR" ):\n errores.append
# tipo_error="CRITICO", puede_corregirse=True, sugerencia="Ingrese fecha de entrega (ej:\n 2025-01-15)", ) ) return
# erroresasync \ndef _analizar_archivo_clientes( contenido:\n bytes, nombre_archivo:\n str, db:\n Session, usuario_id:\n int)
# try:\n # Leer Excel df = pd.read_excel(io.BytesIO(contenido)) # Mapear columnas df = _mapear_columnas(df) # Validar
# columnas requeridas _validar_columnas_requeridas(df) # ============================================ # PROCESAR CADA
# concesionario, total_financiamiento, cuota_inicial, numero_amortizaciones, modalidad_pago, fecha_entrega, asesor, ) =
# e.tipo_error == "DATO_VACIO" ] ) # ============================================ # VALIDACIÓN 2:\n CAMPOS DE ADVERTENCIA
# VACÍOS # ============================================ # Móvil (ADVERTENCIA) if not movil or movil.upper() == "ERROR":\n
# errores_registro.append
# (ej:\n 4241234567)", ) ) errores_advertencia += 1 # Email (ADVERTENCIA) if not email or email.upper() == "ERROR":\n
# errores_registro.append
# (ej:\n cliente@ejemplo.com)", ) ) errores_advertencia += 1 # Concesionario (DATO_VACIO) if not concesionario:\n
# errores_registro.append
# 1 # Analista (DATO_VACIO) if not asesor:\n errores_registro.append
# ============================================ # Validar cédula con validador del sistema if cedula and cedula.upper() !=
# "ERROR":\n resultado_cedula = ValidadorCedula.validar_y_formatear_cedula( cedula, "VENEZUELA" ) if not
# resultado_cedula.get("valido"):\n errores_registro.append
# campo="cedula", valor_original=cedula, error=resultado_cedula.get( "mensaje", "Formato inválido" ), tipo_error="CRITICO",
# móvil con validador del sistema if movil and movil.upper() != "ERROR":\n resultado_movil = 
# ValidadorTelefono.validar_y_formatear_telefono( movil, "VENEZUELA" ) ) if not resultado_movil.get("valido"):\n
# errores_registro.append
# error=resultado_movil.get( "mensaje", "Formato inválido" ), tipo_error="ADVERTENCIA", puede_corregirse=True,
# if email and email.upper() != "ERROR":\n resultado_email = ValidadorEmail.validar_email(email) if not
# resultado_email.get("valido"):\n errores_registro.append
# valor_original=email, error=resultado_email.get( "mensaje", "Formato inválido" ), tipo_error="ADVERTENCIA",
# puede_corregirse=True, sugerencia="Formato:\n usuario@dominio.com", ) ) errores_advertencia += 1 # Validar fecha de entrega
# if fecha_entrega and fecha_entrega.upper() != "ERROR":\n resultado_fecha = ValidadorFecha.validar_y_formatear_fecha
# fecha_entrega ) if not resultado_fecha.get("valido"):\n errores_registro.append
# inválido" ), tipo_error="CRITICO", puede_corregirse=True, sugerencia="Formato:\n DD/MM/YYYY o YYYY-MM-DD", ) )
# "ERROR" ):\n resultado_monto = ValidadorMonto.validar_y_formatear_monto( total_financiamiento ) if not
# resultado_monto.get("valido"):\n errores_registro.append
# db.query(Concesionario) .filter( Concesionario.nombre.ilike(f"%{concesionario}%"), Concesionario.activo, ) .first() ) if
# not concesionario_obj:\n errores_registro.append
# db.query(ModeloVehiculo) .filter( ModeloVehiculo.modelo.ilike(f"%{modelo_vehiculo}%"), ModeloVehiculo.activo, ) .first() )
# if not modelo_obj:\n errores_registro.append
# # Verificar si asesor existe if asesor:\n asesor_obj = ( db.query(Analista) .filter( Analista.nombre.ilike(f"%{asesor}%"),
# Analista.activo ) .first() ) if not asesor_obj:\n errores_registro.append
# "QUINCENAL", "MENSUAL", "BIMENSUAL", ] if modalidad_pago.upper() not in modalidades_validas:\n errores_registro.append
# "modalidad_pago":\n modalidad_pago or "MENSUAL", "fecha_entrega":\n fecha_entrega, "asesor":\n asesor, }, ) ) #
# ============================================ # RETORNAR RESULTADO PARA DASHBOARD #
# usuario_id=usuario_id, ) except Exception as e:\n raise HTTPException
# de clientes:\n {str(e)}", )# ============================================# FUNCIÓN:\n ANALIZAR ARCHIVO DE PAGOS#
# "CEDULA IDENTIDAD":\n "cedula", "CEDULA":\n "cedula", "FECHA PAGO":\n "fecha_pago", "FECHA":\n "fecha_pago", "MONTO
# PAGADO":\n "monto_pagado", "MONTO":\n "monto_pagado", "NUMERO CUOTA":\n "numero_cuota", "CUOTA":\n "numero_cuota",
# "DOCUMENTO PAGO":\n "documento_pago", "DOCUMENTO":\n "documento_pago", "REFERENCIA":\n "documento_pago", "METODO PAGO":\n
# "metodo_pago", "METODO":\n "metodo_pago", } df = df.rename(columns=mapeo_columnas) # Validar columnas requeridas
# columnas_requeridas = ["cedula", "fecha_pago", "monto_pagado"] columnas_faltantes = [ col for col in columnas_requeridas if
# col not in df.columns ] if columnas_faltantes:\n raise HTTPException
# fila_numero = index + 2 errores_registro = [] cedula = str(row.get("cedula", "")).strip() fecha_pago =
# str(row.get("fecha_pago", "")).strip() monto_pagado = str(row.get("monto_pagado", "")).strip() numero_cuota =
# str(row.get("numero_cuota", "")).strip() documento_pago = str(row.get("documento_pago", "")).strip() metodo_pago =
# str(row.get("metodo_pago", "")).strip() # ============================================ # VALIDACIÓN:\n ARTICULACIÓN CON
# CLIENTE # ============================================ # Buscar cliente por cédula cliente = None if cedula and
# cedula.upper() != "ERROR":\n cliente = ( db.query(Cliente).filter(Cliente.cedula == cedula).first() ) if not cliente:\n
# errores_registro.append
# fecha_pago.upper() == "ERROR":\n errores_registro.append
# resultado_fecha = ValidadorFecha.validar_y_formatear_fecha( fecha_pago ) if not resultado_fecha.get("valido"):\n
# errores_registro.append
# error=resultado_fecha.get( "mensaje", "Formato inválido" ), tipo_error="CRITICO", puede_corregirse=True,
# monto_pagado.upper() == "ERROR":\n errores_registro.append
# resultado_monto = ValidadorMonto.validar_y_formatear_monto( monto_pagado ) if not resultado_monto.get("valido"):\n
# errores_registro.append
# valor_original=monto_pagado, error=resultado_monto.get( "mensaje", "Formato inválido" ), tipo_error="CRITICO",
# (ADVERTENCIA si vacío) if not documento_pago or documento_pago.upper() == "ERROR":\n errores_registro.append
# de pago vacío", tipo_error="ADVERTENCIA", puede_corregirse=True, sugerencia="Ingrese número de referencia o documento", ) )
# errores_advertencia += 1 # Método de pago (DATO_VACIO si vacío) if not metodo_pago:\n errores_registro.append
# tipo_error="DATO_VACIO", puede_corregirse=True, sugerencia="Seleccione:\n TRANSFERENCIA, EFECTIVO, CHEQUE, etc.", ) )
# "cedula":\n cedula, "fecha_pago":\n fecha_pago, "monto_pagado":\n monto_pagado, "numero_cuota":\n numero_cuota,
# "documento_pago":\n documento_pago, "metodo_pago":\n metodo_pago, "cliente_id":\n cliente.id if cliente else None,
# "cliente_nombre":\n ( cliente.nombre_completo if cliente else None ), }, ) ) return ResultadoCargaMasiva
# usuario_id=usuario_id, ) except Exception as e:\n raise HTTPException
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
# {resultado.get('mensaje')}", "" return True, "", resultado.get("valor_formateado")\ndef _validar_correccion_monto
# str) -> tuple[bool, str, str]:\n """Validar corrección de monto""" resultado =
# ValidadorMonto.validar_y_formatear_monto(valor) if not resultado.get("valido"):\n return False, "Monto:\n
# {resultado.get('mensaje')}", "" return True, "", resultado.get("valor_formateado")\ndef _validar_correccion_concesionario
# valor:\n str, db:\n Session) -> tuple[bool, str, str, int]:\n """Validar corrección de concesionario""" concesionario = 
# db.query(Concesionario) .filter(Concesionario.nombre.ilike(f"%{valor}%"), Concesionario.activo) .first() ) if not
# concesionario:\n return False, f"Concesionario '{valor}' no existe en la BD", "", 0 return True, "", valor,
# concesionario.id\ndef _validar_correccion_modelo_vehiculo( valor:\n str, db:\n Session) -> tuple[bool, str, str, int]:\n
# """Validar corrección de modelo de vehículo""" modelo = ( db.query(ModeloVehiculo) .filter
# ModeloVehiculo.modelo.ilike(f"%{valor}%"), ModeloVehiculo.activo ) .first() ) if not modelo:\n return False, f"Modelo
# '{valor}' no existe en la BD", "", 0 return True, "", valor, modelo.id\ndef _validar_correccion_asesor
# Session) -> tuple[bool, str, str, int]:\n """Validar corrección de asesor""" asesor = ( db.query(Analista)
# .filter(Analista.nombre.ilike(f"%{valor}%"), Analista.activo) .first() ) if not asesor:\n return False, f"Analista
# '{valor}' no existe en la BD", "", 0 return True, "", valor, asesor.id\ndef _validar_correccion_modalidad_pago
# str) -> tuple[bool, str, str]:\n """Validar corrección de modalidad de pago""" modalidades_validas = ["SEMANAL",
# "QUINCENAL", "MENSUAL", "BIMENSUAL"] if valor.upper() not in modalidades_validas:\n return 
# no es válida. Use:\n " f"{', '.join(modalidades_validas)}", "", ) return True, "", valor.upper()\ndef
# _procesar_correccion_campo( campo:\n str, valor:\n str, db:\n Session) -> tuple[bool, str, dict]:\n """Procesar corrección
# "modelo_vehiculo":\n valido, error, valor_formateado, modelo_id = ( _validar_correccion_modelo_vehiculo(valor, db) ) if
# corregir_registro_en_linea( correccion:\n CorreccionRegistro, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ ✏️ PASO 2:\n Corregir un registro con errores en línea (VERSIÓN REFACTORIZADA)
# Proceso:\n 1. Recibir correcciones del usuario 2. Validar con validadores del sistema 3. Si pasa validación, marcar como
# retornar sin guardar if errores_validacion:\n return 
# Exception as e:\n raise HTTPException( status_code=500, detail=f"Error corrigiendo registro:\n {str(e)}", )#
# ============================================# ENDPOINT:\n GUARDAR REGISTROS CORREGIDOS#
# except Exception as e:\n errores_guardado.append( {"cedula":\n registro.get("cedula"), "error":\n str(e)} ) db.commit() #
# Registrar en auditoría auditoria = Auditoria.registrar
# Concesionario.activo, ) .first() ) return concesionario_obj.id if concesionario_obj else None\ndef
# ForeignKeys "concesionario_id":\n concesionario_id, "modelo_vehiculo_id":\n modelo_vehiculo_id, "asesor_id":\n asesor_id, #
# """Guardar nuevo cliente o actualizar existente""" cliente_existente = ( db.query(Cliente).filter
# if key not in ["cedula", "fecha_registro"]:\n setattr(cliente_existente, key, value) cliente_existente.fecha_actualizacion
# cliente nuevo_cliente = Cliente(**cliente_data) db.add(nuevo_cliente) db.flush() logger.info
# """ Guardar cliente usando MISMO proceso que crear_cliente (VERSIÓN REFACTORIZADA) """ try:\n # 1. Buscar ForeignKeys
# modelo_vehiculo_id, asesor_id, usuario_id ) # 3. Verificar si existe y guardar/actualizar cliente_existente = 
# {str(e)}" )# ============================================# FUNCIÓN:\n GUARDAR PAGO DESDE CARGA MASIVA#
# usuario_id:\n int):\n """ Guardar pago articulado con cliente por cédula """ try:\n #
# ============================================ # ARTICULACIÓN:\n Buscar cliente por cédula #
# ============================================ cliente = ( db.query(Cliente).filter
# DESCARGAR TEMPLATE EXCEL# ============================================@router.get("/template-excel/{tipo}")async \ndef
# descargar_template_excel( tipo:\n str, db:\n Session = Depends(get_db), current_user:\n User =
# columnas requeridas df = pd.DataFrame
# "MODALIDAD PAGO", "FECHA ENTREGA", "USER", ] ) # Agregar fila de ejemplo df.loc[0] = [ "V12345678", "Juan", "Pérez",
# "4241234567", "juan.perez@ejemplo.com", "Av. Principal, Caracas", "Toyota Corolla", "AutoCenter Caracas", "50000.00",
# "10000.00", "24", "MENSUAL", "2025-01-15", "Roberto Martínez", ] nombre_archivo = "template_clientes.xlsx" elif tipo ==
# "NUMERO CUOTA", "DOCUMENTO PAGO", "METODO PAGO", ] ) # Agregar fila de ejemplo df.loc[0] = [ "V12345678", "2025-01-15",
# return StreamingResponse
# status_code=500, detail=f"Error generando template:\n {str(e)}", )# ============================================#
# ENDPOINT:\n OBTENER LISTAS DE CONFIGURACIÓN#
# ============================================@router.get("/opciones-configuracion")async \ndef
# obtener_opciones_configuracion( db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """
# db.query(ModeloVehiculo).filter(ModeloVehiculo.activo).all() # Modalidades de pago configurables modalidades_pago = [
# {"value":\n "SEMANAL", "label":\n "Semanal"}, {"value":\n "QUINCENAL", "label":\n "Quincenal"}, 
# modalidades_pago, } except Exception as e:\n raise HTTPException
# {str(e)}", )# ============================================# ENDPOINT:\n DASHBOARD DE CARGA MASIVA#
# ============================================@router.get("/dashboard")async \ndef dashboard_carga_masiva
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Dashboard de carga masiva Muestra:\n -
# usuario auditorias = ( db.query(Auditoria) .filter
# "CargaMasiva", ) .order_by(Auditoria.fecha.desc()) .limit(10) .all() ) return 
# "usuario":\n f"{current_user.nombre} {current_user.apellido}".strip(), "historial_cargas":\n [ 
# raise HTTPException( status_code=500, detail=f"Error obteniendo dashboard:\n {str(e)}", )

"""