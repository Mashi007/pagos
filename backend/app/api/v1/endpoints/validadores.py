"""
Endpoints de validadores (cédula, teléfono, email, fecha).
GET /validadores/configuracion-validadores devuelve la configuración para el frontend.
Sin implementación completa se devuelve stub para evitar 404 en Configuración > Validadores.
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter

router = APIRouter()


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


@router.get("/configuracion-validadores")
def get_configuracion_validadores():
    """
    Configuración de validadores para el frontend (ValidadoresConfig).
    Estructura mínima para que la UI no falle; sin backend de validación real.
    """
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
