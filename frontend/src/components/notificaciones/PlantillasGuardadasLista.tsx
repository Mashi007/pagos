import { useState, useEffect } from 'react'
import { Card, CardContent } from '../ui/card'
import { notificacionService, type NotificacionPlantilla } from '../../services/notificacionService'
import { FileText, Loader2, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

const TIPO_LABEL: Record<string, string> = {
  PAGO_5_DIAS_ANTES: 'Faltan 5',
  PAGO_3_DIAS_ANTES: 'Faltan 3',
  PAGO_1_DIA_ANTES: 'Falta 1',
  PAGO_DIA_0: 'Hoy vence',
  PAGO_1_DIA_ATRASADO: '1 día retraso',
  PAGO_3_DIAS_ATRASADO: '3 días retraso',
  PAGO_5_DIAS_ATRASADO: '5 días atraso',
  PREJUDICIAL: 'Prejudicial',
  MORA_90: '90+ mora',
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

export function PlantillasGuardadasLista({ className = '', maxItems = 20, tabActivo = true }: PlantillasGuardadasListaProps) {
  const [plantillas, setPlantillas] = useState<NotificacionPlantilla[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    notificacionService
      .listarPlantillas(undefined, false)
      .then((data) => {
        if (!cancelled) setPlantillas(data || [])
      })
      .catch(() => {
        if (!cancelled) setPlantillas([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const cargar = () => {
    setLoading(true)
    notificacionService.listarPlantillas(undefined, false).then((data) => setPlantillas(data || [])).catch(() => setPlantillas([])).finally(() => setLoading(false))
  }
  useEffect(() => { if (tabActivo) cargar() }, [tabActivo])

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
        <h4 className="text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-600" />
          Plantillas guardadas
        </h4>
        <p className="text-xs text-muted-foreground mb-3">
          Plantillas de cuerpo de email creadas y vinculadas por tipo de notificación. Editar en la pestaña «Plantilla cuerpo email».
        </p>
        {list.length === 0 ? (
          <p className="text-sm text-gray-500">Aún no hay plantillas. Crea una en la pestaña «Plantilla cuerpo email».</p>
        ) : (
          <ul className="space-y-1.5">
            {list.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-2 text-sm rounded-md border border-gray-100 bg-white px-2 py-1.5">
                <span className="truncate font-medium text-gray-800" title={p.nombre || `#${p.id}`}>
                  {p.nombre || `Plantilla #${p.id}`}
                </span>
                <span className="shrink-0 flex items-center gap-1">
                  <span className="text-xs text-gray-500">
                    {TIPO_LABEL[p.tipo] || p.tipo}
                  </span>
                  <Link
                    to="/configuracion?tab=plantillas"
                    className="text-blue-600 hover:text-blue-800 inline-flex items-center"
                    title="Ir a Plantilla cuerpo email"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </span>
              </li>
            ))}
            {hayMas && (
              <li className="text-xs text-gray-500 pt-1">
                y {plantillas.length - list.length} más. Ver todas en «Plantilla cuerpo email».
              </li>
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
