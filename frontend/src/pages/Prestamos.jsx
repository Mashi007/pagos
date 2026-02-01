import { useState, useEffect } from 'react';
import apiClient from '../services/api';
import './Prestamos.css';

function Prestamos() {
  const [prestamos, setPrestamos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPrestamos();
  }, []);

  const loadPrestamos = async () => {
    try {
      setLoading(true);
      // TODO: Implementar endpoint cuando esté disponible en backend
      // const response = await apiClient.get('/api/v1/prestamos');
      // setPrestamos(response.data);
      setPrestamos([]);
    } catch (err) {
      console.error('Error cargando préstamos:', err);
      setError('Error al cargar los préstamos');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="page-container"><div className="loading">Cargando préstamos...</div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Gestión de Préstamos</h1>
      </div>
      
      {error && <div className="error-banner">{error}</div>}
      
      <div className="page-content">
        <p>Módulo de gestión de préstamos - En desarrollo</p>
        <p>Este módulo permitirá gestionar todos los préstamos del sistema.</p>
      </div>
    </div>
  );
}

export default Prestamos;
