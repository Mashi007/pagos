import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'
import { notificacionService } from '../../services/notificacionService'
import { toast } from 'sonner'
import { FileText, Save, Loader2, Link, Eye, CheckCircle2, XCircle } from 'lucide-react'
import { Badge } from '../ui/badge'

const DEFAULT_CUERPO =
  'Ante todo, queremos extenderle un cordial saludo, por medio del presente instrumento queremos recordarle que, a la presente fecha, usted mantiene un saldo pendiente correspondiente a <b><u>USD {monto_total_usd} ({num_cuotas}) CUOTAS PENDIENTES</u></b> por cancelación, de fechas: <b>({fechas_str})</b>'

const DEFAULT_CLAUSULA =
  'Es pacto expreso de esta negociación, que el incumplimiento del presente contrato por parte de <b>EL COMPRADOR (A),</b> y en especial la falta del pago al vencimiento de (2) dos o más cuotas conforme a los términos establecidos por la Ley, dará derecho a exigir el pago inmediato de la totalidad del saldo deudor, declarar resuelto de pleno derecho el presente Contrato y recuperar la propiedad y posesión del bien objeto de esta venta. En caso de devolución <b>EL COMPRADOR (A),</b> conviene con <b>EL VENDEDOR (A),</b> recoger el vehículo donde se encuentre, sin más avisos ni trámites. <b>EL COMPRADOR (A),</b> renuncia toda acción que pudiera corresponderle por la recuperación del bien vehículo, salvo la que la propia ley le acuerde.'

