// frontend/src/config/env.ts
/**
 * ValidaciÃ³n y centralizaciÃ³n de variables de entorno
 * Previene errores de configuraciÃ³n en runtime
 */

// Constantes de configuraciÃ³n
const DEFAULT_APP_NAME = "Sistema de PrÃ©stamos y Cobranza"
const DEFAULT_APP_VERSION = "1.0.0"

/**
 * Base path de la app (ej. /pagos para https://rapicredit.onrender.com/pagos).
 * Emparejamiento con basename:
 * - Vite (vite.config.ts): base: '/pagos/' â import.meta.env.BASE_URL = '/pagos/'
 * - AquÃ­: BASE_PATH = '/pagos' (sin barra final)
 * - main.tsx: <BrowserRouter basename={BASE_PATH || '/'}> â Router usa /pagos
 * - server.js: FRONTEND_BASE = '/pagos' (estÃ¡ticos y SPA fallback)
 * - App.tsx: rutas pÃºblicas por pathname relativo al basename: '/' y '/login'
 * Fallback: si la URL es /pagos/chat-ai (o cualquier /pagos/*), usar /pagos aunque BASE_URL falle en build.
 */
function getBasePath(): string {
  const fromVite = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') || '';
  if (fromVite) return fromVite;
  if (typeof window !== 'undefined' && window.location.pathname.startsWith('/pagos')) return '/pagos';
  return '/';
}
export const BASE_PATH = getBasePath();

/** Path del formulario pÃºblico de reporte de pago (cobros). Link canÃ³nico: /rapicredit-cobros */
export const PUBLIC_REPORTE_PAGO_PATH = 'rapicredit-cobros';

/**
 * Clave de sessionStorage que indica que el usuario estÃ¡ en un flujo pÃºblico (cobros o estado de cuenta).
 * Si intenta ir a /login, se muestra "Acceso prohibido" y botÃ³n Continuar para volver al flujo.
 */
export const PUBLIC_FLOW_SESSION_KEY = 'public_flow_active';

interface EnvConfig {
  API_URL: string;
  NODE_ENV: string;
  APP_NAME: string;
  APP_VERSION: string;
}

function validateEnv(): EnvConfig {
  const NODE_ENV = import.meta.env.VITE_NODE_ENV || import.meta.env.MODE;
  const APP_NAME = import.meta.env.VITE_APP_NAME || DEFAULT_APP_NAME;
  const APP_VERSION = import.meta.env.VITE_APP_VERSION || DEFAULT_APP_VERSION;

  // â PRODUCCIÃN: Usar rutas relativas (el proxy en server.js maneja /api/*)
  // â DESARROLLO: Usar URL absoluta si estÃ¡ configurada
  let API_URL = import.meta.env.VITE_API_URL || '';

  if (import.meta.env.PROD || NODE_ENV === 'production') {
    // Mismo servicio (proxy): rutas relativas. Servicios distintos (ej. Render): usar VITE_API_URL si está definida (CSP permite ambos orígenes).
    const prodApiUrl = (import.meta.env.VITE_API_URL || '').trim();
    if (prodApiUrl) {
      try {
        new URL(prodApiUrl);
        API_URL = prodApiUrl.replace(/\/$/, '');
      } catch {
        API_URL = '';
      }
    } else {
      API_URL = '';
    }
  } else {
    // En desarrollo, validar URL si estÃ¡ configurada
    if (API_URL) {
      try {
        new URL(API_URL);
      } catch {
        console.warn(`â ï¸ VITE_API_URL tiene formato invÃ¡lido: ${API_URL}. Usando rutas relativas.`);
        API_URL = '';
      }
    } else {
      console.warn('â ï¸ VITE_API_URL no configurada. Usando rutas relativas en desarrollo.');
    }
  }

  return {
    API_URL,
    NODE_ENV,
    APP_NAME,
    APP_VERSION,
  };
}

// Validar al importar
export const env = validateEnv();

// Helper para determinar ambiente
export const isDevelopment = env.NODE_ENV === 'development';
export const isProduction = env.NODE_ENV === 'production';

