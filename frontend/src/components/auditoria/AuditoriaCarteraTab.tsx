import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  Check,
  ChevronLeft,
  ChevronRight,
  CircleCheck,
  Download,
  FileText,
  Filter,
  Loader2,
  RefreshCw,
  RotateCcw,
} from 'lucide-react'

import { Button } from '../ui/button'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { AlertDescription, AlertWithIcon } from '../ui/alert'

import { Input } from '../ui/input'

import { Label } from '../ui/label'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

import { Badge } from '../ui/badge'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'

import { Textarea } from '../ui/textarea'

import {
  auditoriaService,
  PrestamoCarteraChequeo,
  type CarteraRevisionItem,
  type Control5DuplicadoFechaMontoItem,
  type Control15PagoSinAplicacionItem,
} from '../../services/auditoriaService'

import { prestamoService } from '../../services/prestamoService'

import { useSimpleAuth } from '../../store/simpleAuthStore'
import { isAdminRole } from '../../utils/rol'

import { canonicalRol } from '../../utils/rol'

import { toast } from 'sonner'

import { Link } from 'react-router-dom'

import {
  AUDITORIA_CARTERA_CONTROLES_CATALOGO,
  numeroControlAuditoriaCartera,
} from './auditoriaCarteraControlesCatalogo'

function controlDismissKey(prestamoId: number, codigo: string) {
  return `${prestamoId}:${codigo}`
}

const COD_DESAJUSTE_PAGOS = 'total_pagado_vs_aplicado_cuotas'

const COD_CTRL_PAGOS_MISMO_DIA_MONTO = 'pagos_mismo_dia_monto'

const COD_PAGOS_SIN_APLICACION = 'pagos_sin_aplicacion_a_cuotas'

const PAGE_SIZE_DEFAULT = 25

const NOTA_EXCEPCION_MIN_LEN = 15

const NOTA_REVOCACION_MIN_LEN = 10

function csvEscapeCell(val: string): string {
  if (/[",\n\r]/.test(val)) {
    return `"${val.replace(/"/g, '""')}"`
  }
  return val
}

type FiltrosApi = {
  cedula: string
  prestamo_id?: number
  /** Filtro servidor: solo prestamos con este control en SI (opcional). */
  codigo_control?: string
}

const VALOR_TODOS_CONTROLES = '__todos__'

function etiquetaCasosControl(n: number): string {
  if (n === 1) return '1 caso'
  return `${n} casos`
}

/** Solo el numero en color: verde si 0, naranja si hay casos (texto "caso(s)" sin color). */
function ConteoCasosResaltado({ n }: { n: number }) {
  const numCls = n === 0 ? '!text-green-600' : '!text-orange-600'
  return (
    <>
      <span className={`tabular-nums ${numCls}`}>{n}</span>
      {n === 1 ? ' caso' : ' casos'}
    </>
  )
}

function ConteoPrestamosAlertaResaltado({ n }: { n: number }) {
  const numCls = n === 0 ? '!text-green-600' : '!text-orange-600'
  return (
    <>
      <span className={`tabular-nums ${numCls}`}>{n}</span>
      {n === 1 ? ' prestamo con alerta' : ' prestamos con alerta'}
    </>
  )
}

function etiquetaPrestamosConAlerta(n: number): string {
  if (n === 1) return '1 prestamo con alerta'
  return `${n} prestamos con alerta`
}

const SESSION_CACHE_KEY = 'auditoria_cartera_ui_v1'

type CarteraSessionCacheV1 = {
  v: 1
  items: PrestamoCarteraChequeo[]
  resumen: Record<string, unknown>
  filtrosApi: FiltrosApi
  page: number
  /** Legacy; UI ya no filtra por control (se persiste vacio). */
  filtroControlCodigo: string
  ocultosKeys: string[]
  /** true = ver tambien excepciones ya aceptadas (motor completo). */
  vista_motor_crudo?: boolean
}

function loadCarteraSessionCache(): CarteraSessionCacheV1 | null {
  try {
    const raw = sessionStorage.getItem(SESSION_CACHE_KEY)
    if (!raw) return null
    const c = JSON.parse(raw) as Partial<CarteraSessionCacheV1>
    if (c.v !== 1 || !Array.isArray(c.items) || !c.filtrosApi) return null
    return {
      v: 1,
      items: c.items,
      resumen: (c.resumen && typeof c.resumen === 'object'
        ? c.resumen
        : {}) as Record<string, unknown>,
      filtrosApi: {
        cedula:
          typeof c.filtrosApi.cedula === 'string' ? c.filtrosApi.cedula : '',
        prestamo_id: c.filtrosApi.prestamo_id,
      },
      page: typeof c.page === 'number' && c.page >= 1 ? c.page : 1,
      filtroControlCodigo:
        typeof c.filtroControlCodigo === 'string' ? c.filtroControlCodigo : '',
      ocultosKeys: Array.isArray(c.ocultosKeys) ? c.ocultosKeys : [],
      vista_motor_crudo: c.vista_motor_crudo === true,
    }
  } catch {
    return null
  }
}

function saveCarteraSessionCache(payload: {
  items: PrestamoCarteraChequeo[]
  resumen: Record<string, unknown>
  filtrosApi: FiltrosApi
  page: number
  filtroControlCodigo: string
  ocultosKeys: string[]
  vista_motor_crudo: boolean
}) {
  try {
    const row: CarteraSessionCacheV1 = {
      v: 1,
      items: payload.items,
      resumen: payload.resumen,
      filtrosApi: payload.filtrosApi,
      page: payload.page,
      filtroControlCodigo: payload.filtroControlCodigo,
      ocultosKeys: payload.ocultosKeys,
      vista_motor_crudo: payload.vista_motor_crudo,
    }
    sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(row))
  } catch {
    /* quota o modo privado */
  }
}

