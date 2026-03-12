import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Textarea } from '../ui/textarea'
import { notificacionService } from '../../services/notificacionService'
import { toast } from 'sonner'
import { FileText, Save, Loader2, Eye } from 'lucide-react'

const DEFAULT_CUERPO =
  'Ante todo, queremos extenderle un cordial saludo, por medio del presente instrumento queremos recordarle que, a la presente fecha, usted mantiene un saldo pendiente correspondiente a <b><u>USD {monto_total_usd} ({num_cuotas}) CUOTAS PENDIENTES</u></b> por cancelaciÃ³n, de fechas: <b>({fechas_str})</b>'

const DEFAULT_CLAUSULA =
  'Es pacto expreso de esta negociaciÃ³n, que el incumplimiento del presente contrato por parte de <b>EL COMPRADOR (A),</b> y en especial la falta del pago al vencimiento de (2) dos o mÃ¡s cuotas conforme a los tÃ©rminos establecidos por la Ley, darÃ¡ derecho a exigir el pago inmediato de la totalidad del saldo deudor, declarar resuelto de pleno derecho el presente Contrato y recuperar la propiedad y posesiÃ³n del bien objeto de esta venta. En caso de devoluciÃ³n <b>EL COMPRADOR (A),</b> conviene con <b>EL VENDEDOR (A),</b> recoger el vehÃ­culo donde se encuentre, sin mÃ¡s avisos ni trÃ¡mites. <b>EL COMPRADOR (A),</b> renuncia toda acciÃ³n que pudiera corresponderle por la recuperaciÃ³n del bien vehÃ­culo, salvo la que la propia ley le acuerde.'

/**
 * PestaÃ±a: Plantilla del PDF que se anexa al email (carta de cobranza con variables).
 * Este PDF se genera dinÃ¡micamente y se adjunta junto con el cuerpo del email.
 */
export function PlantillaAnexoPdf() {
  const [ciudadDefault, setCiudadDefault] = useState('Guacara')
  const [cuerpoPrincipal, setCuerpoPrincipal] = useState('')
  const [clausulaSeptima, setClausulaSeptima] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generandoPreview, setGenerandoPreview] = useState(false)

  useEffect(() => {
    let cancelled = false
    notificacionService.getPlantillaPdfCobranza().then((pdfData) => {
      if (!cancelled) {
        setCiudadDefault(pdfData.ciudad_default ?? 'Guacara')
        setCuerpoPrincipal(pdfData.cuerpo_principal ?? DEFAULT_CUERPO)
        setClausulaSeptima(pdfData.clausula_septima ?? DEFAULT_CLAUSULA)
      }
    }).catch(() => {
      if (!cancelled) {
        setCuerpoPrincipal(DEFAULT_CUERPO)
        setClausulaSeptima(DEFAULT_CLAUSULA)
        toast.error('Error al cargar la plantilla PDF.')
      }
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await notificacionService.updatePlantillaPdfCobranza({
        ciudad_default: ciudadDefault,
        cuerpo_principal: cuerpoPrincipal || null,
        clausula_septima: clausulaSeptima || null,
      })
      toast.success('Plantilla PDF de cobranza guardada. Se usarÃ¡ como anexo al email.')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  const handleVistaPreviaPdf = async () => {
    setGenerandoPreview(true)
    try {
      const blob = await notificacionService.getPlantillaPdfCobranzaPreview()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank', 'noopener,noreferrer')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
      toast.success('Vista previa abierta en nueva pestaÃ±a')
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
          Plantilla del PDF anexo al email (carta de cobranza)
        </CardTitle>
        <CardDescription>
          Este PDF se genera con variables y se adjunta automÃ¡ticamente al enviar el correo de cobranza. Edite ciudad por defecto, cuerpo principal y ClÃ¡usula SÃ©ptima. Variables: {'{monto_total_usd}'}, {'{num_cuotas}'}, {'{fechas_str}'}.
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
          <label className="text-sm font-medium text-gray-700">ClÃ¡usula SÃ©ptima (HTML)</label>
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


  </>
  )
}
