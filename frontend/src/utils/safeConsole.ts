/**





 * Wrapper seguro para migración gradual de console.log





 * Permite mantener compatibilidad mientras se migra a logger estructurado





 */

import { logger } from './logger'

// Mantener console original como fallback

const originalConsole = {
  log: console.log,

  error: console.error,

  warn: console.warn,

  info: console.info,

  debug: console.debug,
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
  },
}

// Función para migrar un archivo específico de forma segura

export const migrateFileToLogger = (filePath: string) => {
  console.log(`🔄 Migrando ${filePath} a logger estructurado...`)

  // Esta función se puede usar para migrar archivos específicos

  // Por ahora solo registra la intención

  logger.info(`Migration planned for ${filePath}`, {
    action: 'migration_planned',

    file: filePath,

    timestamp: new Date().toISOString(),
  })
}

// Función para verificar si el logger está funcionando correctamente

export const testLogger = () => {
  try {
    logger.info('Logger test successful', {
      test: true,

      timestamp: new Date().toISOString(),
    })

    return true
  } catch (error) {
    console.error('Logger test failed:', error)

    return false
  }
}

export default safeConsole
