import { PrestamosList } from '../components/prestamos/PrestamosList';
import './Prestamos.css';

/**
 * Página de Gestión de Préstamos.
 * Renderiza el listado real con datos del backend (API /api/v1/prestamos).
 */
function Prestamos() {
  return (
    <div className="page-container">
      <PrestamosList />
    </div>
  );
}

export default Prestamos;
