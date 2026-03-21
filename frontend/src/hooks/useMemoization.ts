import React from 'react'

/**
 * Hook personalizado para memoizaciÃ³n de funciones
 * Ãtil para evitar recreaciones innecesarias de callbacks
 */
export const useStableCallback = <T extends (...args: any[]) => any>(
  callback: T,
  deps: any[]
): T => {
  return React.useCallback(callback, deps)
}

/**
 * Hook personalizado para memoizaciÃ³n de valores computados
 * Ãtil para cÃ¡lculos costosos que no deben repetirse innecesariamente
 */
export const useStableMemo = <T>(
  factory: () => T,
  deps: any[]
): T => {
  return React.useMemo(factory, deps)
}

/**
 * Hook para memoizar objetos complejos
 * Ãtil para evitar recreaciones de objetos que se pasan como props
 */
export const useStableObject = <T extends object>(
  factory: () => T,
  deps: any[]
): T => {
  return React.useMemo(factory, deps)
}

/**
 * Hook para memoizar arrays
 * Ãtil para evitar recreaciones de arrays que se pasan como props
 */
export const useStableArray = <T>(
  factory: () => T[],
  deps: any[]
): T[] => {
  return React.useMemo(factory, deps)
}

/**
 * Hook para memoizar funciones de filtrado
 * Ãtil para listas grandes que requieren filtrado frecuente
 */
export const useFilteredData = <T>(
  data: T[],
  filterFn: (item: T) => boolean,
  deps: any[]
): T[] => {
  return useStableMemo(() => {
    return data.filter(filterFn)
  }, [data, filterFn, ...deps])
}

/**
 * Hook para memoizar funciones de ordenamiento
 * Ãtil para listas grandes que requieren ordenamiento frecuente
 */
export const useSortedData = <T>(
  data: T[],
  sortFn: (a: T, b: T) => number,
  deps: any[]
): T[] => {
  return useStableMemo(() => {
    return [...data].sort(sortFn)
  }, [data, sortFn, ...deps])
}

/**
 * Hook para memoizar funciones de bÃºsqueda
 * Ãtil para bÃºsquedas en listas grandes
 */
export const useSearchData = <T>(
  data: T[],
  searchTerm: string,
  searchFn: (item: T, term: string) => boolean,
  deps: any[]
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
  useStableObject,
  useStableArray,
  useFilteredData,
  useSortedData,
  useSearchData
}
