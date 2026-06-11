import { useCallback, useEffect, useRef, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  CreditCard,
  Download,
  Edit2,
  Loader2,
  RefreshCw,
  Save,
  Trash2,
} from 'lucide-react'

import {
  DriveScanCoveragePanel,
  invalidateDriveScanCoverage,
} from '../components/drive/DriveScanCoveragePanel'
import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  getPrestamosCandidatosDriveSnapshot,
  postPrestamosCandidatosDriveActualizarFechaQ,
  postPrestamosCandidatosDriveEliminarSeleccionados,
  postPrestamosCandidatosDriveGuardarFila,
  postPrestamosCandidatosDriveGuardarValidados100,
  postPrestamosCandidatosDriveRefrescar,
  type PrestamoCandidatoDriveFila,
} from '../services/prestamosCandidatosDriveService'
import { reporteService } from '../services/reporteService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

const QK_BASE = ['actualizaciones', 'prestamos-drive', 'snapshot'] as const

/** Filas por página (offset en API = (página − 1) × PAGE_SIZE). */
const PAGE_SIZE = 100
/** Botones numéricos visibles a la vez (ventana deslizante). */
const PAGE_WINDOW = 5
/**
 * Antigüedad máxima permitida para fecha de aprobación (Q) al crear préstamo
 * desde Drive. Debe coincidir con `MAX_DIAS_APROBACION_DRIVE` del backend
 * (`prestamo_candidatos_drive_guardar.py`). Si supera este límite, la fila se
 * marca en rojo y no se permite guardar por este flujo (alta manual aparte).
 */
const MAX_DIAS_APROBACION_DRIVE = 365

/** Ventana de números de página centrada hacia `current`, acotada a `totalPages`. */
function numerosPaginaVisibles(
  current: number,
  totalPages: number,
  maxButtons: number
): number[] {
  if (totalPages <= maxButtons) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }
  const half = Math.floor(maxButtons / 2)
  let start = current - half
  let end = start + maxButtons - 1
  if (start < 1) {
    start = 1
    end = maxButtons
  }
  if (end > totalPages) {
    end = totalPages
    start = Math.max(1, end - maxButtons + 1)
  }
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

function strPayload(
  p: PrestamoCandidatoDriveFila['payload'],
  key: string
): string {
  const v = p[key]
  if (v == null) return '-'
  return String(v)
}

function escapeCsvCell(s: string): string {
  const t = String(s ?? '').replace(/"/g, '""')
  if (/[",\n\r]/.test(t)) return `"${t}"`
  return t
}

/** Cédula normalizada tipo V o E (regla innegociable: máximo un préstamo en cartera). */
function cedulaEsTipoVeFromPayload(
  p: PrestamoCandidatoDriveFila['payload']
): boolean {
  if (p.cedula_es_tipo_ve === true) return true
  const u = String(p.cedula_cmp ?? '')
    .trim()
    .toUpperCase()
  if (u.length > 0 && (u[0] === 'V' || u[0] === 'E')) return true
  return p.cedula_es_tipo_v_venezolano === true || p.cedula_es_tipo_e === true
}

/** Cédula tipo J (jurídico): pueden existir 2 o más préstamos; no aplica el tope V/E en columna 2. */
function cedulaEsTipoJFromPayload(
  p: PrestamoCandidatoDriveFila['payload']
): boolean {
  if (p.cedula_es_tipo_j === true) return true
  const u = String(p.cedula_cmp ?? '')
    .trim()
    .toUpperCase()
  return u.length > 0 && u[0] === 'J'
}

/** 1 formato cédula · 2 regla V/E vs tabla préstamos (J exento) · 3 sin duplicado en hoja */
function validadoresTresFlags(p: PrestamoCandidatoDriveFila['payload']) {
  const formatoOk = (p.validador_formato_cedula_ok ?? p.cedula_valida) === true
  const hojaOk =
    (p.validador_sin_duplicado_en_hoja_ok ?? p.duplicada_en_hoja !== true) ===
    true
  const nPrest = Number(p.prestamos_misma_cedula_norm_count ?? 0)
  const nAprob = Number(
    p.prestamos_aprobados_misma_cedula_norm_count ?? nPrest ?? 0
  )
  const esV = p.cedula_es_tipo_v_venezolano === true
  const esVe = cedulaEsTipoVeFromPayload(p)
  const esJ = cedulaEsTipoJFromPayload(p)
  const tablaVOk = esJ
    ? true
    : (p.validador_ve_max_un_prestamo_ok ??
        p.validador_v_max_un_prestamo_ok ??
        !(esVe && nAprob >= 1)) === true
  return { formatoOk, tablaVOk, hojaOk, nPrest, nAprob, esV, esVe, esJ }
}

/** Parseo ligero alineado a columna Q (DD/MM/YYYY, YYYY-MM-DD o serial Sheets/Excel). */
function parseFechaFlexible(s: string): Date | null {
  const raw = (s || '').trim()
  if (!raw) return null
  // Serial Sheets/Excel (base 1899-12-30). Mismo rango que backend: 20000..80000.
  const serialMatch = raw.match(/^(\d+)(?:[.,]\d+)?$/)
  if (serialMatch) {
    const serial = Number(serialMatch[1])
    if (Number.isFinite(serial) && serial >= 20000 && serial <= 80000) {
      const base = Date.UTC(1899, 11, 30)
      const ms = base + serial * 86400000
      const d = new Date(ms)
      if (!Number.isNaN(d.getTime())) {
        return new Date(
          d.getUTCFullYear(),
          d.getUTCMonth(),
          d.getUTCDate(),
          12,
          0,
          0
        )
      }
    }
  }
  const ymdSlash = raw.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/)
  if (ymdSlash) {
    const year = Number(ymdSlash[1])
    const month = Number(ymdSlash[2])
    const day = Number(ymdSlash[3])
    const d = new Date(year, month - 1, day, 12, 0, 0)
    if (
      d.getFullYear() === year &&
      d.getMonth() === month - 1 &&
      d.getDate() === day
    ) {
      return d
    }
    return null
  }
  if (/^\d{4}-\d{2}-\d{2}(?:[T\s].*)?$/.test(raw)) {
    const d = new Date(`${raw.slice(0, 10)}T12:00:00`)
    return Number.isNaN(d.getTime()) ? null : d
  }
  const m = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/)
  if (m) {
    const day = Number(m[1])
    const month = Number(m[2])
    const year = Number(m[3])
    // Evita invertir día/mes por interpretación humana ambigua.
    if (day >= 1 && day <= 12 && month >= 1 && month <= 12) return null
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
      const d = new Date(year, month - 1, day, 12, 0, 0)
      if (
        d.getFullYear() === year &&
        d.getMonth() === month - 1 &&
        d.getDate() === day
      )
        return d
    }
  }
  return null
}

