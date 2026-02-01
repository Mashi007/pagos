/**
 * Configuración de la API
 */
const API_URL = import.meta.env.VITE_API_URL;

// Validar URL
if (!API_URL) {
  console.warn('⚠️ VITE_API_URL no está configurada, usando localhost');
}

if (API_URL && !API_URL.match(/^https?:\/\//)) {
  throw new Error('VITE_API_URL debe ser una URL válida (http:// o https://)');
}

const API_CONFIG = {
  baseURL: API_URL || 'http://localhost:8000',
  timeout: 30000, // 30 segundos
  retries: 3,
  retryDelay: 1000, // 1 segundo
};

export default API_CONFIG;
