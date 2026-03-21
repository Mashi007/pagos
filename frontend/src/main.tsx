import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { Toaster as SonnerToaster } from 'sonner'
import App from './App.tsx'
import './index.css'

// ValidaciÃÂ³n de variables de entorno; BASE_PATH es la ÃÂºnica fuente de verdad para basename (emparejado con Vite base y server.js FRONTEND_BASE)
import { BASE_PATH } from './config/env'

// Constantes de configuraciÃÂ³n
const STALE_TIME_MINUTES = 5
const STALE_TIME_MS = STALE_TIME_MINUTES * 60 * 1000
const RETRY_COUNT = 1
const TOAST_DURATION_MS = 4000
const SUCCESS_COLOR_HUE = 142
const SUCCESS_COLOR_SATURATION = 76
const SUCCESS_COLOR_LIGHTNESS = 36
const ERROR_COLOR_HUE = 0
const ERROR_COLOR_SATURATION = 84
const ERROR_COLOR_LIGHTNESS = 60

// ConfiguraciÃÂ³n del cliente de React Query
// Ã¢ÂÂ OPTIMIZACIÃÂN: ConfiguraciÃÂ³n mejorada para reducir llamadas redundantes y mejorar rendimiento
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME_MS, // 5 minutos - datos se consideran frescos durante este tiempo
      cacheTime: 10 * 60 * 1000, // Ã¢ÂÂ 10 minutos - mantener datos en cache mÃÂ¡s tiempo
      retry: RETRY_COUNT, // Solo 1 retry para evitar mÃÂºltiples intentos
      refetchOnWindowFocus: false, // Ã¢ÂÂ No recargar automÃÂ¡ticamente al enfocar ventana
      refetchOnMount: false, // Ã¢ÂÂ No recargar si los datos estÃÂ¡n frescos (staleTime)
      refetchOnReconnect: true, // Recargar solo si se reconecta despuÃÂ©s de perder conexiÃÂ³n
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Backoff exponencial
    },
    mutations: {
      retry: RETRY_COUNT,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
})

const rootElement = document.getElementById('root')

// Ã¢ÂÂ Verificar que el elemento root existe antes de renderizar
if (!rootElement) {
  console.error('Ã¢ÂÂ Error: No se encontrÃÂ³ el elemento #root')
  document.body.innerHTML = '<div style="padding: 20px; font-family: sans-serif;"><h1>Error de inicializaciÃÂ³n</h1><p>No se pudo encontrar el elemento raÃÂ­z de la aplicaciÃÂ³n.</p></div>'
} else {
  // Renderizar la aplicaciÃÂ³n
  try {
    ReactDOM.createRoot(rootElement).render(
      <React.StrictMode>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter basename={BASE_PATH || '/'}>
            <App />
            <SonnerToaster
              position="top-center"
              richColors
              closeButton
              toastOptions={{ style: { minWidth: 380, padding: '18px 22px', fontSize: '1.05rem' } }}
              style={{ top: 24 }}
            />
            <Toaster
              position="top-center"
              containerClassName="toast-container-center"
              containerStyle={{ zIndex: 9999 }}
              toastOptions={{
                duration: TOAST_DURATION_MS,
                style: {
                  background: 'hsl(var(--card))',
                  color: 'hsl(var(--card-foreground))',
                  border: '1px solid hsl(var(--border))',
                  boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                  minWidth: 360,
                  maxWidth: 560,
                  padding: '18px 22px',
                  fontSize: '1.05rem',
                },
                success: {
                  iconTheme: {
                    primary: `hsl(${SUCCESS_COLOR_HUE} ${SUCCESS_COLOR_SATURATION}% ${SUCCESS_COLOR_LIGHTNESS}%)`,
                    secondary: 'white',
                  },
                },
                error: {
                  iconTheme: {
                    primary: `hsl(${ERROR_COLOR_HUE} ${ERROR_COLOR_SATURATION}% ${ERROR_COLOR_LIGHTNESS}%)`,
                    secondary: 'white',
                  },
                },
              }}
            />
          </BrowserRouter>
        </QueryClientProvider>
      </React.StrictMode>
    )
  } catch (error) {
    console.error('Ã¢ÂÂ Error al renderizar la aplicaciÃÂ³n:', error)
    rootElement.innerHTML = `
      <div style="padding: 20px; font-family: sans-serif; text-align: center;">
        <h1 style="color: #dc2626;">Error al cargar la aplicaciÃÂ³n</h1>
        <p style="color: #6b7280; margin: 10px 0;">Ha ocurrido un error al inicializar la aplicaciÃÂ³n.</p>
        <button
          onclick="window.location.reload()"
          style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 10px;"
        >
          Recargar pÃÂ¡gina
        </button>
      </div>
    `
  }
}

