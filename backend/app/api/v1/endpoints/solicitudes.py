from datetime import date
# backend/app/api/v1/endpoints/solicitudes.py"""Sistema de Solicitudes de AprobaciónManeja solicitudes para acciones que
# \nimport Path\nfrom typing \nimport Any, Dict, List, Optional\nfrom fastapi \nimport APIRouter, Depends, File,
# HTTPException, Query, UploadFile\nfrom pydantic \nimport BaseModel, Field\nfrom sqlalchemy \nimport func\nfrom
# sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom app.models.aprobacion \nimport
# Aprobacion\nfrom app.models.cliente \nimport Cliente\nfrom app.models.notificacion \nimport Notificacion\nfrom
# app.models.pago \nimport Pago\nfrom app.models.prestamo \nimport Prestamo\nfrom app.models.user \nimport User\nfrom
# app.services.email_service \nimport EmailServicelogger = logging.getLogger(__name__)router = APIRouter()#
# ============================================# SCHEMAS PARA SOLICITUDES# ============================================\nclass
# SolicitudAprobacionCompleta(BaseModel):\n """Schema completo para crear solicitud de aprobación""" tipo_solicitud:\n str =
# Field( ..., description="MODIFICAR_PAGO, ANULAR_PAGO, EDITAR_CLIENTE, MODI \ FICAR_AMORTIZACION", ) entidad_tipo:\n str =
# Field(..., description="cliente, pago, prestamo") entidad_id:\n int = Field
# modificar") justificacion:\n str = Field( ..., min_length=10, max_length=1000, description="Justificación detallada", )
# default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE" ) fecha_limite:\n Optional[date] = Field
# description="Fecha límite para respuesta" ) \nclass Config:\n json_schema_extra = 
# Popular", }, "prioridad":\n "ALTA", "fecha_limite":\n "2025-10-15", } }\nclass FormularioModificarPago(BaseModel):\n
# """Formulario específico para modificar pago""" pago_id:\n int = Field(..., description="ID del pago a modificar")
# motivo_modificacion:\n str = Field( ..., description="ERROR_REGISTRO, CAMBIO_CLIENTE, AJUSTE_MONTO, OTRO" )
# modificar nuevo_monto:\n Optional[float] = Field( None, gt=0, description="Nuevo monto del pago" ) nuevo_metodo_pago:\n
# Optional[str] = Field( None, description="EFECTIVO, TRANSFERENCIA, TARJETA, CHEQUE" ) nueva_fecha_pago:\n Optional[date] =
# Field( None, description="Nueva fecha de pago" ) nuevo_numero_operacion:\n Optional[str] = Field
# número de operación" ) nuevo_banco:\n Optional[str] = Field(None, description="Nuevo banco") nuevas_observaciones:\n
# Optional[str] = Field( None, description="Nuevas observaciones" ) prioridad:\n str = Field
# description="BAJA, NORMAL, ALTA, URGENTE" )\nclass FormularioAnularPago(BaseModel):\n """Formulario específico para anular
# pago""" pago_id:\n int = Field(..., description="ID del pago a anular") motivo_anulacion:\n str = Field
# description="PAGO_DUPLICADO, ERROR_CLIENTE, DEVOLUCION, FRAUDE, OTRO", ) justificacion:\n str = Field
# description="Explicación detallada del motivo" ) revertir_amortizacion:\n bool = Field
# anulación" ) prioridad:\n str = Field( default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE" )\nclass
# FormularioEditarCliente(BaseModel):\n """Formulario específico para editar cliente""" cliente_id:\n int = Field
# description="ID del cliente a editar") motivo_edicion:\n str = Field
# ACTUALIZACION_CONTACTO, OTRO", ) justificacion:\n str = Field
# URGENTE" )\nclass FormularioModificarAmortizacion(BaseModel):\n """Formulario específico para modificar amortización"""
# prestamo_id:\n int = Field(..., description="ID del préstamo") motivo_modificacion:\n str = Field
# description="CAMBIO_TASA, EXTENSION_PLAZO, REFINANCIAMIENTO, OTRO" ) justificacion:\n str = Field
# None, ge=0, le=100, description="Nueva tasa de interés anual" ) nuevo_numero_cuotas:\n Optional[int] = Field
# le=360, description="Nuevo número de cuotas" ) nueva_modalidad_pago:\n Optional[str] = Field
# QUINCENAL, MENSUAL, BIMENSUAL" ) nueva_fecha_inicio:\n Optional[date] = Field( None, description="Nueva fecha de inicio" )
# prioridad:\n str = Field( default="ALTA", description="BAJA, NORMAL, ALTA, URGENTE" )\nclass
# SolicitudResponse(BaseModel):\n """Schema de respuesta para solicitud""" id:\n int tipo_solicitud:\n str entidad_tipo:\n
# ============================================# FUNCIONES AUXILIARES PARA ARCHIVOS#
# ============================================UPLOAD_DIR = Path("uploads/solicitudes")UPLOAD_DIR.mkdir
# exist_ok=True)ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".txt"}MAX_FILE_SIZE = 10 * 1024 *
# 1024 # 10MBasync \ndef guardar_archivo_evidencia( archivo:\n UploadFile,) -> tuple[str, str, int]:\n """Guardar archivo de
# evidencia y retornar (path, tipo, tamaño)""" if not archivo.filename:\n raise HTTPException
# detail="Nombre de archivo requerido" ) # Verificar extensión extension = Path(archivo.filename).suffix.lower() if extension
# '.join(ALLOWED_EXTENSIONS)}", ) # Leer contenido y verificar tamaño contenido = await archivo.read() if len(contenido) >
# MAX_FILE_SIZE:\n raise HTTPException( status_code=400, detail="Archivo demasiado grande (máximo 10MB)" ) # Generar nombre
# único nombre_unico = f"{uuid.uuid4()}{extension}" ruta_archivo = UPLOAD_DIR / nombre_unico # Guardar archivo with
# open(ruta_archivo, "wb") as f:\n f.write(contenido) return str(ruta_archivo), extension[1:\n].upper(), len(contenido)#
# ============================================# SOLICITUDES DE COBRANZAS CON FORMULARIOS COMPLETOS#
# ============================================\ndef _validar_solicitud_modificacion_pago
# FormularioModificarPago, current_user:\n User, db:\n Session) -> tuple[Pago, Optional[Aprobacion]]:\n """Validar solicitud
# detail="Usuario no autorizado") # Verificar que el pago existe pago = db.query(Pago).filter
# formulario.pago_id).first() if not pago:\n raise HTTPException(status_code=404, detail="Pago no encontrado") # Verificar
# que no hay solicitud pendiente para este pago solicitud_existente = ( db.query(Aprobacion) .filter
# "pago", Aprobacion.entidad_id == formulario.pago_id, Aprobacion.estado == "PENDIENTE", ) .first() ) if
# solicitud_existente:\n raise HTTPException
# (ID:\n {solicitud_existente.id})", ) return pago, solicitud_existenteasync \ndef _procesar_archivo_evidencia
# archivo_evidencia:\n Optional[UploadFile],) -> tuple[Optional[str], Optional[str], Optional[int]]:\n """Procesar archivo de
# evidencia""" archivo_path = None tipo_archivo = None tamaño_archivo = None if archivo_evidencia and
# archivo_evidencia.filename:\n archivo_path, tipo_archivo, tamaño_archivo = 
# guardar_archivo_evidencia(archivo_evidencia) ) return archivo_path, tipo_archivo, tamaño_archivo\ndef
# _calcular_fecha_limite(prioridad:\n str) -> Optional[date]:\n """Calcular fecha límite según prioridad""" if prioridad ==
# Optional[date],) -> Aprobacion:\n """Crear solicitud de aprobación""" return Aprobacion
# bloqueado_temporalmente=True, )\ndef _guardar_solicitud_con_archivo
# Optional[str], tipo_archivo:\n Optional[str], tamaño_archivo:\n Optional[int], db:\n Session,) -> Aprobacion:\n """Guardar
# solicitud con archivo adjunto""" # Adjuntar archivo si existe if archivo_path:\n solicitud.adjuntar_archivo
# tipo_archivo, tamaño_archivo) db.add(solicitud) db.commit() db.refresh(solicitud) return solicitud\ndef
# Optional[str],) -> Dict[str, Any]:\n """Generar respuesta de la solicitud""" return 
# "motivo":\n formulario.motivo_anulacion, } # Fecha límite más corta para anulaciones (más crítico) fecha_limite = None if
# solicitud solicitud = Aprobacion
# estado="PENDIENTE", prioridad=formulario.prioridad, fecha_limite=fecha_limite, bloqueado_temporalmente=True, ) if
# archivo_path:\n solicitud.adjuntar_archivo(archivo_path, tipo_archivo, tamaño_archivo) db.add(solicitud) db.commit()
# db.refresh(solicitud) # Notificar al admin await _notificar_nueva_solicitud_admin(solicitud, db) return 
# pago.prestamo.cliente.nombre_completo if pago.prestamo else "N/A" ), },
# detail="Usuario no autorizado") # Verificar que el préstamo existe prestamo = db.query(Prestamo).filter
# prestamo_id).first() if not prestamo:\n raise HTTPException(status_code=404, detail="Préstamo no encontrado") # Crear
# solicitud de aprobación solicitud = Aprobacion
# estado="PENDIENTE", ) db.add(solicitud) db.commit() db.refresh(solicitud) return 
# prestamo.cliente.nombre_completo if prestamo.cliente else "N/A" ), "monto_actual":\n float(prestamo.monto_total), }, }#
# ============================================# SOLICITUDES DE USER#
# = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚠️ USER:\n Solicitar autorización para editar
# administradores pueden usar este endpoint", ) # Verificar que el cliente existe cliente =
# db.query(Cliente).filter(Cliente.id == cliente_id).first() if not cliente:\n raise HTTPException
# detail="Cliente no encontrado") # Crear solicitud de aprobación solicitud = Aprobacion
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ⚠️ USER:\n Solicitar autorización para editar
# detail="Solo administradores pueden usar este endpoint", ) # Verificar que el cliente existe y está asignado al analista
# cliente = ( db.query(Cliente) .filter
# requiere mapeo User->Asesor ) .first() ) if not cliente:\n raise HTTPException
# encontrado o no está asignado a usted", ) # Crear solicitud de aprobación solicitud = Aprobacion
# db.refresh(solicitud) return 
# cliente.id, "nombre":\n cliente.nombre_completo, "cedula":\n cliente.cedula, "es_mi_cliente":\n True, }, }#
# ============================================# GESTIÓN DE SOLICITUDES (ADMIN)#
# ============================================@router.get("/pendientes", response_model=List[SolicitudResponse])\ndef
# listar_solicitudes_pendientes( tipo_solicitud:\n Optional[str] = Query(None), solicitante_id:\n Optional[int] =
# Query(None), page:\n int = Query(1, ge=1), page_size:\n int = Query(20, ge=1, le=1000), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 📋 Listar solicitudes pendientes de aprobación (Solo Admin) """ #
# query = query.filter(Aprobacion.tipo_solicitud == tipo_solicitud) if solicitante_id:\n query =
# query.filter(Aprobacion.solicitante_id == solicitante_id) # Paginación query.count() skip = (page - 1) * page_size
# solicitudes = ( query.order_by(Aprobacion.fecha_solicitud.desc()) .offset(skip) .limit(page_size) .all() ) # Formatear
# respuesta resultado = [] for sol in solicitudes:\n resultado.append
# ), "solicitante":\n ( sol.solicitante.full_name if sol.solicitante else "N/A" ), "fecha_solicitud":\n sol.fecha_solicitud,
# "fecha_revision":\n sol.fecha_revision, "revisor":\n sol.revisor.full_name if sol.revisor else None,
# solicitud solicitud = ( db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first() ) if not solicitud:\n raise
# HTTPException(status_code=404, detail="Solicitud no encontrada") if solicitud.estado != "PENDIENTE":\n raise HTTPException
# status_code=400, detail="La solicitud ya fue procesada" ) # Aprobar solicitud solicitud.aprobar
# Notificar al solicitante sobre la aprobación await _notificar_resultado_solicitud(solicitud, db) return 
# solicitud.fecha_revision, "notificacion_enviada":\n True, }@router.get("/mis-solicitudes")\ndef listar_mis_solicitudes
# estado:\n Optional[str] = Query( None, description="PENDIENTE, APROBADA, RECHAZADA" ), db:\n Session = Depends(get_db),
# current_user:\n User = Depends(get_current_user),):\n """ 📋 Ver mis solicitudes enviadas """ query =
# db.query(Aprobacion).filter( Aprobacion.solicitante_id == current_user.id ) if estado:\n query =
# query.filter(Aprobacion.estado == estado) solicitudes = query.order_by(Aprobacion.fecha_solicitud.desc()).all() return 
# f"{sol.entidad} #{sol.entidad_id}", "estado":\n sol.estado, "fecha_solicitud":\n sol.fecha_solicitud, "fecha_revision":\n
# } for sol in solicitudes ], }# ============================================# FUNCIONES AUXILIARES#
# ============================================\ndef _ejecutar_accion_aprobada( solicitud:\n Aprobacion, db:\n Session) ->
# setattr(pago, campo, valor) db.commit() return {"accion":\n "Pago modificado", "pago_id":\n pago.id} elif
# solicitud.tipo_solicitud == "ANULAR_PAGO":\n # Anular pago pago = ( db.query(Pago).filter
# solicitud.entidad_id).first() ) if pago:\n pago.anular(solicitud.revisor.email, "Aprobado por admin") db.commit() return
# {"accion":\n "Pago anulado", "pago_id":\n pago.id} elif solicitud.tipo_solicitud == "EDITAR_CLIENTE_USER":\n # Editar
# cliente (comercial) cliente = ( db.query(Cliente) .filter(Cliente.id == solicitud.entidad_id) .first() ) if cliente:\n for
# "cliente_id":\n cliente.id} elif solicitud.tipo_solicitud == "EDITAR_CLIENTE_PROPIO":\n # Editar cliente propio (analista)
# cliente = ( db.query(Cliente) .filter(Cliente.id == solicitud.entidad_id) .first() ) if cliente:\n for campo, valor in
# cliente.id} return { "accion":\n "Acción ejecutada", "detalles":\n "Sin implementación específica", } except Exception as
# e:\n return {"error":\n f"Error ejecutando acción:\n {str(e)}"}@router.get("/estadisticas")\ndef estadisticas_solicitudes
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Estadísticas de solicitudes de
# "PENDIENTE").count() ) total_aprobadas = ( db.query(Aprobacion).filter(Aprobacion.estado == "APROBADA").count() )
# total_rechazadas = ( db.query(Aprobacion).filter(Aprobacion.estado == "RECHAZADA").count() ) # Por tipo de solicitud
# por_tipo = ( db.query( Aprobacion.tipo_solicitud, func.count(Aprobacion.id).label("total") )
# .group_by(Aprobacion.tipo_solicitud) .all() ) # Por solicitante por_solicitante = 
# func.count(Aprobacion.id).label("total")) .join(Aprobacion, User.id == Aprobacion.solicitante_id) .group_by
# User.full_name) .all() ) return 
# "rechazadas":\n total_rechazadas, "total":\n total_pendientes + total_aprobadas + total_rechazadas, }, "por_tipo":\n [
# {"tipo":\n tipo, "total":\n total} for tipo, total in por_tipo ], "por_solicitante":\n [ 
# "total":\n total} for nombre, total in por_solicitante ], "alertas":\n 
# "requieren_atencion":\n total_pendientes > 5, }, }@router.get("/dashboard-aprobaciones")\ndef dashboard_aprobaciones
# Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📊 Dashboard visual completo del
# db.query(Aprobacion).filter(Aprobacion.estado == "PENDIENTE").count() ) total_aprobadas_hoy = ( db.query(Aprobacion)
# .filter( Aprobacion.estado == "APROBADA", func.date(Aprobacion.fecha_revision) == date.today(), ) .count() )
# total_rechazadas_hoy = ( db.query(Aprobacion) .filter
# func.date(Aprobacion.fecha_revision) == date.today(), ) .count() ) # Solicitudes urgentes urgentes = ( db.query(Aprobacion)
# .filter( Aprobacion.estado == "PENDIENTE", Aprobacion.prioridad == "URGENTE" ) .count() ) # Solicitudes vencidas vencidas =
# ( db.query(Aprobacion) .filter( Aprobacion.estado == "PENDIENTE", Aprobacion.fecha_limite < date.today(), ) .count() ) #
# Solicitudes por tipo por_tipo = ( db.query( Aprobacion.tipo_solicitud, func.count(Aprobacion.id).label("total"), func.sum
# func.case([(Aprobacion.estado == "PENDIENTE", 1)], else_=0) ).label("pendientes"), ) .group_by(Aprobacion.tipo_solicitud)
# .all() ) # Solicitudes por prioridad por_prioridad = 
# func.count(Aprobacion.id).label("total") ) .filter(Aprobacion.estado == "PENDIENTE") .group_by(Aprobacion.prioridad) .all()
# ) # Tiempo promedio de respuesta tiempo_promedio = ( db.query(func.avg(Aprobacion.tiempo_respuesta_horas))
# .filter(Aprobacion.tiempo_respuesta_horas.isnot(None)) .scalar() or 0 ) # Solicitudes recientes (últimas 10) recientes = 
# db.query(Aprobacion) .filter(Aprobacion.estado == "PENDIENTE") .order_by(Aprobacion.fecha_solicitud.desc()) .limit(10)
# .all() ) # Formatear solicitudes recientes solicitudes_recientes = [] for sol in recientes:\n solicitudes_recientes.append
# sol.fecha_limite, "entidad":\n f"{sol.entidad} #{sol.entidad_id}", "archivo_adjunto":\n bool(sol.archivo_evidencia), } )
# "resumen_principal":\n 
# "color":\n "#ffc107" if total_pendientes > 0 else "#28a745", }, "procesadas_hoy":\n 
# "rechazadas":\n total_rechazadas_hoy, "total":\n total_aprobadas_hoy + total_rechazadas_hoy, }, "rendimiento":\n 
# tiempo_promedio < 48 else "Baja" ), }, }, "alertas":\n 
# if urgentes > 0 else None ), ( f"⏰ {vencidas} solicitudes VENCIDAS" if vencidas > 0 else None ), 
# solicitudes acumuladas" if total_pendientes > 10 else None ), ], "nivel_alerta":\n 
# > 0 else "NORMAL" ), }, "estadisticas":\n 
# int(pendientes or 0), "porcentaje_pendiente":\n ( round((pendientes or 0) / total * 100, 1) if total > 0 else 0 ), } for
# tipo, total, pendientes in por_tipo ], "por_prioridad":\n [ 
# "#6c757d") ), } for prioridad, total in por_prioridad ], }, "solicitudes_recientes":\n solicitudes_recientes,
# "acciones_rapidas":\n 
# "/api/v1/solicitudes/configurar-alertas", }, "metricas_visuales":\n 
# "maximo":\n 50, "color":\n "#ffc107" if total_pendientes < 20 else "#dc3545", }, "grafico_tiempo":\n 
# tiempo_promedio, "objetivo":\n 24, "tendencia":\n ( "mejorando" if tiempo_promedio < 24 else "estable" ), }, },
# "titulo":\n "MATRIZ DE PERMISOS ACTUALIZADA", "descripcion":\n "Sistema de roles con aprobaciones implementado",
# /solicitudes/cobranzas/anular-pago", "modificar_amortizacion":\n "POST /solicitudes/cobranzas/modificar-amortizacion", },
# "comercial":\n { "editar_clientes":\n "POST /solicitudes/comercial/editar-cliente" }, "analista":\n 
# "POST /solicitudes/aprobar/{sol \ icitud_id}", "rechazar_solicitudes":\n "POST /solicitudes/rechazar/{solicitud_id}",
# "ver_pendientes":\n "GET /solicitudes/pendientes", }, }, "endpoints_principales":\n 
# "requiere_aprobacion_para":\n _get_actions_requiring_approval( current_user.is_admin ), }, }\ndef
# _get_actions_requiring_approval(is_admin:\n bool) -> list:\n """ Obtener acciones que requieren aprobación para un usuario
# ============================================# SISTEMA DE NOTIFICACIONES PARA APROBACIONES#
# ============================================async \ndef _notificar_nueva_solicitud_admin
# db.query(User).filter(User.is_admin).all() for admin in admins:\n # Crear notificación in-app notificacion = Notificacion
# solicitud.prioridad, "url_accion":\n f"/solicitudes/pendientes?id={solicitud.id}", } ), ) db.add(notificacion) # Enviar
# email a administradores await _enviar_email_nueva_solicitud(solicitud, admins) # Marcar como notificado
# solicitud.marcar_notificado_admin() db.commit() except Exception as e:\n logger.error
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
# font-weight:\n bold;\n">Prioridad:\n</td> <td style="padding:\n 8px 0;\n"> <span style=" background:\n 
# solicitud.prioridad == 'URGENTE' else '#ffc107' if solicitud.prioridad == 'ALTA' else '#28a745'};\n color:\n white;\n
# padding:\n 2px 8px;\n border-radius:\n 4px;\n font-size:\n 12px;\n ">{solicitud.prioridad}</span> </td> </tr> <tr
# style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n font-weight:\n bold;\n">Fecha límite:\n</td> <td
# style="padding:\n 8px 0;\n">{solicitud.fecha_limite}</td> </tr> <tr> <td style="padding:\n 8px 0;\n font-weight:\n
# bold;\n">Archivo adjunto:\n</td> <td style="padding:\n 8px 0;\n">{'✅ Sí' if solicitud.archivo_evidencia else '❌ No'}</td>
# </tr> </table> <h3 style="color:\n #333;\n margin-top:\n 20px;\n">📝 Justificación:\n</h3> <div style="background:\n
# #f8f9fa;\n padding:\n 15px;\n border-radius:\n 4px;\n border-left:\n 4px solid #007bff;\n"> {solicitud.justificacion}
# </div> <div style="text-align:\n center;\n margin-top:\n 30px;\n"> <a
# padding:\n 12px 24px;\n text-decoration:\n none;\n border-radius:\n 4px;\n display:\n inline-block;\n margin:\n 5px;\n"> 📋
# style="background:\n #28a745;\n color:\n white;\n padding:\n 12px 24px;\n text-decoration:\n none;\n border-radius:\n
# 4px;\n display:\n inline-block;\n margin:\n 5px;\n"> ✅ Aprobar Solicitud </a> </div> </div> </div> <div
# style="background:\n #343a40;\n color:\n white;\n padding:\n 15px;\n text-align:\n center;\n font-size:\n 12px;\n"> <p
# style="margin:\n 0;\n">Sistema de Financiamiento Automotriz | Notificación automática</p> <p style="margin:\n 5px 0 0
# 0;\n">No responder a este email</p> </div> </div> """ # Enviar a cada admin for admin in admins:\n if admin.email:\n await
# EmailService.send_email( to_email=admin.email, subject=asunto, html_content=cuerpo_html, ) except Exception as e:\n
# logger.error(f"Error enviando emails:\n {e}")async \ndef _notificar_resultado_solicitud
# Session):\n """ Notificar al solicitante sobre el resultado de su solicitud """ try:\n # Crear notificación in-app
# estado_emoji = {"APROBADA":\n "✅", "RECHAZADA":\n "❌"} emoji = estado_emoji.get(solicitud.estado, "📋") notificacion =
# Notificacion
# titulo=f"{emoji} Solicitud {solicitud.estado.lower()} - {solicitud.tipo_solicitud}", mensaje=f"""{emoji} **Solicitud
# {solicitud.estado.lower()}** **Detalles:\n** **Tipo:\n** {solicitud.tipo_solicitud} **Entidad:\n** {solicitud.entidad}
# #{solicitud.entidad_id} **Revisado por:\n** {solicitud.revisor.full_name if solicitud.revisor else 'N/A'} **Fecha de
# "estado":\n solicitud.estado, "tipo_solicitud":\n solicitud.tipo_solicitud, } ), ) db.add(notificacion) # Enviar email al
# solicitante await _enviar_email_resultado_solicitud(solicitud) # Marcar como notificado
# solicitud.marcar_notificado_solicitante() db.commit() except Exception as e:\n logger.error
# de resultado:\n {e}")async \ndef _enviar_email_resultado_solicitud(solicitud:\n Aprobacion):\n """ Enviar email al
# solicitante sobre el resultado """ try:\n estado_emoji = {"APROBADA":\n "✅", "RECHAZADA":\n "❌"} emoji =
# estado_emoji.get(solicitud.estado, "📋") color = "#28a745" if solicitud.estado == "APROBADA" else "#dc3545" asunto =
# f"{emoji} Solicitud {solicitud.estado.lower()} - {solicitud.tipo_solicitud}" cuerpo_html = f""" <div style="font-family:\n
# Arial, sans-serif;\n max-width:\n 600px;\n margin:\n 0 auto;\n"> <div style="background:\n {color};\n color:\n white;\n
# padding:\n 20px;\n text-align:\n center;\n"> <h1>{emoji} Solicitud {solicitud.estado.title()}</h1> <p style="margin:\n 0;\n
# font-size:\n 18px;\n">{solicitud.tipo_solicitud}</p> </div> <div style="padding:\n 20px;\n background:\n #f8f9fa;\n"> <div
# style="background:\n white;\n padding:\n 20px;\n border-radius:\n 8px;\n box-shadow:\n 0 2px 4px rgba(0,0,0,0.1);\n"> <h2
# style="color:\n #333;\n margin-top:\n 0;\n">📋 Resultado de su Solicitud</h2> <div style="background:\n 
# solicitud.estado == 'APROBADA' else '#f8d7da'};\n border:\n 1px solid 
# '#f5c6cb'};\n color:\n {'#155724' if solicitud.estado == 'APROBADA' else '#721c24'};\n padding:\n 15px;\n border-radius:\n
# 4px;\n margin:\n 15px 0;\n"> <strong>{emoji} Su solicitud ha sido {solicitud.estado.lower()}</strong> </div> <table
# style="width:\n 100%;\n border-collapse:\n collapse;\n margin:\n 20px 0;\n"> <tr style="border-bottom:\n 1px solid
# #eee;\n"> <td style="padding:\n 8px 0;\n font-weight:\n bold;\n">Tipo de solicitud:\n</td> <td style="padding:\n 8px
# 0;\n">{solicitud.tipo_solicitud}</td> </tr> <tr style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n
# font-weight:\n bold;\n">Entidad afectada:\n</td> <td style="padding:\n 8px 0;\n">{solicitud.entidad}
# #{solicitud.entidad_id}</td> </tr> <tr style="border-bottom:\n 1px solid #eee;\n"> <td style="padding:\n 8px 0;\n
# font-weight:\n bold;\n">Revisado por:\n</td> <td style="padding:\n 8px 0;\n">
# solicitud.revisor else 'N/A'}</td> </tr> <tr> <td style="padding:\n 8px 0;\n font-weight:\n bold;\n">Fecha de
# revisión:\n</td> <td style="padding:\n 8px 0;\n">{solicitud.fecha_revision}</td> </tr> </table> 
# html_content=cuerpo_html, ) except Exception as e:\n logger.error(f"Error enviando email de resultado:\n {e}")
