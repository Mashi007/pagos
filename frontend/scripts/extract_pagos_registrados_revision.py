"""Extract Pagos registrados section from EditarRevisionManual."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src" / "pages" / "EditarRevisionManual.tsx"
OUT = ROOT / "src" / "pages" / "revisionManual" / "PagosRegistradosRevisionSection.tsx"
EXTRACT = ROOT / "scripts" / "_extract_pagos_registrados.jsx"

START, END = 2584, 3562

HEADER = '''import {
  AlertTriangle,
  BarChart3,
  Check,
  CheckSquare,
  CreditCard,
  DollarSign,
  Edit,
  Eye,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { formatDate } from '../../utils'
import type { Pago } from '../../services/pagoService'
import type { UseMutationResult } from '@tanstack/react-query'
import { ConciliarCarteraRevisionManualButton } from '../../components/pagos/ConciliarCarteraRevisionManualButton'
import {
  ConciliarCarteraPagosProgreso,
  type ConciliarCarteraFaseTabla,
} from '../../components/pagos/ConciliarCarteraPagosProgreso'
import {
  claveDocumentoPagoListaNormalizada,
  textoDocumentoPagoParaListado,
} from '../../utils/pagoExcelValidation'
import {
  abrirStaffComprobanteDesdeHref,
  esUrlComprobanteImagenConAuth,
} from '../../utils/comprobanteImagenAuth'
import { COHERENCIA_USD_TOL } from './EditarRevisionManual.helpers'
import type { PagosRegistradosRevisionSectionProps } from './pagosRegistradosRevisionTypes'

export function PagosRegistradosRevisionSection(
  props: PagosRegistradosRevisionSectionProps
) {
'''

FOOTER = '''
}
'''

TYPES = '''import type { RefObject } from 'react'
import type { UseMutationResult } from '@tanstack/react-query'
import type { Pago } from '../../services/pagoService'
import type { ConciliarCarteraFaseTabla } from '../../components/pagos/ConciliarCarteraPagosProgreso'
import type { ConciliarCarteraRevisionResponse } from '../../services/revisionManualService'
import type { PrestamoData } from './EditarRevisionManual.helpers'

export type ConciliarTablaUiState = {
  fase: ConciliarCarteraFaseTabla
  pagosAntes: number
  idsAnteriores?: number[]
  idsRecreados?: number[]
  ocrOk?: number
  ocrTotal?: number
}

export type PagosRealizadosQueryData = {
  pagos?: Pago[]
  total?: number
  page?: number
  total_pages?: number
  sum_monto_pagado_cedula?: number | null
  resumen_prestamo?: {
    suma_monto_pagado: number
    cantidad: number
    cantidad_no_operativos?: number
    suma_monto_total_bd?: number
    cantidad_pendiente?: number
    suma_monto_pendiente?: number
    cantidad_pagado?: number
    suma_monto_estado_pagado?: number
  }
}

export type PagosRegistradosRevisionSectionProps = {
  pagosRegistradosCardRef: RefObject<HTMLDivElement | null>
  vieneDesdeFiniquitos: boolean
  prestamoData: Partial<PrestamoData>
  soloLectura: boolean
  aplicarCascadaPagosMutation: UseMutationResult<unknown, Error, void, unknown>
  abrirAgregarPagoRevision: () => void
  escaneandoComprobanteAgregarPago: boolean
  abrirSelectorEscaneoComprobanteAgregarPago: () => void
  reescaneandoCartera: boolean
  reescaneoCarteraProgreso: { hecho: number; total: number; fase: 'ocr' | 'cascada' } | null
  ejecutarReescaneoCartera: () => void | Promise<void>
  loadingPagosRealizados: boolean
  fetchingPagosRealizados: boolean
  refetchPagosRealizados: () => void | Promise<unknown>
  isAdmin: boolean
  conciliarTablaUi: ConciliarTablaUiState | null
  setConciliarTablaUi: React.Dispatch<React.SetStateAction<ConciliarTablaUiState | null>>
  idsPagosPrestamoEnTabla: () => number[]
  contarPagosPrestamoEnTabla: () => number
  limpiarConciliarTablaUi: () => void
  manejarConciliarExito: (result: ConciliarCarteraRevisionResponse) => void
  pagosRealizadosData: PagosRealizadosQueryData | undefined
  pagosRegistradosOrdenados: Pago[]
  conteoDocumentoPagosRevision: Map<string, number>
  alertasReescaneoPorPagoId: Record<number, string[]>
  abrirEditarPagoRevision: (pago: Pago) => void
  pagoEstaConciliadoOPagado: (pago: Pago) => boolean
  eliminandoPagoId: number | null
  eliminarPagoRevision: (pago: Pago) => void | Promise<void>
  pagePagosRegistrados: number
  setPagePagosRegistrados: React.Dispatch<React.SetStateAction<number>>
  hayPendienteRevision: boolean
  auditoriaCoherenciaActiva: boolean
  estadoPrestamoNorm: string
  agregadosCuotasRevision: { sumMonto: number; sumPagado: number }
}
'''


def main() -> None:
    lines = PAGE.read_text(encoding="utf-8").splitlines()
    body = "\n".join(lines[START - 1 : END])
    # strip outer conditional wrapper
    body = body.replace(
        "            {cedulaParaPagosRealizados ? (\n              <>\n", "  return (\n    <>\n", 1
    )
    body = body.replace("              </>\n            ) : null}", "    </>\n  )", 1)
    # destructure props at top of function
    destructure = "  const {\n    pagosRegistradosCardRef,\n    vieneDesdeFiniquitos,\n    prestamoData,\n    soloLectura,\n    aplicarCascadaPagosMutation,\n    abrirAgregarPagoRevision,\n    escaneandoComprobanteAgregarPago,\n    abrirSelectorEscaneoComprobanteAgregarPago,\n    reescaneandoCartera,\n    reescaneoCarteraProgreso,\n    ejecutarReescaneoCartera,\n    loadingPagosRealizados,\n    fetchingPagosRealizados,\n    refetchPagosRealizados,\n    isAdmin,\n    conciliarTablaUi,\n    setConciliarTablaUi,\n    idsPagosPrestamoEnTabla,\n    contarPagosPrestamoEnTabla,\n    limpiarConciliarTablaUi,\n    manejarConciliarExito,\n    pagosRealizadosData,\n    pagosRegistradosOrdenados,\n    conteoDocumentoPagosRevision,\n    alertasReescaneoPorPagoId,\n    abrirEditarPagoRevision,\n    pagoEstaConciliadoOPagado,\n    eliminandoPagoId,\n    eliminarPagoRevision,\n    pagePagosRegistrados,\n    setPagePagosRegistrados,\n    hayPendienteRevision,\n    auditoriaCoherenciaActiva,\n    estadoPrestamoNorm,\n    agregadosCuotasRevision,\n  } = props\n\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER + destructure + body + FOOTER, encoding="utf-8")
    types_path = OUT.parent / "pagosRegistradosRevisionTypes.ts"
    types_path.write_text(
        "import type React from 'react'\n" + TYPES.split("import type { RefObject }", 1)[1],
        encoding="utf-8",
    )
    # patch page
    new_lines = lines[: START - 1] + [
        "            <PagosRegistradosRevisionSection",
        "              pagosRegistradosCardRef={pagosRegistradosCardRef}",
        "              vieneDesdeFiniquitos={vieneDesdeFiniquitos}",
        "              prestamoData={prestamoData}",
        "              soloLectura={soloLectura}",
        "              aplicarCascadaPagosMutation={aplicarCascadaPagosMutation}",
        "              abrirAgregarPagoRevision={abrirAgregarPagoRevision}",
        "              escaneandoComprobanteAgregarPago={escaneandoComprobanteAgregarPago}",
        "              abrirSelectorEscaneoComprobanteAgregarPago={abrirSelectorEscaneoComprobanteAgregarPago}",
        "              reescaneandoCartera={reescaneandoCartera}",
        "              reescaneoCarteraProgreso={reescaneoCarteraProgreso}",
        "              ejecutarReescaneoCartera={ejecutarReescaneoCartera}",
        "              loadingPagosRealizados={loadingPagosRealizados}",
        "              fetchingPagosRealizados={fetchingPagosRealizados}",
        "              refetchPagosRealizados={refetchPagosRealizados}",
        "              isAdmin={isAdmin}",
        "              conciliarTablaUi={conciliarTablaUi}",
        "              setConciliarTablaUi={setConciliarTablaUi}",
        "              idsPagosPrestamoEnTabla={idsPagosPrestamoEnTabla}",
        "              contarPagosPrestamoEnTabla={contarPagosPrestamoEnTabla}",
        "              limpiarConciliarTablaUi={limpiarConciliarTablaUi}",
        "              manejarConciliarExito={manejarConciliarExito}",
        "              pagosRealizadosData={pagosRealizadosData}",
        "              pagosRegistradosOrdenados={pagosRegistradosOrdenados}",
        "              conteoDocumentoPagosRevision={conteoDocumentoPagosRevision}",
        "              alertasReescaneoPorPagoId={alertasReescaneoPorPagoId}",
        "              abrirEditarPagoRevision={abrirEditarPagoRevision}",
        "              pagoEstaConciliadoOPagado={pagoEstaConciliadoOPagado}",
        "              eliminandoPagoId={eliminandoPagoId}",
        "              eliminarPagoRevision={eliminarPagoRevision}",
        "              pagePagosRegistrados={pagePagosRegistrados}",
        "              setPagePagosRegistrados={setPagePagosRegistrados}",
        "              hayPendienteRevision={hayPendienteRevision}",
        "              auditoriaCoherenciaActiva={auditoriaCoherenciaActiva}",
        "              estadoPrestamoNorm={estadoPrestamoNorm}",
        "              agregadosCuotasRevision={agregadosCuotasRevision}",
        "            />",
    ] + lines[END:]
    text = "\n".join(new_lines) + "\n"
    imp = "import { PagosRegistradosRevisionSection } from './revisionManual/PagosRegistradosRevisionSection'\n"
    if imp.strip() not in text:
        text = text.replace(
            "import { PrestamoRevisionCard } from './revisionManual/PrestamoRevisionCard'\n",
            "import { PrestamoRevisionCard } from './revisionManual/PrestamoRevisionCard'\n" + imp,
        )
    # wrap with cedula conditional
    text = text.replace(
        "            <PagosRegistradosRevisionSection",
        "            {cedulaParaPagosRealizados ? (\n            <PagosRegistradosRevisionSection",
        1,
    )
    text = text.replace(
        "              agregadosCuotasRevision={agregadosCuotasRevision}\n            />",
        "              agregadosCuotasRevision={agregadosCuotasRevision}\n            />\n            ) : null}",
        1,
    )
    PAGE.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT} and patched {PAGE}")


if __name__ == "__main__":
    main()
