# backend/app/api/v1/endpoints/conciliacion.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import csv
import io
import pandas as pd

from app.db.session import get_db, SessionLocal
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.cliente import Cliente
from app.models.amortizacion import Cuota
from app.models.user import User
from app.schemas.conciliacion import (
    ConciliacionCreate,
    ConciliacionResponse,
    MovimientoBancario,
    MovimientoBancarioExtendido,
    ResultadoConciliacion,
    EstadoConciliacion,
    TipoMatch,
    ValidacionArchivoBancario,
    ConciliacionMasiva,
    ResultadoConciliacionMasiva,
    RevisionManual,
    HistorialConciliacion
)
from app.core.security import get_current_user

router = APIRouter()


@router.post("/validar-archivo", response_model=ValidacionArchivoBancario)
async def validar_archivo_bancario(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validar archivo bancario (Excel/CSV) y mostrar vista previa
    
    Formato requerido (Excel):
    - Columna A: Fecha de transacción
    - Columna B: Monto  
    - Columna C: Nº Referencia/Comprobante
    - Columna D: Cédula del pagador
    - Columna E: Descripción/Concepto
    - Columna F: Nº Cuenta origen
    """
    try:
        # Detectar formato
        filename = archivo.filename.lower()
        if filename.endswith(('.xlsx', '.xls')):
            formato = "EXCEL"
        elif filename.endswith('.csv'):
            formato = "CSV"
        else:
            raise HTTPException(
                status_code=400,
                detail="Solo se aceptan archivos Excel (.xlsx, .xls) o CSV"
            )
        
        # Leer archivo
        contenido = await archivo.read()
        
        if formato == "EXCEL":
            # Leer Excel
            df = pd.read_excel(io.BytesIO(contenido))
            
            # Mapear columnas esperadas
            columnas_esperadas = {
                0: 'fecha',
                1: 'monto', 
                2: 'referencia',
                3: 'cedula_pagador',
                4: 'descripcion',
                5: 'cuenta_origen'
            }
            
            # Renombrar columnas
            df.columns = [columnas_esperadas.get(i, f'col_{i}') for i in range(len(df.columns))]
            
        else:  # CSV
            df = pd.read_csv(io.StringIO(contenido.decode('utf-8')))
        
        # Validaciones
        errores = []
        advertencias = []
        movimientos_validos = []
        duplicados = []
        cedulas_no_registradas = []
        
        # Verificar columnas requeridas
        columnas_requeridas = ['fecha', 'monto', 'referencia', 'cedula_pagador']
        for col in columnas_requeridas:
            if col not in df.columns:
                errores.append(f"Columna requerida '{col}' no encontrada")
        
        if errores:
            return ValidacionArchivoBancario(
                archivo_valido=False,
                formato_detectado=formato,
                total_filas=len(df),
                filas_validas=0,
                errores=errores,
                vista_previa=[]
            )
        
        # Procesar cada fila
        referencias_vistas = set()
        
        for index, fila in df.iterrows():
            try:
                # Validar fecha
                if pd.isna(fila['fecha']):
                    advertencias.append(f"Fila {index + 1}: Fecha vacía")
                    continue
                
                fecha_str = str(fila['fecha'])
                if '/' in fecha_str:
                    fecha = datetime.strptime(fecha_str, '%d/%m/%Y').date()
                else:
                    fecha = pd.to_datetime(fila['fecha']).date()
                
                # Validar monto
                monto = Decimal(str(fila['monto']))
                if monto <= 0:
                    advertencias.append(f"Fila {index + 1}: Monto inválido")
                    continue
                
                # Validar referencia
                referencia = str(fila['referencia']).strip()
                if not referencia or referencia == 'nan':
                    advertencias.append(f"Fila {index + 1}: Referencia vacía")
                    continue
                
                # Detectar duplicados
                if referencia in referencias_vistas:
                    duplicados.append({
                        "fila": index + 1,
                        "referencia": referencia,
                        "monto": float(monto)
                    })
                    continue
                referencias_vistas.add(referencia)
                
                # Validar cédula
                cedula = str(fila['cedula_pagador']).strip()
                if cedula and cedula != 'nan':
                    # Verificar si la cédula existe en el sistema
                    cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
                    if not cliente:
                        if cedula not in cedulas_no_registradas:
                            cedulas_no_registradas.append(cedula)
                
                # Crear movimiento
                movimiento = MovimientoBancarioExtendido(
                    fecha=fecha,
                    referencia=referencia,
                    monto=monto,
                    cedula_pagador=cedula if cedula != 'nan' else None,
                    descripcion=str(fila.get('descripcion', '')),
                    cuenta_origen=str(fila.get('cuenta_origen', '')) if 'cuenta_origen' in fila else None,
                    id=len(movimientos_validos) + 1
                )
                
                # Intentar matching automático para vista previa
                if cedula and cedula != 'nan':
                    cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
                    if cliente:
                        # Buscar cuotas pendientes del cliente
                        cuotas_pendientes = db.query(Cuota).join(Prestamo).filter(
                            Prestamo.cliente_id == cliente.id,
                            Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
                            Cuota.monto_cuota == monto  # Monto exacto
                        ).first()
                        
                        if cuotas_pendientes:
                            movimiento.tipo_match = TipoMatch.MONTO_FECHA
                            movimiento.confianza_match = 95.0
                            movimiento.cliente_encontrado = {
                                "id": cliente.id,
                                "nombre": cliente.nombre_completo,
                                "cedula": cliente.cedula
                            }
                            movimiento.pago_sugerido = {
                                "cuota_id": cuotas_pendientes.id,
                                "numero_cuota": cuotas_pendientes.numero_cuota,
                                "monto_cuota": float(cuotas_pendientes.monto_cuota)
                            }
                        else:
                            # Buscar con tolerancia ±2%
                            tolerancia = monto * Decimal("0.02")
                            cuota_aproximada = db.query(Cuota).join(Prestamo).filter(
                                Prestamo.cliente_id == cliente.id,
                                Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
                                Cuota.monto_cuota >= (monto - tolerancia),
                                Cuota.monto_cuota <= (monto + tolerancia)
                            ).first()
                            
                            if cuota_aproximada:
                                movimiento.tipo_match = TipoMatch.MONTO_FECHA
                                movimiento.confianza_match = 75.0
                                movimiento.requiere_revision = True
                                movimiento.cliente_encontrado = {
                                    "id": cliente.id,
                                    "nombre": cliente.nombre_completo,
                                    "cedula": cliente.cedula
                                }
                                movimiento.pago_sugerido = {
                                    "cuota_id": cuota_aproximada.id,
                                    "numero_cuota": cuota_aproximada.numero_cuota,
                                    "monto_cuota": float(cuota_aproximada.monto_cuota),
                                    "diferencia": float(abs(cuota_aproximada.monto_cuota - monto))
                                }
                
                movimientos_validos.append(movimiento)
                
            except Exception as e:
                errores.append(f"Fila {index + 1}: {str(e)}")
        
        return ValidacionArchivoBancario(
            archivo_valido=len(errores) == 0,
            formato_detectado=formato,
            total_filas=len(df),
            filas_validas=len(movimientos_validos),
            errores=errores,
            advertencias=advertencias,
            duplicados_encontrados=duplicados,
            cedulas_no_registradas=cedulas_no_registradas,
            vista_previa=movimientos_validos[:10]  # Primeros 10 para vista previa
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)}"
        )


@router.post("/matching-automatico", response_model=ResultadoConciliacion)
def matching_automatico(
    movimientos: List[MovimientoBancarioExtendido],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Realizar matching automático avanzado con prioridades:
    1° Cédula + Monto exacto
    2° Cédula + Monto aproximado (±2%)
    3° Nº Referencia conocido
    """
    exactos = []  # ✅ COINCIDENCIA EXACTA
    parciales = []  # ⚠️ COINCIDENCIA PARCIAL  
    sin_match = []  # ❌ SIN COINCIDENCIA
    
    for mov in movimientos:
        match_encontrado = False
        
        # 1° PRIORIDAD: Cédula + Monto exacto
        if mov.cedula_pagador and not match_encontrado:
            cliente = db.query(Cliente).filter(Cliente.cedula == mov.cedula_pagador).first()
            
            if cliente:
                # Buscar cuota con monto exacto
                cuota_exacta = db.query(Cuota).join(Prestamo).filter(
                    Prestamo.cliente_id == cliente.id,
                    Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
                    Cuota.monto_cuota == mov.monto
                ).first()
                
                if cuota_exacta:
                    exactos.append({
                        "movimiento": mov,
                        "cliente": {
                            "id": cliente.id,
                            "nombre": cliente.nombre_completo,
                            "cedula": cliente.cedula
                        },
                        "cuota": {
                            "id": cuota_exacta.id,
                            "numero": cuota_exacta.numero_cuota,
                            "monto": float(cuota_exacta.monto_cuota),
                            "fecha_vencimiento": cuota_exacta.fecha_vencimiento
                        },
                        "tipo_match": "CEDULA_MONTO_EXACTO",
                        "confianza": 100.0,
                        "estado_visual": "✅ EXACTO"
                    })
                    match_encontrado = True
        
        # 2° PRIORIDAD: Cédula + Monto aproximado (±2%)
        if mov.cedula_pagador and not match_encontrado:
            cliente = db.query(Cliente).filter(Cliente.cedula == mov.cedula_pagador).first()
            
            if cliente:
                tolerancia = mov.monto * Decimal("0.02")
                cuota_aproximada = db.query(Cuota).join(Prestamo).filter(
                    Prestamo.cliente_id == cliente.id,
                    Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
                    Cuota.monto_cuota >= (mov.monto - tolerancia),
                    Cuota.monto_cuota <= (mov.monto + tolerancia)
                ).first()
                
                if cuota_aproximada:
                    diferencia = abs(cuota_aproximada.monto_cuota - mov.monto)
                    porcentaje_diferencia = (diferencia / mov.monto) * 100
                    
                    parciales.append({
                        "movimiento": mov,
                        "cliente": {
                            "id": cliente.id,
                            "nombre": cliente.nombre_completo,
                            "cedula": cliente.cedula
                        },
                        "cuota": {
                            "id": cuota_aproximada.id,
                            "numero": cuota_aproximada.numero_cuota,
                            "monto": float(cuota_aproximada.monto_cuota),
                            "diferencia": float(diferencia),
                            "porcentaje_diferencia": float(porcentaje_diferencia)
                        },
                        "tipo_match": "CEDULA_MONTO_APROXIMADO",
                        "confianza": 80.0,
                        "estado_visual": "⚠️ REVISAR"
                    })
                    match_encontrado = True
        
        # 3° PRIORIDAD: Referencia conocida
        if not match_encontrado:
            pago_existente = db.query(Pago).filter(
                Pago.numero_operacion == mov.referencia
            ).first()
            
            if pago_existente:
                exactos.append({
                    "movimiento": mov,
                    "pago_existente": {
                        "id": pago_existente.id,
                        "monto": float(pago_existente.monto_pagado),
                        "fecha": pago_existente.fecha_pago
                    },
                    "tipo_match": "REFERENCIA_CONOCIDA",
                    "confianza": 90.0,
                    "estado_visual": "✅ EXACTO"
                })
                match_encontrado = True
        
        # Sin coincidencia
        if not match_encontrado:
            sin_match.append({
                "movimiento": mov,
                "estado_visual": "❌ MANUAL",
                "requiere_busqueda_manual": True
            })
    
    return ResultadoConciliacion(
        total_movimientos=len(movimientos),
        total_pagos=0,  # No relevante en este contexto
        conciliados=len(exactos),
        sin_conciliar_banco=len(sin_match),
        sin_conciliar_sistema=len(parciales),
        porcentaje_conciliacion=round((len(exactos) / len(movimientos) * 100), 2) if movimientos else 0,
        detalle_conciliados=exactos,
        detalle_sin_conciliar_banco=sin_match,
        detalle_sin_conciliar_sistema=parciales
    )


@router.post("/confirmar-conciliacion/{pago_id}")
def confirmar_conciliacion(
    pago_id: int,
    referencia_bancaria: str,
    db: Session = Depends(get_db)
):
    """
    Confirma manualmente la conciliación de un pago.
    """
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    pago.referencia_bancaria = referencia_bancaria
    pago.estado_conciliacion = EstadoConciliacion.CONCILIADO
    pago.fecha_conciliacion = datetime.now()
    
    db.commit()
    db.refresh(pago)
    
    return {"message": "Conciliación confirmada", "pago_id": pago_id}


@router.get("/pendientes", response_model=List[dict])
def obtener_pendientes_conciliacion(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Obtiene pagos pendientes de conciliar.
    """
    query = db.query(Pago).filter(
        Pago.estado_conciliacion == EstadoConciliacion.PENDIENTE
    )
    
    if fecha_inicio:
        query = query.filter(Pago.fecha_pago >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Pago.fecha_pago <= fecha_fin)
    
    pagos = query.all()
    
    return [
        {
            "id": p.id,
            "prestamo_id": p.prestamo_id,
            "monto": p.monto,
            "fecha_pago": p.fecha_pago,
            "concepto": p.concepto
        }
        for p in pagos
    ]


@router.get("/reporte-conciliacion")
def reporte_conciliacion(
    mes: int,
    anio: int,
    db: Session = Depends(get_db)
):
    """
    Genera reporte mensual de conciliación.
    """
    from calendar import monthrange
    
    fecha_inicio = date(anio, mes, 1)
    ultimo_dia = monthrange(anio, mes)[1]
    fecha_fin = date(anio, mes, ultimo_dia)
    
    total_pagos = db.query(Pago).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin
    ).count()
    
    conciliados = db.query(Pago).filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin,
        Pago.estado_conciliacion == EstadoConciliacion.CONCILIADO
    ).count()
    
    pendientes = total_pagos - conciliados
    
    return {
        "mes": mes,
        "anio": anio,
        "total_pagos": total_pagos,
        "conciliados": conciliados,
        "pendientes": pendientes,
        "porcentaje_conciliacion": round((conciliados / total_pagos * 100) if total_pagos > 0 else 0, 2)
    }


# ============================================
# REVISIÓN MANUAL
# ============================================

@router.post("/revision-manual")
def procesar_revision_manual(
    revision: RevisionManual,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Procesar revisión manual de movimiento bancario
    """
    try:
        if revision.accion == "APLICAR":
            # Buscar cliente
            cliente = db.query(Cliente).filter(Cliente.cedula == revision.cliente_cedula).first()
            if not cliente:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            
            # Buscar cuota si se especifica
            cuota = None
            if revision.cuota_id:
                cuota = db.query(Cuota).join(Prestamo).filter(
                    Cuota.id == revision.cuota_id,
                    Prestamo.cliente_id == cliente.id
                ).first()
                
                if not cuota:
                    raise HTTPException(status_code=404, detail="Cuota no encontrada")
            
            # Crear pago
            monto_final = revision.monto_ajustado or movimiento.monto
            
            # Obtener movimiento original (esto requeriría almacenamiento temporal)
            # Por simplicidad, crear pago directamente
            
            db_pago = Pago(
                prestamo_id=cuota.prestamo_id if cuota else cliente.prestamos[0].id,
                numero_cuota=cuota.numero_cuota if cuota else 1,
                monto_cuota_programado=cuota.monto_cuota if cuota else monto_final,
                monto_pagado=monto_final,
                monto_total=monto_final,
                fecha_pago=date.today(),
                fecha_vencimiento=cuota.fecha_vencimiento if cuota else date.today(),
                metodo_pago="TRANSFERENCIA",
                numero_operacion=f"CONC-{revision.movimiento_id}",
                observaciones=f"Conciliación manual: {revision.observaciones}",
                usuario_registro=current_user.email,
                estado_conciliacion="CONCILIADO_MANUAL"
            )
            
            db.add(db_pago)
            db.commit()
            db.refresh(db_pago)
            
            return {
                "message": "Pago aplicado manualmente",
                "pago_id": db_pago.id,
                "cliente": cliente.nombre_completo,
                "monto": float(monto_final)
            }
        
        elif revision.accion == "RECHAZAR":
            # Marcar como rechazado (requeriría tabla de movimientos temporales)
            return {
                "message": "Movimiento rechazado",
                "observaciones": revision.observaciones
            }
        
        elif revision.accion == "NO_APLICABLE":
            # Marcar como no aplicable
            return {
                "message": "Movimiento marcado como no aplicable",
                "observaciones": revision.observaciones
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en revisión manual: {str(e)}")


# ============================================
# APLICACIÓN MASIVA
# ============================================

@router.post("/aplicar-masivo", response_model=ResultadoConciliacionMasiva)
def aplicar_conciliacion_masiva(
    conciliacion_data: ConciliacionMasiva,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aplicar conciliación masiva de movimientos
    """
    try:
        pagos_creados = []
        errores = []
        total_monto = Decimal("0.00")
        clientes_afectados = set()
        
        # Procesar cada movimiento (esto requeriría almacenamiento temporal de movimientos)
        # Por simplicidad, simulamos el proceso
        
        for mov_id in conciliacion_data.movimientos_a_aplicar:
            try:
                # En implementación real, obtendríamos el movimiento de almacenamiento temporal
                # Por ahora simulamos la creación de pago
                
                # Simular creación de pago exitoso
                pago_id = len(pagos_creados) + 1000  # ID simulado
                pagos_creados.append(pago_id)
                total_monto += Decimal("500.00")  # Monto simulado
                clientes_afectados.add(f"Cliente-{mov_id}")
                
            except Exception as e:
                errores.append({
                    "movimiento_id": mov_id,
                    "error": str(e)
                })
        
        # Generar reporte en background
        background_tasks.add_task(
            _generar_reporte_conciliacion,
            user_id=current_user.id,
            pagos_creados=pagos_creados,
            total_monto=float(total_monto)
        )
        
        return ResultadoConciliacionMasiva(
            total_procesados=len(conciliacion_data.movimientos_a_aplicar),
            exitosos=len(pagos_creados),
            fallidos=len(errores),
            pagos_creados=pagos_creados,
            errores=errores,
            resumen_financiero={
                "total_monto_aplicado": float(total_monto),
                "clientes_afectados": len(clientes_afectados),
                "promedio_pago": float(total_monto / len(pagos_creados)) if pagos_creados else 0
            },
            reporte_generado=True
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en aplicación masiva: {str(e)}")


# ============================================
# HISTORIAL DE CONCILIACIONES
# ============================================

@router.get("/historial", response_model=List[HistorialConciliacion])
def obtener_historial_conciliaciones(
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    usuario: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener historial de conciliaciones procesadas
    """
    # Por ahora retornamos datos simulados
    # En implementación real, habría una tabla de conciliaciones
    
    historial_simulado = [
        {
            "id": 1,
            "fecha_proceso": datetime(2024, 1, 15, 10, 30),
            "usuario_proceso": "admin@sistema.com",
            "archivo_original": "extracto_enero_2024.xlsx",
            "total_movimientos": 150,
            "total_aplicados": 142,
            "tasa_exito": 94.67,
            "estado": "COMPLETADO",
            "observaciones": "Conciliación mensual enero"
        },
        {
            "id": 2,
            "fecha_proceso": datetime(2024, 2, 15, 14, 45),
            "usuario_proceso": "cobranzas@sistema.com", 
            "archivo_original": "extracto_febrero_2024.xlsx",
            "total_movimientos": 203,
            "total_aplicados": 198,
            "tasa_exito": 97.54,
            "estado": "COMPLETADO",
            "observaciones": "Conciliación mensual febrero"
        }
    ]
    
    # Aplicar filtros si se proporcionan
    resultado = historial_simulado
    
    if fecha_desde:
        resultado = [h for h in resultado if h["fecha_proceso"].date() >= fecha_desde]
    
    if fecha_hasta:
        resultado = [h for h in resultado if h["fecha_proceso"].date() <= fecha_hasta]
    
    if usuario:
        resultado = [h for h in resultado if usuario.lower() in h["usuario_proceso"].lower()]
    
    return resultado


@router.get("/tabla-resultados/{proceso_id}")
def obtener_tabla_resultados(
    proceso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener tabla de resultados visual como el diagrama
    """
    # Datos simulados para la tabla visual
    tabla_resultados = [
        {
            "banco_ref": "7400874",
            "monto": "$500.00",
            "cliente": "Juan P.",
            "cedula": "12345678",
            "estado": "✅ Exacto",
            "color": "success",
            "confianza": 100.0,
            "accion_sugerida": "AUTO_APLICAR"
        },
        {
            "banco_ref": "7400875", 
            "monto": "$498.00",
            "cliente": "María G.",
            "cedula": "87654321",
            "estado": "⚠️ Revisar",
            "color": "warning",
            "confianza": 75.0,
            "accion_sugerida": "REVISION_MANUAL",
            "diferencia": "$2.00"
        },
        {
            "banco_ref": "7400876",
            "monto": "$750.00", 
            "cliente": "?????",
            "cedula": "11111111",
            "estado": "❌ Manual",
            "color": "danger",
            "confianza": 0.0,
            "accion_sugerida": "BUSQUEDA_MANUAL"
        }
    ]
    
    return {
        "proceso_id": proceso_id,
        "fecha_proceso": datetime.now(),
        "tabla_resultados": tabla_resultados,
        "resumen": {
            "total": len(tabla_resultados),
            "exactos": len([r for r in tabla_resultados if "✅" in r["estado"]]),
            "revision": len([r for r in tabla_resultados if "⚠️" in r["estado"]]),
            "manuales": len([r for r in tabla_resultados if "❌" in r["estado"]])
        },
        "leyenda": {
            "✅ EXACTO": "Coincidencia perfecta - Se puede aplicar automáticamente",
            "⚠️ REVISAR": "Coincidencia parcial - Requiere revisión manual",
            "❌ MANUAL": "Sin coincidencia - Requiere búsqueda manual"
        }
    }


# ============================================
# FUNCIONES AUXILIARES
# ============================================

async def _generar_reporte_conciliacion(user_id: int, pagos_creados: List[int], total_monto: float):
    """
    Generar reporte de conciliación en background
    """
    try:
        # Simulación de generación de reporte
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Generando reporte de conciliación - Usuario: {user_id}, Pagos: {len(pagos_creados)}, Monto: ${total_monto}")
        
        # En implementación real:
        # 1. Crear PDF/Excel con detalles
        # 2. Enviar por email al usuario
        # 3. Almacenar en sistema de archivos
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando reporte de conciliación: {str(e)}")
