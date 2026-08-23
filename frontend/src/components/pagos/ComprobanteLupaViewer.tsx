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
 * Vista de comprobante: rotar y lupa al pie del visor.
 * Con lupa: clic y arrastre (mano) mueve la imagen; al soltar se queda fija para revisar.
 * El desplazamiento sigue el mouse en ejes de pantalla, aunque la imagen esté rotada.
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
  const [agarrando, setAgarrando] = useState(false)
  const viewportRef = useRef<HTMLDivElement>(null)
  const lupaRef = useRef(false)
  const arrastrando = useRef(false)
  const ultimoPuntero = useRef({ x: 0, y: 0 })

  useEffect(() => {
    lupaRef.current = lupaActiva
  }, [lupaActiva])

  const soltarImagen = useCallback(() => {
    arrastrando.current = false
    setAgarrando(false)
  }, [])

  const resetZoom = useCallback(() => {
    setEscala(lupaRef.current ? 1.75 : 1)
    setOffset({ x: 0, y: 0 })
    soltarImagen()
  }, [soltarImagen])

  const rotarImagen = useCallback(() => {
    setRotacion(prev => (prev + 90) % 360)
  }, [])

  const toggleLupa = useCallback(() => {
    setLupaActiva(prev => {
      const next = !prev
      lupaRef.current = next
      setEscala(next ? 1.75 : 1)
      setOffset({ x: 0, y: 0 })
      arrastrando.current = false
      setAgarrando(false)
      return next
    })
  }, [])

  useEffect(() => {
    setRotacion(0)
    setLupaActiva(false)
    lupaRef.current = false
    setEscala(1)
    setOffset({ x: 0, y: 0 })
    arrastrando.current = false
    setAgarrando(false)
  }, [src])

  useEffect(() => {
    if (!lupaActiva) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setLupaActiva(false)
        lupaRef.current = false
        setEscala(1)
        setOffset({ x: 0, y: 0 })
        arrastrando.current = false
        setAgarrando(false)
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
    if ((e.target as HTMLElement).closest('[data-lupa-controles]')) return
    e.preventDefault()
    arrastrando.current = true
    setAgarrando(true)
    ultimoPuntero.current = { x: e.clientX, y: e.clientY }
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!lupaActiva || !arrastrando.current) return
    const dx = e.clientX - ultimoPuntero.current.x
    const dy = e.clientY - ultimoPuntero.current.y
    ultimoPuntero.current = { x: e.clientX, y: e.clientY }
    if (dx === 0 && dy === 0) return
    setOffset(prev => ({ x: prev.x + dx, y: prev.y + dy }))
  }

  const onPointerUp = (e: React.PointerEvent) => {
    soltarImagen()
    try {
      ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
  }

  const transformCapa = lupaActiva
    ? `translate(${offset.x}px, ${offset.y}px) scale(${escala})`
    : undefined

  return (
    <div className={`relative ${className}`}>
      <div
        ref={viewportRef}
        className={`relative overflow-hidden rounded border border-slate-200 bg-slate-50 ${
          lupaActiva ? (agarrando ? 'cursor-grabbing touch-none' : 'cursor-grab touch-none') : ''
        }`}
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          className="flex justify-center"
          style={{
            transform: transformCapa,
            transformOrigin: 'center center',
          }}
        >
          <img
            src={src}
            alt={alt}
            draggable={false}
            className={`${imgClassName} select-none ${lupaActiva ? 'max-h-none' : ''}`}
            style={{
              transform: rotacion ? `rotate(${rotacion}deg)` : undefined,
              transformOrigin: 'center center',
            }}
          />
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex justify-center p-2">
          <div className="pointer-events-auto flex flex-col items-center gap-1.5" data-lupa-controles>
            <div className="flex flex-wrap items-center justify-center gap-2 rounded-full bg-slate-950/70 p-1.5 shadow-xl ring-1 ring-white/50 backdrop-blur-[2px]">
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
                    ? 'Quitar lupa (Esc). Clic y arrastra: la mano mueve la imagen; suelta para revisar'
                    : 'Lupa: ampliar. Clic y arrastra para mover'
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
              {lupaActiva ? (
                <>
                  <button
                    type="button"
                    title="Alejar"
                    aria-label="Alejar"
                    className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-white bg-slate-950 text-lg font-semibold text-white shadow-lg hover:bg-slate-800"
                    onClick={e => {
                      e.preventDefault()
                      e.stopPropagation()
                      ajustarEscala(-0.25)
                    }}
                  >
                    −
                  </button>
                  <button
                    type="button"
                    title="Ajustar zoom"
                    aria-label="Ajustar zoom"
                    className="inline-flex h-10 min-w-[2.5rem] shrink-0 items-center justify-center rounded-full border-2 border-white bg-slate-950 px-2 text-[11px] font-semibold text-white shadow-lg hover:bg-slate-800"
                    onClick={e => {
                      e.preventDefault()
                      e.stopPropagation()
                      resetZoom()
                    }}
                  >
                    1:1
                  </button>
                  <button
                    type="button"
                    title="Acercar"
                    aria-label="Acercar"
                    className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-white bg-slate-950 text-lg font-semibold text-white shadow-lg hover:bg-slate-800"
                    onClick={e => {
                      e.preventDefault()
                      e.stopPropagation()
                      ajustarEscala(0.25)
                    }}
                  >
                    +
                  </button>
                </>
              ) : null}
            </div>
            <div className="rounded bg-slate-950/85 px-2 py-1 text-[11px] font-medium text-white shadow">
              {lupaActiva
                ? `Lupa ${Math.round(escala * 100)}% · clic y arrastra · suelta para revisar · Esc`
                : 'Rotar · Lupa'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
