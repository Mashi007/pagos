import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { notificacionService } from '../../services/notificacionService'
import { toast } from 'sonner'
import { Link, Upload, Loader2, Trash2, FileText } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

const TIPOS_CASO: { value: string; label: string }[] = [
  { value: 'dias_5', label: '5 dias' },
  { value: 'dias_3', label: '3 dias' },
  { value: 'dias_1', label: '1 dia' },
  { value: 'hoy', label: 'Hoy' },
  { value: 'mora_90', label: 'Mora 90+' },
]

type AdjuntoItem = { id: string; nombre_archivo: string; ruta: string }

export function DocumentosPdfAnexos() {
  const [porCaso, setPorCaso] = useState<Record<string, AdjuntoItem[]>>({})
  const [tipoCasoSeleccionado, setTipoCasoSeleccionado] = useState<string>('dias_5')
  const [archivo, setArchivo] = useState<File | null>(null)
  const [subiendo, setSubiendo] = useState(false)
  const [loading, setLoading] = useState(true)
  const [eliminandoId, setEliminandoId] = useState<string | null>(null)

  const cargar = () => {
    setLoading(true)
    notificacionService.getAdjuntosFijosCobranza()
      .then((data) => { setPorCaso(data || {}) })
      .catch(() => { toast.error('Error al cargar documentos anexos.') })
      .finally(() => setLoading(false))
  }

  useEffect(() => { cargar() }, [])

  const handleSubir = async () => {
    if (!archivo) { toast.error('Selecciona un archivo PDF.'); return }
    if (!(archivo.name || '').toLowerCase().endsWith('.pdf')) {
      toast.error('Solo se permiten documentos PDF.'); return
    }
    setSubiendo(true)
    try {
      await notificacionService.uploadAdjuntoFijoCobranza(archivo, tipoCasoSeleccionado)
      toast.success('Documento guardado.')
      setArchivo(null)
      cargar()
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
      cargar()
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
            Sube documentos PDF y asignalos a un caso (5 dias, 3 dias, 1 dia, hoy, mora 90). Solo PDF. Se almacenan y se envian con la notificacion.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <label htmlFor="tipo-caso" className="text-sm font-medium text-gray-700">Aplicar al caso</label>
              <Select value={tipoCasoSeleccionado} onValueChange={setTipoCasoSeleccionado}>
                <SelectTrigger id="tipo-caso" className="w-[180px]"><SelectValue placeholder="Selecciona caso" /></SelectTrigger>
                <SelectContent>
                  {TIPOS_CASO.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label htmlFor="archivo-pdf" className="text-sm font-medium text-gray-700">Archivo PDF</label>
              <input id="archivo-pdf" type="file" accept=".pdf,application/pdf" className="block w-full max-w-xs text-sm text-gray-700 file:mr-2 file:rounded file:border-0 file:bg-violet-100 file:px-3 file:py-1.5 file:text-violet-700" onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
            </div>
            <Button onClick={handleSubir} disabled={subiendo || !archivo} variant="default" aria-label="Subir documento PDF">
              {subiendo ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              Subir
            </Button>
          </div>
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Documentos almacenados por caso</h4>
            <div className="space-y-3">
              {TIPOS_CASO.map(({ value, label }) => {
                const items = porCaso[value] || []
                if (items.length === 0) return null
                return (
                  <div key={value} className="rounded-md border bg-gray-50/50 p-3">
                    <span className="text-sm font-medium text-gray-600">{label}</span>
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
              {TIPOS_CASO.every((t) => (porCaso[t.value]?.length ?? 0) === 0) && (
                <p className="text-sm text-gray-500">Aun no hay documentos. Sube un PDF y elige el caso.</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
