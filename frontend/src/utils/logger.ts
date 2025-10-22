/**
 * Logger estructurado para el frontend
 * Implementación simple sin dependencias externas para evitar problemas de build
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface LogEntry {
  level: LogLevel
  message: string
  timestamp: string
  data?: Record<string, any>
  userId?: string
  action?: string
  component?: string
}

class Logger {
  private isDevelopment = process.env.NODE_ENV === 'development'
  private isProduction = process.env.NODE_ENV === 'production'

  private formatLog(level: LogLevel, message: string, data?: Record<string, any>): LogEntry {
    return {
      level,
      message,
      timestamp: new Date().toISOString(),
      data,
      component: this.getComponentName()
    }
  }

  private getComponentName(): string {
    // Obtener el nombre del componente desde el stack trace
    try {
      const stack = new Error().stack
      if (stack) {
        const lines = stack.split('\n')
        const componentLine = lines[3] || lines[2] || 'unknown'
        const match = componentLine.match(/(\w+)\.tsx?/)
        return match ? match[1] : 'unknown'
      }
    } catch (error) {
      // Ignorar errores al obtener el nombre del componente
    }
    return 'unknown'
  }

  private shouldLog(level: LogLevel): boolean {
    if (this.isDevelopment) {
      return true // En desarrollo, logear todo
    }
    
    if (this.isProduction) {
      // En producción, solo logear warn y error
      return level === 'warn' || level === 'error'
    }
    
    return true
  }

  private output(entry: LogEntry): void {
    if (!this.shouldLog(entry.level)) {
      return
    }

    // En desarrollo, usar console con colores
    if (this.isDevelopment) {
      const colors = {
        debug: '\x1b[36m', // Cyan
        info: '\x1b[32m',  // Green
        warn: '\x1b[33m',  // Yellow
        error: '\x1b[31m', // Red
        reset: '\x1b[0m'   // Reset
      }
      
      console.log(
        `${colors[entry.level]}[${entry.level.toUpperCase()}]${colors.reset} ` +
        `${entry.timestamp} [${entry.component}] ${entry.message}`,
        entry.data || ''
      )
    } else {
      // En producción, usar console estándar para compatibilidad
      const method = entry.level === 'error' ? 'error' : 
                    entry.level === 'warn' ? 'warn' : 'log'
      
      console[method](JSON.stringify(entry))
    }
  }

  debug(message: string, data?: Record<string, any>): void {
    this.output(this.formatLog('debug', message, data))
  }

  info(message: string, data?: Record<string, any>): void {
    this.output(this.formatLog('info', message, data))
  }

  warn(message: string, data?: Record<string, any>): void {
    this.output(this.formatLog('warn', message, data))
  }

  error(message: string, data?: Record<string, any>): void {
    this.output(this.formatLog('error', message, data))
  }

  // Método para logging de acciones de usuario
  userAction(action: string, data?: Record<string, any>): void {
    this.info(`User action: ${action}`, {
      ...data,
      action,
      userId: data?.userId || 'anonymous'
    })
  }

  // Método para logging de errores de API
  apiError(endpoint: string, error: any, data?: Record<string, any>): void {
    this.error(`API Error: ${endpoint}`, {
      ...data,
      endpoint,
      error: error?.message || error,
      status: error?.status || error?.response?.status,
      stack: error?.stack
    })
  }

  // Método para logging de performance
  performance(operation: string, duration: number, data?: Record<string, any>): void {
    this.info(`Performance: ${operation}`, {
      ...data,
      operation,
      duration,
      durationMs: duration
    })
  }
}

// Exportar instancia singleton
export const logger = new Logger()

// Exportar también la clase para testing
export { Logger }

// Función helper para migrar console.log existentes
export const migrateConsoleLog = (originalLog: any, message: string, ...args: any[]) => {
  if (typeof message === 'string') {
    logger.info(message, { args: args.length > 0 ? args : undefined })
  } else {
    logger.info('Console log', { data: message, args: args.length > 0 ? args : undefined })
  }
}

export default logger
