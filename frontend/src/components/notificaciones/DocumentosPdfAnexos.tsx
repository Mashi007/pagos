import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { notificacionService } from '../../services/notificacionService'
import { toast } from 'sonner'
import { Link, Upload, Loader2, Trash2, FileText } from 'lucide-react'
import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const TIPOS_CASO: { value: string; label: string }[] = [
  { value: 'dias_5', label: 'Faltan 5' },
  { value: 'dias_3', label: 'Faltan 3' },
  { value: 'dias_1', label: 'Falta 1' },
  { value: 'hoy', label: 'Hoy vence' },
  { value: 'dias_1_retraso', label: '1 día retraso' },
  { value: 'dias_3_retraso', label: '3 días retraso' },
  { value: 'dias_5_retraso', label: '5 días retraso' },
  { value: 'prejudicial', label: 'Prejudicial' },
  { value: 'mora_90', label: '90+ mora' },
]

type AdjuntoItem = { id: string; nombre_archivo: string; ruta: string }

export function DocumentosPdfAnexos() {
  const queryClient = useQueryClient()
  const { data: porCaso = {}, isLoading: loading } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos,
    queryFn: () => notificacionService.getAdjuntosFijosCobranza(),
    staleTime: 1 * 60 * 1000,
  })
  const [selectedTipos, setSelectedTipos] = useState<string[]>([TIPOS_CASO[0].value])
  const [archivo, setArchivo] = useState<File | null>(null)
  const [subiendo, setSubiendo] = useState(false)
  const [eliminandoId, setEliminandoId] = useState<string | null>(null)

  const toggleTipo = (value: string) => {
    setSelectedTipos((prev) => (prev.includes(value) ? prev.filter((t) => t !== value) : [...prev, value]))
  }
  const selectTodos = () => { setSelectedTipos(TIPOS_CASO.map((t) => t.value)) }
  const handleSubir = async () => {
    if (!archivo) { toast.error('Selecciona un archivo PDF.'); return }
    if (!(archivo.name || '').toLowerCase().endsWith('.pdf')) {
      toast.error('Solo se permiten documentos PDF.'); return
    }
    if (selectedTipos.length === 0) { toast.error('Elige al menos un caso (pestaña).'); return }
    setSubiendo(true)
    try {
      const tiposToUpload: string[] =
        selectedTipos.length === TIPOS_CASO.length
          ? TIPOS_CASO.map((t) => t.value)
          : selectedTipos
      for (const tipoCaso of tiposToUpload) {
        await notificacionService.uploadAdjuntoFijoCobranza(archivo, tipoCaso)
      }
      toast.success('Documento guardado.')
      setArchivo(null)
      await queryClient.invalidateQueries({ queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg || 'Error al subir.')
    } finally { setSubiendo(false) }
  }

  const handleEliminar = async (id: string) => {
    setEliminandoId(id)
    try {
      await notificacionService.deleteAdjuntoFijoCobranza(id)
      toast.success('Documento eliminado.')
      await queryClient.invalidateQueries({ queryKey: NOTIFICACIONES_QUERY_KEYS.adjuntosFijos })
    } catch (e: unknown) {
      toast.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Error al eliminar.')
    } finally { setEliminandoId(null) }
  }

  if (loading) {
    return (
      <Card><CardContent className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </CardContent></Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2" aria-label="Documentos PDF anexos">
            <Link className="h-5 w-5 text-violet-600" />
            Documentos PDF anexos
          </CardTitle>
          <CardDescription>
            Sube documentos PDF y asígnalos a una, varias o todas las pestañas (Faltan 5, Hoy vence, Retrasadas, Prejudicial, 90+ mora). Marca los casos que quieras o «Todos los casos». Solo PDF.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700 block">Aplicar a la pestaña(s)</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {TIPOS_CASO.map((t) => (
                  <label key={t.value} className="inline-flex items-center gap-1.5 cursor-pointer text-sm">
                    <input type="checkbox" checked={selectedTipos.includes(t.value)} onChange={() => toggleTipo(t.value)} className="rounded border-gray-300 text-violet-600 focus:ring-violet-500" />
                    <span>{t.label}</span>
                  </label>
                ))}
                <Button type="button" variant="outline" size="sm" onClick={selectTodos} className="text-xs">Todos los casos</Button>
              </div>
            </div>
            <div className="space-y-1">
              <label htmlFor="archivo-pdf" className="text-sm font-medium text-gray-700">Archivo PDF</label>
              <input id="archivo-pdf" type="file" accept=".pdf,application/pdf" className="block w-full max-w-xs text-sm text-gray-700 file:mr-2 file:rounded file:border-0 file:bg-violet-100 file:px-3 file:py-1.5 file:text-violet-700" onChange={(e) => setArchivo(e.target.files?.[0] ? null)} />
            </div>
            <Button onClick={handleSubir} disabled={subiendo || !archivo} variant="default" aria-label="Subir documento PDF">
              {subiendo ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              Subir
            </Button>
          </div>
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-1">Documentos almacenados por pestaña</h4>
            <p className="text-xs text-muted-foreground mb-2">Cada documento se adjunta solo a la notificación de la pestaña indicada (ej. los de «1 día retraso» van con ese tipo de aviso).</p>
            <div className="space-y-3">
              {TIPOS_CASO.map(({ value, label }) => {
                const items = porCaso[value] || []
                if (items.length === 0) return null
                return (
                  <div key={value} className="rounded-md border bg-gray-50/50 p-3">
                    <span className="text-sm font-medium text-gray-600" title={`Se envían con la notificación: ${label}`}>{label}</span>
                    <ul className="mt-2 space-y-1">
                      {items.map((doc) => (
                        <li key={doc.id} className="flex items-center justify-between gap-2 text-sm">
                          <span className="flex items-center gap-2 truncate"><FileText className="h-4 w-4 shrink-0 text-gray-500" />{doc.nombre_archivo}</span>
                          <Button type="button" variant="ghost" size="sm" onClick={() => handleEliminar(doc.id)} disabled={eliminandoId === doc.id} aria-label={"Eliminar " + doc.nombre_archivo}>
                            {eliminandoId === doc.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4 text-red-600" />}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
              {TIPOS_CASO.every((t) => (porCaso[t.value]?.length ? 0) === 0) && (
                <p className="text-sm text-gray-500">Aún no hay documentos. Sube un PDF y elige la pestaña.</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
