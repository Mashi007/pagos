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
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['framer-motion', 'lucide-react'],
          query: ['@tanstack/react-query'],
          utils: ['clsx', 'tailwind-merge', 'date-fns'],
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
    },
    chunkSizeWarningLimit: 1000,
    target: 'esnext',
    minify: 'esbuild',
    // Configuración de source maps para producción
    sourcemap: process.env.NODE_ENV === 'development' ? true : false,
    // Configuración adicional para producción
    reportCompressedSize: true,
    cssCodeSplit: true,
    // Suprimir warnings de CSS durante el build
    cssMinify: 'esbuild',
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
