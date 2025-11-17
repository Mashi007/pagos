// ============================================
// GUARDAR CONFIGURACIÓN CON AUTENTICACIÓN CORRECTA
// Este código usa el apiClient del frontend para manejar la autenticación
// ============================================

(() => {
  console.log('🔍 Buscando apiClient en el frontend...');

  // Intentar acceder al apiClient desde el contexto de React
  // Primero, intentar importar dinámicamente
  const obtenerToken = () => {
    // Intentar obtener el token de localStorage o sessionStorage
    const rememberMe = localStorage.getItem('remember_me') === 'true';
    const token = rememberMe
      ? localStorage.getItem('access_token')
      : sessionStorage.getItem('access_token');

    if (!token) {
      console.error('❌ No se encontró token de autenticación');
      console.log('💡 Por favor, usa el botón "Guardar" de la interfaz en lugar de este código');
      return null;
    }

    // Verificar si el token está expirado
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const exp = payload.exp * 1000; // Convertir a milisegundos
      if (Date.now() >= exp) {
        console.error('❌ Token expirado. Por favor, recarga la página e inicia sesión nuevamente');
        return null;
      }
    } catch (e) {
      console.warn('⚠️ No se pudo verificar expiración del token, continuando...');
    }

    return token;
  };

  const token = obtenerToken();
  if (!token) {
    return;
  }

  // Obtener la configuración actual del formulario
  const obtenerConfiguracion = () => {
    // Intentar obtener los valores del formulario desde el DOM
    // Esto es una aproximación, lo mejor es usar el botón de la interfaz
    const config = {
      smtp_host: 'smtp.gmail.com',
      smtp_port: '587',
      smtp_user: 'pafo.kampei@gmail.com',
      smtp_password: '', // El usuario debe ingresar esto
      from_email: 'pafo.kampei@gmail.com',
      from_name: 'RapiCredit',
      smtp_use_tls: 'true',
      modo_pruebas: 'false'
    };

    console.warn('⚠️ Este código no puede leer los valores del formulario automáticamente');
    console.log('💡 Por favor, usa el botón "Guardar" de la interfaz');
    return config;
  };

  const config = obtenerConfiguracion();

  // Realizar la petición con el token correcto
  fetch('/api/v1/configuracion/email/configuracion', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(config)
  })
  .then(async (response) => {
    const data = await response.json();

    if (!response.ok) {
      // Si la respuesta no es OK, lanzar error
      throw new Error(data.detail || `Error ${response.status}: ${response.statusText}`);
    }

    return data;
  })
  .then((data) => {
    console.log('✅ Configuración guardada exitosamente:', data);
    alert('✅ Configuración guardada exitosamente');

    // Recargar la página para actualizar el estado
    setTimeout(() => {
      window.location.reload();
    }, 1500);
  })
  .catch((error) => {
    console.error('❌ Error guardando configuración:', error);
    alert(`❌ Error: ${error.message}\n\nPor favor, verifica que:\n1. Estés autenticado correctamente\n2. Tengas permisos de administrador\n3. Los valores de configuración sean correctos`);
  });
})();

