# -*- coding: utf-8 -*-
"""One-shot patch: Masivos in plantillas UI, PDF anexos, backend adjuntos."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    p_plant = ROOT / "frontend/src/components/notificaciones/PlantillasNotificaciones.tsx"
    s = p_plant.read_text(encoding="utf-8")

    old1 = """    prejudicial: [{ valor: 'PREJUDICIAL', label: 'Prejudicial' }],

    cobranza: [{ valor: 'COBRANZA', label: 'Carta de cobranza' }],
  }"""
    new1 = """    prejudicial: [{ valor: 'PREJUDICIAL', label: 'Prejudicial' }],

    masivos: [
      { valor: 'MASIVOS', label: 'Comunicaciones masivas (Masivos)' },
    ],

    cobranza: [{ valor: 'COBRANZA', label: 'Carta de cobranza' }],
  }"""
    if old1 not in s:
        raise SystemExit("PlantillasNotificaciones: block1 not found")
    s = s.replace(old1, new1, 1)

    old2 = """  const todosLosTipos = [
    ...tiposPorCategoria.retraso,

    ...tiposPorCategoria.prejudicial,

    ...(tiposPorCategoria.cobranza || []),
  ]"""
    new2 = """  const todosLosTipos = [
    ...tiposPorCategoria.retraso,

    ...tiposPorCategoria.prejudicial,

    ...tiposPorCategoria.masivos,

    ...(tiposPorCategoria.cobranza || []),
  ]"""
    if old2 not in s:
        raise SystemExit("PlantillasNotificaciones: todosLosTipos not found")
    s = s.replace(old2, new2, 1)

    old3 = """    PREJUDICIAL: { categoria: 'Prejudicial', caso: 'Prejudicial' },

    COBRANZA: { categoria: 'Cobranza', caso: 'Carta de cobranza' },
  }"""
    new3 = """    PREJUDICIAL: { categoria: 'Prejudicial', caso: 'Prejudicial' },

    MASIVOS: {
      categoria: 'Comunicaciones masivas',
      caso: 'Masivos',
    },

    COBRANZA: { categoria: 'Cobranza', caso: 'Carta de cobranza' },
  }"""
    if old3 not in s:
        raise SystemExit("PlantillasNotificaciones: mapeoTipos not found")
    s = s.replace(old3, new3, 1)

    old4 = """    {
      tipo: 'PREJUDICIAL',
      label: 'Prejudicial',
      borderColor: 'border-red-500',
    },

    {
      tipo: 'COBRANZA',
      label: 'Carta de cobranza',
      borderColor: 'border-violet-500',
    },
  ]"""
    new4 = """    {
      tipo: 'PREJUDICIAL',
      label: 'Prejudicial',
      borderColor: 'border-red-500',
    },

    {
      tipo: 'MASIVOS',
      label: 'Masivos',
      borderColor: 'border-teal-500',
    },

    {
      tipo: 'COBRANZA',
      label: 'Carta de cobranza',
      borderColor: 'border-violet-500',
    },
  ]"""
    if old4 not in s:
        raise SystemExit("PlantillasNotificaciones: ordenCasos not found")
    s = s.replace(old4, new4, 1)

    old5 = """    {
      key: 'Prejudicial',
      color: 'red',
      borderColor: 'border-red-500',
      icon: 'dYs"',
    },

    {
      key: 'Cobranza',
      color: 'violet',
      borderColor: 'border-violet-500',
      icon: 'dY"',
    },
"""
    # File may have corrupted icons; match without icon lines
    import re
    pat = r"(\{\s*key: 'Prejudicial',[\s\S]*?borderColor: 'border-red-500',[\s\S]*?\},\s*)(\{\s*key: 'Cobranza',)"
    m = re.search(pat, s)
    if not m:
        raise SystemExit("PlantillasNotificaciones: categoriasOrden Prejudicial block not found")
    insert = """    {
      key: 'Comunicaciones masivas',
      color: 'teal',
      borderColor: 'border-teal-500',
      icon: 'mail',
    },

