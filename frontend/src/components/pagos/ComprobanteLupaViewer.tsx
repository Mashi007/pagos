import { useCallback, useEffect, useRef, useState } from 'react'
import { Plus, Minus, RotateCcw, RotateCw, Search, X } from 'lucide-react'
import { Button } from '../ui/button'

type ComprobanteLupaViewerProps = {
  src: string
  alt?: string
  className?: string
  imgClassName?: string
}

export function ComprobanteLupaViewer({
  src,
  alt = 'Comprobante',
  className = '',
  imgClassName = '',
}: ComprobanteLupaViewerProps) {
  const [abierto, setAbierto] = useState(false)
  const [escala, setEscala] = useState(1)
  const [rotacion, setRotacion] = useState(0)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const arrastrando = useRef(false)
  const ultimoPointer = useRef({ x: 0, y: 0 })
  const viewportRef = useRef<HTMLDivElement>(null)

  const resetZoom = useCallback(() => {
    setEscala(1)
    setOffset({ x: 0, y: 0 })
  }, [])

  const rotarImagen = useCallback(() => {
    setRotacion(prev => (prev + 90) % 360)
  }, [])

  useEffect(() => {
    setRotacion(0)
    resetZoom()
  }, [src, resetZoom])

  const cerrar = useCallback(() => {
    setAbierto(false)
    resetZoom()
  }, [resetZoom])

  useEffect(() => {
    if (!abierto) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cerrar()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [abierto, cerrar])

  const ajustarEscala = (delta: number) => {
    setEscala(prev => Math.min(6, Math.max(0.5, +(prev + delta).toFixed(2))))
  }

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY < 0 ? 0.15 : -0.15
    ajustarEscala(delta)
  }

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return
    arrastrando.current = true
    ultimoPointer.current = { x: e.clientX, y: e.clientY }
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!arrastrando.current) return
    const dx = e.clientX - ultimoPointer.current.x
    const dy = e.clientY - ultimoPointer.current.y
    ultimoPointer.current = { x: e.clientX, y: e.clientY }
    setOffset(prev => ({ x: prev.x + dx, y: prev.y + dy }))
  }

  const onPointerUp = (e: React.PointerEvent) => {
    arrastrando.current = false
    try {
      ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
  }

  const btnIconoComprobante =
    'h-10 w-10 shrink-0 rounded-full border-2 border-white bg-slate-900/92 p-0 text-white shadow-[0_2px_10px_rgba(0,0,0,0.55)] backdrop-blur-[2px] hover:bg-slate-800 hover:text-white focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900'

  return (
    <>
      <div className={`relative ${className}`}>
        <img
          src={src}
          alt={alt}
          className={imgClassName}
          style={{ transform: rotacion ? `rotate(${rotacion}deg)` : undefined }}
        />
        <div className="absolute bottom-2 right-2 flex flex-col gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={btnIconoComprobante}
            title="Rotar imagen 90°"
            aria-label="Rotar imagen 90 grados"
            onClick={rotarImagen}
          >
            <RotateCw className="h-5 w-5 stroke-[2.5]" aria-hidden />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={btnIconoComprobante}
            title="Ampliar comprobante (lupa)"
            aria-label="Ampliar comprobante con lupa"
            onClick={() => {
              resetZoom()
              setAbierto(true)
            }}
          >
            <Search className="h-5 w-5 stroke-[2.5]" aria-hidden />
          </Button>
        </div>
      </div>

      {abierto ? (
        <div
          className="fixed inset-0 z-[70] flex flex-col bg-black/85"
          role="dialog"
          aria-modal="true"
          aria-label="Vista ampliada del comprobante"
        >
          <div className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 px-3 py-2 text-white">
            <p className="text-sm font-medium">Comprobante — use la rueda o los botones para ampliar</p>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10"
                title="Alejar"
                aria-label="Alejar"
                onClick={() => ajustarEscala(-0.25)}
              >
                <Minus className="h-4 w-4" />
              </Button>
              <span className="min-w-[3.5rem] text-center text-xs tabular-nums">
                {Math.round(escala * 100)}%
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10"
                title="Acercar"
                aria-label="Acercar"
                onClick={() => ajustarEscala(0.25)}
              >
                <Plus className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10"
                title="Rotar imagen 90°"
                aria-label="Rotar imagen 90 grados"
                onClick={rotarImagen}
              >
                <RotateCw className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10"
                title="Restablecer zoom"
                aria-label="Restablecer zoom"
                onClick={resetZoom}
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-white hover:bg-white/10"
                title="Cerrar"
                aria-label="Cerrar lupa"
                onClick={cerrar}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
          </div>
          <div
            ref={viewportRef}
            className="relative min-h-0 flex-1 cursor-grab overflow-hidden active:cursor-grabbing"
            onWheel={onWheel}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            <img
              src={src}
              alt={alt}
              draggable={false}
              className="pointer-events-none absolute left-1/2 top-1/2 max-h-none max-w-none select-none"
              style={{
                transform: `translate(calc(-50% + ${offset.x}px), calc(-50% + ${offset.y}px)) rotate(${rotacion}deg) scale(${escala})`,
                transformOrigin: 'center center',
              }}
            />
          </div>
        </div>
      ) : null}
    </>
  )
}
