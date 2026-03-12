import { useState, useEffect, useRef } from 'react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { notificacionService } from '../../services/notificacionService'
import { toast } from 'sonner'
import { Save, Loader2, Eye, Database, ChevronDown, ChevronUp } from 'lucide-react'
import { Badge } from '../ui/badge'

const SEPARATOR = '{{ENCABEZADO_END}}'

const DEFAULT_CUERPO =
  'Ante todo, queremos extenderle un cordial saludo, por medio del presente instrumento queremos recordarle que, a la presente fecha, usted mantiene un saldo pendiente correspondiente a <b><u>USD {monto_total_usd} ({num_cuotas}) CUOTAS PENDIENTES</u></b> por cancelación, de fechas: <b>({fechas_str})</b>'

const DEFAULT_CLAUSULA =
  'Es pacto expreso de esta negociación, que el incumplimiento del presente contrato por parte de <b>EL COMPRADOR (A),</b> y en especial la falta del pago al vencimiento de (2) dos o más cuotas conforme a los términos establecidos por la Ley, dará derecho a exigir el pago inmediato de la totalidad del saldo deudor, declarar resuelto de pleno derecho el presente Contrato y recuperar la propiedad y posesión del bien objeto de esta venta. En caso de devolución <b>EL COMPRADOR (A),</b> conviene con <b>EL VENDEDOR (A),</b> recoger el vehículo donde se encuentre, sin más avisos ni trámites. <b>EL COMPRADOR (A),</b> renuncia toda acción que pudiera corresponderle por la recuperación del bien vehículo, salvo la que la propia ley le acuerde.'

type PdfEditorFocus = 'encabezado' | 'cuerpo' | 'firma'

const VARIABLES_PDF = [
  { key: 'monto_total_usd', label: 'Monto total USD' },
  { key: 'num_cuotas', label: 'Nº cuotas' },
  { key: 'fechas_str', label: 'Fechas (texto)' },
]

/**
 * Pestaña: Plantilla del PDF que se anexa al email.
 * Solo campos necesarios para generación del documento PDF: Encabezado, Firma, Cuerpo (sin Asunto ni Ciudad por defecto en UI).
 */
