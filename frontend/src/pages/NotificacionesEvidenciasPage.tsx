import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Loader2, RefreshCw, Search, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  evidenciasNotificacionService,
  type EvidenciaNotificacionItem,
} from '../services/evidenciasNotificacionService'
import { getErrorMessage } from '../types/errors'
import { useSimpleAuth } from '../store/simpleAuthStore'
import { isAdminRole, isManagerRole, isOperatorRole } from '../utils/rol'

const ETIQUETAS_FILTRO = [
  { value: '', label: 'Todas' },
  { value: 'DIA SIGUIENTE', label: 'DIA SIGUIENTE' },
  { value: '1 CUOTA', label: '1 CUOTA' },
  { value: '2 CUOTAS O MAS', label: '2 CUOTAS O MAS' },
] as const

const ESCANEAR_ETIQUETA_OPTS = [
  { value: 'todos', label: 'Todos (en orden)' },
  { value: 'DIA SIGUIENTE', label: 'DIA SIGUIENTE' },
  { value: '1 CUOTA', label: '1 CUOTA' },
  { value: '2 CUOTAS O MAS', label: '2 CUOTAS O MAS' },
] as const

const ESCANEAR_ORDEN_TODOS = [
  'DIA SIGUIENTE',
  '1 CUOTA',
  '2 CUOTAS O MAS',
] as const

function formatBytes(n: number): string {
  if (!n || n < 0) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function formatFecha(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString('es-VE')
  } catch {
    return iso
  }
}

