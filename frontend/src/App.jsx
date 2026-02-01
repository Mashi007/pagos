import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [count, setCount] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    // Verificar que React está funcionando
    console.log('✅ React cargado correctamente')
    setLoaded(true)
    
    // Verificar configuración de API
    const apiUrl = import.meta.env.VITE_API_URL
    if (apiUrl) {
      console.log(`✅ API URL configurada: ${apiUrl}`)
    } else {
      console.warn('⚠️ VITE_API_URL no está configurada')
    }
  }, [])

  if (error) {
    return (
      <div className="App">
        <header className="App-header">
          <h1>Error</h1>
          <p>{error}</p>
        </header>
      </div>
    )
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>Sistema de Pagos</h1>
        <p>Aplicación en construcción</p>
        {loaded && (
          <div style={{ fontSize: '0.8em', opacity: 0.7, marginTop: '10px' }}>
            ✅ React cargado correctamente
          </div>
        )}
        <div className="card">
          <button onClick={() => setCount((count) => count + 1)}>
            Contador: {count}
          </button>
        </div>
        <div style={{ marginTop: '20px', fontSize: '0.9em', opacity: 0.8 }}>
          <p>Estado: {loaded ? '✅ Cargado' : '⏳ Cargando...'}</p>
          <p>API URL: {import.meta.env.VITE_API_URL || 'No configurada'}</p>
        </div>
      </header>
    </div>
  )
}

export default App
