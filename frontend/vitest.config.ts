import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    // Configuración de entorno
    environment: 'jsdom',
    globals: true,
    
    // Directorios de pruebas
    include: [
      'tests/**/*.{test,spec}.{js,ts,jsx,tsx}',
      'src/**/*.{test,spec}.{js,ts,jsx,tsx}'
    ],
    
    // Excluir archivos
    exclude: [
      'node_modules',
      'dist',
      '.git',
      '.cache'
    ],
    
    // Configuración de cobertura
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{js,ts,jsx,tsx}'],
      exclude: [
        'src/**/*.{test,spec}.{js,ts,jsx,tsx}',
        'src/**/*.d.ts',
        'src/main.tsx',
        'src/vite-env.d.ts'
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    },
    
    // Configuración de setup
    setupFiles: ['./tests/setup.ts'],
    
    // Timeout para pruebas
    testTimeout: 10000,
    
    // Configuración de reporter
    reporter: ['verbose', 'html'],
    
    // Configuración de UI
    ui: true,
    
    // Configuración de watch
    watch: false
  },
  
  // Configuración de resolución de módulos
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@tests': path.resolve(__dirname, './tests')
    }
  }
})