export function AuditoriaCarteraTab() {
  const { user } = useSimpleAuth()

  const esAdmin = isAdminRole(user?.rol)

  const puedeAuditoriaCartera = useMemo(() => {
    const r = canonicalRol(user?.rol)
    return r !== 'operator' && r !== 'viewer'
  }, [user?.rol])

  const boot = useMemo(() => loadCarteraSessionCache(), [])

  const [loading, setLoading] = useState(() => boot === null)

  const [running, setRunning] = useState(false)

  const [syncingEstados, setSyncingEstados] = useState(false)

  const [corrigiendo, setCorrigiendo] = useState(false)

  const [exportando, setExportando] = useState(false)

  const [items, setItems] = useState<PrestamoCarteraChequeo[]>(
    () => boot?.items ?? []
  )

  const [resumen, setResumen] = useState<Record<string, unknown> | null>(
    () => boot?.resumen ?? null
  )

  /** Claves `prestamo_id:codigo_control` con ultimo MARCAR_OK en BD (POST ocultos). */
  const [ocultosKeys, setOcultosKeys] = useState<Set<string>>(
    () => new Set(boot?.ocultosKeys ?? [])
  )

  const [historialOpen, setHistorialOpen] = useState(false)

  const [historialPid, setHistorialPid] = useState<number | null>(null)

  const [historialRows, setHistorialRows] = useState<CarteraRevisionItem[]>([])

  const [historialLoading, setHistorialLoading] = useState(false)

  const [cedulaInput, setCedulaInput] = useState(
    () => boot?.filtrosApi.cedula ?? ''
  )

  const [prestamoInput, setPrestamoInput] = useState(() =>
    boot?.filtrosApi.prestamo_id != null
      ? String(boot.filtrosApi.prestamo_id)
      : ''
  )

  const [filtrosApi, setFiltrosApi] = useState<FiltrosApi>(() => {
    if (!boot?.filtrosApi) return { cedula: '' }
    const codLegacy =
      boot.filtroControlCodigo && String(boot.filtroControlCodigo).trim()
        ? String(boot.filtroControlCodigo).trim()
        : undefined
    const prevCod = (boot.filtrosApi as Partial<FiltrosApi>).codigo_control
    return {
      cedula: boot.filtrosApi.cedula ?? '',
      prestamo_id: boot.filtrosApi.prestamo_id,
      codigo_control: codLegacy ?? prevCod,
    }
  })

  const [page, setPage] = useState(() => boot?.page ?? 1)

  const [pageSize] = useState(PAGE_SIZE_DEFAULT)

  const [vistaMotorCrudo, setVistaMotorCrudo] = useState(
    () => boot?.vista_motor_crudo === true
  )

  const [okDialogOpen, setOkDialogOpen] = useState(false)

  const [okTarget, setOkTarget] = useState<{
    prestamoId: number
    codigo: string
    titulo: string
  } | null>(null)

  const [okNota, setOkNota] = useState('')

  const [okSubmitting, setOkSubmitting] = useState(false)

  const [controlesConExcHist, setControlesConExcHist] = useState<string[]>([])

  const [exportCodigoHist, setExportCodigoHist] = useState('')

  const [exportandoHist, setExportandoHist] = useState(false)

  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false)

  const [revokeTarget, setRevokeTarget] = useState<{
    prestamoId: number
    codigo: string
    titulo: string
  } | null>(null)

  const [revokeNota, setRevokeNota] = useState('')

  const [revokeSubmitting, setRevokeSubmitting] = useState(false)

  const [vistoDialogOpen, setVistoDialogOpen] = useState(false)

  const [vistoPrestamoId, setVistoPrestamoId] = useState<number | null>(null)

  const [vistoFilas, setVistoFilas] = useState<
    Control5DuplicadoFechaMontoItem[]
  >([])

  const [vistoCargando, setVistoCargando] = useState(false)

  const [vistoAplicandoPagoId, setVistoAplicandoPagoId] = useState<
    number | null
  >(null)

  const [ctrl15DialogOpen, setCtrl15DialogOpen] = useState(false)

  const [ctrl15PrestamoId, setCtrl15PrestamoId] = useState<number | null>(null)

  const [ctrl15Filas, setCtrl15Filas] = useState<
    Control15PagoSinAplicacionItem[]
  >([])

  const [ctrl15Cargando, setCtrl15Cargando] = useState(false)

  const [reaplicandoCascadaPid, setReaplicandoCascadaPid] = useState<
    number | null
  >(null)

  const [corrigiendoCtrl15, setCorrigiendoCtrl15] = useState(false)

  useEffect(() => {
    if (!puedeAuditoriaCartera) return
    let cancel = false
    void (async () => {
      try {
        const c =
          await auditoriaService.listarControlesConExcepcionesHistoricas()
        if (!cancel) {
          setControlesConExcHist(Array.isArray(c) ? c : [])
        }
      } catch {
        if (!cancel) {
          setControlesConExcHist([])
        }
      }
    })()
    return () => {
      cancel = true
    }
  }, [puedeAuditoriaCartera])

  const syncOcultosConItems = useCallback(
    async (list: PrestamoCarteraChequeo[]): Promise<Set<string>> => {
      const ids = [...new Set(list.map(r => r.prestamo_id))]
      if (ids.length === 0) {
        const empty = new Set<string>()
        setOcultosKeys(empty)
        return empty
      }
      try {
        const r = await auditoriaService.listarRevisionesOcultos(ids)
        const s = new Set(
          (r.ocultos || []).map(o => `${o.prestamo_id}:${o.codigo_control}`)
        )
        setOcultosKeys(s)
        return s
      } catch (e: unknown) {
        const empty = new Set<string>()
        setOcultosKeys(empty)
        const msg =
          e && typeof e === 'object' && 'message' in e
            ? String((e as { message?: string }).message)
            : 'Error al cargar revisiones en BD (tabla migrada?)'
        toast.error(msg)
        return empty
      }
    },
    []
  )

  const fetchLista = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!puedeAuditoriaCartera) {
        return
      }
      const silent = opts?.silent === true
      try {
        if (!silent) setLoading(true)

        const cheq = await auditoriaService.listarCarteraChequeos({
          skip: (page - 1) * pageSize,
          limit: pageSize,
          cedula: filtrosApi.cedula.trim() || undefined,
          prestamo_id: filtrosApi.prestamo_id,
          codigo_control: filtrosApi.codigo_control?.trim() || undefined,
          excluir_marcar_ok: !vistaMotorCrudo,
        })

        const nextItems = cheq.items || []
        const nextResumen = (cheq.resumen as Record<string, unknown>) || {}

        setItems(nextItems)
        setResumen(nextResumen)

        const exclSrv = nextResumen.excluye_marcar_ok === true
        const ocultos = exclSrv
          ? new Set<string>()
          : await syncOcultosConItems(nextItems)
        if (exclSrv) {
          setOcultosKeys(new Set())
        }
        saveCarteraSessionCache({
          items: nextItems,
          resumen: nextResumen,
          filtrosApi,
          page,
          filtroControlCodigo: filtrosApi.codigo_control?.trim() || '',
          ocultosKeys: [...ocultos],
          vista_motor_crudo: vistaMotorCrudo,
        })
      } catch (e: unknown) {
        const msg =
          e && typeof e === 'object' && 'message' in e
            ? String((e as { message?: string }).message)
            : 'Error al cargar auditoria de cartera'

        toast.error(msg)

        if (!silent) {
          setItems([])
          setResumen(null)
          setOcultosKeys(new Set())
        }
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [
      page,
      pageSize,
      filtrosApi,
      vistaMotorCrudo,
      syncOcultosConItems,
      puedeAuditoriaCartera,
    ]
  )

  const abrirDialogoVistoControl5 = useCallback(async (prestamoId: number) => {
    setVistoPrestamoId(prestamoId)
    setVistoDialogOpen(true)
    setVistoCargando(true)
    setVistoFilas([])
    try {
      const r =
        await auditoriaService.listarControl5DuplicadosPorPrestamo(prestamoId)
      setVistoFilas(Array.isArray(r.items) ? r.items : [])
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'No se pudo cargar la lista (solo administrador)'
      toast.error(msg)
      setVistoDialogOpen(false)
      setVistoPrestamoId(null)
    } finally {
      setVistoCargando(false)
    }
  }, [])

  const aplicarVistoControl5EnPago = useCallback(
    async (pagoId: number, prestamoId: number) => {
      setVistoAplicandoPagoId(pagoId)
      try {
        const out = await auditoriaService.aplicarControl5VistoPago(pagoId)
        toast.success(
          `Visto aplicado. Nuevo documento: ${out.numero_documento_nuevo} (sufijo _${out.sufijo_cuatro_digitos}; A=mismo crédito/carga, P=otro préstamo)`
        )
        const r =
          await auditoriaService.listarControl5DuplicadosPorPrestamo(prestamoId)
        setVistoFilas(Array.isArray(r.items) ? r.items : [])
        void fetchLista({ silent: true })
      } catch (e: unknown) {
        const msg =
          e && typeof e === 'object' && 'message' in e
            ? String((e as { message?: string }).message)
            : 'Error al aplicar Visto'
        toast.error(msg)
      } finally {
        setVistoAplicandoPagoId(null)
      }
    },
    [fetchLista]
  )

  const abrirDialogControl15 = useCallback(async (prestamoId: number) => {
    setCtrl15PrestamoId(prestamoId)
    setCtrl15DialogOpen(true)
    setCtrl15Cargando(true)
    setCtrl15Filas([])
    try {
      const r =
        await auditoriaService.listarControl15PagosSinAplicacionCuotas(
          prestamoId
        )
      setCtrl15Filas(Array.isArray(r.items) ? r.items : [])
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'No se pudo cargar el detalle (solo administrador)'
      toast.error(msg)
      setCtrl15DialogOpen(false)
      setCtrl15PrestamoId(null)
    } finally {
      setCtrl15Cargando(false)
    }
  }, [])

  const reaplicarCascadaUnPrestamo = useCallback(
    async (prestamoId: number) => {
      setReaplicandoCascadaPid(prestamoId)
      try {
        await prestamoService.reaplicarCascadaAplicacion(prestamoId)
        toast.success(`Cascada reaplicada en prestamo ${prestamoId}.`)
        void fetchLista({ silent: true })
        if (ctrl15DialogOpen && ctrl15PrestamoId === prestamoId) {
          const r =
            await auditoriaService.listarControl15PagosSinAplicacionCuotas(
              prestamoId
            )
          setCtrl15Filas(Array.isArray(r.items) ? r.items : [])
        }
      } catch (e: unknown) {
        const msg =
          e && typeof e === 'object' && 'message' in e
            ? String((e as { message?: string }).message)
            : 'Error al reaplicar cascada'
        toast.error(msg)
      } finally {
        setReaplicandoCascadaPid(null)
      }
    },
    [fetchLista, ctrl15DialogOpen, ctrl15PrestamoId]
  )

  /** Mientras la BD responde lento (p. ej. script masivo), no ocultar resumen ni tabla en cache. */
  const bloqueoListaCompleta = loading && items.length === 0

  const primeraCargaRef = useRef(true)
  const bootRef = useRef(boot)
  bootRef.current = boot

  useEffect(() => {
    const b = bootRef.current
    if (primeraCargaRef.current && b) {
      primeraCargaRef.current = false
      void fetchLista({ silent: true })
      return
    }
    primeraCargaRef.current = false
    void fetchLista()
  }, [fetchLista])

  const resetFiltrosUiYSesion = useCallback(() => {
    setCedulaInput('')
    setPrestamoInput('')
    setFiltrosApi({ cedula: '' })
    setPage(1)
    setHistorialOpen(false)
    setHistorialPid(null)
    setHistorialRows([])
  }, [])

  const recargarCompleta = useCallback(() => {
    resetFiltrosUiYSesion()
  }, [resetFiltrosUiYSesion])

  const aplicarFiltros = useCallback(() => {
    let pid: number | undefined
    const p = prestamoInput.trim()
    if (p) {
      const n = parseInt(p, 10)
      if (!Number.isFinite(n) || n < 1) {
        toast.error('ID de prestamo invalido')
        return
      }
      pid = n
    }
    setFiltrosApi(prev => ({
      ...prev,
      cedula: cedulaInput.trim(),
      prestamo_id: pid,
    }))
    setPage(1)
  }, [cedulaInput, prestamoInput])

  const ejecutarAhora = async () => {
    try {
      setRunning(true)

      const cheq = await auditoriaService.ejecutarCartera()

      resetFiltrosUiYSesion()

      const s = cheq.sincronizar_estado_cuotas
      const extra =
        s && typeof s.estados_actualizados === 'number'
          ? ` Estados de cuota alineados: ${s.estados_actualizados} fila(s).`
          : ''
      toast.success(`Auditoria ejecutada y metadatos actualizados.${extra}`)
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al ejecutar auditoria'

      toast.error(msg)
    } finally {
      setRunning(false)
    }
  }

  const alinearEstadosCuotas = async () => {
    try {
      setSyncingEstados(true)
      const r = await auditoriaService.sincronizarEstadosCuotasCartera()
      const n = r.estados_actualizados
      const s = r.cuotas_escaneadas
      toast.success(`Cuotas revisadas: ${s}. Estados actualizados en BD: ${n}.`)
      void fetchLista({ silent: true })
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al alinear estados de cuotas'
      toast.error(msg)
    } finally {
      setSyncingEstados(false)
    }
  }

  const exportarCsv = async () => {
    try {
      setExportando(true)
      const cheq = await auditoriaService.listarCarteraChequeos({
        skip: 0,
        limit: 5000,
        cedula: filtrosApi.cedula.trim() || undefined,
        prestamo_id: filtrosApi.prestamo_id,
        codigo_control: filtrosApi.codigo_control?.trim() || undefined,
        excluir_marcar_ok: !vistaMotorCrudo,
      })
      const header =
        'prestamo_id,cedula,nombres,estado_prestamo,codigo_control,titulo_control,detalle'
      const lines = [`\ufeff${header}`]
      for (const row of cheq.items || []) {
        for (const c of row.controles) {
          lines.push(
            [
              String(row.prestamo_id),
              csvEscapeCell(row.cedula || ''),
              csvEscapeCell(row.nombres || ''),
              csvEscapeCell(row.estado_prestamo || ''),
              csvEscapeCell(c.codigo),
              csvEscapeCell(c.titulo),
              csvEscapeCell(c.detalle || ''),
            ].join(',')
          )
        }
      }
      const blob = new Blob([lines.join('\r\n')], {
        type: 'text/csv;charset=utf-8',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `auditoria_cartera_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('CSV descargado (hasta 5000 prestamos con alerta).')
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al exportar CSV'
      toast.error(msg)
    } finally {
      setExportando(false)
    }
  }

  const servidorExcluyeMarcarOk = resumen?.excluye_marcar_ok === true

  const visibleRows = useMemo(() => {
    return items
      .map(row => ({
        ...row,
        controles: servidorExcluyeMarcarOk
          ? row.controles
          : row.controles.filter(
              c =>
                !ocultosKeys.has(controlDismissKey(row.prestamo_id, c.codigo))
            ),
      }))
      .filter(row => row.controles.length > 0)
  }, [items, ocultosKeys, servidorExcluyeMarcarOk])

  const conteosPorControlCodigo = useMemo(() => {
    const raw = resumen?.conteos_por_control
    if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
      return raw as Record<string, number>
    }
    return {}
  }, [resumen])

  const conteosEfectivosPorControl = useMemo(() => {
    const out: Record<string, number> = {}
    for (const def of AUDITORIA_CARTERA_CONTROLES_CATALOGO) {
      const c = def.codigo
      const fromR = conteosPorControlCodigo[c]
      const r =
        typeof fromR === 'number' && !Number.isNaN(fromR) ? fromR : undefined
      out[c] = r !== undefined ? r : 0
    }
    return out
  }, [conteosPorControlCodigo])

  const prestamosConAlertaNum = useMemo(() => {
    const raw = resumen?.prestamos_con_alerta
    if (raw == null || raw === '') return null
    const n = Number(raw)
    return Number.isNaN(n) ? null : n
  }, [resumen])

  const etiquetaControlFiltroSeleccion = useMemo(() => {
    const cod = filtrosApi.codigo_control?.trim()
    if (!cod) {
      const suf =
        prestamosConAlertaNum != null
          ? ` · ${etiquetaPrestamosConAlerta(prestamosConAlertaNum)}`
          : ''
      return `Todos los controles (cola completa)${suf}`
    }
    const def = AUDITORIA_CARTERA_CONTROLES_CATALOGO.find(d => d.codigo === cod)
    if (!def) return cod
    const cnt = conteosEfectivosPorControl[cod] ?? 0
    return `${def.n}. ${def.titulo} · ${etiquetaCasosControl(cnt)}`
  }, [
    filtrosApi.codigo_control,
    conteosEfectivosPorControl,
    prestamosConAlertaNum,
  ])

  const abrirDialogoExcepcion = (
    prestamoId: number,
    codigo: string,
    titulo: string
  ) => {
    setOkTarget({ prestamoId, codigo, titulo })
    setOkNota('')
    setOkDialogOpen(true)
  }

  const confirmarExcepcionOk = async () => {
    if (!okTarget) return
    const nota = okNota.trim()
    if (nota.length < NOTA_EXCEPCION_MIN_LEN) {
      toast.error(
        `Indique motivo de la excepcion (minimo ${NOTA_EXCEPCION_MIN_LEN} caracteres), ej. acuerdo con cliente o referencia interna.`
      )
      return
    }
    try {
      setOkSubmitting(true)
      await auditoriaService.crearRevisionCartera({
        prestamo_id: okTarget.prestamoId,
        codigo_control: okTarget.codigo,
        nota,
      })
      setOkDialogOpen(false)
      setOkTarget(null)
      setOkNota('')
      toast.success(
        'Excepcion guardada en bitacora. Deja de contar en la cola operativa (vista normal).'
      )
      void fetchLista({ silent: true })
      try {
        const c =
          await auditoriaService.listarControlesConExcepcionesHistoricas()
        setControlesConExcHist(Array.isArray(c) ? c : [])
      } catch {
        /* opcional */
      }
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al registrar revision'
      toast.error(msg)
    } finally {
      setOkSubmitting(false)
    }
  }

  const abrirDialogoRevocacion = (
    prestamoId: number,
    codigo: string,
    titulo: string
  ) => {
    setRevokeTarget({ prestamoId, codigo, titulo })
    setRevokeNota('')
    setRevokeDialogOpen(true)
  }

  const confirmarRevocacion = async () => {
    if (!revokeTarget) return
    const nota = revokeNota.trim()
    if (nota.length < NOTA_REVOCACION_MIN_LEN) {
      toast.error(
        `Indique motivo de la revocacion (minimo ${NOTA_REVOCACION_MIN_LEN} caracteres).`
      )
      return
    }
    try {
      setRevokeSubmitting(true)
      await auditoriaService.crearRevisionCartera({
        prestamo_id: revokeTarget.prestamoId,
        codigo_control: revokeTarget.codigo,
        tipo: 'REVOCAR_OK',
        nota,
      })
      setRevokeDialogOpen(false)
      setRevokeTarget(null)
      setRevokeNota('')
      toast.success(
        'Revocacion registrada. El caso vuelve a la cola operativa si el motor sigue en SI.'
      )
      void fetchLista({ silent: true })
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al revocar excepcion'
      toast.error(msg)
    } finally {
      setRevokeSubmitting(false)
    }
  }

  const descargarHistoricoExcel = async () => {
    const cod = exportCodigoHist.trim()
    if (!cod) {
      toast.error('Elija un control con excepciones en historico.')
      return
    }
    try {
      setExportandoHist(true)
      const blob = await auditoriaService.descargarRevisionesCarteraExcel(cod)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `auditoria_cartera_revisiones_${cod.replace(/[^a-zA-Z0-9_-]/g, '_')}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      toast.success('Descarga iniciada.')
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al exportar'
      toast.error(msg)
    } finally {
      setExportandoHist(false)
    }
  }

  const abrirHistorialRevisiones = async (pid: number) => {
    setHistorialPid(pid)
    setHistorialOpen(true)
    setHistorialLoading(true)
    setHistorialRows([])
    try {
      const rows = await auditoriaService.historialRevisionesCartera(pid, 100)
      setHistorialRows(Array.isArray(rows) ? rows : [])
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al cargar historial'
      toast.error(msg)
    } finally {
      setHistorialLoading(false)
    }
  }

  const totalListados = Number(
    resumen?.prestamos_listados_total ?? resumen?.prestamos_con_alerta ?? 0
  )

  const hayAlertas = totalListados > 0

  const totalPages = Math.max(1, Math.ceil(totalListados / pageSize))

  const hayDesajustePagosVsAplicado = useMemo(() => {
    return (conteosPorControlCodigo[COD_DESAJUSTE_PAGOS] ?? 0) > 0
  }, [conteosPorControlCodigo])

  const hayPagosSinAplicacion = useMemo(() => {
    return (conteosPorControlCodigo[COD_PAGOS_SIN_APLICACION] ?? 0) > 0
  }, [conteosPorControlCodigo])

  const corregirDesajustePagos = async () => {
    try {
      setCorrigiendo(true)
      const res = await auditoriaService.corregirCartera({
        sincronizar_estados: true,
        reaplicar_cascada_desajuste_pagos: true,
        max_reaplicaciones: 100,
      })
      resetFiltrosUiYSesion()
      const ok = (res.reaplicar_cascada || []).filter(
        (x: Record<string, unknown>) => x.ok === true
      ).length
      const fail = (res.reaplicar_cascada || []).length - ok
      const sync = res.sincronizar_estado_cuotas
      toast.success(
        `Correccion: cascada ${ok} prestamo(s) OK${fail ? `, ${fail} con error` : ''}.` +
          (sync && typeof sync.estados_actualizados === 'number'
            ? ` Estados sincronizados: ${sync.estados_actualizados}.`
            : '')
      )
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al corregir cartera'
      toast.error(msg)
    } finally {
      setCorrigiendo(false)
    }
  }

  const corregirSinAplicacionCuotas = async () => {
    try {
      setCorrigiendoCtrl15(true)
      const res = await auditoriaService.corregirCartera({
        sincronizar_estados: true,
        reaplicar_cascada_pagos_sin_aplicacion_cuotas: true,
        max_reaplicaciones: 100,
      })
      resetFiltrosUiYSesion()
      const ok = (res.reaplicar_cascada || []).filter(
        (x: Record<string, unknown>) => x.ok === true
      ).length
      const fail = (res.reaplicar_cascada || []).length - ok
      const sync = res.sincronizar_estado_cuotas
      toast.success(
        `Control 15: cascada ${ok} prestamo(s) OK${fail ? `, ${fail} con error` : ''}.` +
          (sync && typeof sync.estados_actualizados === 'number'
            ? ` Estados sincronizados: ${sync.estados_actualizados}.`
            : '')
      )
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al reaplicar cascada (control 15)'
      toast.error(msg)
    } finally {
      setCorrigiendoCtrl15(false)
    }
  }

  if (!puedeAuditoriaCartera) {
    return (
      <Card className="border-amber-200 bg-amber-50/40">
        <CardContent className="py-8 text-center text-sm text-slate-700">
          No tiene permisos para la auditoria de cartera. Esta seccion esta
          restringida a roles distintos de operativo / usuario(s) basico.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-slate-200/90 shadow-sm">
        <CardHeader className="space-y-1 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white py-3 sm:py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-800 text-white">
              <Filter className="h-4 w-4" aria-hidden />
            </div>
            <div>
              <CardTitle className="text-base text-slate-900">
                Consulta y controles de cartera
              </CardTitle>
              <p className="text-xs font-normal text-muted-foreground">
                Filtre por cedula, ID de prestamo o control; los conteos en el
                desplegable vienen del ultimo resumen de la lista cargada.
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-4">
          <div className="flex flex-col gap-3 rounded-md border border-slate-200 bg-slate-50/60 p-3 sm:flex-row sm:flex-wrap sm:items-end">
            <div className="min-w-[200px] flex-1">
              <Label
                htmlFor="auditoria-export-hist-control"
                className="text-xs font-medium text-slate-700"
              >
                Exportar historico de bitacora (Excel)
              </Label>
              <p className="mb-1.5 text-[11px] text-muted-foreground">
                Todos los eventos del control elegido (MARCAR_OK, REVOCAR_OK,
                etc.), con columna de snapshot JSON.
              </p>
              <Select
                value={exportCodigoHist || '__none__'}
                onValueChange={v =>
                  setExportCodigoHist(v === '__none__' ? '' : v)
                }
              >
                <SelectTrigger
                  id="auditoria-export-hist-control"
                  className="h-9 border-slate-200 bg-white"
                >
                  <SelectValue placeholder="Elija control" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Elija control...</SelectItem>
                  {controlesConExcHist.map(cod => (
                    <SelectItem key={cod} value={cod}>
                      {cod}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="shrink-0 gap-1"
              disabled={exportandoHist || !exportCodigoHist.trim()}
              onClick={() => void descargarHistoricoExcel()}
            >
              {exportandoHist ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Descargar Excel
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => recargarCompleta()}
              disabled={loading}
              title="Vuelve a pedir la lista al servidor (siempre lee la BD en tiempo real)."
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Recargar
            </Button>

            <Button
              size="sm"
              onClick={ejecutarAhora}
              disabled={running || loading}
              title="Recalcula controles desde la BD (motor objetivo) y guarda metadatos en configuracion. Igual criterio que el job 03:00; sin usar MARCAR_OK en esos totales."
            >
              {running ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Ejecutar ahora y guardar meta
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => void alinearEstadosCuotas()}
              disabled={syncingEstados || running || loading}
              title="Actualiza solo la columna cuotas.estado (vencimiento y pagos). Corrige el control estado_cuota_vs_calculo sin recorrer todo el motor ni guardar meta."
            >
              {syncingEstados ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Alinear estados de cuotas
            </Button>

            {esAdmin && hayDesajustePagosVsAplicado && !bloqueoListaCompleta ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void corregirDesajustePagos()}
                disabled={
                  corrigiendo ||
                  corrigiendoCtrl15 ||
                  running ||
                  syncingEstados ||
                  loading
                }
                title="Reaplica pagos en cascada en prestamos con alerta de suma pagos vs cuota_pagos, luego sincroniza estados de cuota."
              >
                {corrigiendo ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Corregir desajuste pagos (cascada)
              </Button>
            ) : null}

            {esAdmin && hayPagosSinAplicacion && !bloqueoListaCompleta ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void corregirSinAplicacionCuotas()}
                disabled={
                  corrigiendoCtrl15 ||
                  corrigiendo ||
                  running ||
                  syncingEstados ||
                  loading
                }
                title="Reaplica cascada en prestamos con control 15 en SI (sin cuota_pagos o saldo sin aplicar). Hasta 100 por ejecucion."
              >
                {corrigiendoCtrl15 ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Reaplicar cascada (control 15)
              </Button>
            ) : null}

            {hayAlertas && !bloqueoListaCompleta ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void exportarCsv()}
                disabled={exportando}
              >
                {exportando ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Exportar CSV
              </Button>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-12 lg:items-end">
            <div className="flex flex-col gap-1.5 sm:col-span-1 lg:col-span-2">
              <Label
                htmlFor="auditoria-cedula-filtro"
                className="text-xs font-medium text-slate-700"
              >
                Cedula (fragmento)
              </Label>
              <Input
                id="auditoria-cedula-filtro"
                type="search"
                placeholder="Ej. V12345678"
                value={cedulaInput}
                onChange={e => setCedulaInput(e.target.value)}
                autoComplete="off"
                className="h-9 border-slate-200"
              />
            </div>

            <div className="flex flex-col gap-1.5 sm:col-span-1 lg:col-span-2">
              <Label
                htmlFor="auditoria-prestamo-filtro"
                className="text-xs font-medium text-slate-700"
              >
                ID prestamo
              </Label>
              <Input
                id="auditoria-prestamo-filtro"
                inputMode="numeric"
                placeholder="Opcional"
                value={prestamoInput}
                onChange={e => setPrestamoInput(e.target.value)}
                autoComplete="off"
                className="h-9 border-slate-200"
              />
            </div>

            <div className="flex flex-col gap-1.5 sm:col-span-2 lg:col-span-5">
              <Label
                htmlFor="auditoria-control-filtro"
                className="text-xs font-medium text-slate-700"
              >
                Control a revisar
              </Label>
              <Select
                value={
                  filtrosApi.codigo_control?.trim()
                    ? filtrosApi.codigo_control.trim()
                    : VALOR_TODOS_CONTROLES
                }
                onValueChange={v => {
                  const cod = v === VALOR_TODOS_CONTROLES ? undefined : v
                  setFiltrosApi(prev => ({ ...prev, codigo_control: cod }))
                  setPage(1)
                }}
              >
                <SelectTrigger
                  id="auditoria-control-filtro"
                  className="h-9 border-slate-200"
                  disabled={loading}
                  title={etiquetaControlFiltroSeleccion}
                >
                  <SelectValue placeholder="Todos los controles" />
                </SelectTrigger>
                <SelectContent wide>
                  <SelectItem
                    value={VALOR_TODOS_CONTROLES}
                    className="w-max min-w-full whitespace-nowrap pr-10"
                  >
                    Todos los controles (cola completa)
                    {prestamosConAlertaNum != null ? (
                      <>
                        {' · '}
                        <ConteoPrestamosAlertaResaltado
                          n={prestamosConAlertaNum}
                        />
                      </>
                    ) : null}
                  </SelectItem>
                  {AUDITORIA_CARTERA_CONTROLES_CATALOGO.map(def => {
                    const cnt = conteosEfectivosPorControl[def.codigo] ?? 0
                    return (
                      <SelectItem
                        key={def.codigo}
                        value={def.codigo}
                        className="w-max min-w-full whitespace-nowrap pr-10"
                      >
                        {def.n}. {def.titulo} · <ConteoCasosResaltado n={cnt} />
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-wrap items-end gap-2 sm:col-span-2 lg:col-span-3">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={aplicarFiltros}
                disabled={loading}
              >
                Aplicar filtros
              </Button>
              <label
                className="flex cursor-pointer items-center gap-2 pb-0.5 text-xs text-slate-600"
                title="Incluye alertas cubiertas por excepcion (informe crudo); desactiva excluir_marcar_ok en la API."
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 rounded border-slate-300"
                  checked={vistaMotorCrudo}
                  onChange={e => setVistaMotorCrudo(e.target.checked)}
                />
                <span className="select-none">Ver motor completo</span>
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      {(() => {
        const cod = filtrosApi.codigo_control?.trim()
        if (!cod) return null
        const def = AUDITORIA_CARTERA_CONTROLES_CATALOGO.find(
          d => d.codigo === cod
        )
        if (!def || (!def.notaOperativa && !def.excepcionesReglas)) return null
        return (
          <div className="mb-4 flex flex-col gap-3">
            {def.notaOperativa ? (
              <AlertWithIcon
                variant="info"
                title={`Control ${def.n}: accion sugerida`}
                description={def.notaOperativa}
              />
            ) : null}
            {def.excepcionesReglas ? (
              <AlertWithIcon
                variant="warning"
                title={`Control ${def.n}: excepciones y alcance (Pagos / carga masiva)`}
              >
                <AlertDescription className="mt-1 whitespace-pre-line text-sm">
                  {def.excepcionesReglas}
                </AlertDescription>
              </AlertWithIcon>
            ) : null}
          </div>
        )
      })()}

      {hayAlertas && !bloqueoListaCompleta && totalPages > 1 ? (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            <ChevronLeft className="mr-1 h-4 w-4" />
            Anterior
          </Button>
          <span className="text-sm text-gray-600">
            Pagina <strong>{page}</strong> de <strong>{totalPages}</strong> (
            {pageSize} por pagina)
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={page >= totalPages || loading}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          >
            Siguiente
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        </div>
      ) : null}

      {bloqueoListaCompleta ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-12 text-gray-500">
              <Loader2 className="mr-2 h-6 w-6 animate-spin" />
              Analizando cartera...
            </div>
          </CardContent>
        </Card>
      ) : !hayAlertas ? (
        <p className="py-6 text-center text-sm text-gray-600">
          No hay prestamos con controles en SI segun estos criterios. La cartera
          esta alineada con lo que aqui se revisa, o no hay prestamos
          APROBADO/LIQUIDADO que cumplan el filtro.
        </p>
      ) : (
        <Card>
          <CardContent className="pt-6">
            {loading && items.length > 0 ? (
              <div
                className="mb-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50/90 px-3 py-2 text-sm text-amber-950"
                role="status"
              >
                <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                Actualizando lista desde la base de datos (puede tardar si hay
                carga pesada en el servidor). La tabla muestra la ultima
                respuesta recibida.
              </div>
            ) : null}
            {visibleRows.length === 0 ? (
              <p className="py-8 text-center text-gray-600">
                En esta pagina no quedan filas (paginacion o casos fuera de cola
                por aceptacion o motor ya en NO). Pulse{' '}
                <strong>Recargar</strong> o <strong>Ver motor completo</strong>{' '}
                para revisar el motor sin filtro operativo.
              </p>
            ) : (
              <div className="space-y-8">
                {visibleRows.map(row => (
                  <div
                    key={row.prestamo_id}
                    className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="text-lg font-semibold text-slate-900">
                          Prestamo #{row.prestamo_id}{' '}
                          <span className="text-slate-500">
                            · {row.nombres}
                          </span>
                        </div>

                        <div className="text-sm text-slate-600">
                          Cedula:{' '}
                          <span className="font-mono">{row.cedula}</span>
                          {' · '}
                          Estado:{' '}
                          <Badge variant="secondary">
                            {row.estado_prestamo}
                          </Badge>
                          {' · '}
                          <Link
                            className="text-blue-600 underline"
                            to={`/prestamos?prestamo_id=${row.prestamo_id}`}
                          >
                            Abrir prestamo
                          </Link>
                          {' · '}
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 text-blue-600 underline"
                            onClick={() =>
                              void abrirHistorialRevisiones(row.prestamo_id)
                            }
                          >
                            <FileText className="h-3.5 w-3.5" />
                            Historial revisiones (BD)
                          </button>
                        </div>
                      </div>
                    </div>

                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[280px]">
                            Control (alerta SI)
                          </TableHead>

                          <TableHead>Detalle</TableHead>

                          <TableHead className="w-[100px] text-right">
                            Accion
                          </TableHead>
                        </TableRow>
                      </TableHeader>

                      <TableBody>
                        {row.controles.map(c => {
                          const numCtrl = numeroControlAuditoriaCartera(
                            c.codigo
                          )

                          return (
                            <TableRow key={`${row.prestamo_id}-${c.codigo}`}>
                              <TableCell className="align-top text-sm font-medium">
                                {numCtrl != null ? (
                                  <span
                                    className="mr-2 inline-flex h-5 min-w-[1.35rem] items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-1 font-mono text-xs text-slate-700"
                                    title={`Control ${numCtrl}`}
                                  >
                                    {numCtrl}
                                  </span>
                                ) : null}
                                {c.titulo}
                              </TableCell>

                              <TableCell className="align-top text-sm text-slate-700">
                                {c.detalle || '-'}
                              </TableCell>

                              <TableCell className="text-right align-top">
                                <div className="flex flex-col items-end gap-1.5">
                                  {esAdmin &&
                                  c.codigo ===
                                    COD_CTRL_PAGOS_MISMO_DIA_MONTO ? (
                                    <Button
                                      type="button"
                                      variant="outline"
                                      size="sm"
                                      className="h-8 w-8 shrink-0 p-0"
                                      title="Visto (admin): autorizar duplicado legitimo; anexa _A#### o _P#### al documento y registra auditoria."
                                      aria-label={`Visto control 5 - prestamo ${row.prestamo_id}`}
                                      onClick={() =>
                                        void abrirDialogoVistoControl5(
                                          row.prestamo_id
                                        )
                                      }
                                    >
                                      <CircleCheck className="h-4 w-4 text-emerald-700" />
                                    </Button>
                                  ) : null}
                                  {esAdmin &&
                                  c.codigo === COD_PAGOS_SIN_APLICACION ? (
                                    <>
                                      <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        className="h-8 gap-1"
                                        title="Listar pagos operativos sin aplicacion completa a cuotas"
                                        onClick={() =>
                                          void abrirDialogControl15(
                                            row.prestamo_id
                                          )
                                        }
                                      >
                                        Ver pagos
                                      </Button>
                                      <Button
                                        type="button"
                                        variant="secondary"
                                        size="sm"
                                        className="h-8 gap-1"
                                        title="Reaplicar cascada solo en este prestamo"
                                        disabled={
                                          reaplicandoCascadaPid ===
                                          row.prestamo_id
                                        }
                                        onClick={() =>
                                          void reaplicarCascadaUnPrestamo(
                                            row.prestamo_id
                                          )
                                        }
                                      >
                                        {reaplicandoCascadaPid ===
                                        row.prestamo_id ? (
                                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                        ) : (
                                          <RefreshCw className="h-3.5 w-3.5" />
                                        )}
                                        Cascada
                                      </Button>
                                    </>
                                  ) : null}
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    className="gap-1"
                                    aria-label={`Aceptar excepcion para control: ${c.titulo}`}
                                    onClick={() =>
                                      abrirDialogoExcepcion(
                                        row.prestamo_id,
                                        c.codigo,
                                        c.titulo
                                      )
                                    }
                                  >
                                    <Check className="h-3.5 w-3.5" />
                                    Aceptar excepcion
                                  </Button>
                                  {ocultosKeys.has(
                                    controlDismissKey(row.prestamo_id, c.codigo)
                                  ) ? (
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="sm"
                                      className="gap-1 text-amber-900 hover:bg-amber-100/80"
                                      aria-label={`Revocar excepcion para control: ${c.titulo}`}
                                      onClick={() =>
                                        abrirDialogoRevocacion(
                                          row.prestamo_id,
                                          c.codigo,
                                          c.titulo
                                        )
                                      }
                                    >
                                      <RotateCcw className="h-3.5 w-3.5" />
                                      Revocar excepcion
                                    </Button>
                                  ) : null}
                                </div>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog
        open={vistoDialogOpen}
        onOpenChange={open => {
          setVistoDialogOpen(open)
          if (!open) {
            setVistoPrestamoId(null)
            setVistoFilas([])
            setVistoCargando(false)
            setVistoAplicandoPagoId(null)
          }
        }}
      >
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              Control 5 - Visto (duplicado fecha y monto)
            </DialogTitle>
          </DialogHeader>

          {vistoPrestamoId != null ? (
            <p className="text-sm text-slate-600">
              Prestamo <strong>#{vistoPrestamoId}</strong>. Aplique Visto al
              pago correcto: se anexa{' '}
              <code className="rounded bg-slate-100 px-1 text-xs">_A####</code>{' '}
              o{' '}
              <code className="rounded bg-slate-100 px-1 text-xs">_P####</code>{' '}
              (A mismo credito/carga, P otro prestamo; 4 digitos aleatorios) al
              numero de documento, queda registro en{' '}
              <span className="font-mono text-xs">
                auditoria_pago_control5_visto
              </span>{' '}
              y el pago deja de contar en este control.
            </p>
          ) : null}

          {vistoCargando ? (
            <div className="flex items-center gap-2 py-8 text-slate-600">
              <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
              Cargando pagos en duplicado...
            </div>
          ) : vistoFilas.length === 0 ? (
            <p className="py-6 text-sm text-slate-600">
              No hay pagos pendientes en duplicado para este prestamo.
            </p>
          ) : (
            <div className="max-h-[min(420px,70vh)] overflow-auto rounded border border-slate-200">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[72px]">ID</TableHead>

                    <TableHead>Fecha</TableHead>

                    <TableHead>Monto (USD)</TableHead>

                    <TableHead>Banco</TableHead>

                    <TableHead>Documento / ref.</TableHead>

                    <TableHead className="w-[100px] text-right">
                      Accion
                    </TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {vistoFilas.map(f => (
                    <TableRow key={f.pago_id}>
                      <TableCell className="font-mono text-xs">
                        {f.pago_id}
                      </TableCell>

                      <TableCell className="text-sm">
                        {f.fecha_pago ?? '-'}
                      </TableCell>

                      <TableCell className="text-sm tabular-nums">
                        {f.monto_pagado != null
                          ? f.monto_pagado.toFixed(2)
                          : '-'}
                      </TableCell>

                      <TableCell
                        className="max-w-[140px] truncate text-sm"
                        title={f.institucion_bancaria}
                      >
                        {f.institucion_bancaria || '-'}
                      </TableCell>

                      <TableCell
                        className="max-w-[220px] truncate font-mono text-xs"
                        title={
                          f.numero_documento || f.referencia_pago || undefined
                        }
                      >
                        {f.numero_documento || f.referencia_pago || '-'}
                      </TableCell>

                      <TableCell className="text-right">
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          disabled={vistoAplicandoPagoId != null}
                          onClick={() =>
                            vistoPrestamoId != null
                              ? void aplicarVistoControl5EnPago(
                                  f.pago_id,
                                  vistoPrestamoId
                                )
                              : undefined
                          }
                        >
                          {vistoAplicandoPagoId === f.pago_id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            'Visto'
                          )}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setVistoDialogOpen(false)}
            >
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={ctrl15DialogOpen}
        onOpenChange={open => {
          setCtrl15DialogOpen(open)
          if (!open) {
            setCtrl15PrestamoId(null)
            setCtrl15Filas([])
            setCtrl15Cargando(false)
          }
        }}
      >
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>
              Control 15 - Pagos sin aplicacion a cuotas
              {ctrl15PrestamoId != null
                ? ` · Prestamo #${ctrl15PrestamoId}`
                : ''}
            </DialogTitle>
          </DialogHeader>

          <p className="text-sm text-slate-600">
            Pagos operativos sin filas en{' '}
            <code className="text-xs">cuota_pagos</code> o con suma aplicada
            menor que el monto (tol. 0,02 USD). Tras reaplicar cascada, vuelva a
            abrir esta lista o recargue la auditoria.
          </p>

          {ctrl15Cargando ? (
            <div className="flex items-center gap-2 py-8 text-slate-600">
              <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
              Cargando pagos...
            </div>
          ) : ctrl15Filas.length === 0 ? (
            <p className="py-6 text-sm text-slate-600">
              No hay pagos en esta condicion para este prestamo (o ya se
              corrigio).
            </p>
          ) : (
            <div className="max-h-[55vh] overflow-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[90px]">Pago ID</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead className="text-right">Monto</TableHead>
                    <TableHead className="text-right">Aplicado</TableHead>
                    <TableHead className="text-right">Saldo</TableHead>
                    <TableHead>Motivo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ctrl15Filas.map(f => (
                    <TableRow key={f.pago_id}>
                      <TableCell className="font-mono text-sm">
                        <Link
                          className="text-blue-600 underline"
                          to={`/prestamos?prestamo_id=${f.prestamo_id}`}
                          title={`Pago ${f.pago_id}: abrir prestamo`}
                        >
                          {f.pago_id}
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm">
                        {f.fecha_pago ?? '-'}
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums">
                        {f.monto_pagado.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums">
                        {f.sum_monto_aplicado_cuotas.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right text-sm tabular-nums">
                        {f.saldo_sin_aplicar_usd.toFixed(2)}
                      </TableCell>
                      <TableCell className="max-w-[220px] text-xs text-slate-700">
                        {f.motivo}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <DialogFooter className="flex flex-wrap gap-2 sm:gap-0">
            {ctrl15PrestamoId != null ? (
              <Button
                type="button"
                variant="secondary"
                disabled={
                  ctrl15Cargando || reaplicandoCascadaPid === ctrl15PrestamoId
                }
                onClick={() =>
                  void reaplicarCascadaUnPrestamo(ctrl15PrestamoId)
                }
              >
                {reaplicandoCascadaPid === ctrl15PrestamoId ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Reaplicar cascada en este prestamo
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              onClick={() => setCtrl15DialogOpen(false)}
            >
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={okDialogOpen}
        onOpenChange={open => {
          setOkDialogOpen(open)
          if (!open) {
            setOkTarget(null)
            setOkNota('')
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Registrar excepcion aceptada</DialogTitle>
          </DialogHeader>

          {okTarget ? (
            <p className="text-sm text-slate-600">
              Prestamo <strong>#{okTarget.prestamoId}</strong> ·{' '}
              <strong>{okTarget.titulo}</strong>
            </p>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="auditoria-ok-nota">
              Motivo, acuerdo con cliente o referencia interna (minimo{' '}
              {NOTA_EXCEPCION_MIN_LEN} caracteres)
            </Label>

            <Textarea
              id="auditoria-ok-nota"
              value={okNota}
              onChange={e => setOkNota(e.target.value)}
              rows={4}
              placeholder="Ej. Acuerdo de pago firmado 12/03/2026; cliente J.Perez; no reaplicar cuota 5..."
              className="resize-y"
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOkDialogOpen(false)}
              disabled={okSubmitting}
            >
              Cancelar
            </Button>

            <Button
              type="button"
              onClick={() => void confirmarExcepcionOk()}
              disabled={okSubmitting}
            >
              {okSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Guardar en bitacora'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={historialOpen}
        onOpenChange={open => {
          setHistorialOpen(open)
          if (!open) {
            setHistorialPid(null)
            setHistorialRows([])
          }
        }}
      >
        <DialogContent className="max-h-[85vh] max-w-lg overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              Historial revisiones cartera
              {historialPid != null ? ` · Prestamo #${historialPid}` : ''}
            </DialogTitle>
          </DialogHeader>

          {historialLoading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-slate-600">
              <Loader2 className="h-5 w-5 animate-spin" />
              Cargando...
            </div>
          ) : historialRows.length === 0 ? (
            <p className="py-4 text-sm text-slate-600">
              Sin registros en bitacora para este prestamo.
            </p>
          ) : (
            <ul className="space-y-3 text-sm">
              {historialRows.map(h => (
                <li
                  key={h.id}
                  className="rounded-md border border-slate-200 bg-slate-50/80 p-3"
                >
                  <div className="font-mono text-xs text-slate-500">
                    {h.creado_en}
                  </div>
                  <div>
                    <strong>{h.codigo_control}</strong> · {h.tipo}
                  </div>
                  <div className="text-slate-600">
                    {h.usuario_email || `usuario_id=${h.usuario_id}`}
                  </div>
                  {h.nota ? (
                    <div className="mt-1 text-slate-700">Nota: {h.nota}</div>
                  ) : null}
                  {h.payload_snapshot &&
                  Object.keys(h.payload_snapshot).length > 0 ? (
                    <pre className="mt-2 max-h-40 overflow-auto rounded border border-slate-200 bg-white p-2 font-mono text-[10px] leading-snug text-slate-800">
                      {JSON.stringify(h.payload_snapshot, null, 2)}
                    </pre>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </DialogContent>
      </Dialog>

      <Dialog
        open={revokeDialogOpen}
        onOpenChange={open => {
          setRevokeDialogOpen(open)
          if (!open) {
            setRevokeTarget(null)
            setRevokeNota('')
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Revocar excepcion aceptada</DialogTitle>
          </DialogHeader>

          {revokeTarget ? (
            <p className="text-sm text-slate-600">
              Prestamo <strong>#{revokeTarget.prestamoId}</strong> ·{' '}
              <strong>{revokeTarget.titulo}</strong>
            </p>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="auditoria-revoke-nota">
              Motivo de la revocacion (minimo {NOTA_REVOCACION_MIN_LEN}{' '}
              caracteres)
            </Label>

            <Textarea
              id="auditoria-revoke-nota"
              value={revokeNota}
              onChange={e => setRevokeNota(e.target.value)}
              rows={4}
              placeholder="Ej. Se corrigen datos en sistema; la excepcion ya no aplica..."
              className="resize-y"
            />
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setRevokeDialogOpen(false)}
              disabled={revokeSubmitting}
            >
              Cancelar
            </Button>

            <Button
              type="button"
              onClick={() => void confirmarRevocacion()}
              disabled={revokeSubmitting}
            >
              {revokeSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Registrar revocacion'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
