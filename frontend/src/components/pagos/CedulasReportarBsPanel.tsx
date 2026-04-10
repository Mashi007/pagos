import { useState, useEffect, useRef } from 'react'
import {
  FileSpreadsheet,
  Search,
  CheckCircle,
  XCircle,
  Plus,
  Trash2,
  Upload,
  Loader2,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { ListPaginationBar } from '../../components/ui/ListPaginationBar'
import { pagoService } from '../../services/pagoService'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'
import { cn } from '../../utils'

const PAGE_SIZE = 10

const CARACAS_TZ = 'America/Caracas'

function formatCreadoEn(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleString('es-VE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: CARACAS_TZ,
  })
}

export type CedulasReportarBsPanelProps = {
  /** Si es false, no se muestra la carga masiva por Excel (p. ej. en /pagos/pago-bs). */
  showExcelUpload?: boolean
}

/**
 * Lista blanca de cédulas que pueden reportar en Bs (RapiCredit Cobros / Infopagos).
 * Antes vivía arriba de PagosList; también se usa en la página dedicada «Pago Bs.».
 */
export function CedulasReportarBsPanel({
  showExcelUpload = true,
}: CedulasReportarBsPanelProps) {
  const [cedulasReportarBsTotal, setCedulasReportarBsTotal] = useState<
    number | null
  >(null)
  const [isUploadingCedulasBs, setIsUploadingCedulasBs] = useState(false)
  const [isAgregandoCedulaBs, setIsAgregandoCedulaBs] = useState(false)
  const [isEliminandoCedulaBs, setIsEliminandoCedulaBs] = useState(false)
  const [nuevaCedulaBs, setNuevaCedulaBs] = useState('')
  const [consultaCedulaBs, setConsultaCedulaBs] = useState('')
  const [consultaCedulaBsResultado, setConsultaCedulaBsResultado] = useState<{
    en_lista: boolean
    cedula_normalizada: string | null
    total_en_lista: number
  } | null>(null)
  const [isConsultandoCedulaBs, setIsConsultandoCedulaBs] = useState(false)
  const fileInputCedulasBsRef = useRef<HTMLInputElement>(null)

  const [listaPage, setListaPage] = useState(1)
  const [listaItems, setListaItems] = useState<
    { cedula: string; creado_en: string | null }[]
  >([])
  const [listaLoading, setListaLoading] = useState(true)
  const [listaError, setListaError] = useState<string | null>(null)
  const [listaRefreshTick, setListaRefreshTick] = useState(0)

  const bumpLista = (opts?: { resetToFirstPage?: boolean }) => {
    if (opts?.resetToFirstPage) setListaPage(1)
    setListaRefreshTick(t => t + 1)
  }

  useEffect(() => {
    let cancelled = false
    setListaLoading(true)
    setListaError(null)
    ;(async () => {
      try {
        const r = await pagoService.getCedulasReportarBs({
          page: listaPage,
          page_size: PAGE_SIZE,
        })
        if (cancelled) return
        setCedulasReportarBsTotal(r.total)
        if (r.items.length === 0 && r.total > 0) {
          setListaPage(p => (p > 1 ? p - 1 : p))
          if (listaPage > 1) return
        }
        setListaItems(r.items)
      } catch {
        if (!cancelled) {
          setListaError('No se pudo cargar la lista.')
          setListaItems([])
          setCedulasReportarBsTotal(0)
        }
      } finally {
        if (!cancelled) setListaLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [listaPage, listaRefreshTick])

  const totalLista = cedulasReportarBsTotal ?? 0
  const totalPagesLista =
    totalLista === 0 ? 0 : Math.ceil(totalLista / PAGE_SIZE)

  const sectionClass =
    'rounded-xl border border-slate-200/80 bg-white/90 p-4 shadow-sm ring-1 ring-slate-900/5 sm:p-5'

  return (
    <Card
      className={cn(
        'overflow-hidden rounded-2xl border-slate-200/90 bg-white shadow-lg shadow-slate-200/40',
        'ring-1 ring-slate-900/[0.04]'
      )}
    >
      <CardHeader
        className={cn(
          'space-y-4 border-b border-slate-100 bg-gradient-to-br from-[#1e67eb]/[0.07] via-white to-slate-50/90',
          'pb-5 pt-6 sm:pt-7'
        )}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 gap-3.5">
            <div
              className={cn(
                'flex h-12 w-12 shrink-0 items-center justify-center rounded-xl',
                'bg-[#1e67eb]/10 ring-1 ring-[#1e67eb]/15'
              )}
              aria-hidden
            >
              <FileSpreadsheet
                className="h-6 w-6 text-[#1e67eb]"
                strokeWidth={2}
              />
            </div>
            <div className="min-w-0 space-y-1">
              <CardTitle className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
                Cédulas que pueden reportar en Bs
              </CardTitle>
              <p className="text-sm font-medium text-slate-500">
                Bolívares · RapiCredit Cobros e Infopagos
              </p>
            </div>
          </div>
          {cedulasReportarBsTotal !== null ? (
            <div
              className={cn(
                'flex shrink-0 items-baseline gap-2 rounded-full border border-slate-200/90',
                'bg-white/90 px-4 py-2 shadow-sm backdrop-blur-sm'
              )}
            >
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                En lista
              </span>
              <span
                className="text-2xl font-bold tabular-nums leading-none text-[#1e67eb]"
                aria-live="polite"
              >
                {cedulasReportarBsTotal}
              </span>
            </div>
          ) : null}
        </div>
        <CardDescription className="text-sm leading-relaxed text-slate-600">
          Solo las cédulas de esta lista pueden elegir «Bs» en Cobros e
          Infopagos. Consulte una cédula, revise el registro paginado y, si
          aplica,{' '}
          {showExcelUpload ? (
            <>
              cargue un Excel con columna <strong>cedula</strong> o agregue
              manualmente
            </>
          ) : (
            <>agregue o elimine manualmente</>
          )}
          .
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 pb-6 pt-6 sm:space-y-7">
        <section className={sectionClass} aria-labelledby="cedulas-bs-consulta">
          <div className="mb-4 flex items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
              <Search className="h-4 w-4" strokeWidth={2} />
            </div>
            <div>
              <h2
                id="cedulas-bs-consulta"
                className="text-base font-semibold text-slate-900"
              >
                Consultar cédula
              </h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Compruebe si ya está autorizada para pagos en bolívares.
              </p>
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-stretch">
            <Input
              placeholder="Ej: V12345678"
              value={consultaCedulaBs}
              onChange={e => {
                setConsultaCedulaBs(e.target.value)
                setConsultaCedulaBsResultado(null)
              }}
              className={cn(
                'h-10 w-full min-w-0 border-slate-200 bg-white sm:min-w-[220px] sm:max-w-md sm:flex-1',
                'focus-visible:border-[#1e67eb] focus-visible:ring-[#1e67eb]/20'
              )}
              maxLength={20}
              aria-label="Cédula a consultar"
              onKeyDown={e =>
                e.key === 'Enter' &&
                (e.preventDefault(),
                document.getElementById('btn-consultar-cedula-bs')?.click())
              }
            />
            <Button
              id="btn-consultar-cedula-bs"
              type="button"
              size="sm"
              className={cn(
                'h-10 shrink-0 border-0 bg-[#1e67eb] text-white shadow-sm hover:bg-[#1858cc]',
                'sm:px-5'
              )}
              disabled={isConsultandoCedulaBs || !consultaCedulaBs.trim()}
              onClick={async () => {
                const ced = consultaCedulaBs.trim()
                if (!ced) return
                setIsConsultandoCedulaBs(true)
                try {
                  const res = await pagoService.consultarCedulaReportarBs(ced)
                  setConsultaCedulaBsResultado(res)
                  setCedulasReportarBsTotal(res.total_en_lista)
                } catch (err) {
                  setConsultaCedulaBsResultado(null)
                  toast.error(getErrorMessage(err))
                } finally {
                  setIsConsultandoCedulaBs(false)
                }
              }}
            >
              {isConsultandoCedulaBs ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              Consultar
            </Button>
          </div>
          {consultaCedulaBsResultado ? (
            <div
              className={cn(
                'mt-4 rounded-lg border px-4 py-3',
                consultaCedulaBsResultado.en_lista
                  ? 'border-emerald-200/90 bg-emerald-50/80'
                  : 'border-amber-200/90 bg-amber-50/80'
              )}
              role="status"
            >
              {consultaCedulaBsResultado.en_lista ? (
                <p className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
                  <CheckCircle className="h-4 w-4 shrink-0" />
                  En lista: puede elegir Bs
                </p>
              ) : (
                <p className="flex items-center gap-2 text-sm font-semibold text-amber-900">
                  <XCircle className="h-4 w-4 shrink-0" />
                  No está en la lista
                </p>
              )}
              {consultaCedulaBsResultado.cedula_normalizada ? (
                <p className="mt-1.5 text-xs text-slate-600">
                  Normalizada:{' '}
                  <span className="font-mono font-semibold text-slate-800">
                    {consultaCedulaBsResultado.cedula_normalizada}
                  </span>
                </p>
              ) : null}
            </div>
          ) : null}
        </section>

        <section className={sectionClass} aria-labelledby="cedulas-bs-lista">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                <FileSpreadsheet className="h-4 w-4" strokeWidth={2} />
              </div>
              <div>
                <h2
                  id="cedulas-bs-lista"
                  className="text-base font-semibold text-slate-900"
                >
                  Registros en el sistema
                </h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  Orden: más reciente primero · {PAGE_SIZE} por página
                </p>
              </div>
            </div>
          </div>
          {listaError ? (
            <div
              className="rounded-lg border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-800"
              role="alert"
            >
              {listaError}
            </div>
          ) : null}
          {!listaLoading && totalLista === 0 && !listaError ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/50 px-6 py-12 text-center">
              <Plus
                className="mb-3 h-10 w-10 text-slate-300"
                strokeWidth={1.5}
                aria-hidden
              />
              <p className="text-sm font-medium text-slate-700">
                No hay cédulas en la lista
              </p>
              <p className="mt-1 max-w-sm text-xs text-slate-500">
                {showExcelUpload
                  ? 'Agregue una cédula o cargue un Excel para comenzar.'
                  : 'Agregue una cédula con el formulario de abajo para comenzar.'}
              </p>
            </div>
          ) : null}
          {listaLoading ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-slate-100 bg-slate-50/40 py-14">
              <Loader2
                className="h-8 w-8 animate-spin text-[#1e67eb]"
                aria-hidden
              />
              <p className="mt-3 text-sm font-medium text-slate-600">
                Cargando lista…
              </p>
            </div>
          ) : null}
          {!listaLoading && totalLista > 0 ? (
            <>
              <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-200 hover:bg-transparent">
                      <TableHead className="h-11 w-[42%] bg-slate-50/95 text-xs font-semibold uppercase tracking-wide text-slate-600">
                        Cédula
                      </TableHead>
                      <TableHead className="h-11 bg-slate-50/95 text-xs font-semibold uppercase tracking-wide text-slate-600">
                        Fecha de alta
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {listaItems.map((row, idx) => (
                      <TableRow
                        key={row.cedula}
                        className={cn(
                          'border-slate-100 transition-colors',
                          idx % 2 === 1 ? 'bg-slate-50/35' : 'bg-white',
                          'hover:bg-[#1e67eb]/[0.04]'
                        )}
                      >
                        <TableCell className="py-3 font-mono text-sm font-semibold text-slate-900">
                          {row.cedula}
                        </TableCell>
                        <TableCell className="py-3 text-sm text-slate-600">
                          {formatCreadoEn(row.creado_en)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              {totalPagesLista > 0 ? (
                <ListPaginationBar
                  className="mt-5"
                  page={listaPage}
                  totalPages={totalPagesLista}
                  onPageChange={setListaPage}
                  subtitle={`${totalLista} cédula(s) en total`}
                />
              ) : null}
            </>
          ) : null}
        </section>

        <section className={sectionClass} aria-labelledby="cedulas-bs-acciones">
          <h2
            id="cedulas-bs-acciones"
            className="mb-4 text-base font-semibold text-slate-900"
          >
            {showExcelUpload
              ? 'Agregar, eliminar o importar'
              : 'Agregar o eliminar'}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div
              className={cn(
                'flex flex-col gap-3 rounded-xl border border-emerald-200/70 bg-emerald-50/20 p-4',
                'ring-1 ring-emerald-900/[0.04]'
              )}
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800/90">
                Alta
              </p>
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                <Input
                  placeholder="Ej: V12345678"
                  value={nuevaCedulaBs}
                  onChange={e => setNuevaCedulaBs(e.target.value)}
                  className="h-10 min-w-0 border-slate-200 bg-white sm:max-w-[200px]"
                  maxLength={20}
                  aria-label="Cédula a agregar a la lista"
                  onKeyDown={e =>
                    e.key === 'Enter' &&
                    (e.preventDefault(),
                    document.getElementById('btn-agregar-cedula-bs')?.click())
                  }
                />
                <Button
                  id="btn-agregar-cedula-bs"
                  type="button"
                  variant="outline"
                  size="sm"
                  className={cn(
                    'h-10 border-emerald-300 bg-white text-emerald-900',
                    'hover:bg-emerald-50'
                  )}
                  disabled={isAgregandoCedulaBs || !nuevaCedulaBs.trim()}
                  onClick={async () => {
                    const ced = nuevaCedulaBs.trim()
                    if (!ced) return
                    setIsAgregandoCedulaBs(true)
                    try {
                      const res = await pagoService.addCedulaReportarBs(ced)
                      setCedulasReportarBsTotal(res.total)
                      setNuevaCedulaBs('')
                      bumpLista({ resetToFirstPage: true })
                      toast.success(res.mensaje)
                    } catch (err) {
                      toast.error(getErrorMessage(err))
                    } finally {
                      setIsAgregandoCedulaBs(false)
                    }
                  }}
                >
                  {isAgregandoCedulaBs ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="mr-2 h-4 w-4" />
                  )}
                  Agregar cédula
                </Button>
              </div>
            </div>
            <div
              className={cn(
                'flex flex-col gap-3 rounded-xl border border-red-200/70 bg-red-50/15 p-4',
                'ring-1 ring-red-900/[0.04]'
              )}
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-red-800/90">
                Baja
              </p>
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                <Input
                  placeholder="Cédula a eliminar"
                  value={consultaCedulaBs}
                  onChange={e => setConsultaCedulaBs(e.target.value)}
                  className="h-10 min-w-0 border-slate-200 bg-white sm:max-w-[200px]"
                  maxLength={20}
                  aria-label="Cédula a eliminar de la lista"
                  onKeyDown={e =>
                    e.key === 'Enter' &&
                    (e.preventDefault(),
                    document.getElementById('btn-eliminar-cedula-bs')?.click())
                  }
                />
                <Button
                  id="btn-eliminar-cedula-bs"
                  type="button"
                  variant="outline"
                  size="sm"
                  className={cn(
                    'h-10 border-red-300 bg-white text-red-900',
                    'hover:bg-red-50'
                  )}
                  disabled={isEliminandoCedulaBs || !consultaCedulaBs.trim()}
                  onClick={async () => {
                    const ced = consultaCedulaBs.trim()
                    if (!ced) return
                    setIsEliminandoCedulaBs(true)
                    try {
                      const res = await pagoService.removeCedulaReportarBs(ced)
                      setCedulasReportarBsTotal(res.total)
                      setConsultaCedulaBs('')
                      bumpLista()
                      toast.success(res.mensaje)
                    } catch (err) {
                      toast.error(getErrorMessage(err))
                    } finally {
                      setIsEliminandoCedulaBs(false)
                    }
                  }}
                >
                  {isEliminandoCedulaBs ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="mr-2 h-4 w-4" />
                  )}
                  Eliminar cédula
                </Button>
              </div>
            </div>
          </div>
          {showExcelUpload ? (
            <div className="mt-4 flex flex-col gap-2 border-t border-slate-200/80 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-slate-600">
                Importación masiva reemplaza la lista completa.
              </p>
              <div className="flex shrink-0 items-center gap-2">
                <input
                  ref={fileInputCedulasBsRef}
                  type="file"
                  accept=".xlsx,.xls"
                  className="hidden"
                  onChange={async e => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    setIsUploadingCedulasBs(true)
                    try {
                      const res =
                        await pagoService.uploadCedulasReportarBs(file)
                      setCedulasReportarBsTotal(res.total)
                      bumpLista({ resetToFirstPage: true })
                      toast.success(res.mensaje)
                      if (fileInputCedulasBsRef.current)
                        fileInputCedulasBsRef.current.value = ''
                    } catch (err) {
                      toast.error(getErrorMessage(err))
                    } finally {
                      setIsUploadingCedulasBs(false)
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className={cn(
                    'h-10 border-slate-300 bg-white text-slate-800',
                    'hover:bg-slate-50'
                  )}
                  onClick={() => fileInputCedulasBsRef.current?.click()}
                  disabled={isUploadingCedulasBs}
                >
                  {isUploadingCedulasBs ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="mr-2 h-4 w-4" />
                  )}
                  Cargar Excel (columna cedula)
                </Button>
              </div>
            </div>
          ) : null}
        </section>
      </CardContent>
    </Card>
  )
}
