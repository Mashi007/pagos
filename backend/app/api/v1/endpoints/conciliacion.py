from datetime import date
# backend/app/api/v1/endpoints/conciliacion.py"""Sistema de Conciliación BancariaProceso completo de conciliación automática"""
# \nimport Decimal\nfrom typing \nimport List, Optional, Dict, Any\nimport pandas as pd\nfrom fastapi \nimport 
# BackgroundTasks, Depends, File, HTTPException, Query, UploadFile,)\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps
# \nimport get_current_user, get_db\nfrom app.db.session \nimport SessionLocal\nfrom app.models.amortizacion \nimport
# Cuota\nfrom app.models.auditoria \nimport Auditoria, TipoAccion\nfrom app.models.cliente \nimport Cliente\nfrom
# app.models.notificacion \nimport Notificacion\nfrom app.models.pago \nimport Pago\nfrom app.models.prestamo \nimport
# Prestamo\nfrom app.models.user \nimport User\nfrom app.schemas.conciliacion \nimport 
# RevisionManual, TipoMatch, ValidacionArchivoBancario,)logger = logging.getLogger(__name__)router = APIRouter()\ndef
# _detectar_formato_archivo(filename:\n str) -> str:\n """Detectar formato del archivo""" filename_lower = filename.lower()
# if filename_lower.endswith((".xlsx", ".xls")):\n return "EXCEL" elif filename_lower.endswith(".csv"):\n return "CSV"
# _leer_archivo_excel(contenido:\n bytes) -> pd.DataFrame:\n """Leer archivo Excel y mapear columnas""" df =
# pd.read_excel(io.BytesIO(contenido)) # Mapear columnas esperadas columnas_esperadas = 
# "referencia", 3:\n "cedula_pagador", 4:\n "descripcion", 5:\n "cuenta_origen", } # Renombrar columnas df.columns = [
# columnas_esperadas.get(i, f"col_{i}") for i in range(len(df.columns)) ] return df\ndef _leer_archivo_csv
# bytes) -> pd.DataFrame:\n """Leer archivo CSV""" return pd.read_csv(io.StringIO(contenido.decode("utf-8")))\ndef
# _validar_columnas_requeridas(df:\n pd.DataFrame) -> list:\n """Validar que existan las columnas requeridas"""
# columnas_requeridas = ["fecha", "monto", "referencia", "cedula_pagador"] errores = [] for col in columnas_requeridas:\n if
# col not in df.columns:\n errores.append(f"Columna requerida '{col}' no encontrada") return errores\ndef
# _validar_fecha(fila:\n pd.Series, index:\n int) -> tuple[date, list]:\n """Validar fecha de una fila""" advertencias = []
# if pd.isna(fila["fecha"]):\n advertencias.append(f"Fila {index + 1}:\n Fecha vacía") return None, advertencias fecha_str =
# 1}:\n Formato de fecha inválido") return None, advertencias\ndef _validar_monto(fila:\n pd.Series, index:\n int) ->
# tuple[Decimal, list]:\n """Validar monto de una fila""" advertencias = [] try:\n monto = Decimal(str(fila["monto"])) if
# monto <= 0:\n advertencias.append(f"Fila {index + 1}:\n Monto inválido") return None, advertencias return monto,
# advertencias except Exception:\n advertencias.append(f"Fila {index + 1}:\n Formato de monto inválido") return None,
# advertencias\ndef _validar_referencia( fila:\n pd.Series, index:\n int, referencias_vistas:\n set) -> tuple[str, list,
# str(fila["referencia"]).strip() if not referencia or referencia == "nan":\n advertencias.append
# _buscar_matching_automatico( cedula:\n str, monto:\n Decimal, db:\n Session) -> dict:\n """Buscar matching automático para
# vista previa""" if not cedula or cedula == "nan":\n return {} cliente = db.query(Cliente).filter"""
# cedula).first() if not cliente:\n return {} # Buscar cuotas pendientes del cliente cuotas_pendientes = ( db.query(Cuota)
# .join(Prestamo) .filter( Prestamo.cliente_id == cliente.id, Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
# Cuota.monto_cuota == monto, # Monto exacto ) .first() ) if cuotas_pendientes:\n return 
# cliente.nombre_completo, "cedula":\n cliente.cedula, }, "pago_sugerido":\n 
# "numero_cuota":\n cuotas_pendientes.numero_cuota, "monto_cuota":\n float(cuotas_pendientes.monto_cuota), }, } # Buscar con
# tolerancia ±2% tolerancia = monto * Decimal("0.02") cuota_aproximada = ( db.query(Cuota) .join(Prestamo) .filter
# Prestamo.cliente_id == cliente.id, Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]), Cuota.monto_cuota >= 
# tolerancia), Cuota.monto_cuota <= (monto + tolerancia), ) .first() ) if cuota_aproximada:\n return 
# cliente.id, "nombre":\n cliente.nombre_completo, "cedula":\n cliente.cedula, }, "pago_sugerido":\n 
# "diferencia":\n float(abs(cuota_aproximada.monto_cuota - monto)), }, } return {}\ndef _procesar_fila_movimiento
# pd.Series, index:\n int, referencias_vistas:\n set, db:\n Session) -> tuple[ Optional[MovimientoBancarioExtendido],
# List[str], List[str], List[str]]:\n """Procesar una fila individual del archivo bancario""" advertencias = [] errores = []
# monto, monto_advertencias = _validar_monto(fila, index) advertencias.extend(monto_advertencias) if monto is None:\n return
# _validar_referencia( fila, index, referencias_vistas ) advertencias.extend(ref_advertencias)
# cedula = str(fila["cedula_pagador"]).strip() if cedula and cedula != "nan":\n cliente = 
# db.query(Cliente).filter(Cliente.cedula == cedula).first() ) if not cliente:\n advertencias.append
# Cédula" + f"{cedula} no registrada \ en sistema" ) # Crear movimiento movimiento = MovimientoBancarioExtendido
# descripcion=str(fila.get("descripcion", "")), cuenta_origen=( str(fila.get("cuenta_origen", "")) if "cuenta_origen" in fila
# else None ), id=index + 1, ) # Buscar matching automático matching_data = _buscar_matching_automatico(cedula, monto, db) if
# matching_data:\n movimiento.tipo_match = matching_data.get("tipo_match") movimiento.confianza_match =
# matching_data.get("confianza_match") movimiento.requiere_revision = matching_data.get( "requiere_revision", False )
# movimiento.cliente_encontrado = matching_data.get( "cliente_encontrado" ) movimiento.pago_sugerido =
# _procesar_archivo_completo(df:\n pd.DataFrame, db:\n Session) -> tuple[ List[MovimientoBancarioExtendido], List[str],
# index, referencias_vistas, db) ) advertencias.extend(fila_advertencias) errores.extend(fila_errores)
# registradas if movimiento.cedula_pagador:\n cliente = ( db.query(Cliente) .filter
# movimiento.cedula_pagador) .first() ) if ( not cliente and movimiento.cedula_pagador not in cedulas_no_registradas ):\n
# validar_archivo_bancario( archivo:\n UploadFile = File(...), db:\n Session = Depends(get_db), current_user:\n User =
# Formato requerido (Excel):\n - Columna A:\n Fecha de transacción - Columna B:\n Monto - Columna C:\n Nº
# Referencia/Comprobante - Columna D:\n Cédula del pagador - Columna E:\n Descripción/Concepto - Columna F:\n Nº Cuenta
# origen """ try:\n # 1. Detectar formato formato = _detectar_formato_archivo(archivo.filename) # 2. Leer archivo contenido ="""
# await archivo.read() if formato == "EXCEL":\n df = _leer_archivo_excel(contenido) else:\n # CSV df =
# _leer_archivo_csv(contenido) # 3. Validar columnas requeridas errores = _validar_columnas_requeridas(df) if errores:\n
# return ValidacionArchivoBancario( archivo_valido=False, formato_detectado=formato, total_filas=len(df), filas_validas=0,
# ValidacionArchivoBancario( archivo_valido=len(errores_procesamiento) == 0, formato_detectado=formato, total_filas=len(df),
# procesando archivo:\n {str(e)}" )\ndef _buscar_cliente_por_cedula(cedula:\n str, db:\n Session) -> Optional[Cliente]:\n
# """Buscar cliente por cédula""" return db.query(Cliente).filter(Cliente.cedula == cedula).first()\ndef
# _buscar_cuota_exacta( cliente_id:\n int, monto:\n Decimal, db:\n Session) -> Optional[Cuota]:\n """Buscar cuota con monto
# exacto""" return ( db.query(Cuota) .join(Prestamo) .filter"""
# Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]), Cuota.monto_cuota == monto, ) .first() )\ndef
# _buscar_cuota_aproximada( cliente_id:\n int, monto:\n Decimal, tolerancia:\n Decimal, db:\n Session) -> Optional[Cuota]:\n
# """Buscar cuota con monto aproximado""" return ( db.query(Cuota) .join(Prestamo) .filter
# cliente_id, Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]), Cuota.monto_cuota >= (monto - tolerancia),
# Cuota.monto_cuota <= (monto + tolerancia), ) .first() )\ndef _crear_match_exacto
# cliente:\n Cliente, cuota:\n Cuota) -> Dict[str, Any]:\n """Crear resultado de match exacto""" return 
# mov, "cliente":\n { "id":\n cliente.id, "nombre":\n cliente.nombre_completo, "cedula":\n cliente.cedula, }, "cuota":\n 
# cuota.fecha_vencimiento, }, "tipo_match":\n "CEDULA_MONTO_EXACTO", "confianza":\n 100.0, "estado_visual":\n "✅ EXACTO",
# }\ndef _crear_match_aproximado( mov:\n MovimientoBancarioExtendido, cliente:\n Cliente, cuota:\n Cuota) -> Dict[str,
# Any]:\n """Crear resultado de match aproximado""" diferencia = abs(cuota.monto_cuota - mov.monto) porcentaje_diferencia =
# (diferencia / mov.monto) * 100 return 
# cliente.nombre_completo, "cedula":\n cliente.cedula, }, "cuota":\n 
# float(porcentaje_diferencia), }, "tipo_match":\n "CEDULA_MONTO_APROXIMADO", "confianza":\n 80.0, "estado_visual":\n "⚠️
# REVISAR", }\ndef _buscar_pago_por_referencia( referencia:\n str, db:\n Session) -> Optional[Pago]:\n """Buscar pago por
# número de referencia""" return db.query(Pago).filter(Pago.numero_operacion == referencia).first()\ndef
# _crear_match_referencia( mov:\n MovimientoBancarioExtendido, pago:\n Pago) -> Dict[str, Any]:\n """Crear resultado de match
# por referencia""" return """
# "fecha":\n pago.fecha_pago, }, "tipo_match":\n "REFERENCIA_CONOCIDA", "confianza":\n 90.0, "estado_visual":\n "✅ EXACTO",
# }\ndef _crear_sin_match(mov:\n MovimientoBancarioExtendido) -> Dict[str, Any]:\n """Crear resultado sin match""" return 
# "Conciliación confirmada", "pago_id":\n pago_id}@router.get("/pendientes", response_model=List[dict])\ndef
# obtener_pendientes_conciliacion
# == EstadoConciliacion.PENDIENTE ) if fecha_inicio:\n query = query.filter(Pago.fecha_pago >= fecha_inicio) if fecha_fin:\n
# ]@router.get("/reporte-conciliacion")\ndef reporte_conciliacion
# Depends(get_db)):\n """ Genera reporte mensual de conciliación. """ \nfrom calendar \nimport monthrange fecha_inicio =
# db.query(Pago) .filter
# revision:\n RevisionManual, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """
# Procesar revisión manual de movimiento bancario """ try:\n if revision.accion == "APLICAR":\n # Buscar cliente cliente = """
# db.query(Cliente) .filter(Cliente.cedula == revision.cliente_cedula) .first() ) if not cliente:\n raise HTTPException
# status_code=404, detail="Cliente no encontrado" ) # Buscar cuota si se especifica cuota = None if revision.cuota_id:\n
# cuota = ( db.query(Cuota) .join(Prestamo) .filter( Cuota.id == revision.cuota_id, Prestamo.cliente_id == cliente.id, )
# .first() ) if not cuota:\n raise HTTPException( status_code=404, detail="Cuota no encontrada" ) # Crear pago monto_final =
# revision.monto_ajustado or revision.monto # Obtener movimiento original (esto requeriría almacenamiento temporal) # Por
# ), numero_cuota=cuota.numero_cuota if cuota else 1, monto_cuota_programado=( cuota.monto_cuota if cuota else monto_final ),
# monto_pagado=monto_final, monto_total=monto_final, fecha_pago=date.today(), fecha_vencimiento=
# cuota else date.today() ), metodo_pago="TRANSFERENCIA", numero_operacion=f"CONC-{revision.movimiento_id}",
# observaciones=f"Conciliación manual:\n {revision.observaciones}", usuario_registro=current_user.email,
# estado_conciliacion="CONCILIADO_MANUAL", ) db.add(db_pago) db.commit() db.refresh(db_pago) return 
# aplicado manualmente", "pago_id":\n db_pago.id, "cliente":\n cliente.nombre_completo, "monto":\n float(monto_final), } elif
# "message":\n "Movimiento rechazado", "observaciones":\n revision.observaciones, } elif revision.accion == "NO_APLICABLE":\n
# # Marcar como no aplicable return 
# revision.observaciones, } except Exception as e:\n db.rollback() raise HTTPException
# revisión manual:\n {str(e)}" )# ============================================# APLICACIÓN MASIVA#
# response_model=ResultadoConciliacionMasiva)\ndef aplicar_conciliacion_masiva
# background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n
# errores.append({"movimiento_id":\n mov_id, "error":\n str(e)}) # Generar reporte en background background_tasks.add_task
# raise HTTPException( status_code=500, detail=f"Error en aplicación masiva:\n {str(e)}" )#
# ============================================# HISTORIAL DE CONCILIACIONES#
# ============================================@router.get("/historial", response_model=List[HistorialConciliacion])\ndef
# obtener_historial_conciliaciones( fecha_desde:\n Optional[date] = Query(None), fecha_hasta:\n Optional[date] = Query(None),
# usuario:\n Optional[str] = Query(None), db:\n Session = Depends(get_db), current_user:\n User =
# 45), "usuario_proceso":\n "cobranzas@sistema.com", "archivo_original":\n "extracto_febrero_2024.xlsx",
# resultado = [ h for h in resultado if h["fecha_proceso"].date() >= fecha_desde ] if fecha_hasta:\n resultado = [ h for h in
# resultado if h["fecha_proceso"].date() <= fecha_hasta ] if usuario:\n resultado = [ h for h in resultado if usuario.lower()
# "12345678", "estado":\n "✅ Exacto", "color":\n "success", "confianza":\n 100.0, "accion_sugerida":\n "AUTO_APLICAR", }, 
# "color":\n "warning", "confianza":\n 75.0, "accion_sugerida":\n "REVISION_MANUAL", "diferencia":\n "$2.00", }, 
# "color":\n "danger", "confianza":\n 0.0, "accion_sugerida":\n "BUSQUEDA_MANUAL", }, ] return 
# revisión manual", "❌ MANUAL":\n "Sin coincidencia - Requiere búsqueda manual", }, }#
# ============================================# FUNCIONES AUXILIARES# ============================================async \ndef
# conciliación en background """ try:\n # Simulación de generación de reporte logger = logging.getLogger(__name__)"""
# ${total_monto}" ) # En implementación real:\n # 1. Crear PDF/Excel con detalles # 2. Enviar por email al usuario # 3.
# generando reporte de conciliación:\n {str(e)}")# ============================================# FLUJO COMPLETO DE
# flujo_completo_conciliacion( background_tasks:\n BackgroundTasks, archivo:\n UploadFile = File(...), db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🏦 FLUJO COMPLETO DE CONCILIACIÓN BANCARIA MASIVA
# genera reporte PDF 14. ✅ Conciliación completada 15. ✅ Notifica a Admin """ try:\n #"""
# ============================================ # PASOS 1-5:\n VALIDACIÓN Y VISTA PREVIA #
# validacion = await validar_archivo_bancario( archivo=archivo, db=db, current_user=current_user ) if not
# validacion.archivo_valido:\n return 
# "monto":\n f"${float(match['movimiento'].monto):\n,.2f}", "cliente":\n match["cliente"]["nombre"], "cedula":\n
# match["cliente"]["cedula"], "estado":\n "✅ Exacto", "color":\n "success", "confianza":\n match["confianza"],
# "accion_sugerida":\n "AUTO_APLICAR", "requiere_revision":\n False, } ) # Procesar coincidencias parciales for match in
# match["movimiento"].referencia, "monto":\n f"${float(match['movimiento'].monto):\n,.2f}", "cliente":\n
# match["cliente"]["nombre"], "cedula":\n match["cliente"]["cedula"], "estado":\n "⚠️ Revisar", "color":\n "warning",
# "confianza":\n match["confianza"], "accion_sugerida":\n "REVISION_MANUAL", "diferencia":\n 
# f"${match['cuota']['diferencia']:\n,.2f}" if "diferencia" in match.get("cuota", {}) else None ), "requiere_revision":\n
# True, } ) # Procesar sin coincidencia for match in resultado_matching.detalle_sin_conciliar_banco:\n
# f"${float(match['movimiento'].monto):\n,.2f}", "cliente":\n "????", "cedula":\n match["movimiento"].cedula_pagador or
# "Desconocida", "estado":\n "❌ Manual", "color":\n "danger", "confianza":\n 0.0, "accion_sugerida":\n "BUSQUEDA_MANUAL",
# "requiere_revision":\n True, } ) # ============================================ # PASO 10:\n RESUMEN ANTES DE APLICAR #
# "resumen":\n resumen_final, "leyenda":\n 
# {revision} requieren revisión" ), } except Exception as e:\n raise HTTPException
# proceso_id:\n str, background_tasks:\n BackgroundTasks, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🚀 PASO 11a:\n Aplicar solo coincidencias exactas automáticamente """ try:\n# En
# e:\n errores.append({"movimiento":\n f"MOV-{i + 1}", "error":\n str(e)}) # Registrar en auditoría auditoria =
# Auditoria.registrar
# db.add(auditoria) db.commit() # Generar reporte en background background_tasks.add_task
# total_monto=float(total_aplicado), ) # Notificar a admin background_tasks.add_task
# total_monto=float(total_aplicado), ) return 
# detail=f"Error aplicando conciliación:\n {str(e)}" )@router.get("/flujo-completo/paso/{paso}")\ndef
# obtener_paso_flujo_conciliacion
# conciliación" ), db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 📋 INFORMACIÓN
# DETALLADA DE CADA PASO DEL FLUJO """ if paso == 1:\n return """
# Referencia/Comprobante", "D:\n Cédula del pagador", "E:\n Descripción/Concepto", "F:\n Nº Cuenta origen", ], },
# "siguiente_paso":\n "Ingresar al sistema y acceder a Conciliación Bancaria", } elif paso == 2:\n return 
# "Cargar archivo Excel", } elif paso == 7:\n return 
# "Auto-aplicar", "estado":\n "✅ EXACTO", }, "prioridad_2":\n 
# "accion":\n "Requiere revisión", "estado":\n "⚠️ REVISAR", }, "prioridad_3":\n 
# "confianza":\n "90%", "accion":\n "Auto-aplicar", "estado":\n "✅ EXACTO", }, "sin_match":\n 
# coincidencia", "confianza":\n "0%", "accion":\n "Búsqueda manual", "estado":\n "❌ MANUAL", }, }, "siguiente_paso":\n
# "acciones_automaticas":\n [ 
# "descripcion":\n "Recalcula días de mora y estado financiero", }, 
# "descripcion":\n "Guarda log completo del proceso masivo", }, 
# "descripcion":\n "Notifica a cada cliente sobre su pago (background)", }, ], "siguiente_paso":\n "Generar reporte PDF", }
# elif paso == 13:\n return 
# validaciones", ], "formato":\n "PDF descargable", "siguiente_paso":\n "Notificar a administrador", } else:\n return 
# completada", "15":\n "Notifica a Admin", }, "endpoints_principales":\n 
# "revision_manual":\n "POST /conciliacion/revision-manual", "aplicar_masivo":\n "POST /conciliacion/aplicar-masivo", }, }#
# ============================================# FUNCIONES AUXILIARES PARA FLUJO COMPLETO#
# ============================================async \ndef _generar_reporte_conciliacion_completo
# """ try:\n logger = logging.getLogger(__name__) # Simulación de generación de reporte PDF reporte_data = """
# total_monto, "archivo_generado":\n f"conciliacion_{proceso_id}.pdf", } logger.info
# e:\n logger = logging.getLogger(__name__) logger.error(f"Error generando reporte completo:\n {str(e)}")async \ndef
# """ 🔔 PASO 15:\n Notificar a Admin sobre conciliación completada """ try:\n db = SessionLocal() # Obtener administradores
# admins = ( db.query(User) .filter(User.is_admin, User.is_active, User.email.isnot(None)) .all() ) for admin in admins:\n
# mensaje = f"""Hola {admin.full_name},CONCILIACIÓN BANCARIA COMPLETADA RESUMEN DEL PROCESO:\n Proceso ID:\n {proceso_id}"""
# = Notificacion
# Enviar emails \nfrom app.services.email_service \nimport EmailService email_service = EmailService() for admin in admins:\n
# notif = ( db.query(Notificacion) .filter( Notificacion.user_id == admin.id, Notificacion.asunto.like(f"%{proceso_id}%"), )
# .order_by(Notificacion.id.desc()) .first() ) if notif:\n await email_service.send_email
# logging.getLogger(__name__) logger.error( f"Error notificando admin sobre conciliación " f"{proceso_id}:\n {str(e)}" )

""""""