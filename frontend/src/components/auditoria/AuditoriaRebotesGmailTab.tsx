import { useCallback, useEffect, useState } from 'react'

import { Download, Loader2, Mail, Play, Trash2 } from 'lucide-react'

import { toast } from 'sonner'

import { useSimpleAuth } from '../../store/simpleAuthStore'
import { isAdminRole } from '../../utils/rol'

import { AlertDescription, AlertWithIcon } from '../ui/alert'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'

import {
  auditoriaService,
  type ReboteGmailItem,
  type ProcesarRebotesGmailResponse,
  type RebotesGmailKpis,
} from '../../services/auditoriaService'

const PAGE_SIZE = 50

const KPI_CERO: RebotesGmailKpis = {
  total_escaneados: 0,
  total_guardados: 0,
  total_omitidos: 0,
  total_sin_correo: 0,
  total_sin_cedula: 0,
  total_cedula_duplicada: 0,
  total_ya_existentes: 0,
  total_mal: 0,
  total_lleno: 0,
  total_temporal: 0,
  total_otro: 0,
  total_corridas: 0,
  ultima_corrida_at: null,
  registros_actuales: 0,
  actual_mal: 0,
  actual_lleno: 0,
  actual_temporal: 0,
  actual_otro: 0,
}

function obsBadgeClass(obs: string): string {
  switch ((obs || '').toLowerCase()) {
    case 'mal':
      return 'bg-red-100 text-red-800'
    case 'lleno':
      return 'bg-amber-100 text-amber-900'
    case 'temporal':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

function KpiTile({
  label,
  value,
  hint,
}: {
  label: string
  value: number | string
  hint?: string
}) {
  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        {hint ? (
          <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p>
        ) : null}
      </CardContent>
    </Card>
  )
}

export function AuditoriaRebotesGmailTab() {
  const { user } = useSimpleAuth()
  const esAdmin = isAdminRole(user?.rol)

  const [items, setItems] = useState<ReboteGmailItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [procesando, setProcesando] = useState(false)
  const [borrando, setBorrando] = useState(false)
  const [kpis, setKpis] = useState<RebotesGmailKpis>(KPI_CERO)
  const [ultimoProceso, setUltimoProceso] =
    useState<ProcesarRebotesGmailResponse | null>(null)

  const cargarKpis = useCallback(async () => {
    try {
      const data = await auditoriaService.obtenerKpisRebotesGmail()
      setKpis(data)
    } catch {
      /* KPIs se muestran en cero si falla */
    }
  }, [])

  const cargar = useCallback(async (pagina: number) => {
    setLoading(true)
    try {
      const res = await auditoriaService.listarRebotesGmail({
        skip: (pagina - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      })
      setItems(res.items)
      setTotal(res.total)
      setPage(res.page)
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'No se pudo cargar el listado'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (esAdmin) {
      void cargar(1)
      void cargarKpis()
    }
  }, [esAdmin, cargar, cargarKpis])

  const handleProcesar = async () => {
    setProcesando(true)
    try {
      const res = await auditoriaService.procesarRebotesGmail(200)
      setUltimoProceso(res)
      if (res.candidatos === 0) {
        toast.message(
          res.mensaje ||
            'Gmail no devolvio candidatos. Revise cuenta OAuth / Inbox.'
        )
      } else {
        toast.success(
          `Procesado: ${res.candidatos} candidatos, ${res.guardados} nuevos, ${res.ya_existentes} ya en BD, ${res.omitidos} omitidos`
        )
      }
      await Promise.all([cargar(1), cargarKpis()])
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al procesar Gmail'
      toast.error(msg)
    } finally {
      setProcesando(false)
    }
  }

  const handleExcel = async () => {
    try {
      await auditoriaService.descargarRebotesGmailExcel()
      toast.success('Excel descargado')
    } catch {
      toast.error('No se pudo descargar el Excel')
    }
  }

  const handleBorrarTodos = async () => {
    if (
      !window.confirm(
        'Se borraran TODOS los registros del listado. Los KPIs acumulados de escaneo se mantienen. Continuar?'
      )
    ) {
      return
    }
    setBorrando(true)
    try {
      const res = await auditoriaService.borrarTodosRebotesGmail()
      toast.success(`Borrados: ${res.borrados}`)
      setUltimoProceso(null)
      await Promise.all([cargar(1), cargarKpis()])
    } catch {
      toast.error('No se pudo borrar')
    } finally {
      setBorrando(false)
    }
  }

  if (!esAdmin) {
    return (
      <AlertWithIcon variant="destructive">
        <AlertDescription>
          Solo administracion puede usar el escaneo de rebotes Gmail.
        </AlertDescription>
      </AlertWithIcon>
    )
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const ultimaCorrida = kpis.ultima_corrida_at
    ? kpis.ultima_corrida_at.replace('T', ' ').slice(0, 19)
    : '-'

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile
          label="Total escaneados"
          value={kpis.total_escaneados}
          hint="Acumulado historico"
        />
        <KpiTile
          label="Total guardados"
          value={kpis.total_guardados}
          hint="Acumulado historico"
        />
        <KpiTile
          label="Registros actuales"
          value={kpis.registros_actuales}
          hint="En listado / Excel"
        />
        <KpiTile
          label="Corridas"
          value={kpis.total_corridas}
          hint={`Ultima: ${ultimaCorrida}`}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Mal (acum.)" value={kpis.total_mal} />
        <KpiTile label="Lleno (acum.)" value={kpis.total_lleno} />
        <KpiTile label="Temporal (acum.)" value={kpis.total_temporal} />
        <KpiTile label="Otro (acum.)" value={kpis.total_otro} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiTile label="Omitidos (acum.)" value={kpis.total_omitidos} />
        <KpiTile label="Sin cedula (acum.)" value={kpis.total_sin_cedula} />
        <KpiTile
          label="Cedula duplicada (acum.)"
          value={kpis.total_cedula_duplicada}
        />
        <KpiTile
          label="Ya existentes (acum.)"
          value={kpis.total_ya_existentes}
        />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Mail className="h-5 w-5" />
            Rebotes Gmail (notificaciones)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Escanea Inbox de itmaster@rapicreditca.com (leidos y no leidos) con
            la etiqueta GMAIL. Solo guarda si el correo matchea un cliente con
            cedula, y no repite cedulas ya guardadas en BD. Los KPIs de arriba
            son permanentes (no se borran con el listado).
          </p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void handleProcesar()} disabled={procesando}>
              {procesando ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Procesar ahora
            </Button>
            <Button
              variant="outline"
              onClick={() => void handleExcel()}
              disabled={total === 0}
            >
              <Download className="mr-2 h-4 w-4" />
              Descargar Excel
            </Button>
            <Button
              variant="destructive"
              onClick={() => void handleBorrarTodos()}
              disabled={borrando || total === 0}
            >
              {borrando ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Borrar todos
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                void cargar(page)
                void cargarKpis()
              }}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Actualizar
            </Button>
          </div>
          {ultimoProceso ? (
            <p className="text-xs text-muted-foreground">
              Ultima corrida (sesion): candidatos {ultimoProceso.candidatos},
              revisados {ultimoProceso.revisados}, guardados{' '}
              {ultimoProceso.guardados}, ya existentes{' '}
              {ultimoProceso.ya_existentes}, cedula duplicada{' '}
              {ultimoProceso.cedula_duplicada}, sin cedula{' '}
              {ultimoProceso.sin_cedula}, omitidos {ultimoProceso.omitidos}
              {ultimoProceso.query ? ` | q=${ultimoProceso.query}` : ''}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {loading && items.length === 0 ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : items.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Sin registros. Use Procesar ahora para escanear Gmail.
            </p>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cedula</TableHead>
                    <TableHead>Correo</TableHead>
                    <TableHead>Observaciones</TableHead>
                    <TableHead>Asunto</TableHead>
                    <TableHead>Fecha mensaje</TableHead>
                    <TableHead>Registro</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map(row => (
                    <TableRow key={row.id}>
                      <TableCell className="font-mono text-sm">
                        {row.cedula || '-'}
                      </TableCell>
                      <TableCell className="text-sm">{row.correo}</TableCell>
                      <TableCell>
                        <Badge className={obsBadgeClass(row.observaciones)}>
                          {row.observaciones}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[220px] truncate text-xs">
                        {row.asunto_gmail || '-'}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {row.fecha_mensaje
                          ? row.fecha_mensaje.replace('T', ' ').slice(0, 19)
                          : '-'}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {row.fecha_registro
                          ? row.fecha_registro.replace('T', ' ').slice(0, 19)
                          : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="mt-4 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {total} registro{total === 1 ? '' : 's'}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1 || loading}
                    onClick={() => void cargar(page - 1)}
                  >
                    Anterior
                  </Button>
                  <span className="px-2 py-1">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages || loading}
                    onClick={() => void cargar(page + 1)}
                  >
                    Siguiente
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
