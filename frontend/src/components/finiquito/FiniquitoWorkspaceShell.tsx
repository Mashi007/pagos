import type { ReactNode } from 'react'

import { FileText } from 'lucide-react'

import { ModulePageHeader } from '../ui/ModulePageHeader'

import { cn } from '../../utils'

export interface FiniquitoWorkspaceShellProps {
  /** Mismo titulo que la pantalla de gestion interna. */
  title?: string

  description?: ReactNode

  actions?: ReactNode

  /** Contenido fijo bajo la cabecera (p. ej. KPIs de gestion). */
  toolbar?: ReactNode

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
  toolbar,
  children,
  className,
}: FiniquitoWorkspaceShellProps) {
  return (
    <div
      className={cn(
        'min-h-[100dvh] min-h-screen bg-slate-100/80 pb-10',
        className
      )}
    >
      <div className="mx-auto max-w-7xl px-4 md:px-6">
        <div
          className={cn(
            'sticky top-0 z-40 -mx-4 space-y-4 border-b border-slate-200/80',
            'bg-slate-100/95 px-4 pb-4 pt-4 shadow-sm backdrop-blur-sm',
            'supports-[backdrop-filter]:bg-slate-100/90 md:-mx-6 md:px-6 md:pt-6'
          )}
        >
          <ModulePageHeader
            icon={FileText}
            title={title}
            description={description}
            actions={actions}
          />
          {toolbar}
        </div>
        <div className="space-y-5 pt-5 md:space-y-6">{children}</div>
      </div>
    </div>
  )
}
