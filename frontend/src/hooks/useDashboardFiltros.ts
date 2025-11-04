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
      console.log('🔧 [useDashboardFiltros] Construyendo params:', { filtrosOriginales: filtros, periodo, paramsConstruidos: result })
      return result
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
      if (filtros.analista && filtros.analista !== '__ALL__') obj.analista = normalizarValor(filtros.analista)
      if (filtros.concesionario && filtros.concesionario !== '__ALL__') obj.concesionario = normalizarValor(filtros.concesionario)
      if (filtros.modelo && filtros.modelo !== '__ALL__') obj.modelo = normalizarValor(filtros.modelo)
      if (filtros.fecha_inicio && filtros.fecha_inicio !== '') obj.fecha_inicio = filtros.fecha_inicio
      if (filtros.fecha_fin && filtros.fecha_fin !== '') obj.fecha_fin = filtros.fecha_fin
      console.log('🔧 [useDashboardFiltros] Construyendo objeto de filtros:', { filtrosOriginales: filtros, objetoConstruido: obj })
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

