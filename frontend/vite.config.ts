import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'https://pagos-f2qf.onrender.com',
        changeOrigin: true,
        secure: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Separar node_modules en chunks más específicos
          if (id.includes('node_modules')) {
            // Librerías pesadas de exportación - cargar solo cuando se necesiten
            if (id.includes('xlsx')) {
              return 'xlsx'
            }
            if (id.includes('jspdf') || id.includes('html2canvas')) {
              return 'pdf-export'
            }
            
            // Recharts - separar en chunk propio para lazy loading
            if (id.includes('recharts')) {
              return 'recharts'
            }
            
            // React core
            if (id.includes('react') || id.includes('react-dom')) {
              return 'react-vendor'
            }
            
            // React Router
            if (id.includes('react-router')) {
              return 'router'
            }
            
            // UI libraries
            if (id.includes('framer-motion') || id.includes('lucide-react')) {
              return 'ui-libs'
            }
            
            // State management
            if (id.includes('@tanstack/react-query') || id.includes('zustand')) {
              return 'state-management'
            }
            
            // Form libraries
            if (id.includes('react-hook-form') || id.includes('zod') || id.includes('@hookform')) {
              return 'form-libs'
            }
            
            // Radix UI components
            if (id.includes('@radix-ui')) {
              return 'radix-ui'
            }
            
            // Otras dependencias comunes
            return 'vendor'
          }
          
          // Separar componentes grandes del dashboard
          if (id.includes('/pages/DashboardMenu')) {
            return 'dashboard-menu'
          }
        },
      },
      onwarn(warning, warn) {
        // Suprimir warnings de CSS relacionados con propiedades problemáticas ya corregidas
        if (warning.message && (
          warning.message.includes('webkit-text-size-adjust') ||
          warning.message.includes('moz-text-size-adjust') ||
          warning.message.includes('text-size-adjust') ||
          warning.message.includes('mal selector') ||
          warning.message.includes('bad selector') ||
          warning.message.includes('Juego de reglas ignoradas') ||
          warning.message.includes('ignored due to bad selector') ||
          warning.message.includes('ignored due to malformed selector')
        )) {
          return;
        }
        warn(warning);
      },
      treeshake: {
        moduleSideEffects: false, // Tree-shaking más agresivo
      },
    },
    chunkSizeWarningLimit: 500, // Reducir límite para detectar chunks grandes
    target: 'esnext',
    minify: 'esbuild',
    // Configuración de source maps para producción
    sourcemap: process.env.NODE_ENV === 'development' ? true : false,
    // Configuración adicional para producción
    reportCompressedSize: true,
    cssCodeSplit: true,
    // Suprimir warnings de CSS durante el build
    cssMinify: 'esbuild',
    // Optimizaciones adicionales
    assetsInlineLimit: 4096, // Inline assets pequeños (< 4KB)
  },
  base: '/',
  preview: {
    port: 4173,
    host: true,
  },
  // Configuración para Render
  define: {
    'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'https://pagos-f2qf.onrender.com'),
  },
})
