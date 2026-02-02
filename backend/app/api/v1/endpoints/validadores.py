"""
Endpoints de validadores (cédula, teléfono, email, fecha).
GET /validadores/configuracion-validadores devuelve la configuración para el frontend.
Datos desde BD si existe clave configuracion; si no, estructura mínima (config de app).
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
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
                "Cédula Venezuela",
                ["V12345678", "E12345678"],
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
