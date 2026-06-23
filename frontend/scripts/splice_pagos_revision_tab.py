"""Move revision-tab logic from PagosList into usePagosRevisionTab + PagosRevisionTab."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGOS_LIST = ROOT / "src" / "components" / "pagos" / "PagosList.tsx"
OUT_HOOK = ROOT / "src" / "components" / "pagos" / "pagosList" / "usePagosRevisionTab.ts"
OUT_TAB = ROOT / "src" / "components" / "pagos" / "pagosList" / "PagosRevisionTab.tsx"
EXTRACT = ROOT / "scripts" / "_extract_revision.jsx"

HOOK_HEADER = '''import { useState, useEffect, useMemo, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import {
  deleteInfopagosBorradorEscaneer,
  listInfopagosBorradoresEscaneer,
  type InfopagosBorradorListItem,
} from '../../../services/cobrosService'
import {
  pagoConErrorService,
  type PagoConError,
} from '../../../services/pagoConErrorService'
import { invalidatePagosPrestamosRevisionYCuotas } from '../../../constants/queryKeys'
import { getErrorMessage } from '../../../types/errors'
import { eliminarPagoRevisionOConError } from '../../../utils/eliminarPagoRevision'
import { BASE_PATH } from '../../../config/env'
import {
  claveDocumentoPagoListaNormalizada,
  textoDocumentoPagoParaListado,
} from '../../../utils/pagoExcelValidation'

export type RevisionRowAnalizada = {
  pago: PagoConError
  motivos: string[]
  score: number
  esDuplicadoFechaNumero: boolean
}

export type UsePagosRevisionTabOptions = {
  active: boolean
  perPage: number
  includeExportados: boolean
  onIncludeExportadosChange: (value: boolean) => void
  onOpenPagoEditor: (pago: PagoConError) => void
  openStaffComprobanteForList: (
    href: string,
    title: string,
    pagoId?: number
  ) => void
}

export function usePagosRevisionTab({
  active,
  perPage,
  includeExportados,
  onIncludeExportadosChange,
  onOpenPagoEditor,
  openStaffComprobanteForList,
}: UsePagosRevisionTabOptions) {
  const queryClient = useQueryClient()
'''

HOOK_FOOTER = '''
  return {
    revisionCedulaInput,
    setRevisionCedulaInput,
    revisionNumeroDocumentoInput,
    setRevisionNumeroDocumentoInput,
    revisionCedulaFiltro,
    revisionNumeroDocumentoFiltro,
    includeRevisionExportados: includeExportados,
    setIncludeRevisionExportados: onIncludeExportadosChange,
    setRevisionPage,
    isLoadingRevision,
    isRevisionError,
    revisionData,
    showBorradoresEscanerDialog,
    setShowBorradoresEscanerDialog,
    isLoadingBorradoresPendientes,
    isBorradoresPendientesError,
    borradoresPendientes,
    handleBuscarRevisionPorCedula,
    handleLimpiarRevisionCedula,
    handleSiguienteAnomalia,
    bulkRevisionObservacion,
    setBulkRevisionObservacion,
    selectedRevisionIds,
    isBulkSavingRevision,
    isBulkMovingRevision,
    bulkMovingProgress,
    isBulkDeletingRevision,
    isBulkScanningRevision,
    isLimpiandoYaCargados,
    handleGuardarRevisionMasivo,
    handleMoverRevisionMasivo,
    handleEliminarRevisionMasivo,
    handleEscanearRevisionMasivo,
    handleLimpiarYaCargados,
    resumenRevision,
    revisionRowsFiltradas,
    toggleRevisionSeleccionTodas,
    toggleRevisionSeleccion,
    editingRevisionId,
    revisionObservacionDraft,
    setRevisionObservacionDraft,
    savingRevisionId,
    deletingRevisionId,
    handleGuardarRevision,
    handleEliminarRevision,
    handleEditarRevision,
    handleAbrirEditorPagoRevision,
    openStaffComprobanteForList,
    deletingBorradorId,
    handleEliminarBorradorPendiente,
  }
}
'''

TAB_HEADER = '''import { Link } from 'react-router-dom'
import {
  Check,
  Edit,
  Eye,
  FileText,
  Loader2,
  Trash2,
  X,
} from 'lucide-react'
import { Button } from '../../ui/button'
import { Input } from '../../ui/input'
import { ListPaginationBar } from '../../ui/ListPaginationBar'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../ui/card'
import { Badge } from '../../ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../ui/table'
import { formatDate, cn } from '../../../utils'
import { toast } from 'sonner'
import type { PagoConError } from '../../../services/pagoConErrorService'
import {
  observacionesConMarcaDuplicadoCartera,
  pagoEstaCerradoSoloConsulta,
} from './pagosListUtils'
import { usePagosRevisionTab, type UsePagosRevisionTabOptions } from './usePagosRevisionTab'

export type PagosRevisionTabProps = UsePagosRevisionTabOptions

export function PagosRevisionTab(props: PagosRevisionTabProps) {
  const tab = usePagosRevisionTab(props)
  const {
    revisionCedulaInput,
    setRevisionCedulaInput,
    revisionNumeroDocumentoInput,
    setRevisionNumeroDocumentoInput,
    revisionCedulaFiltro,
    revisionNumeroDocumentoFiltro,
    includeRevisionExportados,
    setIncludeRevisionExportados,
    setRevisionPage,
    isLoadingRevision,
    isRevisionError,
    revisionData,
    showBorradoresEscanerDialog,
    setShowBorradoresEscanerDialog,
    isLoadingBorradoresPendientes,
    isBorradoresPendientesError,
    borradoresPendientes,
    handleBuscarRevisionPorCedula,
    handleLimpiarRevisionCedula,
    handleSiguienteAnomalia,
    bulkRevisionObservacion,
    setBulkRevisionObservacion,
    selectedRevisionIds,
    isBulkSavingRevision,
    isBulkMovingRevision,
    bulkMovingProgress,
    isBulkDeletingRevision,
    isBulkScanningRevision,
    isLimpiandoYaCargados,
    handleGuardarRevisionMasivo,
    handleMoverRevisionMasivo,
    handleEliminarRevisionMasivo,
    handleEscanearRevisionMasivo,
    handleLimpiarYaCargados,
    resumenRevision,
    revisionRowsFiltradas,
    toggleRevisionSeleccionTodas,
    toggleRevisionSeleccion,
    editingRevisionId,
    revisionObservacionDraft,
    setRevisionObservacionDraft,
    savingRevisionId,
    deletingRevisionId,
    handleGuardarRevision,
    handleEliminarRevision,
    handleEditarRevision,
    handleAbrirEditorPagoRevision,
    openStaffComprobanteForList,
    deletingBorradorId,
    handleEliminarBorradorPendiente,
  } = tab

  return (
'''

TAB_FOOTER = '''
  )
}
'''


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1 : end])


def transform_hook_body(body: str) -> str:
    body = body.replace("includeRevisionExportados", "includeExportados")
    body = body.replace("setIncludeRevisionExportados(e.target.checked)", "onIncludeExportadosChange(e.target.checked)")
    body = body.replace("activeTab === 'revision'", "active")
    body = body.replace("setPagoEditando(pago)\n    setShowRegistrarPago(true)", "onOpenPagoEditor(pago)")
    body = body.replace("setPagoEditando(siguiente.pago)\n    setShowRegistrarPago(true)", "onOpenPagoEditor(siguiente.pago)")
    return body


def main() -> None:
    lines = PAGOS_LIST.read_text(encoding="utf-8").splitlines()

  # state blocks (1-based line numbers from PagosList)
    state = slice_lines(lines, 212, 257)
    state += "\n" + slice_lines(lines, 190, 191)

    queries = slice_lines(lines, 765, 798)
    memos = slice_lines(lines, 831, 969)
    effect = slice_lines(lines, 939, 948)

    handlers = "\n".join(
        [
            slice_lines(lines, 1163, 1172),
            slice_lines(lines, 1180, 1204),
            slice_lines(lines, 1205, 1444),
            slice_lines(lines, 1370, 1389),
            slice_lines(lines, 1745, 1857),
        ]
    )

    hook_body = transform_hook_body(
        "\n\n".join([state, queries, memos, effect, handlers])
    )

    OUT_HOOK.parent.mkdir(parents=True, exist_ok=True)
    OUT_HOOK.write_text(HOOK_HEADER + hook_body + HOOK_FOOTER, encoding="utf-8")

    jsx = EXTRACT.read_text(encoding="utf-8")
    jsx = jsx.replace("includeRevisionExportados", "includeRevisionExportados")
    jsx = jsx.replace(
        "setIncludeRevisionExportados(e.target.checked)",
        "setIncludeRevisionExportados(e.target.checked)",
    )
    OUT_TAB.write_text(TAB_HEADER + jsx + TAB_FOOTER, encoding="utf-8")
    print(f"Wrote {OUT_HOOK} and {OUT_TAB}")


if __name__ == "__main__":
    main()
