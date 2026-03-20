#!/usr/bin/env python3
"""
Testing E2E: Flujo de pago completo en piloto (préstamos 2, 7, 8)

Prueba:
  1. Validar que cuotas fueron regeneradas
  2. Simular pagos (si API disponible)
  3. Verificar FIFO
  4. Validar reporte de amortización

Uso:
  python test_regeneracion_piloto.py
"""

import sys
import os
import requests
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago


class TestRegeneracionPiloto:
    """Suite de tests para piloto 2, 7, 8"""

    PRESTAMO_IDS = [2, 7, 8]
    API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

    def __init__(self):
        self.db = SessionLocal()
        self.results = []

    def test_1_cobertura_cuotas(self):
        """Test 1: Todos los préstamos piloto tienen cuotas"""
        test_name = "TEST 1: Cobertura de Cuotas"
        try:
            for pid in self.PRESTAMO_IDS:
                p = self.db.query(Prestamo).filter(Prestamo.id == pid).first()
                if not p:
                    raise ValueError(f"Préstamo {pid} no existe")

                c_count = self.db.query(Cuota).filter(Cuota.prestamo_id == pid).count()
                if c_count != p.numero_cuotas:
                    raise AssertionError(
                        f"Préstamo {pid}: {c_count} cuotas en tabla, "
                        f"{p.numero_cuotas} declaradas"
                    )

            self.results.append((test_name, "✅ PASS", ""))
        except Exception as e:
            self.results.append((test_name, "❌ FAIL", str(e)))

    def test_2_sin_duplicados(self):
        """Test 2: No hay duplicados de numero_cuota por préstamo"""
        test_name = "TEST 2: Sin Duplicados numero_cuota"
        try:
            from sqlalchemy import func
            q = (
                self.db.query(Cuota.prestamo_id, Cuota.numero_cuota, func.count())
                .filter(Cuota.prestamo_id.in_(self.PRESTAMO_IDS))
                .group_by(Cuota.prestamo_id, Cuota.numero_cuota)
                .having(func.count() > 1)
                .all()
            )
            if q:
                raise AssertionError(f"Duplicados encontrados: {q}")

            self.results.append((test_name, "✅ PASS", ""))
        except Exception as e:
            self.results.append((test_name, "❌ FAIL", str(e)))

    def test_3_cuota_1_alineada(self):
        """Test 3: Cuota 1 alineada con fecha_aprobacion + modalidad"""
        test_name = "TEST 3: Cuota 1 Alineada"
        try:
            from datetime import timedelta
            from dateutil.relativedelta import relativedelta

            for pid in self.PRESTAMO_IDS:
                p = self.db.query(Prestamo).filter(Prestamo.id == pid).first()
                c1 = (
                    self.db.query(Cuota)
                    .filter(Cuota.prestamo_id == pid, Cuota.numero_cuota == 1)
                    .first()
                )

                if not c1:
                    raise AssertionError(f"Préstamo {pid}: sin cuota 1")

                modalidad = (p.modalidad_pago or "MENSUAL").strip().upper()
                fecha_aprob = p.fecha_aprobacion.date() if p.fecha_aprobacion else None

                if not fecha_aprob:
                    raise AssertionError(f"Préstamo {pid}: sin fecha_aprobacion")

                if modalidad == "MENSUAL":
                    expected_venc = fecha_aprob + relativedelta(months=1)
                elif modalidad == "QUINCENAL":
                    expected_venc = fecha_aprob + timedelta(days=14)
                elif modalidad == "SEMANAL":
                    expected_venc = fecha_aprob + timedelta(days=6)
                else:
                    expected_venc = fecha_aprob + relativedelta(months=1)

                if c1.fecha_vencimiento.date() != expected_venc:
                    raise AssertionError(
                        f"Préstamo {pid}: venc {c1.fecha_vencimiento.date()} != {expected_venc}"
                    )

            self.results.append((test_name, "✅ PASS", ""))
        except Exception as e:
            self.results.append((test_name, "❌ FAIL", str(e)))

    def test_4_fifo_validacion(self):
        """Test 4: FIFO validación (no hay cuota posterior pagada si anterior impaga)"""
        test_name = "TEST 4: FIFO Validación"
        try:
            for pid in self.PRESTAMO_IDS:
                cuotas = (
                    self.db.query(Cuota)
                    .filter(Cuota.prestamo_id == pid)
                    .order_by(Cuota.numero_cuota)
                    .all()
                )

                for i, c in enumerate(cuotas):
                    monto_faltante = (c.monto_cuota or 0) - (c.total_pagado or 0)
                    is_cubierta = monto_faltante <= 0.01

                    if not is_cubierta:
                        # Esta cuota está impaga; verificar que ninguna posterior tiene pago
                        for siguiente in cuotas[i + 1 :]:
                            if (siguiente.total_pagado or 0) > 0:
                                raise AssertionError(
                                    f"Préstamo {pid}: cuota {siguiente.numero_cuota} "
                                    f"pagada pero {c.numero_cuota} impaga (violación FIFO)"
                                )
                        break

            self.results.append((test_name, "✅ PASS", ""))
        except Exception as e:
            self.results.append((test_name, "❌ FAIL", str(e)))

    def test_5_estado_consistencia(self):
        """Test 5: Estado de cuota consistente con total_pagado"""
        test_name = "TEST 5: Estado Consistencia"
        try:
            for pid in self.PRESTAMO_IDS:
                cuotas = self.db.query(Cuota).filter(Cuota.prestamo_id == pid).all()

                for c in cuotas:
                    monto_faltante = (c.monto_cuota or 0) - (c.total_pagado or 0)
                    total_pagado = c.total_pagado or 0

                    if c.estado == "PAGADO" and monto_faltante > 0.01:
                        raise AssertionError(
                            f"Préstamo {pid}, cuota {c.numero_cuota}: "
                            f"estado=PAGADO pero total_pagado={total_pagado} < monto_cuota={c.monto_cuota}"
                        )

                    if c.estado == "PENDIENTE" and total_pagado >= (c.monto_cuota - 0.01):
                        raise AssertionError(
                            f"Préstamo {pid}, cuota {c.numero_cuota}: "
                            f"estado=PENDIENTE pero total_pagado={total_pagado} >= {c.monto_cuota}"
                        )

            self.results.append((test_name, "✅ PASS", ""))
        except Exception as e:
            self.results.append((test_name, "❌ FAIL", str(e)))

    def test_6_montos_coherentes(self):
        """Test 6: Montos de cuota coherentes (sistema francés o iguales)"""
        test_name = "TEST 6: Montos Coherentes"
        try:
            for pid in self.PRESTAMO_IDS:
                p = self.db.query(Prestamo).filter(Prestamo.id == pid).first()
                tasa = p.tasa_interes or 0

                cuotas = (
                    self.db.query(Cuota)
                    .filter(Cuota.prestamo_id == pid)
                    .order_by(Cuota.numero_cuota)
                    .all()
                )

                if tasa <= 0:
                    # Cuotas iguales
                    monto_esperado = cuotas[0].monto_cuota
                    for c in cuotas:
                        if abs((c.monto_cuota or 0) - monto_esperado) > 0.01:
                            raise AssertionError(
                                f"Préstamo {pid}: cuotas desiguales con tasa={tasa}"
                            )
                else:
                    # Sistema francés: montos similares (pequeña variación por redondeo)
                    montos = [c.monto_cuota or 0 for c in cuotas]
                    promedio = sum(montos) / len(montos)
                    for c in cuotas:
                        variacion = abs((c.monto_cuota or 0) - promedio) / promedio
                        if variacion > 0.10:  # Tolerancia: 10%
                            raise AssertionError(
                                f"Préstamo {pid}: variación cuota {variacion:.2%} > 10%"
                            )

            self.results.append((test_name, "✅ PASS", ""))
        except Exception as e:
            self.results.append((test_name, "❌ FAIL", str(e)))

    def run_all(self):
        """Ejecutar todos los tests"""
        print("\n" + "=" * 80)
        print("SUITE DE TESTS: Regeneración Piloto (Préstamos 2, 7, 8)")
        print("=" * 80 + "\n")

        self.test_1_cobertura_cuotas()
        self.test_2_sin_duplicados()
        self.test_3_cuota_1_alineada()
        self.test_4_fifo_validacion()
        self.test_5_estado_consistencia()
        self.test_6_montos_coherentes()

        # Mostrar resultados
        print(f"{'Test':<50} {'Resultado':<15} {'Detalle':<30}")
        print("-" * 95)
        for test_name, resultado, detalle in self.results:
            print(f"{test_name:<50} {resultado:<15} {detalle:<30}")

        passed = sum(1 for _, r, _ in self.results if "PASS" in r)
        failed = sum(1 for _, r, _ in self.results if "FAIL" in r)

        print("-" * 95)
        print(f"\nResumen: {passed} PASS, {failed} FAIL / {len(self.results)} total\n")

        if failed > 0:
            print("⚠️  ALGUNOS TESTS FALLARON")
            sys.exit(1)
        else:
            print("✅ TODOS LOS TESTS PASARON\n")
            sys.exit(0)

    def cleanup(self):
        self.db.close()


if __name__ == "__main__":
    suite = TestRegeneracionPiloto()
    try:
        suite.run_all()
    finally:
        suite.cleanup()
