import { useState, useEffect } from 'react';
import { pagoService } from '../services/pagoService';
import './PagosPage.css';

function PagosPage() {
  const [kpis, setKpis] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [kpisRes, statsRes] = await Promise.all([
        pagoService.getKPIs(),
        pagoService.getStats(),
      ]);
      setKpis(kpisRes);
      setStats(statsRes);
    } catch (err) {
      console.error('Error cargando datos de pagos:', err);
      setError(err?.response?.data?.detail || 'Error al cargar los datos de pagos');
    } finally {
      setLoading(false);
    }
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

        {/* Stats */}
        {stats && (
          <section className="pagos-section">
            <h2 className="pagos-section-title">Estadísticas</h2>
            <div className="pagos-cards">
              <div className="pagos-card">
                <span className="pagos-card-label">Total cuotas</span>
                <span className="pagos-card-value">{stats.total_pagos ?? 0}</span>
              </div>
              <div className="pagos-card">
                <span className="pagos-card-label">Cuotas pagadas</span>
                <span className="pagos-card-value">{stats.cuotas_pagadas ?? 0}</span>
              </div>
              <div className="pagos-card">
                <span className="pagos-card-label">Cuotas pendientes</span>
                <span className="pagos-card-value">{stats.cuotas_pendientes ?? 0}</span>
              </div>
              <div className="pagos-card">
                <span className="pagos-card-label">Cuotas atrasadas</span>
                <span className="pagos-card-value">{stats.cuotas_atrasadas ?? 0}</span>
              </div>
              <div className="pagos-card pagos-card--highlight">
                <span className="pagos-card-label">Total pagado</span>
                <span className="pagos-card-value">{formatMoneda(stats.total_pagado)}</span>
              </div>
              <div className="pagos-card">
                <span className="pagos-card-label">Pagos hoy</span>
                <span className="pagos-card-value">{stats.pagos_hoy ?? 0}</span>
              </div>
            </div>
            {stats.pagos_por_estado && stats.pagos_por_estado.length > 0 && (
              <div className="pagos-estados">
                <h3 className="pagos-estados-title">Por estado</h3>
                <ul className="pagos-estados-list">
                  {stats.pagos_por_estado.map((item, i) => (
                    <li key={i}>
                      <span>{item.estado || 'Sin estado'}</span>
                      <span>{item.count ?? 0}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {!kpis && !stats && !error && (
          <p className="pagos-empty">No hay datos de pagos disponibles.</p>
        )}
      </div>
    </div>
  );
}

export default PagosPage;
