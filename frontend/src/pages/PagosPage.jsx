import { useState, useEffect } from 'react';
import { pagoService } from '../services/pagoService';
import './PagosPage.css';

function PagosPage() {
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await pagoService.getKPIs();
      setKpis(data);
    } catch (err) {
      console.error('Error cargando KPIs de pagos:', err);
      setError('No se pudieron cargar los indicadores (KPIs).');
    }
    setLoading(false);
  };

  const formatMoneda = (n) => {
    if (n == null || n === undefined) return '0,00';
    return Number(n).toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">Cargando datos de pagos...</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Gestión de Pagos</h1>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="page-content">
        {/* KPIs */}
        {kpis && (
          <section className="pagos-section">
            <h2 className="pagos-section-title">Indicadores (KPIs)</h2>
            <div className="pagos-cards">
              <div className="pagos-card">
                <span className="pagos-card-label">Cuotas pendientes</span>
                <span className="pagos-card-value">{kpis.cuotas_pendientes ?? 0}</span>
              </div>
              <div className="pagos-card">
                <span className="pagos-card-label">Clientes en mora</span>
                <span className="pagos-card-value">{kpis.clientes_en_mora ?? 0}</span>
              </div>
              <div className="pagos-card pagos-card--highlight">
                <span className="pagos-card-label">Monto cobrado (mes)</span>
                <span className="pagos-card-value">{formatMoneda(kpis.montoCobradoMes)}</span>
              </div>
              <div className="pagos-card">
                <span className="pagos-card-label">Saldo por cobrar</span>
                <span className="pagos-card-value">{formatMoneda(kpis.saldoPorCobrar)}</span>
              </div>
              <div className="pagos-card">
                <span className="pagos-card-label">Clientes al día</span>
                <span className="pagos-card-value">{kpis.clientesAlDia ?? 0}</span>
              </div>
            </div>
          </section>
        )}

        {!kpis && !error && (
          <p className="pagos-empty">No hay datos de pagos disponibles.</p>
        )}
      </div>
    </div>
  );
}

export default PagosPage;
