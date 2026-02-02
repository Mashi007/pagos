import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import Layout from './components/Layout';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import PagosPage from './pages/PagosPage';
import Clientes from './pages/Clientes';
import Prestamos from './pages/Prestamos';
import Cobranzas from './pages/Cobranzas';
import Notificaciones from './pages/Notificaciones';
import Analistas from './pages/Analistas';
import Concesionarios from './pages/Concesionarios';
import Usuarios from './pages/Usuarios';
import Reportes from './pages/Reportes';
import Configuracion from './pages/Configuracion';
import EmbudoClientes from './pages/EmbudoClientes';
import EmbudoConcesionarios from './pages/EmbudoConcesionarios';
import ChatAI from './pages/ChatAI';
import ConversacionesWhatsApp from './pages/ConversacionesWhatsApp';
import Comunicaciones from './pages/Comunicaciones';
import TicketsAtencion from './pages/TicketsAtencion';
import Solicitudes from './pages/Solicitudes';
import VisualizacionBD from './pages/VisualizacionBD';
import Ventas from './pages/Ventas';
import Programador from './pages/Programador';
import Plantillas from './pages/Plantillas';
import { authService } from './services/auth';
import './App.css';

function App() {
  useEffect(() => {
    // Verificar que React está funcionando
    console.log('✅ React cargado correctamente');
    
    // Verificar configuración de API
    const apiUrl = import.meta.env.VITE_API_URL;
    if (apiUrl) {
      console.log(`✅ API URL configurada: ${apiUrl}`);
    } else {
      console.warn('⚠️ VITE_API_URL no está configurada');
    }
  }, []);

  // Componente de ruta protegida
  const ProtectedRoute = ({ children }) => {
    // Por ahora, permitir acceso sin autenticación
    // Cuando el backend tenga autenticación, descomentar:
    // if (!authService.isAuthenticated()) {
    //   return <Navigate to="/login" replace />;
    // }
    return children;
  };

  return (
    <BrowserRouter>
      <Routes>
        {/* Ruta de login */}
        <Route path="/login" element={<Login />} />
        
        {/* Rutas protegidas con Layout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          {/* Dashboard */}
          <Route index element={<Dashboard />} />
          
          {/* Módulos principales */}
          <Route path="pagos" element={<PagosPage />} />
          <Route path="clientes" element={<Clientes />} />
          <Route path="prestamos" element={<Prestamos />} />
          <Route path="cobranzas" element={<Cobranzas />} />
          <Route path="notificaciones" element={<Notificaciones />} />
          
          {/* Gestión */}
          <Route path="analistas" element={<Analistas />} />
          <Route path="concesionarios" element={<Concesionarios />} />
          <Route path="usuarios" element={<Usuarios />} />
          
          {/* Embudos */}
          <Route path="embudo-clientes" element={<EmbudoClientes />} />
          <Route path="embudo-concesionarios" element={<EmbudoConcesionarios />} />
          
          {/* Sistema */}
          <Route path="reportes" element={<Reportes />} />
          <Route path="configuracion" element={<Configuracion />} />
          
          {/* Comunicaciones y WhatsApp */}
          <Route path="chat-ai" element={<ChatAI />} />
          <Route path="conversaciones-whatsapp" element={<ConversacionesWhatsApp />} />
          <Route path="comunicaciones" element={<Comunicaciones />} />
          <Route path="tickets-atencion" element={<TicketsAtencion />} />
          
          {/* Otros módulos */}
          <Route path="solicitudes" element={<Solicitudes />} />
          <Route path="visualizacion-bd" element={<VisualizacionBD />} />
          <Route path="ventas" element={<Ventas />} />
          <Route path="programador" element={<Programador />} />
          <Route path="plantillas" element={<Plantillas />} />
        </Route>
        
        {/* Redirección por defecto */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
