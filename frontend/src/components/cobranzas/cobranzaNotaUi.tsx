import { FileText } from 'lucide-react'

import {
  cobranzaNotaAdjuntoUrl,
  ESTADO_ACUERDO_LABEL,
  MENSAJE_SESION_ABIERTA,
  type CobranzaAcuerdo,
  type CobranzaNotaAdjunto,
} from '../../services/cobranzaService'
import { Badge } from '../ui/badge'
import { formatCurrency, formatDate } from '../../utils'
import { cn } from '../../utils'

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
export function notasGuardadasOrdenadas(
  acuerdos: CobranzaAcuerdo[]
): CobranzaAcuerdo[] {
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

function iconoAdjunto() {
  return <FileText className="h-3.5 w-3.5 shrink-0" />
}

export function CobranzaEvidenciasLista({
  adjuntos,
  compacto,
}: {
  adjuntos: CobranzaNotaAdjunto[]
  compacto?: boolean
}) {
  if (!adjuntos.length) return null
  return (
    <div className={cn('flex flex-wrap gap-2', compacto && 'mt-2')}>
      {adjuntos.map(adj => (
        <a
          key={adj.id}
          href={cobranzaNotaAdjuntoUrl(adj.id)}
          target="_blank"
          rel="noreferrer"
          onClick={e => e.stopPropagation()}
          className="inline-flex items-center gap-1.5 rounded-md border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-900 hover:bg-violet-100"
        >
          {iconoAdjunto()}
          <span className="max-w-[140px] truncate">
            {adj.nombre_archivo ||
              (adj.content_type.includes('pdf') ? 'PDF' : 'Imagen')}
          </span>
        </a>
      ))}
    </div>
  )
}

export function CobranzaConversacionCard({
  nota,
  onClick,
  activa,
}: {
  nota: CobranzaAcuerdo
  onClick: () => void
  activa?: boolean
}) {
  const tieneEvidencias = (nota.adjuntos?.length ?? 0) > 0
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full rounded-lg border p-4 text-left transition-colors',
        activa
          ? 'border-violet-400 bg-violet-50 ring-1 ring-violet-200'
          : 'border-slate-200 bg-white hover:border-violet-300 hover:bg-violet-50/60'
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            {formatDate(nota.fecha)}
          </p>
          {nota.cantidad != null && (
            <p className="text-sm text-amber-800">
              Acuerdo: {formatCantidadMoneda(nota.cantidad, nota.moneda)}
            </p>
          )}
        </div>
        {estadoAcuerdoBadge(nota.estado)}
      </div>
      <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-slate-700">
        {nota.mensaje}
      </p>
      {tieneEvidencias && (
        <div className="mt-3 border-t border-slate-100 pt-2">
          <p className="mb-1 text-xs font-medium text-slate-500">
            Evidencias ({nota.adjuntos!.length})
          </p>
          <CobranzaEvidenciasLista adjuntos={nota.adjuntos!} compacto />
        </div>
      )}
    </button>
  )
}

export function CobranzaNotaDetallePanel({ nota }: { nota: CobranzaAcuerdo }) {
  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-violet-50 px-4 py-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-violet-700">
            Conversacion / acuerdo
          </p>
          <p className="text-lg font-semibold text-slate-900">
            {formatDate(nota.fecha)}
          </p>
          {nota.cantidad != null && (
            <p className="text-base text-amber-800">
              Monto acordado: {formatCantidadMoneda(nota.cantidad, nota.moneda)}
            </p>
          )}
        </div>
        {estadoAcuerdoBadge(nota.estado)}
      </div>
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Mensaje de la conversacion
        </p>
        <p className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-slate-800">
          {nota.mensaje}
        </p>
      </div>
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Evidencias adjuntas
        </p>
        {nota.adjuntos && nota.adjuntos.length > 0 ? (
          <CobranzaEvidenciasLista adjuntos={nota.adjuntos} />
        ) : (
          <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-slate-500">
            Sin archivos de respaldo en esta nota.
          </p>
        )}
      </div>
    </div>
  )
}
