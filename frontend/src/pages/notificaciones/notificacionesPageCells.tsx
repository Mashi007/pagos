import { useState, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'

import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Scale,
} from 'lucide-react'

import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'

import {
  notificacionService,
  type AplicarAbonosDriveCuotasResponse,
  type ClienteRetrasadoItem,
  type CompararAbonosDriveCuotasResponse,
  type CompararFechaEntregaQvsAprobacionResponse,
} from '../../services/notificacionService'

import { revisionManualService } from '../../services/revisionManualService'

import { useSimpleAuth } from '../../store/simpleAuthStore'

import { toast } from 'sonner'

import {
  invalidateListasNotificacionesMora,
  invalidatePagosPrestamosRevisionYCuotas,
} from '../../constants/queryKeys'

import { getErrorMessage } from '../../types/errors'

export type NotificacionesCuotasSortCol =
  | 'numero_cuota'
  | 'fecha_vencimiento'
  | 'cuotas_atrasadas'
  | 'total_pendiente'
  | 'diferencia_abono'

export function SortArrowsCuotas({
  column,
  labelAsc,
  labelDesc,
  sortCol,
  sortDir,
  onAsc,
  onDesc,
}: {
  column: NotificacionesCuotasSortCol
  labelAsc: string
  labelDesc: string
  sortCol: NotificacionesCuotasSortCol | null
  sortDir: 'asc' | 'desc'
  onAsc: (c: NotificacionesCuotasSortCol) => void
  onDesc: (c: NotificacionesCuotasSortCol) => void
}) {
  const upActive = sortCol === column && sortDir === 'asc'
  const downActive = sortCol === column && sortDir === 'desc'
  const baseBtn =
    'rounded p-0.5 text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500'
  return (
    <span
      className="inline-flex shrink-0 flex-col gap-0 leading-none"
      role="group"
    >
      <button
        type="button"
        className={`${baseBtn} ${upActive ? 'text-blue-600' : ''}`}
        aria-label={labelAsc}
        onClick={() => onAsc(column)}
      >
        <ChevronUp className="h-3.5 w-3.5" strokeWidth={2.5} />
      </button>
      <button
        type="button"
        className={`${baseBtn} ${downActive ? 'text-blue-600' : ''}`}
        aria-label={labelDesc}
        onClick={() => onDesc(column)}
      >
        <ChevronDown className="h-3.5 w-3.5" strokeWidth={2.5} />
      </button>
    </span>
  )
}

/** Texto fijo de probación / cierre rápido desde la tabla de notificaciones. */
const TEXTO_NOTA_REVISION_DESDE_NOTIF = 'Revisión en módulo de notificación'

export function detalleErrorRevisionNotif(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: string } } })?.response?.data
    ?.detail
  return typeof d === 'string'
    ? d
    : (e as Error)?.message || 'Error desconocido'
}

export function soloDigitosCedulaNotif(s: string): string {
  return String(s ?? '').replace(/\D/g, '')
}

/** Coincidencia por subcadena: prioriza comparación solo dígitos (V-123 / 123). */
export function filaCoincideFiltroCedulaNotif(
  row: ClienteRetrasadoItem,
  filtro: string
): boolean {
  const t = filtro.trim()
  if (!t) return true
  const qDigits = soloDigitosCedulaNotif(t)
  const ced = String(row.cedula ?? '')
  if (qDigits.length > 0) {
    return soloDigitosCedulaNotif(ced).includes(qDigits)
  }
  return ced.toLowerCase().includes(t.toLowerCase())
}

/** Filtro de columna «Diferencia Abono» (General): criterios alineados con `diferencia` y `tolerancia` del modal/caché. */
export type FiltroDiferenciaAbonoGeneral =
  | 'todas'
  | 'cero'
  | 'drive_mayor'
  | 'drive_menor'

export function toleranciaCompararAbonos(cmp: CompararAbonosDriveCuotasResponse): number {
  const t = cmp.tolerancia
  return typeof t === 'number' && Number.isFinite(t) ? t : 0.02
}

export function filaCumpleFiltroDiferenciaAbonoGeneral(
  filtro: FiltroDiferenciaAbonoGeneral,
  cmp: CompararAbonosDriveCuotasResponse
): boolean {
  if (filtro === 'todas') return true
  const tol = toleranciaCompararAbonos(cmp)
  if (filtro === 'drive_mayor') {
    const d = cmp.diferencia
    if (d == null || Number.isNaN(Number(d))) return false
    return Number(d) > tol
  }
  if (filtro === 'cero') return cmp.coincide_aproximado === true
  if (filtro === 'drive_menor') {
    const d = cmp.diferencia
    if (d == null || Number.isNaN(Number(d))) return false
    return Number(d) < -tol
  }
  return true
}

