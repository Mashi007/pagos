import { useMemo } from 'react'

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
 * Flag para habilitar logs de depuración (solo en desarrollo con flag explícito)
 * Por defecto está deshabilitado para evitar logs en producción
 */
const DEBUG_LOGS = import.meta.env.MODE === 'development' && import.meta.env.VITE_DEBUG_FILTROS === 'true'

/**
 * Hook para manejar filtros del dashboard de manera centralizada
 * Cualquier KPI nuevo debe usar este hook para aplicar filtros automáticamente
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
   * Construye parámetros de query string para endpoints de dashboard
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
        console.log('🔧 [useDashboardFiltros] Construyendo params:', { filtrosOriginales: filtros, periodo, paramsConstruidos: result })
      }
      return result
    }
  }, [filtros])

  /**
   * Calcula fecha_inicio y fecha_fin basado en el período
   */
  const calcularFechasPorPeriodo = (periodo: string): { fecha_inicio: string; fecha_fin: string } => {
    const hoy = new Date()
    let fecha_inicio: Date
    let fecha_fin: Date = new Date(hoy)

    switch (periodo) {
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
      case 'año':
        fecha_inicio = new Date(hoy.getFullYear(), 0, 1)
        fecha_inicio.setHours(0, 0, 0, 0)
        fecha_fin = new Date(hoy.getFullYear(), 11, 31)
        fecha_fin.setHours(23, 59, 59, 999)
        break
      default:
        fecha_inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
        fecha_inicio.setHours(0, 0, 0, 0)
        fecha_fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0)
        fecha_fin.setHours(23, 59, 59, 999)
    }

    return {
      fecha_inicio: fecha_inicio.toISOString().split('T')[0],
      fecha_fin: fecha_fin.toISOString().split('T')[0],
    }
  }

  /**
   * Construye objeto de filtros para servicios que aceptan objetos
   * Uso: servicio.getStats(construirFiltrosObject(periodo))
   * ✅ ACTUALIZADO: Ahora incluye fecha_inicio/fecha_fin basado en período si no están definidos
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

      // ✅ Si hay fecha_inicio/fecha_fin explícitos, usarlos; si no, calcular del período
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
        console.log('🔧 [useDashboardFiltros] Construyendo objeto de filtros:', { filtrosOriginales: filtros, periodo, objetoConstruido: obj })
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
   * Obtiene el número de filtros activos
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

