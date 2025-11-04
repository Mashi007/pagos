import { useState, useEffect } from 'react'
import { cn } from '@/utils'
import { getErrorMessage, isAxiosError } from '@/types/errors'

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

// Extensiones posibles del logo personalizado (ordenadas por prioridad)
const LOGO_EXTENSIONS = ['.svg', '.png', '.jpg', '.jpeg']

// Cache compartido en memoria para evitar múltiples peticiones
// NOTA: Este caché se resetea al recargar la página, pero eso está bien
// porque consultamos la BD al iniciar
interface LogoCache {
  logoUrl: string | null
  isChecking: boolean
  hasChecked: boolean
  version: number // Contador de versión para forzar actualizaciones
  logoNotFound: boolean // ✅ Flag para recordar que el logo no existe (evitar requests repetidos)
}

const logoCache: LogoCache = {
  logoUrl: null,
  isChecking: false,
  hasChecked: false,
  version: 0,
  logoNotFound: false, // ✅ Inicializar flag
}

// Listeners para notificar a todos los componentes cuando cambia el logo
const logoListeners = new Set<(url: string | null, version: number) => void>()

function notifyLogoListeners(url: string | null, version: number) {
  logoListeners.forEach(listener => {
    try {
      listener(url, version)
    } catch (error) {
      console.error('Error notificando listener de logo:', error)
    }
  })
}

