import { useState, useEffect } from 'react'
import { cn } from '@/utils'
import { getErrorMessage, isAxiosError } from '@/types/errors'
import { safeGetItem, safeSetItem } from '@/utils/storage'
import { useIsMounted } from '@/hooks/useIsMounted'

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
// ✅ MEJORADO: Ahora persiste metadatos en localStorage para evitar placeholder al recargar
interface LogoCache {
  logoUrl: string | null
  isChecking: boolean
  hasChecked: boolean
  version: number // Contador de versión para forzar actualizaciones
  logoNotFound: boolean // ✅ Flag para recordar que el logo no existe (evitar requests repetidos)
  logoFilename: string | null // ✅ Nombre del archivo del logo para persistencia
}

// Función para cargar metadatos del logo desde localStorage
const loadLogoMetadata = (): Partial<LogoCache> => {
  try {
    const cached = safeGetItem('logo_metadata', null)
    if (cached && cached.logoFilename) {
      // Construir URL del logo desde el nombre del archivo cacheado
      const logoPath = `/api/v1/configuracion/logo/${cached.logoFilename}`
      return {
        logoUrl: `${logoPath}?t=${Date.now()}`,
        logoFilename: cached.logoFilename,
        hasChecked: true,
        logoNotFound: false,
      }
    }
  } catch (error) {
    console.warn('Error cargando metadatos del logo:', error)
  }
  return {}
}

// Función para guardar metadatos del logo en localStorage
const saveLogoMetadata = (filename: string | null) => {
  try {
    if (filename) {
      safeSetItem('logo_metadata', { logoFilename: filename, timestamp: Date.now() })
    } else {
      safeSetItem('logo_metadata', null)
    }
  } catch (error) {
    console.warn('Error guardando metadatos del logo:', error)
  }
}

