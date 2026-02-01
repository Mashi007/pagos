import { useEffect } from 'react'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
  useEffect(() => {
    // Verificar que React está funcionando
    console.log('✅ React cargado correctamente')
    
    // Verificar configuración de API
    const apiUrl = import.meta.env.VITE_API_URL
    if (apiUrl) {
      console.log(`✅ API URL configurada: ${apiUrl}`)
    } else {
      console.warn('⚠️ VITE_API_URL no está configurada')
    }
  }, [])

  // Mostrar Dashboard directamente (sin autenticación por ahora)
  return <Dashboard />
}

export default App
