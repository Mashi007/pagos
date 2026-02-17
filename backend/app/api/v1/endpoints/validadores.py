"""
Endpoints de validadores (cédula, teléfono, email, fecha).
GET /validadores/configuracion-validadores devuelve la configuración para el frontend.
Datos desde BD si existe clave configuracion; si no, estructura mínima (config de app).
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
        # Validación básica de formato (compatible con frontend)
        email_pattern = re.compile(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        valor_lower = valor.lower()
        if email_pattern.match(valor_lower):
            return {
                "validacion": {
                    "valido": True,
                    "valor_formateado": valor_lower,
                }
            }
        return {
            "validacion": {
                "valido": False,
                "error": "Formato de email inválido",
                "sugerencia": "Use formato usuario@dominio.com",
            }
        }

    # Otros campos: aceptar por ahora (stub)
    return {
        "validacion": {
            "valido": True,
            "valor_formateado": valor,
        }
    }
