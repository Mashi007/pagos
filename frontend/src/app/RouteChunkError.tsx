import { useEffect, useState } from 'react'

import { Button } from '../components/ui/button'

import { tryAutoReloadForChunkError } from './RouteErrorBoundary'

type Props = {
  error: Error
  reset: () => void
}

export function RouteChunkError({ error, reset }: Props) {
  const [detail, setDetail] = useState('')

  useEffect(() => {
    setDetail(error?.message || 'Error desconocido al cargar la página.')
    const msg = (error?.message || '').toLowerCase()
    const isChunk =
      msg.includes('dynamically imported module') ||
      msg.includes('error loading') ||
      msg.includes('missing js chunk') ||
      msg.includes("doesn't provide an export named") ||
      msg.includes('does not provide an export named') ||
      msg.includes('mime no permitido') ||
      msg.includes('text/html')
    if (isChunk) {
      tryAutoReloadForChunkError()
    }
  }, [error])

  const hardReload = () => {
    try {
      sessionStorage.removeItem('rapicredit_missing_chunk_reload_v1')
    } catch {
      /* ignore */
    }
    const u = new URL(window.location.href)
    u.searchParams.set('nocache', String(Date.now()))
    window.location.replace(`${u.pathname}${u.search}${u.hash}`)
  }

  return (
    <div
      className="mx-auto max-w-lg rounded-lg border border-amber-200 bg-amber-50 p-6 text-center shadow-sm"
      role="alert"
    >
      <h2 className="text-lg font-semibold text-amber-950">
        No se pudo cargar esta pantalla
      </h2>
      <p className="mt-2 text-sm text-amber-900">
        Suele ocurrir tras un despliegue si el navegador guardó archivos
        antiguos. Recargue con caché limpia o reintente.
      </p>
      {detail ? (
        <p className="mt-3 break-words font-mono text-xs text-amber-800">
          {detail}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <Button type="button" variant="outline" onClick={() => reset()}>
          Reintentar
        </Button>
        <Button type="button" onClick={hardReload}>
          Recargar (sin caché)
        </Button>
      </div>
    </div>
  )
}
