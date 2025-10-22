import React from 'react'

/**
 * Hook personalizado para memoización de funciones
 * Útil para evitar recreaciones innecesarias de callbacks
 */
export const useStableCallback = <T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList
): T => {
  return React.useCallback(callback, deps)
}

/**
 * Hook personalizado para memoización de valores computados
 * Útil para cálculos costosos que no deben repetirse innecesariamente
 */
export const useStableMemo = <T>(
  factory: () => T,
  deps: React.DependencyList
): T => {
  return React.useMemo(factory, deps)
}

/**
 * Componente memoizado genérico
 * Wrapper para React.memo con configuración por defecto
 */
export const MemoizedComponent = React.memo<React.ComponentType<any>>(
  (Component) => Component,
  (prevProps, nextProps) => {
    // Comparación superficial por defecto
    return JSON.stringify(prevProps) === JSON.stringify(nextProps)
  }
)

/**
 * HOC para memoizar componentes con comparación personalizada
 */
export const withMemo = <P extends object>(
  Component: React.ComponentType<P>,
  areEqual?: (prevProps: P, nextProps: P) => boolean
) => {
  return React.memo(Component, areEqual)
}

/**
 * Hook para memoizar objetos complejos
 * Útil para evitar recreaciones de objetos que se pasan como props
 */
export const useStableObject = <T extends object>(
  factory: () => T,
  deps: React.DependencyList
): T => {
  return React.useMemo(factory, deps)
}

/**
 * Hook para memoizar arrays
 * Útil para evitar recreaciones de arrays que se pasan como props
 */
export const useStableArray = <T>(
  factory: () => T[],
  deps: React.DependencyList
): T[] => {
  return React.useMemo(factory, deps)
}

/**
 * Hook para memoizar funciones de filtrado
 * Útil para listas grandes que requieren filtrado frecuente
 */
export const useFilteredData = <T>(
  data: T[],
  filterFn: (item: T) => boolean,
  deps: React.DependencyList
): T[] => {
  return useStableMemo(() => {
    return data.filter(filterFn)
  }, [data, filterFn, ...deps])
}

/**
 * Hook para memoizar funciones de ordenamiento
 * Útil para listas grandes que requieren ordenamiento frecuente
 */
export const useSortedData = <T>(
  data: T[],
  sortFn: (a: T, b: T) => number,
  deps: React.DependencyList
): T[] => {
  return useStableMemo(() => {
    return [...data].sort(sortFn)
  }, [data, sortFn, ...deps])
}

/**
 * Hook para memoizar funciones de búsqueda
 * Útil para búsquedas en listas grandes
 */
export const useSearchData = <T>(
  data: T[],
  searchTerm: string,
  searchFn: (item: T, term: string) => boolean,
  deps: React.DependencyList
): T[] => {
  return useStableMemo(() => {
    if (!searchTerm.trim()) {
      return data
    }
    return data.filter(item => searchFn(item, searchTerm))
  }, [data, searchTerm, searchFn, ...deps])
}

export default {
  useStableCallback,
  useStableMemo,
  MemoizedComponent,
  withMemo,
  useStableObject,
  useStableArray,
  useFilteredData,
  useSortedData,
  useSearchData
}
