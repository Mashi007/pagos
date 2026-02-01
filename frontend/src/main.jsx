import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Verificar que el elemento root existe
const rootElement = document.getElementById('root')

if (!rootElement) {
  console.error('❌ ERROR: No se encontró el elemento con id="root"')
  document.body.innerHTML = `
    <div style="padding: 20px; font-family: Arial, sans-serif;">
      <h1>Error de configuración</h1>
      <p>No se encontró el elemento con id="root" en el HTML.</p>
      <p>Por favor, verifica que index.html contenga: &lt;div id="root"&gt;&lt;/div&gt;</p>
    </div>
  `
} else {
  try {
    console.log('🚀 Iniciando aplicación React...')
    const root = ReactDOM.createRoot(rootElement)
    root.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    )
    console.log('✅ Aplicación React renderizada correctamente')
  } catch (error) {
    console.error('❌ ERROR al renderizar React:', error)
    rootElement.innerHTML = `
      <div style="padding: 20px; font-family: Arial, sans-serif;">
        <h1>Error al cargar la aplicación</h1>
        <p>Error: ${error.message}</p>
        <pre>${error.stack}</pre>
      </div>
    `
  }
}