export function PlantillaPdfCobranza() {
  const [ciudadDefault, setCiudadDefault] = useState('Guacara')
  const [cuerpoPrincipal, setCuerpoPrincipal] = useState('')
  const [clausulaSeptima, setClausulaSeptima] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [adjuntoNombre, setAdjuntoNombre] = useState('')
  const [adjuntoRuta, setAdjuntoRuta] = useState('')
  const [adjuntoSaving, setAdjuntoSaving] = useState(false)
  const [adjuntoExiste, setAdjuntoExiste] = useState<boolean | null>(null)
  const [adjuntoMensaje, setAdjuntoMensaje] = useState<string>('')
  const [verificandoRuta, setVerificandoRuta] = useState(false)
  const [generandoPreview, setGenerandoPreview] = useState(false)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      notificacionService.getPlantillaPdfCobranza(),
      notificacionService.getAdjuntoFijoCobranza(),
    ])
      .then(([pdfData, adjuntoData]) => {
        if (!cancelled) {
          setCiudadDefault(pdfData.ciudad_default ?? 'Guacara')
          setCuerpoPrincipal(pdfData.cuerpo_principal ?? DEFAULT_CUERPO)
          setClausulaSeptima(pdfData.clausula_septima ?? DEFAULT_CLAUSULA)
          setAdjuntoNombre(adjuntoData.nombre_archivo ?? '')
          setAdjuntoRuta(adjuntoData.ruta ?? '')
          if (adjuntoData.ruta?.trim()) {
            notificacionService.verificarAdjuntoFijoCobranza().then((r) => {
              if (!cancelled) {
                setAdjuntoExiste(r.existe)
                setAdjuntoMensaje(r.mensaje ?? '')
              }
            }).catch(() => {
              if (!cancelled) { setAdjuntoExiste(false); setAdjuntoMensaje('Error al verificar'); }
            })
          } else {
            setAdjuntoExiste(false)
            setAdjuntoMensaje('Ruta vacía')
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCuerpoPrincipal(DEFAULT_CUERPO)
          setClausulaSeptima(DEFAULT_CLAUSULA)
          toast.error('Error al cargar la configuración de PDF y adjunto fijo. Se muestran valores por defecto.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await notificacionService.updatePlantillaPdfCobranza({
        ciudad_default: ciudadDefault,
        cuerpo_principal: cuerpoPrincipal || null,
        clausula_septima: clausulaSeptima || null,
      })
      toast.success('Plantilla PDF de cobranza guardada. Se usará en el adjunto del email.')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveAdjunto = async () => {
    setAdjuntoSaving(true)
    try {
      await notificacionService.updateAdjuntoFijoCobranza({
        nombre_archivo: adjuntoNombre || 'Adjunto_Cobranza.pdf',
        ruta: adjuntoRuta,
      })
      toast.success('Adjunto fijo guardado. Se anexará junto con la carta de cobranza.')
      if (adjuntoRuta.trim()) {
        const r = await notificacionService.verificarAdjuntoFijoCobranza()
        setAdjuntoExiste(r.existe)
        setAdjuntoMensaje(r.mensaje ?? '')
      } else {
        setAdjuntoExiste(false)
        setAdjuntoMensaje('Ruta vacía')
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

  const handleVistaPreviaPdf = async () => {
    setGenerandoPreview(true)
    try {
      const blob = await notificacionService.getPlantillaPdfCobranzaPreview()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank', 'noopener,noreferrer')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
      toast.success('Vista previa abierta en nueva pestaña')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al generar la vista previa')
    } finally {
      setGenerandoPreview(false)
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
    <>
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-violet-600" />
          Plantilla del PDF de carta de cobranza (adjunto al email)
        </CardTitle>
        <CardDescription>
          Este PDF se adjunta automáticamente al enviar el correo de cobranza. Puede editar la ciudad por defecto y los textos del cuerpo y de la Cláusula Séptima. Use las variables: {'{monto_total_usd}'}, {'{num_cuotas}'}, {'{fechas_str}'} en el cuerpo principal (HTML).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label htmlFor="pdf-ciudad" className="text-sm font-medium text-gray-700">Ciudad por defecto</label>
          <Input
            id="pdf-ciudad"
            value={ciudadDefault}
            onChange={(e) => setCiudadDefault(e.target.value)}
            placeholder="Guacara"
            className="mt-1 max-w-xs"
            aria-describedby="pdf-ciudad-desc"
          />
        </div>
        <div>
          <label htmlFor="pdf-cuerpo" className="text-sm font-medium text-gray-700">Cuerpo principal (HTML)</label>
          <Textarea
            id="pdf-cuerpo"
            value={cuerpoPrincipal}
            onChange={(e) => setCuerpoPrincipal(e.target.value)}
            rows={6}
            placeholder={DEFAULT_CUERPO}
            className="mt-1 font-mono text-sm"
          />
          <p className="text-xs text-gray-500 mt-1">Variables: {'{monto_total_usd}'}, {'{num_cuotas}'}, {'{fechas_str}'}</p>
        </div>
        <div>
          <label className="text-sm font-medium text-gray-700">Cláusula Séptima (HTML)</label>
          <Textarea
            value={clausulaSeptima}
            onChange={(e) => setClausulaSeptima(e.target.value)}
            rows={8}
            placeholder={DEFAULT_CLAUSULA}
            className="mt-1 font-mono text-sm"
          />
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            Guardar plantilla PDF
          </Button>
          <Button type="button" variant="outline" onClick={handleVistaPreviaPdf} disabled={generandoPreview}>
            {generandoPreview ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Eye className="h-4 w-4 mr-2" />}
            Vista previa (datos de ejemplo)
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Link className="h-5 w-5 text-violet-600" />
          Adjunto fijo (PDF estático)
        </CardTitle>
        <CardDescription>
          Un segundo PDF que se anexa siempre al mismo correo de cobranza, sin cambios. Indique la ruta del archivo en el servidor (absoluta o relativa al proceso). Si la ruta está vacía, no se anexa ningún documento adicional.
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
          Guardar adjunto fijo
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={handleVerificarRuta} disabled={verificandoRuta || !adjuntoRuta.trim()}>
          {verificandoRuta ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
          Comprobar ruta
        </Button>
        </div>
      </CardContent>
    </Card>
    </>
  )
}
