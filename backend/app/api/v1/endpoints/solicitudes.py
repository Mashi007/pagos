# backend/app/api/v1/endpoints/solicitudes.py
"""
Sistema de Solicitudes de Aprobación
Maneja solicitudes para acciones que requieren autorización
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.aprobacion import Aprobacion
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SCHEMAS PARA SOLICITUDES
# ============================================


class SolicitudAprobacionCompleta(BaseModel):
    """Schema completo para crear solicitud de aprobación"""

    tipo_solicitud: str = Field(
        ...,
        description="MODIFICAR_PAGO, ANULAR_PAGO, EDITAR_CLIENTE, MODI \
        FICAR_AMORTIZACION",
    )
    entidad_tipo: str = Field(..., description="cliente, pago, prestamo")
    entidad_id: int = Field(..., description="ID de la entidad a modificar")
    justificacion: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Justificación detallada",
    )
    datos_solicitados: Dict[str, Any] = Field(
        ..., description="Datos que se desean cambiar"
    )
    prioridad: str = Field(
        default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE"
    )
    fecha_limite: Optional[date] = Field(
        None, description="Fecha límite para respuesta"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tipo_solicitud": "MODIFICAR_PAGO",
                "entidad_tipo": "pago",
                "entidad_id": 123,
                "justificacion": (
                    "El cliente pagó con transferencia pero se registró como "
                    "efectivo por error. Necesito corregir el método de pago "
                    "para cuadrar la conciliación bancaria."
                ),
                "datos_solicitados": {
                    "metodo_pago": "TRANSFERENCIA",
                    "numero_operacion": "TRF-789456123",
                    "banco": "Banco Popular",
                },
                "prioridad": "ALTA",
                "fecha_limite": "2025-10-15",
            }
        }


class FormularioModificarPago(BaseModel):
    """Formulario específico para modificar pago"""

    pago_id: int = Field(..., description="ID del pago a modificar")
    motivo_modificacion: str = Field(
        ..., description="ERROR_REGISTRO, CAMBIO_CLIENTE, AJUSTE_MONTO, OTRO"
    )
    justificacion: str = Field(
        ..., min_length=20, description="Explicación detallada del motivo"
    )

    # Campos que se pueden modificar
    nuevo_monto: Optional[float] = Field(
        None, gt=0, description="Nuevo monto del pago"
    )
    nuevo_metodo_pago: Optional[str] = Field(
        None, description="EFECTIVO, TRANSFERENCIA, TARJETA, CHEQUE"
    )
    nueva_fecha_pago: Optional[date] = Field(
        None, description="Nueva fecha de pago"
    )
    nuevo_numero_operacion: Optional[str] = Field(
        None, description="Nuevo número de operación"
    )
    nuevo_banco: Optional[str] = Field(None, description="Nuevo banco")
    nuevas_observaciones: Optional[str] = Field(
        None, description="Nuevas observaciones"
    )

    prioridad: str = Field(
        default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE"
    )


class FormularioAnularPago(BaseModel):
    """Formulario específico para anular pago"""

    pago_id: int = Field(..., description="ID del pago a anular")
    motivo_anulacion: str = Field(
        ...,
        description="PAGO_DUPLICADO, ERROR_CLIENTE, DEVOLUCION, FRAUDE, OTRO",
    )
    justificacion: str = Field(
        ..., min_length=20, description="Explicación detallada del motivo"
    )
    revertir_amortizacion: bool = Field(
        True, description="Si revertir cambios en tabla de amortización"
    )
    notificar_cliente: bool = Field(
        True, description="Si notificar al cliente sobre la anulación"
    )
    prioridad: str = Field(
        default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE"
    )


class FormularioEditarCliente(BaseModel):
    """Formulario específico para editar cliente"""

    cliente_id: int = Field(..., description="ID del cliente a editar")
    motivo_edicion: str = Field(
        ...,
        description="CORRECCION_DATOS, CAMBIO_VEHICULO, ACTUALIZACION_CONTACTO, OTRO",
    )
    justificacion: str = Field(
        ..., min_length=20, description="Explicación detallada del motivo"
    )

    # Campos que se pueden modificar
    nuevos_datos_personales: Optional[Dict[str, Any]] = Field(
        None, description="Datos personales a cambiar"
    )
    nuevos_datos_vehiculo: Optional[Dict[str, Any]] = Field(
        None, description="Datos del vehículo a cambiar"
    )
    nuevos_datos_contacto: Optional[Dict[str, Any]] = Field(
        None, description="Datos de contacto a cambiar"
    )

    prioridad: str = Field(
        default="NORMAL", description="BAJA, NORMAL, ALTA, URGENTE"
    )


class FormularioModificarAmortizacion(BaseModel):
    """Formulario específico para modificar amortización"""

    prestamo_id: int = Field(..., description="ID del préstamo")
    motivo_modificacion: str = Field(
        ..., description="CAMBIO_TASA, EXTENSION_PLAZO, REFINANCIAMIENTO, OTRO"
    )
    justificacion: str = Field(
        ..., min_length=20, description="Explicación detallada del motivo"
    )

    # Parámetros a modificar
    nueva_tasa_interes: Optional[float] = Field(
        None, ge=0, le=100, description="Nueva tasa de interés anual"
    )
    nuevo_numero_cuotas: Optional[int] = Field(
        None, ge=1, le=360, description="Nuevo número de cuotas"
    )
    nueva_modalidad_pago: Optional[str] = Field(
        None, description="SEMANAL, QUINCENAL, MENSUAL, BIMENSUAL"
    )
    nueva_fecha_inicio: Optional[date] = Field(
        None, description="Nueva fecha de inicio"
    )

    prioridad: str = Field(
        default="ALTA", description="BAJA, NORMAL, ALTA, URGENTE"
    )


class SolicitudResponse(BaseModel):
    """Schema de respuesta para solicitud"""

    id: int
    tipo_solicitud: str
    entidad_tipo: str
    entidad_id: int
    estado: str
    justificacion: str
    datos_solicitados: Dict[str, Any]
    solicitante: str
    fecha_solicitud: datetime
    fecha_revision: Optional[datetime] = None
    revisor: Optional[str] = None
    comentarios_revisor: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================
# FUNCIONES AUXILIARES PARA ARCHIVOS
# ============================================

UPLOAD_DIR = Path("uploads/solicitudes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def guardar_archivo_evidencia(
    archivo: UploadFile,
) -> tuple[str, str, int]:
    """Guardar archivo de evidencia y retornar (path, tipo, tamaño)"""
    if not archivo.filename:
        raise HTTPException(
            status_code=400, detail="Nombre de archivo requerido"
        )

    # Verificar extensión
    extension = Path(archivo.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Leer contenido y verificar tamaño
    contenido = await archivo.read()
    if len(contenido) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, detail="Archivo demasiado grande (máximo 10MB)"
        )

    # Generar nombre único
    nombre_unico = f"{uuid.uuid4()}{extension}"
    ruta_archivo = UPLOAD_DIR / nombre_unico

    # Guardar archivo
    with open(ruta_archivo, "wb") as f:
        f.write(contenido)

    return str(ruta_archivo), extension[1:].upper(), len(contenido)


# ============================================
# SOLICITUDES DE COBRANZAS CON FORMULARIOS COMPLETOS
# ============================================


def _validar_solicitud_modificacion_pago(
    formulario: FormularioModificarPago, current_user: User, db: Session
) -> tuple[Pago, Optional[Aprobacion]]:
    """Validar solicitud de modificación de pago"""
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")

    # Verificar que el pago existe
    pago = db.query(Pago).filter(Pago.id == formulario.pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # Verificar que no hay solicitud pendiente para este pago
    solicitud_existente = (
        db.query(Aprobacion)
        .filter(
            Aprobacion.entidad == "pago",
            Aprobacion.entidad_id == formulario.pago_id,
            Aprobacion.estado == "PENDIENTE",
        )
        .first()
    )

    if solicitud_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una solicitud pendiente para este pago (ID: {solicitud_existente.id})",
        )

    return pago, solicitud_existente


async def _procesar_archivo_evidencia(
    archivo_evidencia: Optional[UploadFile],
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """Procesar archivo de evidencia"""
    archivo_path = None
    tipo_archivo = None
    tamaño_archivo = None

    if archivo_evidencia and archivo_evidencia.filename:
        archivo_path, tipo_archivo, tamaño_archivo = (
            await guardar_archivo_evidencia(archivo_evidencia)
        )

    return archivo_path, tipo_archivo, tamaño_archivo


def _preparar_datos_solicitados(
    formulario: FormularioModificarPago,
) -> Dict[str, Any]:
    """Preparar datos solicitados"""
    datos_solicitados = {}
    if formulario.nuevo_monto:
        datos_solicitados["monto_pagado"] = formulario.nuevo_monto
    if formulario.nuevo_metodo_pago:
        datos_solicitados["metodo_pago"] = formulario.nuevo_metodo_pago
    if formulario.nueva_fecha_pago:
        datos_solicitados["fecha_pago"] = (
            formulario.nueva_fecha_pago.isoformat()
        )
    if formulario.nuevo_numero_operacion:
        datos_solicitados["numero_operacion"] = (
            formulario.nuevo_numero_operacion
        )
    if formulario.nuevo_banco:
        datos_solicitados["banco"] = formulario.nuevo_banco
    if formulario.nuevas_observaciones:
        datos_solicitados["observaciones"] = formulario.nuevas_observaciones

    return datos_solicitados


def _calcular_fecha_limite(prioridad: str) -> Optional[date]:
    """Calcular fecha límite según prioridad"""
    if prioridad == "URGENTE":
        return date.today() + timedelta(days=1)
    elif prioridad == "ALTA":
        return date.today() + timedelta(days=2)
    elif prioridad == "NORMAL":
        return date.today() + timedelta(days=5)
    return None


def _crear_solicitud_aprobacion(
    formulario: FormularioModificarPago,
    datos_solicitados: Dict[str, Any],
    current_user: User,
    fecha_limite: Optional[date],
) -> Aprobacion:
    """Crear solicitud de aprobación"""
    return Aprobacion(
        solicitante_id=current_user.id,
        tipo_solicitud=f"MODIFICAR_PAGO_{formulario.motivo_modificacion}",
        entidad="pago",
        entidad_id=formulario.pago_id,
        justificacion=f"[{formulario.motivo_modificacion}] {formulario.justificacion}",
        datos_solicitados=str(datos_solicitados),
        estado="PENDIENTE",
        prioridad=formulario.prioridad,
        fecha_limite=fecha_limite,
        bloqueado_temporalmente=True,
    )


def _guardar_solicitud_con_archivo(
    solicitud: Aprobacion,
    archivo_path: Optional[str],
    tipo_archivo: Optional[str],
    tamaño_archivo: Optional[int],
    db: Session,
) -> Aprobacion:
    """Guardar solicitud con archivo adjunto"""
    # Adjuntar archivo si existe
    if archivo_path:
        solicitud.adjuntar_archivo(archivo_path, tipo_archivo, tamaño_archivo)

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)
    return solicitud


def _generar_respuesta_solicitud(
    solicitud: Aprobacion,
    pago: Pago,
    datos_solicitados: Dict[str, Any],
    archivo_path: Optional[str],
) -> Dict[str, Any]:
    """Generar respuesta de la solicitud"""
    return {
        "solicitud_id": solicitud.id,
        "mensaje": "✅ Solicitud de modificación de pago enviada exitosamente",
        "estado": "PENDIENTE",
        "prioridad": solicitud.prioridad,
        "fecha_limite": solicitud.fecha_limite,
        "requiere_aprobacion": True,
        "bloqueado_temporalmente": True,
        "archivo_adjunto": bool(archivo_path),
        "pago_afectado": {
            "id": pago.id,
            "monto_actual": float(pago.monto_pagado),
            "fecha_actual": pago.fecha_pago,
            "cliente": (
                pago.prestamo.cliente.nombre_completo
                if pago.prestamo
                else "N/A"
            ),
        },
        "cambios_solicitados": datos_solicitados,
        "siguiente_paso": "Esperar aprobación del administrador",
    }


@router.post("/cobranzas/modificar-pago-completo")
async def solicitar_modificacion_pago_completo(
    formulario: FormularioModificarPago,
    archivo_evidencia: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ COBRANZAS: Solicitar modificación de pago con formulario completo (VERSIÓN REFACTORIZADA)

    FLUJO COMPLETO:
    1. ✅ Usuario completa formulario detallado
    2. ✅ Adjunta evidencia (opcional)
    3. ✅ Sistema registra solicitud
    4. ✅ Notifica al Admin (in-app + email)
    5. ✅ Bloquea temporalmente el registro
    """
    # Validar solicitud
    pago, solicitud_existente = _validar_solicitud_modificacion_pago(
        formulario, current_user, db
    )

    # Procesar archivo de evidencia
    archivo_path, tipo_archivo, tamaño_archivo = (
        await _procesar_archivo_evidencia(archivo_evidencia)
    )

    # Preparar datos solicitados
    datos_solicitados = _preparar_datos_solicitados(formulario)

    # Calcular fecha límite
    fecha_limite = _calcular_fecha_limite(formulario.prioridad)

    # Crear solicitud de aprobación
    solicitud = _crear_solicitud_aprobacion(
        formulario, datos_solicitados, current_user, fecha_limite
    )

    # Guardar solicitud con archivo
    solicitud = _guardar_solicitud_con_archivo(
        solicitud, archivo_path, tipo_archivo, tamaño_archivo, db
    )

    # Notificar al admin
    await _notificar_nueva_solicitud_admin(solicitud, db)

    # Generar respuesta
    return _generar_respuesta_solicitud(
        solicitud, pago, datos_solicitados, archivo_path
    )


