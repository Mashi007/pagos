import { useEffect, useRef, useState } from 'react'

/**
 * Hook que detecta cuando un elemento entra en el viewport.
 * Útil para lazy loading: cargar datos solo cuando el usuario hace scroll hasta el componente.
 */
export function useInView(options?: IntersectionObserverInit) {
  const ref = useRef<HTMLDivElement>(null)
  const [isInView, setIsInView] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true)
        }
      },
      {
        rootMargin: '100px',
        threshold: 0.01,
        ...options,
      }
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [options?.root, options?.rootMargin, options?.threshold])

  return { ref, isInView }
}
