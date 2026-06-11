import { CheckCircle2, DollarSign, Loader2, Trash2, Upload } from 'lucide-react'

export type ConciliarCarteraFaseTabla =
  | 'borrando'
  | 'ocr'
  | 'cascada'
  | 'recargando'
  | 'listo'

type Props = {
  fase: ConciliarCarteraFaseTabla
  prestamoId: number
  pagosAntes?: number
  idsRecreados?: number[]
  ocrOk?: number
  ocrTotal?: number
}

const PASOS: Array<{
  id: ConciliarCarteraFaseTabla
  label: string
  icon: typeof Trash2
}> = [
  { id: 'borrando', label: 'Borrando pagos del préstamo', icon: Trash2 },
  { id: 'ocr', label: 'Reescaneando comprobantes (OCR)', icon: Upload },
  { id: 'cascada', label: 'Aplicando cascada a cuotas', icon: DollarSign },
  { id: 'recargando', label: 'Recargando pagos en cartera', icon: Loader2 },
]

function indiceFase(fase: ConciliarCarteraFaseTabla): number {
  if (fase === 'listo') return PASOS.length
  const i = PASOS.findIndex(p => p.id === fase)
  return i >= 0 ? i : 0
}

export function ConciliarCarteraPagosProgreso({
  fase,
  prestamoId,
  pagosAntes = 0,
  idsRecreados = [],
  ocrOk,
  ocrTotal,
}: Props) {
  const activo = indiceFase(fase)

  if (fase === 'listo') {
    return (
      <div className="space-y-3 rounded-lg border border-green-300 bg-green-50 p-4 animate-in fade-in duration-300">
        <p className="flex items-center gap-2 font-medium text-green-900">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          Pagos recreados y cargados en la tabla
        </p>
        <p className="text-sm text-green-800">
          Préstamo <strong>{prestamoId}</strong>: se borraron los pagos anteriores
          {pagosAntes > 0 ? ` (${pagosAntes})` : ''} y se cargaron{' '}
          <strong>{idsRecreados.length || ocrOk || '—'}</strong> fila(s) nueva(s)
          {idsRecreados.length > 0
            ? ` (ID ${idsRecreados.join(', ')})`
            : ''}
          .
          {ocrOk != null && ocrTotal != null ? (
            <span className="block mt-1 text-muted-foreground">
              OCR: {ocrOk}/{ocrTotal} correctos.
            </span>
          ) : null}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4 rounded-lg border border-amber-200 bg-amber-50/80 p-4">
      <p className="text-sm font-medium text-amber-950">
        Conciliando cartera — préstamo {prestamoId}
      </p>
      <ul className="space-y-2">
        {PASOS.map((paso, idx) => {
          const hecho = idx < activo
          const enCurso = idx === activo
          const Icon = paso.icon
          return (
            <li
              key={paso.id}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                enCurso
                  ? 'bg-amber-100 font-medium text-amber-950'
                  : hecho
                    ? 'text-green-800'
                    : 'text-muted-foreground'
              }`}
            >
              {enCurso ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
              ) : hecho ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
              ) : (
                <Icon className="h-4 w-4 shrink-0 opacity-40" />
              )}
              <span>
                {paso.label}
                {paso.id === 'borrando' && pagosAntes > 0 && enCurso
                  ? ` (${pagosAntes} en tabla)`
                  : ''}
              </span>
            </li>
          )
        })}
      </ul>
      {fase === 'borrando' ? (
        <p className="text-xs text-amber-900/80 animate-pulse">
          La lista de pagos se vacía mientras se procesa en el servidor…
        </p>
      ) : null}
    </div>
  )
}
