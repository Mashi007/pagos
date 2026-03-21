import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader } from '../ui/card'
import { Badge } from '../ui/badge'
import { Link } from 'react-router-dom'
import { FileText, Link as LinkIcon, Loader2, Settings } from 'lucide-react'
import { emailConfigService } from '../../services/notificacionService'
import { CRITERIOS } from './ConfiguracionNotificaciones'
import type { ConfigEnvioItem } from './ConfiguracionNotificaciones'
import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

const CLAVES_GLOBALES = ['modo_pruebas', 'email_pruebas', 'emails_pruebas'] as const

/**
 * Muestra la plantilla "Plantilla anexo PDF" y a qué pestañas de notificación está vinculada
 * (tipos con incluir_pdf_anexo === true en la configuración de envíos).
 */
export function VinculacionPlantillaAnexoPdf() {
  const { data: rawEnvios, isLoading: cargando } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
    queryFn: () => emailConfigService.obtenerConfiguracionEnvios(),
    staleTime: 1 * 60 * 1000,
  })
  const pestanasConPdf = useMemo(() => {
    if (!rawEnvios || typeof rawEnvios !== 'object') return []
    const raw = rawEnvios as Record<string, unknown>
    const tipoToLabel = new Map(CRITERIOS.map((c) => [c.tipo, c.label]))
    const conPdf: { tipo: string; label: string }[] = []
    for (const key of Object.keys(raw)) {
      if (CLAVES_GLOBALES.includes(key as (typeof CLAVES_GLOBALES)[number])) continue
      const item = raw[key] as ConfigEnvioItem | undefined
      if (item && typeof item === 'object' && item.incluir_pdf_anexo === true) {
        const label = tipoToLabel.get(key) ? key
        conPdf.push({ tipo: key, label })
      }
    }
    return conPdf
  }, [rawEnvios])

  return (
    <Card className="mb-6 border-blue-100 bg-blue-50/30">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            <h2 className="text-base font-semibold text-gray-900">Plantilla anexo PDF</h2>
          </div>
          <Link
            to="/notificaciones?tab=configuracion"
            className="text-sm text-blue-600 hover:underline flex items-center gap-1"
          >
            <Settings className="h-4 w-4" />
            Configurar envíos
          </Link>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          Esta plantilla genera el archivo <strong>Carta_Cobranza.pdf</strong> que se adjunta al correo. Se usa en las pestañas de notificación que tengan la opción &quot;PDF&quot; activa.
        </p>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center gap-2 text-sm text-gray-700 mb-2">
          <LinkIcon className="h-4 w-4 text-blue-600 shrink-0" />
          <span className="font-medium">Vinculada a las siguientes pestañas:</span>
        </div>
        {cargando ? (
          <div className="flex items-center gap-2 text-gray-500 text-sm py-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando…
          </div>
        ) : pestanasConPdf.length === 0 ? (
          <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
            Ninguna pestaña tiene el PDF activo. Activa la opción &quot;PDF&quot; en{' '}
            <Link to="/notificaciones?tab=configuracion" className="text-blue-600 hover:underline font-medium">
              Notificaciones → Configuración
            </Link>{' '}
            para cada tipo que deba llevar la carta de cobranza.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {pestanasConPdf.map(({ tipo, label }) => (
              <Badge
                key={tipo}
                variant="secondary"
                className="bg-white border border-blue-200 text-blue-900 font-normal"
              >
                {label}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