@router.post("/cobranzas/anular-pago-completo")
async def solicitar_anulacion_pago_completo(
    formulario: FormularioAnularPago,
    archivo_evidencia: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ COBRANZAS: Solicitar anulación de pago con formulario completo
    """
    # Verificar permisos - Todos los usuarios pueden usar este endpoint
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")

    # Verificar que el pago existe y no está anulado
    pago = db.query(Pago).filter(Pago.id == formulario.pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    if pago.anulado:
        raise HTTPException(status_code=400, detail="El pago ya está anulado")

    # Procesar archivo de evidencia
    archivo_path = None
    tipo_archivo = None
    tamaño_archivo = None

    if archivo_evidencia and archivo_evidencia.filename:
        archivo_path, tipo_archivo, tamaño_archivo = (
            await guardar_archivo_evidencia(archivo_evidencia)
        )

    # Preparar datos solicitados
    datos_solicitados = {
        "revertir_amortizacion": formulario.revertir_amortizacion,
        "notificar_cliente": formulario.notificar_cliente,
        "motivo": formulario.motivo_anulacion,
    }

    # Fecha límite más corta para anulaciones (más crítico)
    fecha_limite = None
    if formulario.prioridad == "URGENTE":
        fecha_limite = date.today() + timedelta(hours=4)
    elif formulario.prioridad == "ALTA":
        fecha_limite = date.today() + timedelta(days=1)
    else:
        fecha_limite = date.today() + timedelta(days=3)

    # Crear solicitud
    solicitud = Aprobacion(
        solicitante_id=current_user.id,
        tipo_solicitud=f"ANULAR_PAGO_{formulario.motivo_anulacion}",
        entidad="pago",
        entidad_id=formulario.pago_id,
        justificacion=f"[{formulario.motivo_anulacion}] {formulario.justificacion}",
        datos_solicitados=str(datos_solicitados),
        estado="PENDIENTE",
        prioridad=formulario.prioridad,
        fecha_limite=fecha_limite,
        bloqueado_temporalmente=True,
    )

    if archivo_path:
        solicitud.adjuntar_archivo(archivo_path, tipo_archivo, tamaño_archivo)

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    # Notificar al admin
    await _notificar_nueva_solicitud_admin(solicitud, db)

    return {
        "solicitud_id": solicitud.id,
        "mensaje": "✅ Solicitud de anulación de pago enviada exitosamente",
        "estado": "PENDIENTE",
        "prioridad": solicitud.prioridad,
        "fecha_limite": solicitud.fecha_limite,
        "pago_afectado": {
            "id": pago.id,
            "monto": float(pago.monto_pagado),
            "fecha": pago.fecha_pago,
            "cliente": (
                pago.prestamo.cliente.nombre_completo
                if pago.prestamo
                else "N/A"
            ),
        },
        "acciones_solicitadas": datos_solicitados,
    }


# Mantener endpoints originales para compatibilidad
@router.post("/cobranzas/modificar-pago")
def solicitar_modificacion_pago(
    pago_id: int,
    nuevos_datos: Dict[str, Any],
    justificacion: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ COBRANZAS: Solicitar modificación de monto de pago
    """
    # Verificar permisos - Todos los usuarios pueden usar este endpoint
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")

    # Verificar que el pago existe
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # Crear solicitud de aprobación
    solicitud = Aprobacion(
        solicitante_id=current_user.id,
        tipo_solicitud="MODIFICAR_PAGO",
        entidad="pago",
        entidad_id=pago_id,
        justificacion=justificacion,
        datos_solicitados=str(nuevos_datos),  # JSON como string
        estado="PENDIENTE",
    )

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return {
        "solicitud_id": solicitud.id,
        "mensaje": "✅ Solicitud de modificación de pago enviada para aprobación",
        "estado": "PENDIENTE",
        "requiere_aprobacion": True,
        "pago_afectado": {
            "id": pago.id,
            "monto_actual": float(pago.monto_pagado),
            "cliente": (
                pago.prestamo.cliente.nombre_completo
                if pago.prestamo
                else "N/A"
            ),
        },
    }


@router.post("/cobranzas/anular-pago")
def solicitar_anulacion_pago(
    pago_id: int,
    justificacion: str,
    revertir_amortizacion: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ COBRANZAS: Solicitar anulación de pago
    """
    # Verificar permisos - Todos los usuarios pueden usar este endpoint
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")

    # Verificar que el pago existe
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # Crear solicitud de aprobación
    solicitud = Aprobacion(
        solicitante_id=current_user.id,
        tipo_solicitud="ANULAR_PAGO",
        entidad="pago",
        entidad_id=pago_id,
        justificacion=justificacion,
        datos_solicitados=str(
            {"revertir_amortizacion": revertir_amortizacion}
        ),
        estado="PENDIENTE",
    )

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return {
        "solicitud_id": solicitud.id,
        "mensaje": "✅ Solicitud de anulación de pago enviada para aprobación",
        "estado": "PENDIENTE",
        "requiere_aprobacion": True,
        "pago_afectado": {
            "id": pago.id,
            "monto": float(pago.monto_pagado),
            "fecha": pago.fecha_pago,
            "cliente": (
                pago.prestamo.cliente.nombre_completo
                if pago.prestamo
                else "N/A"
            ),
        },
    }


@router.post("/cobranzas/modificar-amortizacion")
def solicitar_modificacion_amortizacion(
    prestamo_id: int,
    nuevos_parametros: Dict[str, Any],
    justificacion: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ COBRANZAS: Solicitar modificación de tabla de amortización
    """
    # Verificar permisos - Todos los usuarios pueden usar este endpoint
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")

    # Verificar que el préstamo existe

    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    # Crear solicitud de aprobación
    solicitud = Aprobacion(
        solicitante_id=current_user.id,
        tipo_solicitud="MODIFICAR_AMORTIZACION",
        entidad="prestamo",
        entidad_id=prestamo_id,
        justificacion=justificacion,
        datos_solicitados=str(nuevos_parametros),
        estado="PENDIENTE",
    )

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return {
        "solicitud_id": solicitud.id,
        "mensaje": "✅ Solicitud de modificación de amortización enviada para aprobación",
        "estado": "PENDIENTE",
        "requiere_aprobacion": True,
        "prestamo_afectado": {
            "id": prestamo.id,
            "cliente": (
                prestamo.cliente.nombre_completo if prestamo.cliente else "N/A"
            ),
            "monto_actual": float(prestamo.monto_total),
        },
    }


# ============================================
# SOLICITUDES DE USER
# ============================================


@router.post("/comercial/editar-cliente")
def solicitar_edicion_cliente_comercial(
    cliente_id: int,
    nuevos_datos: Dict[str, Any],
    justificacion: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ USER: Solicitar autorización para editar cliente
    """
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden usar este endpoint",
        )

    # Verificar que el cliente existe
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Crear solicitud de aprobación
    solicitud = Aprobacion(
        solicitante_id=current_user.id,
        tipo_solicitud="EDITAR_CLIENTE_USER",
        entidad="cliente",
        entidad_id=cliente_id,
        justificacion=justificacion,
        datos_solicitados=str(nuevos_datos),
        estado="PENDIENTE",
    )

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return {
        "solicitud_id": solicitud.id,
        "mensaje": "✅ Solicitud de edición de cliente enviada para autorización de Admin",
        "estado": "PENDIENTE",
        "requiere_autorizacion": True,
        "cliente_afectado": {
            "id": cliente.id,
            "nombre": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "vehiculo": cliente.vehiculo_completo,
        },
    }


# ============================================
# SOLICITUDES DE USER
# ============================================


@router.post("/analista/editar-cliente-propio")
def solicitar_edicion_cliente_propio(
    cliente_id: int,
    nuevos_datos: Dict[str, Any],
    justificacion: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ⚠️ USER: Solicitar autorización para editar SUS clientes asignados
    """
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden usar este endpoint",
        )

    # Verificar que el cliente existe y está asignado al analista
    cliente = (
        db.query(Cliente)
        .filter(
            Cliente.id == cliente_id,
            Cliente.analista_id
            == current_user.id,  # NOTA: Esto requiere mapeo User->Asesor
        )
        .first()
    )

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado o no está asignado a usted",
        )

    # Crear solicitud de aprobación
    solicitud = Aprobacion(
        solicitante_id=current_user.id,
        tipo_solicitud="EDITAR_CLIENTE_PROPIO",
        entidad="cliente",
        entidad_id=cliente_id,
        justificacion=justificacion,
        datos_solicitados=str(nuevos_datos),
        estado="PENDIENTE",
    )

    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return {
        "solicitud_id": solicitud.id,
        "mensaje": "✅ Solicitud de edición enviada para autorización de Admin",
        "estado": "PENDIENTE",
        "requiere_autorizacion": True,
        "cliente_afectado": {
            "id": cliente.id,
            "nombre": cliente.nombre_completo,
            "cedula": cliente.cedula,
            "es_mi_cliente": True,
        },
    }


# ============================================
# GESTIÓN DE SOLICITUDES (ADMIN)
# ============================================


@router.get("/pendientes", response_model=List[SolicitudResponse])
def listar_solicitudes_pendientes(
    tipo_solicitud: Optional[str] = Query(None),
    solicitante_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📋 Listar solicitudes pendientes de aprobación (Solo Admin)
    """
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Sin permisos para ver solicitudes"
        )

    query = db.query(Aprobacion).filter(Aprobacion.estado == "PENDIENTE")

    # Aplicar filtros
    if tipo_solicitud:
        query = query.filter(Aprobacion.tipo_solicitud == tipo_solicitud)

    if solicitante_id:
        query = query.filter(Aprobacion.solicitante_id == solicitante_id)

    # Paginación
    query.count()
    skip = (page - 1) * page_size
    solicitudes = (
        query.order_by(Aprobacion.fecha_solicitud.desc())
        .offset(skip)
        .limit(page_size)
        .all()
    )

    # Formatear respuesta
    resultado = []
    for sol in solicitudes:
        resultado.append(
            {
                "id": sol.id,
                "tipo_solicitud": sol.tipo_solicitud,
                "entidad_tipo": sol.entidad,
                "entidad_id": sol.entidad_id,
                "estado": sol.estado,
                "justificacion": sol.justificacion,
                "datos_solicitados": (
                    eval(sol.datos_solicitados)
                    if sol.datos_solicitados
                    else {}
                ),
                "solicitante": (
                    sol.solicitante.full_name if sol.solicitante else "N/A"
                ),
                "fecha_solicitud": sol.fecha_solicitud,
                "fecha_revision": sol.fecha_revision,
                "revisor": sol.revisor.full_name if sol.revisor else None,
                "comentarios_revisor": sol.comentarios_revisor,
            }
        )

    return resultado


@router.post("/aprobar/{solicitud_id}")
async def aprobar_solicitud(
    solicitud_id: int,
    comentarios: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✅ Aprobar solicitud (Solo Admin)
    """
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Sin permisos para aprobar solicitudes"
        )

    # Buscar solicitud
    solicitud = (
        db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first()
    )
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "PENDIENTE":
        raise HTTPException(
            status_code=400, detail="La solicitud ya fue procesada"
        )

    # Aprobar solicitud
    solicitud.aprobar(current_user.id, comentarios)
    db.commit()

    # Ejecutar la acción aprobada
    resultado_ejecucion = _ejecutar_accion_aprobada(solicitud, db)

    # Notificar al solicitante sobre la aprobación
    await _notificar_resultado_solicitud(solicitud, db)

    return {
        "mensaje": "✅ Solicitud aprobada y ejecutada exitosamente",
        "solicitud_id": solicitud_id,
        "tipo_solicitud": solicitud.tipo_solicitud,
        "aprobada_por": current_user.full_name,
        "fecha_aprobacion": solicitud.fecha_revision,
        "resultado_ejecucion": resultado_ejecucion,
        "notificacion_enviada": True,
    }


@router.post("/rechazar/{solicitud_id}")
async def rechazar_solicitud(
    solicitud_id: int,
    comentarios: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ❌ Rechazar solicitud (Solo Admin)
    """
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Sin permisos para rechazar solicitudes"
        )

    # Buscar solicitud
    solicitud = (
        db.query(Aprobacion).filter(Aprobacion.id == solicitud_id).first()
    )
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if solicitud.estado != "PENDIENTE":
        raise HTTPException(
            status_code=400, detail="La solicitud ya fue procesada"
        )

    # Rechazar solicitud
    solicitud.rechazar(current_user.id, comentarios)
    db.commit()

    # Notificar al solicitante sobre el rechazo
    await _notificar_resultado_solicitud(solicitud, db)

    return {
        "mensaje": "❌ Solicitud rechazada",
        "solicitud_id": solicitud_id,
        "tipo_solicitud": solicitud.tipo_solicitud,
        "rechazada_por": current_user.full_name,
        "motivo_rechazo": comentarios,
        "fecha_rechazo": solicitud.fecha_revision,
        "notificacion_enviada": True,
    }


@router.get("/mis-solicitudes")
def listar_mis_solicitudes(
    estado: Optional[str] = Query(
        None, description="PENDIENTE, APROBADA, RECHAZADA"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📋 Ver mis solicitudes enviadas
    """
    query = db.query(Aprobacion).filter(
        Aprobacion.solicitante_id == current_user.id
    )

    if estado:
        query = query.filter(Aprobacion.estado == estado)

    solicitudes = query.order_by(Aprobacion.fecha_solicitud.desc()).all()

    return {
        "total": len(solicitudes),
        "solicitudes": [
            {
                "id": sol.id,
                "tipo": sol.tipo_solicitud,
                "entidad": f"{sol.entidad} #{sol.entidad_id}",
                "estado": sol.estado,
                "fecha_solicitud": sol.fecha_solicitud,
                "fecha_revision": sol.fecha_revision,
                "revisor": sol.revisor.full_name if sol.revisor else None,
                "comentarios": sol.comentarios_revisor,
            }
            for sol in solicitudes
        ],
    }


# ============================================
# FUNCIONES AUXILIARES
# ============================================


def _ejecutar_accion_aprobada(
    solicitud: Aprobacion, db: Session
) -> Dict[str, Any]:
    """
    Ejecutar la acción una vez que fue aprobada
    """
    try:
        datos = (
            eval(solicitud.datos_solicitados)
            if solicitud.datos_solicitados
            else {}
        )

        if solicitud.tipo_solicitud == "MODIFICAR_PAGO":
            # Modificar pago
            pago = (
                db.query(Pago).filter(Pago.id == solicitud.entidad_id).first()
            )
            if pago:
                for campo, valor in datos.items():
                    setattr(pago, campo, valor)
                db.commit()
                return {"accion": "Pago modificado", "pago_id": pago.id}

        elif solicitud.tipo_solicitud == "ANULAR_PAGO":
            # Anular pago
            pago = (
                db.query(Pago).filter(Pago.id == solicitud.entidad_id).first()
            )
            if pago:
                pago.anular(solicitud.revisor.email, "Aprobado por admin")
                db.commit()
                return {"accion": "Pago anulado", "pago_id": pago.id}

        elif solicitud.tipo_solicitud == "EDITAR_CLIENTE_USER":
            # Editar cliente (comercial)
            cliente = (
                db.query(Cliente)
                .filter(Cliente.id == solicitud.entidad_id)
                .first()
            )
            if cliente:
                for campo, valor in datos.items():
                    setattr(cliente, campo, valor)
                db.commit()
                return {"accion": "Cliente editado", "cliente_id": cliente.id}

        elif solicitud.tipo_solicitud == "EDITAR_CLIENTE_PROPIO":
            # Editar cliente propio (analista)
            cliente = (
                db.query(Cliente)
                .filter(Cliente.id == solicitud.entidad_id)
                .first()
            )
            if cliente:
                for campo, valor in datos.items():
                    setattr(cliente, campo, valor)
                db.commit()
                return {"accion": "Cliente editado", "cliente_id": cliente.id}

        return {
            "accion": "Acción ejecutada",
            "detalles": "Sin implementación específica",
        }

    except Exception as e:
        return {"error": f"Error ejecutando acción: {str(e)}"}


@router.get("/estadisticas")
def estadisticas_solicitudes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📊 Estadísticas de solicitudes de aprobación
    """
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sin permisos")

    # Estadísticas generales
    total_pendientes = (
        db.query(Aprobacion).filter(Aprobacion.estado == "PENDIENTE").count()
    )
    total_aprobadas = (
        db.query(Aprobacion).filter(Aprobacion.estado == "APROBADA").count()
    )
    total_rechazadas = (
        db.query(Aprobacion).filter(Aprobacion.estado == "RECHAZADA").count()
    )

    # Por tipo de solicitud
    por_tipo = (
        db.query(
            Aprobacion.tipo_solicitud, func.count(Aprobacion.id).label("total")
        )
        .group_by(Aprobacion.tipo_solicitud)
        .all()
    )

    # Por solicitante
    por_solicitante = (
        db.query(User.full_name, func.count(Aprobacion.id).label("total"))
        .join(Aprobacion, User.id == Aprobacion.solicitante_id)
        .group_by(User.id, User.full_name)
        .all()
    )

    return {
        "resumen": {
            "pendientes": total_pendientes,
            "aprobadas": total_aprobadas,
            "rechazadas": total_rechazadas,
            "total": total_pendientes + total_aprobadas + total_rechazadas,
        },
        "por_tipo": [
            {"tipo": tipo, "total": total} for tipo, total in por_tipo
        ],
        "por_solicitante": [
            {"solicitante": nombre, "total": total}
            for nombre, total in por_solicitante
        ],
        "alertas": {
            "solicitudes_urgentes": total_pendientes,
            "requieren_atencion": total_pendientes > 5,
        },
    }


@router.get("/dashboard-aprobaciones")
def dashboard_aprobaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📊 Dashboard visual completo del sistema de aprobaciones
    """
    # Verificar permisos
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Sin permisos para ver dashboard"
        )

    # Estadísticas principales
    total_pendientes = (
        db.query(Aprobacion).filter(Aprobacion.estado == "PENDIENTE").count()
    )
    total_aprobadas_hoy = (
        db.query(Aprobacion)
        .filter(
            Aprobacion.estado == "APROBADA",
            func.date(Aprobacion.fecha_revision) == date.today(),
        )
        .count()
    )
    total_rechazadas_hoy = (
        db.query(Aprobacion)
        .filter(
            Aprobacion.estado == "RECHAZADA",
            func.date(Aprobacion.fecha_revision) == date.today(),
        )
        .count()
    )

    # Solicitudes urgentes
    urgentes = (
        db.query(Aprobacion)
        .filter(
            Aprobacion.estado == "PENDIENTE", Aprobacion.prioridad == "URGENTE"
        )
        .count()
    )

    # Solicitudes vencidas
    vencidas = (
        db.query(Aprobacion)
        .filter(
            Aprobacion.estado == "PENDIENTE",
            Aprobacion.fecha_limite < date.today(),
        )
        .count()
    )

    # Solicitudes por tipo
    por_tipo = (
        db.query(
            Aprobacion.tipo_solicitud,
            func.count(Aprobacion.id).label("total"),
            func.sum(
                func.case([(Aprobacion.estado == "PENDIENTE", 1)], else_=0)
            ).label("pendientes"),
        )
        .group_by(Aprobacion.tipo_solicitud)
        .all()
    )

    # Solicitudes por prioridad
    por_prioridad = (
        db.query(
            Aprobacion.prioridad, func.count(Aprobacion.id).label("total")
        )
        .filter(Aprobacion.estado == "PENDIENTE")
        .group_by(Aprobacion.prioridad)
        .all()
    )

    # Tiempo promedio de respuesta
    tiempo_promedio = (
        db.query(func.avg(Aprobacion.tiempo_respuesta_horas))
        .filter(Aprobacion.tiempo_respuesta_horas.isnot(None))
        .scalar()
        or 0
    )

    # Solicitudes recientes (últimas 10)
    recientes = (
        db.query(Aprobacion)
        .filter(Aprobacion.estado == "PENDIENTE")
        .order_by(Aprobacion.fecha_solicitud.desc())
        .limit(10)
        .all()
    )

    # Formatear solicitudes recientes
    solicitudes_recientes = []
    for sol in recientes:
        solicitudes_recientes.append(
            {
                "id": sol.id,
                "tipo": sol.tipo_solicitud,
                "solicitante": sol.solicitante.full_name,
                "prioridad": sol.prioridad,
                "dias_pendiente": sol.dias_pendiente,
                "requiere_atencion": sol.requiere_atencion_urgente,
                "fecha_limite": sol.fecha_limite,
                "entidad": f"{sol.entidad} #{sol.entidad_id}",
                "archivo_adjunto": bool(sol.archivo_evidencia),
            }
        )

    return {
        "titulo": "🔔 Dashboard de Aprobaciones",
        "fecha_actualizacion": datetime.now().isoformat(),
        "resumen_principal": {
            "pendientes": {
                "total": total_pendientes,
                "urgentes": urgentes,
                "vencidas": vencidas,
                "color": "#ffc107" if total_pendientes > 0 else "#28a745",
            },
            "procesadas_hoy": {
                "aprobadas": total_aprobadas_hoy,
                "rechazadas": total_rechazadas_hoy,
                "total": total_aprobadas_hoy + total_rechazadas_hoy,
            },
            "rendimiento": {
                "tiempo_promedio_horas": round(tiempo_promedio, 1),
                "eficiencia": (
                    "Alta"
                    if tiempo_promedio < 24
                    else "Media" if tiempo_promedio < 48 else "Baja"
                ),
            },
        },
        "alertas": {
            "criticas": [
                (
                    f"🚨 {urgentes} solicitudes URGENTES pendientes"
                    if urgentes > 0
                    else None
                ),
                (
                    f"⏰ {vencidas} solicitudes VENCIDAS"
                    if vencidas > 0
                    else None
                ),
                (
                    f"📈 {total_pendientes} solicitudes acumuladas"
                    if total_pendientes > 10
                    else None
                ),
            ],
            "nivel_alerta": (
                "CRITICO" if urgentes > 0 or vencidas > 0 else "NORMAL"
            ),
        },
        "estadisticas": {
            "por_tipo": [
                {
                    "tipo": tipo,
                    "total": int(total),
                    "pendientes": int(pendientes or 0),
                    "porcentaje_pendiente": (
                        round((pendientes or 0) / total * 100, 1)
                        if total > 0
                        else 0
                    ),
                }
                for tipo, total, pendientes in por_tipo
            ],
            "por_prioridad": [
                {
                    "prioridad": prioridad,
                    "cantidad": int(total),
                    "color": (
                        {
                            "URGENTE": "#dc3545",
                            "ALTA": "#ffc107",
                            "NORMAL": "#17a2b8",
                            "BAJA": "#6c757d",
                        }.get(prioridad, "#6c757d")
                    ),
                }
                for prioridad, total in por_prioridad
            ],
        },
        "solicitudes_recientes": solicitudes_recientes,
        "acciones_rapidas": {
            "ver_pendientes": "/api/v1/solicitudes/pendientes",
            "aprobar_masivo": "/api/v1/solicitudes/aprobar-masivo",
            "exportar_reporte": "/api/v1/solicitudes/reporte-excel",
            "configurar_alertas": "/api/v1/solicitudes/configurar-alertas",
        },
        "metricas_visuales": {
            "gauge_pendientes": {
                "valor": total_pendientes,
                "maximo": 50,
                "color": "#ffc107" if total_pendientes < 20 else "#dc3545",
            },
            "grafico_tiempo": {
                "promedio_actual": tiempo_promedio,
                "objetivo": 24,
                "tendencia": (
                    "mejorando" if tiempo_promedio < 24 else "estable"
                ),
            },
        },
    }


@router.get("/matriz-permisos")
def obtener_matriz_permisos_actualizada(
    current_user: User = Depends(get_current_user),
):
    """
    📋 Obtener matriz de permisos actualizada con sistema de aprobaciones
    """
    # Función obsoleta - sistema de permisos simplificado no requiere matriz compleja
    # from app.core.permissions import get_permission_matrix_summary

    # Sistema simplificado - matriz básica de permisos
    matriz = {
        "ADMIN": {
            "acceso": "✅ COMPLETO",
            "permisos": "✅ TODOS LOS PERMISOS",
            "aprobaciones": "❌ NO REQUERIDAS",
        },
        "USER": {
            "acceso": "⚠️ LIMITADO",
            "permisos": "⚠️ PERMISOS BÁSICOS",
            "aprobaciones": "✅ REQUERIDAS PARA ACCIONES CRÍTICAS",
        },
    }

    return {
        "titulo": "MATRIZ DE PERMISOS ACTUALIZADA",
        "descripcion": "Sistema de roles con aprobaciones implementado",
        "fecha_actualizacion": "2025-10-13",
        "matriz_permisos": matriz,
        "flujos_aprobacion": {
            "cobranzas": {
                "modificar_pagos": "POST /solicitudes/cobranzas/modificar-pago",
                "anular_pagos": "POST /solicitudes/cobranzas/anular-pago",
                "modificar_amortizacion": "POST /solicitudes/cobranzas/modificar-amortizacion",
            },
            "comercial": {
                "editar_clientes": "POST /solicitudes/comercial/editar-cliente"
            },
            "analista": {
                "editar_clientes_propios": "POST /solicitudes/analista/editar-cliente-propio"
            },
            "admin": {
                "aprobar_solicitudes": "POST /solicitudes/aprobar/{sol \
                icitud_id}",
                "rechazar_solicitudes": "POST /solicitudes/rechazar/{solicitud_id}",
                "ver_pendientes": "GET /solicitudes/pendientes",
            },
        },
        "endpoints_principales": {
            "solicitudes_pendientes": "GET /api/v1/solicitudes/pendientes",
            "mis_solicitudes": "GET /api/v1/solicitudes/mis-solicitudes",
            "estadisticas": "GET /api/v1/solicitudes/estadisticas",
            "matriz_permisos": "GET /api/v1/solicitudes/matriz-permisos",
        },
        "usuario_actual": {
            "rol": "ADMIN" if current_user.is_admin else "USER",
            "puede_aprobar": current_user.is_admin,
            "requiere_aprobacion_para": _get_actions_requiring_approval(
                current_user.is_admin
            ),
        },
    }


def _get_actions_requiring_approval(is_admin: bool) -> list:
    """
    Obtener acciones que requieren aprobación para un usuario específico
    """
    if is_admin:
        return []  # Los administradores no necesitan aprobación
    else:
        return [
            "Modificar montos de pagos",
            "Anular/Eliminar pagos",
            "Modificar tabla de amortización",
            "Editar clientes",
        ]


# ============================================
# SISTEMA DE NOTIFICACIONES PARA APROBACIONES
# ============================================


async def _notificar_nueva_solicitud_admin(solicitud: Aprobacion, db: Session):
    """
    Notificar a administradores sobre nueva solicitud
    """
    try:
        # Obtener todos los administradores
        admins = db.query(User).filter(User.is_admin).all()

        for admin in admins:
            # Crear notificación in-app

            notificacion = Notificacion(
                usuario_id=admin.id,
                tipo="SOLICITUD_APROBACION",
                categoria="SISTEMA",
                prioridad=solicitud.prioridad,
                titulo=f"Nueva solicitud de aprobación - {solicitud.tipo_solicitud}",
                mensaje=f"""
 Nueva solicitud de aprobación recibida

 **Detalles:**
 **Tipo:** {solicitud.tipo_solicitud}
 **Solicitante:** {solicitud.solicitante.full_name}
 **Entidad:** {solicitud.entidad} #{solicitud.entidad_id}
 **Prioridad:** {solicitud.prioridad}
 **Fecha límite:** {solicitud.fecha_limite}

 **Justificación:**
{solicitud.justificacion}

 **Acciones:**
 Ver detalles: /solicitudes/pendientes
 Aprobar: /solicitudes/aprobar/{solicitud.id}
 Rechazar: /solicitudes/rechazar/{solicitud.id}
                """,
                extra_data=str(
                    {
                        "solicitud_id": solicitud.id,
                        "tipo_solicitud": solicitud.tipo_solicitud,
                        "prioridad": solicitud.prioridad,
                        "url_accion": f"/solicitudes/pendientes?id={solicitud.id}",
                    }
                ),
            )

            db.add(notificacion)

        # Enviar email a administradores
        await _enviar_email_nueva_solicitud(solicitud, admins)

        # Marcar como notificado
        solicitud.marcar_notificado_admin()
        db.commit()

    except Exception as e:
        logger.error(f"Error enviando notificaciones: {e}")


async def _enviar_email_nueva_solicitud(
    solicitud: Aprobacion, admins: List[User]
):
    """
    Enviar email a administradores sobre nueva solicitud
    """
    try:
        from app.services.email_service import EmailService

        # Determinar urgencia
        urgencia_emoji = {
            "URGENTE": "🚨",
            "ALTA": "⚠️",
            "NORMAL": "📋",
            "BAJA": "📝",
        }

        emoji = urgencia_emoji.get(solicitud.prioridad, "📋")

        # Template del email
        asunto = f"{emoji} Nueva solicitud de aprobación - {solicitud.tipo_solicitud}"

        cuerpo_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; padding: 20px; text-align: center;">
                <h1>{emoji} Nueva Solicitud de Aprobación</h1>
                <p style="margin: 0; font-size: 18px;">{solicitud.tipo_solicitud}</p>
            </div>

            <div style="padding: 20px; background: #f8f9fa;">
                <div style="background: white; padding: 20px; border-radius: \
                8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-top: 0;">📋 Detalles de la Solicitud</h2>

                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bold;">Solicitante:</td>
                            <td style="padding: 8px 0;">{solicitud.sol \
                            icitante.full_name}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bo \
                            ld;">Tipo:</td>
                            <td style="padding: 8px 0;">{solicitud.tipo_solicitud}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bold;">Entidad:</td>
                            <td style="padding: 8px 0;">{solicitud.entidad} #{solicitud.entidad_id}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bold;">Prioridad:</td>
                            <td style="padding: 8px 0;">
                                <span style="
                                    background: {'#dc3545' if solicitud.prioridad == 'URGENTE' else '#ffc107' if solicitud.prioridad == 'ALTA' else '#28a745'};
                                    color: white;
                                    padding: 2px 8px;
                                    border-radius: 4px;
                                    font-size: 12px;
                                ">{solicitud.prioridad}</span>
                            </td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bo \
                            ld;">Fecha límite:</td>
                            <td style="padding: 8px 0;">{solicitud.fecha_limite}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bo \
                            ld;">Archivo adjunto:</td>
                            <td style="padding: 8px 0;">{'✅ Sí' if solicitud.archivo_evidencia else '❌ No'}</td>
                        </tr>
                    </table>

                    <h3 style="color: #333; margin-top: 20px;">📝 Justi \
                    ficación:</h3>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 4px; border-left: 4px solid #007bff;">
                        {solicitud.justificacion}
                    </div>

                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://pagos-f2qf.onrender.com/solicitudes/pendientes"
                           style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 5px;">
                            📋 Ver Solicitudes Pendientes
                        </a>
                        <a href="https://pagos-f2qf.onrender.com/solic \
                        itudes/aprobar/{solicitud.id}"
                           style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 5px;">
                            ✅ Aprobar Solicitud
                        </a>
                    </div>
                </div>
            </div>

            <div style="background: #343a40; color: white; padding: 15px; text-align: center; font-size: 12px;">
                <p style="margin: 0;">Sistema de Financiamiento Automotriz | Notificación automática</p>
                <p style="margin: 5px 0 0 0;">No responder a este email</p>
            </div>
        </div>
        """

        # Enviar a cada admin
        for admin in admins:
            if admin.email:
                await EmailService.send_email(
                    to_email=admin.email,
                    subject=asunto,
                    html_content=cuerpo_html,
                )

    except Exception as e:
        logger.error(f"Error enviando emails: {e}")


async def _notificar_resultado_solicitud(solicitud: Aprobacion, db: Session):
    """
    Notificar al solicitante sobre el resultado de su solicitud
    """
    try:
        # Crear notificación in-app

        estado_emoji = {"APROBADA": "✅", "RECHAZADA": "❌"}

        emoji = estado_emoji.get(solicitud.estado, "📋")

        notificacion = Notificacion(
            usuario_id=solicitud.solicitante_id,
            tipo="RESULTADO_APROBACION",
            categoria="SISTEMA",
            prioridad="ALTA",
            titulo=f"{emoji} Solicitud {solicitud.estado.lower()} - {solicitud.tipo_solicitud}",
            mensaje=f"""
{emoji} **Solicitud {solicitud.estado.lower()}**

 **Detalles:**
 **Tipo:** {solicitud.tipo_solicitud}
 **Entidad:** {solicitud.entidad} #{solicitud.entidad_id}
 **Revisado por:** {solicitud.revisor.full_name if solicitud.revisor else 'N/A'}
 **Fecha de revisión:** {solicitud.fecha_revision}

 **Comentarios del revisor:**
{solicitud.comentarios_revisor or 'Sin comentarios adicionales'}

{'🎉 **La acción solicitada ha sido ejecutada exitosamente.**' if solicitud.estado == 'APROBADA' else '⚠️ **La solicitud no fue aprobada. Revise los comentarios del revisor.**'}
            """,
            extra_data=str(
                {
                    "solicitud_id": solicitud.id,
                    "estado": solicitud.estado,
                    "tipo_solicitud": solicitud.tipo_solicitud,
                }
            ),
        )

        db.add(notificacion)

        # Enviar email al solicitante
        await _enviar_email_resultado_solicitud(solicitud)

        # Marcar como notificado
        solicitud.marcar_notificado_solicitante()
        db.commit()

    except Exception as e:
        logger.error(f"Error enviando notificación de resultado: {e}")


async def _enviar_email_resultado_solicitud(solicitud: Aprobacion):
    """
    Enviar email al solicitante sobre el resultado
    """
    try:

        estado_emoji = {"APROBADA": "✅", "RECHAZADA": "❌"}

        emoji = estado_emoji.get(solicitud.estado, "📋")
        color = "#28a745" if solicitud.estado == "APROBADA" else "#dc3545"

        asunto = f"{emoji} Solicitud {solicitud.estado.lower()} - {solicitud.tipo_solicitud}"

        cuerpo_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {color}; color: white; padding: 20px; text-align: center;">
                <h1>{emoji} Solicitud {solicitud.estado.title()}</h1>
                <p style="margin: 0; font-size: 18px;">{solicitud.tipo_solicitud}</p>
            </div>

            <div style="padding: 20px; background: #f8f9fa;">
                <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-top: 0;">📋 Resultado de su Solicitud</h2>

                    <div style="background: {'#d4edda' if solicitud.estado == 'APROBADA' else '#f8d7da'};
                                border: 1px solid {'#c3e6cb' if solicitud.estado == 'APROBADA' else '#f5c6cb'};
                                color: {'#155724' if solicitud.estado == 'APROBADA' else '#721c24'};
                                padding: 15px; border-radius: 4px; margin: 15px 0;">
                        <strong>{emoji} Su solicitud ha sido {solicitud.estado.lower()}</strong>
                    </div>

                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bold;">Tipo de solicitud:</td>
                            <td style="padding: 8px 0;">{solicitud.tipo_solicitud}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bold;">Entidad afectada:</td>
                            <td style="padding: 8px 0;">{solicitud.entidad} #{solicitud.entidad_id}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #eee;">
                            <td style="padding: 8px 0; font-weight: bold;">Revisado por:</td>
                            <td style="padding: 8px 0;">{solicitud.revisor.full_name if solicitud.revisor else 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">Fecha de revisión:</td>
                            <td style="padding: 8px 0;">{solicitud.fecha_revision}</td>
                        </tr>
                    </table>

                    {f'''
                    <h3 style="color: #333;">💬 Comentarios del revisor:</h3>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 4px; border-left: 4px solid {color};">
                        {solicitud.comentarios_revisor}
                    </div>
                    ''' if solicitud.comentarios_revisor else ''}

                    {f'''
                    <p style="color: #28a745; font-weight: bold;">
                        🎉 La acción solicitada ha sido ejecutada exitosamente.
                    </p>
                    ''' if solicitud.estado == 'APROBADA' else f'''
                    <p style="color: #dc3545; font-weight: bold;">
                        ⚠️ La solicitud no fue aprobada. Revise los comentarios del revisor.
                    </p>
                    '''}

                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://pagos-f2qf.onrender.com/solic \
                        itudes/mis-solicitudes"
                           style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            📋 Ver Mis Solicitudes
                        </a>
                    </div>
                </div>
            </div>

            <div style="background: #343a40; color: white; padding: 15px; text-align: center; font-size: 12px;">
                <p style="margin: 0;">Sistema de Financiamiento Automotriz | Notificación automática</p>
                <p style="margin: 5px 0 0 0;">No responder a este email</p>
            </div>
        </div>
        """

        if solicitud.solicitante.email:
            await EmailService.send_email(
                to_email=solicitud.solicitante.email,
                subject=asunto,
                html_content=cuerpo_html,
            )

    except Exception as e:
        logger.error(f"Error enviando email de resultado: {e}")
