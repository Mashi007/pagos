import { useState, useEffect } from 'react';
import apiClient from '../services/api';
import './PagosPage.css';

function PagosPage() {
  const [pagos, setPagos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPagos();
  }, []);

  const loadPagos = async () => {
    try {
      setLoading(true);
      // TODO: Implementar endpoint cuando esté disponible en backend
      // const response = await apiClient.get('/api/v1/pagos');
      // setPagos(response.data);
      setPagos([]);
    } catch (err) {
      console.error('Error cargando pagos:', err);
      setError('Error al cargar los pagos');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="page-container"><div className="loading">Cargando pagos...</div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Gestión de Pagos</h1>
      </div>
      
      {error && <div className="error-banner">{error}</div>}
      
      <div className="page-content">
        <p>Módulo de gestión de pagos - En desarrollo</p>
        <p>Este módulo permitirá gestionar todos los pagos del sistema.</p>
      </div>
    </div>
  );
}

export default PagosPage;
