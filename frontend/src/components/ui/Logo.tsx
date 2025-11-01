import { useState, useEffect } from 'react'
import { cn } from '@/utils'

interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizeMap = {
  sm: 'w-8 h-8',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
  xl: 'w-20 h-20',
}

// Generar IDs únicos para evitar conflictos si hay múltiples logos en la página
const uniqueId = `logo-${Math.random().toString(36).substr(2, 9)}`

// Extensiones posibles del logo personalizado
const LOGO_EXTENSIONS = ['.svg', '.png', '.jpg', '.jpeg']

export function Logo({ className, size = 'md' }: LogoProps) {
  const [customLogoUrl, setCustomLogoUrl] = useState<string | null>(null)
  const [hasChecked, setHasChecked] = useState(false)

  useEffect(() => {
    // Intentar cargar el logo personalizado desde el API
    const checkCustomLogo = async () => {
      for (const ext of LOGO_EXTENSIONS) {
        const filename = `logo-custom${ext}`
        const logoPath = `/api/v1/configuracion/logo/${filename}`
        try {
          // Usar timestamp para evitar caché
          const img = new Image()
          await new Promise((resolve, reject) => {
            img.onload = () => {
              setCustomLogoUrl(`${logoPath}?t=${Date.now()}`)
              resolve(true)
            }
            img.onerror = reject
            img.src = logoPath
          })
          break
        } catch {
          // Continuar con la siguiente extensión
          continue
        }
      }
      setHasChecked(true)
    }

    checkCustomLogo()
  }, [])

  // Si hay logo personalizado, mostrar imagen
  if (customLogoUrl) {
    return (
      <img
        src={customLogoUrl}
        alt="Logo de la empresa"
        className={cn(sizeMap[size], className, 'object-contain')}
        role="img"
      />
    )
  }

  // Si ya verificamos y no hay logo personalizado, mostrar SVG por defecto
  // También mostrar SVG mientras verificamos (hasChecked === false)
  return (
    <svg 
      className={cn(sizeMap[size], className)}
      viewBox="0 0 48 48" 
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="RAPICREDIT Logo"
    >
      <defs>
        {/* Filtro de sombra más pronunciada para la R */}
        <filter id={`shadowR-${uniqueId}`} x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="2" stdDeviation="2.5" floodColor="#000000" floodOpacity="0.25"/>
        </filter>
        
        {/* Filtro de sombra para el círculo naranja */}
        <filter id={`shadowDot-${uniqueId}`} x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor="#000000" floodOpacity="0.3"/>
        </filter>
        
        {/* Efecto glow para el punto naranja */}
        <filter id={`glowDot-${uniqueId}`}>
          <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      
      {/* Letra R estilizada - MÁS GRANDE Y MÁS GRUESA para mejor visibilidad */}
      <g filter={`url(#shadowR-${uniqueId})`}>
        {/* Tallo vertical principal - MÁS GRUESO (9px) */}
        <rect x="7" y="5" width="9" height="28" rx="1.5" className="fill-slate-900"/>
        
        {/* Borde blanco sutil en el tallo para definir mejor los bordes */}
        <rect x="7" y="5" width="9" height="28" rx="1.5" fill="none" stroke="#E0E7FF" strokeWidth="0.5" opacity="0.6"/>
        
        {/* Parte superior curva de la R - MÁS GRANDE */}
        <path d="M 16 5 L 16 14 Q 16 9 21 9 Q 26 9 27.5 11.5 L 27.5 17 Q 27.5 14.5 25 14.5 L 22 14.5 Q 20 14.5 18.5 15.5 L 16 18 Z" 
              className="fill-slate-900"/>
        
        {/* Borde sutil en la parte superior */}
        <path d="M 16 5 L 16 14 Q 16 9 21 9 Q 26 9 27.5 11.5 L 27.5 17 Q 27.5 14.5 25 14.5 L 22 14.5 Q 20 14.5 18.5 15.5 L 16 18 Z" 
              fill="none" stroke="#E0E7FF" strokeWidth="0.5" opacity="0.6"/>
        
        {/* Pierna diagonal de la R - MÁS GRUESA Y EXTENDIDA */}
        <path d="M 16 19 L 24 11 L 30 11 L 21 19 L 21 21 L 28 27 L 34 27 L 25 21 L 23 21 Z" 
              className="fill-slate-900"/>
        
        {/* Borde sutil en la pierna */}
        <path d="M 16 19 L 24 11 L 30 11 L 21 19 L 21 21 L 28 27 L 34 27 L 25 21 L 23 21 Z" 
              fill="none" stroke="#E0E7FF" strokeWidth="0.5" opacity="0.6"/>
        
        {/* Punta inferior derecha - MÁS PRONUNCIADA */}
        <path d="M 28 27 L 34 27 L 32 24 L 30 24 Z" 
              className="fill-slate-900"/>
      </g>
      
      {/* Círculo naranja vibrante - MÁS GRANDE Y MÁS VISIBLE */}
      <g filter={`url(#shadowDot-${uniqueId})`}>
        <circle cx="11" cy="41" r="6" className="fill-orange-600" filter={`url(#glowDot-${uniqueId})`}/>
        <circle cx="11" cy="41" r="4.5" className="fill-orange-500"/>
        {/* Punto brillante interno */}
        <circle cx="10" cy="40" r="1.5" className="fill-orange-400" opacity="0.8"/>
      </g>
    </svg>
  )
}

