// frontend/src/config/env.ts
/**
 * Validación y centralización de variables de entorno
 * Previene errores de configuración en runtime
 */

interface EnvConfig {
  API_URL: string;
  NODE_ENV: string;
  APP_NAME: string;
  APP_VERSION: string;
}

function validateEnv(): EnvConfig {
  const API_URL = import.meta.env.VITE_API_URL;
  const NODE_ENV = import.meta.env.VITE_NODE_ENV || import.meta.env.MODE;
  const APP_NAME = import.meta.env.VITE_APP_NAME || "Sistema de Préstamos y Cobranza";
  const APP_VERSION = import.meta.env.VITE_APP_VERSION || "1.0.0";

  // Validar variables críticas
  if (!API_URL) {
    throw new Error(
      '❌ CRÍTICO: Variable VITE_API_URL no configurada. ' +
      'Configure en archivo .env o variables de entorno.'
    );
  }

  // Validar formato de URL
  try {
    new URL(API_URL);
  } catch {
    throw new Error(
      `❌ CRÍTICO: VITE_API_URL tiene formato inválido: ${API_URL}`
    );
  }

  // Advertir si está en producción sin HTTPS
  if (NODE_ENV === 'production' && !API_URL.startsWith('https://')) {
    console.warn(
      '⚠️ ADVERTENCIA: API_URL en producción no usa HTTPS:',
      API_URL
    );
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

