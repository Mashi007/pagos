import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { ComponentType } from 'react'

import {
  Briefcase,
  Calendar,
  Car,
  CreditCard,
  DollarSign,
  Download,
  FileText,
  Key,
  Loader2,
  Settings,
  User,
  Users,
} from 'lucide-react'

import { toast } from 'sonner'

/** Icono Lucide compatible con la versión del proyecto (sin tipo `LucideIcon`). */
type DescripcionIcon = ComponentType<{
  className?: string
  'aria-hidden'?: boolean
}>

import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'

import { cn, formatCurrency, formatDate } from '../../utils'

import { lineasFiniquitoColumna } from '../../utils/prestamoFiniquitoDisplay'

import {
  finiquitoAdminRevisionDatos,
  finiquitoRevisionDatos,
  type FiniquitoRevisionDatosResponse,
} from '../../services/finiquitoService'
import {
  descargarRevisionCuotasExcel,
  descargarRevisionPagosExcel,
} from '../../utils/finiquitoRevisionExcelExport'

/** Contenedor del área de datos bajo pestañas (flex consume alto del modal). */
const PANEL_SCROLL =
  'flex min-h-0 flex-1 flex-col overflow-hidden sm:min-h-[min(58vh,520px)]'

/** Tabla densa tipo back-office; cabecera oscura fija al hacer scroll. */
const TABLE_SHELL =
  'min-h-0 flex-1 overflow-auto rounded-md border border-slate-300 bg-white shadow-sm'

const thFin =
  'h-7 whitespace-nowrap bg-slate-800 px-2 py-0.5 text-left text-[11px] font-semibold uppercase tracking-wide text-white'

const tdFin = 'px-2 py-1 align-middle text-[11px] text-slate-900 tabular-nums'

const trFinEven = 'border-b border-slate-200 bg-white hover:bg-slate-100/90'

const trFinOdd =
  'border-b border-slate-200 bg-slate-50/90 hover:bg-slate-100/90'

/** Claves mostradas en Descripción (mismo conjunto de negocio que antes). */
type DescripcionCampoKey =
  | 'cedula'
  | 'id'
  | 'analista'
  | 'cliente_id'
  | 'cuota_periodo'
  | 'fecha_aprobacion'
  | 'fecha_registro'
  | 'modalidad_pago'
  | 'nombres'
  | 'producto'
  | 'total_financiamiento'

const DESCRIPCION_GRUPOS: {
  titulo: string
  subtitulo?: string
  icon: DescripcionIcon
  keys: readonly DescripcionCampoKey[]
}[] = [
  {
    titulo: 'Cliente y producto',
    subtitulo: 'Identificación y bien financiado',
    icon: User,
    keys: ['cedula', 'nombres', 'cliente_id', 'producto', 'fecha_registro'],
  },
  {
    titulo: 'Condiciones del crédito',
    subtitulo: 'Montos y forma de pago',
    icon: Briefcase,
    keys: ['id', 'cuota_periodo', 'modalidad_pago', 'total_financiamiento'],
  },
  {
    titulo: 'Gestión y aprobación',
    subtitulo: 'Responsable y fechas clave',
    icon: Settings,
    keys: ['analista', 'fecha_aprobacion'],
  },
]

function iconoCampoDescripcion(key: DescripcionCampoKey): DescripcionIcon {
  switch (key) {
    case 'cedula':
      return CreditCard
    case 'id':
    case 'cliente_id':
      return Key
    case 'nombres':
      return User
    case 'producto':
      return Car
    case 'fecha_registro':
    case 'fecha_aprobacion':
      return Calendar
    case 'cuota_periodo':
    case 'total_financiamiento':
      return DollarSign
    case 'modalidad_pago':
      return Briefcase
    case 'analista':
      return Users
    default:
      return FileText
  }
}

function esMontoDescripcion(key: DescripcionCampoKey): boolean {
  return key === 'cuota_periodo' || key === 'total_financiamiento'
}

