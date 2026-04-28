import { useCallback, useEffect, useState } from 'react'

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

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  getPrestamosCandidatosDriveSnapshot,
  postPrestamosCandidatosDriveEliminarSeleccionados,
  postPrestamosCandidatosDriveGuardarFila,
  postPrestamosCandidatosDriveGuardarValidados100,
  postPrestamosCandidatosDriveRefrescar,
  type PrestamoCandidatoDriveFila,
} from '../services/prestamosCandidatosDriveService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

const QK_BASE = ['actualizaciones', 'prestamos-drive', 'snapshot'] as const

/** Filas por página (offset en API = (página − 1) × PAGE_SIZE). */
const PAGE_SIZE = 100
/** Botones numéricos visibles a la vez (ventana deslizante). */
const PAGE_WINDOW = 5

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
  const esV = p.cedula_es_tipo_v_venezolano === true
  const esVe = cedulaEsTipoVeFromPayload(p)
  const esJ = cedulaEsTipoJFromPayload(p)
  const tablaVOk = esJ
    ? true
    : (p.validador_ve_max_un_prestamo_ok ??
        p.validador_v_max_un_prestamo_ok ??
        !(esVe && nPrest >= 2)) === true
  return { formatoOk, tablaVOk, hojaOk, nPrest, esV, esVe, esJ }
}

