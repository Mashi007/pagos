"""Extract Pagos registrados block from EditarRevisionManual."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "pages"
MAIN = ROOT / "EditarRevisionManual.tsx"
OUT = ROOT / "revisionManual" / "PagosRegistradosRevisionSection.tsx"

lines = MAIN.read_text(encoding="utf-8").splitlines(keepends=True)
# cedulaParaPagosRealizados block: 2584-3562 (1-based)
body = "".join(lines[2583:3562])

component = '''import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import {
  BarChart3,
  CreditCard,
  Edit,
  Eye,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Input } from '../../components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { ListPaginationBar } from '../../components/ui/ListPaginationBar'
import { RegistrarPagoForm } from '../../components/pagos/RegistrarPagoForm'
import { ConciliarCarteraPagosProgreso } from '../../components/pagos/ConciliarCarteraPagosProgreso'
import { ConciliarCarteraRevisionManualButton } from '../../components/pagos/ConciliarCarteraRevisionManualButton'
import { formatDate } from '../../utils'
import { textoDocumentoPagoParaListado } from '../../utils/pagoExcelValidation'
import type { Pago } from '../../services/pagoService'
import type { ConciliarCarteraFaseTabla } from '../../components/pagos/ConciliarCarteraPagosProgreso'
import type { PrestamoData } from './EditarRevisionManual.helpers'

/** Bloque «Pagos registrados en cartera» + panel de coherencia (revisión manual). */
export type PagosRegistradosRevisionSectionProps = {
  cedulaParaPagosRealizados: string | null | undefined
  pagosRegistradosCardRef: MutableRefObject<HTMLDivElement | null>
  vieneDesdeFiniquitos: boolean
  soloLectura: boolean
  prestamoData: Partial<PrestamoData>
  aplicarCascadaPagosMutation: { isPending: boolean; mutate: () => void }
  reescaneandoCartera: boolean
  onReescanearCartera: () => void
  conciliarCarteraFaseTabla: ConciliarCarteraFaseTabla | null
  pagosRealizadosOrdenados: Pago[]
  pagosRealizadosData: {
    pagos: Pago[]
    total: number
    total_pages: number
  } | undefined
  pagePagosRegistrados: number
  setPagePagosRegistrados: Dispatch<SetStateAction<number>>
  perPagePagosRegistrados: number
  loadingPagosRealizados: boolean
  pagoEditando: Pago | null
  setPagoEditando: Dispatch<SetStateAction<Pago | null>>
  showRegistrarPago: boolean
  setShowRegistrarPago: Dispatch<SetStateAction<boolean>>
  escaneandoComprobanteAgregarPago: boolean
  onEscanearComprobanteAgregar: (file: File) => void
  onAbrirComprobante: (href: string, label: string, pagoId: number | null) => void
  onEditarPago: (pago: Pago) => void
  onEliminarPago: (pagoId: number) => void | Promise<void>
  eliminandoPagoId: number | null
  clavesDocumentoPagina: Set<string>
  coherenciaPanel: React.ReactNode
}

export function PagosRegistradosRevisionSection(props: PagosRegistradosRevisionSectionProps) {
  const {
    cedulaParaPagosRealizados,
    pagosRegistradosCardRef,
    vieneDesdeFiniquitos,
    soloLectura,
    prestamoData,
    aplicarCascadaPagosMutation,
    reescaneandoCartera,
    onReescanearCartera,
    conciliarCarteraFaseTabla,
    pagosRealizadosOrdenados,
    pagosRealizadosData,
    pagePagosRegistrados,
    setPagePagosRegistrados,
    perPagePagosRegistrados,
    loadingPagosRealizados,
    pagoEditando,
    setPagoEditando,
    showRegistrarPago,
    setShowRegistrarPago,
    escaneandoComprobanteAgregarPago,
    onEscanearComprobanteAgregar,
    onAbrirComprobante,
    onEditarPago,
    onEliminarPago,
    eliminandoPagoId,
    clavesDocumentoPagina,
    coherenciaPanel,
  } = props

  if (!cedulaParaPagosRealizados) return null

  return (
''' + body.replace(
    "{cedulaParaPagosRealizados ? (\n              <>", "", 1
).replace(
    "            ) : null}\n", "", 1
) + "\n  )\n}\n"

OUT.write_text(component, encoding="utf-8")

replacement = """            <PagosRegistradosRevisionSection
              cedulaParaPagosRealizados={cedulaParaPagosRealizados}
              pagosRegistradosCardRef={pagosRegistradosCardRef}
              vieneDesdeFiniquitos={vieneDesdeFiniquitos}
              soloLectura={soloLectura}
              prestamoData={prestamoData}
              aplicarCascadaPagosMutation={aplicarCascadaPagosMutation}
              reescaneandoCartera={reescaneandoCartera}
              onReescanearCartera={() => void reescanearComprobantesCarteraPrestamo(/* prestamo */)}
              conciliarCarteraFaseTabla={conciliarCarteraFaseTabla}
              pagosRealizadosOrdenados={pagosRealizadosOrdenados}
              pagosRealizadosData={pagosRealizadosData}
              pagePagosRegistrados={pagePagosRegistrados}
              setPagePagosRegistrados={setPagePagosRegistrados}
              perPagePagosRegistrados={PER_PAGE_PAGOS_REGISTRADOS}
              loadingPagosRealizados={loadingPagosRealizados}
              pagoEditando={pagoEditando}
              setPagoEditando={setPagoEditando}
              showRegistrarPago={showRegistrarPago}
              setShowRegistrarPago={setShowRegistrarPago}
              escaneandoComprobanteAgregarPago={escaneandoComprobanteAgregarPago}
              onEscanearComprobanteAgregar={handleEscanearComprobanteAgregarPago}
              onAbrirComprobante={openStaffComprobanteForList}
              onEditarPago={handleEditarPagoRegistrado}
              onEliminarPago={handleEliminarPagoRegistrado}
              eliminandoPagoId={eliminandoPagoId}
              clavesDocumentoPagina={clavesDocumentoPagina}
              coherenciaPanel={null}
            />
"""

print("Wrote", OUT, "— manual integration required for props/handlers")
print("Body lines:", body.count(chr(10)))
