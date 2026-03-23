"""One-off patch: prueba paquete completo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NT = ROOT / "app" / "api" / "v1" / "endpoints" / "notificaciones_tabs.py"
NF = ROOT / "app" / "api" / "v1" / "endpoints" / "notificaciones.py"


def patch_tabs() -> None:
    t = NT.read_text(encoding="utf-8")

    old_sig = """def _enviar_correos_items(
    items: List[dict],
    asunto_base: str,
    cuerpo_base: str,
    config_envios: dict,
    get_tipo_for_item: Callable[[dict], str],
    db,
) -> dict:"""

    new_sig = """def _enviar_correos_items(
    items: List[dict],
    asunto_base: str,
    cuerpo_base: str,
    config_envios: dict,
    get_tipo_for_item: Callable[[dict], str],
    db,
    forzar_destinos_prueba: Optional[List[str]] = None,
) -> dict:"""

    if old_sig not in t:
        raise SystemExit("signature not found")
    t = t.replace(old_sig, new_sig, 1)

    old0 = """    sync_email_config_from_db()
    modo_pruebas = coerce_modo_pruebas_notificaciones(config_envios.get("modo_pruebas"))"""

    new0 = """    if forzar_destinos_prueba is not None:
        if len(items) != 1:
            raise ValueError("forzar_destinos_prueba requiere exactamente un item")
    sync_email_config_from_db()
    modo_pruebas = coerce_modo_pruebas_notificaciones(config_envios.get("modo_pruebas"))"""

    if old0 not in t:
        raise SystemExit("sync block not found")
    t = t.replace(old0, new0, 1)

    old_dest = """        if usar_solo_pruebas:
            to_email = [email_pruebas]
            bcc_list = None
        elif bloqueo_pruebas_sin_email:"""

    new_dest = """        if forzar_destinos_prueba is not None:
            to_email = [e.strip() for e in forzar_destinos_prueba if e and isinstance(e, str) and "@" in e.strip()]
            bcc_list = None
        elif usar_solo_pruebas:
            to_email = [email_pruebas]
            bcc_list = None
        elif bloqueo_pruebas_sin_email:"""

    if old_dest not in t:
        raise SystemExit("dest block not found")
    t = t.replace(old_dest, new_dest, 1)

    old_send = """            ok, msg = send_email(
                to_email,
                asunto,
                cuerpo,
                body_html=body_html,
                bcc_emails=bcc_list or None,
                attachments=attachments,
                servicio="notificaciones",
                tipo_tab=tipo_tab_envio,
            )"""

    new_send = """            ok, msg = send_email(
                to_email,
                asunto,
                cuerpo,
                body_html=body_html,
                bcc_emails=bcc_list or None,
                attachments=attachments,
                servicio="notificaciones",
                tipo_tab=tipo_tab_envio,
                respetar_destinos_manuales=bool(forzar_destinos_prueba),
            )"""

    if old_send not in t:
        raise SystemExit("send_email block not found")
    t = t.replace(old_send, new_send, 1)

    old_wa = """        if telefono and email_sent_ok:
            ok, _ = send_whatsapp_text(telefono, cuerpo)"""

    new_wa = """        if telefono and email_sent_ok and forzar_destinos_prueba is None:
            ok, _ = send_whatsapp_text(telefono, cuerpo)"""

    if old_wa not in t:
        raise SystemExit("whatsapp block not found")
    t = t.replace(old_wa, new_wa, 1)

    NT.write_text(t, encoding="utf-8")
    print("patched", NT)


def append_endpoint() -> None:
    t = NF.read_text(encoding="utf-8")
    if "enviar-prueba-paquete" in t:
        print("endpoint exists")
        return

    block = r'''

# --- Prueba de paquete completo (plantilla + Carta PDF + PDFs fijos) ---

TIPOS_PRUEBA_PAQUETE = frozenset({
    "PAGO_1_DIA_ATRASADO",
    "PAGO_3_DIAS_ATRASADO",
    "PAGO_5_DIAS_ATRASADO",
    "PREJUDICIAL",
})


def _primer_item_ejemplo_por_tipo(data: dict, tipo: str) -> Optional[dict]:
    """Un registro real de BD para armar el cuerpo y los PDFs como en producción."""
    if tipo == "PAGO_1_DIA_ATRASADO":
        return data["dias_1_retraso"][0] if data.get("dias_1_retraso") else None
    if tipo == "PAGO_3_DIAS_ATRASADO":
        return data["dias_3_retraso"][0] if data.get("dias_3_retraso") else None
    if tipo == "PAGO_5_DIAS_ATRASADO":
        return data["dias_5_retraso"][0] if data.get("dias_5_retraso") else None
    if tipo == "PREJUDICIAL":
        return data["prejudicial"][0] if data.get("prejudicial") else None
    return None


@router.post("/enviar-prueba-paquete")
def post_enviar_prueba_paquete(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Envía un correo de prueba con el mismo contenido que producción:
    asunto/cuerpo desde plantilla vinculada en Configuración > Envíos,
    Carta_Cobranza.pdf (plantilla PDF cobranza) y PDF(s) fijos (documentos anexos).
    Requiere al menos un cliente en el criterio para datos reales.
    Body: { "tipo": "PAGO_1_DIA_ATRASADO", "destinos": ["a@b.com"] }
    """
    from app.api.v1.endpoints import notificaciones_tabs as nt

    tipo = (payload.get("tipo") or "PAGO_1_DIA_ATRASADO").strip()
    if tipo not in TIPOS_PRUEBA_PAQUETE:
        raise HTTPException(
            status_code=422,
            detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PRUEBA_PAQUETE))}",
        )
    raw_dest = payload.get("destinos") or payload.get("emails") or []
    if isinstance(raw_dest, str):
        destinos = [raw_dest]
    elif isinstance(raw_dest, list):
        destinos = [str(x).strip() for x in raw_dest if x]
    else:
        destinos = [str(raw_dest).strip()] if raw_dest else []
    destinos = [d for d in destinos if d and "@" in d]
    if not destinos:
        raise HTTPException(status_code=422, detail="Indique al menos un destino en destinos (lista de emails).")

    data = get_notificaciones_tabs_data(db)
    item = _primer_item_ejemplo_por_tipo(data, tipo)
    if not item:
        raise HTTPException(
            status_code=404,
            detail="No hay datos de ejemplo en BD para este criterio. Debe existir al menos un cliente en la lista correspondiente.",
        )

    config_envios = get_notificaciones_envios_config(db)

    if tipo in ("PAGO_1_DIA_ATRASADO", "PAGO_3_DIAS_ATRASADO", "PAGO_5_DIAS_ATRASADO"):
        get_tipo = nt._tipo_retrasadas
        asunto = "Cuenta con cuota atrasada - Rapicredit"
        cuerpo = (
            "Estimado/a {nombre} (cédula {cedula}),\n\n"
            "Le recordamos que tiene una cuota en mora.\n"
            "Fecha de vencimiento: {fecha_vencimiento}\n"
            "Número de cuota: {numero_cuota}\n"
            "Monto: {monto}\n\n"
            "Por favor regularice su pago lo antes posible.\n\n"
            "Saludos,\nRapicredit"
        )
    else:
        get_tipo = nt._tipo_prejudicial
        asunto = "Aviso prejudicial - Rapicredit"
        cuerpo = (
            "Estimado/a {nombre} (cédula {cedula}),\n\n"
            "Le informamos que su cuenta presenta varias cuotas en mora.\n"
            "Fecha de vencimiento de referencia: {fecha_vencimiento}\n"
            "Cuota de referencia: {numero_cuota}\n"
            "Monto de referencia: {monto}\n\n"
            "Por favor contacte a la entidad para regularizar su situación.\n\n"
            "Saludos,\nRapicredit"
        )

    try:
        res = nt._enviar_correos_items(
            [item],
            asunto,
            cuerpo,
            config_envios,
            get_tipo,
            db,
            forzar_destinos_prueba=destinos,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    res = dict(res)
    res["mensaje"] = "Prueba de paquete completo enviada (plantilla + PDF carta + PDFs fijos)."
    res["tipo"] = tipo
    res["destinos"] = destinos
    return res
'''

    NF.write_text(t.rstrip() + "\n" + block + "\n", encoding="utf-8")
    print("appended", NF)


if __name__ == "__main__":
    patch_tabs()
    append_endpoint()
