import { useState, useEffect } from 'react'
import { cn } from '@/utils'
import { getErrorMessage, isAxiosError } from '@/types/errors'
import { safeGetItem, safeSetItem } from '@/utils/storage'
import { useIsMounted } from '@/hooks/useIsMounted'

interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  forceDefault?: boolean // ✅ Opción para forzar el uso del logo por defecto
}

// ✅ Función para limpiar el caché del logo (útil para debugging o reset)
export function clearLogoCache() {
  logoCache.logoUrl = null
  logoCache.logoFilename = null
  logoCache.logoNotFound = true
  logoCache.hasChecked = false
  logoCache.isChecking = false
  logoCache.version += 1
  saveLogoMetadata(null)
  notifyLogoListeners(null, logoCache.version)
  console.log('✅ Caché del logo limpiado, se usará el logo por defecto')
}

// ✅ Exponer función globalmente para debugging (solo en desarrollo)
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  ;(window as any).clearLogoCache = clearLogoCache
  console.log('💡 Función de debugging disponible: window.clearLogoCache() para limpiar el caché del logo')
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
// ✅ MEJORADO: Ahora persiste metadatos en localStorage para evitar recargas innecesarias
interface LogoCache {
  logoUrl: string | null
  isChecking: boolean
  hasChecked: boolean
  version: number // Contador de versión para forzar actualizaciones
  logoNotFound: boolean // ✅ Flag para recordar que el logo no existe (evitar requests repetidos)
  logoFilename: string | null // ✅ Nombre del archivo del logo para persistencia
  lastCheckTime: number | null // ✅ Timestamp de la última verificación para evitar requests frecuentes
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

export function Logo({ className, size = 'md', forceDefault = false }: LogoProps) {
  const [customLogoUrl, setCustomLogoUrl] = useState<string | null>(forceDefault ? null : logoCache.logoUrl)
  const [hasChecked, setHasChecked] = useState(forceDefault ? true : logoCache.hasChecked)
  const [logoVersion, setLogoVersion] = useState(logoCache.version)
  const [imageLoaded, setImageLoaded] = useState(false) // ✅ Estado para controlar cuando la imagen está completamente cargada
  const isMounted = useIsMounted()

  useEffect(() => {
    // ✅ PRIORIDAD 0: Si forceDefault está activado, usar siempre el logo por defecto
    if (forceDefault) {
      setCustomLogoUrl(null)
      setHasChecked(true)
      return
    }

    // ✅ PRIORIDAD 1: Si ya verificamos y el logo NO existe, no hacer nada más
    if (logoCache.logoNotFound) {
      setHasChecked(true)
      setCustomLogoUrl(null)
      return
    }

    // ✅ PRIORIDAD 2: Si ya tenemos el logo cacheado, usarlo directamente
    // Si el logo está disponible, mostrarlo inmediatamente
    if (logoCache.logoUrl && logoCache.hasChecked) {
      setCustomLogoUrl(logoCache.logoUrl)
      setHasChecked(true)
      // ✅ Si el logo está cacheado, marcarlo como cargado inmediatamente
      if (logoCache.logoFilename && !logoCache.logoNotFound) {
        setImageLoaded(true) // ✅ Mostrar logo directamente
      }
      // ✅ Si el logo está cacheado y ya fue verificado recientemente (< 5 minutos),
      // no hacer nueva solicitud para evitar abortos innecesarios
      const cacheAge = Date.now() - (logoCache.lastCheckTime || 0)
      if (cacheAge < 300000) { // 5 minutos
        return // Usar logo cacheado sin verificar nuevamente
      }
      // ✅ Continuar para verificar si hay una versión más reciente en el servidor
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
                  logoCache.lastCheckTime = Date.now() // ✅ Guardar timestamp de verificación

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
                      setLogoVersion(logoCache.version)
                      // ✅ Precargar el nuevo logo y mostrarlo directamente cuando esté listo
                      const img = new Image()
                      img.onload = () => {
                        if (isMounted()) {
                          setImageLoaded(true) // ✅ Mostrar logo personalizado directamente
                        }
                      }
                      img.onerror = () => {
                        if (isMounted()) {
                          setImageLoaded(false)
                        }
                      }
                      img.src = logoUrl
                      // ✅ Si hay logo anterior, mantenerlo visible hasta que el nuevo esté listo
                      if (logoCache.logoUrl) {
                        setImageLoaded(true)
                      }
                    } else if (logoCache.logoUrl) {
                      // ✅ Mismo logo, pero actualizar URL con nuevo timestamp para evitar caché del navegador
                      // Solo actualizar si el URL actual no tiene timestamp (para forzar recarga si es necesario)
                      const currentUrl = logoCache.logoUrl
                      if (!currentUrl.includes('?t=')) {
                        setCustomLogoUrl(logoUrl)
                        // ✅ Mantener logo visible mientras se actualiza
                        setImageLoaded(true)
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
                    // Solo mostrar en desarrollo para evitar ruido en producción
                    if (process.env.NODE_ENV === 'development') {
                      console.debug('✅ Logo actualizado desde configuración:', config.logo_filename)
                    }
                  } else {
                    // Solo mostrar en desarrollo
                    if (process.env.NODE_ENV === 'development') {
                      console.debug('✅ Logo verificado (sin cambios):', config.logo_filename)
                    }
                  }
                  return
                } else {
                  // Logo no existe (404), marcar como no encontrado
                  console.warn('⚠️ Logo no encontrado en servidor (HEAD 404):', config.logo_filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.logoFilename = null // ✅ Limpiar nombre del archivo
                  logoCache.hasChecked = true
                  logoCache.lastCheckTime = Date.now() // ✅ Guardar timestamp de verificación
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
              logoCache.lastCheckTime = Date.now() // ✅ Guardar timestamp de verificación
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
          logoCache.lastCheckTime = Date.now() // ✅ Guardar timestamp de verificación (incluso si falló)
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
        setLogoVersion(version)
        setHasChecked(true)
        // ✅ Precargar el logo y mostrarlo directamente cuando esté listo
        if (url) {
          // ✅ Si hay logo anterior, mantenerlo visible hasta que el nuevo esté listo
          if (customLogoUrl) {
            setImageLoaded(true)
          }
          const img = new Image()
          img.onload = () => {
            if (isMounted()) {
              setImageLoaded(true) // ✅ Mostrar logo personalizado directamente
            }
          }
          img.onerror = () => {
            if (isMounted()) {
              setImageLoaded(false)
            }
          }
          img.src = url
        } else {
          setImageLoaded(false)
        }
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
              // ✅ Actualizar estado local para mostrar logo directamente
              if (isMounted()) {
                setCustomLogoUrl(newLogoUrl)
                setLogoVersion(logoCache.version)
                // ✅ Precargar el logo y mostrarlo directamente cuando esté listo
                const img = new Image()
                img.onload = () => {
                  if (isMounted()) {
                    setImageLoaded(true) // ✅ Mostrar logo personalizado directamente
                  }
                }
                img.onerror = () => {
                  if (isMounted()) {
                    setImageLoaded(false)
                  }
                }
                img.src = newLogoUrl
                // ✅ Si hay logo anterior, mantenerlo visible hasta que el nuevo esté listo
                if (customLogoUrl) {
                  setImageLoaded(true)
                }
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
        // ✅ Actualizar estado local para mostrar logo directamente
        if (isMounted()) {
          setCustomLogoUrl(newLogoUrl)
          setLogoVersion(logoCache.version)
          // ✅ Precargar el logo y mostrarlo directamente cuando esté listo
          const img = new Image()
          img.onload = () => {
            if (isMounted()) {
              setImageLoaded(true) // ✅ Mostrar logo personalizado directamente
            }
          }
          img.onerror = () => {
            if (isMounted()) {
              setImageLoaded(false)
            }
          }
          img.src = newLogoUrl
          // ✅ Si hay logo anterior, mantenerlo visible hasta que el nuevo esté listo
          if (customLogoUrl) {
            setImageLoaded(true)
          }
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
  }, [forceDefault, isMounted])

  // ✅ PRIORIDAD: Si forceDefault está activado, siempre mostrar logo por defecto
  if (forceDefault) {
    // Continuar al renderizado del SVG por defecto
  }
  // ✅ Si el logo está marcado como no encontrado, NO renderizar <img> (evitar GET requests)
  // Si hay logo personalizado Y NO está marcado como no encontrado, mostrar imagen directamente
  // ✅ CORRECCIÓN: Solo mostrar logo personalizado si realmente existe y está disponible Y no se fuerza el default
  else if (customLogoUrl && !logoCache.logoNotFound && hasChecked && !forceDefault) {
    return (
      <div className={cn('relative', sizeMap[size])}>
        {/* Indicador de carga mientras la imagen se carga */}
        {!imageLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100 rounded animate-pulse">
            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <img
          key={`logo-${logoVersion}-${customLogoUrl}`}
          src={customLogoUrl}
          alt="Logo de la empresa"
          className={cn(
            sizeMap[size],
            className,
            'object-contain',
            imageLoaded ? 'opacity-100' : 'opacity-0',
            'transition-opacity duration-300'
          )}
          role="img"
          loading="eager"
          onLoad={() => {
            // ✅ Cuando la imagen se carga completamente, marcarla como cargada
            if (isMounted()) {
              setImageLoaded(true)
            }
          }}
          onError={(e) => {
            // ✅ Si falla la carga (404 o imagen corrupta), marcar como no encontrado y limpiar caché
            console.warn('⚠️ Error cargando logo (GET falló o imagen inválida), limpiando caché:', customLogoUrl)
            logoCache.logoNotFound = true
            logoCache.logoUrl = null
            logoCache.logoFilename = null
            logoCache.version += 1
            // ✅ Limpiar metadatos del localStorage
            saveLogoMetadata(null)
            setCustomLogoUrl(null)
            setHasChecked(true)
            setImageLoaded(false)
            setLogoVersion(logoCache.version)
            notifyLogoListeners(null, logoCache.version) // ✅ Notificar a todas las instancias
            // No intentar recargar - el logo no existe o está corrupto
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
      {/* Letra R estilizada en azul oscuro (#2A3B8F) */}
      <g>
        {/* Tallo vertical principal */}
        <path d="M 8 4 L 8 32 L 16 32 L 16 28 L 12 28 L 12 4 Z" fill="#2A3B8F"/>
        
        {/* Curva superior de la R (bowl) */}
        <path 
          d="M 12 4 Q 12 8 18 8 Q 24 8 26 12 Q 26 16 20 16 L 16 16 Q 14 16 12 14 Z" 
          fill="#2A3B8F"
        />
        
        {/* Pierna diagonal de la R (extiende hacia abajo y derecha) */}
        <path 
          d="M 12 20 L 12 24 L 20 24 L 28 32 L 32 32 L 24 24 L 24 20 Z" 
          fill="#2A3B8F"
        />
      </g>

      {/* Círculo naranja sólido (#F57F20) debajo y ligeramente a la izquierda */}
      <circle cx="10" cy="40" r="5.5" fill="#F57F20"/>
    </svg>
  )
}

