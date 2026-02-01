import { useState, useEffect } from 'react';
import apiClient from '../services/api';
import './Clientes.css';

function Clientes() {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadClientes();
  }, []);

  const loadClientes = async () => {
    try {
      setLoading(true);
      // TODO: Implementar endpoint cuando esté disponible en backend
      // const response = await apiClient.get('/api/v1/clientes');
      // setClientes(response.data);
      setClientes([]);
    } catch (err) {
      console.error('Error cargando clientes:', err);
      setError('Error al cargar los clientes');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="page-container"><div className="loading">Cargando clientes...</div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Gestión de Clientes</h1>
      </div>
      
      {error && <div className="error-banner">{error}</div>}
      
      <div className="page-content">
        <p>Módulo de gestión de clientes - En desarrollo</p>
        <p>Este módulo permitirá gestionar todos los clientes del sistema.</p>
      </div>
    </div>
  );
}

export default Clientes;
