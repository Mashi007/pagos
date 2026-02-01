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
   * NOTA: Este endpoint requiere que el backend tenga /api/v1/auth/me implementado
   */
  async getCurrentUser() {
    try {
      const response = await apiClient.get('/api/v1/auth/me');
      return response.data;
    } catch (error) {
      // Si el endpoint no existe (404) o hay error del servidor (500), no lanzar error visible
      if (error.response?.status === 404 || error.response?.status === 500) {
        console.warn('Endpoint /api/v1/auth/me no disponible en el backend');
        return null; // Retornar null en lugar de lanzar error
      }
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
