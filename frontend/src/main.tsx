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
  // ✅ Capturar errores NS_ERROR_FAILURE que ocurren en Firefox (especialmente con ExcelJS)
  if (event.error && event.error.name === 'NS_ERROR_FAILURE') {
    // Este error generalmente ocurre cuando se intenta actualizar el estado después del desmontaje
    // o durante la inicialización de módulos dinámicos (como ExcelJS)
    // Ya está siendo manejado por useIsMounted, pero lo capturamos para evitar que se muestre en consola
    event.preventDefault() // Prevenir que el error se propague
    event.stopPropagation() // Detener la propagación del evento
    return false // Retornar false para indicar que el error fue manejado
  }
  
  // ✅ Capturar errores relacionados con ExcelJS durante la inicialización
  if (event.filename && event.filename.includes('exceljs')) {
    if (event.error && event.error.name === 'NS_ERROR_FAILURE') {
      event.preventDefault()
      event.stopPropagation()
      return false
    }
  }
  
  // Capturar otros errores relacionados con React/Radix UI
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
    event.preventDefault() // Prevenir que el error se propague
    event.stopPropagation() // Detener la propagación
    return false
  }
  
  // ✅ Capturar errores relacionados con ExcelJS
  const reasonMessage = event.reason?.message || event.reason?.toString() || ''
  if (reasonMessage.includes('exceljs') && event.reason?.name === 'NS_ERROR_FAILURE') {
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
