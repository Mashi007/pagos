# 📦 Código Completo - Implementación Segura

## 📋 Índice

1. [package.json - Dependencias](#1-packagejson)
2. [Configuración de API](#2-configuración-de-api)
3. [Cliente HTTP](#3-cliente-http)
4. [Servicio de Autenticación](#4-servicio-de-autenticación)
5. [Manejo de Errores](#5-manejo-de-errores)
6. [Componente Login](#6-componente-login)
7. [Componente Dashboard](#7-componente-dashboard)
8. [App.jsx con Toggle](#8-appjsx-con-toggle)
9. [Estilos CSS](#9-estilos-css)

---

## 1. package.json

**Archivo**: `frontend/package.json`

```json
{
  "name": "pagos-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8",
    "express": "^4.18.2",
    "axios": "^1.6.0",
    "react-router-dom": "^6.20.0"
  },
  "devDependencies": {}
}
```

---

## 2. Configuración de API

**Archivo**: `frontend/src/config/api.js`

```javascript
/**
 * Configuración de la API
 */
const API_URL = import.meta.env.VITE_API_URL;

// Validar URL
if (!API_URL) {
  console.warn('⚠️ VITE_API_URL no está configurada, usando localhost');
}

if (API_URL && !API_URL.match(/^https?:\/\//)) {
  throw new Error('VITE_API_URL debe ser una URL válida (http:// o https://)');
}

const API_CONFIG = {
  baseURL: API_URL || 'http://localhost:8000',
  timeout: 30000, // 30 segundos
  retries: 3,
  retryDelay: 1000, // 1 segundo
};

export default API_CONFIG;
```

---

## 3. Cliente HTTP

**Archivo**: `frontend/src/services/api.js`

```javascript
/**
 * Cliente HTTP para comunicación con el backend
 */
import axios from 'axios';
import API_CONFIG from '../config/api';

// Crear instancia de axios
const apiClient = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token de autenticación
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para manejar errores y refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Manejar 401 (Unauthorized) - Token expirado
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${API_CONFIG.baseURL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken }
          );
          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // Refresh falló, limpiar tokens y redirigir a login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // No hay refresh token, redirigir a login
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

---

## 4. Servicio de Autenticación

**Archivo**: `frontend/src/services/auth.js`

```javascript
/**
 * Servicio de autenticación
 */
import apiClient from './api';
import { handleApiError } from '../utils/errorHandler';

export const authService = {
  /**
   * Iniciar sesión
   */
  async login(email, password) {
    try {
      const response = await apiClient.post('/api/v1/auth/login', {
        email,
        password,
      });
      const { access_token, refresh_token, user } = response.data;
      
      // Guardar tokens
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      
      return { user, access_token, refresh_token };
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  /**
   * Cerrar sesión
   */
  async logout() {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } catch (error) {
      console.error('Error en logout:', error);
    } finally {
      // Limpiar tokens siempre
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  },
  
  /**
   * Obtener usuario actual
   */
  async getCurrentUser() {
    try {
      const response = await apiClient.get('/api/v1/auth/me');
      return response.data;
    } catch (error) {
      throw new Error(handleApiError(error));
    }
  },
  
  /**
   * Verificar si el usuario está autenticado
   */
  isAuthenticated() {
    return !!localStorage.getItem('access_token');
  },
  
  /**
   * Obtener token de acceso
   */
  getToken() {
    return localStorage.getItem('access_token');
  },
};
```

---

## 5. Manejo de Errores

**Archivo**: `frontend/src/utils/errorHandler.js`

```javascript
/**
 * Utilidad para manejar errores de la API
 */
export const handleApiError = (error) => {
  if (error.response) {
    // Error de respuesta del servidor
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return data.detail || 'Solicitud inválida';
      case 401:
        return 'No autorizado. Por favor, inicia sesión.';
      case 403:
        return 'No tienes permiso para realizar esta acción';
      case 404:
        return 'Recurso no encontrado';
      case 500:
        return 'Error interno del servidor. Por favor, intenta más tarde.';
      default:
        return data.detail || `Error ${status}: ${data.message || 'Error desconocido'}`;
    }
  } else if (error.request) {
    // Error de red
    return 'Error de conexión. Verifica tu conexión a internet.';
  } else {
    // Error de configuración
    return 'Error de configuración. Por favor, contacta al administrador.';
  }
};
```

---

## 6. Componente Login

**Archivo**: `frontend/src/components/Login.jsx`

```javascript
/**
 * Componente de Login básico
 */
import { useState } from 'react';
import { authService } from '../services/auth';
import './Login.css';

function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await authService.login(email, password);
      console.log('✅ Login exitoso:', result);
      if (onLoginSuccess) {
        onLoginSuccess(result.user);
      }
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión');
      console.error('❌ Error en login:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Sistema de Pagos</h1>
        <h2>Iniciar Sesión</h2>
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              placeholder="usuario@ejemplo.com"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Contraseña:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              placeholder="••••••••"
            />
          </div>
          
          <button type="submit" disabled={loading} className="login-button">
            {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>
        </form>
        
        <div className="login-info">
          <p>⚠️ Nota: El sistema de autenticación aún no está implementado en el backend.</p>
          <p>Este componente está listo para cuando se implemente.</p>
        </div>
      </div>
    </div>
  );
}

export default Login;
```

---

## 7. Componente Dashboard

**Archivo**: `frontend/src/components/Dashboard.jsx`

```javascript
/**
 * Dashboard básico - Muestra información del sistema
 */
import { useState, useEffect } from 'react';
import apiClient from '../services/api';
import { authService } from '../services/auth';
import './Dashboard.css';

function Dashboard() {
  const [healthStatus, setHealthStatus] = useState(null);
  const [apiInfo, setApiInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Verificar health del backend
      try {
        const healthResponse = await apiClient.get('/health');
        setHealthStatus(healthResponse.data);
      } catch (err) {
        console.warn('Health check falló:', err);
      }

      // Obtener información de la API
      try {
        const apiResponse = await apiClient.get('/');
        setApiInfo(apiResponse.data);
      } catch (err) {
        console.warn('Info API falló:', err);
      }

      // Intentar obtener usuario actual (si está autenticado)
      if (authService.isAuthenticated()) {
        try {
          const userData = await authService.getCurrentUser();
          setUser(userData);
        } catch (err) {
          console.warn('No se pudo obtener usuario:', err);
        }
      }
    } catch (err) {
      setError('Error al cargar datos del dashboard');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await authService.logout();
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading">Cargando dashboard...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Sistema de Pagos</h1>
        {authService.isAuthenticated() && (
          <button onClick={handleLogout} className="logout-button">
            Cerrar Sesión
          </button>
        )}
      </header>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <div className="dashboard-content">
        <div className="dashboard-section">
          <h2>Estado del Sistema</h2>
          <div className="status-grid">
            <div className="status-card">
              <h3>Backend</h3>
              {healthStatus ? (
                <div className="status-success">
                  ✅ {healthStatus.status || 'Conectado'}
                </div>
              ) : (
                <div className="status-error">
                  ❌ No disponible
                </div>
              )}
            </div>

            <div className="status-card">
              <h3>Autenticación</h3>
              {authService.isAuthenticated() ? (
                <div className="status-success">
                  ✅ Autenticado
                </div>
              ) : (
                <div className="status-warning">
                  ⚠️ No autenticado
                </div>
              )}
            </div>

            <div className="status-card">
              <h3>API</h3>
              {apiInfo ? (
                <div className="status-success">
                  ✅ {apiInfo.message || 'Conectado'}
                </div>
              ) : (
                <div className="status-error">
                  ❌ No disponible
                </div>
              )}
            </div>
          </div>
        </div>

        {apiInfo && (
          <div className="dashboard-section">
            <h2>Información del Sistema</h2>
            <div className="info-card">
              <p><strong>Mensaje:</strong> {apiInfo.message}</p>
              <p><strong>Versión:</strong> {apiInfo.version}</p>
              <p><strong>Documentación:</strong> <a href={`${import.meta.env.VITE_API_URL}/docs`} target="_blank" rel="noopener noreferrer">Ver API Docs</a></p>
            </div>
          </div>
        )}

        {user && (
          <div className="dashboard-section">
            <h2>Usuario Actual</h2>
            <div className="info-card">
              <p><strong>Email:</strong> {user.email}</p>
              <p><strong>Usuario:</strong> {user.username || 'N/A'}</p>
            </div>
          </div>
        )}

        <div className="dashboard-section">
          <h2>Próximos Pasos</h2>
          <div className="info-card">
            <ul>
              <li>✅ Cliente HTTP configurado</li>
              <li>✅ Servicio de autenticación listo</li>
              <li>⏳ Implementar endpoints de autenticación en backend</li>
              <li>⏳ Agregar componentes de préstamos</li>
              <li>⏳ Agregar componentes de pagos</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
```

---

## 8. App.jsx con Toggle

**Archivo**: `frontend/src/App.jsx`

```javascript
import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import Login from './components/Login'
import { authService } from './services/auth'
import './App.css'

// Variable para activar/desactivar nuevas funcionalidades
// ⚠️ IMPORTANTE: Por defecto está en false para NO cambiar nada hasta que lo actives
const USE_NEW_FEATURES = false; // Cambiar a true para activar nuevas funcionalidades

function App() {
  const [count, setCount] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

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

    // Si usamos nuevas funcionalidades, verificar autenticación
    if (USE_NEW_FEATURES) {
      const authenticated = authService.isAuthenticated()
      setIsAuthenticated(authenticated)
      setLoading(false)
    } else {
      setLoading(false)
    }
  }, [])

  const handleLoginSuccess = (user) => {
    setIsAuthenticated(true)
    console.log('✅ Usuario autenticado:', user)
  }

  // Si no usamos nuevas funcionalidades, mostrar el placeholder original
  if (!USE_NEW_FEATURES) {
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

  // Usar nuevas funcionalidades con routing
  if (loading) {
    return (
      <div className="App">
        <div className="loading">Cargando...</div>
      </div>
    )
  }

  return (
    <Router>
      <Routes>
        <Route 
          path="/login" 
          element={
            isAuthenticated ? (
              <Navigate to="/" replace />
            ) : (
              <Login onLoginSuccess={handleLoginSuccess} />
            )
          } 
        />
        <Route 
          path="/" 
          element={
            isAuthenticated ? (
              <Dashboard />
            ) : (
              <Navigate to="/login" replace />
            )
          } 
        />
      </Routes>
    </Router>
  )
}

export default App
```

---

## 9. Estilos CSS

### Login.css

**Archivo**: `frontend/src/components/Login.css`

```css
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #242424;
  padding: 20px;
}

.login-card {
  background: #1a1a1a;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 400px;
}

.login-card h1 {
  color: white;
  text-align: center;
  margin-bottom: 0.5rem;
  font-size: 2rem;
}

.login-card h2 {
  color: rgba(255, 255, 255, 0.87);
  text-align: center;
  margin-bottom: 2rem;
  font-size: 1.5rem;
  font-weight: 400;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  color: rgba(255, 255, 255, 0.87);
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #444;
  border-radius: 4px;
  background-color: #2a2a2a;
  color: white;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #646cff;
}

.form-group input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-button {
  width: 100%;
  padding: 0.75rem;
  background-color: #646cff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.25s;
}

.login-button:hover:not(:disabled) {
  background-color: #535bf2;
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  background-color: #ff4444;
  color: white;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
}

.login-info {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #444;
}

.login-info p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.85rem;
  margin: 0.5rem 0;
  text-align: center;
}
```

### Dashboard.css

**Archivo**: `frontend/src/components/Dashboard.css`

```css
.dashboard-container {
  min-height: 100vh;
  background-color: #242424;
  color: rgba(255, 255, 255, 0.87);
  padding: 20px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #444;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 2rem;
}

.logout-button {
  padding: 0.5rem 1rem;
  background-color: #ff4444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.25s;
}

.logout-button:hover {
  background-color: #cc3333;
}

.error-banner {
  background-color: #ff4444;
  color: white;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  text-align: center;
}

.loading {
  text-align: center;
  padding: 2rem;
  font-size: 1.2rem;
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-section {
  margin-bottom: 2rem;
}

.dashboard-section h2 {
  margin-bottom: 1rem;
  font-size: 1.5rem;
  color: rgba(255, 255, 255, 0.87);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.status-card {
  background: #1a1a1a;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #444;
}

.status-card h3 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.87);
}

.status-success {
  color: #4caf50;
  font-weight: 500;
}

.status-warning {
  color: #ff9800;
  font-weight: 500;
}

.status-error {
  color: #f44336;
  font-weight: 500;
}

.info-card {
  background: #1a1a1a;
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid #444;
}

.info-card p {
  margin: 0.75rem 0;
  color: rgba(255, 255, 255, 0.87);
}

.info-card a {
  color: #646cff;
  text-decoration: none;
}

.info-card a:hover {
  text-decoration: underline;
}

.info-card ul {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
  color: rgba(255, 255, 255, 0.87);
}

.info-card li {
  margin: 0.5rem 0;
}
```

---

## 📋 Estructura de Archivos Completa

```
frontend/
├── src/
│   ├── config/
│   │   └── api.js              ← Código arriba (sección 2)
│   ├── services/
│   │   ├── api.js              ← Código arriba (sección 3)
│   │   └── auth.js             ← Código arriba (sección 4)
│   ├── utils/
│   │   └── errorHandler.js    ← Código arriba (sección 5)
│   ├── components/
│   │   ├── Login.jsx           ← Código arriba (sección 6)
│   │   ├── Login.css           ← Código arriba (sección 9)
│   │   ├── Dashboard.jsx       ← Código arriba (sección 7)
│   │   └── Dashboard.css       ← Código arriba (sección 9)
│   ├── App.jsx                 ← Código arriba (sección 8)
│   ├── App.css                 ← Ya existe (no modificar)
│   ├── main.jsx                ← Ya existe (no modificar)
│   └── index.css               ← Ya existe (no modificar)
├── package.json                ← Código arriba (sección 1)
└── .env                        ← Ya existe (no modificar)
```

---

## 🚀 Pasos para Implementar

### Paso 1: Crear Directorios
```bash
cd frontend/src
mkdir -p config services utils components
```

### Paso 2: Crear Archivos
Copia el código de cada sección al archivo correspondiente.

### Paso 3: Instalar Dependencias
```bash
cd frontend
npm install axios react-router-dom
```

### Paso 4: Probar
```bash
npm run dev
```

---

## ✅ Verificación

Después de crear los archivos, verifica:

1. **Estructura de directorios:**
   ```bash
   tree frontend/src
   ```

2. **Archivos creados:**
   ```bash
   ls -la frontend/src/config/
   ls -la frontend/src/services/
   ls -la frontend/src/utils/
   ls -la frontend/src/components/
   ```

3. **Sin errores:**
   ```bash
   npm run dev
   # Debería iniciar sin errores
   ```

---

*Documento creado el 2026-02-01*
