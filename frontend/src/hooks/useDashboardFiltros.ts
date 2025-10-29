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
 * Hook para manejar filtros del dashboard de manera centralizada
 * Cualquier KPI nuevo debe usar este hook para aplicar filtros automáticamente
 */
export function useDashboardFiltros(filtros: DashboardFiltros) {
  /**
   * Construye parámetros de query string para endpoints de dashboard
   * Uso: const params = construirParams(); apiClient.get(`/endpoint?${params}`)
   */
  const construirParams = useMemo(() => {
    return (periodo: string = 'mes') => {
      const params = new URLSearchParams()
      params.append('periodo', periodo)
      
      // Aplicar todos los filtros disponibles
      if (filtros.analista) params.append('analista', filtros.analista)
      if (filtros.concesionario) params.append('concesionario', filtros.concesionario)
      if (filtros.modelo) params.append('modelo', filtros.modelo)
      if (filtros.fecha_inicio) params.append('fecha_inicio', filtros.fecha_inicio)
      if (filtros.fecha_fin) params.append('fecha_fin', filtros.fecha_fin)
      if (filtros.consolidado) params.append('consolidado', 'true')
      
      return params.toString()
    }
  }, [filtros])

  /**
   * Construye objeto de filtros para servicios que aceptan objetos
   * Uso: servicio.getStats(construirFiltrosObject())
   */
  const construirFiltrosObject = useMemo(() => {
    return (): {
      analista?: string
      concesionario?: string
      modelo?: string
      fecha_inicio?: string
      fecha_fin?: string
    } => {
      const obj: any = {}
      if (filtros.analista) obj.analista = filtros.analista
      if (filtros.concesionario) obj.concesionario = filtros.concesionario
      if (filtros.modelo) obj.modelo = filtros.modelo
      if (filtros.fecha_inicio) obj.fecha_inicio = filtros.fecha_inicio
      if (filtros.fecha_fin) obj.fecha_fin = filtros.fecha_fin
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

