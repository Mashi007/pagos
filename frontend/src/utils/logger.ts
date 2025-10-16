// frontend/src/utils/logger.ts
/**
 * Logger utility para manejo seguro de logs
 * En producción, los console.log son eliminados
 */

const isDevelopment = import.meta.env.MODE === 'development';

export const logger = {
  log: (...args: any[]) => {
    if (isDevelopment) {
      console.log(...args);
    }
  },
  
  error: (...args: any[]) => {
    if (isDevelopment) {
      console.error(...args);
    } else {
      // En producción, enviar a servicio de logging (ej: Sentry)
      // Aquí podrías integrar con Sentry, LogRocket, etc.
    }
  },
  
  warn: (...args: any[]) => {
    if (isDevelopment) {
      console.warn(...args);
    }
  },
  
  info: (...args: any[]) => {
    if (isDevelopment) {
      console.info(...args);
    }
  }
};

