"""Patch PagosList after PagosRevisionTab extraction."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGOS_LIST = ROOT / "src" / "components" / "pagos" / "PagosList.tsx"

REMOVE_RANGES = [
    (190, 191),  # showBorradoresEscanerDialog
    (212, 257),  # revision tab state
    (765, 798),  # revision queries
    (831, 969),  # revision memos + borradores + effect + resumen revision
    (1163, 1172),  # refetchDiagnosticoRevision
    (1180, 1204),  # handleEditarRevision .. handleSiguienteAnomalia
    (1205, 1342),  # toggle .. handleMoverRevisionMasivo
    (1390, 1444),  # handleEscanearRevisionMasivo .. handleLimpiarYaCargados
    (1745, 1857),  # handleBuscarRevision .. handleEliminarBorradorPendiente
]

REVISION_TAB_START = 2482
REVISION_TAB_END = 3066

IMPORT_LINE = "import { PagosRevisionTab } from './pagosList/PagosRevisionTab'\n"

REPLACEMENT_TAB = """          <TabsContent value="revision" forceMount>
            <PagosRevisionTab
              active={activeTab === 'revision'}
              perPage={perPage}
              includeExportados={includeRevisionExportados}
              onIncludeExportadosChange={setIncludeRevisionExportados}
              onOpenPagoEditor={pago => {
                setPagoEditando(pago)
                setShowRegistrarPago(true)
              }}
              openStaffComprobanteForList={openStaffComprobanteForList}
            />
          </TabsContent>
"""


def main() -> None:
    lines = PAGOS_LIST.read_text(encoding="utf-8").splitlines()
    remove = set()
    for start, end in REMOVE_RANGES:
        for i in range(start, end + 1):
            remove.add(i)

    new_lines: list[str] = []
    for i, line in enumerate(lines, start=1):
        if i < REVISION_TAB_START or i > REVISION_TAB_END:
            if i not in remove:
                new_lines.append(line)
        elif i == REVISION_TAB_START:
            new_lines.extend(REPLACEMENT_TAB.splitlines())

    text = "\n".join(new_lines) + "\n"
    if IMPORT_LINE.strip() not in text:
        anchor = "import { useStaffComprobantePreview }"
        text = text.replace(anchor, IMPORT_LINE + anchor, 1)

    # URL pestana: only set active tab; ndoc seed handled in usePagosRevisionTab
    old_pestana = """    if (pestana === 'revision' || pestana === 'revision-global') {
      setActiveTab('revision')
      const ndoc = (searchParams.get('numero_documento') || '').trim()
      if (ndoc) {
        setRevisionNumeroDocumentoInput(ndoc)
        setRevisionNumeroDocumentoFiltro(ndoc)
      }
      setRevisionPage(1)
      const next = new URLSearchParams(searchParams)
      next.delete('pestana')
      next.delete('numero_documento')
      if (next.toString()) {
        setSearchParams(next, { replace: true })
      } else {
        setSearchParams({}, { replace: true })
      }
    }"""
    new_pestana = """    if (pestana === 'revision' || pestana === 'revision-global') {
      setActiveTab('revision')
    }"""
    text = text.replace(old_pestana, new_pestana)

    PAGOS_LIST.write_text(text, encoding="utf-8")
    print(f"Patched {PAGOS_LIST}: {len(lines)} -> {len(new_lines)} lines")


if __name__ == "__main__":
    main()