const PRESTAMO_CAMPO_LABEL: Record<string, string> = {
  id: 'ID préstamo',
  cliente_id: 'ID cliente',
  cedula: 'Cédula',
  nombres: 'Nombres',
  total_financiamiento: 'Total financiamiento',
  fecha_requerimiento: 'Fecha requerimiento',
  modalidad_pago: 'Modalidad de pago',
  numero_cuotas: 'Número de cuotas',
  cuota_periodo: 'Cuota / periodo',
  tasa_interes: 'Tasa interés',
  fecha_base_calculo: 'Fecha base cálculo',
  producto: 'Producto',
  estado: 'Estado préstamo',
  fecha_liquidado: 'Fecha liquidado',
  usuario_proponente: 'Usuario proponente',
  usuario_aprobador: 'Usuario aprobador',
  observaciones: 'Observaciones',
  fecha_registro: 'Fecha registro',
  fecha_aprobacion: 'Fecha aprobación',
  fecha_actualizacion: 'Fecha actualización',
  concesionario: 'Concesionario',
  analista: 'Analista',
  modelo_vehiculo: 'Modelo vehículo',
  usuario_autoriza: 'Usuario autoriza',
  valor_activo: 'Valor activo',
  requiere_revision: 'Requiere revisión',
  concesionario_id: 'ID concesionario',
  analista_id: 'ID analista',
  modelo_vehiculo_id: 'ID modelo vehículo',
}

function modalidadLabel(v: unknown): string {
  const s = String(v || '')
  if (s === 'MENSUAL') return 'Mensual'
  if (s === 'QUINCENAL') return 'Quincenal'
  if (s === 'SEMANAL') return 'Semanal'
  return s || '-'
}

function estadoPrestamoBadgeClass(estado: string): string {
  const e = (estado || '').toUpperCase()
  if (e === 'APROBADO') return 'bg-green-100 text-green-800'
  if (e === 'LIQUIDADO') return 'bg-gray-100 text-gray-800'
  if (e === 'EN_REVISION') return 'bg-yellow-100 text-yellow-800'
  if (e === 'DESISTIMIENTO') return 'bg-orange-100 text-orange-900'
  if (e === 'RECHAZADO') return 'bg-red-100 text-red-800'
  if (e === 'EVALUADO') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-800'
}

function estadoPrestamoLabel(estado: string): string {
  const e = (estado || '').toUpperCase()
  if (e === 'APROBADO') return 'Aprobado'
  if (e === 'LIQUIDADO') return 'Liquidado'
  if (e === 'EN_REVISION') return 'En Revisión'
  if (e === 'DESISTIMIENTO') return 'Desistimiento'
  if (e === 'RECHAZADO') return 'Rechazado'
  if (e === 'EVALUADO') return 'Evaluado'
  if (e === 'DRAFT') return 'Borrador'
  return estado || '-'
}

function formatearValorPrestamoCampo(key: string, val: unknown): string {
  if (val === null || val === undefined) return '-'
  if (key === 'modalidad_pago') return modalidadLabel(val)
  if (key === 'requiere_revision') return val ? 'Sí' : 'No'
  if (
    key === 'total_financiamiento' ||
    key === 'cuota_periodo' ||
    key === 'tasa_interes' ||
    key === 'valor_activo'
  ) {
    const n = Number(val)
    return Number.isFinite(n) ? formatCurrency(n) : String(val)
  }
  if (
    key.includes('fecha') ||
    key === 'fecha_registro' ||
    key === 'fecha_aprobacion' ||
    key === 'fecha_actualizacion'
  ) {
    const s = String(val)
    if (!s) return '-'
    try {
      return formatDate(s)
    } catch {
      return s
    }
  }
  return String(val)
}

type Props = {
  open: boolean
  casoId: number | null
  onOpenChange: (open: boolean) => void
  mode?: 'public' | 'admin'
}

