import { Eye, Loader2, RotateCcw } from 'lucide-react'
import { Button } from '../../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card'
import { abrirStaffComprobanteDesdeHref } from '../../../utils/comprobanteImagenAuth'
import type { StaffComprobanteListPreview } from './staffComprobanteTypes'

type Props = {
  preview: StaffComprobanteListPreview
  onClose: () => void
  onRotate: (deltaDeg: number) => void
}

export function StaffComprobanteDock({ preview, onClose, onRotate }: Props) {
  return (
    <aside className="flex min-h-[min(36vh,320px)] min-w-0 flex-col bg-slate-100 lg:h-full lg:max-h-full lg:min-h-0 lg:overflow-y-auto lg:overscroll-y-contain">
      <Card className="flex h-full min-h-0 flex-col rounded-none border-0 shadow-none">
        <CardHeader className="shrink-0 border-b border-slate-200/80 px-3 pb-2 pt-3">
          <CardTitle className="text-base">Comprobante</CardTitle>
          <p className="text-xs text-muted-foreground">{preview.label}</p>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col space-y-2 overflow-hidden p-2 sm:p-3 lg:pl-0 lg:pr-2">
          {preview.loading ? (
            <div className="flex flex-1 items-center justify-center py-12">
              <Loader2 className="h-10 w-10 animate-spin text-slate-500" />
            </div>
          ) : preview.blobUrl && preview.contentType?.startsWith('image/') ? (
            <>
              <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto rounded-md border border-slate-200/80 bg-white lg:rounded-l-none lg:border-l-0">
                <div
                  className="inline-flex max-h-full max-w-full origin-center transition-transform duration-200"
                  style={{
                    transform: `rotate(${preview.rotDeg}deg)`,
                  }}
                >
                  <img
                    src={preview.blobUrl}
                    alt="Comprobante"
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  title="Rotar 90° a la izquierda"
                  onClick={() => onRotate(-90)}
                >
                  <RotateCcw className="mr-1 h-4 w-4" />
                  Rotar
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  title="Rotar 90° a la derecha"
                  onClick={() => onRotate(90)}
                >
                  <span className="inline-flex" aria-hidden>
                    <RotateCcw className="mr-1 h-4 w-4 scale-x-[-1]" />
                  </span>
                  Rotar der.
                </Button>
              </div>
            </>
          ) : preview.blobUrl ? (
            <div className="min-h-0 flex-1 overflow-auto rounded-md border border-slate-200/80 bg-white lg:rounded-l-none lg:border-l-0">
              <iframe
                title={preview.label || 'Comprobante PDF'}
                src={preview.blobUrl}
                className="h-[min(36vh,320px)] min-h-[200px] w-full border-0 lg:h-full lg:min-h-[min(50vh,520px)]"
              />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No se pudo cargar el comprobante.
            </p>
          )}
          {preview.href ? (
            <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="w-full sm:flex-1"
                onClick={() =>
                  void abrirStaffComprobanteDesdeHref(preview.href)
                }
              >
                <Eye className="mr-1 h-4 w-4" />
                Abrir en nueva pestaña
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="w-full sm:flex-1"
                onClick={onClose}
              >
                Cerrar panel
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </aside>
  )
}