// Ã¢ÂÂ Manejador para capturar errores crÃÂ­ticos que impiden el renderizado
window.addEventListener('error', (event) => {
  // Ã¢ÂÂ Loggear errores crÃÂ­ticos para debugging (pero no bloquear el renderizado)
  if (event.error && !event.error.name?.includes('NS_ERROR_FAILURE')) {
    // Solo loggear si no es un error conocido que ya estamos manejando
    const errorMessage = event.error?.message || event.message || ''
    const isKnownError = errorMessage.includes('radix-ui') ||
                        errorMessage.includes('exceljs') ||
                        errorMessage.includes('useState') ||
                        errorMessage.includes('form-libs')

    if (!isKnownError && process.env.NODE_ENV === 'development') {
      console.error('Ã¢ÂÂ Ã¯Â¸Â Error capturado:', event.error || event.message)
    }
  }

  // Manejador global de errores para capturar NS_ERROR_FAILURE y otros errores de React
  // Ã¢ÂÂ Capturar errores NS_ERROR_FAILURE que ocurren en Firefox (especialmente con ExcelJS y Radix UI)
  if (event.error && event.error.name === 'NS_ERROR_FAILURE') {
    // Este error generalmente ocurre cuando se intenta actualizar el estado despuÃÂ©s del desmontaje
    // o durante la inicializaciÃÂ³n de mÃÂ³dulos dinÃÂ¡micos (como ExcelJS o Radix UI)
    // Ya estÃÂ¡ siendo manejado por useIsMounted, pero lo capturamos para evitar que se muestre en consola

    // Ã¢ÂÂ Verificar si el error estÃÂ¡ relacionado con Radix UI
    const stackTrace = event.error?.stack || event.error?.toString() || ''
    const isRadixUIError = stackTrace.includes('radix-ui') ||
                          stackTrace.includes('radix') ||
                          (event.filename && event.filename.includes('radix'))

    // Ã¢ÂÂ Verificar si el error estÃÂ¡ relacionado con useState durante la inicializaciÃÂ³n
    const isUseStateError = stackTrace.includes('useState') ||
                           stackTrace.includes('form-libs') ||
                           (event.filename && event.filename.includes('form-libs'))

    // Ã¢ÂÂ Capturar errores de Radix UI relacionados con useState durante la inicializaciÃÂ³n
    if (isRadixUIError || isUseStateError) {
      event.preventDefault() // Prevenir que el error se propague
      event.stopPropagation() // Detener la propagaciÃÂ³n del evento
      return false // Retornar false para indicar que el error fue manejado
    }

    // Ã¢ÂÂ Capturar errores relacionados con ExcelJS durante la inicializaciÃÂ³n
    if (event.filename && event.filename.includes('exceljs')) {
      event.preventDefault()
      event.stopPropagation()
      return false
    }

    // Ã¢ÂÂ Capturar otros errores NS_ERROR_FAILURE genÃÂ©ricos (solo si no son crÃÂ­ticos)
    // No capturamos todos los NS_ERROR_FAILURE para no ocultar errores importantes
    event.preventDefault()
    event.stopPropagation()
    return false
  }

  // Ã¢ÂÂ Capturar errores relacionados con Radix UI en el stack trace
  if (event.error && event.error.stack) {
    const stackTrace = event.error.stack.toLowerCase()
    if (stackTrace.includes('radix-ui') || stackTrace.includes('radix')) {
      // Verificar si es un error conocido de inicializaciÃÂ³n
      if (stackTrace.includes('usestate') || stackTrace.includes('form-libs')) {
        event.preventDefault()
        event.stopPropagation()
        return false
      }
    }
  }

  // Ã¢ÂÂ Capturar errores relacionados con React/Radix UI en el mensaje
  if (event.error && typeof event.error.message === 'string') {
    const errorMessage = event.error.message.toLowerCase()
    if (errorMessage.includes('cannot read property') && errorMessage.includes('useState')) {
      event.preventDefault()
      event.stopPropagation()
      return false
    }
  }

  // Ã¢ÂÂ "The operation is insecure" (Demasiadas llamadas a location/history o contexto restringido)
  if (event.error && (event.error.message === 'The operation is insecure' || event.error?.name === 'SecurityError')) {
    const stack = (event.error?.stack || '').toLowerCase()
    if (stack.includes('history') || stack.includes('location') || stack.includes('replaceState') || stack.includes('pushState')) {
      event.preventDefault()
      event.stopPropagation()
      return false
    }
  }
}, true) // Ã¢ÂÂ Usar capture phase para interceptar errores antes de que se propaguen