export function Logo({ className, size = 'md' }: LogoProps) {
  const [customLogoUrl, setCustomLogoUrl] = useState<string | null>(logoCache.logoUrl)
  const [hasChecked, setHasChecked] = useState(logoCache.hasChecked)
  const [logoVersion, setLogoVersion] = useState(logoCache.version)

  useEffect(() => {
    // Si ya tenemos el logo cacheado y existe, usarlo directamente
    if (logoCache.logoUrl && !logoCache.logoNotFound) {
      setCustomLogoUrl(logoCache.logoUrl)
      setHasChecked(true)
      return
    }

    // Si ya verificamos y no hay logo (o logo no encontrado), no hacer nada más
    if (logoCache.hasChecked || logoCache.logoNotFound) {
      setHasChecked(true)
      return
    }

    // Si otra instancia ya está verificando, esperar
    if (logoCache.isChecking) {
      // Esperar hasta que termine la verificación
      const checkInterval = setInterval(() => {
        if (!logoCache.isChecking) {
          setCustomLogoUrl(logoCache.logoUrl)
          setHasChecked(logoCache.hasChecked)
          clearInterval(checkInterval)
        }
      }, 100)

      return () => clearInterval(checkInterval)
    }

    // Marcar que estamos verificando
    logoCache.isChecking = true

    // Intentar cargar el logo personalizado desde el API
    const checkCustomLogo = async () => {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // Timeout de 5 segundos

      try {
        // PRIMERO: Intentar obtener el nombre del logo desde la configuración general
        try {
          const configResponse = await fetch('/api/v1/configuracion/general', {
            signal: controller.signal,
          })
          
          if (configResponse.ok) {
            const config = await configResponse.json()
            if (config.logo_filename) {
              // ✅ Si tenemos el nombre del logo, verificar primero si existe antes de intentar cargar
              const logoPath = `/api/v1/configuracion/logo/${config.logo_filename}`
              
              // Verificar si el logo existe con HEAD request (más ligero que GET)
              try {
                const headResponse = await fetch(logoPath, {
                  method: 'HEAD',
                  signal: controller.signal,
                })
                
                if (headResponse.ok) {
                  // Logo existe, usar URL con timestamp
                  const logoUrl = `${logoPath}?t=${Date.now()}`
                  logoCache.logoUrl = logoUrl
                  logoCache.logoNotFound = false // ✅ Resetear flag
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  setCustomLogoUrl(logoUrl)
                  setHasChecked(true)
                  setLogoVersion(logoCache.version)
                  clearTimeout(timeoutId)
                  logoCache.isChecking = false
                  notifyLogoListeners(logoUrl, logoCache.version)
                  console.log('✅ Logo cargado desde configuración:', config.logo_filename)
                  return
                } else {
                  // Logo no existe (404), marcar como no encontrado
                  console.warn('⚠️ Logo no encontrado en servidor:', config.logo_filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.hasChecked = true
                  logoCache.isChecking = false
                  setHasChecked(true)
                  clearTimeout(timeoutId)
                  return
                }
              } catch (headError: unknown) {
                // Si HEAD falla, asumir que no existe (evitar requests repetidos)
                const error = headError as { name?: string }
                if (error?.name !== 'AbortError') {
                  console.warn('⚠️ Error verificando logo, asumiendo que no existe:', getErrorMessage(headError))
                }
                logoCache.logoNotFound = true
                logoCache.logoUrl = null
                logoCache.hasChecked = true
                logoCache.isChecking = false
                setHasChecked(true)
                clearTimeout(timeoutId)
                return
              }
            } else {
              // Si no hay logo_filename en la configuración, no hay logo personalizado
              // No hacer solicitudes HEAD innecesarias
              logoCache.hasChecked = true
              logoCache.isChecking = false
              setHasChecked(true)
              clearTimeout(timeoutId)
              return
            }
          }
        } catch (configError: unknown) {
          // Si falla obtener la configuración, marcar como verificado y no hacer más intentos
          const error = configError as { name?: string }
          if (error?.name !== 'AbortError') {
            console.warn('⚠️ No se pudo obtener logo_filename desde configuración:', getErrorMessage(configError))
          }
          logoCache.hasChecked = true
          logoCache.isChecking = false
          setHasChecked(true)
          clearTimeout(timeoutId)
          return
        }
      } catch (error: unknown) {
        const err = error as { name?: string }
        if (err?.name !== 'AbortError') {
          console.warn('⚠️ Error cargando logo:', getErrorMessage(error))
        }
      }
      
      // Si no encontramos ningún logo, marcar como verificado
      clearTimeout(timeoutId)
      logoCache.hasChecked = true
      logoCache.isChecking = false
      setHasChecked(true)
    }

    checkCustomLogo()

    // Listener para cambios en el caché compartido
    const handleCacheUpdate = (url: string | null, version: number) => {
      console.log('🔄 Actualizando logo desde caché compartido, versión:', version)
      setCustomLogoUrl(url)
      setHasChecked(true)
      setLogoVersion(version)
    }

    logoListeners.add(handleCacheUpdate)
    
    // Si el logo ya estaba cacheado, sincronizar versión
    if (logoCache.logoUrl && logoCache.version > 0) {
      setLogoVersion(logoCache.version)
    }

    // Escuchar eventos de actualización del logo
    const handleLogoUpdate = (event: CustomEvent) => {
      const { filename, url, confirmed } = event.detail || {}
      
      console.log('📢 Evento logoUpdated recibido:', { filename, url, confirmed })
      
      // Si solo viene confirmed: true sin filename ni url, ignorar
      if (confirmed && !filename && !url) {
        console.warn('Evento logoUpdated recibido con confirmed pero sin filename/url')
        return
      }
      
      // Cuando se confirma el logo, invalidar caché y recargar desde configuración
      if (confirmed && (filename || url)) {
        console.log('🔄 Logo confirmado, invalidando caché y recargando desde configuración')
        // Invalidar caché para forzar recarga desde BD
        logoCache.logoUrl = null
        logoCache.hasChecked = false
        logoCache.isChecking = false
        
        // Recargar desde configuración general para obtener logo_filename persistido en BD
        fetch('/api/v1/configuracion/general')
          .then(res => res.json())
          .then(async config => {
            let newLogoUrl: string | null = null
            
            if (config.logo_filename) {
              const logoPath = `/api/v1/configuracion/logo/${config.logo_filename}`
              // ✅ Verificar primero si existe con HEAD request
              try {
                const headResponse = await fetch(logoPath, { method: 'HEAD' })
                if (headResponse.ok) {
                  newLogoUrl = `${logoPath}?t=${Date.now()}`
                  console.log('✅ Logo recargado desde configuración (BD):', config.logo_filename)
                } else {
                  console.warn('⚠️ Logo no encontrado al recargar desde configuración:', config.logo_filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  notifyLogoListeners(null, logoCache.version)
                  return
                }
              } catch (headError) {
                console.warn('⚠️ Error verificando logo al recargar:', headError)
                logoCache.logoNotFound = true
                logoCache.logoUrl = null
                logoCache.hasChecked = true
                logoCache.version += 1
                notifyLogoListeners(null, logoCache.version)
                return
              }
            } else if (filename) {
              // Fallback: usar filename del evento si no está en BD aún
              const logoPath = `/api/v1/configuracion/logo/${filename}`
              // ✅ Verificar primero si existe
              try {
                const headResponse = await fetch(logoPath, { method: 'HEAD' })
                if (headResponse.ok) {
                  newLogoUrl = `${logoPath}?t=${Date.now()}`
                  console.log('✅ Logo actualizado desde evento (fallback):', filename)
                } else {
                  console.warn('⚠️ Logo no encontrado en fallback:', filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  notifyLogoListeners(null, logoCache.version)
                  return
                }
              } catch (headError) {
                console.warn('⚠️ Error verificando logo en fallback:', headError)
                logoCache.logoNotFound = true
                logoCache.logoUrl = null
                logoCache.hasChecked = true
                logoCache.version += 1
                notifyLogoListeners(null, logoCache.version)
                return
              }
            }
            
            if (newLogoUrl) {
              // Actualizar caché y notificar a todos los listeners
              logoCache.logoUrl = newLogoUrl
              logoCache.logoNotFound = false // ✅ Resetear flag cuando se actualiza el logo
              logoCache.hasChecked = true
              logoCache.version += 1
              notifyLogoListeners(newLogoUrl, logoCache.version)
            }
          })
          .catch(err => {
            console.warn('⚠️ Error recargando logo desde configuración:', err)
            // Fallback: usar valores del evento directamente, pero verificar primero
            let newLogoUrl: string | null = null
            if (url) {
              // Si tenemos URL directa, verificar que existe
              fetch(url, { method: 'HEAD' })
                .then(headRes => {
                  if (headRes.ok) {
                    newLogoUrl = `${url}?t=${Date.now()}`
                    logoCache.logoUrl = newLogoUrl
                    logoCache.logoNotFound = false
                    logoCache.hasChecked = true
                    logoCache.version += 1
                    notifyLogoListeners(newLogoUrl, logoCache.version)
                  } else {
                    logoCache.logoNotFound = true
                    logoCache.logoUrl = null
                    logoCache.hasChecked = true
                    logoCache.version += 1
                    notifyLogoListeners(null, logoCache.version)
                  }
                })
                .catch(() => {
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  notifyLogoListeners(null, logoCache.version)
                })
            } else if (filename) {
              const logoPath = `/api/v1/configuracion/logo/${filename}`
              // Verificar primero si existe
              fetch(logoPath, { method: 'HEAD' })
                .then(headRes => {
                  if (headRes.ok) {
                    newLogoUrl = `${logoPath}?t=${Date.now()}`
                    logoCache.logoUrl = newLogoUrl
                    logoCache.logoNotFound = false
                    logoCache.hasChecked = true
                    logoCache.version += 1
                    notifyLogoListeners(newLogoUrl, logoCache.version)
                  } else {
                    logoCache.logoNotFound = true
                    logoCache.logoUrl = null
                    logoCache.hasChecked = true
                    logoCache.version += 1
                    notifyLogoListeners(null, logoCache.version)
                  }
                })
                .catch(() => {
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  notifyLogoListeners(null, logoCache.version)
                })
            }
          })
        return
      }
      
      // Para actualizaciones no confirmadas (preview durante carga), actualizar directamente
      let newLogoUrl: string | null = null
      
      if (url) {
        // Recargar el logo con timestamp para evitar caché
        newLogoUrl = `${url}?t=${Date.now()}`
      } else if (filename) {
        // Si solo tenemos el filename, construir el path
        const logoPath = `/api/v1/configuracion/logo/${filename}`
        newLogoUrl = `${logoPath}?t=${Date.now()}`
      }
      
      if (newLogoUrl) {
        // Actualizar cache y notificar a todos los listeners
        console.log('🔄 Actualizando logo (preview):', newLogoUrl)
        logoCache.logoUrl = newLogoUrl
        logoCache.logoNotFound = false // ✅ Resetear flag cuando se actualiza el logo
        logoCache.hasChecked = true
        logoCache.version += 1
        notifyLogoListeners(newLogoUrl, logoCache.version)
      }
    }

    window.addEventListener('logoUpdated', handleLogoUpdate as EventListener)

    return () => {
      window.removeEventListener('logoUpdated', handleLogoUpdate as EventListener)
      logoListeners.delete(handleCacheUpdate)
    }
  }, [])

  // Si hay logo personalizado, mostrar imagen
  // Usar logoVersion como key para forzar re-render cuando cambia
  if (customLogoUrl && !logoCache.logoNotFound) {
    return (
      <img
        key={`logo-${logoVersion}-${customLogoUrl}`}
        src={customLogoUrl}
        alt="Logo de la empresa"
        className={cn(sizeMap[size], className, 'object-contain')}
        role="img"
        onError={(e) => {
          // ✅ Si falla la carga (404), marcar como no encontrado y evitar más intentos
          console.warn('⚠️ Error cargando logo, marcando como no encontrado:', customLogoUrl)
          logoCache.logoNotFound = true
          logoCache.logoUrl = null
          logoCache.version += 1
          setCustomLogoUrl(null)
          setHasChecked(true)
          setLogoVersion(logoCache.version)
          // No intentar recargar - el logo no existe
        }}
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

