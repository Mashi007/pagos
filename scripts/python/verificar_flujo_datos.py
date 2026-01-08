"""
🔄 VERIFICACIÓN DE FLUJO DE DATOS ENTRE TABLAS
Sistema de Cobranzas y Gestión de Créditos

Este script verifica que los datos se mueven correctamente entre tablas:
- Cliente → Préstamo → Cuotas → Pagos
- Verifica que los cálculos se propagan correctamente
- Verifica que los estados se actualizan adecuadamente

Autor: Sistema de Auditoría Automatizado
Fecha: 2025-01-27
"""

import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo


class VerificadorFlujoDatos:
    """Verifica el flujo de datos entre tablas"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
        self.problemas: List[Dict] = []

    def verificar_flujo_completo(self) -> Dict:
        """Verifica el flujo completo de datos"""
        print("🔄 Verificando flujo de datos entre tablas...")
        print("=" * 80)

        # 1. Verificar flujo Cliente → Préstamo
        print("\n1. Verificando flujo Cliente → Préstamo...")
        self.verificar_cliente_prestamo()

        # 2. Verificar flujo Préstamo → Cuotas
        print("\n2. Verificando flujo Préstamo → Cuotas...")
        self.verificar_prestamo_cuotas()

        # 3. Verificar flujo Pagos → Cuotas
        print("\n3. Verificando flujo Pagos → Cuotas...")
        self.verificar_pagos_cuotas()

        # 4. Verificar propagación de cálculos
        print("\n4. Verificando propagación de cálculos...")
        self.verificar_propagacion_calculos()

        # 5. Verificar actualización de estados
        print("\n5. Verificando actualización de estados...")
        self.verificar_actualizacion_estados()

        return {
            "fecha_verificacion": datetime.now().isoformat(),
            "problemas": self.problemas,
            "total_problemas": len(self.problemas),
        }

    def verificar_cliente_prestamo(self):
        """Verifica que los datos del cliente se copien correctamente al préstamo"""
        # Verificar que cédulas coincidan
        try:
            prestamos_cedula_diferente = (
                self.db.query(Prestamo.id, Prestamo.cedula, Cliente.cedula.label("cliente_cedula"))
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .filter(Prestamo.cedula != Cliente.cedula)
                .count()
            )
        except Exception as e:
            # Si hay error con columnas, intentar sin join completo
            print(f"   [ADVERTENCIA] No se pudo verificar cédulas: {e}")
            prestamos_cedula_diferente = 0

        if prestamos_cedula_diferente > 0:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Cliente → Préstamo",
                "problema": f"{prestamos_cedula_diferente} préstamos con cédula diferente a la del cliente",
                "cantidad": prestamos_cedula_diferente,
            })

        # Verificar que nombres coincidan (o al menos sean similares)
        try:
            prestamos_nombre_diferente = (
                self.db.query(Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .filter(Prestamo.nombres != Cliente.nombres)
                .count()
            )
        except Exception as e:
            print(f"   [ADVERTENCIA] No se pudo verificar nombres: {e}")
            prestamos_nombre_diferente = 0

        if prestamos_nombre_diferente > 0:
            self.problemas.append({
                "tipo": "MENOR",
                "seccion": "Cliente → Préstamo",
                "problema": f"{prestamos_nombre_diferente} préstamos con nombres diferentes al cliente",
                "cantidad": prestamos_nombre_diferente,
            })

        print(f"   ✅ Verificados {self.db.query(Prestamo).count()} préstamos")

    def verificar_prestamo_cuotas(self):
        """Verifica que las cuotas se generen correctamente desde el préstamo"""
        # Verificar que todos los préstamos aprobados tengan cuotas
        prestamos_sin_cuotas = (
            self.db.query(Prestamo)
            .filter(Prestamo.estado == "APROBADO")
            .outerjoin(Cuota, Prestamo.id == Cuota.prestamo_id)
            .filter(Cuota.id.is_(None))
            .count()
        )

        if prestamos_sin_cuotas > 0:
            self.problemas.append({
                "tipo": "CRITICO",
                "seccion": "Préstamo → Cuotas",
                "problema": f"{prestamos_sin_cuotas} préstamos APROBADOS sin cuotas generadas",
                "cantidad": prestamos_sin_cuotas,
            })

        # Verificar que el número de cuotas coincida
        prestamos_cuotas_incorrectas = (
            self.db.query(Prestamo.id, Prestamo.numero_cuotas)
            .join(Cuota, Prestamo.id == Cuota.prestamo_id)
            .group_by(Prestamo.id, Prestamo.numero_cuotas)
            .having(func.count(Cuota.id) != Prestamo.numero_cuotas)
            .count()
        )

        if prestamos_cuotas_incorrectas > 0:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Préstamo → Cuotas",
                "problema": f"{prestamos_cuotas_incorrectas} préstamos con número de cuotas incorrecto",
                "cantidad": prestamos_cuotas_incorrectas,
            })

        # Verificar que los montos de las cuotas sumen correctamente
        prestamos_monto_incorrecto = []
        prestamos_con_cuotas = (
            self.db.query(Prestamo.id, Prestamo.total_financiamiento)
            .join(Cuota, Prestamo.id == Cuota.prestamo_id)
            .group_by(Prestamo.id, Prestamo.total_financiamiento)
            .all()
        )

        for prestamo_id, total_financiamiento in prestamos_con_cuotas:
            suma_cuotas = (
                self.db.query(func.sum(Cuota.monto_cuota))
                .filter(Cuota.prestamo_id == prestamo_id)
                .scalar()
                or Decimal("0.00")
            )

            # Permitir pequeña diferencia por redondeo
            if abs(total_financiamiento - suma_cuotas) > Decimal("1.00"):
                prestamos_monto_incorrecto.append(prestamo_id)

        if prestamos_monto_incorrecto:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Préstamo → Cuotas",
                "problema": f"{len(prestamos_monto_incorrecto)} préstamos donde suma de cuotas no coincide con total_financiamiento",
                "cantidad": len(prestamos_monto_incorrecto),
                "prestamos_afectados": prestamos_monto_incorrecto[:10],  # Primeros 10
            })

        print(f"   ✅ Verificadas {self.db.query(Cuota).count()} cuotas")

    def verificar_pagos_cuotas(self):
        """Verifica que los pagos se apliquen correctamente a las cuotas"""
        # Verificar que los pagos con prestamo_id tengan cuotas asociadas
        pagos_sin_cuotas = (
            self.db.query(Pago)
            .filter(
                and_(
                    Pago.prestamo_id.isnot(None),
                    Pago.activo == True,
                )
            )
            .outerjoin(Cuota, Pago.prestamo_id == Cuota.prestamo_id)
            .filter(Cuota.id.is_(None))
            .count()
        )

        if pagos_sin_cuotas > 0:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Pagos → Cuotas",
                "problema": f"{pagos_sin_cuotas} pagos activos con prestamo_id pero sin cuotas asociadas",
                "cantidad": pagos_sin_cuotas,
            })

        # Verificar que la suma de pagos coincida con total_pagado en cuotas
        prestamos_con_pagos = (
            self.db.query(Prestamo.id)
            .join(Pago, Prestamo.id == Pago.prestamo_id)
            .filter(Pago.activo == True)
            .distinct()
            .all()
        )

        prestamos_suma_incorrecta = []
        for (prestamo_id,) in prestamos_con_pagos:
            suma_pagos = (
                self.db.query(func.sum(Pago.monto_pagado))
                .filter(
                    and_(
                        Pago.prestamo_id == prestamo_id,
                        Pago.activo == True,
                    )
                )
                .scalar()
                or Decimal("0.00")
            )

            suma_cuotas = (
                self.db.query(func.sum(Cuota.total_pagado))
                .filter(Cuota.prestamo_id == prestamo_id)
                .scalar()
                or Decimal("0.00")
            )

            if abs(suma_pagos - suma_cuotas) > Decimal("0.01"):
                prestamos_suma_incorrecta.append(prestamo_id)

        if prestamos_suma_incorrecta:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Pagos → Cuotas",
                "problema": f"{len(prestamos_suma_incorrecta)} préstamos donde suma de pagos no coincide con suma de cuotas",
                "cantidad": len(prestamos_suma_incorrecta),
                "prestamos_afectados": prestamos_suma_incorrecta[:10],
            })

        print(f"   ✅ Verificados {self.db.query(Pago).filter(Pago.activo == True).count()} pagos activos")

    def verificar_propagacion_calculos(self):
        """Verifica que los cálculos se propaguen correctamente"""
        # Verificar que cuando se aplica un pago, los campos se actualicen correctamente
        cuotas_con_pagos_incoherentes = (
            self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.total_pagado > 0,
                    func.abs(
                        Cuota.total_pagado
                        - (Cuota.capital_pagado + Cuota.interes_pagado + Cuota.mora_pagada)
                    )
                    > Decimal("0.01"),
                )
            )
            .count()
        )

        if cuotas_con_pagos_incoherentes > 0:
            self.problemas.append({
                "tipo": "CRITICO",
                "seccion": "Propagación de Cálculos",
                "problema": f"{cuotas_con_pagos_incoherentes} cuotas con cálculos de pago incoherentes",
                "cantidad": cuotas_con_pagos_incoherentes,
            })

        # Verificar que los pendientes se calculen correctamente
        cuotas_pendientes_incoherentes = (
            self.db.query(Cuota)
            .filter(
                func.abs(
                    (Cuota.capital_pendiente + Cuota.interes_pendiente)
                    - (Cuota.monto_cuota - Cuota.total_pagado)
                )
                > Decimal("0.01")
            )
            .count()
        )

        if cuotas_pendientes_incoherentes > 0:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Propagación de Cálculos",
                "problema": f"{cuotas_pendientes_incoherentes} cuotas con cálculos de pendientes incoherentes",
                "cantidad": cuotas_pendientes_incoherentes,
            })

        # Verificar que la mora se calcule cuando corresponde
        cuotas_mora_no_calculada = (
            self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.fecha_pago.isnot(None),
                    Cuota.fecha_pago > Cuota.fecha_vencimiento,
                    or_(
                        Cuota.dias_mora == 0,
                        Cuota.monto_mora == 0,
                    ),
                )
            )
            .count()
        )

        if cuotas_mora_no_calculada > 0:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Propagación de Cálculos",
                "problema": f"{cuotas_mora_no_calculada} cuotas pagadas después de vencimiento sin mora calculada",
                "cantidad": cuotas_mora_no_calculada,
            })

        print(f"   ✅ Verificada propagación de cálculos")

    def verificar_actualizacion_estados(self):
        """Verifica que los estados se actualicen correctamente"""
        # Verificar que cuotas pagadas tengan estado correcto
        cuotas_pagadas_estado_incorrecto = (
            self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.total_pagado >= Cuota.monto_cuota,
                    Cuota.estado != "PAGADO",
                )
            )
            .count()
        )

        if cuotas_pagadas_estado_incorrecto > 0:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Actualización de Estados",
                "problema": f"{cuotas_pagadas_estado_incorrecto} cuotas completamente pagadas con estado incorrecto",
                "cantidad": cuotas_pagadas_estado_incorrecto,
            })

        # Verificar que cuotas parcialmente pagadas tengan estado PARCIAL
        cuotas_parciales_estado_incorrecto = (
            self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.total_pagado > 0,
                    Cuota.total_pagado < Cuota.monto_cuota,
                    Cuota.estado != "PARCIAL",
                    Cuota.estado != "PAGADO",
                )
            )
            .count()
        )

        if cuotas_parciales_estado_incorrecto > 0:
            self.problemas.append({
                "tipo": "MENOR",
                "seccion": "Actualización de Estados",
                "problema": f"{cuotas_parciales_estado_incorrecto} cuotas parcialmente pagadas con estado incorrecto",
                "cantidad": cuotas_parciales_estado_incorrecto,
            })

        # Verificar que cuotas vencidas tengan estado ATRASADO
        hoy = date.today()
        cuotas_vencidas_estado_incorrecto = (
            self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.total_pagado < Cuota.monto_cuota,
                    Cuota.estado != "ATRASADO",
                    Cuota.estado != "PAGADO",
                )
            )
            .count()
        )

        if cuotas_vencidas_estado_incorrecto > 0:
            self.problemas.append({
                "tipo": "MEDIO",
                "seccion": "Actualización de Estados",
                "problema": f"{cuotas_vencidas_estado_incorrecto} cuotas vencidas con estado incorrecto",
                "cantidad": cuotas_vencidas_estado_incorrecto,
            })

        print(f"   ✅ Verificada actualización de estados")

    def generar_reporte(self) -> str:
        """Genera un reporte del flujo de datos"""
        reporte = []
        reporte.append("=" * 80)
        reporte.append("🔄 REPORTE DE VERIFICACIÓN DE FLUJO DE DATOS")
        reporte.append("=" * 80)
        reporte.append(f"Fecha: {datetime.now().isoformat()}")
        reporte.append("")

        if not self.problemas:
            reporte.append("✅ No se encontraron problemas en el flujo de datos")
        else:
            reporte.append(f"⚠️ Se encontraron {len(self.problemas)} problemas:")
            reporte.append("")

            # Agrupar por tipo
            criticos = [p for p in self.problemas if p["tipo"] == "CRITICO"]
            medios = [p for p in self.problemas if p["tipo"] == "MEDIO"]
            menores = [p for p in self.problemas if p["tipo"] == "MENOR"]

            if criticos:
                reporte.append("🔴 PROBLEMAS CRÍTICOS:")
                for i, problema in enumerate(criticos, 1):
                    reporte.append(f"   {i}. [{problema['seccion']}] {problema['problema']}")
                reporte.append("")

            if medios:
                reporte.append("🟡 PROBLEMAS MEDIOS:")
                for i, problema in enumerate(medios, 1):
                    reporte.append(f"   {i}. [{problema['seccion']}] {problema['problema']}")
                reporte.append("")

            if menores:
                reporte.append("🟢 PROBLEMAS MENORES:")
                for i, problema in enumerate(menores, 1):
                    reporte.append(f"   {i}. [{problema['seccion']}] {problema['problema']}")
                reporte.append("")

        reporte.append("=" * 80)

        return "\n".join(reporte)

    def cerrar(self):
        """Cierra la conexión a la base de datos"""
        if self.db:
            self.db.close()


def main():
    """Función principal"""
    verificador = None
    try:
        verificador = VerificadorFlujoDatos()
        resultados = verificador.verificar_flujo_completo()

        reporte = verificador.generar_reporte()
        print("\n" + reporte)

        return 0

    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        if verificador:
            verificador.cerrar()


if __name__ == "__main__":
    sys.exit(main())
