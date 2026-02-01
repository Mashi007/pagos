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
