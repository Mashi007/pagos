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
    
    // Manejar 404 o 500 - Endpoint no existe o error del servidor
    if (error.response?.status === 404 || error.response?.status === 500) {
      // Si es un endpoint de autenticación que no existe, silenciar el error
      // para evitar mostrar "Internal Error" al usuario
      if (originalRequest.url?.includes('/api/v1/auth/me') || 
          originalRequest.url?.includes('/api/v1/auth/refresh') ||
          originalRequest.url?.includes('/api/v1/auth/logout')) {
        // Crear un error silencioso que no se mostrará al usuario
        const silentError = new Error('Endpoint no disponible');
        silentError.response = error.response;
        silentError.config = error.config;
        silentError.isSilent = true; // Marcar como error silencioso
        return Promise.reject(silentError);
      }
    }
    
    // Manejar 401 (Unauthorized) - Token expirado
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Si el endpoint de refresh no existe, limpiar tokens silenciosamente
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
          // Refresh falló (endpoint no existe o token inválido), limpiar tokens silenciosamente
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          // No redirigir si estamos en Dashboard básico
          return Promise.reject(refreshError);
        }
      } else {
        // No hay refresh token, limpiar tokens
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