export function fmtDiferenciaAbonoCelda(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return '-'
  return Number(n).toLocaleString('es-VE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/** Filtro columna «Diferencia fecha» (submódulo Fecha): días = Q (hoja) − fecha_aprobacion (BD). */
export type FiltroDiferenciaFechaGeneral = 'todas' | 'cero' | 'mayor_cero' | 'menor_cero'

export function filaCumpleFiltroDiferenciaFechaGeneral(
  filtro: FiltroDiferenciaFechaGeneral,
  cmp: CompararFechaEntregaQvsAprobacionResponse
): boolean {
  if (filtro === 'todas') return true
  const puede =
    cmp.puede_aplicar === true ||
    (typeof cmp.indicador === 'string' && cmp.indicador.toLowerCase() === 'si')
  if (filtro === 'cero') {
    return cmp.coincide_calendario === true || cmp.coincide_aproximado === true
  }
  if (filtro === 'mayor_cero') return puede
  if (filtro === 'menor_cero') {
    const d = cmp.diferencia_dias
    if (d == null || Number.isNaN(Number(d))) return false
    return (
      cmp.coincide_calendario !== true &&
      cmp.coincide_aproximado !== true &&
      !puede &&
      Number(d) < 0
    )
  }
  return true
}

export function fmtDiferenciaFechaDiasCelda(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return '-'
  const v = Number(n)
  if (v === 0) return '0'
  if (v > 0) return `+${v}`
  return String(v)
}

export function DiferenciaFechaGeneralCell({
  row,
  data,
  isLoading,
  isError,
}: {
  row: ClienteRetrasadoItem
  data?: CompararFechaEntregaQvsAprobacionResponse
  isLoading: boolean
  isError: boolean
}) {
  const pid = row.prestamo_id
  const ced = (row.cedula || '').trim()
  if (pid == null || !ced) {
    return (
      <span className="text-xs text-muted-foreground" title="Sin cédula o préstamo">
        -
      </span>
    )
  }
  if (isLoading) {
    return <span className="text-xs text-muted-foreground">…</span>
  }
  if (isError || !data) {
    return (
      <span
        className="text-xs text-muted-foreground"
        title="Dato del caché semanal (04:00 Caracas, domingo). Si está vacío, aún no hay caché en BD para este préstamo."
      >
        -
      </span>
    )
  }
  return (
    <span
      className={`tabular-nums text-sm font-medium ${
        data.coincide_calendario ? 'text-green-700' : 'text-amber-800'
      }`}
      title="Días (columna Q entrega en hoja − fecha_aprobacion en sistema). Valor del listado desde caché en BD."
    >
      {fmtDiferenciaFechaDiasCelda(data.diferencia_dias)}
    </span>
  )
}

export function DiferenciaAbonoGeneralCell({
  row,
  data,
  isLoading,
  isError,
}: {
  row: ClienteRetrasadoItem
  data?: CompararAbonosDriveCuotasResponse
  isLoading: boolean
  isError: boolean
}) {
  const pid = row.prestamo_id
  const ced = (row.cedula || '').trim()
  if (pid == null || !ced) {
    return (
      <span className="text-xs text-muted-foreground" title="Sin cédula o préstamo">
        -
      </span>
    )
  }
  if (isLoading) {
    return <span className="text-xs text-muted-foreground">…</span>
  }
  if (isError || !data) {
    return (
      <span
        className="text-xs text-muted-foreground"
        title="Dato del cierre nocturno (02:00 Caracas). Si está vacío, aún no hay caché en BD para este préstamo."
      >
        -
      </span>
    )
  }
  return (
    <span
      className={`tabular-nums text-sm font-medium ${
        data.coincide_aproximado ? 'text-green-700' : 'text-amber-800'
      }`}
      title="Diferencia (hoja Drive − total pagado en cuotas). Valor fijo del listado: se actualiza en servidor a las 02:00 (Caracas) y al aplicar ABONOS desde la balanza."
    >
      {fmtDiferenciaAbonoCelda(data.diferencia)}
    </span>
  )
}

/**
 * Triángulo: un clic marca revisado (visto) y deja constancia en notas del cliente; si no hay
 * permiso para notas, en observaciones de la revisión. Visto: solo admin puede reabrir a revisando.
 */
export function RevisionManualNotifCell({ row }: { row: ClienteRetrasadoItem }) {
  const queryClient = useQueryClient()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const pid = row.prestamo_id
  const rev = (row.revision_manual_estado || 'pendiente').toLowerCase().trim()
  const esVisto = rev === 'revisado'
  const [busy, setBusy] = useState(false)

  if (pid == null) return null

  const lineaAuditoria = () => {
    const ts = new Date().toLocaleString('es-VE', {
      timeZone: 'America/Caracas',
    })
    return `${ts} - ${TEXTO_NOTA_REVISION_DESDE_NOTIF}`
  }

  const invalidarListas = async () => {
    await invalidateListasNotificacionesMora(queryClient, {
      skipCrossTabBroadcast: true,
    })
    await queryClient.invalidateQueries({
      queryKey: ['revision-manual-prestamos'],
    })
  }

  const marcarVisto = async () => {
    setBusy(true)
    try {
      const detalle =
        await revisionManualService.getDetallePrestamoRevision(pid)
      const estadoSrv = (
        detalle?.revision?.estado_revision || 'pendiente'
      ).toLowerCase()

      if (estadoSrv === 'revisado') {
        await invalidarListas()
        toast.message('Ya constaba como revisado.')
        return
      }

      const clienteId = detalle?.cliente?.cliente_id as number | undefined
      if (!clienteId) {
        toast.error('No se pudo obtener el cliente del préstamo.')
        return
      }

      const notasPrev = String(detalle?.cliente?.notas || '').trim()
      const linea = lineaAuditoria()
      const notasNuevas = notasPrev ? `${notasPrev}\n${linea}` : linea

      let notasClienteOk = false
      try {
        await revisionManualService.editarCliente(
          clienteId,
          { notas: notasNuevas },
          { prestamoId: pid }
        )
        notasClienteOk = true
      } catch (e) {
        const msg = detalleErrorRevisionNotif(e)
        toast.message(
          `Notas del cliente no actualizadas (${msg}). Se deja constancia en la revisión.`
        )
      }

      await revisionManualService.cambiarEstadoRevision(pid, {
        nuevo_estado: 'revisado',
        ...(notasClienteOk ? {} : { observaciones: linea }),
      })

      await invalidarListas()
      toast.success('Marcado como visto (revisión en módulo de notificación).')
    } catch (e) {
      toast.error(detalleErrorRevisionNotif(e))
    } finally {
      setBusy(false)
    }
  }

  const quitarVisto = async () => {
    if (!esAdmin) {
      toast.error(
        'Solo un administrador puede quitar el visto. Use Revisión manual en el menú.'
      )
      return
    }
    setBusy(true)
    try {
      await revisionManualService.cambiarEstadoRevision(pid, {
        nuevo_estado: 'revisando',
      })
      await invalidarListas()
      toast.success('Revisión reabierta (estado revisando).')
    } catch (e) {
      toast.error(detalleErrorRevisionNotif(e))
    } finally {
      setBusy(false)
    }
  }

  const btnBase =
    'inline-flex h-9 w-9 items-center justify-center rounded-md border border-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50'

  if (!esVisto) {
    return (
      <button
        type="button"
        role="switch"
        aria-checked={false}
        disabled={busy}
        title="Marcar visto: revisión cerrada y nota genérica en datos del cliente (o en observaciones si no hay permiso)"
        aria-label="Marcar como revisado desde notificaciones con nota genérica"
        onClick={() => {
          if (busy) return
          void marcarVisto()
        }}
        className={`${btnBase} bg-amber-50 text-amber-600 hover:bg-amber-100`}
      >
        <AlertTriangle className="h-4 w-4" aria-hidden />
      </button>
    )
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked
      disabled={busy}
      title={
        esAdmin
          ? 'Visto: clic para reabrir revisión (solo admin)'
          : 'Visto: solo un administrador puede reabrir'
      }
      aria-label="Revisión cerrada. Clic para reabrir si es administrador"
      onClick={() => {
        if (busy) return
        void quitarVisto()
      }}
      className={`${btnBase} bg-emerald-50 text-green-600 hover:bg-emerald-100`}
    >
      <CheckCircle2 className="h-4 w-4" aria-hidden />
    </button>
  )
}

export function umbralConfirmaAbonosUsd(
  data: CompararAbonosDriveCuotasResponse | null
): number {
  const u = data?.umbral_doble_confirmacion_abonos_usd
  return u != null && Number.isFinite(Number(u)) ? Number(u) : 5000
}

export function abonosSuperanUmbralConfirmo(
  data: CompararAbonosDriveCuotasResponse | null,
  abonos: number | null | undefined
): boolean {
  if (abonos == null || Number.isNaN(Number(abonos))) return false
  return Number(abonos) > umbralConfirmaAbonosUsd(data)
}

/**
 * Icono junto a revisión manual: compara ABONOS (hoja CONCILIACIÓN en BD) vs suma total_pagado en cuotas del préstamo.
 * El borrado de pagos y la cascada solo ocurren si el usuario pulsa explícitamente «Sí» y confirma (no al abrir el diálogo).
 */
export function CompararAbonosDriveCuotasCell({ row }: { row: ClienteRetrasadoItem }) {
  const queryClient = useQueryClient()
  const location = useLocation()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const pid = row.prestamo_id
  const ced = (row.cedula || '').trim()
  const [open, setOpen] = useState(false)
  const [paso, setPaso] = useState<'resumen' | 'confirmar'>('resumen')
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [data, setData] = useState<CompararAbonosDriveCuotasResponse | null>(null)
  const [confirmacionMontosAltos, setConfirmacionMontosAltos] = useState('')

  /** Cierra el modal sin cambiar de ruta (mismo submenú de notificaciones). */
  const onDialogAbonosOpenChange = useCallback((v: boolean) => {
    setOpen(v)
    if (!v) {
      setPaso('resumen')
      setData(null)
      setConfirmacionMontosAltos('')
    }
  }, [])

  if (pid == null || !ced) return null

  const loteResuelto =
    !data?.requiere_seleccion_lote ||
    Boolean((data?.lote_aplicado ?? '').toString().trim())

  const puedeOperar =
    loteResuelto &&
    (data?.puede_aplicar === true ||
      (typeof data?.indicador === 'string' && data.indicador.toLowerCase() === 'si'))

  const abrir = async (loteExplicito?: string | null) => {
    setOpen(true)
    setPaso('resumen')
    setConfirmacionMontosAltos('')
    setLoading(true)
    setData(null)
    try {
      const loteQ = (loteExplicito ?? '').trim()
      const res = await notificacionService.getCompararAbonosDriveCuotas({
        cedula: ced,
        prestamoId: pid,
        ...(loteQ ? { lote: loteQ } : {}),
      })
      setData(res)
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo comparar ABONOS vs cuotas.')
      onDialogAbonosOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  const aplicar = async () => {
    setApplying(true)
    try {
      const loteAplicar = (data?.lote_aplicado ?? '').toString().trim() || undefined
      const needConf =
        data != null && abonosSuperanUmbralConfirmo(data, data.abonos_drive)
      const res: AplicarAbonosDriveCuotasResponse =
        await notificacionService.postAplicarAbonosDriveACuotas({
          cedula: ced,
          prestamoId: pid,
          ...(loteAplicar ? { lote: loteAplicar } : {}),
          ...(needConf
            ? { confirmacionMontosAltos: confirmacionMontosAltos.trim() }
            : {}),
        })
      toast.success(
        `Aplicado: pago #${res.pago_id}. Pagos eliminados: ${res.pagos_eliminados}. Cuotas completadas: ${res.cuotas_completadas}.`
      )
      onDialogAbonosOpenChange(false)
      await invalidatePagosPrestamosRevisionYCuotas(queryClient, {
        skipNotificacionesMora: true,
        includeDashboardMenu: true,
      })
      await invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo aplicar ABONOS a cuotas.')
    } finally {
      setApplying(false)
    }
  }

  const fmt = (n: number | null | undefined) =>
    n == null || Number.isNaN(Number(n))
      ? '-'
      : Number(n).toLocaleString('es-VE', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })

  const btnBase =
    'inline-flex h-9 w-9 items-center justify-center rounded-md border border-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50'

  const pillBase =
    'inline-flex min-w-[2.25rem] items-center justify-center rounded-md border px-2 py-1 text-xs font-semibold'

  const needConfirmaMontosAltos =
    data != null && abonosSuperanUmbralConfirmo(data, data.abonos_drive)

  return (
    <>
      <button
        type="button"
        className={`${btnBase} bg-sky-50 text-sky-700 hover:bg-sky-100`}
        title="Comparar ABONOS (Drive / hoja CONCILIACIÓN) con total pagado en cuotas (BD)"
        aria-label="Comparar ABONOS de la hoja con total pagado en cuotas"
        onClick={() => {
          void abrir()
        }}
      >
        <Scale className="h-4 w-4" aria-hidden />
      </button>

      <Dialog open={open} onOpenChange={onDialogAbonosOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {paso === 'confirmar'
                ? 'Confirmar aplicación desde la hoja'
                : 'ABONOS (hoja) vs cuotas pagadas'}
            </DialogTitle>
          </DialogHeader>

          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : paso === 'confirmar' && data ? (
            <div className="space-y-3 text-sm">
              <p className="text-amber-900">
                Se eliminarán todos los pagos del préstamo #{data.prestamo_id} y se registrará un
                único pago por{' '}
                <span className="font-semibold tabular-nums">{fmt(data.abonos_drive)}</span>{' '}
                (ABONOS hoja), aplicado en cascada a las cuotas. Esta acción no se deshace desde
                aquí.
              </p>
              <div className="rounded-md border border-slate-200 bg-muted/30 p-3 text-xs text-foreground">
                <p className="mb-1 font-semibold text-slate-800">Verifique antes de aplicar</p>
                <ul className="list-none space-y-1 tabular-nums">
                  <li>
                    Cédula: <span className="font-medium">{data.cedula}</span>
                  </li>
                  <li>
                    Préstamo: <span className="font-medium">#{data.prestamo_id}</span>
                  </li>
                  <li>
                    Lote (hoja):{' '}
                    <span className="font-mono font-medium">
                      {(data.lote_aplicado ?? '').toString().trim() || '-'}
                    </span>
                  </li>
                  <li>
                    Monto ABONOS (hoja):{' '}
                    <span className="font-semibold">{fmt(data.abonos_drive)}</span>
                  </li>
                </ul>
              </div>
              {needConfirmaMontosAltos ? (
                <div className="space-y-2 rounded-md border border-amber-300 bg-amber-50/90 p-3 text-xs text-amber-950">
                  <p className="font-medium">
                    Monto elevado (&gt; {umbralConfirmaAbonosUsd(data).toLocaleString('es-VE')} USD).
                    Escriba <span className="font-mono">CONFIRMO</span> para continuar.
                  </p>
                  <Input
                    id="confirma-abonos-montos-altos"
                    autoComplete="off"
                    placeholder="CONFIRMO"
                    value={confirmacionMontosAltos}
                    onChange={e => setConfirmacionMontosAltos(e.target.value)}
                    className="bg-white font-mono text-sm"
                    aria-label="Confirmación por monto elevado: escriba CONFIRMO"
                  />
                </div>
              ) : null}
              <p className="text-xs text-muted-foreground">
                Solo continúe si revisó cédula, hoja y montos. Requiere administrador.
              </p>
            </div>
          ) : data ? (
            <div className="space-y-3 text-sm">
              <p className="text-muted-foreground">
                Cédula <span className="font-medium text-foreground">{data.cedula}</span>
                {' · '}
                Préstamo <span className="font-medium text-foreground">#{data.prestamo_id}</span>
              </p>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                <Link
                  to={`/revision-manual/editar/${pid}`}
                  state={{
                    returnTo: `${location.pathname}${location.search || ''}`,
                  }}
                  className="font-medium text-blue-600 hover:underline"
                >
                  Abrir en revisión manual
                </Link>
                <span className="text-muted-foreground">
                  (edición del préstamo y cuotas en otra pantalla)
                </span>
              </div>

              {data.hoja_sync_antigua ? (
                <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                  La hoja supera las 48 h desde la última sincronización (aprox.{' '}
                  {data.hoja_sync_antigua_horas != null
                    ? `${data.hoja_sync_antigua_horas} h`
                    : '-'}
                  ). Resincronice CONCILIACIÓN si necesita ABONOS al día.
                </p>
              ) : null}

              {data.prestamo_huella ? (
                <div className="rounded-md border bg-slate-50 p-3 text-xs text-slate-900">
                  <p className="mb-1 font-semibold text-slate-800">
                    Huella del préstamo en BD (alinear con fila de la hoja)
                  </p>
                  <ul className="list-none space-y-0.5 tabular-nums">
                    <li>
                      Total financiamiento:{' '}
                      {fmt(data.prestamo_huella.total_financiamiento)}
                    </li>
                    <li>N.º cuotas: {data.prestamo_huella.numero_cuotas}</li>
                    <li>Modalidad: {data.prestamo_huella.modalidad_pago || '-'}</li>
                  </ul>
                </div>
              ) : null}

              {!puedeOperar ? (
                <p className="rounded-md border border-slate-200 bg-muted/40 p-2 text-xs text-slate-800">
                  <span className="font-medium">Regla: </span>
                  solo se puede aplicar desde aquí si ABONOS en la hoja es{' '}
                  <strong>mayor</strong> que la suma de los pagos reflejados en cuotas del préstamo
                  (total pagado en cuotas), más una tolerancia de ±{data.tolerancia}. Si ABONOS es
                  igual o menor (p. ej. cero o ya cubierto en BD), el flujo queda en «No»: aquí no se
                  reordenan pagos ni se corrigen diferencias pequeñas; use revisión manual o la
                  conciliación habitual.
                </p>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground text-xs">Indicador:</span>
                <button
                  type="button"
                  disabled={!puedeOperar || !esAdmin || applying}
                  title={
                    !esAdmin
                      ? 'Solo administradores pueden operar.'
                      : data?.requiere_seleccion_lote && !loteResuelto
                        ? 'Elija primero el lote de la hoja que corresponde a este préstamo.'
                        : puedeOperar
                          ? 'Pulsar Sí para continuar al paso de confirmación (no aplica nada todavía).'
                          : 'ABONOS no supera el total en cuotas: no hay operación.'
                  }
                  onClick={() => {
                    if (!puedeOperar || !esAdmin || applying) return
                    setPaso('confirmar')
                  }}
                  className={`${pillBase} ${
                    puedeOperar
                      ? 'border-green-600 bg-green-50 text-green-800 hover:bg-green-100 disabled:opacity-50'
                      : 'cursor-not-allowed border-muted bg-muted/40 text-muted-foreground'
                  }`}
                  aria-label={
                    puedeOperar
                      ? 'Sí: ABONOS mayor que total en cuotas; pulse para confirmar operación'
                      : 'Sí: no aplica'
                  }
                >
                  Sí
                </button>
                <button
                  type="button"
                  className={`${pillBase} ${
                    !puedeOperar
                      ? 'border-slate-600 bg-slate-100 text-slate-800 hover:bg-slate-200/80'
                      : 'border-muted bg-muted/30 text-muted-foreground hover:bg-muted/50'
                  }`}
                  title="Cierra el cuadro sin aplicar nada; permanece en esta misma pantalla de notificaciones."
                  aria-label="No: cerrar el cuadro sin cambiar de submenú"
                  onClick={() => onDialogAbonosOpenChange(false)}
                >
                  No
                </button>
              </div>

              {data.requiere_seleccion_lote &&
              data.opciones_lote &&
              data.opciones_lote.length > 0 ? (
                <div className="rounded-md border border-amber-200 bg-amber-50/90 p-3 text-xs text-amber-950">
                  <p className="mb-2 font-medium">
                    Hay varios lotes en la hoja para esta cédula. Elija el que corresponde a este
                    préstamo (solo se usará el abono de esa fila; no se mezclan otros créditos).
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {data.opciones_lote.map(op => (
                      <Button
                        key={op.lote}
                        type="button"
                        size="sm"
                        variant="outline"
                        className="border-amber-300 bg-white text-amber-950 hover:bg-amber-100"
                        disabled={loading}
                        onClick={() => {
                          void abrir(op.lote)
                        }}
                      >
                        Lote {op.lote} - {fmt(op.abonos)}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}

              {data.lote_aplicado && loteResuelto ? (
                <p className="rounded-md border border-sky-200 bg-sky-50/90 p-2 text-xs text-sky-950">
                  <span className="font-semibold">Resumen: </span>
                  Lote <span className="font-mono">{data.lote_aplicado}</span>
                  {' · '}
                  ABONOS hoja{' '}
                  <span className="font-medium tabular-nums">{fmt(data.abonos_drive)}</span>
                  {' · '}
                  Préstamo #{data.prestamo_id}
                </p>
              ) : data.lote_aplicado ? (
                <p className="text-xs text-muted-foreground">
                  Lote usado para esta comparación:{' '}
                  <span className="font-mono font-medium text-foreground">{data.lote_aplicado}</span>
                </p>
              ) : null}

              <dl className="grid grid-cols-1 gap-2 rounded-md border bg-muted/30 p-3">
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">ABONOS (hoja Drive)</dt>
                  <dd className="font-medium tabular-nums">{fmt(data.abonos_drive)}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Total pagado (cuotas)</dt>
                  <dd className="font-medium tabular-nums">
                    {fmt(data.total_pagado_cuotas)}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Diferencia (hoja − cuotas)</dt>
                  <dd
                    className={`font-semibold tabular-nums ${
                      data.coincide_aproximado ? 'text-green-700' : 'text-amber-800'
                    }`}
                  >
                    {fmt(data.diferencia)}
                  </dd>
                </div>
              </dl>
              <p className="text-xs text-muted-foreground">
                Filas de la hoja que corresponden a este préstamo:{' '}
                <span className="font-medium text-foreground">
                  {data.filas_hoja_coincidentes}
                </span>
                {data.filas_misma_cedula_hoja != null ? (
                  <>
                    {' '}
                    · Filas con la misma cédula en la hoja (todas):{' '}
                    <span className="font-medium text-foreground">
                      {data.filas_misma_cedula_hoja}
                    </span>
                  </>
                ) : null}
                {data.hoja_synced_at ? (
                  <>
                    {' '}
                    · Última sync hoja:{' '}
                    <span className="font-medium text-foreground">
                      {new Date(data.hoja_synced_at).toLocaleString('es-VE', {
                        timeZone: 'America/Caracas',
                      })}
                    </span>
                  </>
                ) : null}
              </p>
              {data.columna_cedula_detectada ||
              data.columna_abonos_detectada ||
              data.columna_lote_detectada ? (
                <p className="text-xs text-muted-foreground">
                  Columnas detectadas:{' '}
                  <span className="font-mono text-foreground">
                    {data.columna_cedula_detectada ?? '-'}
                  </span>
                  {' · '}
                  <span className="font-mono text-foreground">
                    {data.columna_abonos_detectada ?? '-'}
                  </span>
                  {data.columna_lote_detectada ? (
                    <>
                      {' · '}
                      <span className="font-mono text-foreground">
                        {data.columna_lote_detectada}
                      </span>
                    </>
                  ) : null}
                </p>
              ) : null}
              {data.advertencias?.length ? (
                <ul className="list-disc space-y-1 pl-4 text-xs text-amber-900">
                  {data.advertencias.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              ) : null}
              {data.coincide_aproximado ? (
                <p className="text-xs font-medium text-green-700">
                  Coinciden (tolerancia ±{data.tolerancia}).
                </p>
              ) : data.diferencia != null ? (
                <p className="text-xs text-amber-900">
                  Hay diferencia mayor a la tolerancia (±{data.tolerancia}). Revise sync de la
                  hoja o pagos aplicados a cuotas.
                </p>
              ) : null}
              {!esAdmin && puedeOperar ? (
                <p className="text-xs text-muted-foreground">
                  El indicador «Sí» requiere administrador para operar.
                </p>
              ) : null}
            </div>
          ) : null}

          <DialogFooter className="gap-2 sm:gap-0">
            {paso === 'confirmar' ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  disabled={applying}
                  onClick={() => {
                    setConfirmacionMontosAltos('')
                    setPaso('resumen')
                  }}
                >
                  Volver
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  disabled={
                    applying ||
                    !esAdmin ||
                    (needConfirmaMontosAltos &&
                      confirmacionMontosAltos.trim().toUpperCase() !== 'CONFIRMO')
                  }
                  onClick={() => {
                    void aplicar()
                  }}
                >
                  {applying ? 'Aplicando…' : 'Confirmar y aplicar'}
                </Button>
              </>
            ) : (
              <Button
                type="button"
                variant="outline"
                onClick={() => onDialogAbonosOpenChange(false)}
              >
                Cerrar
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export function fmtFechaNotifIso(iso?: string | null): string {
  if (iso == null || String(iso).trim() === '') return '-'
  const s = String(iso).trim()
  const t = Date.parse(s.length >= 10 ? s.slice(0, 10) : s)
  if (Number.isNaN(t)) return s
  return new Date(t).toLocaleDateString('es-VE', { timeZone: 'America/Caracas' })
}

export function fmtDiferenciaDiasNotif(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return '-'
  const v = Number(n)
  if (v === 0) return '0'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v}`
}

/**
 * Misma estructura visual que ABONOS vs cuotas: huella, aviso de sync, regla, indicador Sí/No,
 * tabla de comparación y pie. La fecha Q debe ser estrictamente posterior a fecha_aprobación
 * para «Sí» (paralelo a hoja &gt; sistema en ABONOS). El paso de confirmación llama al backend:
 * `PUT /prestamos/{id}` vía endpoint de notificaciones (misma persistencia y recálculo de
 * vencimientos que revisión manual al cambiar la fecha de aprobación).
 */
export function CompararFechaEntregaQAprobacionCell({ row }: { row: ClienteRetrasadoItem }) {
  const queryClient = useQueryClient()
  const location = useLocation()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const pid = row.prestamo_id
  const ced = (row.cedula || '').trim()
  const [open, setOpen] = useState(false)
  const [paso, setPaso] = useState<'resumen' | 'confirmar'>('resumen')
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [data, setData] = useState<CompararFechaEntregaQvsAprobacionResponse | null>(null)

  const onDialogFechaOpenChange = useCallback((v: boolean) => {
    setOpen(v)
    if (!v) {
      setPaso('resumen')
      setData(null)
      setApplying(false)
    }
  }, [])

  if (pid == null || !ced) return null

  const loteResuelto =
    !data?.requiere_seleccion_lote ||
    Boolean((data?.lote_aplicado ?? '').toString().trim())

  const puedeOperar =
    loteResuelto &&
    (data?.puede_aplicar === true ||
      (typeof data?.indicador === 'string' && data.indicador.toLowerCase() === 'si'))

  const abrir = async (loteExplicito?: string | null) => {
    setOpen(true)
    setPaso('resumen')
    setLoading(true)
    setData(null)
    try {
      const loteQ = (loteExplicito ?? '').trim()
      const res = await notificacionService.getCompararFechaEntregaQvsAprobacion({
        cedula: ced,
        prestamoId: pid,
        ...(loteQ ? { lote: loteQ } : {}),
      })
      setData(res)
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo comparar la columna Q con la fecha de aprobación.')
      onDialogFechaOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  const aplicarFechaQComoAprobacion = async () => {
    if (!data || pid == null) return
    setApplying(true)
    try {
      const loteA = (data.lote_aplicado ?? '').toString().trim() || undefined
      await notificacionService.postAplicarFechaEntregaQComoFechaAprobacion({
        cedula: ced,
        prestamoId: pid,
        ...(loteA ? { lote: loteA } : {}),
      })
      toast.success(
        'Fecha de aprobación guardada en BD con la fecha de la columna Q. Si había cuotas en APROBADO/LIQUIDADO y cambió la base, se recalcularon vencimientos (misma regla que al editar en revisión manual).'
      )
      onDialogFechaOpenChange(false)
      await invalidatePagosPrestamosRevisionYCuotas(queryClient, {
        skipNotificacionesMora: true,
        includeDashboardMenu: true,
      })
      await invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })
    } catch (e) {
      toast.error(
        getErrorMessage(e) ||
          'No se pudo guardar la fecha de aprobación. Revise el mensaje del servidor o use revisión manual.'
      )
    } finally {
      setApplying(false)
    }
  }

  const btnBase =
    'inline-flex h-9 w-9 items-center justify-center rounded-md border border-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50'

  const pillBase =
    'inline-flex min-w-[2.25rem] items-center justify-center rounded-md border px-2 py-1 text-xs font-semibold'

  const colQEtiqueta =
    data != null
      ? `${(data.columna_q_letra ?? 'Q').trim()}${
          (data.columna_q_header_detectado ?? '').toString().trim()
            ? ` (${String(data.columna_q_header_detectado).trim()})`
            : ''
        }`
      : 'Q'

  return (
    <>
      <button
        type="button"
        className={`${btnBase} bg-sky-50 text-sky-700 hover:bg-sky-100`}
        title="Comparar fecha de entrega (columna Q de CONCILIACIÓN) con fecha de aprobación del préstamo (BD)"
        aria-label="Comparar columna Q con fecha de aprobación"
        onClick={() => {
          void abrir()
        }}
      >
        <Calendar className="h-4 w-4" aria-hidden />
      </button>

      <Dialog open={open} onOpenChange={onDialogFechaOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {paso === 'confirmar'
                ? 'Confirmar: fecha Q como fecha de aprobación'
                : 'Fecha (columna Q) vs fecha de aprobación'}
            </DialogTitle>
          </DialogHeader>

          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : paso === 'confirmar' && data ? (
            <div className="space-y-3 text-sm">
              <p className="text-slate-800">
                Va a guardar en la tabla <span className="font-semibold">prestamos</span> la fecha
                de la columna Q como <strong>nueva fecha de aprobación</strong> (y la base de cálculo
                alineada al mismo día calendario). No modifica la hoja de Google. Si el préstamo
                está en APROBADO o LIQUIDADO con cuotas y la base cambia, el servidor{' '}
                <strong>recalcula fechas de vencimiento</strong> en <span className="font-semibold">cuotas</span>{' '}
                con la misma lógica que al guardar desde revisión manual.
              </p>
              <ul className="list-none space-y-1 rounded-md border border-slate-200 bg-muted/30 p-3 text-xs tabular-nums">
                <li>
                  Cédula: <span className="font-medium">{data.cedula}</span>
                </li>
                <li>
                  Préstamo: <span className="font-medium">#{data.prestamo_id}</span>
                </li>
                <li>
                  Fecha Q:{' '}
                  <span className="font-medium">{fmtFechaNotifIso(data.fecha_entrega_column_q)}</span>
                </li>
                <li>
                  Fecha aprobación (BD):{' '}
                  <span className="font-medium">
                    {fmtFechaNotifIso(data.fecha_aprobacion_sistema)}
                  </span>
                </li>
                <li>
                  Diferencia (días):{' '}
                  <span className="font-semibold">{fmtDiferenciaDiasNotif(data.diferencia_dias)}</span>
                </li>
              </ul>
              <p className="text-xs text-muted-foreground">
                Pulse «Confirmar y guardar» solo si la fecha Q es la fuente de verdad que desea en el
                sistema.
              </p>
            </div>
          ) : data ? (
            <div className="space-y-3 text-sm">
              <p className="text-muted-foreground">
                Cédula <span className="font-medium text-foreground">{data.cedula}</span>
                {' · '}
                Préstamo <span className="font-medium text-foreground">#{data.prestamo_id}</span>
              </p>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                <Link
                  to={`/revision-manual/editar/${pid}`}
                  state={{
                    returnTo: `${location.pathname}${location.search || ''}`,
                  }}
                  className="font-medium text-blue-600 hover:underline"
                >
                  Abrir en revisión manual
                </Link>
                <span className="text-muted-foreground">
                  (edición del préstamo y cuotas en otra pantalla)
                </span>
              </div>

              {data.hoja_sync_antigua ? (
                <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                  La hoja supera las 48 h desde la última sincronización (aprox.{' '}
                  {data.hoja_sync_antigua_horas != null
                    ? `${data.hoja_sync_antigua_horas} h`
                    : '-'}
                  ). Resincronice CONCILIACIÓN si necesita la columna Q (fechas) al día.
                </p>
              ) : null}

              {data.prestamo_huella ? (
                <div className="rounded-md border bg-slate-50 p-3 text-xs text-slate-900">
                  <p className="mb-1 font-semibold text-slate-800">
                    Huella del préstamo en BD (alinear con fila de la hoja)
                  </p>
                  <ul className="list-none space-y-0.5 tabular-nums">
                    <li>
                      Total financiamiento:{' '}
                      {data.prestamo_huella.total_financiamiento.toLocaleString('es-VE', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </li>
                    <li>N.º cuotas: {data.prestamo_huella.numero_cuotas}</li>
                    <li>Modalidad: {data.prestamo_huella.modalidad_pago || '-'}</li>
                  </ul>
                </div>
              ) : null}

              {!puedeOperar ? (
                <p className="rounded-md border border-slate-200 bg-muted/40 p-2 text-xs text-slate-800">
                  <span className="font-medium">Regla: </span>
                  el indicador «Sí» solo aplica si la fecha de la columna Q es{' '}
                  <strong>estrictamente posterior</strong> a la fecha de aprobación del préstamo en el
                  sistema. Si la fecha Q es igual o anterior, el flujo queda en «No»: use revisión
                  manual o la conciliación habitual.
                </p>
              ) : null}

              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground text-xs">Indicador:</span>
                <button
                  type="button"
                  disabled={!puedeOperar || !esAdmin || loading}
                  title={
                    !esAdmin
                      ? 'Solo administradores pueden abrir el paso de confirmación.'
                      : data?.requiere_seleccion_lote && !loteResuelto
                        ? 'Elija primero el lote de la hoja que corresponde a este préstamo.'
                        : puedeOperar
                          ? 'Pulse Sí para confirmar en el siguiente paso el guardado en BD (fecha Q → fecha de aprobación).'
                          : 'La fecha Q no es posterior a la aprobación: no hay indicador Sí.'
                  }
                  onClick={() => {
                    if (!puedeOperar || !esAdmin || loading) return
                    setPaso('confirmar')
                  }}
                  className={`${pillBase} ${
                    puedeOperar
                      ? 'border-green-600 bg-green-50 text-green-800 hover:bg-green-100 disabled:opacity-50'
                      : 'cursor-not-allowed border-muted bg-muted/40 text-muted-foreground'
                  }`}
                  aria-label={
                    puedeOperar
                      ? 'Sí: fecha Q posterior a fecha de aprobación; siguiente paso para guardar en BD'
                      : 'Sí: no aplica'
                  }
                >
                  Sí
                </button>
                <button
                  type="button"
                  className={`${pillBase} ${
                    !puedeOperar
                      ? 'border-slate-600 bg-slate-100 text-slate-800 hover:bg-slate-200/80'
                      : 'border-muted bg-muted/30 text-muted-foreground hover:bg-muted/50'
                  }`}
                  title="Cierra el cuadro sin aplicar nada; permanece en esta misma pantalla de notificaciones."
                  aria-label="No: cerrar el cuadro sin cambiar de submenú"
                  onClick={() => onDialogFechaOpenChange(false)}
                >
                  No
                </button>
              </div>

              {data.requiere_seleccion_lote &&
              data.opciones_lote &&
              data.opciones_lote.length > 0 ? (
                <div className="rounded-md border border-amber-200 bg-amber-50/90 p-3 text-xs text-amber-950">
                  <p className="mb-2 font-medium">
                    Hay varios lotes en la hoja para esta cédula. Elija el que corresponde a este
                    préstamo (solo se usará la fila de esa combinación cédula + lote).
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {data.opciones_lote.map(op => (
                      <Button
                        key={op.lote}
                        type="button"
                        size="sm"
                        variant="outline"
                        className="border-amber-300 bg-white text-amber-950 hover:bg-amber-100"
                        disabled={loading}
                        onClick={() => {
                          void abrir(op.lote)
                        }}
                      >
                        Lote {op.lote}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}

              {data.lote_aplicado && loteResuelto ? (
                <p className="rounded-md border border-sky-200 bg-sky-50/90 p-2 text-xs text-sky-950">
                  <span className="font-semibold">Resumen: </span>
                  Lote <span className="font-mono">{data.lote_aplicado}</span>
                  {' · '}
                  Columna {colQEtiqueta}
                  {' · '}
                  Préstamo #{data.prestamo_id}
                </p>
              ) : data.lote_aplicado ? (
                <p className="text-xs text-muted-foreground">
                  Lote usado para esta comparación:{' '}
                  <span className="font-mono font-medium text-foreground">{data.lote_aplicado}</span>
                </p>
              ) : null}

              <dl className="grid grid-cols-1 gap-2 rounded-md border bg-muted/30 p-3">
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Fecha entrega (columna Q)</dt>
                  <dd className="font-medium tabular-nums">
                    {fmtFechaNotifIso(data.fecha_entrega_column_q)}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Fecha aprobación (sistema)</dt>
                  <dd className="font-medium tabular-nums">
                    {fmtFechaNotifIso(data.fecha_aprobacion_sistema)}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-muted-foreground">Diferencia (Q − aprobación, días)</dt>
                  <dd
                    className={`font-semibold tabular-nums ${
                      data.coincide_aproximado ? 'text-green-700' : 'text-amber-800'
                    }`}
                  >
                    {fmtDiferenciaDiasNotif(data.diferencia_dias)}
                  </dd>
                </div>
              </dl>
              <p className="text-xs text-muted-foreground">
                Filas de la hoja que corresponden a este préstamo:{' '}
                <span className="font-medium text-foreground">{data.filas_hoja_coincidentes}</span>
                {data.filas_misma_cedula_hoja != null ? (
                  <>
                    {' '}
                    · Filas con la misma cédula en la hoja (todas):{' '}
                    <span className="font-medium text-foreground">{data.filas_misma_cedula_hoja}</span>
                  </>
                ) : null}
                {data.hoja_synced_at ? (
                  <>
                    {' '}
                    · Última sync hoja:{' '}
                    <span className="font-medium text-foreground">
                      {new Date(data.hoja_synced_at).toLocaleString('es-VE', {
                        timeZone: 'America/Caracas',
                      })}
                    </span>
                  </>
                ) : null}
              </p>
              {data.columna_cedula_detectada || data.columna_q_letra || data.columna_lote_detectada ? (
                <p className="text-xs text-muted-foreground">
                  Columnas detectadas:{' '}
                  <span className="font-mono text-foreground">
                    {data.columna_cedula_detectada ?? '-'}
                  </span>
                  {' · '}
                  <span className="font-mono text-foreground">{colQEtiqueta}</span>
                  {data.columna_lote_detectada ? (
                    <>
                      {' · '}
                      <span className="font-mono text-foreground">{data.columna_lote_detectada}</span>
                    </>
                  ) : null}
                  {data.rango_columnas_hoja ? (
                    <>
                      {' '}
                      <span className="text-muted-foreground">
                        (rango hoja {data.rango_columnas_hoja}
                        {data.columna_q_dentro_rango === false ? '; Q fuera de rango' : ''})
                      </span>
                    </>
                  ) : null}
                </p>
              ) : null}
              {data.advertencias?.length ? (
                <ul className="list-disc space-y-1 pl-4 text-xs text-amber-900">
                  {data.advertencias.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              ) : null}
              {data.coincide_aproximado ? (
                <p className="text-xs font-medium text-green-700">
                  Coinciden (misma fecha en calendario; tolerancia ±{data.tolerancia_dias ?? 0}{' '}
                  día(s)).
                </p>
              ) : data.diferencia_dias != null ? (
                <p className="text-xs text-amber-900">
                  Hay diferencia de días entre la hoja y la fecha de aprobación en BD. Revise la sync
                  de la hoja o el registro del préstamo.
                </p>
              ) : null}
              {!esAdmin && puedeOperar ? (
                <p className="text-xs text-muted-foreground">
                  El indicador «Sí» y el guardado en BD requieren administrador.
                </p>
              ) : null}
            </div>
          ) : null}

          <DialogFooter className="gap-2 sm:gap-0">
            {paso === 'confirmar' ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  disabled={applying}
                  onClick={() => {
                    setPaso('resumen')
                  }}
                >
                  Volver
                </Button>
                <Button
                  type="button"
                  disabled={applying || !esAdmin}
                  onClick={() => {
                    void aplicarFechaQComoAprobacion()
                  }}
                >
                  {applying ? 'Guardando…' : 'Confirmar y guardar'}
                </Button>
              </>
            ) : (
              <Button type="button" variant="outline" onClick={() => onDialogFechaOpenChange(false)}>
                Cerrar
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
