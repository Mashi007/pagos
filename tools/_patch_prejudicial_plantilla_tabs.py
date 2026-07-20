# -*- coding: utf-8 -*-
"""Patch notificaciones_tabs defaults + docstring for PREJUDICIAL plantilla unica."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABS = ROOT / "backend/app/api/v1/endpoints/notificaciones_tabs/routes.py"


def main() -> None:
    t = TABS.read_text(encoding="utf-8")

    # --- enviar_notificaciones_prejudicial: docstring + asunto/cuerpo ---
    sig = (
        "def enviar_notificaciones_prejudicial(\n"
        "    fecha_caracas: Optional[str] = _FC_Q,\n"
        "    db: Session = Depends(get_db),\n"
        "):\n"
    )
    idx = t.find(sig)
    if idx < 0:
        raise SystemExit("missing enviar_notificaciones_prejudicial signature")

    idx_fecha = t.find("    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)", idx)
    if idx_fecha < 0:
        raise SystemExit("missing fecha_ref after signature")

    new_head = (
        sig
        + '    """Envio MANUAL de correos PREJUDICIAL (60 dias o mas). '
        "Sin cron ni enviar-todas; solo este POST o enviar-caso-manual. "
        'Respeta config envios (habilitado/CCO) desde BD."""\n'
    )

    rest = t[idx_fecha:]
    pat = re.compile(
        r"(    fecha_ref = _fecha_referencia_desde_query\(fecha_caracas\)\n"
        r"    config_envios = get_notificaciones_envios_config\(db\)\n"
        r"    items = build_prejudicial_items\(db, fecha_referencia=fecha_ref\)\n"
        r"    asunto = \".*?\"\n"
        r"    cuerpo = \(\n(?:.*?\n)*?    \)\n)",
        re.DOTALL,
    )
    if not pat.match(rest):
        raise SystemExit("asunto/cuerpo block not matched")

    new_block = (
        "    fecha_ref = _fecha_referencia_desde_query(fecha_caracas)\n"
        "    from app.services.notificacion_plantilla_prejudicial import (\n"
        "        ASUNTO_PREJUDICIAL_FALLBACK,\n"
        "        CUERPO_PREJUDICIAL_FALLBACK,\n"
        "        asegurar_modulo_prejudicial,\n"
        "    )\n"
        "    try:\n"
        "        asegurar_modulo_prejudicial(db, forzar_contenido_plantilla=False)\n"
        "        db.commit()\n"
        "    except Exception:\n"
        "        db.rollback()\n"
        "    config_envios = get_notificaciones_envios_config(db)\n"
        "    items = build_prejudicial_items(db, fecha_referencia=fecha_ref)\n"
        "    asunto = ASUNTO_PREJUDICIAL_FALLBACK\n"
        "    cuerpo = CUERPO_PREJUDICIAL_FALLBACK\n"
    )
    rest2 = pat.sub(new_block, rest, count=1)
    rest2 = re.sub(
        r'return \{"mensaje": "Env.*?de notificaciones prejudiciales finalizado\.", \*\*res\}',
        'return {"mensaje": "Envio de notificaciones prejudiciales finalizado.", **res}',
        rest2,
        count=1,
    )
    t = t[:idx] + new_head + rest2

    # --- defaults en enviar-caso-manual ---
    m1 = t.find("    asunto_prej = ")
    m2 = t.find("    cuerpo_mas = (", m1 if m1 >= 0 else 0)
    if m1 < 0 or m2 < 0:
        raise SystemExit("cannot find asunto_prej / cuerpo_mas markers")
    replacement = (
        "    from app.services.notificacion_plantilla_prejudicial import (\n"
        "        ASUNTO_PREJUDICIAL_FALLBACK as asunto_prej,\n"
        "        CUERPO_PREJUDICIAL_FALLBACK as cuerpo_prej,\n"
        "    )\n"
        '    asunto_mas = "Comunicado oficial - Rapicredit"\n'
    )
    t = t[:m1] + replacement + t[m2:]

    TABS.write_text(t, encoding="utf-8")
    print("OK patched", TABS)


if __name__ == "__main__":
    main()
