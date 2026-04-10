import { useState, useEffect } from 'react'

import { useSearchParams, useNavigate } from 'react-router-dom'

import { motion } from 'framer-motion'

import { Settings } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import {
  SECCIONES_CONFIGURACION,
  NOMBRES_SECCION_ESPECIAL,
  findSeccionById as findSeccionByIdHelper,
} from '../constants/configuracionSecciones'

import { KeepAliveConfigSection } from '../components/configuracion/KeepAliveConfigSection'

import {
  ConfigGeneralTab,
  ConfigPlantillasTab,
  ConfigEmailTab,
  ConfigWhatsAppTab,
  ConfigAITab,
  ConfigValidadoresTab,
  ConfigInformePagosTab,
  ConfigAnalistasTab,
  ConfigConcesionariosTab,
  ConfigModelosTab,
  ConfigUsuariosTab,
  ConfigNotificacionesTab,
  ConfigAuditoriaTab,
  ConfigBaseDatosTab,
  ConfigFacturacionTab,
} from '../components/configuracion/tabs'

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

    auditoria: 'auditoria',

    'base-datos': 'baseDatos',

    facturacion: 'facturacion',
  }

  return (tab && map[tab]) || 'general'
}

/** Identificadores de panel: cada uno montado con keep-alive (independiente del resto). */
const CONFIG_SECTION_IDS = [
  'general',
  'notificaciones',
  'plantillas',
  'emailConfig',
  'whatsappConfig',
  'aiConfig',
  'informePagosConfig',
  'auditoria',
  'baseDatos',
  'facturacion',
  'validadores',
  'concesionarios',
  'analistas',
  'modelosVehiculos',
  'usuarios',
] as const

type ConfigSectionId = (typeof CONFIG_SECTION_IDS)[number]

function renderSeccionPanel(id: ConfigSectionId) {
  switch (id) {
    case 'general':
      return <ConfigGeneralTab />

    case 'notificaciones':
      return <ConfigNotificacionesTab />

    case 'plantillas':
      return <ConfigPlantillasTab />

    case 'emailConfig':
      return <ConfigEmailTab />

    case 'whatsappConfig':
      return <ConfigWhatsAppTab />

    case 'aiConfig':
      return <ConfigAITab />

    case 'informePagosConfig':
      return <ConfigInformePagosTab />

    case 'auditoria':
      return <ConfigAuditoriaTab />

    case 'baseDatos':
      return <ConfigBaseDatosTab />

    case 'facturacion':
      return <ConfigFacturacionTab />

    case 'validadores':
      return <ConfigValidadoresTab />

    case 'concesionarios':
      return <ConfigConcesionariosTab />

    case 'analistas':
      return <ConfigAnalistasTab />

    case 'modelosVehiculos':
      return <ConfigModelosTab />

    case 'usuarios':
      return <ConfigUsuariosTab />

    default:
      return <ConfigGeneralTab />
  }
}

const Configuracion = () => {
  const [searchParams] = useSearchParams()

  const navigate = useNavigate()

  const [seccionActiva, setSeccionActiva] = useState(() =>
    tabToSeccion(searchParams.get('tab'))
  )

  useEffect(() => {
    const tab = searchParams.get('tab')

    if (tab === 'programador') {
      navigate('/configuracion?tab=general', { replace: true })
      return
    }

    setSeccionActiva(tabToSeccion(tab))
  }, [searchParams, navigate])

  const findSeccionById = (id: string) =>
    findSeccionByIdHelper(SECCIONES_CONFIGURACION, id)

  const nombresSeccionEspecial = NOMBRES_SECCION_ESPECIAL

  const seccionActivaNormalizada =
    seccionActiva === 'inteligenciaArtificial' ? 'aiConfig' : seccionActiva

  const activePanel: ConfigSectionId = (
    CONFIG_SECTION_IDS as readonly string[]
  ).includes(seccionActivaNormalizada)
    ? (seccionActivaNormalizada as ConfigSectionId)
    : 'general'

  const seccionEncontrada = findSeccionById(seccionActiva)

  const seccionEspecial = nombresSeccionEspecial[seccionActiva]

  const seccion =
    seccionEncontrada ||
    (seccionEspecial
      ? { nombre: seccionEspecial.nombre, icono: seccionEspecial.icono }
      : SECCIONES_CONFIGURACION.find(
          (s: { id: string }) => s.id === seccionActiva
        ))

  const IconComponent = (seccion && seccion.icono) || Settings

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-1">
              <CardTitle className="flex items-center">
                <IconComponent className="mr-2 h-5 w-5" />

                {seccion?.nombre ?? 'Configuracion'}
              </CardTitle>

              <p className="text-sm text-gray-500">
                Cada submenú conserva su propio estado al cambiar de pestaña.
                Guardar ajustes no inicia procesos automáticos en el servidor;
                use las acciones manuales de cada módulo (Programador,
                notificaciones, Gmail, etc.).
              </p>
            </div>
          </CardHeader>

          <CardContent>
            {CONFIG_SECTION_IDS.map(id => (
              <KeepAliveConfigSection
                key={id}
                sectionId={id}
                active={activePanel === id}
              >
                {renderSeccionPanel(id)}
              </KeepAliveConfigSection>
            ))}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  )
}

export default Configuracion
