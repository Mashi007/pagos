import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Settings, Save, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import {
  SECCIONES_ConfiguraciÃ³n,
  NOMBRES_SECCION_ESPECIAL,
  findSeccionById as findSeccionByIdHelper,
} from '../constants/ConfiguraciÃ³nSecciones'
import {
  ConfigGeneralTab,
  ConfigPlantillasTab,
  ConfigEmailTab,
  ConfigWhatsAppTab,
  ConfigAITab,
  ConfigValidadoresTab,
  ConfigOCRTab,
  ConfigInformePagosTab,
  ConfigAnalistasTab,
  ConfigConcesionariosTab,
  ConfigModelosTab,
  ConfigUsuariosTab,
  ConfigNotificacionesTab,
  ConfigProgramadorTab,
  ConfigAuditoriaTab,
  ConfigBaseDatosTab,
  ConfigFacturacionTab,
} from '../components/ConfiguraciÃ³n/tabs'

function tabToSeccion(tab: string | null): string {
  const map: Record<string, string> = {
    email: 'emailConfig',
    whatsapp: 'whatsappConfig',
    ai: 'aiConfig',
    'informe-pagos': 'informePagosConfig',
    ocr: 'informePagosConfig',
    plantillas: 'plantillas',
    validadores: 'validadores',
    analistas: 'analistas',
    concesionarios: 'concesionarios',
    modelos: 'modelosVehiculos',
    usuarios: 'usuarios',
    notificaciones: 'notificaciones',
    programador: 'programador',
    auditoria: 'auditoria',
    'base-datos': 'baseDatos',
    facturacion: 'facturacion',
  }
  return (tab && map[tab]) || 'general'
}

const SECTIONS_WITH_OWN_SAVE = ['emailConfig', 'whatsappConfig', 'aiConfig', 'informePagosConfig', 'plantillas']
const SECTIONS_SELF_LOADING = ['plantillas', 'emailConfig', 'whatsappConfig', 'aiConfig', 'informePagosConfig']

const Configuracion = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [seccionActiva, setSeccionActiva] = useState(() => tabToSeccion(searchParams.get('tab')))
  const [loading, setLoading] = useState(false)
  const [cambiosPendientes, setCambiosPendientes] = useState(false)

  useEffect(() => {
    const tab = searchParams.get('tab')
    setSeccionActiva(tabToSeccion(tab))
  }, [searchParams])

  useEffect(() => {
    if (seccionActiva === 'scheduler') navigate('/scheduler')
  }, [seccionActiva, navigate])

  const findSeccionById = (id: string) => findSeccionByIdHelper(SECCIONES_ConfiguraciÃ³n, id)
  const nombresSeccionEspecial = NOMBRES_SECCION_ESPECIAL

  const renderContenidoSeccion = () => {
    if (seccionActiva === 'scheduler') return null
    switch (seccionActiva) {
      case 'general': return <ConfigGeneralTab />
      case 'notificaciones': return <ConfigNotificacionesTab />
      case 'plantillas': return <ConfigPlantillasTab />
      case 'emailConfig': return <ConfigEmailTab />
      case 'whatsappConfig': return <ConfigWhatsAppTab />
      case 'aiConfig':
      case 'inteligenciaArtificial': return <ConfigAITab />
      case 'informePagosConfig': return <ConfigInformePagosTab />
      case 'programador': return <ConfigProgramadorTab />
      case 'auditoria': return <ConfigAuditoriaTab />
      case 'baseDatos': return <ConfigBaseDatosTab />
      case 'facturacion': return <ConfigFacturacionTab />
      case 'validadores': return <ConfigValidadoresTab />
      case 'concesionarios': return <ConfigConcesionariosTab />
      case 'analistas': return <ConfigAnalistasTab />
      case 'modelosVehiculos': return <ConfigModelosTab />
      case 'usuarios': return <ConfigUsuariosTab />
      default: return <ConfigGeneralTab />
    }
  }

  const seccion = findSeccionById(seccionActiva) ||
    (nombresSeccionEspecial[seccionActiva]
      ? { nombre: nombresSeccionEspecial[seccionActiva].nombre, icono: nombresSeccionEspecial[seccionActiva].icono }
      : SECCIONES_ConfiguraciÃ³n.find((s: { id: string }) => s.id === seccionActiva))
  const IconComponent = seccion?.icono || Settings
  const showGuardar = cambiosPendientes && !SECTIONS_WITH_OWN_SAVE.includes(seccionActiva)
  const showLoading = loading && !SECTIONS_SELF_LOADING.includes(seccionActiva)

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="space-y-6">
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center">
                  <IconComponent className="mr-2 h-5 w-5" />
                  {seccion?.nombre ?? 'ConfiguraciÃ³n'}
                </CardTitle>
              </div>
              <div className="flex space-x-2">
                {showGuardar && (
                  <>
                    <Badge variant="secondary" className="animate-pulse">Cambios pendientes</Badge>
                    <Button disabled className={cambiosPendientes ? 'animate-pulse' : ''}>
                      <Save className="mr-2 h-4 w-4" /> Guardar
                    </Button>
                  </>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {showLoading && (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="h-6 w-6 animate-spin text-blue-600 mr-2" />
                <span className="text-gray-600">Cargando ConfiguraciÃ³n...</span>
              </div>
            )}
            {(!loading || SECTIONS_SELF_LOADING.includes(seccionActiva)) && renderContenidoSeccion()}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  )
}

export default Configuracion


