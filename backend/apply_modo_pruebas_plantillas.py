"""Aplica en notificaciones.py: helpers + modo_pruebas en get_plantilla_asunto_cuerpo."""
import re

path = "app/api/v1/endpoints/notificaciones.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Insertar helpers justo antes de "def get_plantilla_asunto_cuerpo"
helpers = '''
def _item_placeholder_pruebas() -> dict:
    """Item con valores placeholder para modo pruebas: las variables se mantienen como {{nombre}}, etc."""
    return {
        "nombre": "{{nombre}}",
        "cedula": "{{cedula}}",
        "fecha_vencimiento": "{{fecha_vencimiento}}",
        "numero_cuota": "{{numero_cuota}}",
        "monto_cuota": "{{monto}}",
        "dias_atraso": "{{dias_atraso}}",
    }


def _contexto_cobranza_placeholder() -> dict:
    """Contexto de cobranza con placeholders para modo pruebas (variables visibles, sin datos reales)."""
    return {
        "CLIENTES.TRATAMIENTO": "{{CLIENTES.TRATAMIENTO}}",
        "CLIENTES.NOMBRE_COMPLETO": "{{CLIENTES.NOMBRE_COMPLETO}}",
        "CLIENTES.CEDULA": "{{CLIENTES.CEDULA}}",
        "PRESTAMOS.ID": "{{PRESTAMOS.ID}}",
        "IDPRESTAMO": "{{IDPRESTAMO}}",
        "NUMEROCORRELATIVO": "{{NUMEROCORRELATIVO}}",
        "TOTAL_ADEUDADO": "{{TOTAL_ADEUDADO}}",
        "FECHA_CARTA": "{{FECHA_CARTA}}",
        "LOGO_URL": "{{LOGO_URL}}",
        "CUOTAS.VENCIMIENTOS": [
            {"numero_cuota": "{{CUOTA.NUMERO}}", "fecha_vencimiento": "{{CUOTA.FECHA_VENCIMIENTO}}", "monto": "{{CUOTA.MONTO}}"}
        ],
        "cuotas_vencidas": [
            {"numero": "{{CUOTA.NUMERO}}", "fecha_vencimiento": "{{CUOTA.FECHA_VENCIMIENTO}}", "monto": "{{CUOTA.MONTO}}"}
        ],
    }


'''

# Si ya están los helpers, no duplicar
if "_item_placeholder_pruebas" not in content:
    content = content.replace(
        "def get_plantilla_asunto_cuerpo(db: Session, plantilla_id: Optional[int], item: dict, asunto_default: str, cuerpo_default: str) -> tuple:",
        helpers + "def get_plantilla_asunto_cuerpo(db: Session, plantilla_id: Optional[int], item: dict, asunto_default: str, cuerpo_default: str, modo_pruebas: bool = False) -> tuple:",
    )
else:
    content = content.replace(
        "def get_plantilla_asunto_cuerpo(db: Session, plantilla_id: Optional[int], item: dict, asunto_default: str, cuerpo_default: str) -> tuple:",
        "def get_plantilla_asunto_cuerpo(db: Session, plantilla_id: Optional[int], item: dict, asunto_default: str, cuerpo_default: str, modo_pruebas: bool = False) -> tuple:",
    )

# 2) Tras el docstring, añadir: if modo_pruebas: item = ... y en COBRANZA usar placeholder si modo_pruebas
old_block = '''    ({{TABLA.CAMPO}} y bloque {{#CUOTAS.VENCIMIENTOS}}). Si no, se usa _sustituir_variables.
    """
    if plantilla_id:
        plantilla = db.get(PlantillaNotificacion, plantilla_id)
        if plantilla and plantilla.activa:
            contexto_cobranza = item.get("contexto_cobranza")
            if getattr(plantilla, "tipo", None) == "COBRANZA" and isinstance(contexto_cobranza, dict):
'''

new_block = '''    ({{TABLA.CAMPO}} y bloque {{#CUOTAS.VENCIMIENTOS}}). Si no, se usa _sustituir_variables.
    Si modo_pruebas=True, se usan placeholders para que las variables se vean (no datos reales).
    """
    if modo_pruebas:
        item = {**_item_placeholder_pruebas(), **{k: "{{" + str(k) + "}}" for k, v in item.items() if k != "contexto_cobranza"}}
    if plantilla_id:
        plantilla = db.get(PlantillaNotificacion, plantilla_id)
        if plantilla and plantilla.activa:
            contexto_cobranza = item.get("contexto_cobranza")
            if getattr(plantilla, "tipo", None) == "COBRANZA":
                if modo_pruebas:
                    contexto_cobranza = _contexto_cobranza_placeholder()
                elif not isinstance(contexto_cobranza, dict):
                    contexto_cobranza = None
            if getattr(plantilla, "tipo", None) == "COBRANZA" and isinstance(contexto_cobranza, dict):
'''

content = content.replace(old_block, new_block)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: notificaciones.py actualizado")
