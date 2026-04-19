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
function numerosPaginaVisibles(current: number, totalPages: number, maxButtons: number): number[] {
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

function strPayload(p: PrestamoCandidatoDriveFila['payload'], key: string): string {
  const v = p[key]
  if (v == null) return '—'
  return String(v)
}

function escapeCsvCell(s: string): string {
  const t = String(s ?? '').replace(/"/g, '""')
  if (/[",\n\r]/.test(t)) return `"${t}"`
  return t
}

/** Cédula normalizada tipo V o E (regla innegociable: máximo un préstamo en cartera). */
function cedulaEsTipoVeFromPayload(p: PrestamoCandidatoDriveFila['payload']): boolean {
  if (p.cedula_es_tipo_ve === true) return true
  const u = String(p.cedula_cmp ?? '')
    .trim()
    .toUpperCase()
  if (u.length > 0 && (u[0] === 'V' || u[0] === 'E')) return true
  return p.cedula_es_tipo_v_venezolano === true || p.cedula_es_tipo_e === true
}

/** Cédula tipo J (jurídico): pueden existir 2 o más préstamos; no aplica el tope V/E en columna 2. */
function cedulaEsTipoJFromPayload(p: PrestamoCandidatoDriveFila['payload']): boolean {
  if (p.cedula_es_tipo_j === true) return true
  const u = String(p.cedula_cmp ?? '')
    .trim()
    .toUpperCase()
  return u.length > 0 && u[0] === 'J'
}

/** 1 formato cédula · 2 regla V/E vs tabla préstamos (J exento) · 3 sin duplicado en hoja */
function validadoresTresFlags(p: PrestamoCandidatoDriveFila['payload']) {
  const formatoOk = (p.validador_formato_cedula_ok ?? p.cedula_valida) === true
  const hojaOk = (p.validador_sin_duplicado_en_hoja_ok ?? p.duplicada_en_hoja !== true) === true
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
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
      const d = new Date(year, month - 1, day, 12, 0, 0)
      if (d.getFullYear() === year && d.getMonth() === month - 1 && d.getDate() === day) return d
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
    const parts = raw.split(multiSpace).map(x => x.trim()).filter(Boolean)
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

type FilaCandidatoDriveTono = 'red' | 'amber' | 'green' | 'plain'

/** Fondo de fila: rojo (prioridad), ámbar, verde, o neutro. */
function filaCandidatoDriveTono(p: PrestamoCandidatoDriveFila['payload']): FilaCandidatoDriveTono {
  const { formatoOk, tablaVOk, hojaOk, nPrest, esVe } = validadoresTresFlags(p)
  const dup = p.duplicada_en_hoja === true
  const qRaw = String(p.col_q_fecha ?? '').trim()

  const redInvalida = !formatoOk
  const redVeDosOMasCreditos = esVe && Number.isFinite(nPrest) && nPrest >= 2
  const redFechaAntigua = aprobacionQMasDe30Dias(qRaw)

  if (redInvalida || redVeDosOMasCreditos || redFechaAntigua) return 'red'
  if (formatoOk && dup) return 'amber'
  if (formatoOk && tablaVOk && hojaOk) return 'green'
  return 'plain'
}

/** Innegociable: solo filas en verde (100% de reglas de esta pantalla, incl. Q ≤ 30 días) pueden guardarse. */
function filaCumpleCienParaGuardar(p: PrestamoCandidatoDriveFila['payload']): boolean {
  return filaCandidatoDriveTono(p) === 'green'
}

const FILA_TONE_TR: Record<FilaCandidatoDriveTono, string> = {
  red: 'bg-red-50/95 hover:bg-red-50/90 border-b border-red-100',
  amber: 'bg-amber-50/95 hover:bg-amber-50/90 border-b border-amber-100',
  green: 'bg-emerald-50/95 hover:bg-emerald-50/90 border-b border-emerald-100',
  plain: 'border-b border-border bg-background hover:bg-muted/25',
}

const FILA_TONE_STICKY_TD: Record<FilaCandidatoDriveTono, string> = {
  red: 'bg-red-50/98 backdrop-blur-sm',
  amber: 'bg-amber-50/98 backdrop-blur-sm',
  green: 'bg-emerald-50/98 backdrop-blur-sm',
  plain: 'bg-background/98 backdrop-blur-sm',
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
    const { formatoOk, tablaVOk, hojaOk, nPrest, esVe, esJ } = validadoresTresFlags(p)
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
      : `Guardar solo esta fila (cumple 100% de validadores).`
    : `No se puede guardar: la fila debe cumplir el 100% de validadores (debe verse en verde).`

  return (
    <div className="flex flex-nowrap items-center justify-end gap-1">
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
        <Edit2 className="h-3.5 w-3.5 text-foreground" strokeWidth={2} aria-hidden />
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
        <Trash2 className="h-3.5 w-3.5 text-red-600" strokeWidth={2} aria-hidden />
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
            <td key={j} className="px-3 py-2">
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
  const [manualUpdating, setManualUpdating] = useState(false)
  const [guardarValidosSaving, setGuardarValidosSaving] = useState(false)
  const [guardandoFilaSheet, setGuardandoFilaSheet] = useState<number | null>(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    const t = window.setTimeout(() => setCedulaDebounced(cedulaInput.trim()), 400)
    return () => window.clearTimeout(t)
  }, [cedulaInput])

  useEffect(() => {
    setPage(1)
  }, [cedulaDebounced])

  const snapshotQuery = useQuery({
    queryKey: [...QK_BASE, cedulaDebounced, page],
    queryFn: () =>
      getPrestamosCandidatosDriveSnapshot(
        PAGE_SIZE,
        (page - 1) * PAGE_SIZE,
        cedulaDebounced || undefined
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
          toast.success('Snapshot vaciado (drive sin filas, recálculo forzado).')
        } else {
          toast.success(
            `Snapshot actualizado: ${Number(res.candidatos_insertados ?? 0)} candidato(s).`
          )
        }
      }
      await qc.resetQueries({ queryKey: [...QK_BASE, cedulaDebounced] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo recalcular')
    } finally {
      setManualUpdating(false)
    }
  }, [qc, forzarVacio, cedulaDebounced])

  const refetchLista = snapshotQuery.refetch

  const onGuardarUnaFila = useCallback(
    async (sheetRowNumber: number) => {
      const fila = rows.find(r => r.sheet_row_number === sheetRowNumber)
      if (!fila || !filaCumpleCienParaGuardar(fila.payload)) {
        toast.error('Solo se puede guardar una fila en verde (100% de validadores de esta pantalla).')
        return
      }
      setGuardandoFilaSheet(sheetRowNumber)
      try {
        const res = await postPrestamosCandidatosDriveGuardarFila(sheetRowNumber)
        if (!res.ok) {
          const m = (res.motivos && res.motivos.length > 0 ? res.motivos.join(' · ') : null) || res.mensaje
          toast.error(m || 'No se pudo guardar la fila.')
          return
        }
        toast.success(res.mensaje || `Fila ${sheetRowNumber} guardada.`)
        await qc.resetQueries({ queryKey: [...QK_BASE, cedulaDebounced] })
      } catch (e) {
        toast.error(getErrorMessage(e) || 'No se pudo guardar la fila')
      } finally {
        setGuardandoFilaSheet(null)
      }
    },
    [qc, cedulaDebounced, rows]
  )

  const onGuardarValidos100 = useCallback(async () => {
    setGuardarValidosSaving(true)
    try {
      const res = await postPrestamosCandidatosDriveGuardarValidados100()
      const ins = Number(res.insertados_ok ?? 0)
      const om = Number(res.omitidos_no_100 ?? 0)
      const err = Number(res.errores_al_guardar ?? 0)
      if (err > 0) {
        toast.warning(res.mensaje || `Creados: ${ins}. Omitidos: ${om}. Errores: ${err}.`)
      } else if (ins > 0) {
        toast.success(res.mensaje || `${ins} préstamo(s) creado(s) (solo 100% validadores).`)
      } else {
        toast.message(res.mensaje || 'Ninguna fila cumplió el 100% de validadores; no se guardó nada.')
      }
      await qc.resetQueries({ queryKey: [...QK_BASE, cedulaDebounced] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar')
    } finally {
      setGuardarValidosSaving(false)
    }
  }, [qc, cedulaDebounced])

  const onRefrescarLista = useCallback(async () => {
    try {
      await refetchLista()
      toast.message('Lista actualizada desde el servidor.')
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo refrescar la lista')
    }
  }, [refetchLista])

  const fmtCaracas = useCallback((iso: string | null | undefined) => {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleString('es-VE', { timeZone: 'America/Caracas' })
    } catch {
      return iso
    }
  }, [])

  const estadoFila = useCallback((p: PrestamoCandidatoDriveFila['payload']) => {
    const { formatoOk, tablaVOk, hojaOk } = validadoresTresFlags(p)
    const qRaw = String(p.col_q_fecha ?? '').trim()
    if (!formatoOk) {
      return (
        <span className="text-red-600">
          (1) Formato: {String(p.cedula_error ?? 'cédula inválida')}
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
    if (!hojaOk) return <span className="text-amber-700">(3) Repetida en hoja</span>
    if (!tablaVOk) {
      return (
        <span className="text-red-600">
          (2) Cédula V o E: máximo un préstamo en tabla (innegociable). J puede tener varios.
        </span>
      )
    }
    return <span className="text-emerald-700">Listo (validadores 1·2·3 OK)</span>
  }, [])

  const showSkeleton = snapshotQuery.isPending && !snapshotQuery.data
  const isBusy = snapshotQuery.isFetching
  const listRefreshing = isBusy && !manualUpdating
  const accionesGlobalesDeshabilitadas =
    manualUpdating || guardarValidosSaving || guardandoFilaSheet !== null || isBusy
  const guardarMasivoDeshabilitado = accionesGlobalesDeshabilitadas || total === 0

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Préstamos"
        description="Actualizaciones: cédulas en CONCILIACIÓN (columna E). V y E: sin préstamo previo. J (jurídico): puede figurar con uno o más préstamos ya en cartera. Lista paginada (100 filas por página). Job dom/mié ~04:05 Caracas. Solo administradores."
        icon={CreditCard}
      />

      <Card>
        <CardHeader className="space-y-1">
          <CardTitle className="text-lg">Candidatos desde Drive</CardTitle>
          <p className="text-sm text-muted-foreground">
            {cedulaDebounced && totalSinFiltro != null ? (
              <>
                Coincidencias: <strong>{total}</strong> de {totalSinFiltro} en snapshot
              </>
            ) : (
              <>
                Total: <strong>{total}</strong>
              </>
            )}
            {' · '}
            Página <strong>{page}</strong> de {totalPages} · Esta página: <strong>{rows.length}</strong> filas
            {' · '}
            Último sync hoja: {fmtCaracas(data?.drive_synced_at ?? null)}
            {' · '}
            Snapshot: {fmtCaracas(data?.computed_at ?? null)}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-4 rounded-lg border border-blue-100 bg-blue-50/40 p-4">
            <div className="min-w-0 space-y-3">
              <div className="space-y-1 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">Actualización</p>
                <p>
                  Use <strong>Actualización manual</strong> para volver a calcular el snapshot desde la tabla{' '}
                  <code className="rounded bg-white/80 px-1">drive</code> (mismo proceso que el cron). Use{' '}
                  <strong>Refrescar lista</strong> solo para releer en pantalla lo ya guardado.{' '}
                  <strong>Guardar (100%)</strong> recorre <strong>todo</strong> el snapshot y crea préstamos solo para
                  las filas que cumplen el 100% de validadores (el servidor valida cada una; si falla un validador, esa
                  fila no se guarda). <strong>Guardar por fila</strong> (icono disco) solo está activo en filas{' '}
                  <strong>verdes</strong>. Validadores resumidos en columna <strong>Val. 1·2·3</strong>: (1) formato de
                  cédula, (2) tipo <strong>V</strong> o <strong>E</strong> — a lo sumo un préstamo en tabla{' '}
                  <code className="rounded bg-white/80 px-1">prestamos</code> (más de uno no cumple); tipo{' '}
                  <strong>J</strong> puede tener dos o más préstamos (sin ese tope), (3) no duplicada en la hoja; además
                  la fecha de aprobación en <strong>Q</strong> no puede superar 30 días (misma regla que el fondo rojo).
                  La columna <strong>Acciones</strong> incluye editar y quitar (en desarrollo).
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void onGuardarValidos100()}
                  disabled={guardarMasivoDeshabilitado}
                  title={
                    total === 0
                      ? 'No hay candidatos en el snapshot.'
                      : 'Inserta en préstamos cada fila del snapshot que cumpla el 100% de validadores (las demás se omiten).'
                  }
                >
                  <Save
                    className={`mr-2 h-4 w-4 ${guardarValidosSaving ? 'animate-pulse' : ''}`}
                    aria-hidden
                  />
                  Guardar (100%)
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void onRecalcular()}
                  disabled={accionesGlobalesDeshabilitadas}
                >
                  <RefreshCw
                    className={`mr-2 h-4 w-4 ${manualUpdating ? 'animate-spin' : ''}`}
                    aria-hidden
                  />
                  Actualización manual
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void onRefrescarLista()}
                  disabled={accionesGlobalesDeshabilitadas || listRefreshing}
                >
                  <Loader2 className={`mr-2 h-4 w-4 ${listRefreshing ? 'animate-spin' : ''}`} aria-hidden />
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
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
            <div className="min-w-[200px] flex-1 space-y-1">
              <label htmlFor="filtro-cedula" className="text-sm font-medium text-foreground">
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

          <p className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-6 rounded-sm bg-emerald-200 ring-1 ring-emerald-300/60" aria-hidden />
              Verde: cumple validadores 1·2·3 de esta pantalla
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-6 rounded-sm bg-amber-200 ring-1 ring-amber-300/60" aria-hidden />
              Ámbar: cédula válida pero repetida en el snapshot Drive
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-6 rounded-sm bg-red-200 ring-1 ring-red-300/60" aria-hidden />
              Rojo: cédula inválida; tipo V/E con ≥2 préstamos con esa cédula (J exento); o fecha aprobación (Q) con
              más de 30 días
            </span>
          </p>

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[1120px] text-left text-sm">
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-3 py-2">Fila</th>
                  <th className="px-3 py-2">Cédula (E)</th>
                  <th
                    className="px-3 py-2 whitespace-nowrap"
                    title="1 formato · 2 tabla préstamos (V/E máx. 1; J puede varios) · 3 hoja"
                  >
                    Val. 1·2·3
                  </th>
                  <th className="px-3 py-2">Total (N)</th>
                  <th className="px-3 py-2">Modalidad (S)</th>
                  <th className="px-3 py-2">Fecha (Q)</th>
                  <th className="px-3 py-2">Cuotas (R)</th>
                  <th className="px-3 py-2">Analista (J)</th>
                  <th className="px-3 py-2">Concesionario (K)</th>
                  <th className="px-3 py-2">Modelo (I)</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="sticky right-0 z-[1] bg-muted/95 px-3 py-2 text-right shadow-[-4px_0_8px_-4px_rgba(0,0,0,0.08)] backdrop-blur-sm">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody>
                {showSkeleton && <TableSkeletonRows />}
                {!showSkeleton &&
                  rows.map(r => {
                    const { formatoOk, tablaVOk, hojaOk } = validadoresTresFlags(r.payload)
                    const tono = filaCandidatoDriveTono(r.payload)
                    const trTone = FILA_TONE_TR[tono]
                    const stickyTone = FILA_TONE_STICKY_TD[tono]
                    const mk = (x: boolean) => (
                      <span className={x ? 'text-emerald-700' : 'text-red-600'}>{x ? '✓' : '✗'}</span>
                    )
                    return (
                      <tr key={`${r.id}-${r.sheet_row_number}`} className={trTone}>
                        <td className="px-3 py-2 font-mono">{r.sheet_row_number}</td>
                        <td className="px-3 py-2 font-mono">{strPayload(r.payload, 'col_e_cedula')}</td>
                        <td className="px-3 py-2 font-mono text-xs" title="1 formato · 2 tabla (V/E; J exento) · 3 hoja">
                          {mk(formatoOk)}
                          {mk(tablaVOk)}
                          {mk(hojaOk)}
                        </td>
                        <td className="px-3 py-2">{strPayload(r.payload, 'col_n_total_financiamiento')}</td>
                        <td className="px-3 py-2">{strPayload(r.payload, 'col_s_modalidad_pago')}</td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {strPayload(r.payload, 'col_q_fecha')}
                        </td>
                        <td className="px-3 py-2">{strPayload(r.payload, 'col_r_numero_cuotas')}</td>
                        <td className="px-3 py-2">{strPayload(r.payload, 'col_j_analista')}</td>
                        <td className="px-3 py-2">{strPayload(r.payload, 'col_k_concesionario')}</td>
                        <td
                          className="px-3 py-2 max-w-[140px] truncate"
                          title={strPayload(r.payload, 'col_i_modelo_vehiculo')}
                        >
                          {strPayload(r.payload, 'col_i_modelo_vehiculo')}
                        </td>
                        <td className="px-3 py-2 text-xs">{estadoFila(r.payload)}</td>
                        <td
                          className={`sticky right-0 z-[1] border-l border-border px-2 py-1.5 text-right shadow-[-4px_0_8px_-4px_rgba(0,0,0,0.06)] ${stickyTone}`}
                        >
                          <AccionesPorFilaCandidatoDrive
                            fila={r}
                            disabled={accionesGlobalesDeshabilitadas}
                            puedeGuardarFila={filaCumpleCienParaGuardar(r.payload)}
                            guardandoEstaFila={guardandoFilaSheet === r.sheet_row_number}
                            onGuardarFila={sr => void onGuardarUnaFila(sr)}
                          />
                        </td>
                      </tr>
                    )
                  })}
                {!showSkeleton && !snapshotQuery.isPending && rows.length === 0 && (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={12}>
                      No hay candidatos: para V/E suele significar que ya tienen préstamo en cartera; el snapshot está
                      vacío, o no hay filas que cumplan el criterio. Verifique CONCILIACIÓN en Configuración (Google)
                      y el job automático (dom/mié 04:00 sync + 04:05 snapshot si está activo en servidor).
                      {cedulaDebounced ? ' Pruebe otro filtro de cédula.' : ''}
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
