import { useState, useEffect } from 'react'

import { useSearchParams, useNavigate } from 'react-router-dom'

import { PlantillasNotificaciones } from '../components/notificaciones/PlantillasNotificaciones'

import { PlantillaAnexoPdf } from '../components/notificaciones/PlantillaAnexoPdf'

import { VinculacionPlantillaAnexoPdf } from '../components/notificaciones/VinculacionPlantillaAnexoPdf'

import { DocumentosPdfAnexos } from '../components/notificaciones/DocumentosPdfAnexos'

import { DocumentosAlmacenadosPorPestana } from '../components/notificaciones/DocumentosAlmacenadosPorPestana'

import { PlantillasGuardadasLista } from '../components/notificaciones/PlantillasGuardadasLista'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'

import { Button } from '../components/ui/button'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'

import {
  FileText,
  Link as LinkIcon,
  ChevronLeft,
  Download,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Bell,
} from 'lucide-react'


import type { NotificacionPlantilla } from '../services/notificacionService'

import {
  NOTIF_PLANTILLA_TIPO_QUERY,
  normalizarNotifTipoDesdeQuery,
  OPCIONES_SELECT_NOTIF_TIPO_PLANTILLA,
  rutaListadoNotificacionesPorTipoPlantilla,
} from '../constants/notifPlantillaServicioContexto'

const SUBTAB_CUERPO_EMAIL = 'cuerpo-email'

const SUBTAB_ANEXO_PDF = 'anexo-pdf'

const SUBTAB_DOCUMENTOS_PDF = 'documentos-pdf'

