import { Button } from './button'

import { cn } from '../../utils'

/** Hasta `max` números de página visibles (ventana deslizante), alineado al mock 1…5. */
export function getVisiblePageNumbers(
  current: number,
  totalPages: number,
  max = 5
): number[] {
  if (totalPages < 1) return []
  if (totalPages <= max) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }
  if (current <= 3) {
    return Array.from({ length: max }, (_, i) => i + 1)
  }
  if (current >= totalPages - 2) {
    return Array.from({ length: max }, (_, i) => totalPages - max + i + 1)
  }
  return Array.from({ length: max }, (_, i) => current - 2 + i)
}

export type ListPaginationBarProps = {
  /** 1-based */
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  className?: string
  /** Texto opcional bajo "Página X de Y" (p. ej. totales / tamaño de página). */
  subtitle?: string
}

export function ListPaginationBar({
  page,
  totalPages,
  onPageChange,
  className,
  subtitle,
}: ListPaginationBarProps) {
  if (totalPages < 1) return null

  const safePage = Math.min(Math.max(1, page), totalPages)
  const pages = getVisiblePageNumbers(safePage, totalPages, 5)

  return (
    <div className={cn('flex flex-col items-center gap-2', className)}>
      <div
        className="flex flex-wrap items-center justify-center gap-1 sm:gap-1.5"
        role="navigation"
        aria-label="Paginación"
      >
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={safePage <= 1}
          onClick={() => onPageChange(safePage - 1)}
          className="rounded-md border-gray-300 bg-white text-gray-800 shadow-none hover:bg-gray-50"
        >
          ← Anterior
        </Button>
        {pages.map(p => {
          const isActive = p === safePage
          return (
            <Button
              key={p}
              type="button"
              variant={isActive ? 'default' : 'outline'}
              size="sm"
              onClick={() => onPageChange(p)}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'min-w-[2.25rem] rounded-md px-2.5 shadow-none sm:min-w-[2.5rem]',
                isActive
                  ? ''
                  : 'border-gray-300 bg-white text-gray-800 hover:bg-gray-50'
              )}
            >
              {p}
            </Button>
          )
        })}
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={safePage >= totalPages}
          onClick={() => onPageChange(safePage + 1)}
          className="rounded-md border-gray-300 bg-white text-gray-800 shadow-none hover:bg-gray-50"
        >
          Siguiente →
        </Button>
      </div>
      <p className="text-center text-sm text-gray-500">
        Página {safePage} de {totalPages}
      </p>
      {subtitle ? (
        <p className="text-center text-xs text-gray-400">{subtitle}</p>
      ) : null}
    </div>
  )
}
