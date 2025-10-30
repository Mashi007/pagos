// frontend/src/config/env.ts
/**
 * Validación y centralización de variables de entorno
 * Previene errores de configuración en runtime
 */

// Constantes de configuración
const DEFAULT_APP_NAME = "Sistema de Préstamos y Cobranza"
const DEFAULT_APP_VERSION = "1.0.0"

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
  
  // ✅ PRODUCCIÓN: Usar rutas relativas (el proxy en server.js maneja /api/*)
  // ✅ DESARROLLO: Usar URL absoluta si está configurada
  let API_URL = import.meta.env.VITE_API_URL || '';
  
  if (NODE_ENV === 'production') {
    // En producción, usar rutas relativas para que el proxy funcione
    API_URL = '';
  } else {
    // En desarrollo, validar URL si está configurada
    if (API_URL) {
      try {
        new URL(API_URL);
      } catch {
        console.warn(`⚠️ VITE_API_URL tiene formato inválido: ${API_URL}. Usando rutas relativas.`);
        API_URL = '';
      }
    } else {
      console.warn('⚠️ VITE_API_URL no configurada. Usando rutas relativas en desarrollo.');
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

