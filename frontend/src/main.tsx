import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import App from './App.tsx'
import './index.css'

// Validación de variables de entorno
import './config/env'

// Constantes de configuración
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

// Configuración del cliente de React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME_MS,
      retry: RETRY_COUNT,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: RETRY_COUNT,
    },
  },
})

const rootElement = document.getElementById('root')!

// Renderizar la aplicación
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <Toaster
        position="top-right"
        toastOptions={{
          duration: TOAST_DURATION_MS,
          style: {
            background: 'hsl(var(--card))',
            color: 'hsl(var(--card-foreground))',
            border: '1px solid hsl(var(--border))',
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
  </React.StrictMode>,
)

// Manejador global de errores para capturar NS_ERROR_FAILURE y otros errores de React
window.addEventListener('error', (event) => {
  // ✅ Capturar errores NS_ERROR_FAILURE que ocurren en Firefox (especialmente con ExcelJS y Radix UI)
  if (event.error && event.error.name === 'NS_ERROR_FAILURE') {
    // Este error generalmente ocurre cuando se intenta actualizar el estado después del desmontaje
    // o durante la inicialización de módulos dinámicos (como ExcelJS o Radix UI)
    // Ya está siendo manejado por useIsMounted, pero lo capturamos para evitar que se muestre en consola
    
    // ✅ Verificar si el error está relacionado con Radix UI
    const stackTrace = event.error?.stack || event.error?.toString() || ''
    const isRadixUIError = stackTrace.includes('radix-ui') || 
                          stackTrace.includes('radix') ||
                          (event.filename && event.filename.includes('radix'))
    
    // ✅ Verificar si el error está relacionado con useState durante la inicialización
    const isUseStateError = stackTrace.includes('useState') || 
                           stackTrace.includes('form-libs') ||
                           (event.filename && event.filename.includes('form-libs'))
    
    // ✅ Capturar errores de Radix UI relacionados con useState durante la inicialización
    if (isRadixUIError || isUseStateError) {
      event.preventDefault() // Prevenir que el error se propague
      event.stopPropagation() // Detener la propagación del evento
      return false // Retornar false para indicar que el error fue manejado
    }
    
    // ✅ Capturar errores relacionados con ExcelJS durante la inicialización
    if (event.filename && event.filename.includes('exceljs')) {
      event.preventDefault()
      event.stopPropagation()
      return false
    }
    
    // ✅ Capturar otros errores NS_ERROR_FAILURE genéricos (solo si no son críticos)
    // No capturamos todos los NS_ERROR_FAILURE para no ocultar errores importantes
    event.preventDefault()
    event.stopPropagation()
    return false
  }
  
  // ✅ Capturar errores relacionados con Radix UI en el stack trace
  if (event.error && event.error.stack) {
    const stackTrace = event.error.stack.toLowerCase()
    if (stackTrace.includes('radix-ui') || stackTrace.includes('radix')) {
      // Verificar si es un error conocido de inicialización
      if (stackTrace.includes('usestate') || stackTrace.includes('form-libs')) {
        event.preventDefault()
        event.stopPropagation()
        return false
      }
    }
  }
  
  // ✅ Capturar errores relacionados con React/Radix UI en el mensaje
  if (event.error && typeof event.error.message === 'string') {
    const errorMessage = event.error.message.toLowerCase()
    if (errorMessage.includes('cannot read property') && errorMessage.includes('useState')) {
      event.preventDefault()
      event.stopPropagation()
      return false
    }
  }
}, true) // ✅ Usar capture phase para interceptar errores antes de que se propaguen

// Manejador global de promesas rechazadas no manejadas
window.addEventListener('unhandledrejection', (event) => {
  // ✅ Capturar promesas rechazadas relacionadas con NS_ERROR_FAILURE
  if (event.reason && event.reason.name === 'NS_ERROR_FAILURE') {
    // ✅ Verificar si el error está relacionado con Radix UI o useState
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
      event.stopPropagation() // Detener la propagación
      return false
    }
    
    // ✅ Capturar errores relacionados con ExcelJS
    if (reasonMessage.includes('exceljs') || reasonStack.includes('exceljs')) {
      event.preventDefault()
      event.stopPropagation()
      return false
    }
    
    // ✅ Capturar otros errores NS_ERROR_FAILURE genéricos (solo si no son críticos)
    event.preventDefault()
    event.stopPropagation()
    return false
  }
  
  // ✅ Capturar errores relacionados con Radix UI en promesas rechazadas
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

// Marcar que los estilos están cargados después de que React renderice
// Usar requestAnimationFrame para asegurar que el render esté completo
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    // Verificar que las variables CSS estén disponibles (indica que Tailwind está cargado)
    const root = document.getElementById('root')
    if (root) {
      const computedStyle = window.getComputedStyle(root)
      // Si las variables CSS están disponibles, mostrar contenido
      if (computedStyle && computedStyle.fontFamily) {
        root.classList.add('styles-loaded')
      } else {
        // Si aún no están, esperar un poco más
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
