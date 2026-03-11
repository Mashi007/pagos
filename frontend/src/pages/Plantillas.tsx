import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { PlantillasNotificaciones } from '../components/notificaciones/PlantillasNotificaciones'
import { GestionVariables } from '../components/notificaciones/GestionVariables'
import { PlantillaPdfCobranza } from '../components/notificaciones/PlantillaPdfCobranza'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Button } from '../components/ui/button'
import { FileText, Database, ChevronLeft, FileDown, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react'

const SUBTAB_PLANTILLAS = 'plantillas'
const SUBTAB_VARIABLES = 'variables'
const SUBTAB_PDF_COBRANZA = 'pdf-cobranza'

export function Plantillas() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const subtabFromUrl = searchParams.get('subtab')
  const [plantillaAEditar, setPlantillaAEditar] = useState<any>(null)
  const [resumenAbierto, setResumenAbierto] = useState(false)
  const [activeTab, setActiveTab] = useState(() => {
    if (subtabFromUrl === SUBTAB_VARIABLES) return SUBTAB_VARIABLES
    if (subtabFromUrl === SUBTAB_PDF_COBRANZA) return SUBTAB_PDF_COBRANZA
    return SUBTAB_PLANTILLAS
  })

  // Sincronizar pestaña activa con URL
  useEffect(() => {
    const sub = searchParams.get('subtab')
    if (sub === SUBTAB_VARIABLES) setActiveTab(SUBTAB_VARIABLES)
    else if (sub === SUBTAB_PDF_COBRANZA) setActiveTab(SUBTAB_PDF_COBRANZA)
    else if (sub === SUBTAB_PLANTILLAS) setActiveTab(SUBTAB_PLANTILLAS)
  }, [searchParams])

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    const next = new URLSearchParams(searchParams)
    if (value === SUBTAB_VARIABLES) next.set('subtab', SUBTAB_VARIABLES)
    else if (value === SUBTAB_PDF_COBRANZA) next.set('subtab', SUBTAB_PDF_COBRANZA)
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
          <p className="text-sm text-gray-500">Herramienta de construcción de plantillas y gestión de variables (solo Administrador)</p>
          <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50/50 text-sm text-gray-700 overflow-hidden">
            <button
              type="button"
              onClick={() => setResumenAbierto(!resumenAbierto)}
              className="w-full px-3 py-2 flex items-center justify-between gap-2 text-left font-medium text-gray-800 hover:bg-blue-100/50 transition-colors"
              aria-expanded={resumenAbierto}
            >
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 text-blue-600 shrink-0" />
                Resumen de configuración
              </span>
              {resumenAbierto ? <ChevronUp className="h-4 w-4 shrink-0" /> : <ChevronDown className="h-4 w-4 shrink-0" />}
            </button>
            {resumenAbierto && (
              <div className="px-3 pb-3 pt-0 border-t border-blue-100">
                <p className="text-gray-600 mt-2 md:hidden">1) Email con variables. 2) Anexo PDF con variables. 3) PDF fijo.</p>
                <ol className="list-decimal list-inside space-y-0.5 text-gray-600 mt-2 hidden md:block">
                  <li><strong>Plantilla email (con variables)</strong> — Pestaña &quot;Plantillas&quot;: asunto y cuerpo del correo con variables (nombre, cédula, fecha_vencimiento, etc.).</li>
                  <li><strong>Anexo PDF (con variables)</strong> — Pestaña &quot;PDF Cobranza&quot;: carta de cobranza en PDF con variables monto_total_usd, num_cuotas, fechas_str.</li>
                  <li><strong>Carga PDF fijo</strong> — Pestaña &quot;PDF Cobranza&quot;: documento PDF estático que se anexa siempre al mismo correo, sin cambios.</li>
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
          Otras secciones de Configuración
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value={SUBTAB_PLANTILLAS}>
            <FileText className="h-4 w-4 mr-2" />
            Plantillas
          </TabsTrigger>
          <TabsTrigger value={SUBTAB_PDF_COBRANZA}>
            <FileDown className="h-4 w-4 mr-2" />
            PDF Cobranza
          </TabsTrigger>
          <TabsTrigger value={SUBTAB_VARIABLES}>
            <Database className="h-4 w-4 mr-2" />
            Variables
          </TabsTrigger>
        </TabsList>

        <TabsContent value={SUBTAB_PLANTILLAS} className="mt-6">
          <PlantillasNotificaciones
            plantillaInicial={plantillaAEditar}
            onPlantillaCargada={() => setPlantillaAEditar(null)}
            tabSeccionActiva={activeTab}
          />
        </TabsContent>

        <TabsContent value={SUBTAB_PDF_COBRANZA} className="mt-6 min-h-[400px]">
          <PlantillaPdfCobranza />
        </TabsContent>

        <TabsContent value={SUBTAB_VARIABLES} className="mt-6 min-h-[400px]">
          <GestionVariables />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Plantillas


