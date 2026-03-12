import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { notificacionService } from '../../services/notificacionService'
import { toast } from 'sonner'
import { Link, Save, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { Badge } from '../ui/badge'

/**
 * PestaÃ±a: Documentos PDF que se anexan a la notificaciÃ³n (PDFs fijos).
 * Permite configurar 1 o 2 documentos que se envÃ­an siempre con el email.
 * Actualmente el backend soporta un documento; el segundo slot queda preparado para futura ampliaciÃ³n.
 */
export function DocumentosPdfAnexos() {
  const [adjuntoNombre, setAdjuntoNombre] = useState('')
  const [adjuntoRuta, setAdjuntoRuta] = useState('')
  const [adjuntoSaving, setAdjuntoSaving] = useState(false)
  const [adjuntoExiste, setAdjuntoExiste] = useState<boolean | null>(null)
  const [adjuntoMensaje, setAdjuntoMensaje] = useState<string>('')
  const [verificandoRuta, setVerificandoRuta] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    notificacionService.getAdjuntoFijoCobranza().then((adjuntoData) => {
        if (!cancelled) {
          setAdjuntoNombre(adjuntoData.nombre_archivo ?? '')
          setAdjuntoRuta(adjuntoData.ruta ?? '')
          if (adjuntoData.ruta?.trim()) {
            notificacionService
              .verificarAdjuntoFijoCobranza()
              .then((r) => {
                if (!cancelled) {
                  setAdjuntoExiste(r.existe)
                  setAdjuntoMensaje(r.mensaje ?? '')
                }
              })
              .catch(() => {
                if (!cancelled) {
                  setAdjuntoExiste(false)
                  setAdjuntoMensaje('Error al verificar')
                }
              })
          } else {
            setAdjuntoExiste(false)
            setAdjuntoMensaje('Ruta vacÃ­a')
          }
        }
      })
      .catch(() => {
        if (!cancelled) toast.error('Error al cargar la configuraciÃ³n de documentos anexos.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleSaveAdjunto = async () => {
    setAdjuntoSaving(true)
    try {
      await notificacionService.updateAdjuntoFijoCobranza({
        nombre_archivo: adjuntoNombre || 'Adjunto_Cobranza.pdf',
        ruta: adjuntoRuta,
      })
      toast.success('Documento anexo guardado. Se enviarÃ¡ junto con el email y el PDF de cobranza.')
      if (adjuntoRuta.trim()) {
        const r = await notificacionService.verificarAdjuntoFijoCobranza()
        setAdjuntoExiste(r.existe)
        setAdjuntoMensaje(r.mensaje ?? '')
      } else {
        setAdjuntoExiste(false)
        setAdjuntoMensaje('Ruta vacÃ­a')
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al guardar')
    } finally {
      setAdjuntoSaving(false)
    }
  }

  const handleVerificarRuta = async () => {
    setVerificandoRuta(true)
    try {
      const r = await notificacionService.verificarAdjuntoFijoCobranza()
      setAdjuntoExiste(r.existe)
      setAdjuntoMensaje(r.mensaje ?? '')
      toast[r.existe ? 'success' : 'warning'](r.existe ? 'Archivo encontrado en el servidor' : r.mensaje || 'Archivo no encontrado')
    } catch {
      setAdjuntoExiste(false)
      setAdjuntoMensaje('Error al verificar')
      toast.error('Error al comprobar la ruta')
    } finally {
      setVerificandoRuta(false)
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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link className="h-5 w-5 text-violet-600" />
            Documento PDF anexo 1 (fijo)
          </CardTitle>
          <CardDescription>
            Un PDF estÃ¡tico que se anexa siempre al correo de notificaciÃ³n, junto con la plantilla de email y el PDF de cobranza (variable). Indique la ruta del archivo en el servidor. Si la ruta estÃ¡ vacÃ­a, no se anexa.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label htmlFor="adjunto-nombre" className="text-sm font-medium text-gray-700">Nombre del archivo en el correo</label>
            <Input
              id="adjunto-nombre"
              value={adjuntoNombre}
              onChange={(e) => setAdjuntoNombre(e.target.value)}
              placeholder="Documento_Adicional.pdf"
              className="mt-1 max-w-xs"
            />
          </div>
          <div>
            <label htmlFor="adjunto-ruta" className="text-sm font-medium text-gray-700">Ruta del PDF en el servidor</label>
            <Input
              id="adjunto-ruta"
              value={adjuntoRuta}
              onChange={(e) => setAdjuntoRuta(e.target.value)}
              placeholder="documento.pdf o carpeta/documento.pdf (relativa si hay directorio base)"
              className="mt-1 font-mono text-sm"
            />
            {adjuntoExiste !== null && (
              <div className="mt-2 flex items-center gap-2">
                {adjuntoExiste ? (
                  <Badge variant="default" className="bg-green-600 gap-1">
                    <CheckCircle2 className="h-3 w-3" /> Archivo encontrado
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="gap-1">
                    <XCircle className="h-3 w-3" /> {adjuntoMensaje || 'Archivo no encontrado'}
                  </Badge>
                )}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleSaveAdjunto} disabled={adjuntoSaving} variant="secondary">
              {adjuntoSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              Guardar documento anexo 1
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleVerificarRuta}
              disabled={verificandoRuta || !adjuntoRuta.trim()}
            >
              {verificandoRuta ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
              Comprobar ruta
            </Button>
          </div>
        </CardContent>
      </Card>

  
    </div>
  )
}

