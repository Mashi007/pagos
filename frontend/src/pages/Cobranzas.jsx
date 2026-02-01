import { useState, useEffect } from 'react';
import apiClient from '../services/api';
import './Cobranzas.css';

function Cobranzas() {
  const [cobranzas, setCobranzas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadCobranzas();
  }, []);

  const loadCobranzas = async () => {
    try {
      setLoading(true);
      // TODO: Implementar endpoint cuando esté disponible en backend
      setCobranzas([]);
    } catch (err) {
      console.error('Error cargando cobranzas:', err);
      setError('Error al cargar las cobranzas');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="page-container"><div className="loading">Cargando cobranzas...</div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Gestión de Cobranzas</h1>
      </div>
      
      {error && <div className="error-banner">{error}</div>}
      
      <div className="page-content">
        <p>Módulo de gestión de cobranzas - En desarrollo</p>
      </div>
    </div>
  );
}

export default Cobranzas;
