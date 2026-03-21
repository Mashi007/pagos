from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "src"


def patch(rel: str, old: str, new: str, count: int = 1) -> bool:
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    if old not in t:
        return False
    p.write_text(t.replace(old, new, count), encoding="utf-8")
    return True


def patch_all(rel: str, old: str, new: str) -> int:
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    n = t.count(old)
    if n:
        p.write_text(t.replace(old, new), encoding="utf-8")
    return n


def main() -> None:
    # LoginForm
    patch(
        "components/auth/LoginForm.tsx",
        "const first = result.error.flatten().fieldErrors?.email?.[0] ? result.error.message",
        "const first = result.error.flatten().fieldErrors?.email?.[0] ?? result.error.message",
    )

    # ErroresDetallados — branch row data by tipo
    p = ROOT / "components/carga-masiva/ErroresDetallados.tsx"
    t = p.read_text(encoding="utf-8")
    old_block = """      return [

        error.cedula,

        String(error.data.nombre ? error.data.fecha ?? ''),

        String(error.data.telefono ? error.data.monto_pagado ?? ''),

        String(error.data.email ? error.data.documento_pago ?? ''),

        error.error,

        correccionSugerida

      ]"""
    new_block = """      return [

        error.cedula,

        ...(tipo === 'clientes'

          ? [

              String(error.data.nombre ?? ''),

              String(error.data.telefono ?? ''),

              String(error.data.email ?? ''),

            ]

          : [

              String(error.data.fecha ?? ''),

              String(error.data.monto_pagado ?? ''),

              String(error.data.documento_pago ?? ''),

            ]),

        error.error,

        correccionSugerida

      ]"""
    if old_block in t:
        p.write_text(t.replace(old_block, new_block, 1), encoding="utf-8")
        print("ErroresDetallados: tipo branch")
    else:
        print("FAIL ErroresDetallados block")

    # CasosRevisarDialog
    tel_key = "(Cliente as any)['telefono'] ? (Cliente as any)['Tel\u00e9fono']"
    tel_fix = "(Cliente as any)['telefono'] ?? (Cliente as any)['Tel\u00e9fono']"
    n = patch_all("components/clientes/CasosRevisarDialog.tsx", tel_key, tel_fix)
    print("CasosRevisar tel keys", n)
    patch(
        "components/clientes/CasosRevisarDialog.tsx",
        "telefono: c.telefono ? c.Tel\u00e9fono",
        "telefono: c.telefono ?? c.Tel\u00e9fono",
    )
    for old, new in [
        ("cedula: payload.cedula ? c.cedula,", "cedula: payload.cedula ?? c.cedula,"),
        ("nombres: payload.nombres ? c.nombres,", "nombres: payload.nombres ?? c.nombres,"),
        ("payload.telefono ? c.telefono,", "payload.telefono ?? c.telefono,"),
        ("email: payload.email ? c.email,", "email: payload.email ?? c.email,"),
    ]:
        c = patch_all("components/clientes/CasosRevisarDialog.tsx", old, new)
        if c:
            print("CasosRevisar", old[:30], c)

    # ClienteDetalle
    patch(
        "components/clientes/ClienteDetalle.tsx",
        '<p className="text-sm text-slate-900">{value ? \'-\'}</p>',
        '<p className="text-sm text-slate-900">{value ?? \'-\'}</p>',
    )

    # ClientesList export table
    for old, new in [
        (
            '<TableCell className="font-mono text-xs">{item.fila_origen ? \'-\'}</TableCell>',
            '<TableCell className="font-mono text-xs">{item.fila_origen ?? \'-\'}</TableCell>',
        ),
        ("<TableCell>{item.cedula ? '-'}</TableCell>", "<TableCell>{item.cedula ?? '-'}</TableCell>"),
        ("<TableCell>{item.nombres ? '-'}</TableCell>", "<TableCell>{item.nombres ?? '-'}</TableCell>"),
        ("<TableCell>{item.email ? '-'}</TableCell>", "<TableCell>{item.email ?? '-'}</TableCell>"),
        ("<TableCell>{item.telefono ? '-'}</TableCell>", "<TableCell>{item.telefono ?? '-'}</TableCell>"),
        (
            "title={item.errores ?? ''}>{item.errores ? '-'}</TableCell>",
            "title={item.errores ?? ''}>{item.errores ?? '-'}</TableCell>",
        ),
    ]:
        patch("components/clientes/ClientesList.tsx", old, new)

    # Comunicaciones
    patch(
        "components/comunicaciones/Comunicaciones.tsx",
        "        const operado = comm.operado ? false",
        "        const operado = comm.operado ?? false",
    )
    patch(
        "components/comunicaciones/Comunicaciones.tsx",
        "        asignado_a_id: ticketForm.responsable_id ? undefined,",
        "        asignado_a_id: ticketForm.responsable_id ?? undefined,",
    )

    # EmailConfig
    for old, new in [
        (
            "            imap_use_ssl: config.imap_use_ssl ? 'true',",
            "            imap_use_ssl: config.imap_use_ssl ?? 'true',",
        ),
        (
            "                    checked={(config[key] ? 'true') === 'true'}",
            "                    checked={(config[key] ?? 'true') === 'true'}",
        ),
        (
            "                    <span className=\"text-xs text-gray-500\">{(config[key] ? 'false') === 'true' ? 'Pruebas' : 'Producci\u00f3n'}</span>",
            "                    <span className=\"text-xs text-gray-500\">{(config[key] ?? 'false') === 'true' ? 'Pruebas' : 'Producci\u00f3n'}</span>",
        ),
        (
            "                      checked={(config[key] ? 'false') === 'true'}",
            "                      checked={(config[key] ?? 'false') === 'true'}",
        ),
        (
            "                checked={(config.imap_use_ssl ? 'true') === 'true'}",
            "                checked={(config.imap_use_ssl ?? 'true') === 'true'}",
        ),
        (
            "                      imap_use_ssl: config.imap_use_ssl ? undefined,",
            "                      imap_use_ssl: config.imap_use_ssl ?? undefined,",
        ),
    ]:
        patch("components/configuracion/EmailConfig.tsx", old, new)

    # EmailCuentasConfig — error messages
    for old, new in [
        (
            "      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ? (e as Error)?.message?? 'Error al guardar'",
            "      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (e as Error)?.message ?? 'Error al guardar'",
        ),
        (
            "      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ? (e as Error)?.message?? 'Error al enviar prueba'",
            "      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (e as Error)?.message ?? 'Error al enviar prueba'",
        ),
    ]:
        patch("components/configuracion/EmailCuentasConfig.tsx", old, new)

    for old, new in [
        (
            "                    checked={(data?.[key] ? 'true') === 'true'}",
            "                    checked={(data?.[key] ?? 'true') === 'true'}",
        ),
        (
            "                  <span className=\"ml-2 text-sm\">{(data?.[key] ? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>",
            "                  <span className=\"ml-2 text-sm\">{(data?.[key] ?? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>",
        ),
        (
            "              <span className=\"ml-2 text-sm\">{(data?.modo_pruebas ? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>",
            "              <span className=\"ml-2 text-sm\">{(data?.modo_pruebas ?? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>",
        ),
    ]:
        patch("components/configuracion/EmailCuentasConfig.tsx", old, new)

    # Card title: fallback label (fix ? without :)
    ec = ROOT / "components/configuracion/EmailCuentasConfig.tsx"
    et = ec.read_text(encoding="utf-8")
    # Match either corrupted em dash or ASCII
    import re

    et2 = re.sub(
        r"(\{SERVICIO_POR_CUENTA\[i \+ 1\]) \? (`Cuenta \$\{i \+ 1\}`)\}",
        r"\1 ?? \2}",
        et,
        count=1,
    )
    if et2 != et:
        ec.write_text(et2, encoding="utf-8")
        print("EmailCuentasConfig SERVICIO_POR_CUENTA")
    else:
        # try alternate spacing
        et2 = et.replace("SERVICIO_POR_CUENTA[i + 1] ? `Cuenta", "SERVICIO_POR_CUENTA[i + 1] ?? `Cuenta", 1)
        if et2 != et:
            ec.write_text(et2, encoding="utf-8")
            print("EmailCuentasConfig SERVICIO simple")

    patch(
        "components/configuracion/EmailCuentasConfig.tsx",
        "                  value={asignacion[id] ? 3}",
        "                  value={asignacion[id] ?? 3}",
    )

    print("done")


if __name__ == "__main__":
    main()
