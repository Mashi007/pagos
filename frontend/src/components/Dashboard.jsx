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
      // NOTA: Deshabilitado temporalmente porque el backend no tiene endpoints de autenticación implementados
      // Cuando el backend tenga /api/v1/auth/me, descomentar esto:
      /*
      if (authService.isAuthenticated()) {
        try {
          const userData = await authService.getCurrentUser();
          setUser(userData);
        } catch (err) {
          // Si el endpoint no existe (404) o hay error del servidor (500), limpiar tokens silenciosamente
          if (err.response?.status === 404 || err.response?.status === 500) {
            console.warn('Endpoint de autenticación no disponible, limpiando tokens');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
          } else {
            console.warn('No se pudo obtener usuario:', err);
          }
        }
      }
      */
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
              <li>✅ Dashboard implementado</li>
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
