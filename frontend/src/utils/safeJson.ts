// frontend/src/utils/safeJson.ts
/**
 * Utilidades para manejo seguro de JSON
 * Previene errores de SyntaxError al parsear datos corruptos
 */

export function safeJsonParse<T = any>(data: string | null | undefined, fallback: T | null = null): T | null {
  if (!data) {
    return fallback;
  }

  // Verificar si es un string válido
  if (typeof data !== 'string') {
    console.warn('safeJsonParse: data no es un string:', typeof data, data);
    return fallback;
  }

  // Verificar valores problemáticos
  const trimmedData = data.trim();
  if (trimmedData === '' || trimmedData === 'undefined' || trimmedData === 'null') {
    console.warn('safeJsonParse: datos inválidos:', trimmedData);
    return fallback;
  }

  try {
    const parsed = JSON.parse(data);
    return parsed;
  } catch (error) {
    console.error('safeJsonParse: Error al parsear JSON:', {
      error: error instanceof Error ? error.message : error,
      data: data,
      dataLength: data.length,
      dataPreview: data.substring(0, 100)
    });
    return fallback;
  }
}

export function safeJsonStringify<T = any>(data: T, fallback: string = '{}'): string {
  try {
    return JSON.stringify(data);
  } catch (error) {
    console.error('safeJsonStringify: Error al serializar:', error);
    return fallback;
  }
}

// Helper específico para datos de usuario
export function safeParseUserData(data: string | null | undefined) {
  return safeJsonParse(data, null);
}

// Helper específico para tokens
export function safeParseTokenData(data: string | null | undefined) {
  return safeJsonParse(data, null);
}
