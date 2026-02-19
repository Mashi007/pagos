"""
Endpoints de validadores (cédula, teléfono, email, fecha).
GET /validadores/configuracion-validadores devuelve la configuración para el frontend.
Datos desde BD si existe clave configuracion; si no, estructura mínima (config de app).

Validadores disponibles:
- validate_cedula: Validación de cédula venezolana (V/E/J/Z + 6-11 dígitos)
- validate_phone: Validación de teléfono venezolano
- validate_email: Validación de email (RFC 5322)
- validate_fecha: Validación de fecha DD/MM/YYYY
"""
from datetime import datetime
from typing import Any

import re

from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.configuracion import Configuracion

router = APIRouter(dependencies=[Depends(get_current_user)])

CLAVE_VALIDADORES = "configuracion_validadores"


def validate_cedula(cedula: str) -> dict[str, Any]:
    """
    Valida una cédula venezolana.
    Formato: [V|E|J|Z] + 6-11 dígitos (ej: V12345678, E1234567)
    
    Returns:
        dict con: {"valido": bool, "valor_formateado": str, "error": str or None}
    """
    if not cedula:
        return {"valido": False, "error": "Cédula no puede estar vacía"}
    
    cedula_clean = cedula.strip().upper().replace("-", "").replace(" ", "")
    
    # Patrón: [VEGJ] + 6-11 dígitos (ej: V12345678)
    pattern = r"^([VEGJ])(\d{6,11})$"
    match = re.match(pattern, cedula_clean)
    
    if not match:
        return {
            "valido": False,
            "valor_formateado": cedula_clean,
            "error": "Cédula inválida. Formato: [V|E|J|Z] + 6-11 dígitos (ej: V12345678)"
        }
    
    # Formatear: V-12345678
    tipo, numero = match.groups()
    valor_formateado = f"{tipo}-{numero}"
    
    return {
        "valido": True,
        "valor_formateado": valor_formateado,
    }


def validate_phone(phone: str) -> dict[str, Any]:
    """
    Valida un teléfono venezolano.
    Formatos válidos:
    - 0414-1234567 (móvil)
    - 04141234567 (móvil sin guiones)
    - 0212-1234567 (fijo)
    - 02121234567 (fijo sin guiones)
    
    Returns:
        dict con: {"valido": bool, "valor_formateado": str, "error": str or None}
    """
    if not phone:
        return {"valido": False, "error": "Teléfono no puede estar vacío"}
    
    phone_clean = phone.strip().replace(" ", "").replace("-", "")
    
    # Patrón: 04XX9999999 (11 dígitos) o 02XX9999999 (11 dígitos)
    if not re.match(r"^0[24]\d{9}$", phone_clean):
        return {
            "valido": False,
            "valor_formateado": phone_clean,
            "error": "Teléfono inválido. Formato: 0XXX-9999999 (11 dígitos, comenzando con 04 o 02)"
        }
    
    # Formatear: 0414-1234567
    valor_formateado = f"{phone_clean[:4]}-{phone_clean[4:]}"
    
    return {
        "valido": True,
        "valor_formateado": valor_formateado,
    }


def validate_email(email: str) -> dict[str, Any]:
    """
    Valida un email según RFC 5322 (versión simplificada).
    
    Returns:
        dict con: {"valido": bool, "valor_formateado": str, "error": str or None}
    """
    if not email:
        return {"valido": False, "error": "Email no puede estar vacío"}
    
    email_clean = email.strip().lower()
    
    # Patrón RFC 5322 simplificado
    email_pattern = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        re.IGNORECASE
    )
    
    if not email_pattern.match(email_clean):
        return {
            "valido": False,
            "valor_formateado": email_clean,
            "error": "Email inválido. Formato: usuario@dominio.com"
        }
    
    return {
        "valido": True,
        "valor_formateado": email_clean,
    }


