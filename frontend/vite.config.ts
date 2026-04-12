import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'url'
import type { Plugin } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const requireFromViteConfig = createRequire(import.meta.url)

/**
 * exceljs "main" apunta a excel.js (Node). Alias al bundle browser.
 * Debe resolverse con require.resolve (soporta hoist de npm fuera de frontend/node_modules);
 * path fija .../frontend/node_modules/exceljs/... falla en ENOENT en algunos CI.
 */
function resolveExcelJsBrowserPath(): string {
  let pkgDir: string
  try {
    pkgDir = path.dirname(requireFromViteConfig.resolve('exceljs/package.json'))
  } catch {
    throw new Error(
      '[vite] No se pudo resolver el paquete npm "exceljs". Ejecute npm install en frontend.'
    )
  }
  const candidates = [
    path.join(pkgDir, 'dist', 'exceljs.min.js'),
    path.join(pkgDir, 'dist', 'exceljs.js'),
    path.join(pkgDir, 'dist', 'exceljs.bare.min.js'),
    path.join(pkgDir, 'lib', 'exceljs.browser.js'),
  ]
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate
    }
  }
  throw new Error(
    `[vite] exceljs en "${pkgDir}" sin bundle browser esperado (dist/). Revise la instalación del paquete.`
  )
}
// Ruta a src con barras normales (necesario para que Vite resuelva @/ en Windows)
const srcDir = path.resolve(__dirname, 'src').replace(/\\/g, '/')

