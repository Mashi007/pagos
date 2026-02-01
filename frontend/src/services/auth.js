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
