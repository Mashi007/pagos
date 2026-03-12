import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { PlantillasNotificaciones } from '../components/notificaciones/PlantillasNotificaciones'
import { PlantillaAnexoPdf } from '../components/notificaciones/PlantillaAnexoPdf'
import { DocumentosPdfAnexos } from '../components/notificaciones/DocumentosPdfAnexos'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Button } from '../components/ui/button'
import { FileText, Link, ChevronLeft, Download, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react'

const SUBTAB_CUERPO_EMAIL = 'cuerpo-email'
const SUBTAB_ANEXO_PDF = 'anexo-pdf'
const SUBTAB_DOCUMENTOS_PDF = 'documentos-pdf'

export function Plantillas() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const subtabFromUrl = searchParams.get('subtab')
  const [plantillaAEditar, setPlantillaAEditar] = useState<any>(null)
  const [resumenAbierto, setResumenAbierto] = useState(false)
  const [activeTab, setActiveTab] = useState(() => {
    if (subtabFromUrl === SUBTAB_ANEXO_PDF) return SUBTAB_ANEXO_PDF
    if (subtabFromUrl === SUBTAB_DOCUMENTOS_PDF) return SUBTAB_DOCUMENTOS_PDF
    return SUBTAB_CUERPO_EMAIL
  })

  useEffect(() => {
    const sub = searchParams.get('subtab')
    if (sub === SUBTAB_ANEXO_PDF) setActiveTab(SUBTAB_ANEXO_PDF)
    else if (sub === SUBTAB_DOCUMENTOS_PDF) setActiveTab(SUBTAB_DOCUMENTOS_PDF)
    else if (sub === SUBTAB_CUERPO_EMAIL) setActiveTab(SUBTAB_CUERPO_EMAIL)
    else setActiveTab(SUBTAB_CUERPO_EMAIL)
  }, [searchParams])

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    const next = new URLSearchParams(searchParams)
    if (value === SUBTAB_ANEXO_PDF) next.set('subtab', SUBTAB_ANEXO_PDF)
    else if (value === SUBTAB_DOCUMENTOS_PDF) next.set('subtab', SUBTAB_DOCUMENTOS_PDF)
    else next.delete('subtab')
    setSearchParams(next, { replace: true })
  }

  const handleVolver = () => {
    navigate('/configuracion')
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h1 className="text-xl font-bold">Plantillas de notificaciones</h1>
          <p className="text-sm text-gray-500">Plantilla de email, plantilla PDF anexo y documentos PDF fijos que se env\u00edan con la notificaci\u00f3n</p>
          <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50/50 text-sm text-gray-700 overflow-hidden">
            <button
              type="button"
              onClick={() => setResumenAbierto(!resumenAbierto)}
              className="w-full px-3 py-2 flex items-center justify-between gap-2 text-left font-medium text-gray-800 hover:bg-blue-100/50 transition-colors"
              aria-expanded={resumenAbierto}
            >
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-blue-600 shrink-0" />
                Resumen de configuraci\u00f3n
              </span>
              {resumenAbierto ? <ChevronUp className="h-4 w-4 shrink-0" /> : <ChevronDown className="h-4 w-4 shrink-0" />}
            </button>
            {resumenAbierto && (
              <div className="px-3 pb-3 pt-0 border-t border-blue-100">
                <p className="text-gray-600 mt-2 md:hidden">Al enviar el correo se usa: 1) Cuerpo email. 2) PDF variable (carta cobranza). 3) PDF(s) fijos opcionales.</p>
                <ol className="list-decimal list-inside space-y-0.5 text-gray-600 mt-2 hidden md:block">
                  <li><strong>Plantilla cuerpo email</strong> â€” Asunto y cuerpo del correo con variables (nombre, c\u00e9dula, fecha_vencimiento, etc.).</li>
                  <li><strong>Plantilla anexo PDF</strong> â€” Carta de cobranza en PDF generada con variables (monto_total_usd, num_cuotas, fechas_str). Se anexa al email.</li>
                  <li><strong>Documentos PDF anexos</strong> â€” Hasta 2 PDFs fijos que se cargan aqu\u00ed y se anexan siempre a la notificaci\u00f3n (junto con el PDF variable).</li>
                </ol>
              </div>
            )}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleVolver}
          className="flex items-center gap-2"
        >
          <ChevronLeft className="h-4 w-4" />
          Otras secciones de Configuraci\u00f3n
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value={SUBTAB_CUERPO_EMAIL}>
            <FileText className="h-4 w-4 mr-2" />
            Plantilla cuerpo email
          </TabsTrigger>
          <TabsTrigger value={SUBTAB_ANEXO_PDF}>
            <Download className="h-4 w-4 mr-2" />
            Plantilla anexo PDF
          </TabsTrigger>
          <TabsTrigger value={SUBTAB_DOCUMENTOS_PDF}>
            <Link className="h-4 w-4 mr-2" />
            Documentos PDF anexos
          </TabsTrigger>
        </TabsList>

        <TabsContent value={SUBTAB_CUERPO_EMAIL} className="mt-6">
          <PlantillasNotificaciones
            plantillaInicial={plantillaAEditar}
            onPlantillaCargada={() => setPlantillaAEditar(null)}
            tabSeccionActiva={activeTab}
          />
        </TabsContent>

        <TabsContent value={SUBTAB_ANEXO_PDF} className="mt-6 min-h-[400px]">
          <PlantillaAnexoPdf />
        </TabsContent>

        <TabsContent value={SUBTAB_DOCUMENTOS_PDF} className="mt-6 min-h-[400px]">
          <DocumentosPdfAnexos />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Plantillas


