import { useState, useEffect } from 'react'
import { cn } from '../../utils'
import { getErrorMessage, isAxiosError } from '../../types/errors'
import { safeGetItem, safeGetSessionItem, safeSetItem } from '../../utils/storage'
import { useIsMounted } from '../../hooks/useIsMounted'
import { apiClient } from '../../services/api'
import { env } from '../../config/env'

/** Base URL del API para peticiones (vacÃÂ­o = mismo origen). */
const getApiBase = () => (env.API_URL || '').replace(/\/$/, '')

/** Headers de auth para fetch (token desde storage; ApiClient no expone .defaults). */
function getAuthHeaders(): Record<string, string> {
  const rememberMe = safeGetItem('remember_me', false)
  let token = rememberMe ? safeGetItem('access_token', '') : safeGetSessionItem('access_token', '')
  if (token) {
    token = String(token).trim()
    if (token.startsWith('Bearer ')) token = token.slice(7).trim()
    if (token) return { Authorization: `Bearer ${token}` }
  }
  return {}
}
const isDev = typeof import.meta !== 'undefined' && (import.meta as { env?: { DEV?: boolean } }).env?.DEV
const devLog = (...args: unknown[]) => { if (isDev) console.log(...args) }
const devWarn = (...args: unknown[]) => { if (isDev) console.warn(...args) }
const devDebug = (...args: unknown[]) => { if (isDev) console.debug(...args) }

interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  forceDefault?: boolean // ÃÂ¢ÃÂÃ¢ÂÂ¦ OpciÃÂ³n para forzar el uso del logo por defecto
}

// ÃÂ¢ÃÂÃ¢ÂÂ¦ FunciÃÂ³n para limpiar el cachÃÂ© del logo (ÃÂºtil para debugging o reset)
export function clearLogoCache() {
  logoCache.logoUrl = null
  logoCache.logoFilename = null
  logoCache.logoNotFound = true
  logoCache.hasChecked = false
  logoCache.isChecking = false
  logoCache.version += 1
  saveLogoMetadata(null)
  notifyLogoListeners(null, logoCache.version)
  devLog('CachÃÂ© del logo limpiado, se usarÃÂ¡ el logo por defecto')
}

// ÃÂ¢ÃÂÃ¢ÂÂ¦ Exponer funciÃÂ³n globalmente para debugging (solo en desarrollo)
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  ;(window as any).clearLogoCache = clearLogoCache
  devLog('FunciÃÂ³n de debugging disponible: window.clearLogoCache() para limpiar el cachÃÂ© del logo')
}

const sizeMap = {
  sm: 'w-8 h-8',
  md: 'w-12 h-12',
  lg: 'w-16 h-16',
  xl: 'w-20 h-20',
}