export function FiniquitoRevisionDialog({
  open,
  casoId,
  onOpenChange,
  mode = 'public',
}: Props) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<FiniquitoRevisionDatosResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tabRevision, setTabRevision] = useState('descripcion')
  const [excelExport, setExcelExport] = useState<'cuotas' | 'pagos' | null>(
    null
  )

  useEffect(() => {
    if (!open || casoId == null) {
      setData(null)
      setError(null)
      setTabRevision('descripcion')
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    const promise =
      mode === 'admin'
        ? finiquitoAdminRevisionDatos(casoId)
        : finiquitoRevisionDatos(casoId)
    promise
      .then(res => {
        if (!cancelled) setData(res)
      })
      .catch(e => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Error al cargar revision')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, casoId, mode])

  const prestamosItems = data?.prestamos?.prestamos ?? []
  const pagosItems = data?.pagos?.pagos ?? []
  const cuotasItems = data?.cuotas_caso ?? []
  const prestamoCaso = data?.prestamo_caso
  const cedulaDescripcion = (
    (data?.cedula ?? prestamoCaso?.cedula ?? '') as string
  ).trim()

  const pagosTotal = data?.pagos?.total ?? 0
  const pagosPerPage = data?.pagos?.per_page ?? 100

  const handleExcelCuotas = async () => {
    if (!cuotasItems.length) {
      toast.error('No hay cuotas para exportar')
      return
    }
    setExcelExport('cuotas')
    try {
      await descargarRevisionCuotasExcel(cuotasItems, {
        casoId,
        cedula: data?.cedula,
        prestamoId: data?.prestamo_id_finiquito ?? null,
      })
      toast.success('Excel de cuotas descargado')
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'Error al exportar cuotas a Excel'
      )
    } finally {
      setExcelExport(null)
    }
  }

  const handleExcelPagos = async () => {
    if (!pagosItems.length) {
      toast.error('No hay pagos para exportar')
      return
    }
    setExcelExport('pagos')
    try {
      await descargarRevisionPagosExcel(pagosItems, {
        casoId,
        cedula: data?.cedula,
      })
      toast.success('Excel de pagos descargado')
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'Error al exportar pagos a Excel'
      )
    } finally {
      setExcelExport(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          'flex !h-[92vh] !max-h-[92vh] w-[min(96rem,calc(100vw-0.75rem))] !max-w-[min(96rem,calc(100vw-0.75rem))] flex-col gap-0 overflow-hidden !p-0 shadow-xl',
          'rounded-lg border border-slate-300 bg-white'
        )}
      >
        <DialogHeader className="mb-0 shrink-0 border-b border-slate-300 bg-gradient-to-r from-slate-100 to-slate-50 px-4 py-2.5 sm:px-5">
          <DialogTitle className="text-left text-base font-bold tracking-tight text-[#1e3a5f]">
            Detalle del caso - préstamo, cuotas, movimientos
          </DialogTitle>
          <DialogDescription className="text-left text-xs leading-relaxed text-slate-800">
            <span className="font-mono font-semibold text-slate-900">
              {data?.cedula ?? '…'}
            </span>
            {data?.prestamo_id_finiquito != null && (
              <>
                {' '}
                <span className="text-slate-500">|</span> Crédito{' '}
                <span className="font-mono font-semibold text-slate-900">
                  #{data.prestamo_id_finiquito}
                </span>
              </>
            )}
            <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
              Solo lectura
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-100/60 px-2 pb-2 pt-1.5 sm:px-3">
          {loading && (
            <div className="flex flex-1 items-center justify-center py-12">
              <Loader2 className="h-9 w-9 animate-spin text-slate-500" />
            </div>
          )}
          {!loading && error && (
            <div className="m-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
              {error}
            </div>
          )}
          {!loading && !error && data && (
            <Tabs
              value={tabRevision}
              onValueChange={setTabRevision}
              className="flex min-h-0 flex-1 flex-col"
            >
              <TabsList className="mb-1.5 h-auto shrink-0 flex-wrap justify-start gap-0.5 rounded-md border border-slate-300 bg-slate-200/90 p-0.5 sm:h-9 sm:flex-nowrap">
                <TabsTrigger
                  value="descripcion"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Descripción
                </TabsTrigger>
                <TabsTrigger
                  value="prestamos"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Resumen Préstamo
                </TabsTrigger>
                <TabsTrigger
                  value="cuotas"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Cuotas
                </TabsTrigger>
                <TabsTrigger
                  value="pagos"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Pagos
                </TabsTrigger>
              </TabsList>

              <TabsContent
                value="descripcion"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div
                  className={cn(
                    PANEL_SCROLL,
                    'gap-3 rounded-md border border-slate-300 bg-slate-100/40 p-3'
                  )}
                >
                  {!prestamoCaso && !cedulaDescripcion ? (
                    <p className="text-xs text-slate-600">
                      No hay préstamo asociado a este caso.
                    </p>
                  ) : (
                    <div className="flex min-h-0 flex-col gap-3 overflow-y-auto">
                      {prestamoCaso?.estado != null &&
                        String(prestamoCaso.estado).trim() !== '' && (
                          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                            <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                              Estado del préstamo
                            </span>
                            <Badge
                              className={cn(
                                'border-0 text-xs font-semibold',
                                estadoPrestamoBadgeClass(
                                  String(prestamoCaso.estado)
                                )
                              )}
                            >
                              {estadoPrestamoLabel(String(prestamoCaso.estado))}
                            </Badge>
                          </div>
                        )}
                      {prestamoCaso
                        ? (() => {
                            const lineas = lineasFiniquitoColumna({
                              estado: String(prestamoCaso.estado ?? ''),
                              estado_gestion_finiquito:
                                prestamoCaso.estado_gestion_finiquito != null
                                  ? String(prestamoCaso.estado_gestion_finiquito)
                                  : null,
                              finiquito_tramite_fecha_limite:
                                prestamoCaso.finiquito_tramite_fecha_limite !=
                                null
                                  ? String(
                                      prestamoCaso.finiquito_tramite_fecha_limite
                                    )
                                  : null,
                            })
                            if (!lineas) return null
                            return (
                              <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm">
                                <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                                  Finiquito
                                </span>
                                <p className="mt-1 text-sm font-semibold text-slate-900">
                                  {lineas.primary}
                                </p>
                                {lineas.secondary ? (
                                  <p className="mt-1 text-xs text-slate-600">
                                    {lineas.secondary}
                                  </p>
                                ) : null}
                              </div>
                            )
                          })()
                        : null}
                      <div className="grid min-h-0 grid-cols-1 gap-3 lg:grid-cols-3">
                        {DESCRIPCION_GRUPOS.map(grupo => {
                          const IconGrupo = grupo.icon
                          const filas = grupo.keys
                            .map(key => {
                              if (key !== 'cedula' && !prestamoCaso) {
                                return null
                              }
                              const raw =
                                key === 'cedula'
                                  ? cedulaDescripcion || null
                                  : prestamoCaso
                                    ? prestamoCaso[key as string]
                                    : undefined
                              const empty =
                                raw === null ||
                                raw === undefined ||
                                (typeof raw === 'string' && raw.trim() === '')
                              const label =
                                PRESTAMO_CAMPO_LABEL[key] ?? String(key)
                              const IconCampo = iconoCampoDescripcion(key)
                              const monto = esMontoDescripcion(key)
                              const mono =
                                key === 'cedula' ||
                                key === 'id' ||
                                key === 'cliente_id'
                              return (
                                <div
                                  key={key}
                                  className="flex gap-2.5 border-b border-slate-100 py-2.5 first:pt-0 last:border-b-0 last:pb-0"
                                >
                                  <IconCampo
                                    className="mt-0.5 h-4 w-4 shrink-0 text-slate-400"
                                    aria-hidden
                                  />
                                  <div className="min-w-0 flex-1">
                                    <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                                      {label}
                                    </div>
                                    <div
                                      className={cn(
                                        'mt-1 break-words text-sm font-semibold leading-snug text-slate-900',
                                        mono && 'font-mono text-[13px]',
                                        monto &&
                                          'text-right tabular-nums text-[#0f5132]'
                                      )}
                                    >
                                      {empty
                                        ? '-'
                                        : formatearValorPrestamoCampo(key, raw)}
                                    </div>
                                  </div>
                                </div>
                              )
                            })
                            .filter(Boolean)
                          if (filas.length === 0) return null
                          return (
                            <div
                              key={grupo.titulo}
                              className="flex min-h-0 flex-col rounded-lg border border-slate-200 bg-white shadow-sm"
                            >
                              <div className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white px-3 py-2.5">
                                <div className="flex items-center gap-2">
                                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[#1e3a5f]/10 text-[#1e3a5f]">
                                    <IconGrupo
                                      className="h-4 w-4"
                                      aria-hidden
                                    />
                                  </span>
                                  <div>
                                    <h3 className="text-xs font-bold tracking-tight text-[#1e3a5f]">
                                      {grupo.titulo}
                                    </h3>
                                    {grupo.subtitulo ? (
                                      <p className="text-[10px] text-slate-500">
                                        {grupo.subtitulo}
                                      </p>
                                    ) : null}
                                  </div>
                                </div>
                              </div>
                              <div className="flex flex-col px-3 pb-1 pt-0">
                                {filas}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent
                value="prestamos"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div
                  className={cn(
                    PANEL_SCROLL,
                    'gap-2 rounded-md border border-slate-300 bg-slate-100/40 p-3'
                  )}
                >
                  <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-sm">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#1e3a5f]/10 text-[#1e3a5f]">
                        <Briefcase className="h-4 w-4" aria-hidden />
                      </span>
                      <div className="min-w-0">
                        <p className="text-xs font-bold tracking-tight text-[#1e3a5f]">
                          Préstamos del titular
                        </p>
                        <p className="text-[10px] leading-snug text-slate-500">
                          Histórico vinculado a la cédula del caso. La fila del
                          crédito en revisión va resaltada.
                        </p>
                      </div>
                    </div>
                    <span className="shrink-0 rounded bg-slate-100 px-2 py-1 font-mono text-[11px] font-semibold text-slate-700">
                      {prestamosItems.length}{' '}
                      {prestamosItems.length === 1 ? 'registro' : 'registros'}
                    </span>
                  </div>

                  <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-slate-200 bg-white shadow-sm">
                    <Table className="text-xs">
                      <TableHeader className="sticky top-0 z-20 shadow-sm">
                        <TableRow className="border-0 hover:bg-transparent">
                          <TableHead className={thFin}>Cliente</TableHead>
                          <TableHead className={thFin}>Cédula</TableHead>
                          <TableHead className={cn(thFin, 'text-right')}>
                            Financiamiento
                          </TableHead>
                          <TableHead className={thFin}>Modalidad</TableHead>
                          <TableHead className={cn(thFin, 'text-center')}>
                            Cuotas
                          </TableHead>
                          <TableHead className={thFin}>Estado</TableHead>
                          <TableHead className={thFin}>Aprobación</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {prestamosItems.length === 0 ? (
                          <TableRow>
                            <TableCell
                              colSpan={7}
                              className={cn(
                                tdFin,
                                'py-10 text-center text-slate-500'
                              )}
                            >
                              No hay préstamos listados para esta cédula.
                            </TableCell>
                          </TableRow>
                        ) : (
                          prestamosItems.map(
                            (p: Record<string, unknown>, idx) => {
                              const esPrestamoCaso =
                                data.prestamo_id_finiquito != null &&
                                Number(p.id) ===
                                  Number(data.prestamo_id_finiquito)
                              return (
                                <TableRow
                                  key={`p-${String(p.id)}`}
                                  className={cn(
                                    esPrestamoCaso &&
                                      'border-l-[3px] border-l-[#1e3a5f] bg-[#1e3a5f]/5',
                                    !esPrestamoCaso &&
                                      (idx % 2 === 0 ? trFinEven : trFinOdd)
                                  )}
                                >
                                  <TableCell
                                    className={cn(
                                      tdFin,
                                      'max-w-[min(200px,28vw)] font-medium'
                                    )}
                                  >
                                    <div className="flex flex-col gap-1">
                                      <span className="break-words leading-snug">
                                        {String(
                                          p.nombres ??
                                            p.nombre_cliente ??
                                            `Cliente #${p.cliente_id ?? '-'}`
                                        )}
                                      </span>
                                      {esPrestamoCaso ? (
                                        <Badge
                                          className="w-fit border-0 bg-[#1e3a5f] text-[9px] font-bold uppercase tracking-wide text-white"
                                          title="Crédito asociado a este caso finiquito"
                                        >
                                          Caso actual
                                        </Badge>
                                      ) : null}
                                    </div>
                                  </TableCell>
                                  <TableCell
                                    className={cn(
                                      tdFin,
                                      'font-mono text-[10px] text-slate-800'
                                    )}
                                  >
                                    {String(
                                      p.cedula ?? p.cedula_cliente ?? '-'
                                    )}
                                  </TableCell>
                                  <TableCell
                                    className={cn(
                                      tdFin,
                                      'text-right tabular-nums'
                                    )}
                                  >
                                    <span className="font-semibold text-[#0f5132]">
                                      {formatCurrency(
                                        Number(p.total_financiamiento ?? 0)
                                      )}
                                    </span>
                                  </TableCell>
                                  <TableCell
                                    className={cn(tdFin, 'text-slate-800')}
                                  >
                                    {modalidadLabel(p.modalidad_pago)}
                                  </TableCell>
                                  <TableCell
                                    className={cn(
                                      tdFin,
                                      'text-center font-medium tabular-nums'
                                    )}
                                  >
                                    {p.numero_cuotas != null
                                      ? String(p.numero_cuotas)
                                      : '-'}
                                  </TableCell>
                                  <TableCell className={tdFin}>
                                    <Badge
                                      className={cn(
                                        'border-0 text-[10px] font-semibold',
                                        estadoPrestamoBadgeClass(
                                          String(p.estado ?? '')
                                        )
                                      )}
                                    >
                                      {estadoPrestamoLabel(
                                        String(p.estado ?? '')
                                      )}
                                    </Badge>
                                  </TableCell>
                                  <TableCell
                                    className={cn(
                                      tdFin,
                                      'whitespace-nowrap text-slate-800'
                                    )}
                                  >
                                    {p.fecha_aprobacion ? (
                                      <span className="inline-flex items-center gap-1">
                                        <Calendar
                                          className="h-3.5 w-3.5 shrink-0 text-slate-400"
                                          aria-hidden
                                        />
                                        {formatDate(String(p.fecha_aprobacion))}
                                      </span>
                                    ) : (
                                      '-'
                                    )}
                                  </TableCell>
                                </TableRow>
                              )
                            }
                          )
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              </TabsContent>

              <TabsContent
                value="cuotas"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
                  <div className="flex shrink-0 justify-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="gap-1.5 border-slate-300 font-semibold text-[#1e3a5f]"
                      disabled={
                        excelExport !== null || cuotasItems.length === 0
                      }
                      title="Descargar plan de cuotas en Excel (.xlsx)"
                      onClick={() => void handleExcelCuotas()}
                    >
                      {excelExport === 'cuotas' ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      ) : (
                        <Download className="h-4 w-4" aria-hidden />
                      )}
                      Excel
                    </Button>
                  </div>
                  <div className={TABLE_SHELL}>
                    <Table className="text-xs">
                      <TableHeader className="sticky top-0 z-20 shadow-sm">
                        <TableRow className="border-0 hover:bg-transparent">
                          <TableHead className={thFin}>Nº</TableHead>
                          <TableHead className={thFin}>Venc.</TableHead>
                          <TableHead className={thFin}>F. pago</TableHead>
                          <TableHead className={thFin}>Cuota</TableHead>
                          <TableHead className={thFin}>Capital</TableHead>
                          <TableHead className={thFin}>Int.</TableHead>
                          <TableHead className={thFin}>Pagado</TableHead>
                          <TableHead className={thFin}>Saldo cap.</TableHead>
                          <TableHead className={thFin}>Estado</TableHead>
                          <TableHead className={thFin}>Pago</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {cuotasItems.length === 0 ? (
                          <TableRow>
                            <TableCell
                              colSpan={10}
                              className={cn(
                                tdFin,
                                'text-center text-slate-500'
                              )}
                            >
                              Sin cuotas para el préstamo del caso.
                            </TableCell>
                          </TableRow>
                        ) : (
                          cuotasItems.map((c: Record<string, unknown>, idx) => (
                            <TableRow
                              key={`cu-${String(c.id)}`}
                              className={idx % 2 === 0 ? trFinEven : trFinOdd}
                            >
                              <TableCell
                                className={cn(
                                  tdFin,
                                  'font-semibold text-slate-800'
                                )}
                              >
                                {String(c.numero_cuota ?? '')}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'whitespace-nowrap')}
                              >
                                {c.fecha_vencimiento
                                  ? formatDate(String(c.fecha_vencimiento))
                                  : '-'}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'whitespace-nowrap')}
                              >
                                {c.fecha_pago
                                  ? formatDate(String(c.fecha_pago))
                                  : '-'}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {formatCurrency(Number(c.monto_cuota ?? 0))}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {formatCurrency(Number(c.monto_capital ?? 0))}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {formatCurrency(Number(c.monto_interes ?? 0))}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {formatCurrency(Number(c.total_pagado ?? 0))}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {formatCurrency(
                                  Number(c.saldo_capital_final ?? 0)
                                )}
                              </TableCell>
                              <TableCell
                                className={cn(
                                  tdFin,
                                  'font-medium uppercase text-slate-800'
                                )}
                              >
                                {String(c.estado ?? '')}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'font-mono text-[10px]')}
                              >
                                {c.pago_id != null ? String(c.pago_id) : '-'}
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              </TabsContent>

              <TabsContent
                value="pagos"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-slate-300 bg-white shadow-sm">
                  <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-b border-slate-200 bg-slate-50/80 px-2 py-1.5">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="gap-1.5 border-slate-300 font-semibold text-[#1e3a5f]"
                      disabled={excelExport !== null || pagosItems.length === 0}
                      title={
                        pagosTotal > pagosPerPage
                          ? `Exporta los ${pagosPerPage} pagos visibles en esta vista (total ${pagosTotal} en sistema)`
                          : 'Descargar pagos en Excel (.xlsx)'
                      }
                      onClick={() => void handleExcelPagos()}
                    >
                      {excelExport === 'pagos' ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      ) : (
                        <Download className="h-4 w-4" aria-hidden />
                      )}
                      Excel
                    </Button>
                  </div>
                  <div className="min-h-0 flex-1 overflow-auto">
                    <Table className="text-xs">
                      <TableHeader className="sticky top-0 z-20 shadow-sm">
                        <TableRow className="border-0 hover:bg-transparent">
                          <TableHead className={thFin}>ID</TableHead>
                          <TableHead className={thFin}>Cédula</TableHead>
                          <TableHead className={thFin}>Créd.</TableHead>
                          <TableHead className={thFin}>Est.</TableHead>
                          <TableHead className={thFin}>Notas</TableHead>
                          <TableHead className={thFin}>Monto</TableHead>
                          <TableHead className={thFin}>Fecha</TableHead>
                          <TableHead className={thFin}>Doc.</TableHead>
                          <TableHead className={thFin}>Comprobante</TableHead>
                          <TableHead className={thFin}>Conc.</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {pagosItems.length === 0 ? (
                          <TableRow>
                            <TableCell
                              colSpan={10}
                              className={cn(
                                tdFin,
                                'text-center text-slate-500'
                              )}
                            >
                              Sin pagos en esta página.
                            </TableCell>
                          </TableRow>
                        ) : (
                          pagosItems.map((p: Record<string, unknown>, idx) => (
                            <TableRow
                              key={`pay-${String(p.id)}`}
                              className={idx % 2 === 0 ? trFinEven : trFinOdd}
                            >
                              <TableCell
                                className={cn(tdFin, 'font-mono text-[10px]')}
                              >
                                {String(p.id ?? '')}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'font-mono text-[10px]')}
                              >
                                {String(p.cedula_cliente ?? '')}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {p.prestamo_id != null
                                  ? String(p.prestamo_id)
                                  : '-'}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {String(p.estado ?? '')}
                              </TableCell>
                              <TableCell
                                className={cn(
                                  tdFin,
                                  'max-w-[160px] truncate text-left'
                                )}
                                title={String(p.notas ?? '')}
                              >
                                {p.notas != null &&
                                String(p.notas).trim() !== ''
                                  ? String(p.notas)
                                  : '-'}
                              </TableCell>
                              <TableCell className={cn(tdFin, 'font-semibold')}>
                                {formatCurrency(Number(p.monto_pagado ?? 0))}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'whitespace-nowrap')}
                              >
                                {p.fecha_pago
                                  ? formatDate(String(p.fecha_pago))
                                  : '-'}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {String(p.numero_documento ?? '')}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {(() => {
                                  const rid = p.pago_reportado_id
                                  const idNum =
                                    rid != null && rid !== ''
                                      ? Number(rid)
                                      : NaN
                                  if (
                                    Number.isFinite(idNum) &&
                                    !Number.isNaN(idNum)
                                  ) {
                                    return (
                                      <Link
                                        to={`/cobros/pagos-reportados/${idNum}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 font-semibold text-[#1e3a5f] underline-offset-2 hover:underline"
                                        title="Abrir detalle en Pagos reportados (imagen / comprobante)"
                                      >
                                        <FileText
                                          className="h-3.5 w-3.5 shrink-0"
                                          aria-hidden
                                        />
                                        Ver
                                      </Link>
                                    )
                                  }
                                  return (
                                    <span className="text-slate-500">
                                      No disponible
                                    </span>
                                  )
                                })()}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {p.conciliado ? 'Sí' : 'No'}
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                  {pagosTotal > pagosPerPage && (
                    <p className="shrink-0 border-t border-slate-300 bg-slate-100 px-2 py-1.5 text-[10px] text-slate-700">
                      Total {pagosTotal} pagos; vista limitada a {pagosPerPage}.
                      Histórico completo en módulo Pagos.
                    </p>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          )}
        </div>

        <div className="flex shrink-0 justify-end border-t border-slate-300 bg-slate-100 px-4 py-2 sm:px-5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="border-slate-400 font-semibold text-[#1e3a5f]"
            onClick={() => onOpenChange(false)}
          >
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
