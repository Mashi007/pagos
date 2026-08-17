import { Clock, Settings } from 'lucide-react'

import type { EstadisticasPorTab } from '../../services/notificacionService'

type TabIcon = typeof Clock

export type NotificacionesModulo =
  | 'a1dia'
  | 'a2cuotas'
  | 'cobranzas'
  | 'a4cuotas'
  | 'a10dias'
  | 'd2antes'

export type TabId =
  | 'dias_1_atraso'
  | 'prejudicial'
  | 'cobranzas'
  | 'cuotas_4_mas'
  | 'd2antes'
  | 'atraso10dias'
  | 'configuracion'

export function tabsParaModulo(
  modulo: NotificacionesModulo
): { id: TabId; label: string; icon: TabIcon }[] {
  if (modulo === 'a2cuotas') {
    return [
      {
        id: 'prejudicial',
        label: '2 cuotas o mas',
        icon: Clock,
      },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  if (modulo === 'cobranzas') {
    return [
      {
        id: 'cobranzas',
        label: 'Cobranzas',
        icon: Clock,
      },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  if (modulo === 'a4cuotas') {
    return [
      {
        id: 'cuotas_4_mas',
        label: '4 cuotas y más',
        icon: Clock,
      },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  if (modulo === 'd2antes') {
    return [
      { id: 'd2antes', label: '3 días antes', icon: Clock },
      { id: 'configuracion', label: 'Configuración', icon: Settings },
    ]
  }
  if (modulo === 'a10dias') {
    return [
      {
        id: 'atraso10dias',
        label: '1 Cuota',
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
  if (modulo === 'a2cuotas') return 'prejudicial'
  if (modulo === 'cobranzas') return 'cobranzas'
  if (modulo === 'a4cuotas') return 'cuotas_4_mas'
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

    case 'cobranzas':
      return 'cobranzas'

    case 'cuotas_4_mas':
      return 'cuotas_4_mas'

    case 'd2antes':
      return 'd_2_antes_vencimiento'

    case 'atraso10dias':
      return 'dias_10_retraso'

    default:
      return null
  }
}

/** tipo_caso de envio batch asociado a un submodulo / pestana de Notificaciones. */
export function tipoCasoEnvioParaModulo(
  modulo: NotificacionesModulo
): string | null {
  switch (modulo) {
    case 'a2cuotas':
      return 'PREJUDICIAL'
    case 'cobranzas':
      return 'COBRANZAS_EXCEL'
    case 'a4cuotas':
      return 'CUOTAS_4_MAS'
    case 'd2antes':
      return 'PAGO_2_DIAS_ANTES_PENDIENTE'
    case 'a10dias':
      return 'PAGO_10_DIAS_ATRASADO'
    case 'a1dia':
      return 'PAGO_1_DIA_ATRASADO'
    default:
      return null
  }
}

export function tipoCasoEnvioParaTab(
  tab: TabId,
  modulo: NotificacionesModulo
): string | null {
  switch (tab) {
    case 'prejudicial':
      return 'PREJUDICIAL'
    case 'cobranzas':
      return 'COBRANZAS_EXCEL'
    case 'cuotas_4_mas':
      return 'CUOTAS_4_MAS'
    case 'd2antes':
      return 'PAGO_2_DIAS_ANTES_PENDIENTE'
    case 'atraso10dias':
      return 'PAGO_10_DIAS_ATRASADO'
    case 'dias_1_atraso':
      return 'PAGO_1_DIA_ATRASADO'
    case 'configuracion':
      return tipoCasoEnvioParaModulo(modulo)
    default:
      return null
  }
}
