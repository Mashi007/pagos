import { useQuery } from '@tanstack/react-query'

import { Card, CardContent } from '../ui/card'

import {
  notificacionService,
  type NotificacionPlantilla,
} from '../../services/notificacionService'

import { FileText, Loader2, ChevronRight } from 'lucide-react'

import { Link } from 'react-router-dom'

import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

const TIPO_LABEL: Record<string, string> = {
  PAGO_5_DIAS_ANTES: 'Faltan 5',

  PAGO_3_DIAS_ANTES: 'Faltan 3',

  PAGO_1_DIA_ANTES: 'Falta 1',

  PAGO_2_DIAS_ANTES_PENDIENTE: '2 días antes (al vencimiento)',

  PAGO_DIA_0: 'Hoy vence',

  PAGO_1_DIA_ATRASADO: 'Día siguiente al vencimiento',

  PAGO_10_DIAS_ATRASADO: '10 días retraso',

  PREJUDICIAL: 'Prejudicial',

  COBRANZA: 'Cobranza',
}

interface PlantillasGuardadasListaProps {
  /** Clase CSS para el contenedor */

  className?: string

  /** Máximo de plantillas a mostrar (0 = todas) */

  maxItems?: number

  /** Si true, al mostrarse la pestaña se vuelve a cargar la lista. */

  tabActivo?: boolean
}

export function PlantillasGuardadasLista({
  className = '',
  maxItems = 20,
  tabActivo = true,
}: PlantillasGuardadasListaProps) {
  const { data: plantillas = [], isLoading: loading } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,

    queryFn: () => notificacionService.listarPlantillas(undefined, false),

    staleTime: 1 * 60 * 1000,

    placeholderData: [] as NotificacionPlantilla[],
  })

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
        </CardContent>
      </Card>
    )
  }

  const list = maxItems > 0 ? plantillas.slice(0, maxItems) : plantillas

  const hayMas = plantillas.length > list.length

  return (
    <Card className={className}>
      <CardContent className="pt-4">
        <h4 className="mb-1 flex items-center gap-2 text-sm font-medium text-gray-700">
          <FileText className="h-4 w-4 text-blue-600" />
          Plantillas guardadas
        </h4>

        <p className="mb-3 text-xs text-muted-foreground">
          Plantillas de cuerpo de email creadas y vinculadas por tipo de
          notificación. Editar en la pestaña «Plantilla cuerpo email».
        </p>

        {list.length === 0 ? (
          <p className="text-sm text-gray-500">
            Aún no hay plantillas. Crea una en la pestaña «Plantilla cuerpo
            email».
          </p>
        ) : (
          <ul className="space-y-1.5">
            {list.map(p => (
              <li
                key={p.id}
                className="flex items-center justify-between gap-2 rounded-md border border-gray-100 bg-white px-2 py-1.5 text-sm"
              >
                <span
                  className="truncate font-medium text-gray-800"
                  title={p.nombre || `#${p.id}`}
                >
                  {p.nombre || `Plantilla #${p.id}`}
                </span>

                <span className="flex shrink-0 items-center gap-1">
                  <span className="text-xs text-gray-500">
                    {TIPO_LABEL[p.tipo] || p.tipo}
                  </span>

                  <Link
                    to="/configuracion?tab=plantillas"
                    className="inline-flex items-center text-blue-600 hover:text-blue-800"
                    title="Ir a Plantilla cuerpo email"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </span>
              </li>
            ))}

            {hayMas && (
              <li className="pt-1 text-xs text-gray-500">
                y {plantillas.length - list.length} más. Ver todas en «Plantilla
                cuerpo email».
              </li>
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