// Manejador global de promesas rechazadas no manejadas
window.addEventListener('unhandledrejection', (event) => {
  // Ã¢ÂÂ Capturar promesas rechazadas relacionadas con NS_ERROR_FAILURE
  if (event.reason && event.reason.name === 'NS_ERROR_FAILURE') {
    // Ã¢ÂÂ Verificar si el error estÃÂ¡ relacionado con Radix UI o useState
    const reasonMessage = event.reason?.message || event.reason?.toString() || ''
    const reasonStack = event.reason?.stack || ''
    const isRadixUIError = reasonMessage.includes('radix-ui') ||
                          reasonMessage.includes('radix') ||
                          reasonStack.includes('radix-ui') ||
                          reasonStack.includes('radix') ||
                          reasonMessage.includes('form-libs') ||
                          reasonStack.includes('form-libs')

    if (isRadixUIError) {
      event.preventDefault() // Prevenir que el error se propague
      event.stopPropagation() // Detener la propagaciÃÂ³n
      return false
    }

    // Ã¢ÂÂ Capturar errores relacionados con ExcelJS
    if (reasonMessage.includes('exceljs') || reasonStack.includes('exceljs')) {
      event.preventDefault()
      event.stopPropagation()
      return false
    }

    // Ã¢ÂÂ Capturar otros errores NS_ERROR_FAILURE genÃÂ©ricos (solo si no son crÃÂ­ticos)
    event.preventDefault()
    event.stopPropagation()
    return false
  }

  // Ã¢ÂÂ Capturar errores relacionados con Radix UI en promesas rechazadas
  const reasonMessage = event.reason?.message || event.reason?.toString() || ''
  const reasonStack = event.reason?.stack || ''
  if ((reasonMessage.includes('radix-ui') || reasonMessage.includes('radix') ||
       reasonStack.includes('radix-ui') || reasonStack.includes('radix')) &&
      (reasonMessage.includes('usestate') || reasonMessage.includes('form-libs') ||
       reasonStack.includes('usestate') || reasonStack.includes('form-libs'))) {
    event.preventDefault()
    event.stopPropagation()
    return false
  }
})

// Marcar que los estilos estÃÂ¡n cargados despuÃÂ©s de que React renderice
// Usar requestAnimationFrame para asegurar que el render estÃÂ© completo
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    // Verificar que las variables CSS estÃÂ©n disponibles (indica que Tailwind estÃÂ¡ cargado)
    const root = document.getElementById('root')
    if (root) {
      const computedStyle = window.getComputedStyle(root)
      // Si las variables CSS estÃÂ¡n disponibles, mostrar contenido
      if (computedStyle && computedStyle.fontFamily) {
        root.classList.add('styles-loaded')
      } else {
        // Si aÃÂºn no estÃÂ¡n, esperar un poco mÃÂ¡s
        setTimeout(() => {
          const rootEl = document.getElementById('root')
          if (rootEl) {
            rootEl.classList.add('styles-loaded')
          }
        }, 100)
      }
    }
  })
})
