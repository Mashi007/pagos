import { useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../ui/card'

import { Button } from '../ui/button'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

import { notificacionService } from '../../services/notificacionService'

import { toast } from 'sonner'

import { Link, Upload, Loader2, Trash2, FileText } from 'lucide-react'

import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

import { TIPOS_CASO_ADJUNTO_SUBIDA } from '../../constants/adjuntosFijosCasoTab'

type AdjuntoItem = { id: string; nombre_archivo: string; ruta: string }

function etiquetaCaso(value: string): string {
  return TIPOS_CASO_ADJUNTO_SUBIDA.find(t => t.value === value)?.label ?? value
}

export type DocumentosPdfAnexosProps = {
  /**
   * Desde Notificaciones → Configuración por submenú: un solo caso (sin elegir destino).
   */
  casoDestinoFijo?: string
}

export function DocumentosPdfAnexos({
  casoDestinoFijo,
}: DocumentosPdfAnexosProps = {}) {
  const queryClient = useQueryClient()

  const primerCaso = TIPOS_CASO_ADJUNTO_SUBIDA[0]?.value ?? 'dias_1_retraso'

  const [casoSeleccionado, setCasoSeleccionado] = useState<string>(primerCaso)

  const casoActivo = casoDestinoFijo ?? casoSeleccionado

  const { data: porCaso = {}, isLoading: loading } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos,

    queryFn: () => notificacionService.getAdjuntosFijosCobranza(),

    staleTime: 1 * 60 * 1000,
  })

  const [archivo, setArchivo] = useState<File | null>(null)

  const [subiendo, setSubiendo] = useState(false)

  const [eliminandoId, setEliminandoId] = useState<string | null>(null)

  const itemsCasoActivo: AdjuntoItem[] = (porCaso[casoActivo] ??
    []) as AdjuntoItem[]

  const handleSubir = async () => {
    if (!archivo) {
      toast.error('Selecciona un archivo PDF.')
      return
    }

    if (!(archivo.name || '').toLowerCase().endsWith('.pdf')) {
      toast.error('Solo se permiten documentos PDF.')
      return
    }

    if (!casoActivo) {
      toast.error('Elige un caso de envío.')
      return
    }

    setSubiendo(true)

    try {
      await notificacionService.uploadAdjuntoFijoCobranza(archivo, casoActivo)

      toast.success('Documento guardado.')

      setArchivo(null)

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos,
      })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail

      toast.error(msg || 'Error al subir.')
    } finally {
      setSubiendo(false)
    }
  }

  const handleEliminar = async (id: string) => {
    setEliminandoId(id)

    try {
      await notificacionService.deleteAdjuntoFijoCobranza(id)

      toast.success('Documento eliminado.')

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos,
      })
    } catch (e: unknown) {
      toast.error(
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'Error al eliminar.'
      )
    } finally {
      setEliminandoId(null)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </CardContent>
      </Card>
    )
  }

  const inputId = casoDestinoFijo
    ? `archivo-pdf-fijo-${casoDestinoFijo}`
    : 'archivo-pdf-plantillas'

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle
            className="flex items-center gap-2"
            aria-label="Documentos PDF anexos"
          >
            <Link className="h-5 w-5 text-violet-600" />
            Documentos PDF anexos
          </CardTitle>

          <CardDescription>
            {casoDestinoFijo ? (
              <>
                PDFs fijos solo para{' '}
                <strong>{etiquetaCaso(casoDestinoFijo)}</strong>. Se guardan en
                la base de datos y se reutilizan en cada envío de este
                submenú. Solo PDF.
              </>
            ) : (
              <>
                Elija el <strong>caso de envío</strong> y suba el PDF; el archivo
                queda asociado solo a ese criterio (sin aplicar a varios a la
                vez). Los datos persisten en la base de datos. Solo PDF.
              </>
            )}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            {!casoDestinoFijo && (
              <div className="space-y-1">
                <label
                  htmlFor="caso-adjunto-pdf"
                  className="block text-sm font-medium text-gray-700"
                >
                  Caso de envío
                </label>

                <Select
                  value={casoSeleccionado}
                  onValueChange={setCasoSeleccionado}
                >
                  <SelectTrigger
                    id="caso-adjunto-pdf"
                    className="h-9 w-[min(100vw-2rem,22rem)] bg-white"
                  >
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent>
                    {TIPOS_CASO_ADJUNTO_SUBIDA.map(t => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {casoDestinoFijo && (
              <div className="rounded-md border border-violet-200 bg-violet-50/60 px-3 py-2 text-sm text-violet-900">
                <span className="font-medium">Caso:</span>{' '}
                {etiquetaCaso(casoDestinoFijo)}
              </div>
            )}

            <div className="space-y-1">
              <label
                htmlFor={inputId}
                className="text-sm font-medium text-gray-700"
              >
                Archivo PDF
              </label>

              <input
                id={inputId}
                type="file"
                accept=".pdf,application/pdf"
                className="block w-full max-w-xs text-sm text-gray-700 file:mr-2 file:rounded file:border-0 file:bg-violet-100 file:px-3 file:py-1.5 file:text-violet-700"
                onChange={e => setArchivo(e.target.files?.[0] ?? null)}
              />
            </div>

            <Button
              type="button"
              onClick={() => void handleSubir()}
              disabled={subiendo || !archivo}
              variant="default"
              aria-label="Subir documento PDF"
            >
              {subiendo ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              Subir
            </Button>
          </div>

          <div className="border-t pt-4">
            <h4 className="mb-1 text-sm font-medium text-gray-700">
              Documentos guardados para este caso
            </h4>

            <p className="mb-2 text-xs text-muted-foreground">
              {etiquetaCaso(casoActivo)} - se anexan al correo si la opción Adj.
              está activa en la fila correspondiente.
            </p>

            <div className="rounded-md border bg-gray-50/50 p-3">
              {itemsCasoActivo.length === 0 ? (
                <p className="text-sm text-gray-500">
                  Aún no hay PDFs para este caso. Suba uno arriba.
                </p>
              ) : (
                <ul className="space-y-1">
                  {itemsCasoActivo.map(doc => (
                    <li
                      key={doc.id}
                      className="flex items-center justify-between gap-2 text-sm"
                    >
                      <span className="flex min-w-0 items-center gap-2 truncate">
                        <FileText className="h-4 w-4 shrink-0 text-gray-500" />
                        {doc.nombre_archivo}
                      </span>

                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => void handleEliminar(doc.id)}
                        disabled={eliminandoId === doc.id}
                        aria-label={'Eliminar ' + doc.nombre_archivo}
                      >
                        {eliminandoId === doc.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4 text-red-600" />
                        )}
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
