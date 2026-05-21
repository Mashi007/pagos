import {
  cobranzaNotaAdjuntoUrl,
  ESTADO_ACUERDO_LABEL,
  MENSAJE_SESION_ABIERTA,
  type CobranzaAcuerdo,
} from '../../services/cobranzaService'
import { Badge } from '../ui/badge'
import { formatCurrency, formatDate } from '../../utils'

export function formatCantidadMoneda(
  cantidad?: number | null,
  moneda?: string
): string {
  if (cantidad == null || Number.isNaN(cantidad)) return '-'
  const m = (moneda || 'USD').toUpperCase()
  if (m === 'BS') {
    return `Bs. ${cantidad.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
  return formatCurrency(cantidad)
}

export function esNotaBorrador(a: CobranzaAcuerdo): boolean {
  return a.mensaje.trim() === MENSAJE_SESION_ABIERTA
}

/** Notas guardadas: mas reciente primero. */
export function notasGuardadasOrdenadas(acuerdos: CobranzaAcuerdo[]): CobranzaAcuerdo[] {
  return acuerdos
    .filter(a => !esNotaBorrador(a))
    .sort((a, b) => {
      const fa = a.fecha || ''
      const fb = b.fecha || ''
      if (fa !== fb) return fb.localeCompare(fa)
      return (b.id ?? 0) - (a.id ?? 0)
    })
}

export function estadoAcuerdoBadge(estado: string) {
  const cls =
    estado === 'CUMPLIDO'
      ? 'bg-green-100 text-green-800'
      : estado === 'INCUMPLIDO'
        ? 'bg-red-100 text-red-800'
        : 'bg-amber-100 text-amber-800'
  return (
    <Badge className={cls}>
      {ESTADO_ACUERDO_LABEL[estado as keyof typeof ESTADO_ACUERDO_LABEL] ||
        estado}
    </Badge>
  )
}

export function resumenNotaLinea(a: CobranzaAcuerdo): string {
  const monto =
    a.cantidad != null ? ` · ${formatCantidadMoneda(a.cantidad, a.moneda)}` : ''
  const preview = a.mensaje.trim().slice(0, 80)
  const suf = a.mensaje.length > 80 ? '...' : ''
  return `${formatDate(a.fecha)}${monto} — ${preview}${suf}`
}

export function CobranzaNotaDetallePanel({ nota }: { nota: CobranzaAcuerdo }) {
  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <p className="text-lg font-semibold text-slate-900">
            {formatDate(nota.fecha)}
          </p>
          {nota.cantidad != null && (
            <p className="text-slate-600">
              {formatCantidadMoneda(nota.cantidad, nota.moneda)}
            </p>
          )}
        </div>
        {estadoAcuerdoBadge(nota.estado)}
      </div>
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Mensaje
        </p>
        <p className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 text-slate-800">
          {nota.mensaje}
        </p>
      </div>
      {nota.adjuntos && nota.adjuntos.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Respaldos
          </p>
          <div className="flex flex-wrap gap-2">
            {nota.adjuntos.map(adj => (
              <a
                key={adj.id}
                href={cobranzaNotaAdjuntoUrl(adj.id)}
                target="_blank"
                rel="noreferrer"
                className="rounded border border-slate-200 bg-white px-3 py-2 text-sm text-blue-700 shadow-sm hover:bg-blue-50"
              >
                {adj.nombre_archivo ||
                  (adj.content_type.includes('pdf') ? 'PDF' : 'Archivo')}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