/**
 * Fecha de aprobación normalizada: usa `col_q_fecha_iso` provisto por el backend
 * (que ya admite seriales de Google Sheets / Excel) y cae al texto crudo solo
 * si no viene la versión normalizada.
 */
function fechaAprobacionNormalizada(
  p: PrestamoCandidatoDriveFila['payload']
): Date | null {
  const iso = String(p.col_q_fecha_iso ?? '').trim()
  if (iso) {
    const d = parseFechaFlexible(iso)
    if (d) return d
  }
  return fechaAprobacionDesdeColQ(String(p.col_q_fecha ?? ''))
}

/** ISO `YYYY-MM-DD` mostrable; usa el normalizado del backend si está presente. */
function colQFechaIsoDisplay(p: PrestamoCandidatoDriveFila['payload']): string {
  const iso = String(p.col_q_fecha_iso ?? '').trim()
  if (iso) return iso.slice(0, 10)
  const d = fechaAprobacionDesdeColQ(String(p.col_q_fecha ?? ''))
  if (!d) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Valor para `<input type="date">` (YYYY-MM-DD). */
function fechaQInputValue(p: PrestamoCandidatoDriveFila['payload']): string {
  return colQFechaIsoDisplay(p)
}

/** Segunda parte de Q = aprobación si hay separador; si no, una sola fecha cuenta para ambas. */
function fechaAprobacionDesdeColQ(qVal: string): Date | null {
  const raw = (qVal || '').trim()
  if (!raw) return null
  for (const sep of ['|', ';', '\n']) {
    if (raw.includes(sep)) {
      const i = raw.indexOf(sep)
      const a = raw.slice(0, i).trim()
      const b = raw.slice(i + sep.length).trim()
      if (a && b) {
        const d2 = parseFechaFlexible(b)
        if (d2) return d2
      }
      break
    }
  }
  const multiSpace = /\s{2,}/
  if (multiSpace.test(raw)) {
    const parts = raw
      .split(multiSpace)
      .map(x => x.trim())
      .filter(Boolean)
    if (parts.length >= 2) {
      const d2 = parseFechaFlexible(parts[1])
      if (d2) return d2
    }
  }
  return parseFechaFlexible(raw)
}

/**
 * Fecha de aprobación (Q) más antigua que la ventana permitida (zona local).
 * Coincide con la regla de servidor: > `MAX_DIAS_APROBACION_DRIVE` días.
 */
function aprobacionFueraVentanaFromPayload(
  p: PrestamoCandidatoDriveFila['payload']
): boolean {
  const ap = fechaAprobacionNormalizada(p)
  if (!ap) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const ap0 = new Date(ap)
  ap0.setHours(0, 0, 0, 0)
  const diffDays = Math.floor((today.getTime() - ap0.getTime()) / 86400000)
  return diffDays > MAX_DIAS_APROBACION_DRIVE
}

/** Solo determina ambigüedad textual DD/MM cuando el backend no nos entregó la bandera. */
function qTieneFechaAmbiguaFromPayload(
  p: PrestamoCandidatoDriveFila['payload']
): boolean {
  if (p.col_q_fecha_ambigua === true) return true
  if (p.col_q_fecha_ambigua === false) return false
  const raw = String(p.col_q_fecha ?? '').trim()
  if (!raw) return false
  // Si ya hay ISO normalizado, el dato dejó de ser ambiguo para la UI.
  if (String(p.col_q_fecha_iso ?? '').trim()) return false
  const tokens = raw
    .split(/[|;\n]|\s{2,}/)
    .map(x => x.trim())
    .filter(Boolean)
  const list = tokens.length > 0 ? tokens : [raw]
  return list.some(t => {
    const m = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
    if (!m) return false
    const d = Number(m[1])
    const mo = Number(m[2])
    return d >= 1 && d <= 12 && mo >= 1 && mo <= 12
  })
}

type FilaCandidatoDriveTono = 'red' | 'amber' | 'green' | 'plain'

/** Tono de fila en tabla: incluye `partial` = ✓✓✓ en pantalla pero aún no guardable en servidor. */
type FilaTablaTono = FilaCandidatoDriveTono | 'partial'

/** Fondo de fila: rojo (prioridad), ámbar, verde pantalla, o neutro (solo reglas 1·2·3 + Q en UI). */
function filaCandidatoDriveTono(
  p: PrestamoCandidatoDriveFila['payload']
): FilaCandidatoDriveTono {
  const { formatoOk, tablaVOk, hojaOk, nAprob, esVe, esJ } =
    validadoresTresFlags(p)
  const dup = p.duplicada_en_hoja === true

  const redInvalida = !formatoOk
  const redVeCupoAprobado = !esJ && esVe && Number.isFinite(nAprob) && nAprob >= 1
  const redFechaAntigua = aprobacionFueraVentanaFromPayload(p)
  const redHuellaNoComparable = p.huella_no_comparable === true

  if (
    redInvalida ||
    redVeCupoAprobado ||
    redFechaAntigua ||
    redHuellaNoComparable
  )
    return 'red'
  if (formatoOk && dup) return 'amber'
  if (formatoOk && tablaVOk && hojaOk) return 'green'
  return 'plain'
}

/** Solo filas que el servidor marcará como guardables (misma regla que «Guardar (100%)»). */
function filaCumpleCienParaGuardar(fila: PrestamoCandidatoDriveFila): boolean {
  if (typeof fila.listo_para_guardar === 'boolean') {
    return fila.listo_para_guardar
  }
  return filaCandidatoDriveTono(fila.payload) === 'green'
}

/** Verde intenso solo si el servidor marca guardable; si solo pasan 1·2·3 en pantalla → `partial` (azul). */
function filaTonoTabla(fila: PrestamoCandidatoDriveFila): FilaTablaTono {
  const base = filaCandidatoDriveTono(fila.payload)
  if (fila.listo_para_guardar === true) {
    return 'green'
  }
  if (fila.listo_para_guardar === false && base === 'green') {
    return 'partial'
  }
  return base
}

const FILA_TONE_TR: Record<FilaTablaTono, string> = {
  red: 'bg-red-50/95 hover:bg-red-50/90 border-b border-red-100',
  amber: 'bg-amber-50/95 hover:bg-amber-50/90 border-b border-amber-100',
  green: 'bg-emerald-50/95 hover:bg-emerald-50/90 border-b border-emerald-100',
  partial: 'bg-sky-50/95 hover:bg-sky-50/90 border-b border-sky-100',
  plain: 'border-b border-border bg-background hover:bg-muted/25',
}

/** Fondos opacos en la celda sticky para que no se transparente el texto de la columna anterior al hacer scroll. */
const FILA_TONE_STICKY_TD: Record<FilaTablaTono, string> = {
  red: 'bg-red-50',
  amber: 'bg-amber-50',
  green: 'bg-emerald-50',
  partial: 'bg-sky-50',
  plain: 'bg-background',
}

function exportarCsvVistaActual(filas: PrestamoCandidatoDriveFila[]) {
  const headers = [
    'fila',
    'cedula_e',
    'prestamos_misma_cedula_n',
    'es_tipo_ve',
    'es_tipo_j',
    'val_formato',
    'val_tabla_ve',
    'val_hoja',
    'total_n',
    'modalidad_s',
    'fecha_q',
    'fecha_q_hoja',
    'cuotas_r',
    'analista_j',
    'concesionario_k',
    'modelo_i',
    'estado',
  ]
  const lines = [headers.join(',')]
  for (const r of filas) {
    const p = r.payload
    const { formatoOk, tablaVOk, hojaOk, nPrest, esVe, esJ } =
      validadoresTresFlags(p)
    const ok = p.cedula_valida === true
    const dup = p.duplicada_en_hoja === true
    let estado = 'revisión'
    if (!ok) estado = `inválida: ${String(p.cedula_error ?? '')}`
    else if (dup) estado = 'repetida_hoja'
    else if (!tablaVOk) estado = 'tipo_VE: más de un préstamo o no cumple tabla'
    else estado = 'listo'
    const fechaQNorm = colQFechaIsoDisplay(p) || strPayload(p, 'col_q_fecha')
    lines.push(
      [
        r.sheet_row_number,
        strPayload(p, 'col_e_cedula'),
        String(nPrest),
        esVe ? 'si' : 'no',
        esJ ? 'si' : 'no',
        formatoOk ? 'ok' : 'no',
        tablaVOk ? 'ok' : 'no',
        hojaOk ? 'ok' : 'no',
        strPayload(p, 'col_n_total_financiamiento'),
        strPayload(p, 'col_s_modalidad_pago'),
        fechaQNorm,
        strPayload(p, 'col_q_fecha'),
        strPayload(p, 'col_r_numero_cuotas'),
        strPayload(p, 'col_j_analista'),
        strPayload(p, 'col_k_concesionario'),
        strPayload(p, 'col_i_modelo_vehiculo'),
        estado,
      ]
        .map(v => escapeCsvCell(String(v)))
        .join(',')
    )
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `candidatos-prestamos-drive-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/** Iconos de acción por fila (revisión tipo grilla). */
function AccionesPorFilaCandidatoDrive({
  fila,
  disabled,
  puedeGuardarFila,
  guardandoEstaFila,
  eliminandoEstaFila,
  onGuardarFila,
  onEliminarFila,
  onEditarFecha,
}: {
  fila: PrestamoCandidatoDriveFila
  disabled: boolean
  puedeGuardarFila: boolean
  guardandoEstaFila: boolean
  eliminandoEstaFila: boolean
  onGuardarFila: (sheetRowNumber: number) => void
  onEliminarFila: (filaId: number, sheetRowNumber: number) => void
  onEditarFecha: (filaId: number) => void
}) {
  const iconBtn =
    'h-8 w-8 shrink-0 rounded-md border border-slate-200 bg-white p-0 shadow-sm hover:bg-slate-50 disabled:opacity-50'
  const sr = fila.sheet_row_number
  // Botón siempre clicable salvo carga global o guardado en curso; la validación corre al pulsar (onGuardarFila).
  const saveDisabled = disabled || guardandoEstaFila
  const saveTitle = guardandoEstaFila
    ? `Guardando fila de hoja ${sr}…`
    : puedeGuardarFila
      ? `Guardar solo esta fila (misma validación de servidor que «Guardar válidas»).`
      : `Guardar fila ${sr}: al pulsar se aplican los mismos validadores de servidor; si no cumple, verá el motivo en un mensaje.`
  const deleteDisabled = disabled || eliminandoEstaFila

  return (
    <div className="flex min-w-0 flex-nowrap items-center justify-center gap-0.5 sm:gap-1">
      <Button
        type="button"
        variant="outline"
        size="icon"
        className={iconBtn}
        title={`Editar fecha (Q) de la fila ${sr} en pantalla (también actualiza el snapshot local y la tabla drive).`}
        aria-label={`Editar fecha fila ${sr}`}
        disabled={disabled}
        onClick={() => onEditarFecha(fila.id)}
      >
        <Edit2
          className="h-3.5 w-3.5 text-foreground"
          strokeWidth={2}
          aria-hidden
        />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className={iconBtn}
        title={saveTitle}
        aria-label={`Guardar fila ${sr}`}
        disabled={saveDisabled}
        onClick={() => onGuardarFila(sr)}
      >
        <Save
          className={`h-3.5 w-3.5 text-foreground ${guardandoEstaFila ? 'animate-pulse' : ''}`}
          strokeWidth={2}
          aria-hidden
        />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className={iconBtn}
        title={
          eliminandoEstaFila
            ? `Quitando candidato fila ${sr}…`
            : `Quitar este candidato del snapshot (no toca la hoja Drive ni crea préstamo). Volverá a aparecer en el siguiente recálculo si sigue en la hoja.`
        }
        aria-label={`Borrar fila ${sr}`}
        disabled={deleteDisabled}
        onClick={() => onEliminarFila(fila.id, sr)}
      >
        <Trash2
          className={`h-3.5 w-3.5 text-red-600 ${eliminandoEstaFila ? 'animate-pulse' : ''}`}
          strokeWidth={2}
          aria-hidden
        />
      </Button>
    </div>
  )
}

function TableSkeletonRows({ n = 6 }: { n?: number }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <tr key={i} className="border-t">
          {Array.from({ length: 12 }).map((__, j) => (
            <td key={j} className="px-2 py-2 align-middle">
              <div className="h-4 animate-pulse rounded bg-muted" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

export default function ActualizacionesPrestamosDrivePage() {
  const qc = useQueryClient()
  const [cedulaInput, setCedulaInput] = useState('')
  const [cedulaDebounced, setCedulaDebounced] = useState('')
  const [forzarVacio, setForzarVacio] = useState(false)
  const [soloHuellaNoComparable, setSoloHuellaNoComparable] = useState(false)
  const [manualUpdating, setManualUpdating] = useState(false)
  const [guardarValidosSaving, setGuardarValidosSaving] = useState(false)
  const [eliminandoSeleccionados, setEliminandoSeleccionados] = useState(false)
  const [guardandoFilaSheet, setGuardandoFilaSheet] = useState<number | null>(
    null
  )
  const [eliminandoFilaId, setEliminandoFilaId] = useState<number | null>(null)
  const [actualizandoFechaId, setActualizandoFechaId] = useState<number | null>(
    null
  )
  const fechaQInputRefs = useRef<Record<number, HTMLInputElement | null>>({})
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaDebounced(cedulaInput.trim()),
      400
    )
    return () => window.clearTimeout(t)
  }, [cedulaInput])

  useEffect(() => {
    setPage(1)
  }, [cedulaDebounced, soloHuellaNoComparable])

  const snapshotQuery = useQuery({
    queryKey: [...QK_BASE, cedulaDebounced, soloHuellaNoComparable, page],
    queryFn: () =>
      getPrestamosCandidatosDriveSnapshot(
        PAGE_SIZE,
        (page - 1) * PAGE_SIZE,
        cedulaDebounced || undefined,
        soloHuellaNoComparable
      ),
  })

  const data = snapshotQuery.data
  const rows = data?.filas ?? []
  const total = data?.total ?? 0
  const guardables =
    typeof data?.kpis_aprueban === 'number' ? data.kpis_aprueban : null
  const totalSinFiltro = data?.total_sin_filtro
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const pageNumbers = numerosPaginaVisibles(page, totalPages, PAGE_WINDOW)

  useEffect(() => {
    if (page > totalPages) setPage(totalPages)
  }, [page, totalPages])

  useEffect(() => {
    setSelectedIds(prev => {
      if (prev.size === 0) return prev
      const currentIds = new Set(rows.map(r => r.id))
      const next = new Set(Array.from(prev).filter(id => currentIds.has(id)))
      return next.size === prev.size ? prev : next
    })
  }, [rows])

  const refetchLista = snapshotQuery.refetch

  const refrescarSnapshotPostAccion = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: [...QK_BASE], exact: false })
    await refetchLista()
  }, [qc, refetchLista])

  const onRecalcular = useCallback(async () => {
    setManualUpdating(true)
    try {
      const syncRes = await reporteService.syncConciliacionSheetDesdeDrive()
      const res = await postPrestamosCandidatosDriveRefrescar({
        forzar: forzarVacio,
      })
      const n = syncRes?.row_count
      const ultima =
        typeof syncRes?.last_data_sheet_row_number === 'number'
          ? syncRes.last_data_sheet_row_number
          : null
      const filasSync = typeof n === 'number' ? `${n} fila(s) importadas. ` : ''
      const cola = ultima != null ? `Última fila hoja (A:S): ${ultima}. ` : ''
      if (res?.omitido === true) {
        toast.message(
          `${filasSync}${cola}${
            (res.motivo as string) === 'tabla_drive_sin_filas'
              ? 'No se recalculó el snapshot: la tabla drive quedó vacía (se mantiene el anterior). Marque «Forzar…» para vaciarlo.'
              : 'Recálculo del snapshot omitido.'
          }`
        )
      } else {
        const motivo = res?.motivo as string | undefined
        if (motivo === 'forzar_con_drive_vacio') {
          toast.success(
            `${filasSync}${cola}Snapshot vaciado (drive sin filas, recálculo forzado).`
          )
        } else {
          toast.success(
            `${filasSync}${cola}Snapshot actualizado: ${Number(res.candidatos_insertados ?? 0)} candidato(s).`
          )
        }
      }
      await invalidateDriveScanCoverage(qc)
      await refrescarSnapshotPostAccion()
    } catch (e) {
      toast.error(
        getErrorMessage(e) || 'No se pudo sincronizar la hoja desde Google'
      )
    } finally {
      setManualUpdating(false)
    }
  }, [forzarVacio, qc, refrescarSnapshotPostAccion])

  const onGuardarUnaFila = useCallback(
    async (sheetRowNumber: number) => {
      const fila = rows.find(r => r.sheet_row_number === sheetRowNumber)
      if (!fila) {
        toast.error(`No se encontró la fila ${sheetRowNumber} en esta página.`)
        return
      }
      setGuardandoFilaSheet(sheetRowNumber)
      try {
        const res =
          await postPrestamosCandidatosDriveGuardarFila(sheetRowNumber)
        if (!res.ok) {
          const m =
            (res.motivos && res.motivos.length > 0
              ? res.motivos.join(' · ')
              : null) || res.mensaje
          toast.error(m || 'No se pudo guardar la fila.')
          return
        }
        toast.success(res.mensaje || `Fila ${sheetRowNumber} guardada.`)
        await refrescarSnapshotPostAccion()
      } catch (e) {
        toast.error(getErrorMessage(e) || 'No se pudo guardar la fila')
      } finally {
        setGuardandoFilaSheet(null)
      }
    },
    [refrescarSnapshotPostAccion, rows]
  )

  const onGuardarValidos100 = useCallback(async () => {
    if ((guardables ?? 0) <= 0) {
      toast.message(
        'No hay préstamos guardables en este momento. Solo se guardan filas que cumplen validadores de servidor.'
      )
      return
    }
    setGuardarValidosSaving(true)
    try {
      const res = await postPrestamosCandidatosDriveGuardarValidados100()
      const ins = Number(res.insertados_ok ?? 0)
      const om = Number(res.omitidos_no_100 ?? 0)
      const err = Number(res.errores_al_guardar ?? 0)
      const msg =
        res.mensaje ||
        `Creados: ${ins}. Omitidos: ${om}. Errores: ${err}. Las no guardadas siguen en el snapshot para revisión.`
      if (err > 0) {
        toast.warning(msg)
      } else if (ins > 0) {
        toast.success(msg)
      } else {
        toast.message(
          msg ||
            'Ninguna fila cumplió la validación; no se guardó nada. Todas siguen en la lista para revisarlas y corregir.'
        )
      }
      await refrescarSnapshotPostAccion()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar')
    } finally {
      setGuardarValidosSaving(false)
    }
  }, [guardables, refrescarSnapshotPostAccion])

  const onRefrescarLista = useCallback(async () => {
    try {
      await refetchLista()
      toast.message('Lista actualizada desde el servidor.')
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo refrescar la lista')
    }
  }, [refetchLista])

  const onEliminarUnaFila = useCallback(
    async (filaId: number, sheetRowNumber: number) => {
      if (!Number.isFinite(filaId) || filaId <= 0) {
        toast.error('Fila inválida; no se puede eliminar.')
        return
      }
      const confirmado = window.confirm(
        `Va a quitar el candidato de la fila ${sheetRowNumber} del snapshot. No se crea préstamo ni se modifica la hoja Drive; si la fila sigue en Drive volverá a aparecer en el próximo recálculo. ¿Continuar?`
      )
      if (!confirmado) return
      setEliminandoFilaId(filaId)
      try {
        const res = await postPrestamosCandidatosDriveEliminarSeleccionados([
          filaId,
        ])
        toast.success(
          res?.mensaje ||
            `Candidato de la fila ${sheetRowNumber} quitado del snapshot.`
        )
        setSelectedIds(prev => {
          if (!prev.has(filaId)) return prev
          const next = new Set(prev)
          next.delete(filaId)
          return next
        })
        await refrescarSnapshotPostAccion()
      } catch (e) {
        toast.error(
          getErrorMessage(e) || 'No se pudo quitar el candidato de la fila'
        )
      } finally {
        setEliminandoFilaId(null)
      }
    },
    [refrescarSnapshotPostAccion]
  )

  const onActualizarFechaQ = useCallback(
    async (filaId: number, fechaQ: string, sheetRowNumber: number) => {
      const valor = fechaQ.trim()
      if (!/^\d{4}-\d{2}-\d{2}$/.test(valor)) {
        toast.error('Use una fecha válida (YYYY-MM-DD).')
        return
      }
      setActualizandoFechaId(filaId)
      try {
        const res = await postPrestamosCandidatosDriveActualizarFechaQ(
          filaId,
          valor
        )
        toast.success(
          res.mensaje ||
            `Fecha (Q) actualizada en fila ${sheetRowNumber}.`
        )
        await refrescarSnapshotPostAccion()
      } catch (e) {
        toast.error(getErrorMessage(e) || 'No se pudo actualizar la fecha (Q)')
      } finally {
        setActualizandoFechaId(null)
      }
    },
    [refrescarSnapshotPostAccion]
  )

  const enfocarFechaQFila = useCallback((filaId: number) => {
    const el = fechaQInputRefs.current[filaId]
    if (!el) {
      toast.message('Use el campo Fecha (Q) en la fila para corregir la fecha.')
      return
    }
    el.focus()
    try {
      el.showPicker?.()
    } catch {
      /* showPicker no disponible en todos los navegadores */
    }
  }, [])

  const onEliminarSeleccionados = useCallback(async () => {
    const ids = Array.from(selectedIds)
    if (ids.length === 0) {
      toast.message('Seleccione al menos una fila para eliminar.')
      return
    }
    const confirmado = window.confirm(
      `Va a eliminar ${ids.length} fila(s) seleccionada(s) del snapshot. Esta acción no crea préstamos ni se puede deshacer. ¿Desea continuar?`
    )
    if (!confirmado) return
    setEliminandoSeleccionados(true)
    try {
      const res = await postPrestamosCandidatosDriveEliminarSeleccionados(ids)
      toast.success(
        res?.mensaje ||
          `Se eliminaron ${res?.eliminados ?? 0} fila(s) seleccionadas del snapshot.`
      )
      setSelectedIds(new Set())
      await refrescarSnapshotPostAccion()
    } catch (e) {
      toast.error(
        getErrorMessage(e) || 'No se pudieron eliminar las filas seleccionadas'
      )
    } finally {
      setEliminandoSeleccionados(false)
    }
  }, [refrescarSnapshotPostAccion, selectedIds])

  const fmtCaracas = useCallback((iso: string | null | undefined) => {
    if (!iso) return '-'
    try {
      return new Date(iso).toLocaleString('es-VE', {
        timeZone: 'America/Caracas',
      })
    } catch {
      return iso
    }
  }, [])

  const estadoFila = useCallback((fila: PrestamoCandidatoDriveFila) => {
    const p = fila.payload
    const { formatoOk, tablaVOk, hojaOk } = validadoresTresFlags(p)
    const qRaw = String(p.col_q_fecha ?? '').trim()
    const qIso = String(p.col_q_fecha_iso ?? '').trim()
    if (!formatoOk) {
      return (
        <span className="text-red-600">
          (1) Formato: {String(p.cedula_error ?? 'cédula inválida')}
        </span>
      )
    }
    if (qTieneFechaAmbiguaFromPayload(p)) {
      return (
        <span className="text-red-600">
          (Q) Fecha ambigua en Q (dd/mm). Use YYYY-MM-DD en la hoja para evitar
          inversión día/mes.
        </span>
      )
    }
    if (qRaw && !qIso && !parseFechaFlexible(qRaw)) {
      return (
        <span className="text-red-600">
          (Q) Fecha inválida: use YYYY-MM-DD o YYYY/MM/DD (no ambiguas). Los
          seriales numéricos de la hoja se aceptan y se muestran normalizados.
        </span>
      )
    }
    if (p.huella_no_comparable === true) {
      return (
        <span className="text-red-600">
          Huella no comparable: revise y normalice N/R/S/Q (monto, cuotas,
          modalidad y fecha).
        </span>
      )
    }
    if (aprobacionFueraVentanaFromPayload(p)) {
      return (
        <span className="text-red-600">
          (Q) Fecha de aprobación con más de {MAX_DIAS_APROBACION_DRIVE} días (1
          año); no se permite guardar desde este flujo. Use el alta manual de
          préstamos para operaciones más antiguas.
        </span>
      )
    }
    if (!hojaOk)
      return <span className="text-amber-700">(3) Repetida en hoja</span>
    if (!tablaVOk) {
      return (
        <span className="text-red-600">
          (2) Cédula V o E: ya tiene un préstamo APROBADO (máximo uno). J puede
          tener varios.
        </span>
      )
    }
    if (fila.listo_para_guardar === true) {
      return (
        <span className="text-emerald-700">Listo para guardar (servidor)</span>
      )
    }
    if (fila.listo_para_guardar === false) {
      const motivos = (fila.motivos_no_guardable ?? []).filter(
        m => typeof m === 'string' && m.trim().length > 0
      )
      if (motivos.length > 0) {
        return (
          <span className="text-sky-900">
            ✓✓✓ en pantalla pero servidor rechaza:
            <ul className="mt-0.5 list-disc pl-4">
              {motivos.map((m, i) => (
                <li key={`${fila.id}-mot-${i}`}>{m}</li>
              ))}
            </ul>
          </span>
        )
      }
      return (
        <span className="text-sky-900">
          ✓✓✓ solo en pantalla: revise cliente en BD, montos/fechas (N, R, Q),
          modalidad (S), analista (J), etc.
        </span>
      )
    }
    return (
      <span className="text-emerald-700">
        Listo en pantalla (1·2·3); validación servidor no recibida aún.
      </span>
    )
  }, [])

  const showSkeleton = snapshotQuery.isPending && !snapshotQuery.data
  const isBusy = snapshotQuery.isFetching
  const listRefreshing = isBusy && !manualUpdating
  const accionesGlobalesDeshabilitadas =
    manualUpdating ||
    guardarValidosSaving ||
    eliminandoSeleccionados ||
    guardandoFilaSheet !== null ||
    eliminandoFilaId !== null ||
    actualizandoFechaId !== null ||
    isBusy
  const huellaNoComparableTotal =
    typeof data?.kpis_huella_no_comparable === 'number'
      ? data.kpis_huella_no_comparable
      : null
  const guardarMasivoDeshabilitado =
    accionesGlobalesDeshabilitadas ||
    total === 0 ||
    (guardables === 0 && total > 0)
  const currentPageIds = rows.map(r => r.id)
  const selectedCount = selectedIds.size
  const allSelectedInPage =
    currentPageIds.length > 0 && currentPageIds.every(id => selectedIds.has(id))
  const someSelectedInPage =
    !allSelectedInPage && currentPageIds.some(id => selectedIds.has(id))

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Préstamos"
        description="Actualizaciones: cédulas en CONCILIACIÓN (columna E). V y E: sin préstamo previo. J (jurídico): puede figurar con uno o más préstamos ya en cartera. Puede corregir la fecha (Q) en pantalla (YYYY-MM-DD); se guarda en snapshot y tabla drive local. Lista paginada (100 filas por página). Job automático diario 02:00 Caracas (sync rango A:S hasta última fila con dato → snapshot). Solo administradores."
        icon={CreditCard}
      />

      <DriveScanCoveragePanel />

      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <CardTitle className="text-lg">Candidatos desde Drive</CardTitle>
            <div
              className="flex shrink-0 flex-wrap gap-2 sm:justify-end"
              aria-label="Resumen validación guardado"
            >
              <div
                className="min-w-[6.25rem] rounded-lg border border-emerald-200/80 bg-emerald-50 px-3 py-2 text-center shadow-sm"
                title="Filas que pasan la validación completa de servidor para crear préstamo (cédula, cliente en BD, N, R, Q, S, J, V/E en cartera, etc.). No es un porcentaje del total: es un conteo."
              >
                <p className="text-lg font-semibold tabular-nums text-emerald-900">
                  {data?.kpis_aprueban ?? '-'}
                </p>
                <p className="text-[11px] font-medium uppercase tracking-wide text-emerald-800/90">
                  Guardables
                </p>
              </div>
              <div
                className={`min-w-[6.25rem] rounded-lg border px-3 py-2 text-center shadow-sm ${
                  typeof data?.kpis_no_aprueban === 'number' &&
                  data.kpis_no_aprueban > 0
                    ? 'border-rose-200/90 bg-rose-50/80'
                    : 'border-border bg-muted/50'
                }`}
                title="No pasan esa validación de servidor; no se crearán préstamos hasta corregir datos o la hoja y recalcular. El fondo rojo/ámbar de la tabla es una guía rápida y puede no coincidir 1:1 con este número."
              >
                <p
                  className={`text-lg font-semibold tabular-nums ${
                    typeof data?.kpis_no_aprueban === 'number' &&
                    data.kpis_no_aprueban > 0
                      ? 'text-rose-900'
                      : 'text-foreground'
                  }`}
                >
                  {data?.kpis_no_aprueban ?? '-'}
                </p>
                <p
                  className={`text-[11px] font-medium uppercase tracking-wide ${
                    typeof data?.kpis_no_aprueban === 'number' &&
                    data.kpis_no_aprueban > 0
                      ? 'text-rose-800/95'
                      : 'text-muted-foreground'
                  }`}
                >
                  No guardables
                </p>
              </div>
              <div
                className={`min-w-[6.25rem] rounded-lg border px-3 py-2 text-center shadow-sm ${
                  typeof huellaNoComparableTotal === 'number' &&
                  huellaNoComparableTotal > 0
                    ? 'border-orange-200/90 bg-orange-50/80'
                    : 'border-border bg-muted/50'
                }`}
                title="Casos que no tienen huella comparable completa (N/R/S/Q). Revisión operativa."
              >
                <p
                  className={`text-lg font-semibold tabular-nums ${
                    typeof huellaNoComparableTotal === 'number' &&
                    huellaNoComparableTotal > 0
                      ? 'text-orange-900'
                      : 'text-foreground'
                  }`}
                >
                  {huellaNoComparableTotal ?? '-'}
                </p>
                <p
                  className={`text-[11px] font-medium uppercase tracking-wide ${
                    typeof huellaNoComparableTotal === 'number' &&
                    huellaNoComparableTotal > 0
                      ? 'text-orange-800/95'
                      : 'text-muted-foreground'
                  }`}
                >
                  Huella no comparable
                </p>
              </div>
            </div>
          </div>
          <p className="max-w-3xl text-xs leading-snug text-muted-foreground">
            <strong className="font-medium text-foreground">Aclaración:</strong>{' '}
            «Guardar válidas» solo persiste las filas «Guardables». Los tres ✓
            de la columna Val. son solo reglas en pantalla: si faltan datos para
            el servidor, la fila puede verse en{' '}
            <strong className="font-medium text-sky-900">azul claro</strong> con
            ✓✓✓; el{' '}
            <strong className="font-medium text-emerald-900">
              verde intenso
            </strong>{' '}
            indica listo para guardar.
          </p>
          <p className="text-sm text-muted-foreground">
            {cedulaDebounced && totalSinFiltro != null ? (
              <>
                Coincidencias: <strong>{total}</strong> de {totalSinFiltro} en
                snapshot
              </>
            ) : (
              <>
                Total: <strong>{total}</strong>
              </>
            )}
            {' · '}
            Página <strong>{page}</strong> de {totalPages} · Esta página:{' '}
            <strong>{rows.length}</strong> filas
            {' · '}
            Último sync hoja: {fmtCaracas(data?.drive_synced_at ?? null)}
            {' · '}
            Snapshot: {fmtCaracas(data?.computed_at ?? null)}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2 rounded-lg border border-border bg-muted/30 p-3">
            <Button
              type="button"
              size="sm"
              onClick={() => void onGuardarValidos100()}
              disabled={guardarMasivoDeshabilitado}
              title={
                total === 0
                  ? 'No hay candidatos en el snapshot.'
                  : guardables === 0
                    ? 'Ninguna fila cumple la validación de servidor (0 «Guardables»). Corrija datos o la hoja Drive, use Actualización manual y vuelva a intentar.'
                    : 'Crea préstamos solo para las filas «Guardables» (misma validación que el contador). El resto permanece en el snapshot. Si falla la creación en BD, verá el detalle en el resultado.'
              }
            >
              <Save
                className={`mr-2 h-4 w-4 ${guardarValidosSaving ? 'animate-pulse' : ''}`}
                aria-hidden
              />
              Guardar préstamos validados
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => void onRecalcular()}
              disabled={accionesGlobalesDeshabilitadas}
              title="Trae CONCILIACIÓN desde Google (rango A:S hasta la cola real) y recalcula el snapshot de candidatos."
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${manualUpdating ? 'animate-spin' : ''}`}
                aria-hidden
              />
              Sincronización manual con Drive
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={() => void onEliminarSeleccionados()}
              disabled={accionesGlobalesDeshabilitadas || selectedCount === 0}
              title="Elimina del snapshot solo las filas marcadas con check."
            >
              <Trash2
                className={`mr-2 h-4 w-4 ${eliminandoSeleccionados ? 'animate-pulse' : ''}`}
                aria-hidden
              />
              Eliminar seleccionados ({selectedCount})
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void onRefrescarLista()}
              disabled={accionesGlobalesDeshabilitadas || listRefreshing}
            >
              <Loader2
                className={`mr-2 h-4 w-4 ${listRefreshing ? 'animate-spin' : ''}`}
                aria-hidden
              />
              Refrescar lista
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              title="Exporta solo las filas de la página actual"
              onClick={() => exportarCsvVistaActual(rows)}
              disabled={rows.length === 0 || accionesGlobalesDeshabilitadas}
            >
              <Download className="mr-2 h-4 w-4" aria-hidden />
              Exportar CSV
            </Button>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
            <div className="min-w-[200px] flex-1 space-y-1">
              <label
                htmlFor="filtro-cedula"
                className="text-sm font-medium text-foreground"
              >
                Filtrar por cédula
              </label>
              <Input
                id="filtro-cedula"
                placeholder="Ej. V12345678 o parte del número"
                value={cedulaInput}
                onChange={e => setCedulaInput(e.target.value)}
                autoComplete="off"
              />
            </div>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input accent-primary"
                checked={soloHuellaNoComparable}
                onChange={e => setSoloHuellaNoComparable(e.target.checked)}
              />
              Módulo revisión: solo huella no comparable
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input accent-primary"
                checked={forzarVacio}
                onChange={e => setForzarVacio(e.target.checked)}
              />
              Forzar recálculo si drive vacío (vacía el snapshot)
            </label>
          </div>

          {snapshotQuery.isError && (
            <p className="text-sm text-red-600" role="alert">
              {getErrorMessage(snapshotQuery.error) || 'Error al cargar'}
            </p>
          )}

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[1280px] table-fixed text-left text-sm">
              <colgroup>
                <col style={{ width: '3%' }} />
                <col style={{ width: '3%' }} />
                <col style={{ width: '9%' }} />
                <col style={{ width: '5%' }} />
                <col style={{ width: '7%' }} />
                <col style={{ width: '8%' }} />
                <col style={{ width: '7%' }} />
                <col style={{ width: '4%' }} />
                <col style={{ width: '10%' }} />
                <col style={{ width: '14%' }} />
                <col style={{ width: '9%' }} />
                <col style={{ width: '13%' }} />
                <col style={{ width: '11%' }} />
              </colgroup>
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-2 py-2.5 text-center align-middle text-xs font-semibold">
                    <input
                      type="checkbox"
                      aria-label="Seleccionar todas las filas de la página"
                      checked={allSelectedInPage}
                      ref={el => {
                        if (el) {
                          el.indeterminate = someSelectedInPage
                        }
                      }}
                      onChange={e => {
                        const checked = e.target.checked
                        setSelectedIds(prev => {
                          const next = new Set(prev)
                          if (checked) {
                            currentPageIds.forEach(id => next.add(id))
                          } else {
                            currentPageIds.forEach(id => next.delete(id))
                          }
                          return next
                        })
                      }}
                      disabled={
                        accionesGlobalesDeshabilitadas || rows.length === 0
                      }
                    />
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Fila
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Cédula (E)
                  </th>
                  <th
                    className="whitespace-nowrap px-2 py-2.5 align-middle text-xs font-semibold"
                    title="Tres ítems = solo validadores en pantalla (formato, tabla V/E, hoja). Pueden estar ✓✓✓ y la fila seguir en azul claro hasta cumplir la validación completa de servidor (columna Estado)."
                  >
                    Val. 1·2·3
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Total (N)
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Modalidad (S)
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Fecha (Q)
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Cuotas (R)
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Analista (J)
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Conces. (K)
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Modelo (I)
                  </th>
                  <th className="px-2 py-2.5 align-middle text-xs font-semibold">
                    Estado
                  </th>
                  <th className="sticky right-0 z-20 min-w-[7.5rem] border-l border-border bg-muted px-1 py-2.5 text-center align-middle text-xs font-semibold shadow-[-6px_0_12px_-8px_rgba(0,0,0,0.12)]">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody>
                {showSkeleton && <TableSkeletonRows />}
                {!showSkeleton &&
                  rows.map(r => {
                    const { formatoOk, tablaVOk, hojaOk } =
                      validadoresTresFlags(r.payload)
                    const tono = filaTonoTabla(r)
                    const trTone = FILA_TONE_TR[tono]
                    const stickyTone = FILA_TONE_STICKY_TD[tono]
                    const mk = (x: boolean) => (
                      <span className={x ? 'text-emerald-700' : 'text-red-600'}>
                        {x ? '✓' : '✗'}
                      </span>
                    )
                    return (
                      <tr
                        key={`${r.id}-${r.sheet_row_number}`}
                        className={trTone}
                      >
                        <td className="px-2 py-2 text-center align-middle">
                          <input
                            type="checkbox"
                            aria-label={`Seleccionar fila ${r.sheet_row_number}`}
                            checked={selectedIds.has(r.id)}
                            onChange={e => {
                              const checked = e.target.checked
                              setSelectedIds(prev => {
                                const next = new Set(prev)
                                if (checked) next.add(r.id)
                                else next.delete(r.id)
                                return next
                              })
                            }}
                            disabled={accionesGlobalesDeshabilitadas}
                          />
                        </td>
                        <td className="px-2 py-2 align-middle font-mono text-xs tabular-nums">
                          {r.sheet_row_number}
                        </td>
                        <td className="whitespace-nowrap px-2 py-2 align-middle font-mono text-xs">
                          {strPayload(r.payload, 'col_e_cedula')}
                        </td>
                        <td
                          className="px-2 py-2 text-center align-middle font-mono text-xs"
                          title="Solo reglas 1·2·3 en pantalla; no implica solo el fondo verde intenso (ver Estado / servidor)."
                        >
                          <span className="inline-flex gap-0.5">
                            {mk(formatoOk)}
                            {mk(tablaVOk)}
                            {mk(hojaOk)}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-2 py-2 align-middle font-mono text-xs tabular-nums">
                          {strPayload(r.payload, 'col_n_total_financiamiento')}
                        </td>
                        <td
                          className="max-w-0 overflow-hidden text-ellipsis whitespace-nowrap px-2 py-2 align-middle"
                          title={strPayload(r.payload, 'col_s_modalidad_pago')}
                        >
                          {strPayload(r.payload, 'col_s_modalidad_pago')}
                        </td>
                        <td className="whitespace-nowrap px-2 py-2 align-middle">
                          <div className="flex min-w-[8.5rem] flex-col gap-0.5">
                            <Input
                              ref={el => {
                                fechaQInputRefs.current[r.id] = el
                              }}
                              type="date"
                              className="h-8 px-1.5 text-xs"
                              value={fechaQInputValue(r.payload)}
                              disabled={
                                accionesGlobalesDeshabilitadas ||
                                actualizandoFechaId === r.id
                              }
                              title={
                                colQFechaIsoDisplay(r.payload)
                                  ? `Hoja original (Q): ${strPayload(r.payload, 'col_q_fecha')}`
                                  : 'Corrija la fecha de aprobación (columna Q)'
                              }
                              onChange={e => {
                                const next = e.target.value
                                const prev = fechaQInputValue(r.payload)
                                if (next && next !== prev) {
                                  void onActualizarFechaQ(
                                    r.id,
                                    next,
                                    r.sheet_row_number
                                  )
                                }
                              }}
                            />
                            {actualizandoFechaId === r.id ? (
                              <span className="text-[10px] text-muted-foreground">
                                Guardando…
                              </span>
                            ) : strPayload(r.payload, 'col_q_fecha') !==
                                fechaQInputValue(r.payload) ? (
                              <span
                                className="max-w-[8.5rem] truncate text-[10px] text-muted-foreground"
                                title={strPayload(r.payload, 'col_q_fecha')}
                              >
                                Hoja: {strPayload(r.payload, 'col_q_fecha')}
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td className="px-2 py-2 text-center align-middle tabular-nums">
                          {strPayload(r.payload, 'col_r_numero_cuotas')}
                        </td>
                        <td
                          className="max-w-0 overflow-hidden text-ellipsis whitespace-nowrap px-2 py-2 align-middle"
                          title={strPayload(r.payload, 'col_j_analista')}
                        >
                          {strPayload(r.payload, 'col_j_analista')}
                        </td>
                        <td
                          className="max-w-0 overflow-hidden text-ellipsis whitespace-nowrap px-2 py-2 align-middle"
                          title={strPayload(r.payload, 'col_k_concesionario')}
                        >
                          {strPayload(r.payload, 'col_k_concesionario')}
                        </td>
                        <td
                          className="max-w-0 overflow-hidden text-ellipsis whitespace-nowrap px-2 py-2 align-middle"
                          title={strPayload(r.payload, 'col_i_modelo_vehiculo')}
                        >
                          {strPayload(r.payload, 'col_i_modelo_vehiculo')}
                        </td>
                        <td
                          className="max-w-0 overflow-hidden px-2 py-2 align-middle text-xs leading-snug"
                          title={
                            r.listo_para_guardar === false &&
                            (r.motivos_no_guardable ?? []).length > 0
                              ? `Motivos del servidor:\n• ${(
                                  r.motivos_no_guardable ?? []
                                ).join('\n• ')}`
                              : undefined
                          }
                        >
                          <div className="line-clamp-4 break-words">
                            {estadoFila(r)}
                          </div>
                        </td>
                        <td
                          className={`sticky right-0 z-10 min-w-[7.5rem] border-l border-border px-1 py-1.5 text-center align-middle shadow-[-6px_0_12px_-8px_rgba(0,0,0,0.08)] ${stickyTone}`}
                        >
                          <AccionesPorFilaCandidatoDrive
                            fila={r}
                            disabled={accionesGlobalesDeshabilitadas}
                            puedeGuardarFila={filaCumpleCienParaGuardar(r)}
                            guardandoEstaFila={
                              guardandoFilaSheet === r.sheet_row_number
                            }
                            eliminandoEstaFila={eliminandoFilaId === r.id}
                            onGuardarFila={sr => void onGuardarUnaFila(sr)}
                            onEliminarFila={(id, sr) =>
                              void onEliminarUnaFila(id, sr)
                            }
                            onEditarFecha={enfocarFechaQFila}
                          />
                        </td>
                      </tr>
                    )
                  })}
                {!showSkeleton &&
                  !snapshotQuery.isPending &&
                  rows.length === 0 && (
                    <tr>
                      <td
                        className="px-3 py-6 text-muted-foreground"
                        colSpan={13}
                      >
                        No hay candidatos: para V/E suele significar que ya
                        tienen préstamo en cartera; el snapshot está vacío, o no
                        hay filas que cumplan el criterio. Verifique
                        CONCILIACIÓN en Configuración (Google), use
                        «Sincronización manual con Drive» o el job automático
                        diario 02:00 Caracas (sync A:S + snapshot; recálculo
                        respaldo 04:45 si ENABLE_AUTOMATIC_SCHEDULED_JOBS=true).
                        {cedulaDebounced
                          ? ' Pruebe otro filtro de cédula.'
                          : ''}
                      </td>
                    </tr>
                  )}
              </tbody>
            </table>
          </div>

          <nav
            className="flex flex-col items-center gap-3 border-t border-border pt-4"
            aria-label="Paginación de candidatos"
          >
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-w-[7.5rem] rounded-md border-slate-200 bg-white text-foreground shadow-sm hover:bg-slate-50 disabled:text-muted-foreground"
                disabled={page <= 1 || snapshotQuery.isFetching}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                ← Anterior
              </Button>
              {pageNumbers.map(n => (
                <Button
                  key={n}
                  type="button"
                  variant={n === page ? 'default' : 'outline'}
                  size="sm"
                  className={
                    n === page
                      ? 'h-9 min-w-[2.25rem] rounded-md px-3 shadow-sm'
                      : 'h-9 min-w-[2.25rem] rounded-md border-slate-200 bg-white px-3 text-foreground shadow-sm hover:bg-slate-50'
                  }
                  disabled={snapshotQuery.isFetching}
                  onClick={() => setPage(n)}
                  aria-label={`Ir a página ${n}`}
                  aria-current={n === page ? 'page' : undefined}
                >
                  {n}
                </Button>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-w-[7.5rem] rounded-md border-slate-200 bg-white text-foreground shadow-sm hover:bg-slate-50 disabled:text-muted-foreground"
                disabled={page >= totalPages || snapshotQuery.isFetching}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                Siguiente →
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Página {page} de {totalPages}
            </p>
          </nav>
        </CardContent>
      </Card>
    </div>
  )
}
