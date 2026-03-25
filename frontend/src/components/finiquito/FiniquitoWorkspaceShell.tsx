import type { ReactNode } from 'react'

import { FileText } from 'lucide-react'

import { ModulePageHeader } from '../ui/ModulePageHeader'

import { cn } from '../../utils'

export interface FiniquitoWorkspaceShellProps {
  /** Mismo titulo que la pantalla de gestion interna. */
  title?: string

  description?: ReactNode

  actions?: ReactNode

  children: ReactNode

  className?: string
}

/**
 * Marco unificado Finiquito: mismo fondo, ancho y cabecera que /finiquitos/gestion
 * (entorno local, Render y demas despliegues).
 */
export function FiniquitoWorkspaceShell({
  title = 'Finiquito · Gestión',
  description,
  actions,
  children,
  className,
}: FiniquitoWorkspaceShellProps) {
  return (
    <div
      className={cn(
        'min-h-[100dvh] min-h-screen bg-slate-100/80 pb-10 pt-4 md:pt-6',
        className
      )}
    >
      <div className="mx-auto max-w-7xl space-y-5 px-4 md:space-y-6 md:px-6">
        <ModulePageHeader
          icon={FileText}
          title={title}
          description={description}
          actions={actions}
        />
        {children}
      </div>
    </div>
  )
}