"""
    s = s[: m.end(1)] + insert + s[m.start(2) :]

    old_ui = """              {/* Prejudicial */}

              <div>
                <h4 className="mb-2 text-sm font-semibold text-red-700">
                  Prejudicial
                </h4>

                <div className="grid grid-cols-3 gap-2">
                  {tiposPorCategoria.prejudicial.map(t => (
                    <label
                      key={t.valor}
                      className="flex cursor-pointer items-center gap-2 rounded border p-2 hover:bg-white"
                    >
                      <input
                        type="checkbox"
                        checked={tiposSeleccionados.includes(t.valor)}
                        onChange={() => toggleTipo(t.valor)}
                        className="rounded"
                      />

                      <span className="text-sm">{t.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
"""
    new_ui = """              {/* Prejudicial */}

              <div>
                <h4 className="mb-2 text-sm font-semibold text-red-700">
                  Prejudicial
                </h4>

                <div className="grid grid-cols-3 gap-2">
                  {tiposPorCategoria.prejudicial.map(t => (
                    <label
                      key={t.valor}
                      className="flex cursor-pointer items-center gap-2 rounded border p-2 hover:bg-white"
                    >
                      <input
                        type="checkbox"
                        checked={tiposSeleccionados.includes(t.valor)}
                        onChange={() => toggleTipo(t.valor)}
                        className="rounded"
                      />

                      <span className="text-sm">{t.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Masivos: correos masivos (pesta\u00f1a Masivos); sin cuota/pr\u00e9stamo */}

              <div>
                <h4 className="mb-2 text-sm font-semibold text-teal-700">
                  Masivos
                </h4>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {tiposPorCategoria.masivos.map(t => (
                    <label
                      key={t.valor}
                      className="flex cursor-pointer items-center gap-2 rounded border border-teal-200 p-2 hover:bg-white"
                    >
                      <input
                        type="checkbox"
                        checked={tiposSeleccionados.includes(t.valor)}
                        onChange={() => toggleTipo(t.valor)}
                        className="rounded"
                      />

                      <span className="text-sm">{t.label}</span>
                    </label>
                  ))}
                </div>

                <p className="mt-1 text-xs text-gray-500">
                  Asigna la plantilla al caso MASIVOS en Notificaciones &gt;
                  Configuraci\u00f3n. Los PDF fijos para este caso se suben en la
                  pesta\u00f1a Documentos PDF anexos (carpeta Masivos).
                </p>
              </div>
            </div>
"""
    if old_ui not in s:
        raise SystemExit("PlantillasNotificaciones: UI prejudicial block not found")
    s = s.replace(old_ui, new_ui, 1)

    p_plant.write_text(s, encoding="utf-8")
    print("Patched", p_plant)

    # DocumentosPdfAnexos
    p_docs = ROOT / "frontend/src/components/notificaciones/DocumentosPdfAnexos.tsx"
    sd = p_docs.read_text(encoding="utf-8")
    old_t = """const TIPOS_CASO: { value: string; label: string }[] = [
  { value: 'dias_1_retraso', label: 'DA-a siguiente al venc.' },

  { value: 'dias_3_retraso', label: '3 dA-as retraso' },

  { value: 'dias_5_retraso', label: '5 dA-as retraso' },

  { value: 'prejudicial', label: 'Prejudicial' },
]"""
    new_t = """const TIPOS_CASO: { value: string; label: string }[] = [
  { value: 'dias_1_retraso', label: 'DA-a siguiente al venc.' },

  { value: 'dias_3_retraso', label: '3 dA-as retraso' },

  { value: 'dias_5_retraso', label: '5 dA-as retraso' },

  { value: 'prejudicial', label: 'Prejudicial' },

  { value: 'masivos', label: 'Masivos' },
]"""
    if old_t not in sd:
        # try without corrupted chars in labels
        old_t2 = "const TIPOS_CASO: { value: string; label: string }[] = ["
        if old_t2 not in sd:
            raise SystemExit("DocumentosPdfAnexos: TIPOS_CASO not found")
        import re as _re

        sd = _re.sub(
            r"(const TIPOS_CASO: \{ value: string; label: string \}\[] = \[[\s\S]*?\{ value: 'prejudicial', label: [^}]+\},\s*)\]",
            r"\1  { value: 'masivos', label: 'Masivos' },\n]",
            sd,
            count=1,
        )
    else:
        sd = sd.replace(old_t, new_t, 1)
    p_docs.write_text(sd, encoding="utf-8")
    print("Patched", p_docs)

    # DocumentosAlmacenadosPorPestana
    p_alm = ROOT / "frontend/src/components/notificaciones/DocumentosAlmacenadosPorPestana.tsx"
    sa = p_alm.read_text(encoding="utf-8")
    if "{ value: 'masivos'" not in sa:
        sa = sa.replace(
            "  { value: 'prejudicial', label: 'Prejudicial' },\n]",
            "  { value: 'prejudicial', label: 'Prejudicial' },\n\n  { value: 'masivos', label: 'Masivos' },\n]",
            1,
        )
        p_alm.write_text(sa, encoding="utf-8")
    print("Patched", p_alm)

    # adjunto_fijo_cobranza.py
    p_adj = ROOT / "backend/app/services/adjunto_fijo_cobranza.py"
    adj = p_adj.read_text(encoding="utf-8")
    old_v = '''TIPOS_CASO_VALIDOS = frozenset([
    "dias_1_retraso", "dias_3_retraso", "dias_5_retraso",
    "prejudicial",
])'''
    new_v = '''TIPOS_CASO_VALIDOS = frozenset([
    "dias_1_retraso", "dias_3_retraso", "dias_5_retraso",
    "prejudicial",
    "masivos",
])'''
    if old_v not in adj:
        raise SystemExit("adjunto_fijo_cobranza: TIPOS_CASO_VALIDOS not found")
    adj = adj.replace(old_v, new_v, 1)
    p_adj.write_text(adj, encoding="utf-8")
    print("Patched", p_adj)

    # notificaciones.py upload messages
    p_not = ROOT / "backend/app/api/v1/endpoints/notificaciones.py"
    n = p_not.read_text(encoding="utf-8")
    n = n.replace(
        'description="Caso: dias_1_retraso, dias_3_retraso, dias_5_retraso, prejudicial"',
        'description="Caso: dias_1_retraso, dias_3_retraso, dias_5_retraso, prejudicial, masivos"',
        1,
    )
    n = n.replace(
        'detail="tipo_caso debe ser uno de: dias_1_retraso, dias_3_retraso, dias_5_retraso, prejudicial"',
        'detail="tipo_caso debe ser uno de: dias_1_retraso, dias_3_retraso, dias_5_retraso, prejudicial, masivos"',
        1,
    )
    p_not.write_text(n, encoding="utf-8")
    print("Patched", p_not)

    # notificaciones_tabs.py strict mode: allow fixed PDFs for MASIVOS from config
    p_tabs = ROOT / "backend/app/api/v1/endpoints/notificaciones_tabs.py"
    t = p_tabs.read_text(encoding="utf-8")
    old_strict = """        if paquete_estricto:
            incluir_pdf_anexo = tipo != "MASIVOS"
            incluir_adjuntos_fijos = tipo != "MASIVOS"
        else:"""
    new_strict = """        if paquete_estricto:
            incluir_pdf_anexo = tipo != "MASIVOS"
            # Masivos: sin Carta_Cobranza.pdf; adjuntos de pestaña 3 según config
            if tipo == "MASIVOS":
                incluir_adjuntos_fijos = tipo_cfg.get("incluir_adjuntos_fijos", True) is not False
            else:
                incluir_adjuntos_fijos = True
        else:"""
    if old_strict not in t:
        raise SystemExit("notificaciones_tabs: strict block not found")
    t = t.replace(old_strict, new_strict, 1)
    p_tabs.write_text(t, encoding="utf-8")
    print("Patched", p_tabs)

    print("Done.")

if __name__ == "__main__":
    main()
