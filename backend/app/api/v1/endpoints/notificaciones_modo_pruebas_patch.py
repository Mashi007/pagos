# --- PATCH: En modo pruebas las plantillas se cargan con variables (no datos reales) ---
# Aplicar en notificaciones.py y notificaciones_tabs.py

# ========== 1) En notificaciones.py: añadir ANTES de "def get_plantilla_asunto_cuerpo" estas funciones:

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


# ========== 2) En notificaciones.py: cambiar la firma y el inicio de get_plantilla_asunto_cuerpo:

# ANTES:
# def get_plantilla_asunto_cuerpo(db: Session, plantilla_id: Optional[int], item: dict, asunto_default: str, cuerpo_default: str) -> tuple:
#     """
#     Si plantilla_id es válido ...
#     """
#     if plantilla_id:

# DESPUÉS:
# def get_plantilla_asunto_cuerpo(
#     db: Session,
#     plantilla_id: Optional[int],
#     item: dict,
#     asunto_default: str,
#     cuerpo_default: str,
#     modo_pruebas: bool = False,
# ) -> tuple:
#     """
#     Si plantilla_id es válido ... Si modo_pruebas=True, se usan placeholders (variables visibles).
#     """
#     if modo_pruebas:
#         item = {**_item_placeholder_pruebas(), **{k: "{{" + str(k) + "}}" for k, v in item.items() if k not in ("contexto_cobranza",)}}
#     if plantilla_id:
#         plantilla = db.get(PlantillaNotificacion, plantilla_id)
#         if plantilla and plantilla.activa:
#             contexto_cobranza = item.get("contexto_cobranza")
#             if getattr(plantilla, "tipo", None) == "COBRANZA":
#                 if modo_pruebas:
#                     contexto_cobranza = _contexto_cobranza_placeholder()
#                 elif not isinstance(contexto_cobranza, dict):
#                     contexto_cobranza = None
#             if getattr(plantilla, "tipo", None) == "COBRANZA" and isinstance(contexto_cobranza, dict):
#                 from app.services.plantilla_cobranza import render_plantilla_cobranza
#                 if "LOGO_URL" not in contexto_cobranza or contexto_cobranza.get("LOGO_URL") == "{{LOGO_URL}}":
#                     try:
#                         from app.core.config import settings
#                         base = (getattr(settings, "FRONTEND_PUBLIC_URL", None) or "https://rapicredit.onrender.com/pagos").rstrip("/")
#                     except Exception:
#                         base = "https://rapicredit.onrender.com/pagos"
#                     contexto_cobranza["LOGO_URL"] = f"{base}/logos/rapicredit-public.png"
#                 asunto = render_plantilla_cobranza(plantilla.asunto, contexto_cobranza)
#                 cuerpo = render_plantilla_cobranza(plantilla.cuerpo, contexto_cobranza)
#                 return (asunto, cuerpo)
#             asunto = _sustituir_variables(plantilla.asunto, item)
#             cuerpo = _sustituir_variables(plantilla.cuerpo, item)
#             return (asunto, cuerpo)
#     ... resto igual (default con item que ya puede ser placeholder) ...


# ========== 3) En notificaciones_tabs.py: al llamar get_plantilla_asunto_cuerpo, pasar modo_pruebas:

# ANTES:
#         asunto, cuerpo = get_plantilla_asunto_cuerpo(db, plantilla_id, item, asunto_base, cuerpo_base)

# DESPUÉS:
#         asunto, cuerpo = get_plantilla_asunto_cuerpo(
#             db, plantilla_id, item, asunto_base, cuerpo_base, modo_pruebas=usar_solo_pruebas
#         )
