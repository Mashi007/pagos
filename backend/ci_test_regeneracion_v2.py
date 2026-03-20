#!/usr/bin/env python3
"""
Script de Testing para CI/CD: Validacion de regeneracion de cuotas

Usa SQL directo (sin vistas) para mayor compatibilidad.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from sqlalchemy import text

class CITestRegeneracion:
    """Suite de tests para CI/CD"""
    
    def __init__(self, verbose=False):
        self.db = SessionLocal()
        self.verbose = verbose
        self.results = []
        self.timestamp = datetime.now().isoformat()
    
    def log(self, msg, level="INFO"):
        """Log con timestamp"""
        prefix = f"[{level}]" if level else "[.]"
        print(f"{prefix} {msg}")
    
    def test_cobertura_global(self):
        """Test: Todos los prestamos elegibles tienen cuotas"""
        try:
            result = self.db.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE numero_cuotas >= 1 AND fecha_aprobacion IS NOT NULL) AS eligibles,
                  COUNT(*) FILTER (WHERE (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = p.id) > 0) AS con_cuotas
                FROM prestamos p
            """)).fetchone()
            
            eligibles, con_cuotas = result[0], result[1]
            
            if eligibles == con_cuotas:
                self.results.append(("COBERTURA_GLOBAL", "PASS", f"{con_cuotas}/{eligibles}"))
                self.log(f"OK: {con_cuotas}/{eligibles} prestamos con cuotas", "OK")
                return True
            else:
                self.results.append(("COBERTURA_GLOBAL", "FAIL", f"{con_cuotas}/{eligibles}"))
                self.log(f"FAIL: {con_cuotas}/{eligibles} prestamos (falta {eligibles-con_cuotas})", "ERROR")
                return False
        except Exception as e:
            self.results.append(("COBERTURA_GLOBAL", "ERROR", str(e)))
            self.log(f"ERROR: {e}", "ERROR")
            return False
    
    def test_sin_desalineaciones(self):
        """Test: Cuota 1 alineada con fecha_aprobacion"""
        try:
            result = self.db.execute(text("""
                WITH p AS (
                  SELECT pr.id, pr.modalidad_pago, pr.fecha_aprobacion::date,
                         c.fecha_vencimiento
                  FROM prestamos pr
                  JOIN cuotas c ON c.prestamo_id = pr.id AND c.numero_cuota = 1
                  WHERE pr.fecha_aprobacion IS NOT NULL AND pr.numero_cuotas >= 1
                ),
                esp AS (
                  SELECT p.*,
                    CASE
                      WHEN UPPER(COALESCE(TRIM(p.modalidad_pago), 'MENSUAL')) = 'MENSUAL'
                        THEN (p.fecha_aprobacion + INTERVAL '1 month')::date
                      ELSE p.fecha_aprobacion
                    END AS venc_esperado
                  FROM p
                )
                SELECT COUNT(*) FROM esp
                WHERE fecha_vencimiento IS DISTINCT FROM venc_esperado
            """)).fetchone()
            
            desalineados = result[0]
            
            if desalineados == 0:
                self.results.append(("SIN_DESALINEACIONES", "PASS", "0 anomalias"))
                self.log(f"OK: 0 cuotas 1 desalineadas", "OK")
                return True
            else:
                self.results.append(("SIN_DESALINEACIONES", "FAIL", f"{desalineados}"))
                self.log(f"FAIL: {desalineados} desalineaciones", "ERROR")
                return False
        except Exception as e:
            self.results.append(("SIN_DESALINEACIONES", "ERROR", str(e)))
            self.log(f"ERROR: {e}", "ERROR")
            return False
    
    def test_sin_duplicados(self):
        """Test: Sin duplicados de numero_cuota por prestamo"""
        try:
            result = self.db.execute(text("""
                SELECT COUNT(*)
                FROM (
                  SELECT prestamo_id, numero_cuota
                  FROM cuotas
                  GROUP BY prestamo_id, numero_cuota
                  HAVING COUNT(*) > 1
                ) dups
            """)).fetchone()
            
            duplicados = result[0]
            
            if duplicados == 0:
                self.results.append(("SIN_DUPLICADOS", "PASS", "0 anomalias"))
                self.log(f"OK: 0 duplicados", "OK")
                return True
            else:
                self.results.append(("SIN_DUPLICADOS", "FAIL", f"{duplicados}"))
                self.log(f"FAIL: {duplicados} duplicados", "ERROR")
                return False
        except Exception as e:
            self.results.append(("SIN_DUPLICADOS", "ERROR", str(e)))
            self.log(f"ERROR: {e}", "ERROR")
            return False
    
    def test_integridad_cuotas(self):
        """Test: Campos completos en cuotas"""
        try:
            result = self.db.execute(text("""
                SELECT COUNT(*)
                FROM cuotas
                WHERE prestamo_id IS NULL
                   OR numero_cuota IS NULL
                   OR fecha_vencimiento IS NULL
                   OR monto_cuota IS NULL
            """)).fetchone()
            
            anomalias = result[0]
            
            if anomalias == 0:
                self.results.append(("INTEGRIDAD_CUOTAS", "PASS", "Todos campos OK"))
                self.log(f"OK: Integridad de datos correcta", "OK")
                return True
            else:
                self.results.append(("INTEGRIDAD_CUOTAS", "FAIL", f"{anomalias}"))
                self.log(f"FAIL: {anomalias} cuotas incompletas", "ERROR")
                return False
        except Exception as e:
            self.results.append(("INTEGRIDAD_CUOTAS", "ERROR", str(e)))
            self.log(f"ERROR: {e}", "ERROR")
            return False
    
    def test_distribucion_pagos(self):
        """Test: Distribucion de pagos"""
        try:
            result = self.db.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE COALESCE(total_pagado, 0) > 0) AS con_pago,
                  COUNT(*) FILTER (WHERE COALESCE(total_pagado, 0) = 0) AS sin_pago,
                  COUNT(*) AS total
                FROM cuotas
            """)).fetchone()
            
            con_pago, sin_pago, total = result[0], result[1], result[2]
            
            msg = f"{con_pago} pagadas, {sin_pago} pendientes ({total} total)"
            self.results.append(("DISTRIBUCION_PAGOS", "PASS", msg))
            self.log(f"OK: {msg}", "OK")
            return True
        except Exception as e:
            self.results.append(("DISTRIBUCION_PAGOS", "ERROR", str(e)))
            self.log(f"ERROR: {e}", "ERROR")
            return False
    
    def run_all(self):
        """Ejecutar todos los tests"""
        self.log("="*70, "INFO")
        self.log("SUITE DE TESTS CI/CD: Regeneracion de Cuotas", "INFO")
        self.log("="*70, "INFO")
        
        passed = 0
        failed = 0
        
        tests = [
            self.test_cobertura_global,
            self.test_sin_desalineaciones,
            self.test_sin_duplicados,
            self.test_integridad_cuotas,
            self.test_distribucion_pagos,
        ]
        
        for test_func in tests:
            self.log("", "INFO")
            try:
                result = test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Excepcion: {e}", "ERROR")
                failed += 1
        
        # Resumen
        self.log("", "INFO")
        self.log("="*70, "INFO")
        self.log(f"Resultado: {passed} PASS, {failed} FAIL / {len(tests)} total", "INFO")
        
        if failed > 0:
            self.log("TESTS FALLARON", "ERROR")
            return 1
        else:
            self.log("TODOS LOS TESTS PASARON", "OK")
            return 0
    
    def cleanup(self):
        self.db.close()


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    suite = CITestRegeneracion(verbose=verbose)
    try:
        exit_code = suite.run_all()
        sys.exit(exit_code)
    finally:
        suite.cleanup()
