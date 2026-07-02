/**
 * Thumbnail del comprobante de un pago.
 *
 * Cubre tres casos:
 *  - URL interna /api/v1/pagos/comprobante-imagen/{uuid32} -> requiere Authorization
 *    (Bearer JWT staff). El navegador no envía cabeceras en <img src>, por eso
 *    descargamos el blob con apiClient.getBlob y mostramos un object URL.
 *  - URL externa (Drive heredado, etc.) -> se usa directo como src.
 *  - PDF -> mostramos un placeholder "PDF" en lugar del binario.
 */
import { useEffect, useState } from 'react'

import { FileText, Loader2 } from 'lucide-react'

import { apiClient } from '../../services/api'
import { pathApiComprobanteImagenDesdeHref } from '../../utils/comprobanteImagenAuth'

interface ComprobanteThumbProps {
  url: string | null | undefined
  alt?: string
  /** Clases extra para el <img> / placeholder (tamano, borde, etc.). */
  className?: string
  /** Mostrar caja vacia "Sin imagen" si url es null/vacio. */
  placeholderText?: string
  /** Si es true, hace click abre el comprobante en pestaña nueva (con sesion). */
  abrirEnNuevaPestana?: boolean
}

interface SnifResult {
  mime: string
  isPdf: boolean
}

function sniffMime(head: Uint8Array): SnifResult {
  if (head.length >= 4) {
    if (
      head[0] === 0x25 &&
      head[1] === 0x50 &&
      head[2] === 0x44 &&
      head[3] === 0x46
    ) {
      return { mime: 'application/pdf', isPdf: true }
    }
    if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) {
      return { mime: 'image/jpeg', isPdf: false }
    }
    if (
      head[0] === 0x89 &&
      head[1] === 0x50 &&
      head[2] === 0x4e &&
      head[3] === 0x47
    ) {
      return { mime: 'image/png', isPdf: false }
    }
    if (
      head[0] === 0x47 &&
      head[1] === 0x49 &&
      head[2] === 0x46 &&
      head[3] === 0x38
    ) {
      return { mime: 'image/gif', isPdf: false }
    }
  }
  if (
    head.length >= 12 &&
    head[0] === 0x52 &&
    head[1] === 0x49 &&
    head[2] === 0x46 &&
    head[3] === 0x46 &&
    head[8] === 0x57 &&
    head[9] === 0x45 &&
    head[10] === 0x42 &&
    head[11] === 0x50
  ) {
    return { mime: 'image/webp', isPdf: false }
  }
  return { mime: 'application/octet-stream', isPdf: false }
}

export function ComprobanteThumb({
  url,
  alt = 'Comprobante',
  className,
  placeholderText = 'Sin imagen',
  abrirEnNuevaPestana = true,
}: ComprobanteThumbProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [isPdf, setIsPdf] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  const trimmed = (url || '').trim()
  const pathAuth = trimmed ? pathApiComprobanteImagenDesdeHref(trimmed) : null

  useEffect(() => {
    if (!pathAuth) {
      setBlobUrl(null)
      setIsPdf(false)
      setError(false)
      setLoading(false)
      return
    }
    let cancelado = false
    const abortController = new AbortController()
    setLoading(true)
    setError(false)
    setIsPdf(false)
    ;(async () => {
      try {
        const blob = await apiClient.getBlob(pathAuth, {
          signal: abortController.signal,
        })
        if (cancelado) return
        const head = new Uint8Array(await blob.slice(0, 16).arrayBuffer())
        const sniff = sniffMime(head)
        if (cancelado) return
        if (sniff.isPdf) {
          setIsPdf(true)
          setBlobUrl(null)
          return
        }
        const buf = await blob.arrayBuffer()
        if (cancelado) return
        const finalMime = sniff.mime || blob.type || 'image/jpeg'
        const fixedBlob = new Blob([buf], { type: finalMime })
        const objUrl = URL.createObjectURL(fixedBlob)
        setBlobUrl(prev => {
          if (prev) URL.revokeObjectURL(prev)
          return objUrl
        })
      } catch {
        if (!cancelado) setError(true)
      } finally {
        if (!cancelado) setLoading(false)
      }
    })()
    return () => {
      cancelado = true
      abortController.abort()
      setBlobUrl(prev => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
    }
  }, [pathAuth])

  if (!trimmed) {
    return (
      <span
        className={
          'inline-flex items-center rounded border border-dashed border-muted-foreground/40 px-2 py-1 text-[11px] text-muted-foreground ' +
          (className || '')
        }
      >
        {placeholderText}
      </span>
    )
  }

  // URL externa (Drive, etc.): usar src directo.
  if (!pathAuth) {
    const img = (
      <img
        src={trimmed}
        alt={alt}
        className={'h-16 w-16 rounded border object-cover ' + (className || '')}
        loading="lazy"
        onError={e => {
          ;(e.currentTarget as HTMLImageElement).style.display = 'none'
        }}
      />
    )
    if (abrirEnNuevaPestana) {
      return (
        <a
          href={trimmed}
          target="_blank"
          rel="noreferrer"
          title="Abrir comprobante"
          className="inline-block"
        >
          {img}
        </a>
      )
    }
    return img
  }

  if (loading) {
    return (
      <span
        className={
          'inline-flex h-16 w-16 items-center justify-center rounded border text-muted-foreground ' +
          (className || '')
        }
        title="Cargando comprobante..."
      >
        <Loader2 className="h-4 w-4 animate-spin" />
      </span>
    )
  }

  if (error) {
    return (
      <span
        className={
          'inline-flex h-16 w-16 items-center justify-center rounded border border-rose-300 bg-rose-50 text-[10px] text-rose-900 ' +
          (className || '')
        }
        title="No se pudo cargar el comprobante (sesion expirada o sin permisos)"
      >
        Error
      </span>
    )
  }

  if (isPdf) {
    const onClick = abrirEnNuevaPestana
      ? () => {
          void (async () => {
            try {
              const blob = await apiClient.getBlob(pathAuth)
              const buf = await blob.arrayBuffer()
              const pdfBlob = new Blob([buf], { type: 'application/pdf' })
              const u = URL.createObjectURL(pdfBlob)
              const w = window.open(u, '_blank', 'noopener,noreferrer')
              if (!w) URL.revokeObjectURL(u)
              else window.setTimeout(() => URL.revokeObjectURL(u), 120_000)
            } catch {
              /* noop */
            }
          })()
        }
      : undefined
    return (
      <button
        type="button"
        onClick={onClick}
        className={
          'inline-flex h-16 w-16 flex-col items-center justify-center rounded border bg-rose-50 text-[10px] font-medium text-rose-900 ' +
          (className || '')
        }
        title="Abrir PDF"
      >
        <FileText className="h-5 w-5" />
        PDF
      </button>
    )
  }

  if (!blobUrl) {
    return (
      <span
        className={
          'inline-flex h-16 w-16 items-center justify-center rounded border text-[10px] text-muted-foreground ' +
          (className || '')
        }
      >
        N/D
      </span>
    )
  }

  const img = (
    <img
      src={blobUrl}
      alt={alt}
      className={'h-16 w-16 rounded border object-cover ' + (className || '')}
      loading="lazy"
    />
  )
  if (abrirEnNuevaPestana) {
    const onClick = () => {
      const w = window.open(blobUrl, '_blank', 'noopener,noreferrer')
      if (!w) return
    }
    return (
      <button
        type="button"
        onClick={onClick}
        className="inline-block"
        title="Abrir comprobante"
      >
        {img}
      </button>
    )
  }
  return img
}

export default ComprobanteThumb
