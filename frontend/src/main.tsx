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

ReactDOM.createRoot(document.getElementById('root')!).render(
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
