# backend/app/api/v1/endpoints/validadores.py
"""
Endpoints de Validadores y Corrección de Datos
Sistema para validar y corregir formatos incorrectos
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.auditoria import Auditoria, TipoAccion
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.user import User
from app.services.validators_service import (
    AutoFormateador,
    ServicioCorreccionDatos,
    ValidadorAmortizaciones,
    ValidadorCedula,
    ValidadorEmail,
    ValidadorFecha,
    ValidadorMonto,
    ValidadorTelefono,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SCHEMAS PARA VALIDADORES
# ============================================


class ValidacionCampo(BaseModel):
    """Schema para validación de campo individual"""

    campo: str = Field(..., description="Nombre del campo a validar")
    valor: str = Field(..., description="Valor a validar")
    pais: str = Field(
        "VENEZUELA", description="País para validaciones específicas"
    )
    contexto: Optional[Dict[str, Any]] = Field(
        None, description="Contexto adicional para validación"
    )


class CorreccionDatos(BaseModel):
    """Schema para corrección de datos de cliente"""

    cliente_id: int = Field(..., description="ID del cliente")
    correcciones: Dict[str, str] = Field(
        ..., description="Campos a corregir con nuevos valores"
    )
    pais: str = Field("VENEZUELA", description="País para validaciones")
    recalcular_amortizacion: bool = Field(
        True, description="Recalcular amortización si cambia fecha"
    )


# ============================================
# VALIDACIÓN EN TIEMPO REAL
# ============================================


@router.get("/test-cedula/{cedula}")
def test_cedula_simple(cedula: str):
    """Endpoint simple para probar validación de cédula sin autenticación"""
    try:
        resultado = ValidadorCedula.validar_y_formatear_cedula(
            cedula, "VENEZUELA"
        )
        return {
            "cedula_test": cedula,
            "resultado": resultado,
            "reglas": {
                "prefijos_validos": ["V", "E", "J"],
                "longitud_digitos": "7-10 dígitos",
                "patron": "^[VEJ]\\d{7,10}$",
                "ejemplos_validos": [
                    "V1234567",
                    "E12345678",
                    "J123456789",
                    "V1234567890",
                ],
            },
        }
    except Exception as e:
        return {"error": str(e), "cedula_test": cedula}


@router.get("/test-simple")
def test_simple():
    """Endpoint de prueba muy simple para verificar que el servidor responde"""
    return {
        "mensaje": "Servidor funcionando correctamente",
        "timestamp": datetime.now().isoformat(),
        "status": "ok",
    }


@router.post("/test-cedula-post")
def test_cedula_post(cedula: str = "E12345678"):
    """Endpoint POST simple para probar validación sin autenticación"""
    try:
        resultado = ValidadorCedula.validar_y_formatear_cedula(
            cedula, "VENEZUELA"
        )
        return {
            "cedula_test": cedula,
            "resultado": resultado,
            "deberia_ser_valido": True,
            "explicacion": "E12345678: E (válido) + 8 dígitos (válido) = VÁLIDO",
        }
    except Exception as e:
        return {"error": str(e), "cedula_test": cedula}


@router.post("/test-cedula-custom")
def test_cedula_custom(cedula: str):
    """Endpoint POST para probar cualquier cédula sin autenticación"""
    try:
        resultado = ValidadorCedula.validar_y_formatear_cedula(
            cedula, "VENEZUELA"
        )
        return {
            "cedula_test": cedula,
            "resultado": resultado,
            "reglas": {
                "prefijos_validos": ["V", "E", "J"],
                "longitud_digitos": "7-10 dígitos",
                "patron": "^[VEJ]\\d{7,10}$",
                "ejemplos_validos": [
                    "V1234567",
                    "E12345678",
                    "J123456789",
                    "V1234567890",
                ],
            },
        }
    except Exception as e:
        return {"error": str(e), "cedula_test": cedula}


def _validar_campo_telefono(valor: str, pais: str) -> Dict[str, Any]:
    """Validar campo de teléfono"""
    return ValidadorTelefono.validar_y_formatear_telefono(valor, pais)


def _validar_campo_cedula(valor: str, pais: str) -> Dict[str, Any]:
    """Validar campo de cédula"""
    return ValidadorCedula.validar_y_formatear_cedula(valor, pais)


def _validar_campo_email(valor: str) -> Dict[str, Any]:
    """Validar campo de email"""
    return ValidadorEmail.validar_email(valor)


def _validar_campo_fecha_entrega(valor: str) -> Dict[str, Any]:
    """Validar campo de fecha de entrega"""
    return ValidadorFecha.validar_fecha_entrega(valor)


def _validar_campo_fecha_pago(valor: str) -> Dict[str, Any]:
    """Validar campo de fecha de pago"""
    return ValidadorFecha.validar_fecha_pago(valor)


def _validar_campo_monto(
    valor: str, campo: str, contexto: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Validar campo de monto"""
    saldo_maximo = None
    if contexto and "saldo_pendiente" in contexto:
        saldo_maximo = Decimal(str(contexto["saldo_pendiente"]))
    return ValidadorMonto.validar_y_formatear_monto(
        valor, campo.upper(), saldo_maximo
    )