/** Parseo ligero alineado a columna Q (DD/MM/YYYY o YYYY-MM-DD). */
function parseFechaFlexible(s: string): Date | null {
  const raw = (s || '').trim()
  if (!raw) return null
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
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

/** Fecha de aprobación (Q) con más de 30 días calendario respecto a hoy (zona local). */
function aprobacionQMasDe30Dias(qVal: string): boolean {
  const ap = fechaAprobacionDesdeColQ(qVal)
  if (!ap) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const ap0 = new Date(ap)
  ap0.setHours(0, 0, 0, 0)
  const diffDays = Math.floor((today.getTime() - ap0.getTime()) / 86400000)
  return diffDays > 30
}

function qTieneFechaAmbigua(qVal: string): boolean {
  const raw = (qVal || '').trim()
  if (!raw) return false
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
  const { formatoOk, tablaVOk, hojaOk, nPrest, esVe } = validadoresTresFlags(p)
  const dup = p.duplicada_en_hoja === true
  const qRaw = String(p.col_q_fecha ?? '').trim()

  const redInvalida = !formatoOk
  const redVeDosOMasCreditos = esVe && Number.isFinite(nPrest) && nPrest >= 2
  const redFechaAntigua = aprobacionQMasDe30Dias(qRaw)
  const redHuellaNoComparable = p.huella_no_comparable === true

  if (
    redInvalida ||
    redVeDosOMasCreditos ||
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
  onGuardarFila,
}: {
  fila: PrestamoCandidatoDriveFila
  disabled: boolean
  puedeGuardarFila: boolean
  guardandoEstaFila: boolean
  onGuardarFila: (sheetRowNumber: number) => void
}) {
  const iconBtn =
    'h-8 w-8 shrink-0 rounded-md border border-slate-200 bg-white p-0 shadow-sm hover:bg-slate-50 disabled:opacity-50'
  const sr = fila.sheet_row_number
  const saveDisabled = disabled || !puedeGuardarFila || guardandoEstaFila
  const saveTitle = puedeGuardarFila
    ? guardandoEstaFila
      ? `Guardando fila de hoja ${sr}…`
      : `Guardar solo esta fila (misma validación de servidor que «Guardar válidas»).`
    : `No se puede guardar: la fila no cumple la validación de servidor (cliente, N, R, Q, S, J, cédula, etc.).`

  return (
    <div className="flex min-w-0 flex-nowrap items-center justify-center gap-0.5 sm:gap-1">
      <Button
        type="button"
        variant="outline"
        size="icon"
        className={iconBtn}
        title={`Editar fila hoja ${sr} (próximamente)`}
        aria-label={`Editar fila ${sr}`}
        disabled={disabled}
        onClick={() =>
          toast.message(`Edición de fila ${sr} (hoja): próximamente.`)
        }
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
        title={`Quitar candidato fila ${sr} (próximamente)`}
        aria-label={`Borrar fila ${sr}`}
        disabled={disabled}
        onClick={() =>
          toast.message(`Quitar candidato fila ${sr}: próximamente.`)
        }
      >
        <Trash2
          className="h-3.5 w-3.5 text-red-600"
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

  const onRecalcular = useCallback(async () => {
    setManualUpdating(true)
    try {
      const res = await postPrestamosCandidatosDriveRefrescar({
        forzar: forzarVacio,
      })
      if (res?.omitido === true) {
        toast.message(
          (res.motivo as string) === 'tabla_drive_sin_filas'
            ? 'No se recalculó: la tabla drive está vacía (se mantiene el snapshot anterior). Marque «Forzar…» para vaciar el snapshot.'
            : 'Recálculo omitido.'
        )
      } else {
        const motivo = res?.motivo as string | undefined
        if (motivo === 'forzar_con_drive_vacio') {
          toast.success(
            'Snapshot vaciado (drive sin filas, recálculo forzado).'
          )
        } else {
          toast.success(
            `Snapshot actualizado: ${Number(res.candidatos_insertados ?? 0)} candidato(s).`
          )
        }
      }
      await qc.resetQueries({ queryKey: [...QK_BASE] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo recalcular')
    } finally {
      setManualUpdating(false)
    }
  }, [qc, forzarVacio, cedulaDebounced, page])

  const refetchLista = snapshotQuery.refetch

  const onGuardarUnaFila = useCallback(
    async (sheetRowNumber: number) => {
      const fila = rows.find(r => r.sheet_row_number === sheetRowNumber)
      if (!fila || !filaCumpleCienParaGuardar(fila)) {
        toast.error(
          'Solo se puede guardar una fila que cumpla la validación de servidor (la misma que usa «Guardar válidas»).'
        )
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
        await qc.resetQueries({ queryKey: [...QK_BASE] })
      } catch (e) {
        toast.error(getErrorMessage(e) || 'No se pudo guardar la fila')
      } finally {
        setGuardandoFilaSheet(null)
      }
    },
    [qc, cedulaDebounced, page, rows]
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
      await qc.resetQueries({ queryKey: [...QK_BASE] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar')
    } finally {
      setGuardarValidosSaving(false)
    }
  }, [qc, guardables])

  const onRefrescarLista = useCallback(async () => {
    try {
      await refetchLista()
      toast.message('Lista actualizada desde el servidor.')
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo refrescar la lista')
    }
  }, [refetchLista])

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
      await qc.resetQueries({ queryKey: [...QK_BASE] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudieron eliminar las filas seleccionadas')
    } finally {
      setEliminandoSeleccionados(false)
    }
  }, [qc, selectedIds])

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
    if (!formatoOk) {
      return (
        <span className="text-red-600">
          (1) Formato: {String(p.cedula_error ?? 'cédula inválida')}
        </span>
      )
    }
    if (qTieneFechaAmbigua(qRaw)) {
      return (
        <span className="text-red-600">
          (Q) Fecha ambigua en Q (dd/mm). Use YYYY-MM-DD para evitar inversión
          día/mes.
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
    if (aprobacionQMasDe30Dias(qRaw)) {
      return (
        <span className="text-red-600">
          (Q) Fecha de aprobación con más de 30 días; no se permite guardar.
        </span>
      )
    }
    if (!hojaOk)
      return <span className="text-amber-700">(3) Repetida en hoja</span>
    if (!tablaVOk) {
      return (
        <span className="text-red-600">
          (2) Cédula V o E: máximo un préstamo en tabla (innegociable). J puede
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
    isBusy
  const guardables =
    typeof data?.kpis_aprueban === 'number' ? data.kpis_aprueban : null
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
        description="Actualizaciones: cédulas en CONCILIACIÓN (columna E). V y E: sin préstamo previo. J (jurídico): puede figurar con uno o más préstamos ya en cartera. Lista paginada (100 filas por página). Job dom/mié ~04:05 Caracas. Solo administradores."
        icon={CreditCard}
      />

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
              title="Sincroniza manualmente contra Drive y recalcula snapshot de candidatos."
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
                      disabled={accionesGlobalesDeshabilitadas || rows.length === 0}
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
                          {strPayload(r.payload, 'col_q_fecha')}
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
                        <td className="max-w-0 overflow-hidden px-2 py-2 align-middle text-xs leading-snug">
                          <div className="line-clamp-2 break-words">
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
                            onGuardarFila={sr => void onGuardarUnaFila(sr)}
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
                        CONCILIACIÓN en Configuración (Google) y el job
                        automático (dom/mié 04:00 sync + 04:05 snapshot si está
                        activo en servidor).
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
