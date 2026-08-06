import { useCallback, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Loader2, Search } from 'lucide-react'
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
  const [qInput, setQInput] = useState('')
  const [appliedQ, setAppliedQ] = useState('')
  const [scanning, setScanning] = useState(false)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)

  const listQuery = useQuery({
    queryKey: ['notificaciones', 'evidencias', appliedQ],
    queryFn: () => evidenciasNotificacionService.buscar(appliedQ, 1, 100),
    enabled: appliedQ.trim().length >= 2,
  })

  const buscar = useCallback(() => {
    const q = qInput.trim()
    if (q.length < 2) {
      toast.error('Indique cedula o email (minimo 2 caracteres).')
      return
    }
    setAppliedQ(q)
  }, [qInput])

  const escanear = useCallback(async () => {
    setScanning(true)
    try {
      const r = await evidenciasNotificacionService.escanear(40)
      if (!r.ok) {
        toast.error(r.mensaje || r.error || 'Error al escanear Gmail')
        return
      }
      toast.success(
        r.mensaje ||
          `Guardados: ${r.guardados}. Ya existentes: ${r.ya_existentes}.`
      )
      if (appliedQ.trim().length >= 2) {
        await listQuery.refetch()
      }
    } catch (e) {
      toast.error(getErrorMessage(e) || 'Error al escanear')
    } finally {
      setScanning(false)
    }
  }, [appliedQ, listQuery])

  const descargar = useCallback(async (row: EvidenciaNotificacionItem) => {
    setDownloadingId(row.id)
    try {
      const etiqueta = (row.etiqueta_gmail || 'evidencia').replace(/\s+/g, '_')
      const email = (row.email_cliente || 'cliente').replace(/@/g, '_at_')
      await evidenciasNotificacionService.descargarPdf(
        row.id,
        `evidencia_${etiqueta}_${email}_${row.id}.pdf`
      )
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo descargar el PDF')
    } finally {
      setDownloadingId(null)
    }
  }, [])

  const items = listQuery.data?.items ?? []

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Evidencias</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Archivo PDF (correo + anexo) desde etiquetas Gmail en itmaster:{' '}
          DIA SIGUIENTE, 1 CUOTA, 2 O MAS CUOTAS. Busque por cedula o email.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Escanear Gmail</CardTitle>
          <CardDescription>
            Lee mensajes etiquetados en itmaster, genera un PDF por correo y lo
            guarda en base de datos (idempotente).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={escanear} disabled={scanning}>
            {scanning ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Search className="mr-2 h-4 w-4" />
            )}
            {scanning ? 'Escaneando...' : 'Escanear y almacenar'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Buscar evidencias</CardTitle>
          <CardDescription>
            Filtra los PDF almacenados por cedula o correo del cliente.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              placeholder="Cedula o email..."
              value={qInput}
              onChange={e => setQInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') buscar()
              }}
              className="sm:max-w-md"
            />
            <Button onClick={buscar} variant="secondary">
              <Search className="mr-2 h-4 w-4" />
              Buscar
            </Button>
          </div>

          {!appliedQ && (
            <p className="text-sm text-muted-foreground">
              Escriba cedula o email y pulse Buscar.
            </p>
          )}

          {appliedQ && listQuery.isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Buscando...
            </div>
          )}

          {appliedQ && listQuery.isError && (
            <p className="text-sm text-destructive">
              {getErrorMessage(listQuery.error) || 'Error al buscar'}
            </p>
          )}

          {appliedQ && listQuery.isSuccess && items.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No hay evidencias para &quot;{appliedQ}&quot;. Escanee Gmail si
              aun no se archivaron.
            </p>
          )}

          {items.length > 0 && (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b bg-muted/40">
                  <tr>
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
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={downloadingId === row.id}
                          onClick={() => descargar(row)}
                        >
                          {downloadingId === row.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                          <span className="ml-2">Descargar</span>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="px-3 py-2 text-xs text-muted-foreground">
                {listQuery.data?.total ?? 0} resultado(s)
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
