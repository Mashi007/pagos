Ã¯Â»Â¿import { useMemo } from 'react'

/**
 * Tipos de filtros disponibles para el dashboard
 */
export interface DashboardFiltros {
  analista?: string
  concesionario?: string
  modelo?: string
  fecha_inicio?: string
  fecha_fin?: string
  mes?: string
  consolidado?: boolean
}

/**
 * Flag para habilitar logs de depuraciÃÂ³n (solo en desarrollo con flag explÃÂ­cito)
 * Por defecto estÃÂ¡ deshabilitado para evitar logs en producciÃÂ³n
 */
const DEBUG_LOGS = import.meta.env.MODE === 'development' && import.meta.env.VITE_DEBUG_FILTROS === 'true'

/**
 * Hook para manejar filtros del dashboard de manera centralizada
 * Cualquier KPI nuevo debe usar este hook para aplicar filtros automÃÂ¡ticamente
 */
export function useDashboardFiltros(filtros: DashboardFiltros) {
  // Normaliza valores provenientes del backend que puedan venir con forma de tupla string: ("VALOR",)
  const normalizarValor = (valor?: string): string | undefined => {
    if (!valor) return valor
    let s = String(valor).trim()
    // Casos: ('ABC',) o ("ABC",)
    if ((s.startsWith("('") && s.endsWith("',)")) || (s.startsWith('(\"') && s.endsWith('\",)'))) {
      s = s.slice(2, -2)
    } else if (s.startsWith('(') && s.endsWith(',)')) {
      s = s.slice(1, -2)
    }
    // Remover comillas sobrantes en extremos
    s = s.replace(/^['\"]/,'').replace(/['\"]$/,'').trim()
    return s
  }
  /**
   * Construye parÃÂ¡metros de query string para endpoints de dashboard
   * Uso: const params = construirParams(); apiClient.get(`/endpoint?${params}`)
   */
  const construirParams = useMemo(() => {
    return (periodo: string = 'mes') => {
      const params = new URLSearchParams()
      params.append('periodo', periodo)

      // Aplicar todos los filtros disponibles (ignorar valores especiales)
      if (filtros.analista && filtros.analista !== '__ALL__') params.append('analista', normalizarValor(filtros.analista)!)
      if (filtros.concesionario && filtros.concesionario !== '__ALL__') params.append('concesionario', normalizarValor(filtros.concesionario)!)
      if (filtros.modelo && filtros.modelo !== '__ALL__') params.append('modelo', normalizarValor(filtros.modelo)!)
      if (filtros.fecha_inicio && filtros.fecha_inicio !== '') params.append('fecha_inicio', filtros.fecha_inicio)
      if (filtros.fecha_fin && filtros.fecha_fin !== '') params.append('fecha_fin', filtros.fecha_fin)
      if (filtros.consolidado) params.append('consolidado', 'true')

      const result = params.toString()
      if (DEBUG_LOGS) {
        console.log('Ã°ÂÂÂ§ [useDashboardFiltros] Construyendo params:', { filtrosOriginales: filtros, periodo, paramsConstruidos: result })
      }
      return result
    }
  }, [filtros])

  /**
   * Calcula fecha_inicio y fecha_fin basado en el perÃÂ­odo
   */
  const calcularFechasPorPeriodo = (periodo: string): { fecha_inicio: string; fecha_fin: string } => {
    const hoy = new Date()
    let fecha_inicio: Date
    let fecha_fin: Date = new Date(hoy)

    switch (periodo) {
      case 'dÃÂ­a':
      case 'dia':
        fecha_inicio = new Date(hoy)
        fecha_inicio.setHours(0, 0, 0, 0)
        fecha_fin.setHours(23, 59, 59, 999)
        break
      case 'semana':
        // Lunes de esta semana
        fecha_inicio = new Date(hoy)
        const diaSemana = fecha_inicio.getDay()
        const diff = fecha_inicio.getDate() - diaSemana + (diaSemana === 0 ? -6 : 1) // Ajustar para que lunes = 1
        fecha_inicio.setDate(diff)
        fecha_inicio.setHours(0, 0, 0, 0)
        // Viernes de esta semana
        fecha_fin = new Date(fecha_inicio)
        fecha_fin.setDate(fecha_inicio.getDate() + 4) // Viernes
        fecha_fin.setHours(23, 59, 59, 999)
        break
      case 'mes':
        fecha_inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
        fecha_inicio.setHours(0, 0, 0, 0)
        fecha_fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0)
        fecha_fin.setHours(23, 59, 59, 999)
        break
      case 'aÃÂ±o':
        fecha_inicio = new Date(hoy.getFullYear(), 0, 1)
        fecha_inicio.setHours(0, 0, 0, 0)
        fecha_fin = new Date(hoy.getFullYear(), 11, 31)
        fecha_fin.setHours(23, 59, 59, 999)
        break
      case 'ultimos_12_meses':
        fecha_fin = new Date(hoy)
        fecha_fin.setHours(23, 59, 59, 999)
        fecha_inicio = new Date(hoy)
        fecha_inicio.setMonth(fecha_inicio.getMonth() - 12)
        fecha_inicio.setHours(0, 0, 0, 0)
        break
      default:
        fecha_inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
        fecha_inicio.setHours(0, 0, 0, 0)
        fecha_fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0)
        fecha_fin.setHours(23, 59, 59, 999)
    }

    // Formato YYYY-MM-DD en hora local (evita que 31 dic 23:59 UTC-5 se convierta en 2027-01-01 en UTC)
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return {
      fecha_inicio: fmt(fecha_inicio),
      fecha_fin: fmt(fecha_fin),
    }
  }

  /**
   * Construye objeto de filtros para servicios que aceptan objetos
   * Uso: servicio.getStats(construirFiltrosObject(periodo))
   * Ã¢ÂÂ ACTUALIZADO: Ahora incluye fecha_inicio/fecha_fin basado en perÃÂ­odo si no estÃÂ¡n definidos
   */
  const construirFiltrosObject = useMemo(() => {
    return (periodo?: string): {
      analista?: string
      concesionario?: string
      modelo?: string
      fecha_inicio?: string
      fecha_fin?: string
    } => {
      const obj: any = {}
      if (filtros.analista && filtros.analista !== '__ALL__') obj.analista = normalizarValor(filtros.analista)
      if (filtros.concesionario && filtros.concesionario !== '__ALL__') obj.concesionario = normalizarValor(filtros.concesionario)
      if (filtros.modelo && filtros.modelo !== '__ALL__') obj.modelo = normalizarValor(filtros.modelo)

      // Ã¢ÂÂ Si hay fecha_inicio/fecha_fin explÃÂ­citos, usarlos; si no, calcular del perÃÂ­odo
      if (filtros.fecha_inicio && filtros.fecha_inicio !== '') {
        obj.fecha_inicio = filtros.fecha_inicio
      } else if (periodo) {
        const fechas = calcularFechasPorPeriodo(periodo)
        obj.fecha_inicio = fechas.fecha_inicio
      }

      if (filtros.fecha_fin && filtros.fecha_fin !== '') {
        obj.fecha_fin = filtros.fecha_fin
      } else if (periodo) {
        const fechas = calcularFechasPorPeriodo(periodo)
        obj.fecha_fin = fechas.fecha_fin
      }

      if (DEBUG_LOGS) {
        console.log('Ã°ÂÂÂ§ [useDashboardFiltros] Construyendo objeto de filtros:', { filtrosOriginales: filtros, periodo, objetoConstruido: obj })
      }
      return obj
    }
  }, [filtros])

  /**
   * Verifica si hay filtros activos
   */
  const tieneFiltrosActivos = useMemo(() => {
    return Boolean(
      filtros.analista ||
      filtros.concesionario ||
      filtros.modelo ||
      filtros.fecha_inicio ||
      filtros.fecha_fin
    )
  }, [filtros])

  /**
   * Obtiene el nÃÂºmero de filtros activos
   */
  const cantidadFiltrosActivos = useMemo(() => {
    return Object.values(filtros).filter(v => v !== undefined && v !== '').length
  }, [filtros])

  return {
    construirParams,
    construirFiltrosObject,
    tieneFiltrosActivos,
    cantidadFiltrosActivos,
    filtros, // Exportar filtros para acceso directo si es necesario
  }
}