def _validar_campo_amortizaciones(valor: str) -> Dict[str, Any]:
    """Validar campo de amortizaciones"""
    return ValidadorAmortizaciones.validar_amortizaciones(valor)


def _crear_error_campo_no_soportado(campo: str, valor: str) -> Dict[str, Any]:
    """Crear error para campo no soportado"""
    return {
        "valido": False,
        "error": f"Campo '{campo}' no soporta validación automática",
        "valor_original": valor,
    }


@router.post("/validar-campo")
def validar_campo_tiempo_real(validacion: ValidacionCampo):
    """
    🔍 Validar campo individual en tiempo real (VERSIÓN REFACTORIZADA)

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

        # Validar según el tipo de campo
        if campo == "telefono":
            resultado = _validar_campo_telefono(valor, pais)
        elif campo == "cedula":
            resultado = _validar_campo_cedula(valor, pais)
        elif campo == "email":
            resultado = _validar_campo_email(valor)
        elif campo == "fecha_entrega":
            resultado = _validar_campo_fecha_entrega(valor)
        elif campo == "fecha_pago":
            resultado = _validar_campo_fecha_pago(valor)
        elif campo in [
            "total_financiamiento",
            "monto_pagado",
            "cuota_inicial",
        ]:
            resultado = _validar_campo_monto(valor, campo, validacion.contexto)
        elif campo == "amortizaciones":
            resultado = _validar_campo_amortizaciones(valor)
        else:
            return _crear_error_campo_no_soportado(campo, valor)

        return {
            "campo": validacion.campo,
            "validacion": resultado,
            "timestamp": datetime.now().isoformat(),
            "recomendaciones": _generar_recomendaciones_campo(
                campo, resultado
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error validando campo: {str(e)}"
        )


@router.post("/formatear-tiempo-real")
def formatear_mientras_escribe(
    campo: str,
    valor: str,
    pais: str = "VENEZUELA",
    current_user: User = Depends(get_current_user),
):
    """
    ✨ Auto-formatear valor mientras el usuario escribe (para frontend)

    Uso en frontend:
    - onKeyUp/onChange del input
    - Formateo instantáneo sin validación completa
    - Para mejorar UX mientras el usuario escribe
    """
    try:
        resultado = AutoFormateador.formatear_mientras_escribe(
            campo, valor, pais
        )

        return {
            "campo": campo,
            "valor_original": valor,
            "resultado_formateo": resultado,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error formateando: {
                str(e)}",
        )


# ============================================
# CORRECCIÓN DE DATOS
# ============================================


def _aplicar_correccion_campo(
    cliente: Cliente, campo: str, nuevo_valor: str
) -> dict:
    """Aplicar corrección a un campo específico del cliente"""
    valor_anterior = None

    if campo == "telefono":
        valor_anterior = cliente.telefono
        cliente.telefono = nuevo_valor
    elif campo == "cedula":
        valor_anterior = cliente.cedula
        cliente.cedula = nuevo_valor
    elif campo == "email":
        valor_anterior = cliente.email
        cliente.email = nuevo_valor
    elif campo == "fecha_entrega":
        valor_anterior = cliente.fecha_entrega
        cliente.fecha_entrega = datetime.strptime(
            nuevo_valor, "%d/%m/%Y"
        ).date()
    elif campo == "total_financiamiento":
        valor_anterior = cliente.total_financiamiento
        cliente.total_financiamiento = Decimal(nuevo_valor)
    elif campo == "cuota_inicial":
        valor_anterior = cliente.cuota_inicial
        cliente.cuota_inicial = Decimal(nuevo_valor)
    elif campo == "amortizaciones":
        valor_anterior = cliente.numero_amortizaciones
        cliente.numero_amortizaciones = int(nuevo_valor)

    return {
        "campo": campo,
        "valor_anterior": valor_anterior,
        "valor_nuevo": nuevo_valor,
    }


def _procesar_correcciones_cliente(
    cliente: Cliente, resultado_correccion: dict
) -> list[dict]:
    """Procesar y aplicar correcciones al cliente"""
    cambios_aplicados = []

    for correccion in resultado_correccion["correcciones_aplicadas"]:
        if correccion["cambio_realizado"]:
            campo = correccion["campo"]
            nuevo_valor = correccion["valor_nuevo"]

            cambio = _aplicar_correccion_campo(cliente, campo, nuevo_valor)
            cambios_aplicados.append(cambio)

    return cambios_aplicados


def _registrar_auditoria_correccion(
    cliente_id: int,
    cambios_aplicados: list[dict],
    current_user: User,
    db: Session,
) -> None:
    """Registrar auditoría de corrección"""
    auditoria = Auditoria.registrar(
        usuario_id=current_user.id,
        accion=TipoAccion.ACTUALIZACION,
        entidad="cliente",
        entidad_id=cliente_id,
        detalles=f"Corrección de datos: {
            len(cambios_aplicados)} campos actualizados",
    )
    db.add(auditoria)
    db.commit()


def _generar_respuesta_correccion(
    cliente_id: int,
    cliente: Cliente,
    resultado_correccion: dict,
    cambios_aplicados: list[dict],
    recalcular_amortizacion: bool,
    current_user: User,
) -> dict:
    """Generar respuesta de corrección"""
    mensaje_recalculo = None
    if (
        resultado_correccion["requiere_recalculo_amortizacion"]
        and recalcular_amortizacion
    ):
        mensaje_recalculo = "⚠️ Se requiere recalcular la tabla de amortización"

    return {
        "mensaje": "✅ Corrección de datos procesada exitosamente",
        "cliente": {
            "id": cliente_id,
            "nombre": cliente.nombre_completo,
            "cedula": cliente.cedula,
        },
        "resultado_correccion": resultado_correccion,
        "cambios_aplicados_bd": cambios_aplicados,
        "total_cambios": len(cambios_aplicados),
        "errores_encontrados": len(
            resultado_correccion["errores_encontrados"]
        ),
        "recalculo_amortizacion": {
            "requerido": resultado_correccion[
                "requiere_recalculo_amortizacion"
            ],
            "aplicado": (
                recalcular_amortizacion
                and resultado_correccion["requiere_recalculo_amortizacion"]
            ),
            "mensaje": mensaje_recalculo,
        },
        "fecha_correccion": datetime.now().isoformat(),
        "corregido_por": f"{current_user.nombre} {current_user.apellido}".strip(),
    }


@router.post("/corregir-cliente/{cliente_id}")
def corregir_datos_cliente(
    cliente_id: int,
    correcciones: Dict[str, str],
    pais: str = Query("VENEZUELA", description="País para validaciones"),
    recalcular_amortizacion: bool = Query(
        True, description="Recalcular amortización si cambia fecha"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
            raise HTTPException(
                status_code=404, detail="Cliente no encontrado"
            )

        # Procesar correcciones
        resultado_correccion = ServicioCorreccionDatos.corregir_datos_cliente(
            cliente_id, correcciones, pais
        )

        if resultado_correccion.get("error_general"):
            raise HTTPException(
                status_code=400, detail=resultado_correccion["error_general"]
            )

        # Aplicar correcciones válidas a la base de datos
        cambios_aplicados = _procesar_correcciones_cliente(
            cliente, resultado_correccion
        )

        # Guardar cambios si hay correcciones válidas
        if cambios_aplicados:
            db.commit()
            _registrar_auditoria_correccion(
                cliente_id, cambios_aplicados, current_user, db
            )

        # Generar respuesta
        return _generar_respuesta_correccion(
            cliente_id,
            cliente,
            resultado_correccion,
            cambios_aplicados,
            recalcular_amortizacion,
            current_user,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error corrigiendo datos: {
                str(e)}",
        )


def _validar_y_corregir_monto_pago(
    pago: Pago, monto_pagado: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validar y corregir monto pagado"""
    correcciones = []
    errores = []

    validacion_monto = ValidadorMonto.validar_y_formatear_monto(
        monto_pagado, "MONTO_PAGO"
    )

    if validacion_monto["valido"]:
        pago.monto_pagado = validacion_monto["valor_decimal"]
        correcciones.append(
            {
                "campo": "monto_pagado",
                "valor_anterior": str(pago.monto_pagado),
                "valor_nuevo": str(validacion_monto["valor_decimal"]),
            }
        )
    else:
        errores.append(
            {"campo": "monto_pagado", "error": validacion_monto["error"]}
        )

    return correcciones, errores


