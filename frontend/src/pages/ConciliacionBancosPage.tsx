import { useEffect, useMemo, useState } from 'react'
import {
  ArrowDownWideNarrow,
  ArrowUpWideNarrow,
  Building2,
  Check,
  Download,
  Loader2,
  Upload,
} from 'lucide-react'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import {
  CONCILIACION_BANCOS_CATEGORIAS,
  ConciliacionBancosBancoCategoria,
  ConciliacionBancosLote,
  ConciliacionBancosMoneda,
  ConciliacionBancosResultado,
  conciliacionBancosService,
} from '../services/conciliacionBancosService'

function hoyISO(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function errMsg(err: unknown): string {
  const e = err as {
    response?: { data?: { detail?: string } }
    message?: string
  }
  return e?.response?.data?.detail || e?.message || 'Error'
}

// Tope blando de seleccion (evitar marcar decenas de miles por error).
const MAX_SELECCION_MASIVA = 10000
// Compat UI: "hasta N" en checkbox de visibles = pagina actual.
const MAX_CONFIRMACION_MASIVA = 1000
// Tandas HTTP: MATCH es rapido; AMBIGUO (multi-pago+cascada) es pesado.
const CHUNK_MATCH_MASIVA = 100
const CHUNK_AMBIGUO_MASIVA = 25

const CHIP_NOVEDAD_ORDEN = [
  'MATCH_EXACTO',
  'MATCH_PARCIAL',
  'SIN_BD',
  'SIN_BANCO',
  'AMBIGUO',
  'SIN_TASA',
  'CONCILIADOS',
] as const

function esConciliadoBancario(row: ConciliacionBancosResultado): boolean {
  return row.decision === 'CORREGIR' && Boolean(row.aplicado)
}

function esMatchSimple(row: ConciliacionBancosResultado): boolean {
  // MATCH_EXACTO y MATCH_PARCIAL: mismo pipeline (confirmacion directa, sin candidatos)
  return (
    row.tipo_novedad === 'MATCH_EXACTO' || row.tipo_novedad === 'MATCH_PARCIAL'
  )
}

/** AMBIGUO: fuente predeterminada Ref. RapiC (BD). Resto: Ref. Banco. */
function fuenteDefaultFila(
  row: Pick<ConciliacionBancosResultado, 'tipo_novedad'>
): 'BD' | 'BANCO' {
  return row.tipo_novedad === 'AMBIGUO' ? 'BD' : 'BANCO'
}

/** Regla: VISTO (y OMITIR / CORREGIR aplicado) es definitivo: no se puede cambiar. */
function filaBloqueada(row: ConciliacionBancosResultado): boolean {
  return (
    row.decision === 'VISTO' ||
    row.decision === 'OMITIR' ||
    Boolean(row.aplicado) ||
    (row.decision === 'CORREGIR' && row.aplicado)
  )
}


function idsElegidosFila(
  map: Record<number, number[]>,
  rowId: number
): number[] {
  return map[rowId] || []
}

function togglePagoCandidato(
  prev: Record<number, number[]>,
  rowId: number,
  pagoId: number,
  checked: boolean
): Record<number, number[]> {
  const cur = new Set(prev[rowId] || [])
  if (checked) cur.add(pagoId)
  else cur.delete(pagoId)
  const next = { ...prev }
  if (cur.size === 0) delete next[rowId]
  else next[rowId] = [...cur]
  return next
}

export default function ConciliacionBancosPage() {
  const [moneda, setMoneda] = useState<ConciliacionBancosMoneda>('USD')
  /** excel = subir archivo (siempre guarda historica); historica = cargar desde BD */
  const [fuenteExtracto, setFuenteExtracto] = useState<'excel' | 'historica'>('excel')
  const [serialFiltro, setSerialFiltro] = useState('')
  const [serialInfo, setSerialInfo] = useState<{
    encontrado: boolean
    en_extracto: boolean
    filas_extracto: number
    en_pagos: boolean
    pagos_count: number
    serial: string
  } | null>(null)
  const [fechaDesde, setFechaDesde] = useState(hoyISO())
  const [fechaHasta, setFechaHasta] = useState(hoyISO())
  const [file, setFile] = useState<File | null>(null)
  const [lote, setLote] = useState<ConciliacionBancosLote | null>(null)
  const [items, setItems] = useState<ConciliacionBancosResultado[]>([])
  const [stats, setStats] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(false)
  const [rowBusy, setRowBusy] = useState<number | null>(null)
  const [bulkBusy, setBulkBusy] = useState(false)
  const [fuentePorFila, setFuentePorFila] = useState<
    Record<number, 'BD' | 'BANCO'>
  >({})
  const [fuenteMasiva, setFuenteMasiva] = useState<'BD' | 'BANCO'>('BANCO')
  const [pagoElegidoPorFila, setPagoElegidoPorFila] = useState<
    Record<number, number[]>
  >({})
  const [seleccionados, setSeleccionados] = useState<Set<number>>(new Set())
  const [ordenSimilitud, setOrdenSimilitud] = useState<'desc' | 'asc'>(
    'desc'
  )
  const [bancosSel, setBancosSel] = useState<
    ConciliacionBancosBancoCategoria[]
  >([])
  const [filtroNovedad, setFiltroNovedad] = useState<string[]>([])
  const [mostrarConfirmados, setMostrarConfirmados] = useState(false)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [totalResultados, setTotalResultados] = useState(0)
  const PER_PAGE = 1000

  const toggleBanco = (b: ConciliacionBancosBancoCategoria) => {
    setBancosSel(prev =>
      prev.includes(b) ? prev.filter(x => x !== b) : [...prev, b]
    )
  }

  const toggleNovedad = (tipo: string) => {
    setFiltroNovedad(prev => {
      const next = prev.includes(tipo)
        ? prev.filter(x => x !== tipo)
        : [...prev, tipo]
      return next
    })
    setPage(1)
  }

  // Recargar pagina al cambiar filtro o pagina (solo si hay lote comparado)
  useEffect(() => {
    if (!lote || lote.estado === 'COMPARANDO') return
    if (lote.estado !== 'COMPARADO' && lote.estado !== 'APLICADO') return
    let cancelled = false
    ;(async () => {
      try {
        const quiereConc = filtroNovedad.includes('CONCILIADOS')
        const res = await conciliacionBancosService.listarResultados(lote.id, {
          page,
          per_page: PER_PAGE,
          tipo_novedad: filtroNovedad.length ? filtroNovedad : undefined,
          decision:
            !quiereConc && !mostrarConfirmados ? 'PENDIENTE' : undefined,
        })
        if (cancelled) return
        setItems(res.items || [])
        setPages(res.pages || 1)
        setTotalResultados(res.total || 0)
      } catch {
        /* ignore */
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroNovedad, page, lote?.id, lote?.estado, mostrarConfirmados])

  const pendientes = useMemo(() => {
    const src = stats || lote?.stats
    if (src) {
      return (
        Number(src.MATCH_EXACTO || 0) +
        Number(src.MATCH_PARCIAL || 0) +
        Number(src.SIN_BD || 0) +
        Number(src.SIN_BANCO || 0) +
        Number(src.AMBIGUO || 0) +
        Number(src.SIN_TASA || 0)
      )
    }
    return items.filter(i => i.decision === 'PENDIENTE').length
  }, [stats, lote?.stats, items])

  /** Chips en vivo: MATCH_* = pendientes; CONCILIADOS = aprobados bancarios. */
  const statsVivos = useMemo(() => {
    const out: Record<string, number> = {
      MATCH_EXACTO: 0,
      MATCH_PARCIAL: 0,
      SIN_BD: 0,
      SIN_BANCO: 0,
      AMBIGUO: 0,
      SIN_TASA: 0,
      CONCILIADOS: 0,
    }
    for (const i of items) {
      if (esConciliadoBancario(i)) {
        out.CONCILIADOS += 1
        continue
      }
      if (i.decision !== 'PENDIENTE') continue
      if (i.tipo_novedad in out) out[i.tipo_novedad] += 1
    }
    return out
  }, [items])

  // Con paginacion, los chips deben usar stats del lote (no solo la pagina actual).
  const statsMostrar = stats || lote?.stats || null

  useEffect(() => {
    if (lote?.stats) setStats(lote.stats)
  }, [lote?.stats])

  const itemsFiltrados = useMemo(() => {
    let list = items
    const quiereConciliados = filtroNovedad.includes('CONCILIADOS')
    const tiposPend = filtroNovedad.filter(x => x !== 'CONCILIADOS')

    if (quiereConciliados && tiposPend.length === 0) {
      list = list.filter(esConciliadoBancario)
    } else if (quiereConciliados && tiposPend.length > 0) {
      list = list.filter(
        i =>
          esConciliadoBancario(i) ||
          (i.decision === 'PENDIENTE' && tiposPend.includes(i.tipo_novedad))
      )
    } else {
      if (!mostrarConfirmados) {
        list = list.filter(i => i.decision === 'PENDIENTE')
      }
      if (tiposPend.length > 0) {
        list = list.filter(i => tiposPend.includes(i.tipo_novedad))
      }
    }

    const mult = ordenSimilitud === 'desc' ? -1 : 1
    return [...list].sort((a, b) => {
      const sa = a.similitud_pct == null ? -1 : Number(a.similitud_pct)
      const sb = b.similitud_pct == null ? -1 : Number(b.similitud_pct)
      if (sa !== sb) return (sa - sb) * mult
      return a.id - b.id
    })
  }, [items, filtroNovedad, mostrarConfirmados, ordenSimilitud])

  const elegiblesFiltrados = useMemo(
    () =>
      itemsFiltrados.filter(r => {
        if (filaBloqueada(r)) return false
        // AMBIGUO tambien entra en seleccion masiva (confirma todos los candidatos)
        return true
      }),
    [itemsFiltrados]
  )

  /** Cap a max masivo: seleccionar visibles no supera el limite de confirmacion. */
  const elegiblesParaSeleccionMasiva = useMemo(
    () => elegiblesFiltrados.slice(0, MAX_CONFIRMACION_MASIVA),
    [elegiblesFiltrados]
  )

  const todosElegiblesMarcados =
    elegiblesParaSeleccionMasiva.length > 0 &&
    elegiblesParaSeleccionMasiva.every(r => seleccionados.has(r.id))

  const toggleSeleccion = (id: number) => {
    setSeleccionados(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSeleccionarTodos = () => {
    if (todosElegiblesMarcados) {
      // Solo limpia la pagina actual (no toca otras si las hubiera)
      setSeleccionados(prev => {
        const next = new Set(prev)
        for (const r of elegiblesParaSeleccionMasiva) next.delete(r.id)
        return next
      })
      return
    }
    // Reemplaza seleccion: no acumular paginas (evita 1000+1000=2000 y el bloqueo).
    const next = new Set<number>()
    for (const r of elegiblesParaSeleccionMasiva) next.add(r.id)
    setSeleccionados(next)
    toast.message(
      `Seleccionadas ${next.size} filas de esta pagina (se confirmaran en tandas automaticas).`
    )
    // AMBIGUO masivo: por defecto todos los candidatos -> marca Ambiguo
    setPagoElegidoPorFila(prev => {
      const nextMap = { ...prev }
      for (const r of elegiblesParaSeleccionMasiva) {
        if (r.tipo_novedad !== 'AMBIGUO') continue
        if (idsElegidosFila(nextMap, r.id).length > 0) continue
        const all = (r.candidatos || []).map(c => c.pago_id).filter(Boolean)
        if (all.length) nextMap[r.id] = all
      }
      return nextMap
    })
  }

  const refreshResultados = async (
    loteId: number,
    opts?: { page?: number; tipos?: string[] }
  ) => {
    const pg = opts?.page ?? page
    const tipos = opts?.tipos ?? filtroNovedad
    const quiereConc = tipos.includes('CONCILIADOS')
    const res = await conciliacionBancosService.listarResultados(loteId, {
      page: pg,
      per_page: PER_PAGE,
      tipo_novedad: tipos.length ? tipos : undefined,
      decision:
        !quiereConc && !mostrarConfirmados ? 'PENDIENTE' : undefined,
    })
    setItems(res.items || [])
    setPage(res.page || pg)
    setPages(res.pages || 1)
    setTotalResultados(res.total || 0)
    if (res.stats) setStats(res.stats)
  }


  const handleCargar = async () => {
    if (!file) {
      toast.error('Seleccione el Excel (Banco, Fecha, Referencia, Monto)')
      return
    }
    setLoading(true)
    try {
      const res = await conciliacionBancosService.crearLote({
        file,
        moneda_carga: moneda,
        fecha_desde: fechaDesde,
        fecha_hasta: fechaHasta,
      })
      setLote(res.lote)
      setFuenteExtracto('excel')
      if (res.lote.fecha_desde) setFechaDesde(res.lote.fecha_desde)
      if (res.lote.fecha_hasta) setFechaHasta(res.lote.fecha_hasta)
      setItems([])
      setStats(null)
      setFiltroNovedad([])
      setSeleccionados(new Set())
      toast.success(
        `Lote #${res.lote.id} cargado y guardado en BD historica (${moneda}${res.lote.filas_banco != null ? `, ${res.lote.filas_banco} filas` : ''}). Rango: ${res.lote.fecha_desde} → ${res.lote.fecha_hasta}`
      )
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  const handleCargarHistorica = async () => {
    if (bancosSel.length === 0) {
      toast.error('Seleccione al menos un banco del filtro')
      return
    }
    if (!fechaDesde || !fechaHasta) {
      toast.error('Indique fecha desde y hasta')
      return
    }
    setLoading(true)
    try {
      const res = await conciliacionBancosService.crearLoteDesdeHistorica({
        bancos: bancosSel,
        fecha_desde: fechaDesde,
        fecha_hasta: fechaHasta,
        moneda_carga: moneda,
      })
      setLote(res.lote)
      setFuenteExtracto('historica')
      setFile(null)
      setItems([])
      setStats(null)
      setFiltroNovedad([])
      setSeleccionados(new Set())
      toast.success(
        `Lote #${res.lote.id} desde BD historica (${moneda}${res.lote.filas_banco != null ? `, ${res.lote.filas_banco} filas` : ''}). ${res.lote.fecha_desde} → ${res.lote.fecha_hasta}`
      )
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  const handleBuscarSerial = async () => {
    const s = serialFiltro.trim()
    if (!s) {
      toast.error('Ingrese el serial / referencia')
      return
    }
    setLoading(true)
    setSerialInfo(null)
    try {
      const res = await conciliacionBancosService.buscarSerial({
        serial: s,
        moneda,
      })
      setSerialInfo({
        encontrado: res.encontrado,
        en_extracto: res.en_extracto,
        filas_extracto: res.filas_extracto,
        en_pagos: res.en_pagos,
        pagos_count: res.pagos_count,
        serial: res.serial,
      })
      if (res.encontrado) {
        if (res.ya_visto_o_conciliado) {
          toast.message(
            'Serial en historica pero ya VISTO/conciliado (' +
              String(res.filas_ya_cerradas ?? res.filas_extracto) +
              '); no se vuelve a cargar'
          )
        } else {
          toast.success(
            'Serial en BD historica (' +
              String(res.filas_pendientes ?? res.filas_extracto) +
              ' pendiente(s))' +
              (res.en_pagos
                ? ' · tambien en pagos (' + String(res.pagos_count) + ')'
                : ' · sin pago BD')
          )
        }
      } else {
        toast.message(
          res.en_pagos
            ? 'Serial NO en historica, pero hay ' +
                String(res.pagos_count) +
                ' pago(s) BD'
            : 'Serial NO esta en BD historica'
        )
      }
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  const handleConciliarSerial = async () => {
    const s = serialFiltro.trim()
    if (!s) {
      toast.error('Ingrese el serial / referencia')
      return
    }
    setLoading(true)
    try {
      const res = await conciliacionBancosService.crearLoteDesdeSerial({
        serial: s,
        moneda_carga: moneda,
        bancos: bancosSel.length ? bancosSel : undefined,
      })
      setLote(res.lote)
      setFuenteExtracto('historica')
      setFile(null)
      setItems([])
      setStats(null)
      setFiltroNovedad([])
      setSeleccionados(new Set())
      if (res.lote.fecha_desde) setFechaDesde(res.lote.fecha_desde)
      if (res.lote.fecha_hasta) setFechaHasta(res.lote.fecha_hasta)
      const bancosLote = res.lote.bancos_filtro || []
      if (bancosLote.length && bancosSel.length === 0) {
        setBancosSel(bancosLote as ConciliacionBancosBancoCategoria[])
      }
      toast.success(
        'Serial encontrado. Lote #' +
          String(res.lote.id) +
          ' listo (' +
          String(res.lote.filas_banco ?? 0) +
          ' fila(s)). Pulse Conciliar.'
      )
      setSerialInfo({
        encontrado: true,
        en_extracto: true,
        filas_extracto: res.lote.filas_banco ?? 1,
        en_pagos: false,
        pagos_count: 0,
        serial: s,
      })
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  const handleConciliar = async () => {
    if (!lote) {
      toast.error('Cargue Excel nuevo o BD historica primero')
      return
    }
    if (bancosSel.length === 0) {
      toast.error('Seleccione al menos un banco del filtro')
      return
    }
    setLoading(true)
    try {
      const start = await conciliacionBancosService.comparar(
        lote.id,
        bancosSel,
        {
          fecha_desde: fechaDesde,
          fecha_hasta: fechaHasta,
        }
      )
      setLote(prev =>
        prev
          ? {
              ...prev,
              estado: start.estado || 'COMPARANDO',
              fecha_desde: start.fecha_desde || prev.fecha_desde,
              fecha_hasta: start.fecha_hasta || prev.fecha_hasta,
            }
          : prev
      )
      if (start.fecha_desde) setFechaDesde(start.fecha_desde)
      if (start.fecha_hasta) setFechaHasta(start.fecha_hasta)
      toast.message(
        'Conciliando en segundo plano (lotes grandes pueden tardar varios minutos)...'
      )

      const loteId = lote.id
      const maxPolls = 180 // ~15 min @ 5s
      let finalLote = null as ConciliacionBancosLote | null
      for (let i = 0; i < maxPolls; i++) {
        await new Promise(r => setTimeout(r, 5000))
        const polled = await conciliacionBancosService.obtenerLote(loteId)
        finalLote = polled.lote
        setLote(polled.lote)
        if (polled.lote.estado === 'COMPARADO') break
        if (polled.lote.estado === 'ERROR_COMPARAR') {
          throw new Error(
            polled.lote.comparar_error ||
              'La comparacion fallo o se interrumpio. Pulse Conciliar de nuevo.'
          )
        }
        // Si el backend ya no tiene job vivo y sigue COMPARANDO, el poll
        // siguiente deberia sanear a ERROR; si no, cortar tras varios ciclos.
        if (
          polled.lote.estado === 'COMPARANDO' &&
          polled.lote.job_vivo === false &&
          i >= 2
        ) {
          throw new Error(
            'La conciliacion no esta corriendo en el servidor (posible reinicio). Pulse Conciliar de nuevo.'
          )
        }
      }
      if (!finalLote || finalLote.estado !== 'COMPARADO') {
        throw new Error(
          'La comparacion sigue en curso o tardo demasiado. Recargue el lote mas tarde.'
        )
      }
      setStats(finalLote.stats || null)
      setFiltroNovedad([])
      setPage(1)
      await refreshResultados(loteId, { page: 1, tipos: [] })
      const univ = finalLote.pagos_universo ?? 0
      const sinBd = Number(finalLote.stats?.SIN_BD || 0)
      const rango = `${finalLote.fecha_desde || fechaDesde} → ${finalLote.fecha_hasta || fechaHasta}`
      const elapsed = finalLote.comparar_elapsed_ms
        ? ` (${Math.round(finalLote.comparar_elapsed_ms / 1000)}s)`
        : ''
      if (univ === 0) {
        toast.error(
          `Sin pagos BD en ${rango} para ${bancosSel.join(', ')}. ` +
            `Filas banco sin match: ${sinBd}. Revise bancos del filtro.`
        )
      } else {
        toast.success(
          `Comparacion lista${elapsed}. ${rango}; bancos: ${bancosSel.join(', ')}. Pagos universo: ${univ}.`
        )
      }
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  /** Fuente + visto = confirmar: Ref.BD mantiene; Ref.Banco graba (cascada si aplica). */
  const handleConfirmar = async (row: ConciliacionBancosResultado) => {
    const fuente = fuentePorFila[row.id] || fuenteDefaultFila(row)
    const pagoElegido = pagoElegidoPorFila[row.id]
    setRowBusy(row.id)
    try {
      if (row.tipo_novedad === 'AMBIGUO') {
        const ids = Array.isArray(pagoElegido)
          ? pagoElegido
          : pagoElegido
            ? [pagoElegido]
            : []
        if (ids.length === 0) {
          toast.error(
            'AMBIGUO: elija uno, varios o todos los prestamos/pagos candidatos'
          )
          return
        }
        const r = await conciliacionBancosService.decidir(row.id, {
          decision: 'CORREGIR',
          fuente_elegida: fuente,
          pago_ids_elegidos: ids,
          pago_id_elegido: ids[0],
        })
        const aplicados = Number(r.aplicados || ids.length)
        if (fuente === 'BANCO' && r.cambio) {
          toast.success(
            `AMBIGUO: confirmados ${aplicados} pago(s) (Ref. Banco)`
          )
        } else if (fuente === 'BANCO') {
          toast.message(`AMBIGUO: confirmados ${aplicados} pago(s)`)
        } else {
          toast.message(
            `AMBIGUO: confirmados ${aplicados} pago(s) (Ref. RapiC)`
          )
        }
        if (lote) await refreshResultados(lote.id)
        return
      }
      // Sin pago vinculado no hay que grabar/mantener paquete: solo cierra como revisado
      if (
        !row.pago_id ||
        row.tipo_novedad === 'SIN_BD' ||
        row.tipo_novedad === 'SIN_TASA'
      ) {
        await conciliacionBancosService.decidir(row.id, { decision: 'VISTO' })
        toast.message('Marcado como revisado (sin pago BD para aplicar)')
        if (lote) await refreshResultados(lote.id)
        return
      }
      const r = await conciliacionBancosService.decidir(row.id, {
        decision: 'CORREGIR',
        fuente_elegida: fuente,
      })
      if (fuente === 'BANCO' && r.cambio) {
        toast.success('Confirmado Ref. Banco: datos actualizados')
      } else if (fuente === 'BANCO') {
        toast.message('Confirmado Ref. Banco: ya coincidia con BD')
      } else {
        toast.message('Confirmado Ref. BD: se mantienen los datos')
      }
      if (lote) await refreshResultados(lote.id)
    } catch (err) {
      toast.error(errMsg(err))
      if (lote) await refreshResultados(lote.id)
    } finally {
      setRowBusy(null)
    }
  }

  const handleConfirmarMasivo = async () => {
    const ids = [...seleccionados]
    if (ids.length === 0) {
      toast.error('Seleccione al menos una fila pendiente')
      return
    }
    if (ids.length > MAX_SELECCION_MASIVA) {
      toast.error(
        `Demasiadas filas (${ids.length}). Maximo ${MAX_SELECCION_MASIVA}; filtre por novedad o confirme por paginas.`
      )
      return
    }
    setBulkBusy(true)
    const byId = new Map(items.map(i => [i.id, i]))
    const hayAmbiguo = ids.some(id => byId.get(id)?.tipo_novedad === 'AMBIGUO')
    const chunkSize = hayAmbiguo ? CHUNK_AMBIGUO_MASIVA : CHUNK_MATCH_MASIVA
    const progressToast = toast.loading(
      `Confirmando 0/${ids.length} (tandas de ${chunkSize})...`
    )
    try {
      const payload = ids.map(id => {
        const row = byId.get(id)
        let elegidos = idsElegidosFila(pagoElegidoPorFila, id)
        if (
          row?.tipo_novedad === 'AMBIGUO' &&
          elegidos.length === 0 &&
          row.candidatos?.length
        ) {
          elegidos = row.candidatos.map(c => c.pago_id).filter(Boolean)
        }
        return {
          resultado_id: id,
          fuente_elegida:
            fuentePorFila[id] ||
            (row ? fuenteDefaultFila(row) : fuenteMasiva),
          ...(elegidos.length
            ? {
                pago_ids_elegidos: elegidos,
                pago_id_elegido: elegidos[0],
              }
            : {}),
        }
      })

      let exitosos = 0
      let errores = 0
      let sinPago = 0
      let conCambio = 0
      let firstErr: string | undefined
      const okIds = new Set<number>()

      for (let i = 0; i < payload.length; i += chunkSize) {
        const chunk = payload.slice(i, i + chunkSize)
        const desde = i + 1
        const hasta = Math.min(i + chunk.length, payload.length)
        toast.loading(
          `Confirmando ${desde}-${hasta} de ${payload.length}...`,
          { id: progressToast }
        )
        try {
          const r = await conciliacionBancosService.decidirMasivo({
            items: chunk,
            fuente_default: fuenteMasiva,
          })
          exitosos += Number(r.exitosos || 0)
          errores += Number(r.errores || 0)
          sinPago += Number(r.sin_pago_vistos || 0)
          conCambio += Number(r.con_cambio || 0)
          for (const d of r.detalle || []) {
            if (d.ok) okIds.add(Number(d.resultado_id))
            else if (!firstErr && d.error) firstErr = String(d.error)
          }
        } catch (chunkErr) {
          // Cloudflare 520 / timeout: lo ya commitado en tandas previas se conserva
          errores += chunk.length
          if (!firstErr) firstErr = errMsg(chunkErr)
          toast.message(
            `Tanda ${desde}-${hasta} interrumpida; se conserva lo confirmado antes. Pulse de nuevo para continuar.`
          )
          break
        }
      }

      toast.dismiss(progressToast)
      setSeleccionados(prev => {
        const next = new Set(prev)
        for (const id of okIds) next.delete(id)
        return next
      })

      if (errores === 0) {
        toast.success(
          `Confirmados ${exitosos}/${payload.length}` +
            (conCambio ? ` (${conCambio} con cambio BD)` : '')
        )
      } else {
        toast.message(
          `Masivo: ${exitosos} ok, ${errores} error(es), ${sinPago} sin pago`
        )
        if (firstErr) toast.error(String(firstErr).slice(0, 180))
      }
      if (lote) await refreshResultados(lote.id)
    } catch (err) {
      toast.dismiss(progressToast)
      toast.error(errMsg(err))
      if (lote) await refreshResultados(lote.id)
    } finally {
      setBulkBusy(false)
    }
  }

  const handleExport = async () => {
    if (!lote) return
    try {
      await conciliacionBancosService.descargarExcel(lote.id)
    } catch (err) {
      toast.error(errMsg(err))
    }
  }

  return (
    <div className="space-y-6">
      <ModulePageHeader
        icon={Building2}
        title="Conciliacion Bancos"
        description="Excel Banco|Fecha|Referencia|Monto. Regla: VISTO es definitivo y deja la fila bloqueada. Match vs pagos.numero_documento (OCR)."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">1) Preparar carga</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={moneda === 'USD' ? 'default' : 'outline'}
              onClick={() => setMoneda('USD')}
            >
              Carga USD
            </Button>
            <Button
              type="button"
              variant={moneda === 'BS' ? 'default' : 'outline'}
              onClick={() => setMoneda('BS')}
            >
              Carga Bs
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium">
                Fecha desde (filtro pagos BD)
              </label>
              <Input
                type="date"
                value={fechaDesde}
                onChange={e => setFechaDesde(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Fecha hasta (filtro pagos BD)
              </label>
              <Input
                type="date"
                value={fechaHasta}
                onChange={e => setFechaHasta(e.target.value)}
              />
            </div>
            {fuenteExtracto === 'excel' ? (
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Excel (A Banco, B Fecha, C Referencia, D Monto)
                </label>
                <Input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={e => setFile(e.target.files?.[0] || null)}
                />
              </div>
            ) : (
              <div className="flex items-end">
                <p className="text-sm text-gray-600">
                  Sin archivo: se usan filas ya guardadas en BD historica
                  (bancos + fechas + moneda).
                </p>
              </div>
            )}
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium">
              Filtro banco BD (seleccion multiple)
            </label>
            <div className="flex flex-wrap gap-3">
              {CONCILIACION_BANCOS_CATEGORIAS.map(b => (
                <label
                  key={b}
                  className="flex cursor-pointer items-center gap-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={bancosSel.includes(b)}
                    onChange={() => toggleBanco(b)}
                  />
                  {b}
                </label>
              ))}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Solo se comparan pagos BD de los bancos marcados. Drive =
              ABONOS-NOTIF / ABONOS-DRIVE (asientos Drive, a menudo suma de
              pagos).
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={fuenteExtracto === 'excel' ? 'default' : 'outline'}
              onClick={() => setFuenteExtracto('excel')}
              disabled={loading}
            >
              Excel nuevo
            </Button>
            <Button
              type="button"
              variant={fuenteExtracto === 'historica' ? 'default' : 'outline'}
              onClick={() => setFuenteExtracto('historica')}
              disabled={loading}
            >
              BD historica
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            Cada Excel subido se almacena siempre en BD historica. Use{' '}
            <strong>Excel nuevo</strong> para conciliar lo que acaba de subir, o{' '}
            <strong>BD historica</strong> para cargar lo ya guardado (filtro
            banco + fechas) y conciliar de nuevo.
          </p>

          <div className="rounded-lg border border-gray-200 bg-gray-50/80 p-3 space-y-2">
            <label className="block text-sm font-medium">
              Filtro por serial (referencia / documento)
            </label>
            <div className="flex flex-wrap gap-2 items-end">
              <div className="min-w-[220px] flex-1">
                <Input
                  placeholder="Ej. 740087486821077"
                  value={serialFiltro}
                  onChange={e => {
                    setSerialFiltro(e.target.value)
                    setSerialInfo(null)
                  }}
                />
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={handleBuscarSerial}
                disabled={loading || !serialFiltro.trim()}
              >
                Buscar serial
              </Button>
              <Button
                type="button"
                className="bg-emerald-600 hover:bg-emerald-700"
                onClick={handleConciliarSerial}
                disabled={loading || !serialFiltro.trim()}
              >
                Cargar serial y preparar
              </Button>
            </div>
            <p className="text-xs text-gray-500">
              La BD historica responde si el serial existe; si existe, se arma el
              lote y luego pulse Conciliar.
            </p>
            {serialInfo && (
              <p
                className={
                  serialInfo.encontrado
                    ? 'text-sm text-emerald-700'
                    : 'text-sm text-amber-700'
                }
              >
                {serialInfo.encontrado
                  ? `En historica: ${serialInfo.filas_extracto} fila(s)`
                  : 'No esta en BD historica'}
                {serialInfo.en_pagos
                  ? ` · En pagos BD: ${serialInfo.pagos_count}`
                  : ' · Sin pago BD'}
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {fuenteExtracto === 'excel' ? (
              <Button onClick={handleCargar} disabled={loading || !file}>
                {loading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Subir Excel (guarda en BD)
              </Button>
            ) : (
              <Button
                onClick={handleCargarHistorica}
                disabled={loading || bancosSel.length === 0}
                variant="secondary"
              >
                {loading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Cargar BD historica
              </Button>
            )}
            <Button
              onClick={handleConciliar}
              disabled={loading || !lote || bancosSel.length === 0}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {loading && lote?.estado === 'COMPARANDO'
                ? 'Conciliando...'
                : fuenteExtracto === 'historica'
                  ? 'Conciliar BD historica'
                  : 'Conciliar Excel nuevo'}
            </Button>
            <Button
              variant="outline"
              onClick={handleExport}
              disabled={!lote || (lote.estado !== 'COMPARADO' && lote.estado !== 'APLICADO')}
            >
              <Download className="mr-2 h-4 w-4" />
              Reporte Excel
            </Button>
          </div>

          {lote && (
            <p className="text-sm text-gray-600">
              Lote #{lote.id} · {lote.archivo_nombre} · {lote.moneda_carga}
              {lote.filas_banco != null ? ` · ${lote.filas_banco} filas` : ''} ·{' '}
              {lote.fecha_desde} → {lote.fecha_hasta} · estado {lote.estado}
              {statsMostrar ? ` · pendientes decision: ${pendientes}` : null}
            </p>
          )}

            {lote && totalResultados > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
                <span>
                  Mostrando {items.length} de {totalResultados} (pag. {page}/{pages})
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={loading || page <= 1}
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                >
                  Anterior
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={loading || page >= pages}
                  onClick={() => setPage(p => Math.min(pages, p + 1))}
                >
                  Siguiente
                </Button>
              </div>
            )}


          {statsMostrar && (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                {CHIP_NOVEDAD_ORDEN.map(k => {
                  const v = Number(statsMostrar[k] || 0)

                  const activo = filtroNovedad.includes(k)
                  const esConc = k === 'CONCILIADOS'
                  return (
                    <button
                      key={k}
                      type="button"
                      onClick={() => {
                        toggleNovedad(k)
                        if (esConc && !activo) setMostrarConfirmados(true)
                      }}
                      title={
                        esConc
                          ? 'Pagos con conciliacion bancaria aprobada'
                          : activo
                            ? 'Quitar filtro'
                            : 'Filtrar pendientes por esta novedad'
                      }
                      className="rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <Badge
                        variant="outline"
                        className={
                          activo
                            ? esConc
                              ? 'cursor-pointer border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800'
                              : 'cursor-pointer border-blue-600 bg-blue-600 text-white hover:bg-blue-700'
                            : esConc
                              ? 'cursor-pointer border-emerald-600 text-emerald-800 hover:bg-emerald-50'
                              : 'cursor-pointer hover:border-blue-400 hover:bg-blue-50'
                        }
                      >
                        {k}: {v}
                      </Badge>
                    </button>
                  )
                })}
                <Button
                  type="button"
                  size="sm"
                  variant={mostrarConfirmados ? 'default' : 'ghost'}
                  onClick={() => setMostrarConfirmados(v => !v)}
                >
                  {mostrarConfirmados
                    ? 'Ocultar confirmados'
                    : 'Mostrar confirmados'}
                </Button>
                {filtroNovedad.length > 0 && (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => setFiltroNovedad([])}
                  >
                    Ver todos
                  </Button>
                )}
              </div>
              <p className="text-xs text-gray-500">
                Novedad = pendientes. Al aprobar bajan a CONCILIADOS. Re-subir
                compara solo no conciliados bancarios + nuevos.
                {filtroNovedad.length > 0
                  ? ` Mostrando ${itemsFiltrados.length} de ${items.length}.`
                  : ` Pendientes: ${pendientes}.`}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            2) Resultados (referencia banco · similitud · decision)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {elegiblesFiltrados.length > 0 && (
            <div className="flex flex-wrap items-center gap-3 rounded-md border bg-slate-50 px-3 py-2">
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={todosElegiblesMarcados}
                  onChange={toggleSeleccionarTodos}
                  disabled={bulkBusy || loading}
                />
                Seleccionar visibles (hasta {MAX_CONFIRMACION_MASIVA}
                  {elegiblesFiltrados.length > 0
                    ? ` · ${Math.min(elegiblesFiltrados.length, MAX_CONFIRMACION_MASIVA)} en pantalla`
                    : ''}
                  )
              </label>
              <span className="text-sm text-gray-600">
                {seleccionados.size} seleccionada
                {seleccionados.size === 1 ? '' : 's'}
              </span>
              <label className="flex items-center gap-2 text-sm">
                Cambiar fuente de seleccionadas
                <select
                  className="rounded border px-2 py-1 text-xs"
                  title="Solo cambia el dropdown de las filas marcadas. Al confirmar, cada fila usa su propia fuente."
                  value={fuenteMasiva}
                  disabled={bulkBusy || seleccionados.size === 0}
                  onChange={e => {
                    const f = e.target.value as 'BD' | 'BANCO'
                    setFuenteMasiva(f)
                    setFuentePorFila(prev => {
                      const next = { ...prev }
                      for (const id of seleccionados) next[id] = f
                      return next
                    })
                  }}
                >
                  <option value="BANCO">Ref. Banco</option>
                  <option value="BD">Ref. RapiC</option>
                </select>
              </label>
              <Button
                size="sm"
                disabled={
                  bulkBusy ||
                  loading ||
                  seleccionados.size === 0 ||
                  rowBusy != null
                }
                onClick={handleConfirmarMasivo}
                className="bg-green-700 hover:bg-green-800"
              >
                {bulkBusy ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Check className="mr-2 h-4 w-4" />
                )}
                Confirmar seleccionados
              </Button>
            </div>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <input
                    type="checkbox"
                    title={`Seleccionar filas visibles de esta pagina (confirmacion en tandas automaticas)`}
                    checked={todosElegiblesMarcados}
                    onChange={toggleSeleccionarTodos}
                    disabled={
                      bulkBusy || loading || elegiblesFiltrados.length === 0
                    }
                  />
                </TableHead>
                <TableHead>Cedula</TableHead>
                <TableHead>Prestamo</TableHead>
                <TableHead>Referencias</TableHead>
                <TableHead>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 font-medium hover:text-foreground"
                    title={
                      ordenSimilitud === 'desc'
                        ? 'Orden: mayor a menor. Clic para menor a mayor.'
                        : 'Orden: menor a mayor. Clic para mayor a menor.'
                    }
                    onClick={() =>
                      setOrdenSimilitud(prev =>
                        prev === 'desc' ? 'asc' : 'desc'
                      )
                    }
                  >
                    Similitud
                    {ordenSimilitud === 'desc' ? (
                      <ArrowDownWideNarrow className="h-3.5 w-3.5" />
                    ) : (
                      <ArrowUpWideNarrow className="h-3.5 w-3.5" />
                    )}
                  </button>
                </TableHead>
                <TableHead>Banco BD</TableHead>
                <TableHead>Fechas</TableHead>
                <TableHead>Montos USD</TableHead>
                <TableHead>Novedad</TableHead>
                <TableHead>Fuente</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={11}
                    className="py-8 text-center text-gray-500"
                  >
                    Sin resultados. Suba Excel y pulse Conciliar.
                  </TableCell>
                </TableRow>
              ) : itemsFiltrados.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={11}
                    className="py-8 text-center text-gray-500"
                  >
                    No hay filas para el filtro de novedad seleccionado.{' '}
                    <button
                      type="button"
                      className="text-blue-600 underline"
                      onClick={() => setFiltroNovedad([])}
                    >
                      Ver todos
                    </button>
                  </TableCell>
                </TableRow>
              ) : (
                itemsFiltrados.map(row => {
                  const busy = rowBusy === row.id || bulkBusy
                  const locked = filaBloqueada(row)
                  return (
                    <TableRow key={row.id}>
                      <TableCell>
                        <input
                          type="checkbox"
                          disabled={locked || busy}
                          checked={seleccionados.has(row.id)}
                          onChange={() => {
                            toggleSeleccion(row.id)
                            // Al marcar AMBIGUO en masivo, preseleccionar todos los candidatos
                            if (
                              row.tipo_novedad === 'AMBIGUO' &&
                              !seleccionados.has(row.id) &&
                              idsElegidosFila(pagoElegidoPorFila, row.id)
                                .length === 0
                            ) {
                              const all = (row.candidatos || [])
                                .map(c => c.pago_id)
                                .filter(Boolean)
                              if (all.length) {
                                setPagoElegidoPorFila(prev => ({
                                  ...prev,
                                  [row.id]: all,
                                }))
                              }
                            }
                          }}
                          title={
                            row.tipo_novedad === 'AMBIGUO'
                              ? 'AMBIGUO: seleccion masiva confirma todos los candidatos (Ambiguo)'
                              : undefined
                          }
                        />
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {row.tipo_novedad === 'AMBIGUO' &&
                        row.candidatos &&
                        row.candidatos.length > 0 ? (
                          <div className="max-w-[260px] space-y-1 rounded border border-red-200 bg-red-50/40 p-1.5 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-medium text-red-800">
                                Elegir (uno/varios/todos)
                              </span>
                              <button
                                type="button"
                                className="text-[11px] text-blue-700 underline disabled:opacity-50"
                                disabled={locked || busy}
                                onClick={() => {
                                  const all = row.candidatos!.map(c => c.pago_id)
                                  const cur = idsElegidosFila(
                                    pagoElegidoPorFila,
                                    row.id
                                  )
                                  const todos =
                                    cur.length === all.length &&
                                    all.every(id => cur.includes(id))
                                  setPagoElegidoPorFila(prev => {
                                    const next = { ...prev }
                                    if (todos) delete next[row.id]
                                    else next[row.id] = all
                                    return next
                                  })
                                }}
                              >
                                {idsElegidosFila(pagoElegidoPorFila, row.id)
                                  .length === row.candidatos.length
                                  ? 'Quitar todos'
                                  : 'Todos'}
                              </button>
                            </div>
                            {row.candidatos.map(c => {
                              const checked = idsElegidosFila(
                                pagoElegidoPorFila,
                                row.id
                              ).includes(c.pago_id)
                              return (
                                <label
                                  key={c.pago_id}
                                  className="flex cursor-pointer items-start gap-1.5"
                                >
                                  <input
                                    type="checkbox"
                                    className="mt-0.5"
                                    disabled={locked || busy}
                                    checked={checked}
                                    onChange={e =>
                                      setPagoElegidoPorFila(prev =>
                                        togglePagoCandidato(
                                          prev,
                                          row.id,
                                          c.pago_id,
                                          e.target.checked
                                        )
                                      )
                                    }
                                  />
                                  <span>
                                    {c.cedula || '?'} · #
                                    {c.prestamo_id ?? '?'} · pago {c.pago_id}
                                    {c.monto != null ? ` · $${c.monto}` : ''}
                                  </span>
                                </label>
                              )
                            })}
                          </div>
                        ) : (
                          row.cedula || '-'
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {row.tipo_novedad === 'AMBIGUO' &&
                        idsElegidosFila(pagoElegidoPorFila, row.id).length >
                          0 ? (
                          (() => {
                            const ids = idsElegidosFila(
                              pagoElegidoPorFila,
                              row.id
                            )
                            const labels = ids.map(pid => {
                              const c = row.candidatos?.find(
                                x => x.pago_id === pid
                              )
                              return c?.prestamo_id != null
                                ? `#${c.prestamo_id}`
                                : `pago ${pid}`
                            })
                            return labels.join(', ')
                          })()
                        ) : row.tipo_novedad === 'AMBIGUO' ? (
                          <span className="text-red-700">Elegir →</span>
                        ) : row.prestamo_id != null ? (
                          `#${row.prestamo_id}`
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell className="max-w-[200px] font-mono text-xs">
                        Banco: {row.referencia_banco || '-'}
                        <br />
                        RapiC: {row.referencia_bd || '-'}
                      </TableCell>
                      <TableCell>
                        {row.similitud_pct != null
                          ? `${row.similitud_pct}%`
                          : '-'}
                      </TableCell>
                      <TableCell className="text-xs">
                        {row.institucion_categoria || '-'}
                        {row.institucion_bancaria ? (
                          <div className="max-w-[120px] truncate text-[11px] text-gray-500">
                            {row.institucion_bancaria}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-xs">
                        Banco: {row.fecha_banco || '-'}
                        <br />
                        RapiC: {row.fecha_bd || '-'}
                      </TableCell>
                      <TableCell className="text-xs">
                        Banco: {row.monto_banco ?? '-'}
                        <br />
                        RapiC: {row.monto_bd ?? '-'}
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={
                            esMatchSimple(row)
                              ? 'bg-green-600'
                              : row.tipo_novedad === 'SIN_BD'
                                ? 'bg-amber-600'
                                : row.tipo_novedad === 'AMBIGUO'
                                  ? 'bg-red-600'
                                  : 'bg-gray-600'
                          }
                        >
                          {row.tipo_novedad}
                        </Badge>
                        <div className="mt-1 text-xs text-gray-500">
                          {row.decision}
                          {row.aplicado ? ' · aplicado' : ''}
                        </div>
                        {row.decision === 'VISTO' ? (
                          <Badge
                            variant="outline"
                            className="mt-1 border-slate-400 text-[10px] text-slate-700"
                            title="Regla: VISTO es definitivo y no se puede cambiar"
                          >
                            Bloqueado
                          </Badge>
                        ) : null}
                        {row.tipo_novedad === 'AMBIGUO' &&
                          (row.candidatos?.length || 0) > 1 && (
                            <div className="mt-1 max-w-[160px] text-[11px] text-red-700">
                              Mismo serial en {row.candidatos?.length}{' '}
                              pagos. Seleccion masiva = todos (Ambiguo).
                            </div>
                          )}
                      </TableCell>
                      <TableCell>
                        <select
                          className="rounded border px-2 py-1 text-xs"
                          disabled={locked || busy}
                          value={
                            fuentePorFila[row.id] || fuenteDefaultFila(row)
                          }
                          onChange={e =>
                            setFuentePorFila(prev => ({
                              ...prev,
                              [row.id]: e.target.value as 'BD' | 'BANCO',
                            }))
                          }
                        >
                          <option value="BANCO">Ref. Banco</option>
                          <option value="BD">Ref. RapiC</option>
                        </select>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            title={
                              locked
                                ? row.decision === 'VISTO'
                                  ? 'Bloqueado: VISTO definitivo, no se puede cambiar'
                                  : 'Fila bloqueada (ya procesada)'
                                : (fuentePorFila[row.id] ||
                                      fuenteDefaultFila(row)) === 'BANCO'
                                  ? 'Confirmar: grabar paquete Ref. Banco'
                                  : 'Confirmar: mantener paquete Ref. RapiC'
                            }
                            disabled={
                              locked ||
                              busy ||
                              (row.tipo_novedad === 'AMBIGUO' &&
                                idsElegidosFila(pagoElegidoPorFila, row.id)
                                  .length === 0)
                            }
                            onClick={() => handleConfirmar(row)}
                          >
                            {busy ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Check className="h-4 w-4 text-green-600" />
                            )}
                          </Button>
                        </div>
                        {row.detalle_aplicacion && (
                          <p className="mt-1 max-w-[220px] text-[11px] text-gray-500">
                            {row.detalle_aplicacion}
                          </p>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