// Inicializar caché con metadatos guardados
const initialMetadata = loadLogoMetadata()
const logoCache: LogoCache = {
  logoUrl: initialMetadata.logoUrl || null,
  isChecking: false,
  hasChecked: initialMetadata.hasChecked || false,
  version: 0,
  logoNotFound: initialMetadata.logoNotFound || false,
  logoFilename: initialMetadata.logoFilename || null,
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
  const [imageLoaded, setImageLoaded] = useState(false) // ✅ Estado para controlar cuando la imagen está completamente cargada
  const isMounted = useIsMounted()

  useEffect(() => {
    // ✅ PRIORIDAD 1: Si ya verificamos y el logo NO existe, no hacer nada más
    if (logoCache.logoNotFound) {
      setHasChecked(true)
      setCustomLogoUrl(null)
      return
    }

    // ✅ PRIORIDAD 2: Si ya tenemos el logo cacheado, usarlo temporalmente PERO verificar si hay actualización
    // Esto evita mostrar el logo antiguo mientras se verifica el nuevo
    if (logoCache.logoUrl && logoCache.hasChecked) {
      setCustomLogoUrl(logoCache.logoUrl)
      setHasChecked(true)
      // ✅ Si el logo está cacheado desde localStorage, intentar precargarlo
      if (logoCache.logoFilename && !logoCache.logoNotFound) {
        const img = new Image()
        img.onload = () => setImageLoaded(true)
        img.onerror = () => setImageLoaded(false)
        img.src = logoCache.logoUrl
      }
      // ✅ NO retornar aquí - continuar para verificar si hay una versión más reciente en el servidor
      // Esto asegura que si el logo cambió, se actualice inmediatamente sin mostrar la versión antigua
    }

    // ✅ PRIORIDAD 3: Si otra instancia ya está verificando, esperar a que termine
    if (logoCache.isChecking) {
      // Esperar hasta que termine la verificación
      const checkInterval = setInterval(() => {
        if (!logoCache.isChecking) {
          if (logoCache.logoNotFound) {
            if (isMounted()) {
              setCustomLogoUrl(null)
            }
          } else {
            if (isMounted()) {
              setCustomLogoUrl(logoCache.logoUrl)
              setLogoVersion(logoCache.version)
            }
          }
          if (isMounted()) {
            setHasChecked(true)
          }
          clearInterval(checkInterval)
        }
      }, 50) // ✅ Reducir intervalo para respuesta más rápida

      return () => clearInterval(checkInterval)
    }

    // ✅ PRIORIDAD 4: Si ya verificamos pero no hay logo (sin logoNotFound), no hacer nada
    if (logoCache.hasChecked && !logoCache.logoUrl && !logoCache.logoFilename) {
      setHasChecked(true)
      return
    }

    // ✅ Marcar que estamos verificando ANTES de hacer cualquier request
    logoCache.isChecking = true

    let controller: AbortController | null = null
    let timeoutId: NodeJS.Timeout | null = null

    // Intentar cargar el logo personalizado desde el API
    const checkCustomLogo = async () => {
      controller = new AbortController()
      timeoutId = setTimeout(() => controller?.abort(), 5000) // Timeout de 5 segundos

      try {
        // PRIMERO: Intentar obtener el nombre del logo desde la configuración general
        try {
          const configResponse = await fetch('/api/v1/configuracion/general', {
            signal: controller.signal,
          })
          
          // ✅ Verificar si el componente sigue montado antes de continuar
          if (!isMounted()) {
            clearTimeout(timeoutId)
            return
          }
          
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
                
                // ✅ Verificar si el componente sigue montado antes de continuar
                if (!isMounted()) {
                  clearTimeout(timeoutId)
                  return
                }
                
                if (headResponse.ok) {
                  // Logo existe, usar URL con timestamp
                  const logoUrl = `${logoPath}?t=${Date.now()}`
                  
                  // ✅ Verificar si el logo cambió comparando el filename
                  const logoChanged = logoCache.logoFilename !== config.logo_filename
                  
                  logoCache.logoUrl = logoUrl
                  logoCache.logoFilename = config.logo_filename // ✅ Guardar nombre del archivo
                  logoCache.logoNotFound = false // ✅ Resetear flag
                  logoCache.hasChecked = true
                  
                  // ✅ Solo incrementar versión si el logo realmente cambió
                  if (logoChanged) {
                    logoCache.version += 1
                  }
                  
                  // ✅ Guardar metadatos en localStorage para persistencia
                  saveLogoMetadata(config.logo_filename)
                  
                  if (isMounted()) {
                    // ✅ Actualizar inmediatamente si el logo cambió (filename diferente)
                    // Si el logo no cambió, mantener el URL cacheado pero actualizar el timestamp para evitar caché del navegador
                    if (logoChanged) {
                      setCustomLogoUrl(logoUrl)
                      setImageLoaded(false) // ✅ Resetear estado de carga cuando cambia el URL
                      setLogoVersion(logoCache.version)
                    } else if (logoCache.logoUrl) {
                      // ✅ Mismo logo, pero actualizar URL con nuevo timestamp para evitar caché del navegador
                      // Solo actualizar si el URL actual no tiene timestamp (para forzar recarga si es necesario)
                      const currentUrl = logoCache.logoUrl
                      if (!currentUrl.includes('?t=')) {
                        setCustomLogoUrl(logoUrl)
                      }
                      // Si ya tiene timestamp, mantener el URL actual para evitar cambios visuales innecesarios
                    }
                    setHasChecked(true)
                  }
                  clearTimeout(timeoutId)
                  logoCache.isChecking = false
                  
                  // ✅ Solo notificar si el logo cambió para evitar actualizaciones innecesarias
                  if (logoChanged) {
                    notifyLogoListeners(logoUrl, logoCache.version)
                    console.debug('✅ Logo actualizado desde configuración:', config.logo_filename)
                  } else {
                    console.debug('✅ Logo verificado (sin cambios):', config.logo_filename)
                  }
                  return
                } else {
                  // Logo no existe (404), marcar como no encontrado
                  console.warn('⚠️ Logo no encontrado en servidor (HEAD 404):', config.logo_filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.logoFilename = null // ✅ Limpiar nombre del archivo
                  logoCache.hasChecked = true
                  logoCache.isChecking = false
                  // ✅ Limpiar metadatos guardados
                  saveLogoMetadata(null)
                  if (isMounted()) {
                    setCustomLogoUrl(null)
                    setHasChecked(true)
                  }
                  clearTimeout(timeoutId)
                  notifyLogoListeners(null, logoCache.version) // ✅ Notificar a todas las instancias
                  return
                }
              } catch (headError: unknown) {
                // Si HEAD falla, asumir que no existe (evitar requests repetidos)
                const error = headError as { name?: string }
                if (error?.name !== 'AbortError') {
                  console.warn('⚠️ Error verificando logo (HEAD), asumiendo que no existe:', getErrorMessage(headError))
                }
                logoCache.logoNotFound = true
                logoCache.logoUrl = null
                logoCache.hasChecked = true
                logoCache.isChecking = false
                if (isMounted()) {
                  setCustomLogoUrl(null)
                  setHasChecked(true)
                }
                clearTimeout(timeoutId)
                notifyLogoListeners(null, logoCache.version) // ✅ Notificar a todas las instancias
                return
              }
            } else {
              // Si no hay logo_filename en la configuración, no hay logo personalizado
              // No hacer solicitudes HEAD innecesarias
              logoCache.hasChecked = true
              logoCache.isChecking = false
              if (isMounted()) {
                setHasChecked(true)
              }
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
          if (isMounted()) {
            setHasChecked(true)
          }
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
      if (isMounted()) {
        setHasChecked(true)
      }
    }

    checkCustomLogo()

    // Listener para cambios en el caché compartido
    const handleCacheUpdate = (url: string | null, version: number) => {
      if (!isMounted()) return
      
      // ✅ Extraer filename del URL para comparar si es el mismo logo
      const currentFilename = logoCache.logoFilename
      let newFilename: string | null = null
      if (url) {
        const urlMatch = url.match(/\/logo\/([^/?]+)/)
        newFilename = urlMatch ? urlMatch[1] : null
      }
      
      // ✅ Solo actualizar si el filename realmente cambió (no solo la versión)
      const filenameChanged = newFilename !== currentFilename
      const hadNoLogo = !currentFilename && !customLogoUrl
      
      if (filenameChanged || hadNoLogo) {
        // ✅ Solo mostrar mensaje si el logo realmente cambió
        if (filenameChanged && currentFilename) {
          console.debug('🔄 Actualizando logo desde caché compartido, versión:', version, 'filename:', newFilename)
        }
        setCustomLogoUrl(url)
        setImageLoaded(false) // ✅ Resetear estado de carga cuando se actualiza desde caché
        setLogoVersion(version)
        setHasChecked(true)
      } else if (version > logoVersion) {
        // ✅ Mismo logo, solo actualizar versión sin cambiar el URL (evita parpadeo)
        setLogoVersion(version)
      }
    }

    logoListeners.add(handleCacheUpdate)
    
    // Si el logo ya estaba cacheado, sincronizar versión
    if (logoCache.logoUrl && logoCache.version > 0) {
      setLogoVersion(logoCache.version)
    }

    // Escuchar eventos de actualización del logo
    const handleLogoUpdate = (event: CustomEvent) => {
      const { filename, url, confirmed } = event.detail || {}
      
      console.debug('📢 Evento logoUpdated recibido:', { filename, url, confirmed })
      
      // Si solo viene confirmed: true sin filename ni url, ignorar
      if (confirmed && !filename && !url) {
        console.warn('Evento logoUpdated recibido con confirmed pero sin filename/url')
        return
      }
      
      // Cuando se confirma el logo, invalidar caché y recargar desde configuración
      if (confirmed && (filename || url)) {
        console.debug('🔄 Logo confirmado, invalidando caché y recargando desde configuración')
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
                  console.debug('✅ Logo recargado desde configuración (BD):', config.logo_filename)
                } else {
                  console.warn('⚠️ Logo no encontrado al recargar desde configuración:', config.logo_filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.logoFilename = null // ✅ Limpiar nombre del archivo
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  saveLogoMetadata(null) // ✅ Limpiar metadatos guardados
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
                  console.debug('✅ Logo actualizado desde evento (fallback):', filename)
                } else {
                  console.warn('⚠️ Logo no encontrado en fallback:', filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.logoFilename = null // ✅ Limpiar nombre del archivo
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  saveLogoMetadata(null) // ✅ Limpiar metadatos guardados
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
              const logoFilename = config?.logo_filename || filename || null
              logoCache.logoUrl = newLogoUrl
              logoCache.logoFilename = logoFilename // ✅ Guardar nombre del archivo
              logoCache.logoNotFound = false // ✅ Resetear flag cuando se actualiza el logo
              logoCache.hasChecked = true
              logoCache.version += 1
              // ✅ Guardar metadatos en localStorage
              if (logoFilename) {
                saveLogoMetadata(logoFilename)
              }
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
        console.debug('🔄 Actualizando logo (preview):', newLogoUrl)
        const logoFilename = filename || null
        logoCache.logoUrl = newLogoUrl
        logoCache.logoFilename = logoFilename // ✅ Guardar nombre del archivo
        logoCache.logoNotFound = false // ✅ Resetear flag cuando se actualiza el logo
        logoCache.hasChecked = true
        logoCache.version += 1
        // ✅ Guardar metadatos en localStorage si tenemos filename
        if (logoFilename) {
          saveLogoMetadata(logoFilename)
        }
        notifyLogoListeners(newLogoUrl, logoCache.version)
      }
    }

    window.addEventListener('logoUpdated', handleLogoUpdate as EventListener)

    return () => {
      // ✅ Cancelar peticiones en curso si el componente se desmonta
      if (controller) {
        controller.abort()
      }
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      window.removeEventListener('logoUpdated', handleLogoUpdate as EventListener)
      logoListeners.delete(handleCacheUpdate)
    }
  }, [])

  // ✅ PRIORIDAD: Si el logo está marcado como no encontrado, NO renderizar <img> (evitar GET requests)
  // Si hay logo personalizado Y NO está marcado como no encontrado, mostrar imagen
  if (customLogoUrl && !logoCache.logoNotFound) {
    return (
      <div className={cn(sizeMap[size], className, 'relative')}>
        {/* Mostrar SVG por defecto mientras la imagen se carga */}
        {!imageLoaded && (
          <svg 
            className={cn(sizeMap[size], 'absolute inset-0')}
            viewBox="0 0 48 48" 
            xmlns="http://www.w3.org/2000/svg"
            role="img"
            aria-label="RAPICREDIT Logo"
          >
            <defs>
              <filter id={`shadowR-${uniqueId}`} x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="2" stdDeviation="2.5" floodColor="#000000" floodOpacity="0.25"/>
              </filter>
              <filter id={`shadowDot-${uniqueId}`} x="-50%" y="-50%" width="200%" height="200%">
                <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor="#000000" floodOpacity="0.3"/>
              </filter>
              <filter id={`glowDot-${uniqueId}`}>
                <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <g filter={`url(#shadowR-${uniqueId})`}>
              <rect x="7" y="5" width="9" height="28" rx="1.5" className="fill-slate-900"/>
              <rect x="7" y="5" width="9" height="28" rx="1.5" fill="none" stroke="#E0E7FF" strokeWidth="0.5" opacity="0.6"/>
              <path d="M 16 5 L 16 14 Q 16 9 21 9 Q 26 9 27.5 11.5 L 27.5 17 Q 27.5 14.5 25 14.5 L 22 14.5 Q 20 14.5 18.5 15.5 L 16 18 Z" 
                    className="fill-slate-900"/>
              <path d="M 16 5 L 16 14 Q 16 9 21 9 Q 26 9 27.5 11.5 L 27.5 17 Q 27.5 14.5 25 14.5 L 22 14.5 Q 20 14.5 18.5 15.5 L 16 18 Z" 
                    fill="none" stroke="#E0E7FF" strokeWidth="0.5" opacity="0.6"/>
              <path d="M 16 19 L 24 11 L 30 11 L 21 19 L 21 21 L 28 27 L 34 27 L 25 21 L 23 21 Z" 
                    className="fill-slate-900"/>
              <path d="M 16 19 L 24 11 L 30 11 L 21 19 L 21 21 L 28 27 L 34 27 L 25 21 L 23 21 Z" 
                    fill="none" stroke="#E0E7FF" strokeWidth="0.5" opacity="0.6"/>
              <path d="M 28 27 L 34 27 L 32 24 L 30 24 Z" 
                    className="fill-slate-900"/>
            </g>
            <g filter={`url(#shadowDot-${uniqueId})`}>
              <circle cx="11" cy="41" r="6" className="fill-orange-600" filter={`url(#glowDot-${uniqueId})`}/>
              <circle cx="11" cy="41" r="4.5" className="fill-orange-500"/>
              <circle cx="10" cy="40" r="1.5" className="fill-orange-400" opacity="0.8"/>
            </g>
          </svg>
        )}
        {/* Imagen del logo personalizado - se muestra cuando está completamente cargada */}
        <img
          key={`logo-${logoVersion}-${customLogoUrl}`}
          src={customLogoUrl}
          alt="Logo de la empresa"
          className={cn(
            sizeMap[size], 
            'object-contain transition-opacity duration-300',
            imageLoaded ? 'opacity-100' : 'opacity-0'
          )}
          role="img"
          loading="eager"
          onLoad={() => {
            // ✅ Cuando la imagen se carga completamente, marcarla como cargada
            setImageLoaded(true)
          }}
          onError={(e) => {
            // ✅ Si falla la carga (404), marcar como no encontrado y evitar más intentos
            console.warn('⚠️ Error cargando logo (GET falló), marcando como no encontrado:', customLogoUrl)
            logoCache.logoNotFound = true
            logoCache.logoUrl = null
            logoCache.version += 1
            setCustomLogoUrl(null)
            setHasChecked(true)
            setImageLoaded(false)
            setLogoVersion(logoCache.version)
            notifyLogoListeners(null, logoCache.version) // ✅ Notificar a todas las instancias
            // No intentar recargar - el logo no existe
          }}
        />
      </div>
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