def validate_fecha(fecha: str) -> dict[str, Any]:
    """
    Valida una fecha en formato DD/MM/YYYY.
    
    Returns:
        dict con: {"valido": bool, "valor_formateado": str, "error": str or None}
    """
    if not fecha:
        return {"valido": False, "error": "Fecha no puede estar vacía"}
    
    fecha_clean = fecha.strip()
    
    # Patrón: DD/MM/YYYY
    pattern = r"^(\d{2})/(\d{2})/(\d{4})$"
    match = re.match(pattern, fecha_clean)
    
    if not match:
        return {
            "valido": False,
            "valor_formateado": fecha_clean,
            "error": "Fecha inválida. Formato: DD/MM/YYYY (ej: 01/01/2024)"
        }
    
    dia, mes, anio = match.groups()
    dia, mes, anio = int(dia), int(mes), int(anio)
    
    # Validar rango
    if not (1 <= mes <= 12):
        return {
            "valido": False,
            "valor_formateado": fecha_clean,
            "error": f"Mes inválido: {mes} (debe estar entre 01 y 12)"
        }
    
    if not (1 <= dia <= 31):
        return {
            "valido": False,
            "valor_formateado": fecha_clean,
            "error": f"Día inválido: {dia} (debe estar entre 01 y 31)"
        }
    
    # Validar si la fecha existe (considerando años bisiestos)
    try:
        datetime(anio, mes, dia)
    except ValueError as e:
        return {
            "valido": False,
            "valor_formateado": fecha_clean,
            "error": f"Fecha no válida: {e}"
        }
    
    return {
        "valido": True,
        "valor_formateado": fecha_clean,
    }


def _stub_validador(descripcion: str, ejemplos_validos: list, ejemplos_invalidos: list) -> dict:
    return {
        "descripcion": descripcion,
        "paises_soportados": {
            "venezuela": {
                "codigo": "+58",
                "formato": "",
                "prefijos_validos": [],
                "longitud": "",
                "requisitos": {},
                "ejemplos_validos": ejemplos_validos,
                "ejemplos_invalidos": ejemplos_invalidos,
            }
        },
        "auto_formateo": True,
        "validacion_tiempo_real": True,
    }


def _config_validadores_default() -> dict:
    """Estructura por defecto de validadores (sin datos mock; definición de reglas)."""
    return {
        "titulo": "Configuración de validadores",
        "fecha_consulta": datetime.utcnow().isoformat() + "Z",
        "consultado_por": "sistema",
        "validadores_disponibles": {
            "telefono": _stub_validador(
                "Teléfono Venezuela (+58)",
                ["04141234567", "02121234567"],
                ["123", "abc"],
            ),
            "cedula": _stub_validador(
                "Cédula Venezuela (E, V, J, Z + 6-11 dígitos)",
                ["V12345678", "E12345678", "J1234567", "Z999999999"],
                ["123", "12345678901"],
            ),
            "fecha": _stub_validador(
                "Fecha DD/MM/YYYY",
                ["01/01/2020", "31/12/2024"],
                ["2020-01-01", "32/13/2020"],
            ),
            "email": {
                "descripcion": "Email válido",
                "caracteristicas": {
                    "normalizacion": "lowercase",
                    "limpieza": "trim",
                    "validacion": "RFC 5322",
                    "dominios_bloqueados": [],
                },
                "ejemplos_validos": ["user@example.com"],
                "ejemplos_invalidos": ["invalid", "@nodomain"],
                "auto_formateo": True,
                "validacion_tiempo_real": True,
            },
        },
        "reglas_negocio": {},
        "configuracion_frontend": {},
        "endpoints_validacion": {},
    }


@router.get("/configuracion-validadores")
def get_configuracion_validadores(db: Session = Depends(get_db)):
    """
    Configuración de validadores desde BD (clave configuracion_validadores) o por defecto.
    """
    try:
        row = db.get(Configuracion, CLAVE_VALIDADORES)
        if row and row.valor:
            import json
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return _config_validadores_default()


class ValidarCampoRequest(BaseModel):
    """Request para validar un campo (email, teléfono, etc.)."""
    campo: str
    valor: str
    pais: str | None = None


@router.post(
    "/validar-campo",
    summary="[Stub] Valida un campo (email, etc.) con reglas básicas; no sustituye validación de negocio.",
)
def post_validar_campo(
    payload: ValidarCampoRequest = Body(...),
    db: Session = Depends(get_db),
):
    """
    Valida el valor de un campo. Stub: solo validación de formato (ej. email).
    Devuelve validacion.valido, valor_formateado, error y sugerencia para el frontend.
    """
    campo = (payload.campo or "").strip().lower()
    valor = (payload.valor or "").strip()

    if campo == "email":
        result = validate_email(valor)
        return {"validacion": result}
    elif campo == "cedula":
        result = validate_cedula(valor)
        return {"validacion": result}
    elif campo == "telefono":
        result = validate_phone(valor)
        return {"validacion": result}
    elif campo == "fecha":
        result = validate_fecha(valor)
        return {"validacion": result}

    # Otros campos: aceptar por ahora (stub)
    return {
        "validacion": {
            "valido": True,
            "valor_formateado": valor,
        }
    }
