import type React from 'react'
import type { RefObject } from 'react'
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
  cedulaParaPagosRealizados: string
  pagosRegistradosCardRef: RefObject<HTMLDivElement>
  vieneDesdeFiniquitos: boolean
  prestamoData: Partial<PrestamoData>
  soloLectura: boolean
  aplicarCascadaPagosMutation: {
    isPending: boolean
    mutate: () => void
  }
  abrirAgregarPagoRevision: () => void
  escaneandoComprobanteAgregarPago: boolean
  abrirSelectorEscaneoComprobanteAgregarPago: () => void
  reescaneandoCartera: boolean
  reescaneoCarteraProgreso: {
    hecho: number
    total: number
    fase: 'ocr' | 'cascada'
  } | null
  ejecutarReescaneoCartera: () => void | Promise<void>
  loadingPagosRealizados: boolean
  fetchingPagosRealizados: boolean
  refetchPagosRealizados: () => void | Promise<unknown>
  isAdmin: boolean
  conciliarTablaUi: ConciliarTablaUiState | null
  setConciliarTablaUi: React.Dispatch<
    React.SetStateAction<ConciliarTablaUiState | null>
  >
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
