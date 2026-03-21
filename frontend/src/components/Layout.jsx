import { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { authService } from '../services/auth';
import './Layout.css';

function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleLogout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error('Error en logout:', error);
    } finally {
      navigate('/login');
    }
  };

  const menuItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/pagos', label: 'Pagos', icon: '💰' },
    { path: '/clientes', label: 'Clientes', icon: '👥' },
    { path: '/prestamos', label: 'Préstamos', icon: '📋' },
    { path: '/cobranzas', label: 'Cobranzas', icon: '💵' },
    { path: '/notificaciones', label: 'Notificaciones', icon: '🔔' },
    { path: '/analistas', label: 'Analistas', icon: '👨💼' },
    { path: '/concesionarios', label: 'Concesionarios', icon: '🏢' },
    { path: '/usuarios', label: 'Usuarios', icon: '👤' },
    { path: '/embudo-clientes', label: 'Embudo Clientes', icon: '📈' },
    { path: '/embudo-concesionarios', label: 'Embudo Concesionarios', icon: '📊' },
    { path: '/chat-ai', label: 'Chat AI', icon: '🤖' },
    { path: '/conversaciones-whatsapp', label: 'WhatsApp', icon: '💬' },
    { path: '/comunicaciones', label: 'Comunicaciones', icon: '📧' },
    { path: '/tickets-atencion', label: 'Tickets', icon: '🎫' },
    { path: '/solicitudes', label: 'Solicitudes', icon: '📝' },
    // Ventas: oculto y en pausa
    // { path: '/ventas', label: 'Ventas', icon: '🛒' },
    { path: '/visualizacion-bd', label: 'Visualización BD', icon: '🗄️' },
    { path: '/programador', label: 'Programador', icon: '📅' },
    { path: '/plantillas', label: 'Plantillas', icon: '📑' },
    { path: '/reportes', label: 'Reportes', icon: '📄' },
    { path: '/configuracion', label: 'Configuración', icon: '⚙️' },
  ];

  return (
    <div className="layout-container">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <h2>{sidebarCollapsed ? 'SP' : 'Sistema de Pagos'}</h2>
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            aria-label="Toggle sidebar"
          >
            {sidebarCollapsed ? '→' : '←'}
          </button>
        </div>
        
        <nav className="sidebar-nav">
          <ul>
            {menuItems.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={location.pathname === item.path ? 'active' : ''}
                >
                  <span className="icon">{item.icon}</span>
                  {!sidebarCollapsed && <span className="label">{item.label}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        
        <div className="sidebar-footer">
          <button onClick={handleLogout} className="logout-btn">
            <span className="icon">🚪</span>
            {!sidebarCollapsed && <span>Cerrar Sesión</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div className="content-wrapper">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default Layout;
