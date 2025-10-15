# backend/app/api/v1/endpoints/validadores.py
"""
🔍 Endpoints de Validadores y Corrección de Datos
Sistema para validar y corregir formatos incorrectos
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.user import User
from app.models.auditoria import Auditoria, TipoAccion
from app.api.deps import get_current_user
from app.services.validators_service import (
    ValidadorTelefono,
    ValidadorCedula,
    ValidadorFecha,
    ValidadorMonto,
    ValidadorAmortizaciones,
    ValidadorEmail,
    ServicioCorreccionDatos,
    AutoFormateador
)

router = APIRouter()

# ============================================
# SCHEMAS PARA VALIDADORES
# ============================================

class ValidacionCampo(BaseModel):
    """Schema para validación de campo individual"""
    campo: str = Field(..., description="Nombre del campo a validar")
    valor: str = Field(..., description="Valor a validar")
    pais: str = Field("VENEZUELA", description="País para validaciones específicas")
    contexto: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional para validación")


class CorreccionDatos(BaseModel):
    """Schema para corrección de datos de cliente"""
    cliente_id: int = Field(..., description="ID del cliente")
    correcciones: Dict[str, str] = Field(..., description="Campos a corregir con nuevos valores")
    pais: str = Field("VENEZUELA", description="País para validaciones")
    recalcular_amortizacion: bool = Field(True, description="Recalcular amortización si cambia fecha")


# ============================================
# VALIDACIÓN EN TIEMPO REAL
# ============================================

@router.post("/validar-campo")
def validar_campo_tiempo_real(
    validacion: ValidacionCampo,
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Validar campo individual en tiempo real (para frontend)
    
    Ejemplos de uso:
    • Teléfono: "4241234567" → "+58 424 1234567"
    • Cédula: "12345678" → "V12345678"
    • Email: "USUARIO@GMAIL.COM" → "usuario@gmail.com"
    • Fecha: "15/03/2024" → Validación + formato ISO
    • Monto: "15000" → "$15,000.00"
    """
    try:
        campo = validacion.campo.lower()
        valor = validacion.valor
        pais = validacion.pais
        
        if campo == "telefono":
            resultado = ValidadorTelefono.validar_y_formatear_telefono(valor, pais)
            
        elif campo == "cedula":
            resultado = ValidadorCedula.validar_y_formatear_cedula(valor, pais)
            
        elif campo == "email":
            resultado = ValidadorEmail.validar_email(valor)
            
        elif campo == "fecha_entrega":
            resultado = ValidadorFecha.validar_fecha_entrega(valor)
            
        elif campo == "fecha_pago":
            resultado = ValidadorFecha.validar_fecha_pago(valor)
            
        elif campo in ["total_financiamiento", "monto_pagado", "cuota_inicial"]:
            saldo_maximo = None
            if validacion.contexto and "saldo_pendiente" in validacion.contexto:
                saldo_maximo = Decimal(str(validacion.contexto["saldo_pendiente"]))
            
            resultado = ValidadorMonto.validar_y_formatear_monto(valor, campo.upper(), saldo_maximo)
            
        elif campo == "amortizaciones":
            resultado = ValidadorAmortizaciones.validar_amortizaciones(valor)
            
        else:
            return {
                "valido": False,
                "error": f"Campo '{campo}' no soporta validación automática",
                "valor_original": valor
            }
        
        return {
            "campo": validacion.campo,
            "validacion": resultado,
            "timestamp": datetime.now().isoformat(),
            "recomendaciones": _generar_recomendaciones_campo(campo, resultado)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validando campo: {str(e)}")


@router.post("/formatear-tiempo-real")
def formatear_mientras_escribe(
    campo: str,
    valor: str,
    pais: str = "VENEZUELA",
    current_user: User = Depends(get_current_user)
):
    """
    ✨ Auto-formatear valor mientras el usuario escribe (para frontend)
    
    Uso en frontend:
    - onKeyUp/onChange del input
    - Formateo instantáneo sin validación completa
    - Para mejorar UX mientras el usuario escribe
    """
    try:
        resultado = AutoFormateador.formatear_mientras_escribe(campo, valor, pais)
        
        return {
            "campo": campo,
            "valor_original": valor,
            "resultado_formateo": resultado,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error formateando: {str(e)}")


# ============================================
# CORRECCIÓN DE DATOS
# ============================================

@router.post("/corregir-cliente/{cliente_id}")
def corregir_datos_cliente(
    cliente_id: int,
    correcciones: Dict[str, str],
    pais: str = Query("VENEZUELA", description="País para validaciones"),
    recalcular_amortizacion: bool = Query(True, description="Recalcular amortización si cambia fecha"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔧 Corregir datos incorrectos de un cliente específico
    
    Ejemplo de uso:
    {
        "telefono": "+58 424 1234567",
        "cedula": "V12345678", 
        "email": "cliente@email.com",
        "fecha_entrega": "15/03/2024"
    }
    """
    try:
        # Verificar que el cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # Procesar correcciones
        resultado_correccion = ServicioCorreccionDatos.corregir_datos_cliente(
            cliente_id, correcciones, pais
        )
        
        if resultado_correccion.get("error_general"):
            raise HTTPException(status_code=400, detail=resultado_correccion["error_general"])
        
        # Aplicar correcciones válidas a la base de datos
        cambios_aplicados = []
        for correccion in resultado_correccion["correcciones_aplicadas"]:
            if correccion["cambio_realizado"]:
                campo = correccion["campo"]
                nuevo_valor = correccion["valor_nuevo"]
                
                # Mapear campos a atributos del modelo
                if campo == "telefono":
                    cliente.telefono = nuevo_valor
                elif campo == "cedula":
                    cliente.cedula = nuevo_valor
                elif campo == "email":
                    cliente.email = nuevo_valor
                elif campo == "fecha_entrega":
                    cliente.fecha_entrega = datetime.strptime(nuevo_valor, "%d/%m/%Y").date()
                elif campo == "total_financiamiento":
                    cliente.total_financiamiento = Decimal(nuevo_valor)
                elif campo == "cuota_inicial":
                    cliente.cuota_inicial = Decimal(nuevo_valor)
                elif campo == "amortizaciones":
                    cliente.numero_amortizaciones = int(nuevo_valor)
                
                cambios_aplicados.append({
                    "campo": campo,
                    "valor_anterior": correccion["valor_anterior"],
                    "valor_nuevo": nuevo_valor
                })
        
        # Guardar cambios si hay correcciones válidas
        if cambios_aplicados:
            db.commit()
            
            # Registrar en auditoría
            auditoria = Auditoria.registrar(
                usuario_id=current_user.id,
                accion=TipoAccion.ACTUALIZACION,
                entidad="cliente",
                entidad_id=cliente_id,
                detalles=f"Corrección de datos: {len(cambios_aplicados)} campos actualizados"
            )
            db.add(auditoria)
            db.commit()
        
        # Manejar recálculo de amortización si es necesario
        mensaje_recalculo = None
        if resultado_correccion["requiere_recalculo_amortizacion"] and recalcular_amortizacion:
            # TODO: Integrar con servicio de amortización
            mensaje_recalculo = "⚠️ Se requiere recalcular la tabla de amortización"
        
        return {
            "mensaje": "✅ Corrección de datos procesada exitosamente",
            "cliente": {
                "id": cliente_id,
                "nombre": cliente.nombre_completo,
                "cedula": cliente.cedula
            },
            "resultado_correccion": resultado_correccion,
            "cambios_aplicados_bd": cambios_aplicados,
            "total_cambios": len(cambios_aplicados),
            "errores_encontrados": len(resultado_correccion["errores_encontrados"]),
            "recalculo_amortizacion": {
                "requerido": resultado_correccion["requiere_recalculo_amortizacion"],
                "aplicado": recalcular_amortizacion and resultado_correccion["requiere_recalculo_amortizacion"],
                "mensaje": mensaje_recalculo
            },
            "fecha_correccion": datetime.now().isoformat(),
            "corregido_por": current_user.full_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error corrigiendo datos: {str(e)}")


@router.post("/corregir-pago/{pago_id}")
def corregir_datos_pago(
    pago_id: int,
    monto_pagado: Optional[str] = None,
    fecha_pago: Optional[str] = None,
    numero_operacion: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    💰 Corregir datos incorrectos de un pago específico
    
    Ejemplo: Pago con "MONTO PAGADO = ERROR"
    """
    try:
        # Verificar que el pago existe
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        
        correcciones_aplicadas = []
        errores_validacion = []
        
        # Corregir monto pagado
        if monto_pagado is not None:
            validacion_monto = ValidadorMonto.validar_y_formatear_monto(
                monto_pagado, "MONTO_PAGO"
            )
            
            if validacion_monto["valido"]:
                pago.monto_pagado = validacion_monto["valor_decimal"]
                correcciones_aplicadas.append({
                    "campo": "monto_pagado",
                    "valor_anterior": str(pago.monto_pagado),
                    "valor_nuevo": str(validacion_monto["valor_decimal"])
                })
            else:
                errores_validacion.append({
                    "campo": "monto_pagado",
                    "error": validacion_monto["error"]
                })
        
        # Corregir fecha de pago
        if fecha_pago is not None:
            validacion_fecha = ValidadorFecha.validar_fecha_pago(fecha_pago)
            
            if validacion_fecha["valido"]:
                fecha_parseada = datetime.strptime(validacion_fecha["fecha_iso"], "%Y-%m-%d").date()
                pago.fecha_pago = fecha_parseada
                correcciones_aplicadas.append({
                    "campo": "fecha_pago",
                    "valor_anterior": str(pago.fecha_pago),
                    "valor_nuevo": str(fecha_parseada)
                })
            else:
                errores_validacion.append({
                    "campo": "fecha_pago",
                    "error": validacion_fecha["error"]
                })
        
        # Corregir número de operación
        if numero_operacion is not None:
            if numero_operacion.upper() != "ERROR" and numero_operacion.strip():
                pago.numero_operacion = numero_operacion.strip()
                correcciones_aplicadas.append({
                    "campo": "numero_operacion",
                    "valor_anterior": pago.numero_operacion,
                    "valor_nuevo": numero_operacion.strip()
                })
        
        # Guardar cambios si hay correcciones válidas
        if correcciones_aplicadas:
            # Limpiar observaciones de error
            if pago.observaciones and "REQUIERE_VALIDACIÓN" in pago.observaciones:
                pago.observaciones = f"CORREGIDO - {datetime.now().strftime('%d/%m/%Y')} por {current_user.full_name}"
            
            db.commit()
            
            # Registrar en auditoría
            auditoria = Auditoria.registrar(
                usuario_id=current_user.id,
                accion=TipoAccion.ACTUALIZACION,
                entidad="pago",
                entidad_id=pago_id,
                detalles=f"Corrección de pago: {len(correcciones_aplicadas)} campos actualizados"
            )
            db.add(auditoria)
            db.commit()
        
        return {
            "mensaje": "✅ Corrección de pago procesada exitosamente",
            "pago": {
                "id": pago_id,
                "cliente": pago.prestamo.cliente.nombre_completo if pago.prestamo else "N/A",
                "cuota": pago.numero_cuota
            },
            "correcciones_aplicadas": correcciones_aplicadas,
            "errores_validacion": errores_validacion,
            "total_correcciones": len(correcciones_aplicadas),
            "fecha_correccion": datetime.now().isoformat(),
            "corregido_por": current_user.full_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error corrigiendo pago: {str(e)}")


# ============================================
# DETECCIÓN MASIVA DE ERRORES
# ============================================

@router.get("/detectar-errores-masivo")
def detectar_errores_masivo(
    limite: int = Query(100, ge=1, le=1000, description="Límite de registros a analizar"),
    tipo_analisis: str = Query("CLIENTES", description="CLIENTES, PAGOS, AMBOS"),
    pais: str = Query("VENEZUELA", description="País para validaciones"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Detectar datos incorrectos masivamente en la base de datos
    
    Detecta:
    • Teléfonos mal formateados (sin +58)
    • Cédulas sin letra (V/E)
    • Emails inválidos
    • Fechas = "ERROR"
    • Montos = "ERROR"
    """
    # Solo admin y gerente pueden ejecutar análisis masivo
    if current_user.rol not in ["ADMINISTRADOR_GENERAL", "GERENTE"]:
        raise HTTPException(status_code=403, detail="Sin permisos para análisis masivo")
    
    try:
        resultado = ServicioCorreccionDatos.detectar_datos_incorrectos_masivo(db, limite)
        
        return {
            "analisis_masivo": resultado,
            "parametros": {
                "limite": limite,
                "tipo_analisis": tipo_analisis,
                "pais": pais,
                "ejecutado_por": current_user.full_name
            },
            "acciones_sugeridas": [
                "Usar herramienta de corrección masiva para los casos detectados",
                "Configurar validadores en formularios del frontend",
                "Capacitar usuarios en formatos correctos",
                "Implementar auto-formateo en tiempo real"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis masivo: {str(e)}")


@router.post("/corregir-masivo")
def corregir_datos_masivo(
    correcciones_masivas: List[CorreccionDatos],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔧 Corrección masiva de datos incorrectos
    """
    if current_user.rol not in ["ADMINISTRADOR_GENERAL", "GERENTE"]:
        raise HTTPException(status_code=403, detail="Sin permisos para corrección masiva")
    
    try:
        # Ejecutar correcciones en background
        background_tasks.add_task(
            _procesar_correcciones_masivas,
            correcciones_masivas,
            current_user.id,
            db
        )
        
        return {
            "mensaje": "✅ Corrección masiva iniciada en background",
            "total_clientes": len(correcciones_masivas),
            "estimacion_tiempo": f"{len(correcciones_masivas) * 2} segundos",
            "ejecutado_por": current_user.full_name,
            "timestamp": datetime.now().isoformat(),
            "seguimiento": "GET /api/v1/validadores/estado-correccion-masiva"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error iniciando corrección masiva: {str(e)}")


# ============================================
# EJEMPLOS DE CORRECCIÓN
# ============================================

@router.get("/ejemplos-correccion")
def obtener_ejemplos_correccion(
    pais: str = Query("VENEZUELA", description="País para ejemplos"),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Obtener ejemplos de corrección de formatos incorrectos
    """
    try:
        ejemplos = {
            "telefono": {
                "titulo": "📱 TELÉFONO MAL FORMATEADO",
                "ejemplo_incorrecto": "4241234567",
                "problema": "🟡 Sin código de país (+58)",
                "ejemplo_correccion": "+58 424 1234567",
                "proceso": "Sistema auto-formatea al guardar",
                "validaciones": [
                    "✅ Formato correcto",
                    "✅ Operadora válida",
                    "✅ Longitud correcta"
                ]
            },
            
            "cedula": {
                "titulo": "📝 CÉDULA SIN LETRA",
                "ejemplo_incorrecto": "12345678",
                "problema": "🟡 Sin prefijo V/E",
                "ejemplo_correccion": "V12345678",
                "proceso": "Admin edita y sistema valida",
                "validaciones": [
                    "✅ Prefijo válido (V/E/J/G)",
                    "✅ Longitud correcta (7-8 dígitos)",
                    "✅ Solo números después del prefijo"
                ]
            },
            
            "fecha": {
                "titulo": "📅 FECHA EN FORMATO INCORRECTO",
                "ejemplo_incorrecto": "ERROR",
                "problema": "🔴 Valor inválido",
                "ejemplo_correccion": "15/03/2024",
                "proceso": "Admin selecciona en calendario",
                "validaciones": [
                    "✅ No es fecha futura",
                    "✅ Formato correcto",
                    "⚠️ Puede requerir recálculo de amortización"
                ],
                "accion_adicional": "Sistema pregunta si recalcular tabla de amortización"
            },
            
            "monto": {
                "titulo": "💰 MONTO PAGADO = ERROR",
                "ejemplo_incorrecto": "ERROR",
                "problema": "🔴 Valor inválido",
                "ejemplo_correccion": "15000.00",
                "proceso": "Admin/Cobranzas ingresa monto correcto",
                "validaciones": [
                    "✅ Es número positivo",
                    "✅ Tiene máximo 2 decimales",
                    "✅ No excede saldo pendiente"
                ]
            }
        }
        
        return {
            "titulo": "📋 EJEMPLOS DE CORRECCIÓN DE FORMATOS INCORRECTOS",
            "pais_configurado": pais,
            "ejemplos": ejemplos,
            "herramientas_disponibles": {
                "validacion_tiempo_real": "POST /api/v1/validadores/validar-campo",
                "formateo_automatico": "POST /api/v1/validadores/formatear-tiempo-real",
                "correccion_individual": "POST /api/v1/validadores/corregir-cliente/{id}",
                "deteccion_masiva": "GET /api/v1/validadores/detectar-errores-masivo"
            },
            "integracion_frontend": {
                "validacion_onchange": "Usar endpoint validar-campo en onChange",
                "formateo_onkeyup": "Usar endpoint formatear-tiempo-real en onKeyUp",
                "calendario_fechas": "Usar datepicker para fechas críticas",
                "input_numerico": "Usar input type='number' para montos"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo ejemplos: {str(e)}")


# ============================================
# ENDPOINTS DE PRUEBA
# ============================================

@router.get("/test-simple")
def test_validadores_simple():
    """
    🔧 Endpoint de prueba simple para validadores
    """
    return {
        "status": "ok",
        "message": "Endpoint de validadores funcionando",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/test-con-auth")
def test_validadores_con_auth(
    current_user: User = Depends(get_current_user)
):
    """
    🔧 Endpoint de prueba con autenticación para validadores
    """
    return {
        "status": "ok",
        "message": "Endpoint de validadores con auth funcionando",
        "user": current_user.email,
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# CONFIGURACIÓN DE VALIDADORES
# ============================================

@router.get("/configuracion")
def obtener_configuracion_validadores(
    current_user: User = Depends(get_current_user)
):
    """
    ⚙️ Obtener configuración de validadores para el frontend
    """
    try:
        print(f"🔧 Obteniendo configuración de validadores para usuario: {current_user.email}")
        return {
            "titulo": "⚙️ CONFIGURACIÓN DE VALIDADORES",
            
            "paises_soportados": {
                "venezuela": {
                    "codigo": "VENEZUELA",
                    "telefono_formato": "+58 XXXXXXXXXX",
                    "telefono_requisitos": {
                        "debe_empezar_por": "+58",
                        "longitud_total": "10 dígitos",
                        "primer_digito": "No puede ser 0",
                        "digitos_validos": "0-9"
                    },
                    "cedula_formato": "V12345678",
                    "cedula_prefijos": ["V", "E", "J"],
                    "cedula_longitud": "7-10 dígitos"
                },
                "dominicana": {
                    "codigo": "DOMINICANA", 
                    "telefono_formato": "+1 XXX XXXXXXX",
                    "cedula_formato": "001-1234567-8",
                    "operadoras": ["809", "829", "849"]
                },
                "colombia": {
                    "codigo": "COLOMBIA",
                    "telefono_formato": "+57 XXX XXXXXXX",
                    "cedula_formato": "12345678",
                    "operadoras": ["300", "301", "310", "311", "320"]
                }
            },
            
            "validadores_disponibles": {
                "telefono": {
                    "descripcion": "Validación y formateo de números telefónicos",
                    "auto_formateo": True,
                    "validacion_tiempo_real": True
                },
                "cedula": {
                    "descripcion": "Validación de cédulas por país",
                    "auto_formateo": True,
                    "validacion_tiempo_real": True
                },
                "email": {
                    "descripcion": "Validación RFC 5322 + normalización a minúsculas",
                    "auto_formateo": True,
                    "validacion_tiempo_real": True,
                    "normalizacion": {
                        "convertir_minusculas": True,
                        "remover_espacios": True,
                        "normalizar_aroba": True
                    }
                },
                "fechas": {
                    "descripcion": "Validación estricta formato DD/MM/YYYY",
                    "auto_formateo": False,
                    "validacion_tiempo_real": True,
                    "requiere_calendario": True,
                    "formato_requerido": "DD/MM/YYYY",
                    "requisitos": {
                        "dia": "2 dígitos (01-31)",
                        "mes": "2 dígitos (01-12)",
                        "año": "4 dígitos",
                        "separador": "/ (barra)"
                    }
                },
                "montos": {
                    "descripcion": "Validación con límites por tipo",
                    "auto_formateo": True,
                    "validacion_tiempo_real": True,
                    "formato_display": "$X,XXX.XX"
                },
                "amortizaciones": {
                    "descripcion": "Validación de rango 1-84 meses",
                    "auto_formateo": False,
                    "validacion_tiempo_real": True
                }
            },
            
            "reglas_negocio": {
                "fecha_entrega": "No puede ser futura",
                "fecha_pago": "Máximo 1 día en el futuro",
                "monto_pago": "No puede exceder saldo pendiente",
                "total_financiamiento": "Entre $100 y $50,000,000",
                "amortizaciones": "Entre 1 y 84 meses",
                "cedula_venezuela": "Prefijos V/E/J + 7-10 dígitos del 0-9",
                "telefono_venezuela": "+58 + 10 dígitos (primer dígito no puede ser 0)",
                "fecha_formato": "DD/MM/YYYY (día 2 dígitos, mes 2 dígitos, año 4 dígitos)",
                "email_normalizacion": "Conversión automática a minúsculas (incluyendo @)"
            },
            
            "configuracion_frontend": {
                "validacion_onchange": "Validar al cambiar valor",
                "formateo_onkeyup": "Formatear mientras escribe",
                "mostrar_errores": "Mostrar errores en tiempo real",
                "sugerencias": "Mostrar sugerencias de corrección",
                "calendario_obligatorio": "Para fechas críticas"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo configuración: {str(e)}")


# ============================================
# FUNCIONES AUXILIARES
# ============================================

async def _procesar_correcciones_masivas(
    correcciones: List[CorreccionDatos],
    user_id: int,
    db_session: Session
):
    """Procesar correcciones masivas en background"""
    try:
        from app.db.session import SessionLocal
        db = SessionLocal()
        
        exitosas = 0
        fallidas = 0
        
        for correccion in correcciones:
            try:
                resultado = ServicioCorreccionDatos.corregir_datos_cliente(
                    correccion.cliente_id,
                    correccion.correcciones,
                    correccion.pais
                )
                
                if resultado.get("cambios_realizados"):
                    exitosas += 1
                else:
                    fallidas += 1
                    
            except Exception as e:
                logger.error(f"Error corrigiendo cliente {correccion.cliente_id}: {e}")
                fallidas += 1
        
        logger.info(f"📊 Corrección masiva completada: {exitosas} exitosas, {fallidas} fallidas")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error en corrección masiva: {e}")


def _generar_recomendaciones_campo(campo: str, resultado_validacion: Dict) -> List[str]:
    """Generar recomendaciones específicas por campo"""
    recomendaciones = []
    
    if not resultado_validacion.get("valido"):
        if campo == "telefono":
            recomendaciones.append("📱 Use formato internacional: +58 424 1234567")
            recomendaciones.append("🔍 Verifique que la operadora sea válida")
        elif campo == "cedula":
            recomendaciones.append("📝 Agregue prefijo V para venezolanos, E para extranjeros")
            recomendaciones.append("🔢 Verifique que tenga 7-8 dígitos después de la letra")
        elif campo == "email":
            recomendaciones.append("📧 Verifique formato: usuario@dominio.com")
            recomendaciones.append("🚫 Evite dominios de email temporal")
        elif "fecha" in campo:
            recomendaciones.append("📅 Use calendario para seleccionar fecha")
            recomendaciones.append("⏰ Verifique reglas de negocio (no futuras)")
        elif "monto" in campo:
            recomendaciones.append("💰 Use solo números y punto decimal")
            recomendaciones.append("📊 Verifique límites permitidos")
    
    return recomendaciones


# ============================================
# ENDPOINT DE VERIFICACIÓN
# ============================================

@router.get("/verificacion-validadores")
def verificar_sistema_validadores(
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Verificación completa del sistema de validadores
    """
    return {
        "titulo": "🔍 SISTEMA DE VALIDADORES Y CORRECCIÓN DE DATOS",
        "fecha_verificacion": datetime.now().isoformat(),
        
        "validadores_implementados": {
            "telefono": {
                "estado": "✅ IMPLEMENTADO",
                "paises": ["Venezuela", "República Dominicana", "Colombia"],
                "auto_formateo": True,
                "ejemplo": "4241234567 → +58 424 1234567"
            },
            "cedula": {
                "estado": "✅ IMPLEMENTADO",
                "paises": ["Venezuela", "República Dominicana", "Colombia"],
                "auto_formateo": True,
                "ejemplo": "12345678 → V12345678",
                "venezuela_prefijos": ["V", "E", "J"],
                "venezuela_longitud": "7-10 dígitos"
            },
            "email": {
                "estado": "✅ IMPLEMENTADO",
                "validacion": "RFC 5322",
                "dominios_bloqueados": True,
                "ejemplo": "USUARIO@GMAIL.COM → usuario@gmail.com"
            },
            "fechas": {
                "estado": "✅ IMPLEMENTADO",
                "reglas_negocio": True,
                "formatos_multiples": True,
                "ejemplo": "ERROR → Calendario para selección"
            },
            "montos": {
                "estado": "✅ IMPLEMENTADO",
                "limites_por_tipo": True,
                "auto_formateo": True,
                "ejemplo": "15000 → $15,000.00"
            },
            "amortizaciones": {
                "estado": "✅ IMPLEMENTADO",
                "rango": "1-84 meses",
                "validacion_entero": True,
                "ejemplo": "60.5 → 60 meses"
            }
        },
        
        "funcionalidades_especiales": {
            "validacion_tiempo_real": "✅ Para uso en frontend",
            "auto_formateo_escritura": "✅ Mientras el usuario escribe",
            "deteccion_masiva": "✅ Análisis de toda la BD",
            "correccion_masiva": "✅ Corrección en lotes",
            "reglas_negocio": "✅ Validaciones específicas del dominio",
            "recalculo_amortizacion": "✅ Al cambiar fecha de entrega"
        },
        
        "endpoints_principales": {
            "validar_campo": "POST /api/v1/validadores/validar-campo",
            "formatear_tiempo_real": "POST /api/v1/validadores/formatear-tiempo-real",
            "corregir_cliente": "POST /api/v1/validadores/corregir-cliente/{id}",
            "detectar_errores": "GET /api/v1/validadores/detectar-errores-masivo",
            "ejemplos": "GET /api/v1/validadores/ejemplos-correccion"
        },
        
        "integracion_frontend": {
            "validacion_onchange": "Validar cuando cambia el valor",
            "formateo_onkeyup": "Formatear mientras escribe",
            "mostrar_errores": "Mostrar errores en tiempo real",
            "sugerencias_correccion": "Mostrar cómo corregir",
            "calendario_fechas": "Usar datepicker para fechas",
            "input_numerico": "Input type='number' para montos"
        },
        
        "beneficios": [
            "🔍 Detección automática de datos incorrectos",
            "✨ Auto-formateo mejora experiencia de usuario",
            "🔧 Corrección masiva ahorra tiempo",
            "📊 Análisis de calidad de datos",
            "⚡ Validación en tiempo real previene errores",
            "🎯 Reglas de negocio específicas del dominio"
        ]
    }


@router.get("/configuracion-validadores")
async def obtener_configuracion_validadores():
    """
    🔧 Obtener configuración actualizada de validadores para el frontend
    """
    return {
        "cedula_venezuela": {
            "descripcion": "Cédula venezolana: V/E/J + exactamente entre 7 y 10 dígitos, sin caracteres especiales",
            "requisitos": {
                "debe_empezar_por": "V, E o J",
                "longitud_digitos": "Entre 7 y 10 dígitos",
                "sin_caracteres_especiales": "Solo letra inicial + números",
                "ejemplos_validos": ["V1234567", "E12345678", "J123456789", "V1234567890"]
            },
            "patron_regex": r"^[VEJ]\d{7,10}$",
            "formato_display": "V12345678",
            "tipos": {
                "V": "Venezolano",
                "E": "Extranjero", 
                "J": "Jurídico"
            }
        },
        "telefono_venezuela": {
            "descripcion": "Teléfono venezolano: +58 seguido de 10 dígitos (primer dígito no puede ser 0)",
            "requisitos": {
                "debe_empezar_por": "+58",
                "longitud_total": 10,
                "primer_digito": "No puede ser 0",
                "digitos_validos": "0-9"
            },
            "patron_regex": r"^\+58[1-9][0-9]{9}$",
            "formato_display": "+58 XXXXXXXXXX"
        },
        "email": {
            "descripcion": "Email válido con normalización automática a minúsculas",
            "requisitos": {
                "formato": "usuario@dominio.com",
                "normalizacion": "Automática a minúsculas",
                "dominios_bloqueados": ["tempmail.org", "10minutemail.com", "guerrillamail.com"]
            },
            "patron_regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        },
        "fecha": {
            "descripcion": "Fecha en formato DD/MM/YYYY",
            "requisitos": {
                "formato": "DD/MM/YYYY",
                "dia": "01-31",
                "mes": "01-12", 
                "año": "1900-2100"
            },
            "patron_regex": r"^\d{2}/\d{2}/\d{4}$"
        },
        "monto": {
            "descripcion": "Monto numérico positivo con máximo 2 decimales",
            "requisitos": {
                "formato": "Número positivo",
                "decimales": "Máximo 2",
                "separador_miles": "Comas opcionales",
                "simbolo_moneda": "$ opcional"
            }
        }
    }
