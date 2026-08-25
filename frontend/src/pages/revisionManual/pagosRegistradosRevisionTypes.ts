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
    /** Suma de todas las filas del crédito (igual que la tabla). */
    suma_monto_pagado: number
    /** Total filas en pagos. */
    cantidad: number
    cantidad_operativos?: number
    cantidad_no_operativos?: number
    /** Suma excluyendo anulado/duplicado (cascada). */
    suma_monto_operativos?: number
    suma_monto_total_bd?: number
    cantidad_pendiente?: number
    suma_monto_pendiente?: number
    cantidad_pagado?: number
    suma_monto_estado_pagado?: number
    /** Pagos con confirmacion en Conciliacion Bancos. */
    cantidad_conciliacion_bancaria?: number
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
  escaneoLoteProgreso: { hecho: number; total: number } | null
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
  /** Todos los pagos del crédito mostrados en la tabla. */
  pagosRegistradosOrdenados: Pago[]
  /** Subconjunto con estado anulado/duplicado (aviso; siguen en la tabla). */
  pagosNoOperativosOrdenados: Pago[]
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
  agregadosCuotasRevision: {
    sumMonto: number
    sumPagado: number
    vencidosN: number
    vencidosSaldo: number
    moraN: number
    moraSaldo: number
  }
}
