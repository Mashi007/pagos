// frontend/src/config/env.ts
// Validacion y centralizacion de variables de entorno (evita errores en runtime).

const DEFAULT_APP_NAME = 'Sistema de Prestamos y Cobranza'
const DEFAULT_APP_VERSION = '1.0.0'

/**
 * Base path de la app (ej. /pagos para https://rapicredit.onrender.com/pagos).
 * Emparejamiento con basename:
 * - Vite (vite.config.ts): base: '/pagos/' -> import.meta.env.BASE_URL = '/pagos/'
 * - Aqui: BASE_PATH = '/pagos' (sin barra final)
 * - main.tsx: <BrowserRouter basename={BASE_PATH || '/'}>
 * - server.js: FRONTEND_BASE = '/pagos'
 * - App.tsx: rutas publicas por pathname relativo al basename: '/', cobros, estado cuenta, '/login'
 */
function getBasePath(): string {
  const fromVite = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') || ''

  if (fromVite) return fromVite

  if (
    typeof window !== 'undefined' &&
    window.location.pathname.startsWith('/pagos')
  )
    return '/pagos'

  return '/'
}

export const BASE_PATH = getBasePath()

/** Path del formulario publico de reporte de pago (cobros). Link canonico: /rapicredit-cobros */
export const PUBLIC_REPORTE_PAGO_PATH = 'rapicredit-cobros'

/**
 * Clave de sessionStorage: usuario en flujo publico (cobros o estado de cuenta).
 * Si intenta ir a /login, se muestra acceso prohibido y boton Continuar.
 */
export const PUBLIC_FLOW_SESSION_KEY = 'public_flow_active'

/** Sufijo de URL para mostrar siempre el formulario de personal (evita pantalla Acceso limitado). */
export const STAFF_LOGIN_SEARCH = '?personal=1'

/** Sesion del formulario publico rapicredit-cobros tras verificar codigo por correo. */
export const COBROS_PUBLIC_TOKEN_KEY = 'cobros_public_jwt'

export const COBROS_PUBLIC_CEDULA_KEY = 'cobros_public_cedula'

interface EnvConfig {
  API_URL: string
  NODE_ENV: string
  APP_NAME: string
  APP_VERSION: string
}

function validateEnv(): EnvConfig {
  const NODE_ENV = import.meta.env.VITE_NODE_ENV || import.meta.env.MODE

  const APP_NAME = import.meta.env.VITE_APP_NAME || DEFAULT_APP_NAME

  const APP_VERSION = import.meta.env.VITE_APP_VERSION || DEFAULT_APP_VERSION

  // Produccion: rutas relativas (proxy en server.js maneja /api/*; en Render use API_BASE_URL o BACKEND_URL en Node).
  // Desarrollo: URL absoluta opcional con VITE_API_URL.
  let API_URL = import.meta.env.VITE_API_URL || ''

  if (import.meta.env.PROD || NODE_ENV === 'production') {
    const prodApiUrl = (import.meta.env.VITE_API_URL || '').trim()

    if (prodApiUrl) {
      try {
        new URL(prodApiUrl)

        API_URL = prodApiUrl.replace(/\/$/, '')
      } catch {
        API_URL = ''
      }
    } else {
      API_URL = ''
    }
  } else {
    if (API_URL) {
      try {
        new URL(API_URL)
      } catch {
        console.warn(
          `[env] VITE_API_URL tiene formato invalido: ${API_URL}. Usando rutas relativas.`
        )

        API_URL = ''
      }
    } else {
      console.warn(
        '[env] VITE_API_URL no configurada. Usando rutas relativas en desarrollo.'
      )
    }
  }

  return {
    API_URL,
    NODE_ENV,
    APP_NAME,
    APP_VERSION,
  }
}

export const env = validateEnv()

export const isDevelopment = env.NODE_ENV === 'development'

export const isProduction = env.NODE_ENV === 'production'
