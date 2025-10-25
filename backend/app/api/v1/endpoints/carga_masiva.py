# backend/app/api/v1/endpoints/carga_masiva.py
"""
Sistema de Carga Masiva de Clientes y Pagos
Proceso completo con validación, corrección en línea y articulación por cédula
"""

import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.analista import Analista
from app.models.auditoria import Auditoria, TipoAccion
from app.models.cliente import Cliente
from app.models.concesionario import Concesionario
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.pago import Pago
from app.models.user import User
from app.services.validators_service import (
    ValidadorCedula,
    ValidadorEmail,
    ValidadorFecha,
    ValidadorMonto,
    ValidadorTelefono,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SCHEMAS PARA CARGA MASIVA
# ============================================


class ErrorCargaMasiva(BaseModel):
    """Error encontrado en carga masiva"""

    fila: int
    cedula: str
    campo: str
    valor_original: str
    error: str
    tipo_error: str  # CRITICO, ADVERTENCIA, DATO_VACIO
    puede_corregirse: bool
    sugerencia: Optional[str] = None


class RegistroCargaMasiva(BaseModel):
    """Registro procesado en carga masiva"""

    fila: int
    cedula: str
    nombre_completo: str
    estado: str  # PROCESADO, ERROR, PENDIENTE_CORRECCION
    errores: List[ErrorCargaMasiva]
    datos: Dict[str, Any]


class ResultadoCargaMasiva(BaseModel):
    """Resultado del proceso de carga masiva"""

    total_registros: int
    registros_procesados: int
    registros_con_errores: int
    registros_pendientes: int
    errores_criticos: int
    errores_advertencia: int
    datos_vacios: int
    registros: List[RegistroCargaMasiva]
    archivo: str
    fecha_carga: datetime
    usuario_id: int


class CorreccionRegistro(BaseModel):
    """Corrección de un registro con errores"""

    fila: int
    cedula: str
    correcciones: Dict[str, str]


# ============================================
# ENDPOINT: SUBIR ARCHIVO EXCEL
# ============================================


@router.post("/upload", response_model=ResultadoCargaMasiva)
async def cargar_archivo_excel(
    archivo: UploadFile = File(...),
    tipo_carga: str = Form(..., description="clientes o pagos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📤 PASO 1: Subir archivo Excel y analizar errores

    Proceso:
    1. Leer archivo Excel
    2. Validar TODOS los registros
    3. Clasificar errores (CRÍTICO, ADVERTENCIA, DATO_VACÍO)
    4. NO guardar nada aún
    5. Retornar dashboard con errores para corrección
    """
    try:
        # Validar tipo de archivo
        if not archivo.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel (.xlsx, .xls)")

        # Leer contenido
        contenido = await archivo.read()

        # Procesar según tipo
        if tipo_carga == "clientes":
            resultado = await _analizar_archivo_clientes(contenido, archivo.filename, db, current_user.id)
        elif tipo_carga == "pagos":
            resultado = await _analizar_archivo_pagos(contenido, archivo.filename, db, current_user.id)
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de carga inválido. Use 'clientes' o 'pagos'",
            )

        # Registrar en auditoría
        auditoria = Auditoria.registrar(
            usuario_id=current_user.id,
            accion=TipoAccion.CREAR,
            tabla="CargaMasiva",
            descripcion=f"Análisis de carga masiva: {archivo.filename} ({tipo_carga})",
            datos_nuevos={
                "archivo": archivo.filename,
                "tipo": tipo_carga,
                "total_registros": resultado.total_registros,
                "errores": resultado.registros_con_errores,
            },
            resultado="EXITOSO",
        )
        db.add(auditoria)
        db.commit()

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")


# ============================================
# FUNCIÓN: ANALIZAR ARCHIVO DE CLIENTES
# ============================================


async def _analizar_archivo_clientes(
    contenido: bytes, nombre_archivo: str, db: Session, usuario_id: int
) -> ResultadoCargaMasiva:
    """
    Analizar archivo de clientes sin guardar
    Detectar TODOS los errores y clasificarlos
    """
    try:
        # Leer Excel
        df = pd.read_excel(io.BytesIO(contenido))

        # ============================================
        # MAPEO DE COLUMNAS EXCEL → SISTEMA
        # ============================================
        mapeo_columnas = {
            "CEDULA IDENTIDAD": "cedula",
            "CEDULA IDENT": "cedula",
            "CEDULA": "cedula",
            "NOMBRE": "nombre",
            "APELLIDO": "apellido",
            "MOVIL": "movil",
            "TELEFONO": "movil",
            "CORREO ELECTRONICO": "email",
            "EMAIL": "email",
            "DIRECCION": "direccion",
            "MODELO VEHICULO": "modelo_vehiculo",
            "MODELO": "modelo_vehiculo",
            "CONCESIONARIO": "concesionario",
            "TOTAL FINANCIAMIENTO": "total_financiamiento",
            "MONTO FINANCIAMIENTO": "total_financiamiento",
            "CUOTA INICIAL": "cuota_inicial",
            "INICIAL": "cuota_inicial",
            "NUMERO AMORTIZACIONES": "numero_amortizaciones",
            "AMORTIZACIONES": "numero_amortizaciones",
            "CUOTAS": "numero_amortizaciones",
            "MODALIDAD PAGO": "modalidad_pago",
            "MODALIDAD": "modalidad_pago",
            "FECHA ENTREGA": "fecha_entrega",
            "ENTREGA": "fecha_entrega",
            "USER": "asesor",
            "USER ASIGNADO": "asesor",
        }

        # Renombrar columnas
        df = df.rename(columns=mapeo_columnas)

        # ============================================
        # VALIDAR COLUMNAS REQUERIDAS
        # ============================================
        columnas_requeridas = ["cedula", "nombre"]
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

        if columnas_faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Faltan columnas requeridas: {', '.join(columnas_faltantes)}",
            )

        # ============================================
        # PROCESAR CADA REGISTRO
        # ============================================
        registros_procesados = []
        total_registros = len(df)
        registros_con_errores = 0
        errores_criticos = 0
        errores_advertencia = 0
        datos_vacios = 0

        for index, row in df.iterrows():
            fila_numero = index + 2  # +2 porque Excel empieza en 1 y tiene header
            errores_registro = []

            # ============================================
            # EXTRAER DATOS DE LA FILA
            # ============================================
            cedula = str(row.get("cedula", "")).strip()
            nombre = str(row.get("nombre", "")).strip()
            apellido = str(row.get("apellido", "")).strip() if "apellido" in row else ""
            movil = str(row.get("movil", "")).strip()
            email = str(row.get("email", "")).strip()
            direccion = str(row.get("direccion", "")).strip()
            modelo_vehiculo = str(row.get("modelo_vehiculo", "")).strip()
            concesionario = str(row.get("concesionario", "")).strip()
            total_financiamiento = str(row.get("total_financiamiento", "")).strip()
            cuota_inicial = str(row.get("cuota_inicial", "")).strip()
            numero_amortizaciones = str(row.get("numero_amortizaciones", "")).strip()
            modalidad_pago = str(row.get("modalidad_pago", "")).strip()
            fecha_entrega = str(row.get("fecha_entrega", "")).strip()
            asesor = str(row.get("asesor", "")).strip()

            # Si no hay apellido separado, intentar split del nombre
            if not apellido and nombre:
                partes_nombre = nombre.split(" ", 1)
                if len(partes_nombre) > 1:
                    nombre = partes_nombre[0]
                    apellido = partes_nombre[1]

            # ============================================
            # VALIDACIÓN 1: CAMPOS CRÍTICOS VACÍOS
            # ============================================

            # Cédula (CRÍTICO)
            if not cedula or cedula.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula or "VACÍO",
                        campo="cedula",
                        valor_original=cedula,
                        error="Cédula vacía o marcada como ERROR",
                        tipo_error="CRITICO",
                        puede_corregirse=True,
                        sugerencia="Ingrese cédula válida (ej: V12345678)",
                    )
                )
                errores_criticos += 1

            # Nombre (CRÍTICO)
            if not nombre or nombre.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula or "VACÍO",
                        campo="nombre",
                        valor_original=nombre,
                        error="Nombre vacío o marcado como ERROR",
                        tipo_error="CRITICO",
                        puede_corregirse=True,
                        sugerencia="Ingrese nombre completo del cliente",
                    )
                )
                errores_criticos += 1

            # Total Financiamiento (CRÍTICO si se quiere financiamiento)
            if not total_financiamiento or total_financiamiento.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="total_financiamiento",
                        valor_original=total_financiamiento,
                        error="Total financiamiento vacío o marcado como ERROR",
                        tipo_error="DATO_VACIO",
                        puede_corregirse=True,
                        sugerencia="Ingrese monto del financiamiento (ej: 50000)",
                    )
                )
                datos_vacios += 1

            # Número de Amortizaciones (CRÍTICO si hay financiamiento)
            if total_financiamiento and (not numero_amortizaciones or numero_amortizaciones.upper() == "ERROR"):
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="numero_amortizaciones",
                        valor_original=numero_amortizaciones,
                        error="Número de amortizaciones vacío o marcado como ERROR",
                        tipo_error="DATO_VACIO",
                        puede_corregirse=True,
                        sugerencia="Ingrese número de cuotas (ej: 12, 24, 36)",
                    )
                )
                datos_vacios += 1

            # Fecha Entrega (CRÍTICO si hay financiamiento)
            if total_financiamiento and (not fecha_entrega or fecha_entrega.upper() == "ERROR"):
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="fecha_entrega",
                        valor_original=fecha_entrega,
                        error="Fecha de entrega vacía o marcada como ERROR",
                        tipo_error="CRITICO",
                        puede_corregirse=True,
                        sugerencia="Ingrese fecha de entrega (ej: 2025-01-15)",
                    )
                )
                errores_criticos += 1

            # ============================================
            # VALIDACIÓN 2: CAMPOS DE ADVERTENCIA VACÍOS
            # ============================================

            # Móvil (ADVERTENCIA)
            if not movil or movil.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="movil",
                        valor_original=movil,
                        error="Móvil vacío o marcado como ERROR",
                        tipo_error="ADVERTENCIA",
                        puede_corregirse=True,
                        sugerencia="Ingrese número móvil (ej: 4241234567)",
                    )
                )
                errores_advertencia += 1

            # Email (ADVERTENCIA)
            if not email or email.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="email",
                        valor_original=email,
                        error="Email vacío o marcado como ERROR",
                        tipo_error="ADVERTENCIA",
                        puede_corregirse=True,
                        sugerencia="Ingrese email válido (ej: cliente@ejemplo.com)",
                    )
                )
                errores_advertencia += 1

            # Concesionario (DATO_VACIO)
            if not concesionario:
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="concesionario",
                        valor_original="",
                        error="Concesionario vacío",
                        tipo_error="DATO_VACIO",
                        puede_corregirse=True,
                        sugerencia="Seleccione un concesionario de la lista",
                    )
                )
                datos_vacios += 1

            # Modelo de Vehículo (DATO_VACIO)
            if not modelo_vehiculo:
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="modelo_vehiculo",
                        valor_original="",
                        error="Modelo de vehículo vacío",
                        tipo_error="DATO_VACIO",
                        puede_corregirse=True,
                        sugerencia="Seleccione un modelo de la lista",
                    )
                )
                datos_vacios += 1

            # Analista (DATO_VACIO)
            if not asesor:
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="asesor",
                        valor_original="",
                        error="Analista vacío",
                        tipo_error="DATO_VACIO",
                        puede_corregirse=True,
                        sugerencia="Seleccione un asesor de la lista",
                    )
                )
                datos_vacios += 1

            # Modalidad de Pago (DATO_VACIO)
            if not modalidad_pago:
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="modalidad_pago",
                        valor_original="",
                        error="Modalidad de pago vacía",
                        tipo_error="DATO_VACIO",
                        puede_corregirse=True,
                        sugerencia="Seleccione: SEMANAL, QUINCENAL o MENSUAL",
                    )
                )
                datos_vacios += 1

            # ============================================
            # VALIDACIÓN 3: FORMATO DE DATOS
            # ============================================

            # Validar cédula con validador del sistema
            if cedula and cedula.upper() != "ERROR":
                resultado_cedula = ValidadorCedula.validar_y_formatear_cedula(cedula, "VENEZUELA")
                if not resultado_cedula.get("valido"):
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="cedula",
                            valor_original=cedula,
                            error=resultado_cedula.get("mensaje", "Formato inválido"),
                            tipo_error="CRITICO",
                            puede_corregirse=True,
                            sugerencia="Formato: V/E/J + 7-10 dígitos (ej: V12345678)",
                        )
                    )
                    errores_criticos += 1

            # Validar móvil con validador del sistema
            if movil and movil.upper() != "ERROR":
                resultado_movil = ValidadorTelefono.validar_y_formatear_telefono(movil, "VENEZUELA")
                if not resultado_movil.get("valido"):
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="movil",
                            valor_original=movil,
                            error=resultado_movil.get("mensaje", "Formato inválido"),
                            tipo_error="ADVERTENCIA",
                            puede_corregirse=True,
                            sugerencia="Formato: +58 XXXXXXXXXX (10 dígitos)",
                        )
                    )
                    errores_advertencia += 1

            # Validar email con validador del sistema
            if email and email.upper() != "ERROR":
                resultado_email = ValidadorEmail.validar_email(email)
                if not resultado_email.get("valido"):
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="email",
                            valor_original=email,
                            error=resultado_email.get("mensaje", "Formato inválido"),
                            tipo_error="ADVERTENCIA",
                            puede_corregirse=True,
                            sugerencia="Formato: usuario@dominio.com",
                        )
                    )
                    errores_advertencia += 1

            # Validar fecha de entrega
            if fecha_entrega and fecha_entrega.upper() != "ERROR":
                resultado_fecha = ValidadorFecha.validar_y_formatear_fecha(fecha_entrega)
                if not resultado_fecha.get("valido"):
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="fecha_entrega",
                            valor_original=fecha_entrega,
                            error=resultado_fecha.get("mensaje", "Formato inválido"),
                            tipo_error="CRITICO",
                            puede_corregirse=True,
                            sugerencia="Formato: DD/MM/YYYY o YYYY-MM-DD",
                        )
                    )
                    errores_criticos += 1

            # Validar monto de financiamiento
            if total_financiamiento and total_financiamiento.upper() != "ERROR":
                resultado_monto = ValidadorMonto.validar_y_formatear_monto(total_financiamiento)
                if not resultado_monto.get("valido"):
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="total_financiamiento",
                            valor_original=total_financiamiento,
                            error=resultado_monto.get("mensaje", "Formato inválido"),
                            tipo_error="CRITICO",
                            puede_corregirse=True,
                            sugerencia="Ingrese monto numérico (ej: 50000.00)",
                        )
                    )
                    errores_criticos += 1

            # ============================================
            # VALIDACIÓN 4: EXISTENCIA EN BD
            # ============================================

            # Verificar si concesionario existe
            if concesionario:
                concesionario_obj = (
                    db.query(Concesionario)
                    .filter(
                        Concesionario.nombre.ilike(f"%{concesionario}%"),
                        Concesionario.activo,
                    )
                    .first()
                )

                if not concesionario_obj:
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="concesionario",
                            valor_original=concesionario,
                            error=f'Concesionario "{concesionario}" no existe en la base de datos',
                            tipo_error="DATO_VACIO",
                            puede_corregirse=True,
                            sugerencia="Seleccione un concesionario existente o créelo primero en Configuración",
                        )
                    )
                    datos_vacios += 1

            # Verificar si modelo de vehículo existe
            if modelo_vehiculo:
                modelo_obj = (
                    db.query(ModeloVehiculo)
                    .filter(
                        ModeloVehiculo.modelo.ilike(f"%{modelo_vehiculo}%"),
                        ModeloVehiculo.activo,
                    )
                    .first()
                )

                if not modelo_obj:
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="modelo_vehiculo",
                            valor_original=modelo_vehiculo,
                            error=f'Modelo "{modelo_vehiculo}" no existe en la base de datos',
                            tipo_error="DATO_VACIO",
                            puede_corregirse=True,
                            sugerencia="Seleccione un modelo existente o créelo primero en Configuración",
                        )
                    )
                    datos_vacios += 1

            # Verificar si asesor existe
            if asesor:
                asesor_obj = db.query(Analista).filter(Analista.nombre.ilike(f"%{asesor}%"), Analista.activo).first()

                if not asesor_obj:
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="asesor",
                            valor_original=asesor,
                            error=f'Analista "{asesor}" no existe en la base de datos',
                            tipo_error="DATO_VACIO",
                            puede_corregirse=True,
                            sugerencia="Seleccione un asesor existente o créelo primero en Configuración",
                        )
                    )
                    datos_vacios += 1

            # Validar modalidad de pago
            if modalidad_pago:
                modalidades_validas = ["SEMANAL", "QUINCENAL", "MENSUAL", "BIMENSUAL"]
                if modalidad_pago.upper() not in modalidades_validas:
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="modalidad_pago",
                            valor_original=modalidad_pago,
                            error=f'Modalidad "{modalidad_pago}" no es válida',
                            tipo_error="CRITICO",
                            puede_corregirse=True,
                            sugerencia=f'Use: {", ".join(modalidades_validas)}',
                        )
                    )
                    errores_criticos += 1

            # ============================================
            # DETERMINAR ESTADO DEL REGISTRO
            # ============================================

            tiene_errores_criticos = any(e.tipo_error == "CRITICO" for e in errores_registro)
            tiene_datos_vacios = any(e.tipo_error == "DATO_VACIO" for e in errores_registro)

            if tiene_errores_criticos:
                estado = "ERROR"
                registros_con_errores += 1
            elif tiene_datos_vacios:
                estado = "PENDIENTE_CORRECCION"
                registros_con_errores += 1
            elif errores_registro:
                estado = "ADVERTENCIA"
                registros_con_errores += 1
            else:
                estado = "LISTO"

            # Agregar registro procesado
            registros_procesados.append(
                RegistroCargaMasiva(
                    fila=fila_numero,
                    cedula=cedula or "VACÍO",
                    nombre_completo=f"{nombre} {apellido}".strip(),
                    estado=estado,
                    errores=errores_registro,
                    datos={
                        "cedula": cedula,
                        "nombre": nombre,
                        "apellido": apellido,
                        "movil": movil,
                        "email": email,
                        "direccion": direccion,
                        "modelo_vehiculo": modelo_vehiculo,
                        "concesionario": concesionario,
                        "total_financiamiento": total_financiamiento,
                        "cuota_inicial": cuota_inicial,
                        "numero_amortizaciones": numero_amortizaciones,
                        "modalidad_pago": modalidad_pago or "MENSUAL",
                        "fecha_entrega": fecha_entrega,
                        "asesor": asesor,
                    },
                )
            )

        # ============================================
        # RETORNAR RESULTADO PARA DASHBOARD
        # ============================================

        return ResultadoCargaMasiva(
            total_registros=total_registros,
            registros_procesados=len([r for r in registros_procesados if r.estado == "LISTO"]),
            registros_con_errores=registros_con_errores,
            registros_pendientes=len([r for r in registros_procesados if r.estado == "PENDIENTE_CORRECCION"]),
            errores_criticos=errores_criticos,
            errores_advertencia=errores_advertencia,
            datos_vacios=datos_vacios,
            registros=registros_procesados,
            archivo=nombre_archivo,
            fecha_carga=datetime.utcnow(),
            usuario_id=usuario_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analizando archivo de clientes: {str(e)}")


# ============================================
# FUNCIÓN: ANALIZAR ARCHIVO DE PAGOS
# ============================================


async def _analizar_archivo_pagos(
    contenido: bytes, nombre_archivo: str, db: Session, usuario_id: int
) -> ResultadoCargaMasiva:
    """
    Analizar archivo de pagos y articular con clientes por cédula
    """
    try:
        # Leer Excel
        df = pd.read_excel(io.BytesIO(contenido))

        # Mapeo de columnas para pagos
        mapeo_columnas = {
            "CEDULA IDENTIDAD": "cedula",
            "CEDULA": "cedula",
            "FECHA PAGO": "fecha_pago",
            "FECHA": "fecha_pago",
            "MONTO PAGADO": "monto_pagado",
            "MONTO": "monto_pagado",
            "NUMERO CUOTA": "numero_cuota",
            "CUOTA": "numero_cuota",
            "DOCUMENTO PAGO": "documento_pago",
            "DOCUMENTO": "documento_pago",
            "REFERENCIA": "documento_pago",
            "METODO PAGO": "metodo_pago",
            "METODO": "metodo_pago",
        }

        df = df.rename(columns=mapeo_columnas)

        # Validar columnas requeridas
        columnas_requeridas = ["cedula", "fecha_pago", "monto_pagado"]
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

        if columnas_faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Faltan columnas requeridas: {', '.join(columnas_faltantes)}",
            )

        # Procesar cada pago
        registros_procesados = []
        total_registros = len(df)
        registros_con_errores = 0
        errores_criticos = 0
        errores_advertencia = 0
        datos_vacios = 0

        for index, row in df.iterrows():
            fila_numero = index + 2
            errores_registro = []

            cedula = str(row.get("cedula", "")).strip()
            fecha_pago = str(row.get("fecha_pago", "")).strip()
            monto_pagado = str(row.get("monto_pagado", "")).strip()
            numero_cuota = str(row.get("numero_cuota", "")).strip()
            documento_pago = str(row.get("documento_pago", "")).strip()
            metodo_pago = str(row.get("metodo_pago", "")).strip()

            # ============================================
            # VALIDACIÓN: ARTICULACIÓN CON CLIENTE
            # ============================================

            # Buscar cliente por cédula
            cliente = None
            if cedula and cedula.upper() != "ERROR":
                cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()

                if not cliente:
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="cedula",
                            valor_original=cedula,
                            error=f'Cliente con cédula "{cedula}" NO existe en la base de datos',
                            tipo_error="CRITICO",
                            puede_corregirse=False,
                            sugerencia="Debe crear el cliente primero antes de cargar pagos",
                        )
                    )
                    errores_criticos += 1
            else:
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula or "VACÍO",
                        campo="cedula",
                        valor_original=cedula,
                        error="Cédula vacía o marcada como ERROR",
                        tipo_error="CRITICO",
                        puede_corregirse=True,
                        sugerencia="Ingrese cédula del cliente",
                    )
                )
                errores_criticos += 1

            # Validar fecha de pago
            if not fecha_pago or fecha_pago.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="fecha_pago",
                        valor_original=fecha_pago,
                        error="Fecha de pago vacía o marcada como ERROR",
                        tipo_error="CRITICO",
                        puede_corregirse=True,
                        sugerencia="Ingrese fecha del pago (ej: 15/01/2025)",
                    )
                )
                errores_criticos += 1
            else:
                resultado_fecha = ValidadorFecha.validar_y_formatear_fecha(fecha_pago)
                if not resultado_fecha.get("valido"):
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="fecha_pago",
                            valor_original=fecha_pago,
                            error=resultado_fecha.get("mensaje", "Formato inválido"),
                            tipo_error="CRITICO",
                            puede_corregirse=True,
                            sugerencia="Formato: DD/MM/YYYY o YYYY-MM-DD",
                        )
                    )
                    errores_criticos += 1

            # Validar monto pagado
            if not monto_pagado or monto_pagado.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="monto_pagado",
                        valor_original=monto_pagado,
                        error="Monto pagado vacío o marcado como ERROR",
                        tipo_error="CRITICO",
                        puede_corregirse=True,
                        sugerencia="Ingrese monto del pago (ej: 5000.00)",
                    )
                )
                errores_criticos += 1
            else:
                resultado_monto = ValidadorMonto.validar_y_formatear_monto(monto_pagado)
                if not resultado_monto.get("valido"):
                    errores_registro.append(
                        ErrorCargaMasiva(
                            fila=fila_numero,
                            cedula=cedula,
                            campo="monto_pagado",
                            valor_original=monto_pagado,
                            error=resultado_monto.get("mensaje", "Formato inválido"),
                            tipo_error="CRITICO",
                            puede_corregirse=True,
                            sugerencia="Ingrese monto numérico (ej: 5000.00)",
                        )
                    )
                    errores_criticos += 1

            # Documento de pago (ADVERTENCIA si vacío)
            if not documento_pago or documento_pago.upper() == "ERROR":
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="documento_pago",
                        valor_original=documento_pago,
                        error="Documento de pago vacío",
                        tipo_error="ADVERTENCIA",
                        puede_corregirse=True,
                        sugerencia="Ingrese número de referencia o documento",
                    )
                )
                errores_advertencia += 1

            # Método de pago (DATO_VACIO si vacío)
            if not metodo_pago:
                errores_registro.append(
                    ErrorCargaMasiva(
                        fila=fila_numero,
                        cedula=cedula,
                        campo="metodo_pago",
                        valor_original="",
                        error="Método de pago vacío",
                        tipo_error="DATO_VACIO",
                        puede_corregirse=True,
                        sugerencia="Seleccione: TRANSFERENCIA, EFECTIVO, CHEQUE, etc.",
                    )
                )
                datos_vacios += 1

            # Determinar estado
            tiene_errores_criticos = any(e.tipo_error == "CRITICO" for e in errores_registro)
            tiene_datos_vacios = any(e.tipo_error == "DATO_VACIO" for e in errores_registro)

            if tiene_errores_criticos:
                estado = "ERROR"
                registros_con_errores += 1
            elif tiene_datos_vacios:
                estado = "PENDIENTE_CORRECCION"
                registros_con_errores += 1
            elif errores_registro:
                estado = "ADVERTENCIA"
                registros_con_errores += 1
            else:
                estado = "LISTO"

            # Agregar registro
            registros_procesados.append(
                RegistroCargaMasiva(
                    fila=fila_numero,
                    cedula=cedula or "VACÍO",
                    nombre_completo=(cliente.nombre_completo if cliente else "Cliente no encontrado"),
                    estado=estado,
                    errores=errores_registro,
                    datos={
                        "cedula": cedula,
                        "fecha_pago": fecha_pago,
                        "monto_pagado": monto_pagado,
                        "numero_cuota": numero_cuota,
                        "documento_pago": documento_pago,
                        "metodo_pago": metodo_pago,
                        "cliente_id": cliente.id if cliente else None,
                        "cliente_nombre": cliente.nombre_completo if cliente else None,
                    },
                )
            )

        return ResultadoCargaMasiva(
            total_registros=total_registros,
            registros_procesados=len([r for r in registros_procesados if r.estado == "LISTO"]),
            registros_con_errores=registros_con_errores,
            registros_pendientes=len([r for r in registros_procesados if r.estado == "PENDIENTE_CORRECCION"]),
            errores_criticos=errores_criticos,
            errores_advertencia=errores_advertencia,
            datos_vacios=datos_vacios,
            registros=registros_procesados,
            archivo=nombre_archivo,
            fecha_carga=datetime.utcnow(),
            usuario_id=usuario_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analizando archivo de pagos: {str(e)}")


# ============================================
# ENDPOINT: CORREGIR REGISTRO EN LÍNEA
# ============================================


@router.post("/corregir-registro")
async def corregir_registro_en_linea(
    correccion: CorreccionRegistro,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    ✏️ PASO 2: Corregir un registro con errores en línea

    Proceso:
    1. Recibir correcciones del usuario
    2. Validar con validadores del sistema
    3. Si pasa validación, marcar como LISTO
    4. Retornar estado actualizado
    """
    try:
        errores_validacion = []
        datos_corregidos = {}

        # Validar cada corrección
        for campo, valor in correccion.correcciones.items():
            if campo == "cedula":
                resultado = ValidadorCedula.validar_y_formatear_cedula(valor, "VENEZUELA")
                if not resultado.get("valido"):
                    errores_validacion.append(f"Cédula: {resultado.get('mensaje')}")
                else:
                    datos_corregidos[campo] = resultado.get("valor_formateado")

            elif campo == "movil":
                resultado = ValidadorTelefono.validar_y_formatear_telefono(valor, "VENEZUELA")
                if not resultado.get("valido"):
                    errores_validacion.append(f"Móvil: {resultado.get('mensaje')}")
                else:
                    datos_corregidos[campo] = resultado.get("valor_formateado")

            elif campo == "email":
                resultado = ValidadorEmail.validar_email(valor)
                if not resultado.get("valido"):
                    errores_validacion.append(f"Email: {resultado.get('mensaje')}")
                else:
                    datos_corregidos[campo] = resultado.get("valor_formateado")

            elif campo == "fecha_entrega" or campo == "fecha_pago":
                resultado = ValidadorFecha.validar_y_formatear_fecha(valor)
                if not resultado.get("valido"):
                    errores_validacion.append(f"Fecha: {resultado.get('mensaje')}")
                else:
                    datos_corregidos[campo] = resultado.get("valor_formateado")

            elif campo in ["total_financiamiento", "cuota_inicial", "monto_pagado"]:
                resultado = ValidadorMonto.validar_y_formatear_monto(valor)
                if not resultado.get("valido"):
                    errores_validacion.append(f"Monto: {resultado.get('mensaje')}")
                else:
                    datos_corregidos[campo] = resultado.get("valor_formateado")

            elif campo == "concesionario":
                # Verificar que existe
                concesionario = (
                    db.query(Concesionario)
                    .filter(Concesionario.nombre.ilike(f"%{valor}%"), Concesionario.activo)
                    .first()
                )
                if not concesionario:
                    errores_validacion.append(f"Concesionario '{valor}' no existe en la BD")
                else:
                    datos_corregidos[campo] = valor
                    datos_corregidos["concesionario_id"] = concesionario.id

            elif campo == "modelo_vehiculo":
                # Verificar que existe
                modelo = (
                    db.query(ModeloVehiculo)
                    .filter(ModeloVehiculo.modelo.ilike(f"%{valor}%"), ModeloVehiculo.activo)
                    .first()
                )
                if not modelo:
                    errores_validacion.append(f"Modelo '{valor}' no existe en la BD")
                else:
                    datos_corregidos[campo] = valor
                    datos_corregidos["modelo_vehiculo_id"] = modelo.id

            elif campo == "asesor":
                # Verificar que existe
                asesor = db.query(Analista).filter(Analista.nombre.ilike(f"%{valor}%"), Analista.activo).first()
                if not asesor:
                    errores_validacion.append(f"Analista '{valor}' no existe en la BD")
                else:
                    datos_corregidos[campo] = valor
                    datos_corregidos["asesor_id"] = asesor.id

            elif campo == "modalidad_pago":
                modalidades_validas = ["SEMANAL", "QUINCENAL", "MENSUAL", "BIMENSUAL"]
                if valor.upper() not in modalidades_validas:
                    errores_validacion.append(
                        f"Modalidad '{valor}' no es válida. Use: {', '.join(modalidades_validas)}"
                    )
                else:
                    datos_corregidos[campo] = valor.upper()

            else:
                # Otros campos sin validación especial
                datos_corregidos[campo] = valor

        # Si hay errores, retornar sin guardar
        if errores_validacion:
            return {
                "success": False,
                "errores": errores_validacion,
                "datos_corregidos": datos_corregidos,
            }

        # Si todo está OK, retornar éxito
        return {
            "success": True,
            "mensaje": "✅ Correcciones validadas correctamente",
            "datos_corregidos": datos_corregidos,
            "puede_guardarse": True,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error corrigiendo registro: {str(e)}")


# ============================================
# ENDPOINT: GUARDAR REGISTROS CORREGIDOS
# ============================================


@router.post("/guardar-registros")
async def guardar_registros_corregidos(
    registros: List[Dict[str, Any]],
    tipo_carga: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    💾 PASO 3: Guardar registros que pasaron validación

    Proceso:
    1. Recibir solo registros con estado LISTO
    2. Usar MISMO proceso que crear_cliente o crear_pago
    3. Mapear nombres a ForeignKeys
    4. Guardar en base de datos
    5. Retornar resumen final
    """
    try:
        registros_guardados = 0
        errores_guardado = []

        for registro in registros:
            try:
                if tipo_carga == "clientes":
                    # Usar MISMO proceso que crear_cliente
                    await _guardar_cliente_desde_carga(registro, db, current_user.id)
                    registros_guardados += 1

                elif tipo_carga == "pagos":
                    # Usar MISMO proceso que crear_pago
                    await _guardar_pago_desde_carga(registro, db, current_user.id)
                    registros_guardados += 1

            except Exception as e:
                errores_guardado.append({"cedula": registro.get("cedula"), "error": str(e)})

        db.commit()

        # Registrar en auditoría
        auditoria = Auditoria.registrar(
            usuario_id=current_user.id,
            accion=TipoAccion.CREAR,
            tabla="CargaMasiva",
            descripcion=f"Guardado de carga masiva: {registros_guardados} registros ({tipo_carga})",
            datos_nuevos={
                "tipo": tipo_carga,
                "registros_guardados": registros_guardados,
                "errores": len(errores_guardado),
            },
            resultado="EXITOSO",
        )
        db.add(auditoria)
        db.commit()

        return {
            "success": True,
            "mensaje": f"✅ {registros_guardados} registros guardados exitosamente",
            "registros_guardados": registros_guardados,
            "errores": errores_guardado,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando registros: {str(e)}")


# ============================================
# FUNCIÓN: GUARDAR CLIENTE DESDE CARGA MASIVA
# ============================================


async def _guardar_cliente_desde_carga(datos: Dict[str, Any], db: Session, usuario_id: int):
    """
    Guardar cliente usando MISMO proceso que crear_cliente
    """
    try:
        # ============================================
        # MAPEAR NOMBRES A FOREIGNKEYS
        # ============================================

        concesionario_id = None
        modelo_vehiculo_id = None
        asesor_id = None

        # Buscar concesionario_id
        if datos.get("concesionario"):
            concesionario_obj = (
                db.query(Concesionario)
                .filter(
                    Concesionario.nombre.ilike(f"%{datos['concesionario']}%"),
                    Concesionario.activo,
                )
                .first()
            )
            if concesionario_obj:
                concesionario_id = concesionario_obj.id

        # Buscar modelo_vehiculo_id
        if datos.get("modelo_vehiculo"):
            modelo_obj = (
                db.query(ModeloVehiculo)
                .filter(
                    ModeloVehiculo.modelo.ilike(f"%{datos['modelo_vehiculo']}%"),
                    ModeloVehiculo.activo,
                )
                .first()
            )
            if modelo_obj:
                modelo_vehiculo_id = modelo_obj.id

        # Buscar asesor_id
        if datos.get("asesor"):
            asesor_obj = (
                db.query(Analista).filter(Analista.nombre.ilike(f"%{datos['asesor']}%"), Analista.activo).first()
            )
            if asesor_obj:
                asesor_id = asesor_obj.id

        # ============================================
        # CREAR CLIENTE CON FOREIGNKEYS
        # ============================================

        cliente_data = {
            "cedula": datos["cedula"],
            "nombres": datos["nombre"],
            "apellidos": datos.get("apellido", ""),
            "telefono": datos.get("movil", ""),
            "email": datos.get("email", ""),
            "direccion": datos.get("direccion", ""),
            # ForeignKeys
            "concesionario_id": concesionario_id,
            "modelo_vehiculo_id": modelo_vehiculo_id,
            "asesor_id": asesor_id,
            # Campos legacy (mantener por compatibilidad)
            "concesionario": datos.get("concesionario", ""),
            "modelo_vehiculo": datos.get("modelo_vehiculo", ""),
            "marca_vehiculo": datos.get("modelo_vehiculo", "").split(" ")[0] if datos.get("modelo_vehiculo") else "",
            # Financiamiento
            "total_financiamiento": (
                Decimal(str(datos.get("total_financiamiento", 0))) if datos.get("total_financiamiento") else None
            ),
            "cuota_inicial": Decimal(str(datos.get("cuota_inicial", 0))) if datos.get("cuota_inicial") else None,
            "numero_amortizaciones": (
                int(datos.get("numero_amortizaciones", 12)) if datos.get("numero_amortizaciones") else None
            ),
            "modalidad_pago": datos.get("modalidad_pago", "MENSUAL").upper(),
            "fecha_entrega": (
                datetime.strptime(datos["fecha_entrega"], "%Y-%m-%d").date() if datos.get("fecha_entrega") else None
            ),
            # Estado
            "estado": "ACTIVO",
            "activo": True,
            "fecha_registro": datetime.utcnow(),
            "usuario_registro": f"CARGA_MASIVA_USER_{usuario_id}",
        }

        # Verificar si ya existe
        cliente_existente = db.query(Cliente).filter(Cliente.cedula == datos["cedula"]).first()

        if cliente_existente:
            # Actualizar cliente existente
            for key, value in cliente_data.items():
                if key not in ["cedula", "fecha_registro"]:
                    setattr(cliente_existente, key, value)
            cliente_existente.fecha_actualizacion = datetime.utcnow()

            logger.info(f"Cliente actualizado: {datos['cedula']}")
        else:
            # Crear nuevo cliente
            nuevo_cliente = Cliente(**cliente_data)
            db.add(nuevo_cliente)
            db.flush()

            logger.info(f"Cliente creado: {datos['cedula']} (ID: {nuevo_cliente.id})")

        # Registrar en auditoría
        auditoria = Auditoria.registrar(
            usuario_id=usuario_id,
            accion=TipoAccion.CREAR if not cliente_existente else TipoAccion.ACTUALIZAR,
            tabla="Cliente",
            registro_id=cliente_existente.id if cliente_existente else nuevo_cliente.id,
            descripcion=f"Cliente {'actualizado' if cliente_existente else 'creado'} desde carga masiva: {datos['cedula']}",
            datos_nuevos=cliente_data,
            resultado="EXITOSO",
        )
        db.add(auditoria)

    except Exception as e:
        raise Exception(f"Error guardando cliente {datos.get('cedula')}: {str(e)}")


# ============================================
# FUNCIÓN: GUARDAR PAGO DESDE CARGA MASIVA
# ============================================


async def _guardar_pago_desde_carga(datos: Dict[str, Any], db: Session, usuario_id: int):
    """
    Guardar pago articulado con cliente por cédula
    """
    try:
        # ============================================
        # ARTICULACIÓN: Buscar cliente por cédula
        # ============================================

        cliente = db.query(Cliente).filter(Cliente.cedula == datos["cedula"]).first()

        if not cliente:
            raise Exception(f"Cliente con cédula {datos['cedula']} no existe")

        # Verificar que el cliente tenga préstamo activo
        if not cliente.prestamos or len(cliente.prestamos) == 0:
            raise Exception(f"Cliente {datos['cedula']} no tiene préstamos activos")

        # Usar el primer préstamo activo
        prestamo = cliente.prestamos[0]

        # ============================================
        # CREAR PAGO
        # ============================================

        pago_data = {
            "prestamo_id": prestamo.id,
            "monto": Decimal(str(datos["monto_pagado"])),
            "fecha_pago": (
                datetime.strptime(datos["fecha_pago"], "%Y-%m-%d").date()
                if isinstance(datos["fecha_pago"], str)
                else datos["fecha_pago"]
            ),
            "numero_cuota": int(datos.get("numero_cuota", 1)) if datos.get("numero_cuota") else None,
            "referencia": datos.get("documento_pago", ""),
            "metodo_pago": datos.get("metodo_pago", "TRANSFERENCIA").upper(),
            "estado": "CONFIRMADO",
            "registrado_por": usuario_id,
            "fecha_registro": datetime.utcnow(),
        }

        nuevo_pago = Pago(**pago_data)
        db.add(nuevo_pago)
        db.flush()

        logger.info(f"Pago creado para cliente {datos['cedula']}: ${datos['monto_pagado']}")

        # Registrar en auditoría
        auditoria = Auditoria.registrar(
            usuario_id=usuario_id,
            accion=TipoAccion.CREAR,
            tabla="Pago",
            registro_id=nuevo_pago.id,
            descripcion=f"Pago creado desde carga masiva para cliente {datos['cedula']}",
            datos_nuevos=pago_data,
            resultado="EXITOSO",
        )
        db.add(auditoria)

    except Exception as e:
        raise Exception(f"Error guardando pago para {datos.get('cedula')}: {str(e)}")


# ============================================
# ENDPOINT: DESCARGAR TEMPLATE EXCEL
# ============================================


@router.get("/template-excel/{tipo}")
async def descargar_template_excel(
    tipo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📥 Descargar template de Excel con formato establecido

    Tipos:
    - clientes: Template para carga de clientes
    - pagos: Template para carga de pagos
    """
    try:
        if tipo == "clientes":
            # Crear DataFrame con columnas requeridas
            df = pd.DataFrame(
                columns=[
                    "CEDULA IDENTIDAD",
                    "NOMBRE",
                    "APELLIDO",
                    "MOVIL",
                    "CORREO ELECTRONICO",
                    "DIRECCION",
                    "MODELO VEHICULO",
                    "CONCESIONARIO",
                    "TOTAL FINANCIAMIENTO",
                    "CUOTA INICIAL",
                    "NUMERO AMORTIZACIONES",
                    "MODALIDAD PAGO",
                    "FECHA ENTREGA",
                    "USER",
                ]
            )

            # Agregar fila de ejemplo
            df.loc[0] = [
                "V12345678",
                "Juan",
                "Pérez",
                "4241234567",
                "juan.perez@ejemplo.com",
                "Av. Principal, Caracas",
                "Toyota Corolla",
                "AutoCenter Caracas",
                "50000.00",
                "10000.00",
                "24",
                "MENSUAL",
                "2025-01-15",
                "Roberto Martínez",
            ]

            nombre_archivo = "template_clientes.xlsx"

        elif tipo == "pagos":
            # Crear DataFrame para pagos
            df = pd.DataFrame(
                columns=[
                    "CEDULA IDENTIDAD",
                    "FECHA PAGO",
                    "MONTO PAGADO",
                    "NUMERO CUOTA",
                    "DOCUMENTO PAGO",
                    "METODO PAGO",
                ]
            )

            # Agregar fila de ejemplo
            df.loc[0] = [
                "V12345678",
                "2025-01-15",
                "2083.33",
                "1",
                "REF-001234",
                "TRANSFERENCIA",
            ]

            nombre_archivo = "template_pagos.xlsx"
        else:
            raise HTTPException(status_code=400, detail="Tipo inválido. Use 'clientes' o 'pagos'")

        # Guardar en buffer
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Datos")

        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando template: {str(e)}")


# ============================================
# ENDPOINT: OBTENER LISTAS DE CONFIGURACIÓN
# ============================================


@router.get("/opciones-configuracion")
async def obtener_opciones_configuracion(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    📋 Obtener listas de opciones para corrección en línea

    Retorna:
    - Concesionarios activos
    - Analistaes activos
    - Modelos de vehículos activos
    - Modalidades de pago configurables
    """
    try:
        # Obtener concesionarios activos
        concesionarios = db.query(Concesionario).filter(Concesionario.activo).all()

        # Obtener asesores activos
        asesores = db.query(Analista).filter(Analista.activo).all()

        # Obtener modelos de vehículos activos
        modelos = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo).all()

        # Modalidades de pago configurables
        modalidades_pago = [
            {"value": "SEMANAL", "label": "Semanal"},
            {"value": "QUINCENAL", "label": "Quincenal"},
            {"value": "MENSUAL", "label": "Mensual"},
            {"value": "BIMENSUAL", "label": "Bimensual"},
        ]

        return {
            "concesionarios": [{"id": c.id, "nombre": c.nombre} for c in concesionarios],
            "asesores": [{"id": a.id, "nombre": a.nombre_completo} for a in asesores],
            "modelos_vehiculos": [{"id": m.id, "modelo": m.modelo} for m in modelos],
            "modalidades_pago": modalidades_pago,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo opciones: {str(e)}")


# ============================================
# ENDPOINT: DASHBOARD DE CARGA MASIVA
# ============================================


@router.get("/dashboard")
async def dashboard_carga_masiva(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    📊 Dashboard de carga masiva

    Muestra:
    - Historial de cargas
    - Estadísticas de errores
    - Registros pendientes de corrección
    """
    try:
        # Obtener últimas cargas del usuario
        auditorias = (
            db.query(Auditoria)
            .filter(
                Auditoria.usuario_id == current_user.id,
                Auditoria.tabla == "CargaMasiva",
            )
            .order_by(Auditoria.fecha.desc())
            .limit(10)
            .all()
        )

        return {
            "titulo": "📊 Dashboard de Carga Masiva",
            "usuario": f"{current_user.nombre} {current_user.apellido}".strip(),
            "historial_cargas": [
                {
                    "fecha": a.fecha,
                    "descripcion": a.descripcion,
                    "resultado": a.resultado,
                    "datos": a.datos_nuevos,
                }
                for a in auditorias
            ],
            "instrucciones": {
                "paso_1": "📤 Subir archivo Excel con formato establecido",
                "paso_2": "🔍 Revisar dashboard de errores",
                "paso_3": "✏️ Corregir errores en línea",
                "paso_4": "💾 Guardar registros corregidos en base de datos",
            },
            "tipos_carga": [
                {
                    "tipo": "clientes",
                    "descripcion": "Carga masiva de clientes con financiamiento",
                    "template": "/api/v1/carga-masiva/template-excel/clientes",
                },
                {
                    "tipo": "pagos",
                    "descripcion": "Carga masiva de pagos (articulados por cédula)",
                    "template": "/api/v1/carga-masiva/template-excel/pagos",
                },
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo dashboard: {str(e)}")
