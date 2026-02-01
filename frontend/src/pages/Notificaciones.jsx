import { useState, useEffect } from 'react';
import apiClient from '../services/api';
import './Notificaciones.css';

function Notificaciones() {
  const [notificaciones, setNotificaciones] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotificaciones();
  }, []);

  const loadNotificaciones = async () => {
    try {
      setLoading(true);
      // TODO: Implementar endpoint cuando esté disponible
      setNotificaciones([]);
    } catch (err) {
      console.error('Error cargando notificaciones:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="page-container"><div className="loading">Cargando notificaciones...</div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Notificaciones</h1>
      </div>
      <div className="page-content">
        <p>Módulo de notificaciones - En desarrollo</p>
      </div>
    </div>
  );
}

export default Notificaciones;
