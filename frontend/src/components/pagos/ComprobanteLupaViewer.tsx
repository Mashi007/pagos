import { useCallback, useEffect, useRef, useState } from 'react'

type ComprobanteLupaViewerProps = {
  src: string
  alt?: string
  className?: string
  imgClassName?: string
}

/** Controles solo-icono, alto contraste, sin depender de estilos del Button shadcn. */
function BtnIcono({
  title,
  ariaLabel,
  onClick,
  active,
  children,
}: {
  title: string
  ariaLabel: string
  onClick: () => void
  active?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={ariaLabel}
      aria-pressed={active}
      onClick={e => {
        e.preventDefault()
        e.stopPropagation()
        onClick()
      }}
      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 shadow-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400 ${
        active
          ? 'border-sky-300 bg-sky-600 text-white hover:bg-sky-500'
          : 'border-white bg-slate-950 text-white hover:bg-slate-800'
      }`}
    >
      {children}
    </button>
  )
}

function IconRotate({ className = '' }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
    </svg>
  )
}

function IconSearch({ className = '' }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  )
}

/**
 * Vista de comprobante con rotar y lupa **dentro del mismo panel** del modal Editar/Agregar pago
 * (sin overlay a pantalla completa ni pestaña nueva), para comparar imagen vs campos OCR.
 */
export function ComprobanteLupaViewer({
  src,
  alt = 'Comprobante',
  className = '',
  imgClassName = '',
}: ComprobanteLupaViewerProps) {
  const [lupaActiva, setLupaActiva] = useState(false)
  const [escala, setEscala] = useState(1)
  const [rotacion, setRotacion] = useState(0)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const arrastrando = useRef(false)
  const ultimoPointer = useRef({ x: 0, y: 0 })
  const viewportRef = useRef<HTMLDivElement>(null)

  const resetZoom = useCallback(() => {
    setEscala(lupaActiva ? 1.75 : 1)
    setOffset({ x: 0, y: 0 })
  }, [lupaActiva])

  const rotarImagen = useCallback(() => {
    setRotacion(prev => (prev + 90) % 360)
  }, [])

  const toggleLupa = useCallback(() => {
    setLupaActiva(prev => {
      const next = !prev
      setEscala(next ? 1.75 : 1)
      setOffset({ x: 0, y: 0 })
      return next
    })
  }, [])

  useEffect(() => {
    setRotacion(0)
    setLupaActiva(false)
    setEscala(1)
    setOffset({ x: 0, y: 0 })
  }, [src])

  useEffect(() => {
    if (!lupaActiva) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setLupaActiva(false)
        setEscala(1)
        setOffset({ x: 0, y: 0 })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lupaActiva])

  const ajustarEscala = (delta: number) => {
    setEscala(prev => Math.min(6, Math.max(1, +(prev + delta).toFixed(2))))
  }

  const onWheel = (e: React.WheelEvent) => {
    if (!lupaActiva) return
    e.preventDefault()
    e.stopPropagation()
    ajustarEscala(e.deltaY < 0 ? 0.2 : -0.2)
  }

  const onPointerDown = (e: React.PointerEvent) => {
    if (!lupaActiva || e.button !== 0) return
    arrastrando.current = true
    ultimoPointer.current = { x: e.clientX, y: e.clientY }
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!arrastrando.current || !lupaActiva) return
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

  const transformImg = [
    rotacion ? `rotate(${rotacion}deg)` : '',
    lupaActiva
      ? `translate(${offset.x}px, ${offset.y}px) scale(${escala})`
      : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={`relative ${className}`}>
      <div
        ref={viewportRef}
        className={`relative overflow-hidden rounded border border-slate-200 bg-slate-50 ${
          lupaActiva ? 'cursor-grab active:cursor-grabbing' : ''
        }`}
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
          className={`${imgClassName} select-none ${lupaActiva ? 'max-h-none' : ''}`}
          style={{
            transform: transformImg || undefined,
            transformOrigin: 'center center',
            transition: arrastrando.current ? undefined : 'transform 0.12s ease-out',
          }}
        />
        <div className="pointer-events-none absolute inset-0 z-10 flex flex-col items-end justify-end gap-2 p-2">
          <div className="pointer-events-auto flex flex-col gap-2">
            <BtnIcono
              title="Rotar imagen 90°"
              ariaLabel="Rotar imagen 90 grados"
              onClick={rotarImagen}
            >
              <IconRotate className="h-5 w-5" />
            </BtnIcono>
            <BtnIcono
              title={
                lupaActiva
                  ? 'Quitar lupa (Esc). Rueda = zoom, arrastre = mover'
                  : 'Lupa: ampliar aquí para comparar con el formulario'
              }
              ariaLabel={
                lupaActiva
                  ? 'Desactivar lupa'
                  : 'Activar lupa en el mismo panel'
              }
              active={lupaActiva}
              onClick={toggleLupa}
            >
              <IconSearch className="h-5 w-5" />
            </BtnIcono>
          </div>
        </div>
        {lupaActiva ? (
          <div className="pointer-events-none absolute left-2 top-2 z-10 rounded bg-slate-950/85 px-2 py-1 text-[11px] font-medium text-white shadow">
            Lupa {Math.round(escala * 100)}% · rueda / arrastre · Esc salir
          </div>
        ) : null}
      </div>
      {lupaActiva ? (
        <div className="mt-1.5 flex flex-wrap items-center justify-center gap-1">
          <button
            type="button"
            className="rounded border border-slate-300 bg-white px-2 py-0.5 text-xs font-medium text-slate-800 hover:bg-slate-100"
            onClick={() => ajustarEscala(-0.25)}
          >
            −
          </button>
          <button
            type="button"
            className="rounded border border-slate-300 bg-white px-2 py-0.5 text-xs font-medium text-slate-800 hover:bg-slate-100"
            onClick={resetZoom}
          >
            Ajustar
          </button>
          <button
            type="button"
            className="rounded border border-slate-300 bg-white px-2 py-0.5 text-xs font-medium text-slate-800 hover:bg-slate-100"
            onClick={() => ajustarEscala(0.25)}
          >
            +
          </button>
        </div>
      ) : null}
    </div>
  )
}
