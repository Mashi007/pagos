#!/usr/bin/env python3
"""
Script de Testing para CI/CD: Validacion de regeneracion de cuotas

Ejecutado en pipeline (GitHub Actions, GitLab CI, etc.) para validar:
  1. Integridad post-regeneracion
  2. Alertas de monitoreo
  3. Salud general de la BD

Uso:
  python ci_test_regeneracion.py [--verbose]
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
                self.log(f"Cobertura: {con_cuotas}/{eligibles} prestamos", "OK")
                return True
            else:
                self.results.append(("COBERTURA_GLOBAL", "FAIL", f"{con_cuotas}/{eligibles}"))
                self.log(f"Cobertura: {con_cuotas}/{eligibles} (falta {eligibles-con_cuotas})", "ERROR")
                return False
        except Exception as e:
            self.results.append(("COBERTURA_GLOBAL", "ERROR", str(e)))
            self.log(f"Error en cobertura: {e}", "ERROR")
            return False
    
    def test_alertas_monitoreo(self):
        """Test: Ejecutar todas las vistas de alerta"""
        alerts_ok = True
        try:
            try:
                self.db.execute(text("SELECT 1 FROM v_alert_cascada_violacion LIMIT 1"))
                violacion_view = "v_alert_cascada_violacion"
            except Exception:
                violacion_view = "v_alert_fifo_violacion"
            alert_views = [
                "v_alert_cuota1_desalineada",
                "v_alert_numero_cuotas_inconsistente",
                "v_alert_duplicados_numero_cuota",
                "v_alert_cuotas_estado_invalido",
                "v_alert_cuotas_sin_fecha_aprobacion",
                "v_alert_inconsistencia_estado_pago",
                violacion_view,
            ]
            
            for view_name in alert_views:
                try:
                    result = self.db.execute(text(f"SELECT COUNT(*) FROM {view_name}")).fetchone()
                    count = result[0]
                    
                    if count == 0:
                        self.results.append((f"ALERT_{view_name}", "PASS", "0 anomalias"))
                        if self.verbose:
                            self.log(f"  {view_name}: 0 anomalias", "OK")
                    else:
                        self.results.append((f"ALERT_{view_name}", "WARN", f"{count} anomalias"))
                        self.log(f"  {view_name}: {count} anomalias detectadas", "WARN")
                        alerts_ok = False
                except Exception as e:
                    self.results.append((f"ALERT_{view_name}", "ERROR", str(e)))
                    self.log(f"  {view_name}: Error - {e}", "ERROR")
                    alerts_ok = False
            
            return alerts_ok
        except Exception as e:
            self.log(f"Error ejecutando alertas: {e}", "ERROR")
            return False
    
    def test_resumen_monitoreo(self):
        """Test: Dashboard de alertas"""
        try:
            result = self.db.execute(text("SELECT * FROM v_alert_resumen WHERE cantidad > 0")).fetchall()
            
            if len(result) == 0:
                self.results.append(("RESUMEN_ALERTAS", "PASS", "0 alertas activas"))
                self.log("Resumen de alertas: Todo limpio", "OK")
                return True
            else:
                msg = "; ".join([f"{r[0]}={r[1]}" for r in result])
                self.results.append(("RESUMEN_ALERTAS", "WARN", msg))
                self.log(f"Resumen de alertas: {msg}", "WARN")
                return False
        except Exception as e:
            self.results.append(("RESUMEN_ALERTAS", "ERROR", str(e)))
            self.log(f"Error en resumen: {e}", "ERROR")
            return False
    
    def test_integridad_cuotas(self):
        """Test: Validar integridad basica de cuotas"""
        try:
            # Comprobar que todas las cuotas tienen datos basicos
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
                self.results.append(("INTEGRIDAD_CUOTAS", "PASS", "Todos campos completos"))
                self.log("Integridad de cuotas: OK", "OK")
                return True
            else:
                self.results.append(("INTEGRIDAD_CUOTAS", "FAIL", f"{anomalias} cuotas incompletas"))
                self.log(f"Integridad: {anomalias} cuotas incompletas", "ERROR")
                return False
        except Exception as e:
            self.results.append(("INTEGRIDAD_CUOTAS", "ERROR", str(e)))
            self.log(f"Error en integridad: {e}", "ERROR")
            return False
    
    def test_distribucion_pagos(self):
        """Test: Validar distribucion de pagos"""
        try:
            result = self.db.execute(text("""
                SELECT
                  COUNT(*) FILTER (WHERE COALESCE(total_pagado, 0) > 0) AS con_pago,
                  COUNT(*) FILTER (WHERE COALESCE(total_pagado, 0) = 0) AS sin_pago,
                  COUNT(*) AS total
                FROM cuotas
            """)).fetchone()
            
            con_pago, sin_pago, total = result[0], result[1], result[2]
            
            msg = f"{con_pago} pagadas, {sin_pago} pendientes"
            self.results.append(("DISTRIBUCION_PAGOS", "PASS", msg))
            self.log(f"Distribucion: {msg}", "OK")
            return True
        except Exception as e:
            self.results.append(("DISTRIBUCION_PAGOS", "ERROR", str(e)))
            self.log(f"Error en distribucion: {e}", "ERROR")
            return False
    
    def run_all(self):
        """Ejecutar todos los tests"""
        self.log("Iniciando suite de tests para CI/CD", "INFO")
        self.log("=" * 60, "INFO")
        
        passed = 0
        failed = 0
        
        tests = [
            ("Cobertura Global", self.test_cobertura_global),
            ("Alertas de Monitoreo", self.test_alertas_monitoreo),
            ("Resumen de Alertas", self.test_resumen_monitoreo),
            ("Integridad de Cuotas", self.test_integridad_cuotas),
            ("Distribucion de Pagos", self.test_distribucion_pagos),
        ]
        
        for test_name, test_func in tests:
            self.log(f"\nEjecutando: {test_name}", "INFO")
            try:
                result = test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Excepcion en {test_name}: {e}", "ERROR")
                failed += 1
        
        # Resumen
        self.log("=" * 60, "INFO")
        self.log(f"Resultado: {passed} PASS, {failed} FAIL", "INFO")
        
        # Exportar resultados en JSON para CI
        report = {
            "timestamp": self.timestamp,
            "summary": {
                "passed": passed,
                "failed": failed,
                "total": len(tests)
            },
            "results": [
                {"test": r[0], "status": r[1], "detail": r[2]}
                for r in self.results
            ]
        }
        
        report_file = "/tmp/ci_test_regeneracion_report.json"
        try:
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            self.log(f"Reporte guardado: {report_file}", "INFO")
        except Exception as e:
            self.log(f"Error guardando reporte: {e}", "WARN")
        
        if failed > 0:
            self.log("Tests fallaron", "ERROR")
            return 1
        else:
            self.log("Todos los tests pasaron", "OK")
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