export function Plantillas() {
  const [searchParams, setSearchParams] = useSearchParams()

  const navigate = useNavigate()

  const subtabFromUrl = searchParams.get('subtab')

  const tipoServicioPlantilla = normalizarNotifTipoDesdeQuery(
    searchParams.get(NOTIF_PLANTILLA_TIPO_QUERY)
  )

  const [plantillaAEditar, setPlantillaAEditar] =
    useState<NotificacionPlantilla | null>(null)

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
    else if (value === SUBTAB_DOCUMENTOS_PDF)
      next.set('subtab', SUBTAB_DOCUMENTOS_PDF)
    else next.delete('subtab')

    setSearchParams(next, { replace: true })
  }

  const handleVolver = () => {
    navigate('/configuracion')
  }

  const cambiarCasoPlantillaEmail = (v: string) => {
    const next = new URLSearchParams(searchParams)
    if (v === 'PAGO_1_DIA_ATRASADO') next.delete(NOTIF_PLANTILLA_TIPO_QUERY)
    else next.set(NOTIF_PLANTILLA_TIPO_QUERY, v)
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <h1 className="text-xl font-bold">Plantillas de notificaciones</h1>

          <p className="text-sm text-gray-500">
            Tres piezas para cada envío: plantilla de email (pestaña 1), PDF
            variable carta de cobranza (pestaña 2) y al menos un PDF fijo por
            caso (pestaña 3). El servidor no envía si falta alguna (salvo
            emergencia con NOTIFICACIONES_PAQUETE_ESTRICTO=false).
          </p>

          <div className="mt-3 max-w-xl space-y-1">
            <label
              htmlFor="notif-tipo-plantillas"
              className="text-xs font-medium text-gray-600"
            >
              Caso de notificación (plantillas nuevas de email y editor HTML)
            </label>

            <Select
              value={tipoServicioPlantilla}
              onValueChange={cambiarCasoPlantillaEmail}
            >
              <SelectTrigger
                id="notif-tipo-plantillas"
                className="h-9 bg-white"
              >
                <SelectValue />
              </SelectTrigger>

              <SelectContent>
                {OPCIONES_SELECT_NOTIF_TIPO_PLANTILLA.map(o => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <p className="text-xs text-gray-500">
              Si entra desde el menú lateral sin contexto, elija aquí el mismo
              caso que en Notificaciones para no guardar plantillas en el tipo
              equivocado.
            </p>
          </div>

          <div className="mt-3 overflow-hidden rounded-lg border border-blue-100 bg-blue-50/50 text-sm text-gray-700">
            <button
              type="button"
              onClick={() => setResumenAbierto(!resumenAbierto)}
              className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left font-medium text-gray-800 transition-colors hover:bg-blue-100/50"
              aria-expanded={resumenAbierto}
            >
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-blue-600" />
                Resumen de configuración
              </span>

              {resumenAbierto ? (
                <ChevronUp className="h-4 w-4 shrink-0" />
              ) : (
                <ChevronDown className="h-4 w-4 shrink-0" />
              )}
            </button>

            {resumenAbierto && (
              <div className="border-t border-blue-100 px-3 pb-3 pt-0">
                <p className="mt-2 text-gray-600 md:hidden">
                  Cada correo debe llevar: 1) Cuerpo email. 2) PDF variable
                  (Carta_Cobranza). 3) Al menos un PDF fijo (pestaña 3 + adjunto
                  global si aplica).
                </p>

                <ol className="mt-2 hidden list-inside list-decimal space-y-0.5 text-gray-600 md:block">
                  <li>
                    <strong>Plantilla cuerpo email</strong> - Asunto y cuerpo
                    del correo con variables (nombre, cédula, fecha_vencimiento,
                    etc.).
                  </li>

                  <li>
                    <strong>Plantilla anexo PDF</strong> - Carta de cobranza en
                    PDF generada con variables (monto_total_usd, num_cuotas,
                    fechas_str). Se anexa al email.
                  </li>

                  <li>
                    <strong>Documentos PDF anexos</strong> - PDFs fijos que se
                    suben aquí y se vinculan a cada caso (día siguiente al
                    venc., 3 o 5 días de retraso, prejudicial). Junto con el PDF
                    global de cobranza (si está configurado) cumplen el
                    requisito de documento fijo del paquete.
                  </li>
                </ol>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="default"
            size="sm"
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
            onClick={() => {
              navigate(
                rutaListadoNotificacionesPorTipoPlantilla(tipoServicioPlantilla)
              )
            }}
          >
            <Bell className="h-4 w-4" />
            Ir a Notificaciones
          </Button>

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
      </div>

      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="w-full"
      >
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value={SUBTAB_CUERPO_EMAIL}>
            <FileText className="mr-2 h-4 w-4" />
            Plantilla cuerpo email
          </TabsTrigger>

          <TabsTrigger value={SUBTAB_ANEXO_PDF}>
            <Download className="mr-2 h-4 w-4" />
            Plantilla anexo PDF
          </TabsTrigger>

          <TabsTrigger value={SUBTAB_DOCUMENTOS_PDF}>
            <LinkIcon className="mr-2 h-4 w-4" />
            Documentos PDF anexos
          </TabsTrigger>
        </TabsList>

        <TabsContent value={SUBTAB_CUERPO_EMAIL} className="mt-6">
          <PlantillasNotificaciones
            plantillaInicial={plantillaAEditar}
            onPlantillaCargada={() => setPlantillaAEditar(null)}
            tabSeccionActiva={activeTab}
            tipoServicioPlantilla={tipoServicioPlantilla}
          />
        </TabsContent>

        <TabsContent value={SUBTAB_ANEXO_PDF} className="mt-6 min-h-[400px]">
          <div className="mb-6">
            <PlantillasGuardadasLista
              className="border-blue-200 bg-blue-50/30"
              tabActivo={activeTab === SUBTAB_ANEXO_PDF}
            />
          </div>

          <VinculacionPlantillaAnexoPdf />

          <PlantillaAnexoPdf />

          <p className="mt-6 text-sm text-gray-600">
            Los PDF fijos se suben en la pestaña «Documentos PDF anexos». El
            bloque siguiente resume qué archivos hay por caso para comprobar la
            vinculación sin salir de esta vista.
          </p>

          <div className="mt-3">
            <DocumentosAlmacenadosPorPestana
              permitirEliminar={true}
              titulo="Documentos almacenados por pestaña (confirmar vinculación)"
              className="border-violet-200 bg-violet-50/30"
              tabActivo={activeTab === SUBTAB_ANEXO_PDF}
            />
          </div>
        </TabsContent>

        <TabsContent
          value={SUBTAB_DOCUMENTOS_PDF}
          className="mt-6 min-h-[400px]"
        >
          <div className="mb-6">
            <PlantillasGuardadasLista
              className="border-blue-200 bg-blue-50/30"
              tabActivo={activeTab === SUBTAB_DOCUMENTOS_PDF}
            />
          </div>

          <DocumentosPdfAnexos />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Plantillas