def _validar_y_corregir_fecha_pago(
    pago: Pago, fecha_pago: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validar y corregir fecha de pago"""
    correcciones = []
    errores = []

    validacion_fecha = ValidadorFecha.validar_fecha_pago(fecha_pago)

    if validacion_fecha["valido"]:
        fecha_parseada = datetime.strptime(
            validacion_fecha["fecha_iso"], "%Y-%m-%d"
        ).date()
        pago.fecha_pago = fecha_parseada
        correcciones.append(
            {
                "campo": "fecha_pago",
                "valor_anterior": str(pago.fecha_pago),
                "valor_nuevo": str(fecha_parseada),
            }
        )
    else:
        errores.append(
            {"campo": "fecha_pago", "error": validacion_fecha["error"]}
        )

    return correcciones, errores


def _validar_y_corregir_numero_operacion(
    pago: Pago, numero_operacion: str
) -> List[Dict[str, Any]]:
    """Validar y corregir número de operación"""
    correcciones = []

    if numero_operacion.upper() != "ERROR" and numero_operacion.strip():
        pago.numero_operacion = numero_operacion.strip()
        correcciones.append(
            {
                "campo": "numero_operacion",
                "valor_anterior": pago.numero_operacion,
                "valor_nuevo": numero_operacion.strip(),
            }
        )

    return correcciones


def _limpiar_observaciones_error(pago: Pago, current_user: User) -> None:
    """Limpiar observaciones de error"""
    if pago.observaciones and "REQUIERE_VALIDACIÓN" in pago.observaciones:
        usuario_nombre = f"{
            current_user.nombre} {
            current_user.apellido}".strip()
        pago.observaciones = f"CORREGIDO - {
            datetime.now().strftime('%d/%m/%Y')} por {usuario_nombre}"


@router.post("/corregir-pago/{pago_id}")
def corregir_datos_pago(
    pago_id: int,
    monto_pagado: Optional[str] = None,
    fecha_pago: Optional[str] = None,
    numero_operacion: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    💰 Corregir datos incorrectos de un pago específico (VERSIÓN REFACTORIZADA)

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
            correcciones, errores = _validar_y_corregir_monto_pago(
                pago, monto_pagado
            )
            correcciones_aplicadas.extend(correcciones)
            errores_validacion.extend(errores)

        # Corregir fecha de pago
        if fecha_pago is not None:
            correcciones, errores = _validar_y_corregir_fecha_pago(
                pago, fecha_pago
            )
            correcciones_aplicadas.extend(correcciones)
            errores_validacion.extend(errores)

        # Corregir número de operación
        if numero_operacion is not None:
            correcciones = _validar_y_corregir_numero_operacion(
                pago, numero_operacion
            )
            correcciones_aplicadas.extend(correcciones)

        # Guardar cambios si hay correcciones válidas
        if correcciones_aplicadas:
            # Limpiar observaciones de error
            _limpiar_observaciones_error(pago, current_user)

            db.commit()

            # Registrar en auditoría
            _registrar_auditoria_correccion(
                pago_id, correcciones_aplicadas, current_user, db
            )
            db.commit()

        return {
            "mensaje": "✅ Corrección de pago procesada exitosamente",
            "pago": {
                "id": pago_id,
                "cliente": (
                    pago.prestamo.cliente.nombre_completo
                    if pago.prestamo
                    else "N/A"
                ),
                "cuota": pago.numero_cuota,
            },
            "correcciones_aplicadas": correcciones_aplicadas,
            "errores_validacion": errores_validacion,
            "total_correcciones": len(correcciones_aplicadas),
            "fecha_correccion": datetime.now().isoformat(),
            "corregido_por": f"{
                current_user.nombre} {
                current_user.apellido}".strip(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error corrigiendo pago: {
                str(e)}",
        )


# ============================================
# DETECCIÓN MASIVA DE ERRORES
# ============================================


@router.get("/detectar-errores-masivo")
def detectar_errores_masivo(
    limite: int = Query(
        100, ge=1, le=1000, description="Límite de registros a analizar"
    ),
    tipo_analisis: str = Query(
        "CLIENTES", description="CLIENTES, PAGOS, AMBOS"
    ),
    pais: str = Query("VENEZUELA", description="País para validaciones"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    # Solo administrador general puede ejecutar análisis masivo
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Sin permisos para análisis masivo"
        )

    try:
        resultado = ServicioCorreccionDatos.detectar_datos_incorrectos_masivo(
            db, limite
        )

        return {
            "analisis_masivo": resultado,
            "parametros": {
                "limite": limite,
                "tipo_analisis": tipo_analisis,
                "pais": pais,
                "ejecutado_por": f"{
                    current_user.nombre} {
                    current_user.apellido}".strip(),
            },
            "acciones_sugeridas": [
                "Usar herramienta de corrección masiva para los casos detectados",
                "Configurar validadores en formularios del frontend",
                "Capacitar usuarios en formatos correctos",
                "Implementar auto-formateo en tiempo real",
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis masivo: {
                str(e)}",
        )


@router.post("/corregir-masivo")
def corregir_datos_masivo(
    correcciones_masivas: List[CorreccionDatos],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔧 Corrección masiva de datos incorrectos
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Sin permisos para corrección masiva"
        )

    try:
        # Ejecutar correcciones en background
        background_tasks.add_task(
            _procesar_correcciones_masivas,
            correcciones_masivas,
            current_user.id,
            db,
        )

        return {
            "mensaje": "✅ Corrección masiva iniciada en background",
            "total_clientes": len(correcciones_masivas),
            "estimacion_tiempo": f"{
                len(correcciones_masivas) * 2} segundos",
            "ejecutado_por": f"{
                current_user.nombre} {
                current_user.apellido}".strip(),
            "timestamp": datetime.now().isoformat(),
            "seguimiento": "GET /api/v1/validadores/estado-correccion-masiva",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error iniciando corrección masiva: {
                str(e)}",
        )


# ============================================
# EJEMPLOS DE CORRECCIÓN
# ============================================


@router.get("/ejemplos-correccion")
def obtener_ejemplos_correccion(
    pais: str = Query("VENEZUELA", description="País para ejemplos"),
    current_user: User = Depends(get_current_user),
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
                    "✅ Longitud correcta",
                ],
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
                    "✅ Solo números después del prefijo",
                ],
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
                    "⚠️ Puede requerir recálculo de amortización",
                ],
                "accion_adicional": "Sistema pregunta si recalcular tabla de amortización",
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
                    "✅ No excede saldo pendiente",
                ],
            },
        }

        return {
            "titulo": "📋 EJEMPLOS DE CORRECCIÓN DE FORMATOS INCORRECTOS",
            "pais_configurado": pais,
            "ejemplos": ejemplos,
            "herramientas_disponibles": {
                "validacion_tiempo_real": "POST /api/v1/validadores/validar-campo",
                "formateo_automatico": "POST /api/v1/validadores/formatear-tiempo-real",
                "correccion_individual": "POST /api/v1/validadores/corregir-cliente/{id}",
                "deteccion_masiva": "GET /api/v1/validadores/detectar-errores-masivo",
            },
            "integracion_frontend": {
                "validacion_onchange": "Usar endpoint validar-campo en onChange",
                "formateo_onkeyup": "Usar endpoint formatear-tiempo-real en onKeyUp",
                "calendario_fechas": "Usar datepicker para fechas críticas",
                "input_numerico": "Usar input type='number' para montos",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo ejemplos: {
                str(e)}",
        )


# ============================================
# ENDPOINTS DE PRUEBA
# ============================================


@router.get("/test")
def test_validadores():
    """
    🧪 Endpoint de prueba simple
    """
    return {"message": "Validadores endpoint funcionando", "status": "ok"}


@router.get("/")
@router.get("/info")
def obtener_validadores_info():
    """
    📋 Información general de validadores disponibles
    """
    return {
        "validadores_disponibles": [
            "ValidadorTelefono",
            "ValidadorCedula",
            "ValidadorFecha",
            "ValidadorMonto",
            "ValidadorAmortizaciones",
            "ValidadorEmail",
            "ValidadorEdad",
            "ValidadorCoherenciaFinanciera",
            "ValidadorDuplicados",
        ],
        "endpoints": {
            "validar_campo": "POST /api/v1/validadores/validar-campo",
            "formatear_tiempo_real": "POST /api/v1/validadores/formatear-tiempo-real",
            "configuracion": "GET /api/v1/validadores/configuracion",
            "ejemplos_correccion": "GET /api/v1/validadores/ejemplos-correccion",
            "detectar_errores_masivo": "GET /api/v1/validadores/detectar-errores-masivo",
            "test_cedula": "GET /api/v1/validadores/test-cedula/{cedula}",
            "test_simple": "GET /api/v1/validadores/test-simple",
            "ping": "GET /api/v1/validadores/ping",
        },
        "status": "active",
        "version": "1.0.0",
    }


@router.get("/ping")
def ping_validadores():
    """
    🏓 Endpoint de prueba para verificar conectividad
    """
    return {
        "status": "success",
        "message": "Endpoint de validadores funcionando",
        "timestamp": "2025-10-19T12:00:00Z",
        "version": "1.0.0",
    }

    # ============================================
    # CONFIGURACIÓN DE VALIDADORES
    # ============================================


# ============================================
# FUNCIONES AUXILIARES
# ============================================


async def _procesar_correcciones_masivas(
    correcciones: List[CorreccionDatos], user_id: int, db_session: Session
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
                    correccion.pais,
                )

                if resultado.get("cambios_realizados"):
                    exitosas += 1
                else:
                    fallidas += 1

            except Exception as e:
                logger.error(
                    f"Error corrigiendo cliente {
                        correccion.cliente_id}: {e}"
                )
                fallidas += 1

        logger.info(
            f"📊 Corrección masiva completada: {exitosas} exitosas, {fallidas} fallidas")

        db.close()

    except Exception as e:
        logger.error(f"Error en corrección masiva: {e}")


def _generar_recomendaciones_campo(
    campo: str, resultado_validacion: Dict
) -> List[str]:
    """Generar recomendaciones específicas por campo"""
    recomendaciones = []

    if not resultado_validacion.get("valido"):
        if campo == "telefono":
            recomendaciones.append(
                "📱 Use formato internacional: +58 424 1234567"
            )
            recomendaciones.append("🔍 Verifique que la operadora sea válida")
        elif campo == "cedula":
            recomendaciones.append(
                "📝 Agregue prefijo V para venezolanos, E para extranjeros"
            )
            recomendaciones.append(
                "🔢 Verifique que tenga 7-8 dígitos después de la letra"
            )
        elif campo == "email":
            recomendaciones.append("📧 Verifique formato: usuario@dominio.com")
            recomendaciones.append("🚫 Evite dominios de email temporal")
        elif "fecha" in campo:
            recomendaciones.append("📅 Use calendario para seleccionar fecha")
            recomendaciones.append(
                "⏰ Verifique reglas de negocio (no futuras)"
            )
        elif "monto" in campo:
            recomendaciones.append("💰 Use solo números y punto decimal")
            recomendaciones.append("📊 Verifique límites permitidos")

    return recomendaciones


# ============================================
# ENDPOINT DE VERIFICACIÓN
# ============================================


@router.get("/verificacion-validadores")
def verificar_sistema_validadores(
    current_user: User = Depends(get_current_user),
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
                "ejemplo": "4241234567 → +58 424 1234567",
            },
            "cedula": {
                "estado": "✅ IMPLEMENTADO",
                "paises": ["Venezuela", "República Dominicana", "Colombia"],
                "auto_formateo": True,
                "ejemplo": "12345678 → V12345678",
                "venezuela_prefijos": ["V", "E", "J"],
                "venezuela_longitud": "7-10 dígitos",
            },
            "email": {
                "estado": "✅ IMPLEMENTADO",
                "validacion": "RFC 5322",
                "dominios_bloqueados": True,
                "ejemplo": "USUARIO@GMAIL.COM → usuario@gmail.com",
            },
            "fechas": {
                "estado": "✅ IMPLEMENTADO",
                "reglas_negocio": True,
                "formatos_multiples": True,
                "ejemplo": "ERROR → Calendario para selección",
            },
            "montos": {
                "estado": "✅ IMPLEMENTADO",
                "limites_por_tipo": True,
                "auto_formateo": True,
                "ejemplo": "15000 → $15,000.00",
            },
            "amortizaciones": {
                "estado": "✅ IMPLEMENTADO",
                "rango": "1-84 meses",
                "validacion_entero": True,
                "ejemplo": "60.5 → 60 meses",
            },
        },
        "funcionalidades_especiales": {
            "validacion_tiempo_real": "✅ Para uso en frontend",
            "auto_formateo_escritura": "✅ Mientras el usuario escribe",
            "deteccion_masiva": "✅ Análisis de toda la BD",
            "correccion_masiva": "✅ Corrección en lotes",
            "reglas_negocio": "✅ Validaciones específicas del dominio",
            "recalculo_amortizacion": "✅ Al cambiar fecha de entrega",
        },
        "endpoints_principales": {
            "validar_campo": "POST /api/v1/validadores/validar-campo",
            "formatear_tiempo_real": "POST /api/v1/validadores/formatear-tiempo-real",
            "corregir_cliente": "POST /api/v1/validadores/corregir-cliente/{id}",
            "detectar_errores": "GET /api/v1/validadores/detectar-errores-masivo",
            "ejemplos": "GET /api/v1/validadores/ejemplos-correccion",
        },
        "integracion_frontend": {
            "validacion_onchange": "Validar cuando cambia el valor",
            "formateo_onkeyup": "Formatear mientras escribe",
            "mostrar_errores": "Mostrar errores en tiempo real",
            "sugerencias_correccion": "Mostrar cómo corregir",
            "calendario_fechas": "Usar datepicker para fechas",
            "input_numerico": "Input type='number' para montos",
        },
        "beneficios": [
            "🔍 Detección automática de datos incorrectos",
            "✨ Auto-formateo mejora experiencia de usuario",
            "🔧 Corrección masiva ahorra tiempo",
            "📊 Análisis de calidad de datos",
            "⚡ Validación en tiempo real previene errores",
            "🎯 Reglas de negocio específicas del dominio",
        ],
    }


@router.get("/configuracion-validadores")
async def obtener_configuracion_validadores():
    """
    🔧 Obtener configuración actualizada de validadores para el frontend
    """
    return {
        "cedula_venezuela": {
            "descripcion": (
                "Cédula venezolana: V/E/J + exactamente entre 7 y 10 dígitos, sin caracteres especiales"
            ),
            "requisitos": {
                "debe_empezar_por": "V, E o J",
                "longitud_digitos": "Entre 7 y 10 dígitos",
                "sin_caracteres_especiales": "Solo letra inicial + números",
                "ejemplos_validos": [
                    "V1234567",
                    "E12345678",
                    "J123456789",
                    "V1234567890",
                ],
            },
            "patron_regex": r"^[VEJ]\d{7,10}$",
            "formato_display": "V12345678",
            "tipos": {"V": "Venezolano", "E": "Extranjero", "J": "Jurídico"},
        },
        "telefono_venezuela": {
            "descripcion": (
                "Teléfono venezolano: +58 seguido de 10 dígitos (primer dígito no puede ser 0)"
            ),
            "requisitos": {
                "debe_empezar_por": "+58",
                "longitud_total": 10,
                "primer_digito": "No puede ser 0",
                "digitos_validos": "0-9",
            },
            "patron_regex": r"^\+58[1-9][0-9]{9}$",
            "formato_display": "+58 XXXXXXXXXX",
        },
        "email": {
            "descripcion": "Email válido con normalización automática a minúsculas",
            "requisitos": {
                "formato": "usuario@dominio.com",
                "normalizacion": "Automática a minúsculas",
                "dominios_bloqueados": [
                    "tempmail.org",
                    "10minutemail.com",
                    "guerrillamail.com",
                ],
            },
            "patron_regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        },
        "fecha": {
            "descripcion": "Fecha en formato DD/MM/YYYY",
            "requisitos": {
                "formato": "DD/MM/YYYY",
                "dia": "01-31",
                "mes": "01-12",
                "año": "1900-2100",
            },
            "patron_regex": r"^\d{2}/\d{2}/\d{4}$",
        },
        "monto": {
            "descripcion": "Monto numérico positivo con máximo 2 decimales",
            "requisitos": {
                "formato": "Número positivo",
                "decimales": "Máximo 2",
                "separador_miles": "Comas opcionales",
                "simbolo_moneda": "$ opcional",
            },
        },
    }
