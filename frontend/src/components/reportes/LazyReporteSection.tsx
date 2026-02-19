import { useInView } from '../../hooks/useInView'

interface LazyReporteSectionProps {
  children: React.ReactNode
  /** Nombre del reporte para el placeholder de carga */
  label?: string
}

/**
 * Wrapper que carga el contenido solo cuando el usuario hace scroll hasta la sección.
 * Reduce la carga inicial: solo KPIs + Informe Pago Vencido se cargan al entrar.
 */
export function LazyReporteSection({ children, label = 'Reporte' }: LazyReporteSectionProps) {
  const { ref, isInView } = useInView()

  return (
    <div ref={ref} className="min-h-[120px]">
      {isInView ? (
        children
      ) : (
        <div
          className="flex items-center justify-center rounded-lg border border-dashed border-gray-200 bg-gray-50/50 py-12 text-gray-500"
          aria-label={`Sección ${label} - se cargará al hacer scroll`}
        >
          <span className="text-sm">{label}</span>
        </div>
      )}
    </div>
  )
}