export function PlantillaAnexoPdf() {
  const [ciudadDefault, setCiudadDefault] = useState('Guacara')
  const [encabezado, setEncabezado] = useState('')
  const [cuerpo, setCuerpo] = useState('')
  const [firma, setFirma] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [generandoPreview, setGenerandoPreview] = useState(false)
  const [focus, setFocus] = useState<PdfEditorFocus>('cuerpo')
  const [mostrarVariables, setMostrarVariables] = useState(true)
  const encRef = useRef<HTMLTextAreaElement>(null)
  const cuerpoRef = useRef<HTMLTextAreaElement>(null)
  const firmaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    let cancelled = false
    notificacionService.getPlantillaPdfCobranza().then((pdfData) => {
      if (!cancelled) {
        setCiudadDefault(pdfData.ciudad_default ?? 'Guacara')
        const cuerpoPrincipal = pdfData.cuerpo_principal ?? DEFAULT_CUERPO
        if (cuerpoPrincipal.includes(SEPARATOR)) {
          const [enc, ...rest] = cuerpoPrincipal.split(SEPARATOR)
          setEncabezado(enc.trim())
          setCuerpo(rest.join(SEPARATOR).trim() || DEFAULT_CUERPO)
        } else {
          setEncabezado('')
          setCuerpo(cuerpoPrincipal || DEFAULT_CUERPO)
        }
        setFirma(pdfData.clausula_septima ?? DEFAULT_CLAUSULA)
      }
    }).catch(() => {
      if (!cancelled) {
        setCuerpo(DEFAULT_CUERPO)
        setFirma(DEFAULT_CLAUSULA)
        toast.error('Error al cargar la plantilla PDF.')
      }
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const insertarVariable = (key: string) => {
    const token = `{${key}}`
    const insertInto = (el: HTMLTextAreaElement | null, setter: (v: string) => void, current: string) => {
      if (!el) {
        setter(current + token)
        return
      }
      const start = el.selectionStart ?? current.length
      const end = el.selectionEnd ?? current.length
      const next = current.slice(0, start) + token + current.slice(end)
      setter(next)
      setTimeout(() => {
        try {
          el.focus()
          el.setSelectionRange(start + token.length, start + token.length)
        } catch {}
      }, 0)
    }
    if (focus === 'encabezado') return insertInto(encRef.current, setEncabezado, encabezado)
    if (focus === 'cuerpo') return insertInto(cuerpoRef.current, setCuerpo, cuerpo)
    if (focus === 'firma') return insertInto(firmaRef.current, setFirma, firma)
  }

  const aplicarFormato = (tag: 'b' | 'i' | 'u' | 'ul' | 'a') => {
    const wrap = (el: HTMLTextAreaElement | null, setter: (v: string) => void, current: string) => {
      if (!el) return
      const start = el.selectionStart ?? 0
      const end = el.selectionEnd ?? 0
      const selected = current.slice(start, end)
      let before = '', after = ''
      if (tag === 'a') {
        before = '<a href="https://">'
        after = '</a>'
      } else if (tag === 'ul') {
        const lines = selected || 'Elemento 1\nElemento 2'
        const wrapped = lines.split('\n').map(l => `<li>${l || 'Elemento'}</li>`).join('\n')
        const next = current.slice(0, start) + `<ul>\n${wrapped}\n</ul>` + current.slice(end)
        setter(next)
        return
      } else {
        before = `<${tag}>`
        after = `</${tag}>`
      }
      const next = current.slice(0, start) + before + (selected || 'texto') + after + current.slice(end)
      setter(next)
      setTimeout(() => { try { el.focus() } catch {} }, 0)
    }
    if (focus === 'encabezado') return wrap(encRef.current, setEncabezado, encabezado)
    if (focus === 'cuerpo') return wrap(cuerpoRef.current, setCuerpo, cuerpo)
    if (focus === 'firma') return wrap(firmaRef.current, setFirma, firma)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const cuerpoPrincipal = encabezado.trim()
        ? encabezado.trim() + '\n\n' + SEPARATOR + '\n\n' + (cuerpo || '').trim()
        : (cuerpo || '').trim()
      await notificacionService.updatePlantillaPdfCobranza({
        ciudad_default: ciudadDefault,
        cuerpo_principal: cuerpoPrincipal || null,
        clausula_septima: firma || null,
      })
      toast.success('Plantilla PDF de cobranza guardada. Se usará como anexo al email.')
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
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold">Armar plantilla</h2>
          <p className="text-sm text-gray-500">
            Contenido del documento PDF que se anexa al correo de cobranza. Al guardar se persiste la plantilla.
          </p>
        </div>
      </div>

      <Card className="p-4 space-y-3">
        <div className="grid grid-cols-1 gap-3">
          <div className="border rounded-lg p-4 bg-gray-50 space-y-4">
            <label className="text-sm font-medium text-gray-700 block">Variables del PDF (insertar en encabezado, cuerpo o firma)</label>
            <p className="text-xs text-gray-500 mb-2">
              Haga clic en un campo de texto y luego en la variable para insertarla.
            </p>
            <div className="flex flex-wrap gap-2">
              {VARIABLES_PDF.map(({ key }) => (
                <Button
                  key={key}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="bg-white border-blue-300 text-blue-800 hover:bg-blue-100 font-mono text-xs"
                  onClick={() => {
                    insertarVariable(key)
                    toast.success(`{${key}} insertado`, { duration: 1200 })
                  }}
                >
                  {`{${key}}`}
                </Button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <p className="text-xs text-gray-500 mb-1">
                Puede usar código HTML en encabezado, cuerpo y firma. Use el botón «Vista previa (datos de ejemplo)» para ver cómo queda el resultado.
              </p>
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                Formato rápido (encabezado/cuerpo/firma):
                <Button size="sm" variant="ghost" onClick={() => aplicarFormato('b')}>B</Button>
                <Button size="sm" variant="ghost" onClick={() => aplicarFormato('i')}>I</Button>
                <Button size="sm" variant="ghost" onClick={() => aplicarFormato('u')}>U</Button>
                <Button size="sm" variant="ghost" onClick={() => aplicarFormato('ul')}>Lista</Button>
                <Button size="sm" variant="ghost" onClick={() => aplicarFormato('a')}>Enlace</Button>
              </div>
            </div>
            <div>
              <label className="text-sm text-gray-600">Encabezado (puede incluir HTML)</label>
              <Textarea
                ref={encRef}
                value={encabezado}
                onFocus={() => setFocus('encabezado')}
                onChange={(e) => setEncabezado(e.target.value)}
                rows={4}
                placeholder="Encabezado (ej. <p>Texto</p>)"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600">Firma (puede incluir HTML)</label>
              <Textarea
                ref={firmaRef}
                value={firma}
                onFocus={() => setFocus('firma')}
                onChange={(e) => setFirma(e.target.value)}
                rows={4}
                placeholder="Firma (ej. <p>Atentamente,</p>)"
                className="mt-1"
              />
            </div>
            <div className="col-span-2">
              <label className="text-sm text-gray-600">Cuerpo (puede incluir HTML)</label>
              <Textarea
                ref={cuerpoRef}
                value={cuerpo}
                onFocus={() => setFocus('cuerpo')}
                onChange={(e) => setCuerpo(e.target.value)}
                rows={10}
                placeholder="Contenido principal (ej. <p>Hola <b>{monto_total_usd}</b></p>)"
                className="mt-1"
              />
            </div>
          </div>

          <div className="border-2 border-blue-200 rounded-lg p-4 bg-gradient-to-br from-blue-50 to-white shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-600" />
                <label className="text-base font-bold text-gray-800">Banco de Variables</label>
                <Badge variant="outline" className="text-xs bg-blue-100 text-blue-800 border-blue-300">
                  {VARIABLES_PDF.length} disponibles
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMostrarVariables(!mostrarVariables)}
                className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
              >
                {mostrarVariables ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
            {mostrarVariables && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
                {VARIABLES_PDF.map(({ key, label }) => (
                  <div
                    key={key}
                    className="group border-2 border-gray-200 rounded-lg p-3 bg-white hover:border-blue-400 hover:shadow-md cursor-pointer transition-all duration-200"
                    onClick={() => insertarVariable(key)}
                    title={`Insertar {${key}} en el campo activo`}
                  >
                    <div className="font-mono text-sm text-blue-700">{`{${key}}`}</div>
                    <div className="text-xs text-gray-600 mt-1">{label}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2 items-center pt-2">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              Guardar plantilla PDF
            </Button>
            <Button type="button" variant="outline" onClick={handleVistaPreviaPdf} disabled={generandoPreview}>
              {generandoPreview ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Eye className="h-4 w-4 mr-2" />}
              Vista previa (datos de ejemplo)
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
