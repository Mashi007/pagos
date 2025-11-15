import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import type { Plugin } from 'vite'

// Plugin para eliminar modulepreload de chunks pesados (lazy loading)
function removeHeavyChunksPreload(): Plugin {
  return {
    name: 'remove-heavy-chunks-preload',
    transformIndexHtml(html) {
      // ✅ Eliminar TODOS los modulepreload para exceljs y pdf-export (carga bajo demanda)
      // Esto evita que el navegador precargue estos chunks automáticamente
      let modifiedHtml = html
      
      // Eliminar modulepreload para exceljs
      modifiedHtml = modifiedHtml.replace(
        /<link[^>]*rel=["']modulepreload["'][^>]*(exceljs|exceljs-)[^>]*>/gi,
        ''
      )
      
      // Eliminar modulepreload para pdf-export
      modifiedHtml = modifiedHtml.replace(
        /<link[^>]*rel=["']modulepreload["'][^>]*(pdf-export|jspdf|html2canvas)[^>]*>/gi,
        ''
      )
      
      // ✅ También eliminar cualquier preload que pueda estar causando la carga prematura
      modifiedHtml = modifiedHtml.replace(
        /<link[^>]*rel=["']preload["'][^>]*(exceljs|pdf-export)[^>]*>/gi,
        ''
      )
      
      return modifiedHtml
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      // Asegurar que React esté disponible correctamente
      jsxRuntime: 'automatic',
    }),
    removeHeavyChunksPreload(), // ✅ Eliminar preload de chunks pesados
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    // Asegurar que React se resuelva correctamente
    dedupe: ['react', 'react-dom'],
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
        // ✅ Deshabilitar modulePreload para chunks pesados
        experimentalMinChunkSize: 20000,
        manualChunks: (id) => {
          // ✅ CRÍTICO: React DEBE estar en el chunk principal y cargarse primero
          // Verificar React ANTES de cualquier otra lógica
          if (id.includes('node_modules')) {
            // React core - DEBE estar en chunk principal (undefined = chunk principal)
            // Esto asegura que React esté disponible antes que cualquier otro chunk
            if ((id.includes('/react/') || id.includes('/react-dom/') || 
                 id.includes('\\react\\') || id.includes('\\react-dom\\')) &&
                !id.includes('react-router') && 
                !id.includes('react-hook-form') && 
                !id.includes('@tanstack/react-query') &&
                !id.includes('react-hot-toast')) {
              return undefined // undefined = chunk principal (index.js)
            }
            
            // React Router
            if (id.includes('react-router')) {
              return 'router'
            }
            
            // Librerías pesadas de exportación - LAZY LOADING (cargar solo cuando se necesiten)
            // Estas librerías NO se incluyen en el bundle inicial, solo se cargan bajo demanda
            // ✅ EXCELJS: Forzar chunk separado y evitar precarga
            if (id.includes('exceljs')) {
              return 'exceljs' // Chunk separado, se carga solo al exportar Excel
            }
            if (id.includes('jspdf') || id.includes('html2canvas') || id.includes('jspdf-autotable')) {
              return 'pdf-export' // Chunk separado, se carga solo al exportar PDF
            }
            
            // Recharts - separar en chunk propio para lazy loading
            if (id.includes('recharts')) {
              return 'recharts'
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
            
            // Radix UI components - estos dependen de React, así que deben cargarse después
            if (id.includes('@radix-ui')) {
              return 'radix-ui'
            }
            
            // Otras dependencias comunes
            return 'vendor'
          }
          
          // ✅ NO separar hooks y servicios - incluir en chunks principales para evitar 404
          // Los hooks y servicios deben estar disponibles cuando se necesiten
          if (id.includes('/hooks/useConcesionarios') || 
              id.includes('/hooks/useAnalistas') ||
              id.includes('/services/notificacionService')) {
            return undefined // undefined = chunk principal
          }
          
          // NO separar DashboardMenu - incluir en chunk principal para evitar problemas de carga
          // Los componentes UI que usa (Radix UI) necesitan React disponible
          // if (id.includes('/pages/DashboardMenu')) {
          //   return 'dashboard-menu'
          // }
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
