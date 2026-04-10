import { useEffect, useState, type ReactNode } from 'react'

type Props = {
  sectionId: string
  active: boolean
  children: ReactNode
}

/**
 * Monta la seccion la primera vez que se visita y la deja montada (hidden cuando no esta activa).
 * Cada submenú de Configuración conserva estado y datos cargados al volver.
 */
export function KeepAliveConfigSection({ sectionId, active, children }: Props) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (active) setMounted(true)
  }, [active])

  if (!mounted) return null

  return (
    <div
      id={`config-section-${sectionId}`}
      role="tabpanel"
      hidden={!active}
      className={active ? '' : 'hidden'}
      aria-hidden={!active}
    >
      {children}
    </div>
  )
}
