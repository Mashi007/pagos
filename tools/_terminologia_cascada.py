# -*- coding: utf-8 -*-
"""Unifica terminologia: cascada (waterfall); mantiene alias fifo donde rompe API."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_pagos() -> None:
    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
    t = p.read_text(encoding="utf-8", errors="replace")

    t = t.replace("_estado_pago_tras_aplicar_fifo", "_estado_pago_tras_aplicar_cascada")

    # Alias compatibilidad interna / integraciones
    marker = "def _estado_pago_tras_aplicar_cascada(cuotas_completadas: int, cuotas_parciales: int) -> str:"
    if marker not in t:
        raise SystemExit("pagos.py: no se encontro def _estado_pago_tras_aplicar_cascada")
    # Buscar cierre de funcion: siguiente "def " a nivel modulo tras 4584 - insertar alias despues del return de _estado_pago_tras_aplicar_cascada
    # En su lugar: anadir alias justo despues de la linea del def si ya existe duplicado - mas simple anadir al final del archivo antes de ultima linea
    alias_line = "\n\n# Compat: nombre historico\n_estado_pago_tras_aplicar_fifo = _estado_pago_tras_aplicar_cascada\n"
    if "_estado_pago_tras_aplicar_fifo = _estado_pago_tras_aplicar_cascada" not in t:
        t = t.rstrip() + alias_line

    subs = [
        ("Los pagos válidos se aplican a cuotas del préstamo (FIFO) en el mismo request.",
         "Los pagos válidos se aplican a cuotas del préstamo (asignación en cascada) en el mismo request."),
        ('"fifo: ademas monto>0, prestamo_id, no ANULADO_IMPORT (cola del job). "',
         '"cascada (alias: fifo): ademas monto>0, prestamo_id, no ANULADO_IMPORT (cola del job). "'),
        ('"sin_cupo: como fifo y sin cupo aplicable en cuotas PENDIENTE/MORA/PARCIAL."',
         '"sin_cupo: como cascada/fifo y sin cupo aplicable en cuotas PENDIENTE/MORA/PARCIAL."'),
        ("if c not in (\"todos\", \"fifo\", \"sin_cupo\"):",
         "if c not in (\"todos\", \"fifo\", \"cascada\", \"sin_cupo\"):"),
        ('raise HTTPException(status_code=400, detail="cohorte debe ser todos, fifo o sin_cupo")',
         'raise HTTPException(status_code=400, detail="cohorte debe ser todos, fifo, cascada (alias de fifo) o sin_cupo")'),
        ("        # [C3] Aplicar FIFO a cuotas en la misma transacción para que préstamos y estado de cuenta se actualicen",
         "        # [C3] Aplicar cascada a cuotas en la misma transacción para que préstamos y estado de cuenta se actualicen"),
        ("Evita marcar PAGADO sin cuota_pagos (inconsistencia y bloqueo del job FIFO).",
         "Evita marcar PAGADO sin cuota_pagos (inconsistencia y bloqueo del job en cascada)."),
        ("excluir la cuota bloqueaba el FIFO y los pagos quedaban sin aplicar.",
         "excluir la cuota bloqueaba la cascada y los pagos quedaban sin aplicar."),
        (".order_by(Cuota.numero_cuota.asc())  # FIFO: primero las cuotas más antiguas (numero_cuota menor), luego las siguientes",
         ".order_by(Cuota.numero_cuota.asc())  # Cascada: primero las cuotas más antiguas (numero_cuota menor), luego las siguientes"),
        ('"Use POST /prestamos/{id}/reaplicar-fifo-aplicacion para reconstruir."',
         '"Use POST /prestamos/{id}/reaplicar-cascada-aplicacion (o .../reaplicar-fifo-aplicacion) para reconstruir."'),
        ("# Cuota aún abierta: limpiar fecha_pago residual para no bloquear futuras aplicaciones FIFO.",
         "# Cuota aún abierta: limpiar fecha_pago residual para no bloquear futuras aplicaciones en cascada."),
    ]
    for a, b in subs:
        if a in t:
            t = t.replace(a, b)
        else:
            print("skip subs (missing):", a[:60])

    # cohorte: normalizar cascada -> fifo
    needle = '    c = (cohorte or "todos").strip().lower()\n\n    if c not in'
    if needle in t:
        t = t.replace(
            needle,
            '    c = (cohorte or "todos").strip().lower()\n\n    if c == "cascada":\n\n        c = "fifo"\n\n    if c not in',
            1,
        )
    else:
        # variante sin doble salto
        needle2 = '    c = (cohorte or "todos").strip().lower()\n    if c not in'
        if needle2 in t:
            t = t.replace(
                needle2,
                '    c = (cohorte or "todos").strip().lower()\n    if c == "cascada":\n        c = "fifo"\n    if c not in',
                1,
            )
        else:
            print("WARN: cohorte block not patched")

    p.write_text(t, encoding="utf-8", newline="\n")
    print("patched pagos.py")


def patch_prestamos() -> None:
    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
    t = p.read_text(encoding="utf-8", errors="replace")

    # Rutas alias cascada (misma funcion)
    old = '@router.post("/{prestamo_id}/reaplicar-fifo-aplicacion", response_model=dict)\ndef reaplicar_fifo_aplicacion_prestamo('
    new = (
        '@router.post("/{prestamo_id}/reaplicar-fifo-aplicacion", response_model=dict)\n'
        '@router.post("/{prestamo_id}/reaplicar-cascada-aplicacion", response_model=dict)\n'
        "def reaplicar_fifo_aplicacion_prestamo("
    )
    if old in t:
        t = t.replace(old, new, 1)
    else:
        print("WARN: prestamos single-route block not found")

    old2 = '@router.post("/reaplicar-fifo-aplicacion-masiva", response_model=dict)\ndef reaplicar_fifo_aplicacion_masiva('
    new2 = (
        '@router.post("/reaplicar-fifo-aplicacion-masiva", response_model=dict)\n'
        '@router.post("/reaplicar-cascada-aplicacion-masiva", response_model=dict)\n'
        "def reaplicar_fifo_aplicacion_masiva("
    )
    if old2 in t:
        t = t.replace(old2, new2, 1)
    else:
        print("WARN: prestamos masiva block not found")

    rep = [
        ('"""Lista de prestamo_id a reaplicar FIFO (reset cuota_pagos + aplicar de nuevo). Maximo 500."""',
         '"""Lista de prestamo_id a reaplicar en cascada (reset cuota_pagos + aplicar de nuevo). Maximo 500."""'),
        ("Reaplicacion integral FIFO para un prestamo:",
         "Reaplicacion integral en cascada para un prestamo:"),
        ('detail="Solo administracion puede reaplicar FIFO sobre cuotas."',
         'detail="Solo administracion puede reaplicar la cascada sobre cuotas."'),
        ('"FIFO reaplicado: cuota_pagos reiniciado y pagos conciliados aplicados de nuevo."',
         '"Cascada reaplicada: cuota_pagos reiniciado y pagos conciliados aplicados de nuevo."'),
        ('detail="Solo administracion puede reaplicar FIFO masivo."',
         'detail="Solo administracion puede reaplicar cascada masivo."'),
        ('f"FIFO masivo: {len(ok)} ok, {len(errores)} error(es)."',
         'f"Cascada masiva: {len(ok)} ok, {len(errores)} error(es)."'),
        ("Igual que /{prestamo_id}/reaplicar-fifo-aplicacion pero para varios prestamos.",
         "Igual que /{prestamo_id}/reaplicar-cascada-aplicacion (o ...-fifo-...) pero para varios prestamos."),
    ]
    for a, b in rep:
        t = t.replace(a, b)

    p.write_text(t, encoding="utf-8", newline="\n")
    print("patched prestamos.py")


def patch_misc() -> None:
    files = [
        ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "cobros.py",
        ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "conciliacion.py",
        ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos_con_errores.py",
        ROOT / "backend" / "app" / "models" / "cuota_pago.py",
        ROOT / "backend" / "app" / "scripts" / "aplicar_pagos_pendientes_job.py",
        ROOT / "backend" / "app" / "services" / "conciliacion_automatica_service.py",
    ]
    for fp in files:
        if not fp.is_file():
            continue
        t = fp.read_text(encoding="utf-8", errors="replace")
        t2 = t.replace("(FIFO)", "(cascada)").replace(" (FIFO)", " (cascada)")
        t2 = t2.replace("FIFO por prestamo", "cascada por prestamo")
        t2 = t2.replace("Aplicar FIFO", "Aplicar cascada")
        t2 = t2.replace("Secuencia FIFO", "Secuencia de aplicacion")
        t2 = t2.replace("pagos pendientes (FIFO)", "pagos pendientes (cascada)")
        if t2 != t:
            fp.write_text(t2, encoding="utf-8", newline="\n")
            print("patched", fp.relative_to(ROOT))


def patch_service() -> None:
    p = ROOT / "backend" / "app" / "services" / "pagos_cuotas_reaplicacion.py"
    t = p.read_text(encoding="utf-8", errors="replace")
    t = t.replace("Reconstruccion en cascada (FIFO / waterfall) por prestamo.", "Reconstruccion en cascada (waterfall) por prestamo.")
    t = t.replace("def reset_y_reaplicar_fifo_prestamo", "def reset_y_reaplicar_cascada_prestamo")
    t = t.replace("reconstruir_cascada_fifo_prestamo = reset_y_reaplicar_fifo_prestamo", "reconstruir_cascada_fifo_prestamo = reset_y_reaplicar_cascada_prestamo")
    if "reset_y_reaplicar_fifo_prestamo" in t and "reset_y_reaplicar_fifo_prestamo =" not in t:
        t = t.rstrip() + "\n\n# Compat: nombre historico\nreset_y_reaplicar_fifo_prestamo = reset_y_reaplicar_cascada_prestamo\n"
    p.write_text(t, encoding="utf-8", newline="\n")
    print("patched pagos_cuotas_reaplicacion.py")


def patch_prestamos_import() -> None:
    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
    t = p.read_text(encoding="utf-8", errors="replace")
    t = t.replace("reset_y_reaplicar_fifo_prestamo", "reset_y_reaplicar_cascada_prestamo")
    # volver a incluir alias en import si se reemplazo todo
    old = "from app.services.pagos_cuotas_reaplicacion import (\n    integridad_cuotas_prestamo,\n    reset_y_reaplicar_cascada_prestamo,\n)\n"
    if old not in t:
        t = t.replace(
            "from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo\n",
            "from app.services.pagos_cuotas_reaplicacion import (\n    integridad_cuotas_prestamo,\n    reset_y_reaplicar_cascada_prestamo,\n)\n",
        )
    # Si el import ya era multilinea solo con reset - leer archivo actual
    p.write_text(t, encoding="utf-8", newline="\n")
    print("patched prestamos import")


def main() -> None:
    patch_service()
    patch_pagos()
    patch_prestamos_import()
    patch_prestamos()
    patch_misc()


if __name__ == "__main__":
    main()
