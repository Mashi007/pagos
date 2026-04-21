import { Calendar, Clock, LayoutList, Settings } from 'lucide-react'

import type { EstadisticasPorTab } from '../../services/notificacionService'

type TabIcon = typeof Clock

export type NotificacionesModulo =
  | 'a1dia'
  | 'a3cuotas'
  | 'a10dias'
  | 'd2antes'
  | 'general'
  | 'fecha'

export type TabId =
  | 'dias_1_atraso'
  | 'prejudicial'
  | 'd2antes'
  | 'atraso10dias'
  | 'general_todos'
  | 'configuracion'

export function tabsParaModulo(
  modulo: NotificacionesModulo
): { id: TabId; label: string; icon: TabIcon }[] {
  if (modulo === 'fecha') {
    return [{ id: 'general_todos', label: 'Fechas', icon: Calendar }]
  }
  if (modulo === 'general') {
    return [{ id: 'general_todos', label: 'General', icon: LayoutList }]
  }
  if (modulo === 'a3cuotas') {
    return [
      {
        id: 'prejudicial',
        label: 'Prejudicial (5+ cuotas)',
        icon: Clock,
      },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  if (modulo === 'd2antes') {
    return [
      { id: 'd2antes', label: '2 días antes', icon: Clock },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  if (modulo === 'a10dias') {
    return [
      {
        id: 'atraso10dias',
        label: '10 días de atraso',
        icon: Clock,
      },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  return [
    {
      id: 'dias_1_atraso',
      label: 'Día siguiente al vencimiento',
      icon: Clock,
    },
    { id: 'configuracion', label: 'Configuración', icon: Settings },
  ]
}

export function tabListadoDefault(modulo: NotificacionesModulo): TabId {
  if (modulo === 'general' || modulo === 'fecha') return 'general_todos'
  if (modulo === 'a3cuotas') return 'prejudicial'
  if (modulo === 'd2antes') return 'd2antes'
  if (modulo === 'a10dias') return 'atraso10dias'
  return 'dias_1_atraso'
}

/** Clave de GET estadisticas-por-tab / rebotados (coincide con tipo_tab en envíos). */
export type EstadisticaTabKey = keyof EstadisticasPorTab

export function tipoParaKpiYRebotados(tab: TabId): EstadisticaTabKey | null {
  switch (tab) {
    case 'dias_1_atraso':
      return 'dias_1_retraso'

    case 'prejudicial':
      return 'prejudicial'

    case 'd2antes':
      return 'd_2_antes_vencimiento'

    case 'atraso10dias':
      return 'dias_10_retraso'

    case 'general_todos':
      return null

    default:
      return null
  }
}
