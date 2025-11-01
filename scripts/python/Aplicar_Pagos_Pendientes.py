"""
Script para aplicar pagos pendientes a cuotas
Identifica pagos que tienen prestamo_id pero no se aplicaron a cuotas
y los reaplica usando el endpoint API o la función directamente
"""

import sys
import os
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from app.api.v1.endpoints.pagos import aplicar_pago_a_cuotas
from app.models.user import User

# Configurar encoding para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def identificar_pagos_pendientes(db: Session):
    """Identifica pagos que tienen prestamo_id pero no se aplicaron a cuotas"""
    print("🔍 Identificando pagos pendientes...")
    
    # Pagos con prestamo_id que no se aplicaron (total_pagado en cuotas = 0)
    pagos_pendientes = (
        db.query(Pago)
        .join(Prestamo, Pago.prestamo_id == Prestamo.id)
        .outerjoin(Cuota, Prestamo.id == Cuota.prestamo_id)
        .filter(Pago.prestamo_id.isnot(None))
        .group_by(Pago.id, Pago.monto_pagado)
        .having(
            db.func.coalesce(db.func.sum(Cuota.total_pagado), 0) == 0,
            Pago.monto_pagado > 0
        )
        .all()
    )
    
    print(f"📊 Encontrados {len(pagos_pendientes)} pagos pendientes")
    return pagos_pendientes


def aplicar_pago_a_cuotas_directo(pago: Pago, db: Session):
    """Aplica un pago directamente a las cuotas"""
    try:
        # Crear un usuario dummy para la función (o usar un usuario real)
        # NOTA: La función requiere current_user, pero para este script
        # podemos usar un usuario temporal
        from app.models.user import User
        user_dummy = User(
            email="sistema@aplicacion-pagos",
            nombres="Sistema",
            activo=True
        )
        
        cuotas_completadas = aplicar_pago_a_cuotas(pago, db, user_dummy)
        db.commit()
        
        print(f"✅ Pago ID {pago.id} aplicado. Cuotas completadas: {cuotas_completadas}")
        return True
    except Exception as e:
        print(f"❌ Error aplicando pago ID {pago.id}: {str(e)}")
        db.rollback()
        return False


def main():
    """Función principal"""
    db: Session = SessionLocal()
    
    try:
        print("=" * 60)
        print("APLICAR PAGOS PENDIENTES A CUOTAS")
        print("=" * 60)
        
        # Identificar pagos pendientes
        pagos_pendientes = identificar_pagos_pendientes(db)
        
        if not pagos_pendientes:
            print("✅ No hay pagos pendientes para aplicar")
            return
        
        print(f"\n📋 Aplicando {len(pagos_pendientes)} pagos pendientes...")
        print("-" * 60)
        
        aplicados = 0
        errores = 0
        
        for pago in pagos_pendientes:
            print(f"🔄 Procesando pago ID {pago.id} (Préstamo {pago.prestamo_id}, ${pago.monto_pagado})...")
            
            if aplicar_pago_a_cuotas_directo(pago, db):
                aplicados += 1
            else:
                errores += 1
        
        print("-" * 60)
        print(f"✅ Resumen:")
        print(f"   - Aplicados exitosamente: {aplicados}")
        print(f"   - Errores: {errores}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()

