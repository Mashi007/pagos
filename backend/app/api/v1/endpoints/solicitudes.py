# backend/app/api/v1/endpoints/solicitudes.py"""Sistema de Solicitudes de AprobaciónManeja solicitudes para acciones que
# requieren autorización"""\nimport logging\nimport uuid\nfrom datetime \nimport date, datetime, timedelta\nfrom pathlib
# \nimport Path\nfrom typing \nimport Any, Dict, List, Optional\nfrom fastapi \nimport APIRouter, Depends, File,
# HTTPException, Query, UploadFile\nfrom pydantic \nimport BaseModel, Field\nfrom sqlalchemy \nimport func\nfrom
# sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom app.models.aprobacion \nimport
# Aprobacion\nfrom app.models.cliente \nimport Cliente\nfrom app.models.notificacion \nimport Notificacion\nfrom
# app.models.pago \nimport Pago\nfrom app.models.prestamo \nimport Prestamo\nfrom app.models.user \nimport User\nfrom
# app.services.email_service \nimport EmailServicelogger = logging.getLogger(__name__)router = APIRouter()#
# ============================================# SCHEMAS PARA SOLICITUDES# ============================================\nclass
# SolicitudAprobacionCompleta(BaseModel):\n """Schema completo para crear solicitud de aprobación""" tipo_solicitud:\n str =
# Field( ..., description="MODIFICAR_PAGO, ANULAR_PAGO, EDITAR_CLIENTE, MODI \ FICAR_AMORTIZACION", ) entidad_tipo:\n str =
# Field(..., description="cliente, pago, prestamo") entidad_id:\n int = Field(..., description="ID de la entidad a
# modificar") justificacion:\n str = Field( ..., min_length=10, max_length=1000, description="Justificación detallada", )
# datos_solicitados:\n Dict[str, Any] = Field( ..., description="Datos que se desean cambiar" ) prioridad:\n str = Field(
# default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE" ) fecha_limite:\n Optional[date] = Field( None,
# description="Fecha límite para respuesta" ) \nclass Config:\n json_schema_extra = { "example":\n { "tipo_solicitud":\n
# "MODIFICAR_PAGO", "entidad_tipo":\n "pago", "entidad_id":\n 123, "justificacion":\n ( "El cliente pagó con transferencia
# pero se registró como " "efectivo por error. Necesito corregir el método de pago " "para cuadrar la conciliación bancaria."
# ), "datos_solicitados":\n { "metodo_pago":\n "TRANSFERENCIA", "numero_operacion":\n "TRF-789456123", "banco":\n "Banco
# Popular", }, "prioridad":\n "ALTA", "fecha_limite":\n "2025-10-15", } }\nclass FormularioModificarPago(BaseModel):\n
# """Formulario específico para modificar pago""" pago_id:\n int = Field(..., description="ID del pago a modificar")
# motivo_modificacion:\n str = Field( ..., description="ERROR_REGISTRO, CAMBIO_CLIENTE, AJUSTE_MONTO, OTRO" )
# justificacion:\n str = Field( ..., min_length=20, description="Explicación detallada del motivo" ) # Campos que se pueden
# modificar nuevo_monto:\n Optional[float] = Field( None, gt=0, description="Nuevo monto del pago" ) nuevo_metodo_pago:\n
# Optional[str] = Field( None, description="EFECTIVO, TRANSFERENCIA, TARJETA, CHEQUE" ) nueva_fecha_pago:\n Optional[date] =
# Field( None, description="Nueva fecha de pago" ) nuevo_numero_operacion:\n Optional[str] = Field( None, description="Nuevo
# número de operación" ) nuevo_banco:\n Optional[str] = Field(None, description="Nuevo banco") nuevas_observaciones:\n
# Optional[str] = Field( None, description="Nuevas observaciones" ) prioridad:\n str = Field( default="NORMAL",
# description="BAJA, NORMAL, ALTA, URGENTE" )\nclass FormularioAnularPago(BaseModel):\n """Formulario específico para anular
# pago""" pago_id:\n int = Field(..., description="ID del pago a anular") motivo_anulacion:\n str = Field( ...,
# description="PAGO_DUPLICADO, ERROR_CLIENTE, DEVOLUCION, FRAUDE, OTRO", ) justificacion:\n str = Field( ..., min_length=20,
# description="Explicación detallada del motivo" ) revertir_amortizacion:\n bool = Field( True, description="Si revertir
# cambios en tabla de amortización" ) notificar_cliente:\n bool = Field( True, description="Si notificar al cliente sobre la
# anulación" ) prioridad:\n str = Field( default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE" )\nclass
# FormularioEditarCliente(BaseModel):\n """Formulario específico para editar cliente""" cliente_id:\n int = Field(...,
# description="ID del cliente a editar") motivo_edicion:\n str = Field( ..., description="CORRECCION_DATOS, CAMBIO_VEHICULO,
# ACTUALIZACION_CONTACTO, OTRO", ) justificacion:\n str = Field( ..., min_length=20, description="Explicación detallada del
# motivo" ) # Campos que se pueden modificar nuevos_datos_personales:\n Optional[Dict[str, Any]] = Field( None,
# description="Datos personales a cambiar" ) nuevos_datos_vehiculo:\n Optional[Dict[str, Any]] = Field( None,
# description="Datos del vehículo a cambiar" ) nuevos_datos_contacto:\n Optional[Dict[str, Any]] = Field( None,
# description="Datos de contacto a cambiar" ) prioridad:\n str = Field( default="NORMAL", description="BAJA, NORMAL, ALTA,
# URGENTE" )\nclass FormularioModificarAmortizacion(BaseModel):\n """Formulario específico para modificar amortización"""
# prestamo_id:\n int = Field(..., description="ID del préstamo") motivo_modificacion:\n str = Field( ...,
# description="CAMBIO_TASA, EXTENSION_PLAZO, REFINANCIAMIENTO, OTRO" ) justificacion:\n str = Field( ..., min_length=20,
# description="Explicación detallada del motivo" ) # Parámetros a modificar nueva_tasa_interes:\n Optional[float] = Field(
# None, ge=0, le=100, description="Nueva tasa de interés anual" ) nuevo_numero_cuotas:\n Optional[int] = Field( None, ge=1,
# le=360, description="Nuevo número de cuotas" ) nueva_modalidad_pago:\n Optional[str] = Field( None, description="SEMANAL,
# QUINCENAL, MENSUAL, BIMENSUAL" ) nueva_fecha_inicio:\n Optional[date] = Field( None, description="Nueva fecha de inicio" )
# prioridad:\n str = Field( default="ALTA", description="BAJA, NORMAL, ALTA, URGENTE" )\nclass
# SolicitudResponse(BaseModel):\n """Schema de respuesta para solicitud""" id:\n int tipo_solicitud:\n str entidad_tipo:\n
# str entidad_id:\n int estado:\n str justificacion:\n str datos_solicitados:\n Dict[str, Any] solicitante:\n str
# fecha_solicitud:\n datetime fecha_revision:\n Optional[datetime] = None revisor:\n Optional[str] = None
# comentarios_revisor:\n Optional[str] = None \nclass Config:\n from_attributes = True#
# ============================================# FUNCIONES AUXILIARES PARA ARCHIVOS#
# ============================================UPLOAD_DIR = Path("uploads/solicitudes")UPLOAD_DIR.mkdir(parents=True,
# exist_ok=True)ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".txt"}MAX_FILE_SIZE = 10 * 1024 *
# 1024 # 10MBasync \ndef guardar_archivo_evidencia( archivo:\n UploadFile,) -> tuple[str, str, int]:\n """Guardar archivo de
# evidencia y retornar (path, tipo, tamaño)""" if not archivo.filename:\n raise HTTPException( status_code=400,
# detail="Nombre de archivo requerido" ) # Verificar extensión extension = Path(archivo.filename).suffix.lower() if extension
# not in ALLOWED_EXTENSIONS:\n raise HTTPException( status_code=400, detail=f"Tipo de archivo no permitido. Permitidos:\n {',
# '.join(ALLOWED_EXTENSIONS)}", ) # Leer contenido y verificar tamaño contenido = await archivo.read() if len(contenido) >
# MAX_FILE_SIZE:\n raise HTTPException( status_code=400, detail="Archivo demasiado grande (máximo 10MB)" ) # Generar nombre
# único nombre_unico = f"{uuid.uuid4()}{extension}" ruta_archivo = UPLOAD_DIR / nombre_unico # Guardar archivo with
# open(ruta_archivo, "wb") as f:\n f.write(contenido) return str(ruta_archivo), extension[1:\n].upper(), len(contenido)#
# ============================================# SOLICITUDES DE COBRANZAS CON FORMULARIOS COMPLETOS#
# ============================================\ndef _validar_solicitud_modificacion_pago( formulario:\n
# FormularioModificarPago, current_user:\n User, db:\n Session) -> tuple[Pago, Optional[Aprobacion]]:\n """Validar solicitud
# de modificación de pago""" # Verificar permisos if not current_user.is_admin:\n raise HTTPException(status_code=403,
# detail="Usuario no autorizado") # Verificar que el pago existe pago = db.query(Pago).filter(Pago.id ==
# formulario.pago_id).first() if not pago:\n raise HTTPException(status_code=404, detail="Pago no encontrado") # Verificar
# que no hay solicitud pendiente para este pago solicitud_existente = ( db.query(Aprobacion) .filter( Aprobacion.entidad ==
# "pago", Aprobacion.entidad_id == formulario.pago_id, Aprobacion.estado == "PENDIENTE", ) .first() ) if
# solicitud_existente:\n raise HTTPException( status_code=400, detail=f"Ya existe una solicitud pendiente para este pago
# (ID:\n {solicitud_existente.id})", ) return pago, solicitud_existenteasync \ndef _procesar_archivo_evidencia(
# archivo_evidencia:\n Optional[UploadFile],) -> tuple[Optional[str], Optional[str], Optional[int]]:\n """Procesar archivo de
# evidencia""" archivo_path = None tipo_archivo = None tamaño_archivo = None if archivo_evidencia and
# archivo_evidencia.filename:\n archivo_path, tipo_archivo, tamaño_archivo = ( await
# guardar_archivo_evidencia(archivo_evidencia) ) return archivo_path, tipo_archivo, tamaño_archivo\ndef
# _preparar_datos_solicitados( formulario:\n FormularioModificarPago,) -> Dict[str, Any]:\n """Preparar datos solicitados"""
# datos_solicitados = {} if formulario.nuevo_monto:\n datos_solicitados["monto_pagado"] = formulario.nuevo_monto if
# formulario.nuevo_metodo_pago:\n datos_solicitados["metodo_pago"] = formulario.nuevo_metodo_pago if
# formulario.nueva_fecha_pago:\n datos_solicitados["fecha_pago"] = ( formulario.nueva_fecha_pago.isoformat() ) if
# formulario.nuevo_numero_operacion:\n datos_solicitados["numero_operacion"] = ( formulario.nuevo_numero_operacion ) if
# formulario.nuevo_banco:\n datos_solicitados["banco"] = formulario.nuevo_banco if formulario.nuevas_observaciones:\n
# datos_solicitados["observaciones"] = formulario.nuevas_observaciones return datos_solicitados\ndef
# _calcular_fecha_limite(prioridad:\n str) -> Optional[date]:\n """Calcular fecha límite según prioridad""" if prioridad ==
# "URGENTE":\n return date.today() + timedelta(days=1) elif prioridad == "ALTA":\n return date.today() + timedelta(days=2)
# elif prioridad == "NORMAL":\n return date.today() + timedelta(days=5) return None\ndef _crear_solicitud_aprobacion(
# formulario:\n FormularioModificarPago, datos_solicitados:\n Dict[str, Any], current_user:\n User, fecha_limite:\n
# Optional[date],) -> Aprobacion:\n """Crear solicitud de aprobación""" return Aprobacion( solicitante_id=current_user.id,
# tipo_solicitud=f"MODIFICAR_PAGO_{formulario.motivo_modificacion}", entidad="pago", entidad_id=formulario.pago_id,
# justificacion=f"[{formulario.motivo_modificacion}] " f"{formulario.justificacion}",
# datos_solicitados=str(datos_solicitados), estado="PENDIENTE", prioridad=formulario.prioridad, fecha_limite=fecha_limite,
# bloqueado_temporalmente=True, )\ndef _guardar_solicitud_con_archivo( solicitud:\n Aprobacion, archivo_path:\n
# Optional[str], tipo_archivo:\n Optional[str], tamaño_archivo:\n Optional[int], db:\n Session,) -> Aprobacion:\n """Guardar
# solicitud con archivo adjunto""" # Adjuntar archivo si existe if archivo_path:\n solicitud.adjuntar_archivo(archivo_path,
# tipo_archivo, tamaño_archivo) db.add(solicitud) db.commit() db.refresh(solicitud) return solicitud\ndef
# _generar_respuesta_solicitud( solicitud:\n Aprobacion, pago:\n Pago, datos_solicitados:\n Dict[str, Any], archivo_path:\n
# Optional[str],) -> Dict[str, Any]:\n """Generar respuesta de la solicitud""" return { "solicitud_id":\n solicitud.id,
# "mensaje":\n "✅ Solicitud de modificación de pago enviada exitosamente", "estado":\n "PENDIENTE", "prioridad":\n
# solicitud.prioridad, "fecha_limite":\n solicitud.fecha_limite, "requiere_aprobacion":\n True, "bloqueado_temporalmente":\n
# True, "archivo_adjunto":\n bool(archivo_path), "pago_afectado":\n { "id":\n pago.id, "monto_actual":\n
# float(pago.monto_pagado), "fecha_actual":\n pago.fecha_pago, "cliente":\n ( pago.prestamo.cliente.nombre_completo if
# pago.prestamo else "N/A" ), }, "cambios_solicitados":\n datos_solicitados, "siguiente_paso":\n "Esperar aprobación del
# administrador", }@router.post("/cobranzas/modificar-pago-completo")async \ndef solicitar_modificacion_pago_completo(
# formulario:\n FormularioModificarPago, archivo_evidencia:\n Optional[UploadFile] = File(None), db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚠️ COBRANZAS:\n Solicitar modificación de pago
# con formulario completo (VERSIÓN REFACTORIZADA) FLUJO COMPLETO:\n 1. ✅ Usuario completa formulario detallado 2. ✅ Adjunta
# evidencia (opcional) 3. ✅ Sistema registra solicitud 4. ✅ Notifica al Admin (in-app + email) 5. ✅ Bloquea temporalmente el
# registro """ # Validar solicitud pago, solicitud_existente = _validar_solicitud_modificacion_pago( formulario,
# current_user, db ) # Procesar archivo de evidencia archivo_path, tipo_archivo, tamaño_archivo = ( await
# _procesar_archivo_evidencia(archivo_evidencia) ) # Preparar datos solicitados datos_solicitados =
# _preparar_datos_solicitados(formulario) # Calcular fecha límite fecha_limite = _calcular_fecha_limite(formulario.prioridad)
# # Crear solicitud de aprobación solicitud = _crear_solicitud_aprobacion( formulario, datos_solicitados, current_user,
# fecha_limite ) # Guardar solicitud con archivo solicitud = _guardar_solicitud_con_archivo( solicitud, archivo_path,
# tipo_archivo, tamaño_archivo, db ) # Notificar al admin await _notificar_nueva_solicitud_admin(solicitud, db) # Generar
# respuesta return _generar_respuesta_solicitud( solicitud, pago, datos_solicitados, archivo_path
# )@router.post("/cobranzas/anular-pago-completo")async \ndef solicitar_anulacion_pago_completo( formulario:\n
# FormularioAnularPago, archivo_evidencia:\n Optional[UploadFile] = File(None), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ ⚠️ COBRANZAS:\n Solicitar anulación de pago con formulario
# completo """ # Verificar permisos - Todos los usuarios pueden usar este endpoint if not current_user.is_admin:\n raise
# HTTPException(status_code=403, detail="Usuario no autorizado") # Verificar que el pago existe y no está anulado pago =
# db.query(Pago).filter(Pago.id == formulario.pago_id).first() if not pago:\n raise HTTPException(status_code=404,
# detail="Pago no encontrado") if pago.anulado:\n raise HTTPException(status_code=400, detail="El pago ya está anulado") #
# Procesar archivo de evidencia archivo_path = None tipo_archivo = None tamaño_archivo = None if archivo_evidencia and
# archivo_evidencia.filename:\n archivo_path, tipo_archivo, tamaño_archivo = ( await
# guardar_archivo_evidencia(archivo_evidencia) ) # Preparar datos solicitados datos_solicitados = {
# "revertir_amortizacion":\n formulario.revertir_amortizacion, "notificar_cliente":\n formulario.notificar_cliente,
# "motivo":\n formulario.motivo_anulacion, } # Fecha límite más corta para anulaciones (más crítico) fecha_limite = None if
# formulario.prioridad == "URGENTE":\n fecha_limite = date.today() + timedelta(hours=4) elif formulario.prioridad ==
# "ALTA":\n fecha_limite = date.today() + timedelta(days=1) else:\n fecha_limite = date.today() + timedelta(days=3) # Crear
# solicitud solicitud = Aprobacion( solicitante_id=current_user.id,
# tipo_solicitud=f"ANULAR_PAGO_{formulario.motivo_anulacion}", entidad="pago", entidad_id=formulario.pago_id,
# justificacion=f"[{formulario.motivo_anulacion}] " f"{formulario.justificacion}", datos_solicitados=str(datos_solicitados),
# estado="PENDIENTE", prioridad=formulario.prioridad, fecha_limite=fecha_limite, bloqueado_temporalmente=True, ) if
# archivo_path:\n solicitud.adjuntar_archivo(archivo_path, tipo_archivo, tamaño_archivo) db.add(solicitud) db.commit()
# db.refresh(solicitud) # Notificar al admin await _notificar_nueva_solicitud_admin(solicitud, db) return { "solicitud_id":\n
# solicitud.id, "mensaje":\n "✅ Solicitud de anulación de pago enviada exitosamente", "estado":\n "PENDIENTE", "prioridad":\n
# solicitud.prioridad, "fecha_limite":\n solicitud.fecha_limite, "pago_afectado":\n { "id":\n pago.id, "monto":\n
# float(pago.monto_pagado), "fecha":\n pago.fecha_pago, "cliente":\n ( pago.prestamo.cliente.nombre_completo if pago.prestamo
# else "N/A" ), }, "acciones_solicitadas":\n datos_solicitados, }# Mantener endpoints originales para
# compatibilidad@router.post("/cobranzas/modificar-pago")\ndef solicitar_modificacion_pago( pago_id:\n int, nuevos_datos:\n
# Dict[str, Any], justificacion:\n str, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ ⚠️ COBRANZAS:\n Solicitar modificación de monto de pago """ # Verificar permisos - Todos
# los usuarios pueden usar este endpoint if not current_user.is_admin:\n raise HTTPException(status_code=403, detail="Usuario
# no autorizado") # Verificar que el pago existe pago = db.query(Pago).filter(Pago.id == pago_id).first() if not pago:\n
# raise HTTPException(status_code=404, detail="Pago no encontrado") # Crear solicitud de aprobación solicitud = Aprobacion(
# solicitante_id=current_user.id, tipo_solicitud="MODIFICAR_PAGO", entidad="pago", entidad_id=pago_id,
# justificacion=justificacion, datos_solicitados=str(nuevos_datos), # JSON como string estado="PENDIENTE", )
# db.add(solicitud) db.commit() db.refresh(solicitud) return { "solicitud_id":\n solicitud.id, "mensaje":\n "✅ Solicitud de
# modificación de pago enviada para aprobación", "estado":\n "PENDIENTE", "requiere_aprobacion":\n True, "pago_afectado":\n {
# "id":\n pago.id, "monto_actual":\n float(pago.monto_pagado), "cliente":\n ( pago.prestamo.cliente.nombre_completo if
# pago.prestamo else "N/A" ), }, }@router.post("/cobranzas/anular-pago")\ndef solicitar_anulacion_pago( pago_id:\n int,
# justificacion:\n str, revertir_amortizacion:\n bool = True, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ ⚠️ COBRANZAS:\n Solicitar anulación de pago """ # Verificar permisos - Todos los
# usuarios pueden usar este endpoint if not current_user.is_admin:\n raise HTTPException(status_code=403, detail="Usuario no
# autorizado") # Verificar que el pago existe pago = db.query(Pago).filter(Pago.id == pago_id).first() if not pago:\n raise
# HTTPException(status_code=404, detail="Pago no encontrado") # Crear solicitud de aprobación solicitud = Aprobacion(
# solicitante_id=current_user.id, tipo_solicitud="ANULAR_PAGO", entidad="pago", entidad_id=pago_id,
# justificacion=justificacion, datos_solicitados=str( {"revertir_amortizacion":\n revertir_amortizacion} ),
# estado="PENDIENTE", ) db.add(solicitud) db.commit() db.refresh(solicitud) return { "solicitud_id":\n solicitud.id,
# "mensaje":\n "✅ Solicitud de anulación de pago enviada para aprobación", "estado":\n "PENDIENTE", "requiere_aprobacion":\n
# True, "pago_afectado":\n { "id":\n pago.id, "monto":\n float(pago.monto_pagado), "fecha":\n pago.fecha_pago, "cliente":\n (
# pago.prestamo.cliente.nombre_completo if pago.prestamo else "N/A" ), },
# }@router.post("/cobranzas/modificar-amortizacion")\ndef solicitar_modificacion_amortizacion( prestamo_id:\n int,
# nuevos_parametros:\n Dict[str, Any], justificacion:\n str, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ ⚠️ COBRANZAS:\n Solicitar modificación de tabla de amortización """ # Verificar permisos
# - Todos los usuarios pueden usar este endpoint if not current_user.is_admin:\n raise HTTPException(status_code=403,
# detail="Usuario no autorizado") # Verificar que el préstamo existe prestamo = db.query(Prestamo).filter(Prestamo.id ==
# prestamo_id).first() if not prestamo:\n raise HTTPException(status_code=404, detail="Préstamo no encontrado") # Crear
# solicitud de aprobación solicitud = Aprobacion( solicitante_id=current_user.id, tipo_solicitud="MODIFICAR_AMORTIZACION",
# entidad="prestamo", entidad_id=prestamo_id, justificacion=justificacion, datos_solicitados=str(nuevos_parametros),
# estado="PENDIENTE", ) db.add(solicitud) db.commit() db.refresh(solicitud) return { "solicitud_id":\n solicitud.id,
# "mensaje":\n "✅ Solicitud de modificación de amortización enviada para aprobación", "estado":\n "PENDIENTE",
# "requiere_aprobacion":\n True, "prestamo_afectado":\n { "id":\n prestamo.id, "cliente":\n (
# prestamo.cliente.nombre_completo if prestamo.cliente else "N/A" ), "monto_actual":\n float(prestamo.monto_total), }, }#
# ============================================# SOLICITUDES DE USER#
# ============================================@router.post("/comercial/editar-cliente")\ndef
# solicitar_edicion_cliente_comercial( cliente_id:\n int, nuevos_datos:\n Dict[str, Any], justificacion:\n str, db:\n Session
# = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚠️ USER:\n Solicitar autorización para editar
# cliente """ # Verificar permisos if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Solo
# administradores pueden usar este endpoint", ) # Verificar que el cliente existe cliente =
# db.query(Cliente).filter(Cliente.id == cliente_id).first() if not cliente:\n raise HTTPException(status_code=404,
# detail="Cliente no encontrado") # Crear solicitud de aprobación solicitud = Aprobacion( solicitante_id=current_user.id,
# tipo_solicitud="EDITAR_CLIENTE_USER", entidad="cliente", entidad_id=cliente_id, justificacion=justificacion,
# datos_solicitados=str(nuevos_datos), estado="PENDIENTE", ) db.add(solicitud) db.commit() db.refresh(solicitud) return {
# "solicitud_id":\n solicitud.id, "mensaje":\n "✅ Solicitud de edición de cliente enviada para autorización de Admin",
# "estado":\n "PENDIENTE", "requiere_autorizacion":\n True, "cliente_afectado":\n { "id":\n cliente.id, "nombre":\n
# cliente.nombre_completo, "cedula":\n cliente.cedula, "vehiculo":\n cliente.vehiculo_completo, }, }#
# ============================================# SOLICITUDES DE USER#
# ============================================@router.post("/analista/editar-cliente-propio")\ndef
# solicitar_edicion_cliente_propio( cliente_id:\n int, nuevos_datos:\n Dict[str, Any], justificacion:\n str, db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚠️ USER:\n Solicitar autorización para editar
# SUS clientes asignados """ # Verificar permisos if not current_user.is_admin:\n raise HTTPException( status_code=403,
# detail="Solo administradores pueden usar este endpoint", ) # Verificar que el cliente existe y está asignado al analista
# cliente = ( db.query(Cliente) .filter( Cliente.id == cliente_id, Cliente.analista_id == current_user.id, # NOTA:\n Esto
# requiere mapeo User->Asesor ) .first() ) if not cliente:\n raise HTTPException( status_code=404, detail="Cliente no
# encontrado o no está asignado a usted", ) # Crear solicitud de aprobación solicitud = Aprobacion(
# solicitante_id=current_user.id, tipo_solicitud="EDITAR_CLIENTE_PROPIO", entidad="cliente", entidad_id=cliente_id,
# justificacion=justificacion, datos_solicitados=str(nuevos_datos), estado="PENDIENTE", ) db.add(solicitud) db.commit()
# db.refresh(solicitud) return { "solicitud_id":\n solicitud.id, "mensaje":\n "✅ Solicitud de edición enviada para
# autorización de Admin", "estado":\n "PENDIENTE", "requiere_autorizacion":\n True, "cliente_afectado":\n { "id":\n
# cliente.id, "nombre":\n cliente.nombre_completo, "cedula":\n cliente.cedula, "es_mi_cliente":\n True, }, }#
# ============================================# GESTIÓN DE SOLICITUDES (ADMIN)#
# ============================================@router.get("/pendientes", response_model=List[SolicitudResponse])\ndef
# listar_solicitudes_pendientes( tipo_solicitud:\n Optional[str] = Query(None), solicitante_id:\n Optional[int] =
# Query(None), page:\n int = Query(1, ge=1), page_size:\n int = Query(20, ge=1, le=1000), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 📋 Listar solicitudes pendientes de aprobación (Solo Admin) """ #
# Verificar permisos if not current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para ver
# solicitudes" ) query = db.query(Aprobacion).filter(Aprobacion.estado == "PENDIENTE") # Aplicar filtros if tipo_solicitud:\n
# query = query.filter(Aprobacion.tipo_solicitud == tipo_solicitud) if solicitante_id:\n query =
# query.filter(Aprobacion.solicitante_id == solicitante_id) # Paginación query.count() skip = (page - 1) * page_size
# solicitudes = ( query.order_by(Aprobacion.fecha_solicitud.desc()) .offset(skip) .limit(page_size) .all() ) # Formatear
# respuesta resultado = [] for sol in solicitudes:\n resultado.append( { "id":\n sol.id, "tipo_solicitud":\n
# sol.tipo_solicitud, "entidad_tipo":\n sol.entidad, "entidad_id":\n sol.entidad_id, "estado":\n sol.estado,
# "justificacion":\n sol.justificacion, "datos_solicitados":\n ( eval(sol.datos_solicitados) if sol.datos_solicitados else {}
# ), "solicitante":\n ( sol.solicitante.full_name if sol.solicitante else "N/A" ), "fecha_solicitud":\n sol.fecha_solicitud,
# "fecha_revision":\n sol.fecha_revision, "revisor":\n sol.revisor.full_name if sol.revisor else None,
# "comentarios_revisor":\n sol.comentarios_revisor, } ) return resultado@router.post("/aprobar/{solicitud_id}")async \ndef
# aprobar_solicitud( solicitud_id:\n int, comentarios:\n Optional[str] = None, db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ ✅ Aprobar solicitud (Solo Admin) """ # Verificar permisos if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para aprobar solicitudes" ) # Buscar
# solicitud solicitud = ( db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first() ) if not solicitud:\n raise
# HTTPException(status_code=404, detail="Solicitud no encontrada") if solicitud.estado != "PENDIENTE":\n raise HTTPException(
# status_code=400, detail="La solicitud ya fue procesada" ) # Aprobar solicitud solicitud.aprobar(current_user.id,
# comentarios) db.commit() # Ejecutar la acción aprobada resultado_ejecucion = _ejecutar_accion_aprobada(solicitud, db) #
# Notificar al solicitante sobre la aprobación await _notificar_resultado_solicitud(solicitud, db) return { "mensaje":\n "✅
# Solicitud aprobada y ejecutada exitosamente", "solicitud_id":\n solicitud_id, "tipo_solicitud":\n solicitud.tipo_solicitud,
# "aprobada_por":\n current_user.full_name, "fecha_aprobacion":\n solicitud.fecha_revision, "resultado_ejecucion":\n
# resultado_ejecucion, "notificacion_enviada":\n True, }@router.post("/rechazar/{solicitud_id}")async \ndef
# rechazar_solicitud( solicitud_id:\n int, comentarios:\n str, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ ❌ Rechazar solicitud (Solo Admin) """ # Verificar permisos if not
# current_user.is_admin:\n raise HTTPException( status_code=403, detail="Sin permisos para rechazar solicitudes" ) # Buscar
# solicitud solicitud = ( db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first() ) if not solicitud:\n raise
# HTTPException(status_code=404, detail="Solicitud no encontrada") if solicitud.estado != "PENDIENTE":\n raise HTTPException(
# status_code=400, detail="La solicitud ya fue procesada" ) # Rechazar solicitud solicitud.rechazar(current_user.id,
# comentarios) db.commit() # Notificar al solicitante sobre el rechazo await _notificar_resultado_solicitud(solicitud, db)
# return { "mensaje":\n "❌ Solicitud rechazada", "solicitud_id":\n solicitud_id, "tipo_solicitud":\n
# solicitud.tipo_solicitud, "rechazada_por":\n current_user.full_name, "motivo_rechazo":\n comentarios, "fecha_rechazo":\n
# solicitud.fecha_revision, "notificacion_enviada":\n True, }@router.get("/mis-solicitudes")\ndef listar_mis_solicitudes(
# estado:\n Optional[str] = Query( None, description="PENDIENTE, APROBADA, RECHAZADA" ), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 📋 Ver mis solicitudes enviadas """ query =
# db.query(Aprobacion).filter( Aprobacion.solicitante_id == current_user.id ) if estado:\n query =
# query.filter(Aprobacion.estado == estado) solicitudes = query.order_by(Aprobacion.fecha_solicitud.desc()).all() return {
# "total":\n len(solicitudes), "solicitudes":\n [ { "id":\n sol.id, "tipo":\n sol.tipo_solicitud, "entidad":\n
# f"{sol.entidad} #{sol.entidad_id}", "estado":\n sol.estado, "fecha_solicitud":\n sol.fecha_solicitud, "fecha_revision":\n
# sol.fecha_revision, "revisor":\n sol.revisor.full_name if sol.revisor else None, "comentarios":\n sol.comentarios_revisor,
# } for sol in solicitudes ], }# ============================================# FUNCIONES AUXILIARES#
# ============================================\ndef _ejecutar_accion_aprobada( solicitud:\n Aprobacion, db:\n Session) ->
# Dict[str, Any]:\n """ Ejecutar la acción una vez que fue aprobada """ try:\n datos = ( eval(solicitud.datos_solicitados) if
# solicitud.datos_solicitados else {} ) if solicitud.tipo_solicitud == "MODIFICAR_PAGO":\n # Modificar pago pago = (
# db.query(Pago).filter(Pago.id == solicitud.entidad_id).first() ) if pago:\n for campo, valor in datos.items():\n
# setattr(pago, campo, valor) db.commit() return {"accion":\n "Pago modificado", "pago_id":\n pago.id} elif
# solicitud.tipo_solicitud == "ANULAR_PAGO":\n # Anular pago pago = ( db.query(Pago).filter(Pago.id ==
# solicitud.entidad_id).first() ) if pago:\n pago.anular(solicitud.revisor.email, "Aprobado por admin") db.commit() return
# {"accion":\n "Pago anulado", "pago_id":\n pago.id} elif solicitud.tipo_solicitud == "EDITAR_CLIENTE_USER":\n # Editar
# cliente (comercial) cliente = ( db.query(Cliente) .filter(Cliente.id == solicitud.entidad_id) .first() ) if cliente:\n for
# campo, valor in datos.items():\n setattr(cliente, campo, valor) db.commit() return {"accion":\n "Cliente editado",
# "cliente_id":\n cliente.id} elif solicitud.tipo_solicitud == "EDITAR_CLIENTE_PROPIO":\n # Editar cliente propio (analista)
# cliente = ( db.query(Cliente) .filter(Cliente.id == solicitud.entidad_id) .first() ) if cliente:\n for campo, valor in
# datos.items():\n setattr(cliente, campo, valor) db.commit() return {"accion":\n "Cliente editado", "cliente_id":\n
# cliente.id} return { "accion":\n "Acción ejecutada", "detalles":\n "Sin implementación específica", } except Exception as
# e:\n return {"error":\n f"Error ejecutando acción:\n {str(e)}"}@router.get("/estadisticas")\ndef estadisticas_solicitudes(
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Estadísticas de solicitudes de
# aprobación """ # Verificar permisos if not current_user.is_admin:\n raise HTTPException(status_code=403, detail="Sin
# permisos") # Estadísticas generales total_pendientes = ( db.query(Aprobacion).filter(Aprobacion.estado ==
# "PENDIENTE").count() ) total_aprobadas = ( db.query(Aprobacion).filter(Aprobacion.estado == "APROBADA").count() )
# total_rechazadas = ( db.query(Aprobacion).filter(Aprobacion.estado == "RECHAZADA").count() ) # Por tipo de solicitud
# por_tipo = ( db.query( Aprobacion.tipo_solicitud, func.count(Aprobacion.id).label("total") )
# .group_by(Aprobacion.tipo_solicitud) .all() ) # Por solicitante por_solicitante = ( db.query(User.full_name,
# func.count(Aprobacion.id).label("total")) .join(Aprobacion, User.id == Aprobacion.solicitante_id) .group_by(User.id,
# User.full_name) .all() ) return { "resumen":\n { "pendientes":\n total_pendientes, "aprobadas":\n total_aprobadas,
# "rechazadas":\n total_rechazadas, "total":\n total_pendientes + total_aprobadas + total_rechazadas, }, "por_tipo":\n [
# {"tipo":\n tipo, "total":\n total} for tipo, total in por_tipo ], "por_solicitante":\n [ {"solicitante":\n nombre,
# "total":\n total} for nombre, total in por_solicitante ], "alertas":\n { "solicitudes_urgentes":\n total_pendientes,
# "requieren_atencion":\n total_pendientes > 5, }, }@router.get("/dashboard-aprobaciones")\ndef dashboard_aprobaciones( db:\n
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Dashboard visual completo del
# sistema de aprobaciones """ # Verificar permisos if not current_user.is_admin:\n raise HTTPException( status_code=403,
# detail="Sin permisos para ver dashboard" ) # Estadísticas principales total_pendientes = (
# db.query(Aprobacion).filter(Aprobacion.estado == "PENDIENTE").count() ) total_aprobadas_hoy = ( db.query(Aprobacion)
# .filter( Aprobacion.estado == "APROBADA", func.date(Aprobacion.fecha_revision) == date.today(), ) .count() )
# total_rechazadas_hoy = ( db.query(Aprobacion) .filter( Aprobacion.estado == "RECHAZADA",
# func.date(Aprobacion.fecha_revision) == date.today(), ) .count() ) # Solicitudes urgentes urgentes = ( db.query(Aprobacion)
# .filter( Aprobacion.estado == "PENDIENTE", Aprobacion.prioridad == "URGENTE" ) .count() ) # Solicitudes vencidas vencidas =
# ( db.query(Aprobacion) .filter( Aprobacion.estado == "PENDIENTE", Aprobacion.fecha_limite < date.today(), ) .count() ) #
# Solicitudes por tipo por_tipo = ( db.query( Aprobacion.tipo_solicitud, func.count(Aprobacion.id).label("total"), func.sum(
# func.case([(Aprobacion.estado == "PENDIENTE", 1)], else_=0) ).label("pendientes"), ) .group_by(Aprobacion.tipo_solicitud)
# .all() ) # Solicitudes por prioridad por_prioridad = ( db.query( Aprobacion.prioridad,
# func.count(Aprobacion.id).label("total") ) .filter(Aprobacion.estado == "PENDIENTE") .group_by(Aprobacion.prioridad) .all()
# ) # Tiempo promedio de respuesta tiempo_promedio = ( db.query(func.avg(Aprobacion.tiempo_respuesta_horas))
# .filter(Aprobacion.tiempo_respuesta_horas.isnot(None)) .scalar() or 0 ) # Solicitudes recientes (últimas 10) recientes = (
# db.query(Aprobacion) .filter(Aprobacion.estado == "PENDIENTE") .order_by(Aprobacion.fecha_solicitud.desc()) .limit(10)
# .all() ) # Formatear solicitudes recientes solicitudes_recientes = [] for sol in recientes:\n solicitudes_recientes.append(
# { "id":\n sol.id, "tipo":\n sol.tipo_solicitud, "solicitante":\n sol.solicitante.full_name, "prioridad":\n sol.prioridad,
# "dias_pendiente":\n sol.dias_pendiente, "requiere_atencion":\n sol.requiere_atencion_urgente, "fecha_limite":\n
# sol.fecha_limite, "entidad":\n f"{sol.entidad} #{sol.entidad_id}", "archivo_adjunto":\n bool(sol.archivo_evidencia), } )
# return { "titulo":\n "🔔 Dashboard de Aprobaciones", "fecha_actualizacion":\n datetime.now().isoformat(),
# "resumen_principal":\n { "pendientes":\n { "total":\n total_pendientes, "urgentes":\n urgentes, "vencidas":\n vencidas,
# "color":\n "#ffc107" if total_pendientes > 0 else "#28a745", }, "procesadas_hoy":\n { "aprobadas":\n total_aprobadas_hoy,
# "rechazadas":\n total_rechazadas_hoy, "total":\n total_aprobadas_hoy + total_rechazadas_hoy, }, "rendimiento":\n {
# "tiempo_promedio_horas":\n round(tiempo_promedio, 1), "eficiencia":\n ( "Alta" if tiempo_promedio < 24 else "Media" if
# tiempo_promedio < 48 else "Baja" ), }, }, "alertas":\n { "criticas":\n [ ( f"🚨 {urgentes} solicitudes URGENTES pendientes"
# if urgentes > 0 else None ), ( f"⏰ {vencidas} solicitudes VENCIDAS" if vencidas > 0 else None ), ( f"📈 {total_pendientes}
# solicitudes acumuladas" if total_pendientes > 10 else None ), ], "nivel_alerta":\n ( "CRITICO" if urgentes > 0 or vencidas
# > 0 else "NORMAL" ), }, "estadisticas":\n { "por_tipo":\n [ { "tipo":\n tipo, "total":\n int(total), "pendientes":\n
# int(pendientes or 0), "porcentaje_pendiente":\n ( round((pendientes or 0) / total * 100, 1) if total > 0 else 0 ), } for
# tipo, total, pendientes in por_tipo ], "por_prioridad":\n [ { "prioridad":\n prioridad, "cantidad":\n int(total),
# "color":\n ( { "URGENTE":\n "#dc3545", "ALTA":\n "#ffc107", "NORMAL":\n "#17a2b8", "BAJA":\n "#6c757d", }.get(prioridad,
# "#6c757d") ), } for prioridad, total in por_prioridad ], }, "solicitudes_recientes":\n solicitudes_recientes,
# "acciones_rapidas":\n { "ver_pendientes":\n "/api/v1/solicitudes/pendientes", "aprobar_masivo":\n
# "/api/v1/solicitudes/aprobar-masivo", "exportar_reporte":\n "/api/v1/solicitudes/reporte-excel", "configurar_alertas":\n
# "/api/v1/solicitudes/configurar-alertas", }, "metricas_visuales":\n { "gauge_pendientes":\n { "valor":\n total_pendientes,
# "maximo":\n 50, "color":\n "#ffc107" if total_pendientes < 20 else "#dc3545", }, "grafico_tiempo":\n { "promedio_actual":\n
# tiempo_promedio, "objetivo":\n 24, "tendencia":\n ( "mejorando" if tiempo_promedio < 24 else "estable" ), }, },
# }@router.get("/matriz-permisos")\ndef obtener_matriz_permisos_actualizada( current_user:\n User =
# Depends(get_current_user),):\n """ 📋 Obtener matriz de permisos actualizada con sistema de aprobaciones """ # Función
# obsoleta - sistema de permisos simplificado no requiere matriz compleja # \nfrom app.core.permissions \nimport
# get_permission_matrix_summary # Sistema simplificado - matriz básica de permisos matriz = { "ADMIN":\n { "acceso":\n "✅
# COMPLETO", "permisos":\n "✅ TODOS LOS PERMISOS", "aprobaciones":\n "❌ NO REQUERIDAS", }, "USER":\n { "acceso":\n "⚠️
# LIMITADO", "permisos":\n "⚠️ PERMISOS BÁSICOS", "aprobaciones":\n "✅ REQUERIDAS PARA ACCIONES CRÍTICAS", }, } return {
# "titulo":\n "MATRIZ DE PERMISOS ACTUALIZADA", "descripcion":\n "Sistema de roles con aprobaciones implementado",
# "fecha_actualizacion":\n "2025-10-13", "matriz_permisos":\n matriz, "flujos_aprobacion":\n { "cobranzas":\n {
# "modificar_pagos":\n "POST /solicitudes/cobranzas/modificar-pago", "anular_pagos":\n "POST
# /solicitudes/cobranzas/anular-pago", "modificar_amortizacion":\n "POST /solicitudes/cobranzas/modificar-amortizacion", },
# "comercial":\n { "editar_clientes":\n "POST /solicitudes/comercial/editar-cliente" }, "analista":\n {
# "editar_clientes_propios":\n "POST /solicitudes/analista/editar-cliente-propio" }, "admin":\n { "aprobar_solicitudes":\n
# "POST /solicitudes/aprobar/{sol \ icitud_id}", "rechazar_solicitudes":\n "POST /solicitudes/rechazar/{solicitud_id}",
# "ver_pendientes":\n "GET /solicitudes/pendientes", }, }, "endpoints_principales":\n { "solicitudes_pendientes":\n "GET
# /api/v1/solicitudes/pendientes", "mis_solicitudes":\n "GET /api/v1/solicitudes/mis-solicitudes", "estadisticas":\n "GET
# /api/v1/solicitudes/estadisticas", "matriz_permisos":\n "GET /api/v1/solicitudes/matriz-permisos", }, "usuario_actual":\n {
# "rol":\n "ADMIN" if current_user.is_admin else "USER", "puede_aprobar":\n current_user.is_admin,
# "requiere_aprobacion_para":\n _get_actions_requiring_approval( current_user.is_admin ), }, }\ndef
# _get_actions_requiring_approval(is_admin:\n bool) -> list:\n """ Obtener acciones que requieren aprobación para un usuario
# específico """ if is_admin:\n return [] # Los administradores no necesitan aprobación else:\n return [ "Modificar montos de
# pagos", "Anular/Eliminar pagos", "Modificar tabla de amortización", "Editar clientes", ]#
# ============================================# SISTEMA DE NOTIFICACIONES PARA APROBACIONES#
# ============================================async \ndef _notificar_nueva_solicitud_admin(solicitud:\n Aprobacion, db:\n
# Session):\n """ Notificar a administradores sobre nueva solicitud """ try:\n # Obtener todos los administradores admins =
# db.query(User).filter(User.is_admin).all() for admin in admins:\n # Crear notificación in-app notificacion = Notificacion(
# usuario_id=admin.id, tipo="SOLICITUD_APROBACION", categoria="SISTEMA", prioridad=solicitud.prioridad, titulo=f"Nueva
# solicitud de aprobación - {solicitud.tipo_solicitud}", mensaje=f""" Nueva solicitud de aprobación recibida **Detalles:\n**
# **Tipo:\n** {solicitud.tipo_solicitud} **Solicitante:\n** {solicitud.solicitante.full_name} **Entidad:\n**
# {solicitud.entidad} #{solicitud.entidad_id} **Prioridad:\n** {solicitud.prioridad} **Fecha límite:\n**
# {solicitud.fecha_limite} **Justificación:\n**{solicitud.justificacion} **Acciones:\n** Ver detalles:\n
# /solicitudes/pendientes Aprobar:\n /solicitudes/aprobar/{solicitud.id} Rechazar:\n /solicitudes/rechazar/{solicitud.id}
# """, extra_data=str( { "solicitud_id":\n solicitud.id, "tipo_solicitud":\n solicitud.tipo_solicitud, "prioridad":\n
# solicitud.prioridad, "url_accion":\n f"/solicitudes/pendientes?id={solicitud.id}", } ), ) db.add(notificacion) # Enviar
# email a administradores await _enviar_email_nueva_solicitud(solicitud, admins) # Marcar como notificado
# solicitud.marcar_notificado_admin() db.commit() except Exception as e:\n logger.error(f"Error enviando notificaciones:\n
# {e}")async \ndef _enviar_email_nueva_solicitud( solicitud:\n Aprobacion, admins:\n List[User]):\n """ Enviar email a
# administradores sobre nueva solicitud """ try:\n \nfrom app.services.email_service \nimport EmailService # Determinar
# urgencia urgencia_emoji = { "URGENTE":\n "🚨", "ALTA":\n "⚠️", "NORMAL":\n "📋", "BAJA":\n "📝", } emoji =
# urgencia_emoji.get(solicitud.prioridad, "📋") # Template del email asunto = f"{emoji} Nueva solicitud de aprobación -
# {solicitud.tipo_solicitud}" cuerpo_html = f""" <div style="font-family:\n Arial, sans-serif;\n max-width:\n 600px;\n
# margin:\n 0 auto;\n"> <div style="background:\n linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n color:\n white;\n
# padding:\n 20px;\n text-align:\n center;\n"> <h1>{emoji} Nueva Solicitud de Aprobación</h1> <p style="margin:\n 0;\n
# font-size:\n 18px;\n">{solicitud.tipo_solicitud}</p> </div> <div style="padding:\n 20px;\n background:\n #f8f9fa;\n"> <div
# style="background:\n white;\n padding:\n 20px;\n border-radius:\n \ 8px;\n box-shadow:\n 0 2px 4px rgba(0,0,0,0.1);\n"> <h2
# style="color:\n #333;\n margin-top:\n 0;\n">📋 Detalles de la Solicitud</h2> <table style="width:\n 100%;\n
# border-collapse:\n collapse;\n"> <tr style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n
# font-weight:\n bold;\n">Solicitante:\n</td> <td style="padding:\n 8px 0;\n">{solicitud.solsolicitante.full_name}</td> </tr>
# <tr style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n font-weight:\n bold;\n">Tipo:\n</td> <td
# style="padding:\n 8px 0;\n">{solicitud.tipo_solicitud}</td> </tr> <tr style="border-bottom:\n 1px solid #eee;\n"> <td
# style="padding:\n 8px 0;\n font-weight:\n bold;\n">Entidad:\n</td> <td style="padding:\n 8px 0;\n">{solicitud.entidad}
# #{solicitud.entidad_id}</td> </tr> <tr style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n
# font-weight:\n bold;\n">Prioridad:\n</td> <td style="padding:\n 8px 0;\n"> <span style=" background:\n {'#dc3545' if
# solicitud.prioridad == 'URGENTE' else '#ffc107' if solicitud.prioridad == 'ALTA' else '#28a745'};\n color:\n white;\n
# padding:\n 2px 8px;\n border-radius:\n 4px;\n font-size:\n 12px;\n ">{solicitud.prioridad}</span> </td> </tr> <tr
# style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n font-weight:\n bold;\n">Fecha límite:\n</td> <td
# style="padding:\n 8px 0;\n">{solicitud.fecha_limite}</td> </tr> <tr> <td style="padding:\n 8px 0;\n font-weight:\n
# bold;\n">Archivo adjunto:\n</td> <td style="padding:\n 8px 0;\n">{'✅ Sí' if solicitud.archivo_evidencia else '❌ No'}</td>
# </tr> </table> <h3 style="color:\n #333;\n margin-top:\n 20px;\n">📝 Justificación:\n</h3> <div style="background:\n
# #f8f9fa;\n padding:\n 15px;\n border-radius:\n 4px;\n border-left:\n 4px solid #007bff;\n"> {solicitud.justificacion}
# </div> <div style="text-align:\n center;\n margin-top:\n 30px;\n"> <a
# href="https:\n//pagos-f2qf.onrender.com/solicitudes/pendientes" style="background:\n #007bff;\n color:\n white;\n
# padding:\n 12px 24px;\n text-decoration:\n none;\n border-radius:\n 4px;\n display:\n inline-block;\n margin:\n 5px;\n"> 📋
# Ver Solicitudes Pendientes </a> <a href="https:\n//pagos-f2qf.onrender.com/solicitudes/aprobar/{solicitud.id}"
# style="background:\n #28a745;\n color:\n white;\n padding:\n 12px 24px;\n text-decoration:\n none;\n border-radius:\n
# 4px;\n display:\n inline-block;\n margin:\n 5px;\n"> ✅ Aprobar Solicitud </a> </div> </div> </div> <div
# style="background:\n #343a40;\n color:\n white;\n padding:\n 15px;\n text-align:\n center;\n font-size:\n 12px;\n"> <p
# style="margin:\n 0;\n">Sistema de Financiamiento Automotriz | Notificación automática</p> <p style="margin:\n 5px 0 0
# 0;\n">No responder a este email</p> </div> </div> """ # Enviar a cada admin for admin in admins:\n if admin.email:\n await
# EmailService.send_email( to_email=admin.email, subject=asunto, html_content=cuerpo_html, ) except Exception as e:\n
# logger.error(f"Error enviando emails:\n {e}")async \ndef _notificar_resultado_solicitud(solicitud:\n Aprobacion, db:\n
# Session):\n """ Notificar al solicitante sobre el resultado de su solicitud """ try:\n # Crear notificación in-app
# estado_emoji = {"APROBADA":\n "✅", "RECHAZADA":\n "❌"} emoji = estado_emoji.get(solicitud.estado, "📋") notificacion =
# Notificacion( usuario_id=solicitud.solicitante_id, tipo="RESULTADO_APROBACION", categoria="SISTEMA", prioridad="ALTA",
# titulo=f"{emoji} Solicitud {solicitud.estado.lower()} - {solicitud.tipo_solicitud}", mensaje=f"""{emoji} **Solicitud
# {solicitud.estado.lower()}** **Detalles:\n** **Tipo:\n** {solicitud.tipo_solicitud} **Entidad:\n** {solicitud.entidad}
# #{solicitud.entidad_id} **Revisado por:\n** {solicitud.revisor.full_name if solicitud.revisor else 'N/A'} **Fecha de
# revisión:\n** {solicitud.fecha_revision} **Comentarios del revisor:\n**{solicitud.comentarios_revisor or 'Sin comentarios
# adicionales'}{'🎉 **La acción solicitada ha sido ejecutada exitosamente.**' if solicitud.estado == 'APROBADA' else '⚠️ **La
# solicitud no fue aprobada. Revise los comentarios del revisor.**'} """, extra_data=str( { "solicitud_id":\n solicitud.id,
# "estado":\n solicitud.estado, "tipo_solicitud":\n solicitud.tipo_solicitud, } ), ) db.add(notificacion) # Enviar email al
# solicitante await _enviar_email_resultado_solicitud(solicitud) # Marcar como notificado
# solicitud.marcar_notificado_solicitante() db.commit() except Exception as e:\n logger.error(f"Error enviando notificación
# de resultado:\n {e}")async \ndef _enviar_email_resultado_solicitud(solicitud:\n Aprobacion):\n """ Enviar email al
# solicitante sobre el resultado """ try:\n estado_emoji = {"APROBADA":\n "✅", "RECHAZADA":\n "❌"} emoji =
# estado_emoji.get(solicitud.estado, "📋") color = "#28a745" if solicitud.estado == "APROBADA" else "#dc3545" asunto =
# f"{emoji} Solicitud {solicitud.estado.lower()} - {solicitud.tipo_solicitud}" cuerpo_html = f""" <div style="font-family:\n
# Arial, sans-serif;\n max-width:\n 600px;\n margin:\n 0 auto;\n"> <div style="background:\n {color};\n color:\n white;\n
# padding:\n 20px;\n text-align:\n center;\n"> <h1>{emoji} Solicitud {solicitud.estado.title()}</h1> <p style="margin:\n 0;\n
# font-size:\n 18px;\n">{solicitud.tipo_solicitud}</p> </div> <div style="padding:\n 20px;\n background:\n #f8f9fa;\n"> <div
# style="background:\n white;\n padding:\n 20px;\n border-radius:\n 8px;\n box-shadow:\n 0 2px 4px rgba(0,0,0,0.1);\n"> <h2
# style="color:\n #333;\n margin-top:\n 0;\n">📋 Resultado de su Solicitud</h2> <div style="background:\n {'#d4edda' if
# solicitud.estado == 'APROBADA' else '#f8d7da'};\n border:\n 1px solid {'#c3e6cb' if solicitud.estado == 'APROBADA' else
# '#f5c6cb'};\n color:\n {'#155724' if solicitud.estado == 'APROBADA' else '#721c24'};\n padding:\n 15px;\n border-radius:\n
# 4px;\n margin:\n 15px 0;\n"> <strong>{emoji} Su solicitud ha sido {solicitud.estado.lower()}</strong> </div> <table
# style="width:\n 100%;\n border-collapse:\n collapse;\n margin:\n 20px 0;\n"> <tr style="border-bottom:\n 1px solid
# #eee;\n"> <td style="padding:\n 8px 0;\n font-weight:\n bold;\n">Tipo de solicitud:\n</td> <td style="padding:\n 8px
# 0;\n">{solicitud.tipo_solicitud}</td> </tr> <tr style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n
# font-weight:\n bold;\n">Entidad afectada:\n</td> <td style="padding:\n 8px 0;\n">{solicitud.entidad}
# #{solicitud.entidad_id}</td> </tr> <tr style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n
# font-weight:\n bold;\n">Revisado por:\n</td> <td style="padding:\n 8px 0;\n">{solicitud.revisor.full_name if
# solicitud.revisor else 'N/A'}</td> </tr> <tr> <td style="padding:\n 8px 0;\n font-weight:\n bold;\n">Fecha de
# revisión:\n</td> <td style="padding:\n 8px 0;\n">{solicitud.fecha_revision}</td> </tr> </table> {f''' <h3 style="color:\n
# #333;\n">💬 Comentarios del revisor:\n</h3> <div style="background:\n #f8f9fa;\n padding:\n 15px;\n border-radius:\n 4px;\n
# border-left:\n 4px solid {color};\n"> {solicitud.comentarios_revisor} </div> ''' if solicitud.comentarios_revisor else ''}
# {f''' <p style="color:\n #28a745;\n font-weight:\n bold;\n"> 🎉 La acción solicitada ha sido ejecutada exitosamente. </p>
# ''' if solicitud.estado == 'APROBADA' else f''' <p style="color:\n #dc3545;\n font-weight:\n bold;\n"> ⚠️ La solicitud no
# fue aprobada. Revise los comentarios del revisor. </p> '''} <div style="text-align:\n center;\n margin-top:\n 30px;\n"> <a
# href="https:\n//pagos-f2qf.onrender.com/solicitudes/mis-solicitudes" style="background:\n #007bff;\n color:\n white;\n
# padding:\n 12px 24px;\n text-decoration:\n none;\n border-radius:\n 4px;\n display:\n inline-block;\n"> 📋 Ver Mis
# Solicitudes </a> </div> </div> </div> <div style="background:\n #343a40;\n color:\n white;\n padding:\n 15px;\n
# text-align:\n center;\n font-size:\n 12px;\n"> <p style="margin:\n 0;\n">Sistema de Financiamiento Automotriz |
# Notificación automática</p> <p style="margin:\n 5px 0 0 0;\n">No responder a este email</p> </div> </div> """ if
# solicitud.solicitante.email:\n await EmailService.send_email( to_email=solicitud.solicitante.email, subject=asunto,
# html_content=cuerpo_html, ) except Exception as e:\n logger.error(f"Error enviando email de resultado:\n {e}")