export default function NotificacionesEvidenciasPage() {
  const { user } = useSimpleAuth()
  const puedeEscanear =
    isAdminRole(user?.rol) ||
    isManagerRole(user?.rol) ||
    isOperatorRole(user?.rol)
  const [qInput, setQInput] = useState('')
  const [appliedQ, setAppliedQ] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(25)
  const [etiqueta, setEtiqueta] = useState('')
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [scanning, setScanning] = useState(false)
  const [etiquetaEscanear, setEtiquetaEscanear] = useState('todos')
  const [scanProgress, setScanProgress] = useState('')
  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const [regeneratingId, setRegeneratingId] = useState<number | null>(null)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [deleting, setDeleting] = useState(false)

  const listQuery = useQuery({
    queryKey: [
      'notificaciones',
      'evidencias',
      appliedQ,
      page,
      pageSize,
      etiqueta,
      fechaDesde,
      fechaHasta,
    ],
    queryFn: () =>
      evidenciasNotificacionService.buscar(appliedQ, {
        page,
        pageSize,
        etiqueta: etiqueta || undefined,
        fechaDesde: fechaDesde || undefined,
        fechaHasta: fechaHasta || undefined,
      }),
    enabled: true,
  })

  const buscar = useCallback(() => {
    const q = qInput.trim()
    if (q.length === 1) {
      toast.error(
        'Indique cedula o email (minimo 2 caracteres), o deje vacio para ver recientes.'
      )
      return
    }
    setPage(1)
    setAppliedQ(q)
  }, [qInput])

  const verRecientes = useCallback(() => {
    setQInput('')
    setPage(1)
    setAppliedQ('')
  }, [])

  const escanear = useCallback(async () => {
    const cola =
      etiquetaEscanear === 'todos'
        ? [...ESCANEAR_ORDEN_TODOS]
        : [etiquetaEscanear]
    setScanning(true)
    setScanProgress('')
    let totalGuardados = 0
    let totalEtiquetados = 0
    let abortado = false
    try {
      for (const etiq of cola) {
        let agotada = false
        let ronda = 0
        while (!agotada) {
          ronda += 1
          setScanProgress(`${etiq} · lote ${ronda}`)
          const r = await evidenciasNotificacionService.escanear(etiq, 40)
          if (!r.ok) {
            toast.error(r.mensaje || r.error || `Error al escanear ${etiq}`)
            abortado = true
            break
          }
          totalGuardados += r.guardados || 0
          totalEtiquetados += r.etiquetados || 0
          if (r.mensaje) {
            toast.message(r.mensaje)
          }
          agotada = Boolean(r.etiqueta_agotada)
          // Seguridad: si no avanza y no agota, cortar
          if (
            !agotada &&
            (r.candidatos || 0) === 0 &&
            (r.ya_existentes || 0) === 0 &&
            !r.truncado
          ) {
            agotada = true
          }
          if (ronda >= 80) {
            toast.error(`Demasiados lotes en ${etiq}; revise Gmail/EVIDENCIA_OK`)
            abortado = true
            break
          }
        }
        if (abortado) break
        toast.success(`${etiq}: terminada`)
      }
      if (!abortado) {
        toast.success(
          `Escaneo completo. Guardados: ${totalGuardados}. Etiquetados EVIDENCIA_OK: ${totalEtiquetados}.`
        )
      }
      setPage(1)
      setAppliedQ('')
      setQInput('')
      await listQuery.refetch()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'Error al escanear')
    } finally {
      setScanning(false)
      setScanProgress('')
    }
  }, [etiquetaEscanear, listQuery])

  const descargar = useCallback(async (row: EvidenciaNotificacionItem) => {
    setDownloadingId(row.id)
    try {
      const etiquetaRow = (row.etiqueta_gmail || 'evidencia').replace(/\s+/g, '_')
      const email = (row.email_cliente || 'cliente').replace(/@/g, '_at_')
      await evidenciasNotificacionService.descargarPdf(
        row.id,
        `evidencia_${etiquetaRow}_${email}_${row.id}.pdf`
      )
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo descargar el PDF')
    } finally {
      setDownloadingId(null)
    }
  }, [])

  const regenerar = useCallback(async (row: EvidenciaNotificacionItem) => {
    setRegeneratingId(row.id)
    try {
      await evidenciasNotificacionService.regenerarPdf(row.id)
      toast.success('PDF regenerado desde Gmail (HTML)')
      await listQuery.refetch()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo regenerar el PDF')
    } finally {
      setRegeneratingId(null)
    }
  }, [listQuery])

  const items = listQuery.data?.items ?? []
  const totalPages = listQuery.data?.total_pages ?? 0

  useEffect(() => {
    setSelectedIds([])
  }, [appliedQ, page, pageSize, etiqueta, fechaDesde, fechaHasta])

  const pageIds = useMemo(() => items.map(r => r.id), [items])
  const allPageSelected =
    pageIds.length > 0 && pageIds.every(id => selectedIds.includes(id))
  const somePageSelected =
    pageIds.some(id => selectedIds.includes(id)) && !allPageSelected

  const toggleSelectAllPage = useCallback(() => {
    setSelectedIds(prev => {
      if (pageIds.length === 0) return prev
      if (pageIds.every(id => prev.includes(id))) {
        return prev.filter(id => !pageIds.includes(id))
      }
      const set = new Set(prev)
      pageIds.forEach(id => set.add(id))
      return Array.from(set)
    })
  }, [pageIds])

  const toggleSelectOne = useCallback((id: number) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }, [])

  const eliminarSeleccionados = useCallback(async () => {
    if (!selectedIds.length) {
      toast.error('Seleccione al menos una evidencia')
      return
    }
    if (
      !window.confirm(
        `Eliminar ${selectedIds.length} evidencia(s) seleccionada(s) de la base de datos? Esta accion no se puede deshacer (Gmail no se modifica).`
      )
    ) {
      return
    }
    setDeleting(true)
    try {
      const r = await evidenciasNotificacionService.eliminarSeleccionados(selectedIds)
      toast.success(`Eliminadas: ${r.deleted}`)
      setSelectedIds([])
      await listQuery.refetch()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo eliminar')
    } finally {
      setDeleting(false)
    }
  }, [selectedIds, listQuery])

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Evidencias</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Archivo PDF (correo + anexo) desde etiquetas Gmail en itmaster:{' '}
          DIA SIGUIENTE, 1 CUOTA, 2 CUOTAS O MAS (bajo NOTIFICACIONES). Busque por cedula o email.
        </p>
      </div>

      {puedeEscanear && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Escanear Gmail</CardTitle>
            <CardDescription>
              Elija una etiqueta o Todos. Escanea en orden hasta terminar (marca
              EVIDENCIA_OK). No usa cupo equitativo: una etiqueta completa antes
              de pasar a la siguiente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-muted-foreground">Etiqueta a escanear</label>
                <select
                  className="h-10 min-w-[220px] rounded-md border bg-background px-3 text-sm"
                  value={etiquetaEscanear}
                  disabled={scanning}
                  onChange={e => setEtiquetaEscanear(e.target.value)}
                >
                  {ESCANEAR_ETIQUETA_OPTS.map(opt => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <Button onClick={escanear} disabled={scanning}>
                {scanning ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Search className="mr-2 h-4 w-4" />
                )}
                {scanning ? 'Escaneando...' : 'Escanear'}
              </Button>
            </div>
            {scanning && scanProgress ? (
              <p className="text-sm text-muted-foreground">
                En curso: {scanProgress}. Continua hasta agotar la etiqueta (sin EVIDENCIA_OK).
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">
                Todos recorre DIA SIGUIENTE, luego 1 CUOTA, luego 2 CUOTAS O MAS.
                Cada una se escanea por lotes hasta que no queden pendientes.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Buscar evidencias</CardTitle>
          <CardDescription>
            Filtra por cedula o correo, o use Ver recientes para listar lo archivado.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
            <Input
              placeholder="Cedula o email..."
              value={qInput}
              onChange={e => setQInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') buscar()
              }}
              className="sm:max-w-md"
            />
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Etiqueta</label>
              <select
                className="h-10 rounded-md border bg-background px-3 text-sm"
                value={etiqueta}
                onChange={e => {
                  setEtiqueta(e.target.value)
                  setPage(1)
                }}
              >
                {ETIQUETAS_FILTRO.map(opt => (
                  <option key={opt.label} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Desde</label>
              <Input
                type="date"
                value={fechaDesde}
                onChange={e => {
                  setFechaDesde(e.target.value)
                  setPage(1)
                }}
                className="w-auto"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Hasta</label>
              <Input
                type="date"
                value={fechaHasta}
                onChange={e => {
                  setFechaHasta(e.target.value)
                  setPage(1)
                }}
                className="w-auto"
              />
            </div>
            <Button onClick={verRecientes} variant="outline" type="button">
              Ver recientes
            </Button>
            <Button onClick={buscar} variant="secondary">
              <Search className="mr-2 h-4 w-4" />
              Buscar
            </Button>
          </div>

          {listQuery.isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Buscando...
            </div>
          )}

          {listQuery.isError && (
            <p className="text-sm text-destructive">
              {getErrorMessage(listQuery.error) || 'Error al buscar'}
            </p>
          )}

          {listQuery.isSuccess && items.length === 0 && (
            <p className="text-sm text-muted-foreground">
              {appliedQ.trim()
                ? `No hay evidencias para "${appliedQ}". Escanee Gmail si aun no se archivaron.`
                : 'No hay evidencias archivadas aun. Pulse Escanear y almacenar.'}
            </p>
          )}

          {items.length > 0 && (
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="destructive"
                  disabled={selectedIds.length === 0 || deleting}
                  onClick={eliminarSeleccionados}
                >
                  {deleting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="mr-2 h-4 w-4" />
                  )}
                  Eliminar seleccionados
                  {selectedIds.length > 0 ? ` (${selectedIds.length})` : ''}
                </Button>
                {selectedIds.length > 0 && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={deleting}
                    onClick={() => setSelectedIds([])}
                  >
                    Limpiar seleccion
                  </Button>
                )}
              </div>
              <div className="overflow-x-auto rounded-md border">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b bg-muted/40">
                  <tr>
                    <th className="px-3 py-2 font-medium w-10">
                      <input
                        type="checkbox"
                        aria-label="Seleccionar todos en esta pagina"
                        checked={allPageSelected}
                        ref={el => {
                          if (el) el.indeterminate = somePageSelected
                        }}
                        onChange={toggleSelectAllPage}
                      />
                    </th>
                    <th className="px-3 py-2 font-medium">Etiqueta</th>
                    <th className="px-3 py-2 font-medium">Email</th>
                    <th className="px-3 py-2 font-medium">Cedula</th>
                    <th className="px-3 py-2 font-medium">Fecha</th>
                    <th className="px-3 py-2 font-medium">Anexo</th>
                    <th className="px-3 py-2 font-medium">Tamano</th>
                    <th className="px-3 py-2 font-medium">PDF</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map(row => (
                    <tr key={row.id} className="border-b last:border-0">
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          aria-label={`Seleccionar evidencia ${row.id}`}
                          checked={selectedIds.includes(row.id)}
                          onChange={() => toggleSelectOne(row.id)}
                        />
                      </td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {row.etiqueta_gmail}
                      </td>
                      <td className="px-3 py-2">{row.email_cliente}</td>
                      <td className="px-3 py-2">{row.cedula || '-'}</td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {formatFecha(row.fecha_mensaje || row.fecha_registro)}
                      </td>
                      <td className="px-3 py-2">
                        {row.tiene_anexo
                          ? row.fuente_anexo || 'si'
                          : 'no'}
                      </td>
                      <td className="px-3 py-2">
                        {formatBytes(row.pdf_tamano_bytes)}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={downloadingId === row.id || regeneratingId === row.id}
                            onClick={() => descargar(row)}
                          >
                            {downloadingId === row.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Download className="h-4 w-4" />
                            )}
                            <span className="ml-2">Descargar</span>
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            disabled={regeneratingId === row.id || downloadingId === row.id}
                            onClick={() => regenerar(row)}
                            title="Volver a generar el PDF con el HTML original de Gmail"
                          >
                            {regeneratingId === row.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCw className="h-4 w-4" />
                            )}
                            <span className="ml-2">Regenerar</span>
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                <p className="text-xs text-muted-foreground">
                  {listQuery.data?.total ?? 0} resultado(s)
                  {totalPages > 1
                    ? ` · pagina ${page} de ${totalPages}`
                    : ''}
                </p>
                {totalPages > 1 && (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={page <= 1 || listQuery.isFetching}
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                    >
                      Anterior
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={page >= totalPages || listQuery.isFetching}
                      onClick={() => setPage(p => p + 1)}
                    >
                      Siguiente
                    </Button>
                  </div>
                )}
              </div>
            </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
