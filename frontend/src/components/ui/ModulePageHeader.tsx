import type { ComponentType, ReactNode, SVGProps } from 'react'

import { cn } from '../../utils'

export type ModulePageHeaderIcon = ComponentType<
  SVGProps<SVGSVGElement> & { className?: string }
>

export interface ModulePageHeaderProps {
  /** Icono lineal a la izquierda del titulo (color marca #1e67eb). */
  icon: ModulePageHeaderIcon

  title: string

  /** Texto breve o fragmento con varios parrafos bajo el titulo. */
  description?: ReactNode

  /** Botones u otras acciones alineadas a la derecha en desktop. */
  actions?: ReactNode

  className?: string
}

/**
 * Encabezado unificado de modulos: fondo gris claro, icono azul, titulo oscuro y descripcion gris.
 * Referencia visual: CRM - Centro de tickets.
 */
export function ModulePageHeader({
  icon: Icon,
  title,
  description,
  actions,
  className,
}: ModulePageHeaderProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-gray-100 bg-gray-50 px-4 py-4 sm:px-5',
        className
      )}
    >
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
          <Icon
            className="h-8 w-8 shrink-0 text-[#1e67eb]"
            strokeWidth={2}
            aria-hidden
          />

          <h1 className="text-2xl font-bold tracking-tight text-[#111827] sm:text-3xl">
            {title}
          </h1>
        </div>

        {actions ? (
          <div className="flex w-full flex-wrap items-start gap-2 xl:w-auto xl:shrink-0 xl:items-center xl:justify-end">
            {actions}
          </div>
        ) : null}
      </div>

      {description != null && description !== '' ? (
        <div
          className={cn(
            'mt-2 text-sm font-normal leading-relaxed text-[#374151] sm:text-base',
            '[&_p+p]:mt-2'
          )}
        >
          {typeof description === 'string' ? <p>{description}</p> : description}
        </div>
      ) : null}
    </div>
  )
}
