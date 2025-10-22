import React, { memo, useMemo, useCallback } from 'react'

/**
 * Hook personalizado para memoización de funciones
 * Útil para evitar recreaciones innecesarias de callbacks
 */
export const useStableCallback = <T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList
): T => {
  return useCallback(callback, deps)
}

/**
 * Hook personalizado para memoización de valores computados
 * Útil para cálculos costosos que no deben repetirse innecesariamente
 */
export const useStableMemo = <T>(
  factory: () => T,
  deps: React.DependencyList
): T => {
  return useMemo(factory, deps)
}

/**
 * Componente memoizado genérico
 * Wrapper para React.memo con configuración por defecto
 */
export const MemoizedComponent = memo<React.ComponentType<any>>(
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
  return memo(Component, areEqual)
}

/**
 * Hook para memoizar objetos complejos
 * Útil para evitar recreaciones de objetos que se pasan como props
 */
export const useStableObject = <T extends object>(
  factory: () => T,
  deps: React.DependencyList
): T => {
  return useMemo(factory, deps)
}

/**
 * Hook para memoizar arrays
 * Útil para evitar recreaciones de arrays que se pasan como props
 */
export const useStableArray = <T>(
  factory: () => T[],
  deps: React.DependencyList
): T[] => {
  return useMemo(factory, deps)
}

/**
 * Componente de ejemplo memoizado
 * Demuestra cómo usar memoización en componentes
 */
interface MemoizedButtonProps {
  onClick: () => void
  children: React.ReactNode
  variant?: 'primary' | 'secondary'
  disabled?: boolean
}

export const MemoizedButton = memo<MemoizedButtonProps>(
  ({ onClick, children, variant = 'primary', disabled = false }) => {
    const buttonClasses = useStableMemo(() => {
      const baseClasses = 'px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2'
      
      if (disabled) {
        return `${baseClasses} bg-gray-300 text-gray-500 cursor-not-allowed`
      }
      
      switch (variant) {
        case 'primary':
          return `${baseClasses} bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500`
        case 'secondary':
          return `${baseClasses} bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500`
        default:
          return `${baseClasses} bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500`
      }
    }, [variant, disabled])

    const handleClick = useStableCallback(() => {
      if (!disabled) {
        onClick()
      }
    }, [onClick, disabled])

    return React.createElement('button', {
      className: buttonClasses,
      onClick: handleClick,
      disabled: disabled
    }, children)
  },
  (prevProps, nextProps) => {
    // Comparación personalizada para optimización
    return (
      prevProps.onClick === nextProps.onClick &&
      prevProps.children === nextProps.children &&
      prevProps.variant === nextProps.variant &&
      prevProps.disabled === nextProps.disabled
    )
  }
)

MemoizedButton.displayName = 'MemoizedButton'

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
  MemoizedButton,
  useFilteredData,
  useSortedData,
  useSearchData
}