// Logo por defecto (public/logos/rAPI.png); respeta base path (ej. /pagos/)
const DEFAULT_LOGO_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rAPI.png`

// Generar IDs ÃÂºnicos para evitar conflictos si hay mÃÂºltiples logos en la pÃÂ¡gina
const uniqueId = `logo-${Math.random().toString(36).substr(2, 9)}`

// Extensiones posibles del logo personalizado (ordenadas por prioridad)
const LOGO_EXTENSIONS = ['.svg', '.png', '.jpg', '.jpeg']

// Cache compartido en memoria para evitar mÃÂºltiples peticiones
// ÃÂ¢ÃÂÃ¢ÂÂ¦ MEJORADO: Ahora persiste metadatos en localStorage para evitar recargas innecesarias
interface LogoCache {
  logoUrl: string | null
  isChecking: boolean
  hasChecked: boolean
  version: number // Contador de versiÃÂ³n para forzar actualizaciones
  logoNotFound: boolean // ÃÂ¢ÃÂÃ¢ÂÂ¦ Flag para recordar que el logo no existe (evitar requests repetidos)
  logoFilename: string | null // ÃÂ¢ÃÂÃ¢ÂÂ¦ Nombre del archivo del logo para persistencia
  lastCheckTime: number | null // ÃÂ¢ÃÂÃ¢ÂÂ¦ Timestamp de la ÃÂºltima verificaciÃÂ³n para evitar requests frecuentes
}

// FunciÃÂ³n para cargar metadatos del logo desde localStorage
const loadLogoMetadata = (): Partial<LogoCache> => {
  try {
    const cached = safeGetItem('logo_metadata', null)
    if (cached && cached.logoFilename) {
      const base = getApiBase()
      const logoPath = `${base}/api/v1/configuracion/logo/${cached.logoFilename}`
      return {
        logoUrl: `${logoPath}?t=${Date.now()}`,
        logoFilename: cached.logoFilename,
        hasChecked: true,
        logoNotFound: false,
      }
    }
  } catch (error) {
    devWarn('Error cargando metadatos del logo:', error)
  }
  return {}
}

// FunciÃÂ³n para guardar metadatos del logo en localStorage
const saveLogoMetadata = (filename: string | null) => {
  try {
    if (filename) {
      safeSetItem('logo_metadata', { logoFilename: filename, timestamp: Date.now() })
    } else {
      safeSetItem('logo_metadata', null)
    }
  } catch (error) {
    devWarn('Error guardando metadatos del logo:', error)
  }
}

// Inicializar cachÃÂ© con metadatos guardados (evita DOMException "operation is insecure" en contextos restrictivos)
let initialMetadata: Partial<LogoCache> = {}
try {
  initialMetadata = loadLogoMetadata()
} catch {
  // Storage no disponible o contexto inseguro (iframe, privado, etc.)
}
const logoCache: LogoCache = {
  logoUrl: initialMetadata.logoUrl || null,
  isChecking: false,
  hasChecked: initialMetadata.hasChecked || false,
  version: 0,
  logoNotFound: initialMetadata.logoNotFound || false,
  logoFilename: initialMetadata.logoFilename || null,
  lastCheckTime: null, // ÃÂ¢ÃÂÃ¢ÂÂ¦ Inicializar timestamp de ÃÂºltima verificaciÃÂ³n
}

// Listeners para notificar a todos los componentes cuando cambia el logo
const logoListeners = new Set<(url: string | null, version: number) => void>()

function notifyLogoListeners(url: string | null, version: number) {
  logoListeners.forEach(listener => {
    try {
      listener(url, version)
    } catch (error) {
      devWarn('Error notificando listener de logo:', error)
    }
  })
}

export function Logo({ className, size = 'md', forceDefault = false }: LogoProps) {
  const [customLogoUrl, setCustomLogoUrl] = useState<string | null>(forceDefault ? null : logoCache.logoUrl)
  const [hasChecked, setHasChecked] = useState(forceDefault ? true : logoCache.hasChecked)
  const [logoVersion, setLogoVersion] = useState(logoCache.version)
  const [imageLoaded, setImageLoaded] = useState(false) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Estado para controlar cuando la imagen estÃÂ¡ completamente cargada
  const [defaultLogoFailed, setDefaultLogoFailed] = useState(false) // fallback cuando rAPI.png no carga (404 o no existe en build)
  const isMounted = useIsMounted()

  useEffect(() => {
    // ÃÂ¢ÃÂÃ¢ÂÂ¦ PRIORIDAD 0: Si forceDefault estÃÂ¡ activado, usar siempre el logo por defecto
    if (forceDefault) {
      setCustomLogoUrl(null)
      setHasChecked(true)
      return
    }

    // ÃÂ¢ÃÂÃ¢ÂÂ¦ PRIORIDAD 1: Si ya verificamos y el logo NO existe, no hacer nada mÃÂ¡s
    if (logoCache.logoNotFound) {
      setHasChecked(true)
      setCustomLogoUrl(null)
      return
    }

    // ÃÂ¢ÃÂÃ¢ÂÂ¦ PRIORIDAD 2: Si ya tenemos el logo cacheado, usarlo directamente
    // Si el logo estÃÂ¡ disponible, mostrarlo inmediatamente
    if (logoCache.logoUrl && logoCache.hasChecked) {
      setCustomLogoUrl(logoCache.logoUrl)
      setHasChecked(true)
      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si el logo estÃÂ¡ cacheado, marcarlo como cargado inmediatamente
      if (logoCache.logoFilename && !logoCache.logoNotFound) {
        setImageLoaded(true) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mostrar logo directamente
      }
      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si el logo estÃÂ¡ cacheado y ya fue verificado recientemente (< 5 minutos),
      // no hacer nueva solicitud para evitar abortos innecesarios
      const cacheAge = Date.now() - (logoCache.lastCheckTime || 0)
      if (cacheAge < 300000) { // 5 minutos
        return // Usar logo cacheado sin verificar nuevamente
      }
      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Continuar para verificar si hay una versiÃÂ³n mÃÂ¡s reciente en el servidor
      // Esto asegura que si el logo cambiÃÂ³, se actualice inmediatamente sin mostrar la versiÃÂ³n antigua
    }

    // ÃÂ¢ÃÂÃ¢ÂÂ¦ PRIORIDAD 3: Si otra instancia ya estÃÂ¡ verificando, esperar a que termine
    if (logoCache.isChecking) {
      // Esperar hasta que termine la verificaciÃÂ³n
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
      }, 50) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Reducir intervalo para respuesta mÃÂ¡s rÃÂ¡pida

      return () => clearInterval(checkInterval)
    }

    // ÃÂ¢ÃÂÃ¢ÂÂ¦ PRIORIDAD 4: Si ya verificamos pero no hay logo (sin logoNotFound), no hacer nada
    if (logoCache.hasChecked && !logoCache.logoUrl && !logoCache.logoFilename) {
      setHasChecked(true)
      return
    }

    // ÃÂ¢ÃÂÃ¢ÂÂ¦ Marcar que estamos verificando ANTES de hacer cualquier request
    logoCache.isChecking = true

    let controller: AbortController | null = null
    let timeoutId: NodeJS.Timeout | null = null

    // Intentar cargar el logo personalizado desde el API
    const checkCustomLogo = async () => {
      controller = new AbortController()
      timeoutId = setTimeout(() => controller?.abort(), 5000) // Timeout de 5 segundos

      try {
        // PRIMERO: Intentar obtener el nombre del logo desde la configuraciÃÂ³n general (apiClient = base URL correcta)
        try {
          const config = await apiClient.get<{ logo_filename?: string }>('/api/v1/configuracion/general', {
            signal: controller.signal,
          })

          // Verificar si el componente sigue montado antes de continuar
          if (!isMounted()) {
            clearTimeout(timeoutId)
            return
          }

          if (config?.logo_filename) {
            const base = getApiBase()
            const logoPath = `${base}/api/v1/configuracion/logo/${config.logo_filename}`

            // Verificar si el logo existe con HEAD request (mÃÂ¡s ligero que GET)
            try {
              const headResponse = await fetch(logoPath, {
                method: 'HEAD',
                signal: controller.signal,
                headers: getAuthHeaders(),
              })

                // ÃÂ¢ÃÂÃ¢ÂÂ¦ Verificar si el componente sigue montado antes de continuar
                if (!isMounted()) {
                  clearTimeout(timeoutId)
                  return
                }

                if (headResponse.ok) {
                  // Logo existe, usar URL con timestamp
                  const logoUrl = `${logoPath}?t=${Date.now()}`

                  // ÃÂ¢ÃÂÃ¢ÂÂ¦ Verificar si el logo cambiÃÂ³ comparando el filename
                  const logoChanged = logoCache.logoFilename !== config.logo_filename

                  logoCache.logoUrl = logoUrl
                  logoCache.logoFilename = config.logo_filename // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar nombre del archivo
                  logoCache.logoNotFound = false // ÃÂ¢ÃÂÃ¢ÂÂ¦ Resetear flag
                  logoCache.hasChecked = true
                  logoCache.lastCheckTime = Date.now() // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar timestamp de verificaciÃÂ³n

                  // ÃÂ¢ÃÂÃ¢ÂÂ¦ Solo incrementar versiÃÂ³n si el logo realmente cambiÃÂ³
                  if (logoChanged) {
                    logoCache.version += 1
                  }

                  // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar metadatos en localStorage para persistencia
                  saveLogoMetadata(config.logo_filename)

                  if (isMounted()) {
                    // ÃÂ¢ÃÂÃ¢ÂÂ¦ Actualizar inmediatamente si el logo cambiÃÂ³ (filename diferente)
                    // Si el logo no cambiÃÂ³, mantener el URL cacheado pero actualizar el timestamp para evitar cachÃÂ© del navegador
                    if (logoChanged) {
                      setCustomLogoUrl(logoUrl)
                      setLogoVersion(logoCache.version)
                      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Precargar el nuevo logo y mostrarlo directamente cuando estÃÂ© listo
                      const img = new Image()
                      img.onload = () => {
                        if (isMounted()) {
                          setImageLoaded(true) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mostrar logo personalizado directamente
                        }
                      }
                      img.onerror = () => {
                        if (isMounted()) {
                          setImageLoaded(false)
                        }
                      }
                      img.src = logoUrl
                      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si hay logo anterior, mantenerlo visible hasta que el nuevo estÃÂ© listo
                      if (logoCache.logoUrl) {
                        setImageLoaded(true)
                      }
                    } else if (logoCache.logoUrl) {
                      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mismo logo, pero actualizar URL con nuevo timestamp para evitar cachÃÂ© del navegador
                      // Solo actualizar si el URL actual no tiene timestamp (para forzar recarga si es necesario)
                      const currentUrl = logoCache.logoUrl
                      if (!currentUrl.includes('?t=')) {
                        setCustomLogoUrl(logoUrl)
                        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mantener logo visible mientras se actualiza
                        setImageLoaded(true)
                      }
                      // Si ya tiene timestamp, mantener el URL actual para evitar cambios visuales innecesarios
                    }
                    setHasChecked(true)
                  }
                  clearTimeout(timeoutId)
                  logoCache.isChecking = false

                  // ÃÂ¢ÃÂÃ¢ÂÂ¦ Solo notificar si el logo cambiÃÂ³ para evitar actualizaciones innecesarias
                  if (logoChanged) {
                    notifyLogoListeners(logoUrl, logoCache.version)
                    devDebug('Logo actualizado desde configuraciÃÂ³n:', config.logo_filename)
                  } else {
                    devDebug('Logo verificado (sin cambios):', config.logo_filename)
                  }
                  return
                } else {
                  // Logo no existe (404), marcar como no encontrado
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.logoFilename = null // ÃÂ¢ÃÂÃ¢ÂÂ¦ Limpiar nombre del archivo
                  logoCache.hasChecked = true
                  logoCache.lastCheckTime = Date.now() // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar timestamp de verificaciÃÂ³n
                  logoCache.isChecking = false
                  // ÃÂ¢ÃÂÃ¢ÂÂ¦ Limpiar metadatos guardados
                  saveLogoMetadata(null)
                  if (isMounted()) {
                    setCustomLogoUrl(null)
                    setHasChecked(true)
                  }
                  clearTimeout(timeoutId)
                  notifyLogoListeners(null, logoCache.version) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Notificar a todas las instancias
                  return
                }
              } catch (headError: unknown) {
                // Si HEAD falla, asumir que no existe (evitar requests repetidos)
                const error = headError as { name?: string }
                if (error?.name !== 'AbortError') {
                  devWarn('Error verificando logo (HEAD), asumiendo que no existe:', getErrorMessage(headError))
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
                notifyLogoListeners(null, logoCache.version) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Notificar a todas las instancias
                return
              }
          } else {
            // Si no hay logo_filename en la configuraciÃÂ³n, no hay logo personalizado
            logoCache.hasChecked = true
            logoCache.lastCheckTime = Date.now()
            logoCache.isChecking = false
            if (isMounted()) setHasChecked(true)
            clearTimeout(timeoutId)
            return
          }
        } catch (configError: unknown) {
          // Si falla obtener la configuraciÃÂ³n, marcar como verificado y no hacer mÃÂ¡s intentos
          const error = configError as { name?: string }
          if (error?.name !== 'AbortError') {
            devWarn('No se pudo obtener logo_filename desde configuraciÃÂ³n:', getErrorMessage(configError))
          }
          logoCache.hasChecked = true
          logoCache.lastCheckTime = Date.now() // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar timestamp de verificaciÃÂ³n (incluso si fallÃÂ³)
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
          devWarn('Error cargando logo:', getErrorMessage(error))
        }
      }

      // Si no encontramos ningÃÂºn logo, marcar como verificado
      clearTimeout(timeoutId)
      logoCache.hasChecked = true
      logoCache.isChecking = false
      if (isMounted()) {
        setHasChecked(true)
      }
    }

    // Retrasar fetch para no competir con auth/redirect y reducir NS_BINDING_ABORTED + "operation is insecure"
    const startId = setTimeout(() => {
      checkCustomLogo()
    }, 200)

    // Listener para cambios en el cachÃÂ© compartido
    const handleCacheUpdate = (url: string | null, version: number) => {
      if (!isMounted()) return

      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Extraer filename del URL para comparar si es el mismo logo
      const currentFilename = logoCache.logoFilename
      let newFilename: string | null = null
      if (url) {
        const urlMatch = url.match(/\/logo\/([^/?]+)/)
        newFilename = urlMatch ? urlMatch[1] : null
      }

      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Solo actualizar si el filename realmente cambiÃÂ³ (no solo la versiÃÂ³n)
      const filenameChanged = newFilename !== currentFilename
      const hadNoLogo = !currentFilename && !customLogoUrl

      if (filenameChanged || hadNoLogo) {
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Solo mostrar mensaje si el logo realmente cambiÃÂ³
        if (filenameChanged && currentFilename) {
          devDebug('ÃÂ°ÃÂ¸Ã¢ÂÂÃ¢ÂÂ Actualizando logo desde cachÃÂ© compartido, versiÃÂ³n:', version, 'filename:', newFilename)
        }
        setCustomLogoUrl(url)
        setLogoVersion(version)
        setHasChecked(true)
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Precargar el logo y mostrarlo directamente cuando estÃÂ© listo
        if (url) {
          // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si hay logo anterior, mantenerlo visible hasta que el nuevo estÃÂ© listo
          if (customLogoUrl) {
            setImageLoaded(true)
          }
          const img = new Image()
          img.onload = () => {
            if (isMounted()) {
              setImageLoaded(true) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mostrar logo personalizado directamente
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
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mismo logo, solo actualizar versiÃÂ³n sin cambiar el URL (evita parpadeo)
        setLogoVersion(version)
      }
    }

    logoListeners.add(handleCacheUpdate)

    // Si el logo ya estaba cacheado, sincronizar versiÃÂ³n
    if (logoCache.logoUrl && logoCache.version > 0) {
      setLogoVersion(logoCache.version)
    }

    // Escuchar eventos de actualizaciÃÂ³n del logo
    const handleLogoUpdate = (event: CustomEvent) => {
      const { filename, url, confirmed } = event.detail || {}

      devDebug('ÃÂ°ÃÂ¸Ã¢ÂÂÃÂ¢ Evento logoUpdated recibido:', { filename, url, confirmed })

      // Si solo viene confirmed: true sin filename ni url, ignorar
      if (confirmed && !filename && !url) {
        devWarn('Evento logoUpdated recibido con confirmed pero sin filename/url')
        return
      }

      // Cuando se confirma el logo, invalidar cachÃÂ© y recargar desde configuraciÃÂ³n
      if (confirmed && (filename || url)) {
        devDebug('ÃÂ°ÃÂ¸Ã¢ÂÂÃ¢ÂÂ Logo confirmado, invalidando cachÃÂ© y recargando desde configuraciÃÂ³n')
        // Invalidar cachÃÂ© para forzar recarga desde BD
        logoCache.logoUrl = null
        logoCache.hasChecked = false
        logoCache.isChecking = false

        // Recargar desde configuraciÃÂ³n general para obtener logo_filename persistido en BD
        const base = getApiBase()
        apiClient.get<{ logo_filename?: string }>('/api/v1/configuracion/general')
          .then(async config => {
            let newLogoUrl: string | null = null

            if (config.logo_filename) {
              const logoPath = `${base}/api/v1/configuracion/logo/${config.logo_filename}`
              try {
                const headResponse = await fetch(logoPath, { method: 'HEAD', headers: getAuthHeaders() })
                if (headResponse.ok) {
                  newLogoUrl = `${logoPath}?t=${Date.now()}`
                  devDebug('Logo recargado desde configuraciÃÂ³n (BD):', config.logo_filename)
                } else {
                  devWarn('Logo no encontrado al recargar desde configuraciÃÂ³n:', config.logo_filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.logoFilename = null // ÃÂ¢ÃÂÃ¢ÂÂ¦ Limpiar nombre del archivo
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  saveLogoMetadata(null) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Limpiar metadatos guardados
                  notifyLogoListeners(null, logoCache.version)
                  return
                }
              } catch (headError) {
                devWarn('Error verificando logo al recargar:', headError)
                logoCache.logoNotFound = true
                logoCache.logoUrl = null
                logoCache.hasChecked = true
                logoCache.version += 1
                notifyLogoListeners(null, logoCache.version)
                return
              }
            } else if (filename) {
              // Fallback: usar filename del evento si no estÃÂ¡ en BD aÃÂºn
              const logoPath = `${base}/api/v1/configuracion/logo/${filename}`
              try {
                const headResponse = await fetch(logoPath, { method: 'HEAD', headers: getAuthHeaders() })
                if (headResponse.ok) {
                  newLogoUrl = `${logoPath}?t=${Date.now()}`
                  devDebug('Logo actualizado desde evento (fallback):', filename)
                } else {
                  devWarn('Logo no encontrado en fallback:', filename)
                  logoCache.logoNotFound = true
                  logoCache.logoUrl = null
                  logoCache.logoFilename = null // ÃÂ¢ÃÂÃ¢ÂÂ¦ Limpiar nombre del archivo
                  logoCache.hasChecked = true
                  logoCache.version += 1
                  saveLogoMetadata(null) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Limpiar metadatos guardados
                  notifyLogoListeners(null, logoCache.version)
                  return
                }
              } catch (headError) {
                devWarn('Error verificando logo en fallback:', headError)
                logoCache.logoNotFound = true
                logoCache.logoUrl = null
                logoCache.hasChecked = true
                logoCache.version += 1
                notifyLogoListeners(null, logoCache.version)
                return
              }
            }

            if (newLogoUrl) {
              // Actualizar cachÃÂ© y notificar a todos los listeners
              const logoFilename = config?.logo_filename || filename || null
              logoCache.logoUrl = newLogoUrl
              logoCache.logoFilename = logoFilename // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar nombre del archivo
              logoCache.logoNotFound = false // ÃÂ¢ÃÂÃ¢ÂÂ¦ Resetear flag cuando se actualiza el logo
              logoCache.hasChecked = true
              logoCache.version += 1
              // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar metadatos en localStorage
              if (logoFilename) {
                saveLogoMetadata(logoFilename)
              }
              // ÃÂ¢ÃÂÃ¢ÂÂ¦ Actualizar estado local para mostrar logo directamente
              if (isMounted()) {
                setCustomLogoUrl(newLogoUrl)
                setLogoVersion(logoCache.version)
                // ÃÂ¢ÃÂÃ¢ÂÂ¦ Precargar el logo y mostrarlo directamente cuando estÃÂ© listo
                const img = new Image()
                img.onload = () => {
                  if (isMounted()) {
                    setImageLoaded(true) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mostrar logo personalizado directamente
                  }
                }
                img.onerror = () => {
                  if (isMounted()) {
                    setImageLoaded(false)
                  }
                }
                img.src = newLogoUrl
                // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si hay logo anterior, mantenerlo visible hasta que el nuevo estÃÂ© listo
                if (customLogoUrl) {
                  setImageLoaded(true)
                }
              }
              notifyLogoListeners(newLogoUrl, logoCache.version)
            }
          })
          .catch(err => {
            devWarn('Error recargando logo desde configuraciÃÂ³n:', err)
            // Fallback: usar valores del evento directamente, pero verificar primero
            let newLogoUrl: string | null = null
            if (url) {
              fetch(url, { method: 'HEAD', headers: getAuthHeaders() })
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
              const baseUrl = getApiBase()
              const logoPath = `${baseUrl}/api/v1/configuracion/logo/${filename}`
              fetch(logoPath, { method: 'HEAD', headers: getAuthHeaders() })
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
        // Recargar el logo con timestamp para evitar cachÃÂ©
        newLogoUrl = `${url}?t=${Date.now()}`
      } else if (filename) {
        // Si solo tenemos el filename, construir el path
        const baseUrl = getApiBase()
        const logoPath = `${baseUrl}/api/v1/configuracion/logo/${filename}`
        newLogoUrl = `${logoPath}?t=${Date.now()}`
      }

      if (newLogoUrl) {
        // Actualizar cache y notificar a todos los listeners
        devDebug('ÃÂ°ÃÂ¸Ã¢ÂÂÃ¢ÂÂ Actualizando logo (preview):', newLogoUrl)
        const logoFilename = filename || null
        logoCache.logoUrl = newLogoUrl
        logoCache.logoFilename = logoFilename // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar nombre del archivo
        logoCache.logoNotFound = false // ÃÂ¢ÃÂÃ¢ÂÂ¦ Resetear flag cuando se actualiza el logo
        logoCache.hasChecked = true
        logoCache.version += 1
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Guardar metadatos en localStorage si tenemos filename
        if (logoFilename) {
          saveLogoMetadata(logoFilename)
        }
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Actualizar estado local para mostrar logo directamente
        if (isMounted()) {
          setCustomLogoUrl(newLogoUrl)
          setLogoVersion(logoCache.version)
          // ÃÂ¢ÃÂÃ¢ÂÂ¦ Precargar el logo y mostrarlo directamente cuando estÃÂ© listo
          const img = new Image()
          img.onload = () => {
            if (isMounted()) {
              setImageLoaded(true) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Mostrar logo personalizado directamente
            }
          }
          img.onerror = () => {
            if (isMounted()) {
              setImageLoaded(false)
            }
          }
          img.src = newLogoUrl
          // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si hay logo anterior, mantenerlo visible hasta que el nuevo estÃÂ© listo
          if (customLogoUrl) {
            setImageLoaded(true)
          }
        }
        notifyLogoListeners(newLogoUrl, logoCache.version)
      }
    }

    window.addEventListener('logoUpdated', handleLogoUpdate as EventListener)

    return () => {
      clearTimeout(startId)
      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Cancelar peticiones en curso si el componente se desmonta
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

  // ÃÂ¢ÃÂÃ¢ÂÂ¦ PRIORIDAD: Si forceDefault estÃÂ¡ activado, siempre mostrar logo por defecto
  if (forceDefault) {
    // Continuar al renderizado del SVG por defecto
  }
  // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si el logo estÃÂ¡ marcado como no encontrado, NO renderizar <img> (evitar GET requests)
  // Si hay logo personalizado Y NO estÃÂ¡ marcado como no encontrado, mostrar imagen directamente
  // ÃÂ¢ÃÂÃ¢ÂÂ¦ CORRECCIÃÂN: Solo mostrar logo personalizado si realmente existe y estÃÂ¡ disponible Y no se fuerza el default
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
            // ÃÂ¢ÃÂÃ¢ÂÂ¦ Cuando la imagen se carga completamente, marcarla como cargada
            if (isMounted()) {
              setImageLoaded(true)
            }
          }}
          onError={(e) => {
            // ÃÂ¢ÃÂÃ¢ÂÂ¦ Si falla la carga (404 o imagen corrupta), marcar como no encontrado y limpiar cachÃÂ©
            devWarn('Error cargando logo (GET fallÃÂ³ o imagen invÃÂ¡lida), limpiando cachÃÂ©:', customLogoUrl)
            logoCache.logoNotFound = true
            logoCache.logoUrl = null
            logoCache.logoFilename = null
            logoCache.version += 1
            // ÃÂ¢ÃÂÃ¢ÂÂ¦ Limpiar metadatos del localStorage
            saveLogoMetadata(null)
            setCustomLogoUrl(null)
            setHasChecked(true)
            setImageLoaded(false)
            setLogoVersion(logoCache.version)
            notifyLogoListeners(null, logoCache.version) // ÃÂ¢ÃÂÃ¢ÂÂ¦ Notificar a todas las instancias
            // No intentar recargar - el logo no existe o estÃÂ¡ corrupto
          }}
        />
      </div>
    )
  }

  // Si ya verificamos y no hay logo personalizado: imagen rAPI.png o fallback SVG si falla la carga
  if (defaultLogoFailed) {
    return (
      <svg
        className={cn(sizeMap[size], className)}
        viewBox="0 0 48 48"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="RAPICREDIT Logo"
      >
        <rect width="48" height="48" rx="8" fill="#1e40af" />
        <text x="24" y="32" textAnchor="middle" fill="white" fontSize="20" fontWeight="bold" fontFamily="system-ui">R</text>
        <circle cx="38" cy="38" r="6" fill="#f59e0b" />
      </svg>
    )
  }
  return (
    <img
      src={DEFAULT_LOGO_SRC}
      alt="RAPICREDIT Logo"
      className={cn(sizeMap[size], className, 'object-contain')}
      role="img"
      loading="eager"
      onError={() => {
        if (isMounted()) setDefaultLogoFailed(true)
      }}
    />
  )
}

