/**
 * Wrapper seguro para migraciÃÂ³n gradual de console.log
 * Permite mantener compatibilidad mientras se migra a logger estructurado
 */

import { logger } from './logger'

// Mantener console original como fallback
const originalConsole = {
  log: console.log,
  error: console.error,
  warn: console.warn,
  info: console.info,
  debug: console.debug
}

// Wrapper que usa logger estructurado pero mantiene compatibilidad
export const safeConsole = {
  log: (message: string, ...args: any[]) => {
    try {
      logger.info(message, { args: args.length > 0 ? args : undefined })
    } catch (error) {
      // Fallback a console original si hay error
      originalConsole.log(message, ...args)
    }
  },

  error: (message: string, ...args: any[]) => {
    try {
      logger.error(message, { args: args.length > 0 ? args : undefined })
    } catch (error) {
      originalConsole.error(message, ...args)
    }
  },

  warn: (message: string, ...args: any[]) => {
    try {
      logger.warn(message, { args: args.length > 0 ? args : undefined })
    } catch (error) {
      originalConsole.warn(message, ...args)
    }
  },

  info: (message: string, ...args: any[]) => {
    try {
      logger.info(message, { args: args.length > 0 ? args : undefined })
    } catch (error) {
      originalConsole.info(message, ...args)
    }
  },

  debug: (message: string, ...args: any[]) => {
    try {
      logger.debug(message, { args: args.length > 0 ? args : undefined })
    } catch (error) {
      originalConsole.debug(message, ...args)
    }
  }
}

// FunciÃÂ³n para migrar un archivo especÃÂ­fico de forma segura
export const migrateFileToLogger = (filePath: string) => {
  console.log(`Ã°ÂÂÂ Migrando ${filePath} a logger estructurado...`)

  // Esta funciÃÂ³n se puede usar para migrar archivos especÃÂ­ficos
  // Por ahora solo registra la intenciÃÂ³n
  logger.info(`Migration planned for ${filePath}`, {
    action: 'migration_planned',
    file: filePath,
    timestamp: new Date().toISOString()
  })
}

// FunciÃÂ³n para verificar si el logger estÃÂ¡ funcionando correctamente
export const testLogger = () => {
  try {
    logger.info('Logger test successful', {
      test: true,
      timestamp: new Date().toISOString()
    })
    return true
  } catch (error) {
    console.error('Logger test failed:', error)
    return false
  }
}

export default safeConsole