// Plugin para eliminar modulepreload de chunks pesados (lazy loading)
function removeHeavyChunksPreload(): Plugin {
  const heavyChunks = ['exceljs', 'pdf-export', 'jspdf', 'html2canvas', 'jspdf-autotable']

  return {
    name: 'remove-heavy-chunks-preload',
    generateBundle(options, bundle) {
      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Marcar chunks pesados para que no se incluyan en modulepreload
      Object.keys(bundle).forEach(fileName => {
        const chunk = bundle[fileName]
        if (chunk.type === 'chunk') {
          const isHeavyChunk = heavyChunks.some(name =>
            fileName.includes(name) || chunk.name?.includes(name)
          )
          if (isHeavyChunk) {
            // Marcar el chunk para que no se precargue
            chunk.modulePreload = false
            // TambiÃÂÃÂ©n marcar todas las dependencias del chunk pesado
            if (chunk.imports) {
              chunk.imports.forEach(imp => {
                const importedChunk = bundle[imp]
                if (importedChunk && importedChunk.type === 'chunk') {
                  importedChunk.modulePreload = false
                }
              })
            }
          }
        }
      })
    },
    transformIndexHtml(html) {
      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Eliminar TODOS los modulepreload y preload para chunks pesados (carga bajo demanda)
      // Esto evita que el navegador precargue estos chunks automÃÂÃÂ¡ticamente
      let modifiedHtml = html

      // Lista de nombres de chunks pesados para usar en patrones
      const heavyChunkNames = ['exceljs', 'pdf-export', 'jspdf', 'html2canvas', 'jspdf-autotable']

      // Eliminar modulepreload para chunks pesados (mÃÂÃÂºltiples patrones)
      heavyChunkNames.forEach(name => {
        // PatrÃÂÃÂ³n 1: rel="modulepreload" ... nombre-chunk
        modifiedHtml = modifiedHtml.replace(
          new RegExp(`<link[^>]*rel=["']modulepreload["'][^>]*${name}[^"']*["'][^>]*>`, 'gi'),
          ''
        )
        // PatrÃÂÃÂ³n 2: nombre-chunk ... rel="modulepreload"
        modifiedHtml = modifiedHtml.replace(
          new RegExp(`<link[^>]*${name}[^"']*["'][^>]*rel=["']modulepreload["'][^>]*>`, 'gi'),
          ''
        )
        // PatrÃÂÃÂ³n 3: href contiene nombre-chunk con modulepreload
        modifiedHtml = modifiedHtml.replace(
          new RegExp(`<link[^>]*href=["'][^"']*${name}[^"']*["'][^>]*rel=["']modulepreload["'][^>]*>`, 'gi'),
          ''
        )
      })

      // ÃÂ¢ÃÂÃ¢ÂÂ¦ TambiÃÂÃÂ©n eliminar cualquier preload que pueda estar causando la carga prematura
      heavyChunkNames.forEach(name => {
        // PatrÃÂÃÂ³n 1: rel="preload" ... nombre-chunk
        modifiedHtml = modifiedHtml.replace(
          new RegExp(`<link[^>]*rel=["']preload["'][^>]*${name}[^"']*["'][^>]*>`, 'gi'),
          ''
        )
        // PatrÃÂÃÂ³n 2: nombre-chunk ... rel="preload"
        modifiedHtml = modifiedHtml.replace(
          new RegExp(`<link[^>]*${name}[^"']*["'][^>]*rel=["']preload["'][^>]*>`, 'gi'),
          ''
        )
        // PatrÃÂÃÂ³n 3: href contiene nombre-chunk con preload
        modifiedHtml = modifiedHtml.replace(
          new RegExp(`<link[^>]*href=["'][^"']*${name}[^"']*["'][^>]*rel=["']preload["'][^>]*>`, 'gi'),
          ''
        )
      })

      // ÃÂ¢ÃÂÃ¢ÂÂ¦ Eliminar tambiÃÂÃÂ©n cualquier referencia genÃÂÃÂ©rica a chunks pesados en links
      const allNamesPattern = heavyChunkNames.join('|')
      modifiedHtml = modifiedHtml.replace(
        new RegExp(`<link[^>]*href=["'][^"']*(${allNamesPattern})[^"']*["'][^>]*>`, 'gi'),
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
      // Asegurar que React estÃÂÃÂ© disponible correctamente
      jsxRuntime: 'automatic',
    }),
    removeHeavyChunksPreload(), // ÃÂ¢ÃÂÃ¢ÂÂ¦ Eliminar preload de chunks pesados
  ],
  resolve: {
    alias: [
      { find: /^@\//, replacement: `${srcDir}/` },
      { find: /^@$/, replacement: srcDir },
      // exceljs "main" apunta a excel.js -> lib/exceljs.nodejs.js (Node). Vite 6 falla al resolver
      // la entrada del paquete en build de navegador. Forzar el bundle publicado para browser.
      {
        find: /^exceljs$/,
        replacement: resolveExcelJsBrowserPath(),
      },
    ],
    // Asegurar que React se resuelva correctamente
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'https://rapicredit.onrender.com',
        changeOrigin: true,
        secure: true,
      },
    },
  },
  build: {
    // ÃÂ¢ÃÂÃ¢ÂÂ¦ Deshabilitar completamente modulePreload para evitar precarga automÃÂÃÂ¡tica
    // Los chunks pesados se cargarÃÂÃÂ¡n solo cuando se necesiten (lazy loading)
    modulePreload: {
      polyfill: false, // Deshabilitar polyfill de modulePreload
      resolveDependencies(filename, deps) {
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ CRÃÂÃÂTICO: Excluir chunks pesados de la resoluciÃÂÃÂ³n de dependencias
        // Esto previene que el navegador descubra y precargue estos chunks
        const heavyChunks = ['exceljs', 'pdf-export', 'jspdf', 'html2canvas', 'jspdf-autotable']

        // Si el chunk actual es uno pesado, no resolver dependencias
        if (heavyChunks.some(name => filename.includes(name))) {
          return [] // Retornar array vacÃÂÃÂ­o = no preload
        }

        // Si alguna dependencia es un chunk pesado, excluirla
        return deps.filter(dep => {
          const isHeavy = heavyChunks.some(name => dep.includes(name))
          return !isHeavy // Solo incluir dependencias que NO sean chunks pesados
        })
      }
    },
    rollupOptions: {
      output: {
        // ÃÂ¢ÃÂÃ¢ÂÂ¦ Deshabilitar modulePreload para chunks pesados
        experimentalMinChunkSize: 20000,
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            // Debe ir con react/react-dom: usan React.memo / hooks en el tope del módulo.
            // Si caen en `vendor` (p. ej. junto a exceljs), en producción puede fallar:
            // "can't access property 'memo' of undefined" (React aún no enlazado entre chunks).
            if (id.includes('react-hot-toast') || /[/\\]sonner[/\\]/.test(id)) {
              return 'react-core'
            }

            // Dependencias internas de react-dom / react 18: si quedan en `vendor` rompen el enlace
            // entre chunks (p. ej. "can't access property 'Children', … is undefined").
            if (/[/\\]scheduler[/\\]/.test(id) || id.includes('use-sync-external-store')) {
              return 'react-core'
            }

            if (id.includes('react-is')) {
              return 'react-core'
            }

            // Paquetes `react-*` / hooks que NO pasan por la ruta `.../react/...` del paquete core
            // (Radix, scroll lock, transiciones → useLayoutEffect / Children undefined si van a `vendor`).
            if (
              id.includes('react-remove-scroll') ||
              id.includes('react-remove-scroll-bar') ||
              id.includes('react-style-singleton') ||
              id.includes('react-transition-group') ||
              id.includes('use-sidecar') ||
              id.includes('use-callback-ref')
            ) {
              return 'react-core'
            }

            // React core - chunk separado (se carga primero por dependencia del entry)
            // Reduce el tamaÃÂÃÂ±o del chunk principal index.js
            if ((id.includes('/react/') || id.includes('/react-dom/') ||
                 id.includes('\\react\\') || id.includes('\\react-dom\\')) &&
                !id.includes('react-router') &&
                !id.includes('react-hook-form') &&
                !id.includes('@tanstack/react-query') &&
                !id.includes('react-hot-toast')) {
              return 'react-core'
            }

            // React Router
            if (id.includes('react-router')) {
              return 'router'
            }

            // Axios - usado en todos los servicios, chunk propio para cache
            if (id.includes('axios')) {
              return 'axios'
            }

            // LibrerÃÂÃÂ­as pesadas de exportaciÃÂÃÂ³n - LAZY LOADING (cargar solo cuando se necesiten)
            // Estas librerÃÂÃÂ­as NO se incluyen en el bundle inicial, solo se cargan bajo demanda
            // Chunk propio: no mezclar exceljs con `vendor` (menos riesgo de orden / APIs de React).
            if (id.includes('exceljs')) {
              return 'exceljs'
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

            // Radix UI components - estos dependen de React, asÃÂÃÂ­ que deben cargarse despuÃÂÃÂ©s
            if (id.includes('@radix-ui')) {
              return 'radix-ui'
            }

            // Otras dependencias comunes
            return 'vendor'
          }

          // ÃÂ¢ÃÂÃ¢ÂÂ¦ NO separar hooks y servicios - incluir en chunks principales para evitar 404
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
        // Suprimir warnings de CSS relacionados con propiedades problemÃÂÃÂ¡ticas ya corregidas
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
        moduleSideEffects: false, // Tree-shaking mÃÂÃÂ¡s agresivo
      },
    },
    chunkSizeWarningLimit: 1000, // index ~979 kB; aviso solo si algÃÂÃÂºn chunk supera 1 MB
    target: 'esnext',
    minify: 'esbuild',
    // ConfiguraciÃÂÃÂ³n de source maps para producciÃÂÃÂ³n
    sourcemap: process.env.NODE_ENV === 'development' ? true : false,
    // ConfiguraciÃÂÃÂ³n adicional para producciÃÂÃÂ³n
    reportCompressedSize: true,
    cssCodeSplit: true,
    // Suprimir warnings de CSS durante el build
    cssMinify: 'esbuild',
    // Optimizaciones adicionales
    assetsInlineLimit: 4096, // Inline assets pequeÃÂÃÂ±os (< 4KB)
  },
  // Base path para servir la app en https://rapicredit.onrender.com/pagos
  base: '/pagos/',
  preview: {
    port: 4173,
    host: true,
  },
  // ConfiguraciÃÂÃÂ³n para Render
  define: {
    'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'https://rapicredit.onrender.com'),
  },
})
