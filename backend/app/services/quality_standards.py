# backend/app/services/quality_standards.py
"""Normas de Calidad para Services

Implementa estándares de desarrollo y calidad de código
"""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class QualityStandards:
    """Estándares de calidad para servicios"""

    # Límites de calidad
    MAX_FUNCTION_LINES = 50
    MAX_FUNCTION_PARAMS = 5
    MAX_CYCLOMATIC_COMPLEXITY = 10
    MAX_LINE_LENGTH = 120
    INDENTATION_SIZE = 4

    # Palabras prohibidas en producción
    FORBIDDEN_WORDS = [
        "console.log",
        "print(",
        "debugger",
        "TODO",
        "FIXME",
        "HACK",
    ]

    @staticmethod
    def validate_file_structure(file_path: str) -> Dict[str, Any]:
        """Validar estructura y organización del archivo"""
        results: Dict[str, Any] = {
            "file_path": file_path,
            "validations": {},
            "issues": [],
            "score": 0,
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Validaciones de estructura
            results["validations"]["has_docstring"] = (
                QualityStandards._has_module_docstring(content)
            )
            results["validations"]["proper_imports"] = (
                QualityStandards._validate_imports(content)
            )
            results["validations"]["class_structure"] = (
                QualityStandards._validate_class_structure(content)
            )
            results["validations"]["function_length"] = (
                QualityStandards._validate_function_length(content)
            )

            # Calcular score
            score = sum(results["validations"].values()) * 25
            results["score"] = score

            # Identificar issues
            if not results["validations"]["has_docstring"]:
                results["issues"].append("Falta docstring del módulo")

            if not results["validations"]["proper_imports"]:
                results["issues"].append("Imports mal organizados")

            if not results["validations"]["class_structure"]:
                results["issues"].append("Estructura de clases incorrecta")

            if not results["validations"]["function_length"]:
                results["issues"].append("Funciones demasiado largas")

        except Exception as e:
            logger.error(f"Error validando archivo {file_path}: {e}")
            results["issues"].append(f"Error de validación: {str(e)}")

        return results

    @staticmethod
    def _has_module_docstring(content: str) -> bool:
        """Verificar si el módulo tiene docstring"""
        try:
            tree = ast.parse(content)
            if tree.body and isinstance(tree.body[0], ast.Expr):
                if isinstance(tree.body[0].value, ast.Constant):
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _validate_imports(content: str) -> bool:
        """Validar organización de imports"""
        try:
            lines = content.split("\n")
            import_lines = []

            for line in lines:
                if line.strip().startswith(("import ", "from ")):
                    import_lines.append(line)

            # Verificar que los imports estén al inicio
            if import_lines:
                first_import_idx = lines.index(import_lines[0])
                if first_import_idx > 10:  # Después de docstring y comentarios
                    return False

            return True
        except Exception:
            return False

    @staticmethod
    def _validate_class_structure(content: str) -> bool:
        """Validar estructura de clases"""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Verificar que la clase tenga docstring
                    if not (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                    ):
                        return False
            return True
        except Exception:
            return False

    @staticmethod
    def _validate_function_length(content: str) -> bool:
        """Validar longitud de funciones"""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    lines = len(node.body)
                    if lines > QualityStandards.MAX_FUNCTION_LINES:
                        return False
            return True
        except Exception:
            return False

    @staticmethod
    def generate_quality_report(services_dir: str) -> Dict[str, Any]:
        """Generar reporte de calidad para todos los servicios"""
        services_path = Path(services_dir)

        if not services_path.exists():
            return {"error": "Directorio de servicios no encontrado"}

        report: Dict[str, Any] = {
            "overall_score": 0,
            "services": [],
            "recommendations": [],
        }

        # Analizar cada archivo Python
        for py_file in services_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            service_result = QualityStandards.validate_file_structure(str(py_file))
            report["services"].append(service_result)

        # Calcular score general
        if report["services"]:
            total_score = sum(s["score"] for s in report["services"])
            report["overall_score"] = total_score / len(report["services"])

        # Generar recomendaciones
        report["recommendations"] = QualityStandards._generate_recommendations(report)

        return report

    @staticmethod
    def _generate_recommendations(report: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones basadas en el reporte"""
        recommendations = []

        if report["overall_score"] < 80:
            recommendations.append("Implementar docstrings en todos los módulos")
            recommendations.append("Reorganizar imports según PEP 8")
            recommendations.append("Implementar manejo de errores consistente")

        if report["overall_score"] < 70:
            recommendations.append("Revisar longitud de funciones (máximo 50 líneas)")
            recommendations.append(
                "Refactorizar código con alta complejidad ciclomática"
            )

        if report["overall_score"] < 60:
            recommendations.append(
                "Revisar arquitectura y separación de responsabilidades"
            )

        return recommendations


class ServiceMetrics:
    """Clase para métricas de servicios"""

    @staticmethod
    def calculate_complexity_metrics(content: str) -> Dict[str, Any]:
        """Calcular métricas de complejidad del código"""
        try:
            tree = ast.parse(content)
            metrics = {
                "total_functions": 0,
                "total_classes": 0,
                "max_function_length": 0,
                "cyclomatic_complexity": 0,
            }

            function_lengths = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics["total_functions"] += 1
                    function_length = len(node.body)
                    function_lengths.append(function_length)
                    metrics["max_function_length"] = max(
                        metrics["max_function_length"], function_length
                    )

                    # Calcular complejidad ciclomática básica
                    complexity = 1  # Base complexity
                    for item in ast.walk(node):
                        if isinstance(
                            item, (ast.If, ast.While, ast.For, ast.ExceptHandler)
                        ):
                            complexity += 1
                    metrics["cyclomatic_complexity"] += complexity

                elif isinstance(node, ast.ClassDef):
                    metrics["total_classes"] += 1

            return metrics

        except Exception as e:
            logger.error(f"Error calculando métricas: {e}")
            return {"error": str(e)}

    @staticmethod
    def generate_performance_recommendations(metrics: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones de performance"""
        recommendations = []

        if metrics.get("cyclomatic_complexity", 0) > 20:
            recommendations.append(
                "Reducir complejidad ciclomática usando patrones de diseño"
            )

        if metrics.get("max_function_length", 0) > 50:
            recommendations.append("Dividir función más larga para mejorar legibilidad")

        if metrics.get("total_functions", 0) > 20:
            recommendations.append("Considerar dividir módulo en múltiples archivos")

        return recommendations


def apply_quality_standards(services_dir: str) -> Dict[str, Any]:
    """Aplicar normas de calidad y generar reporte"""
    report = QualityStandards.generate_quality_report(services_dir)

    # Agregar métricas detalladas
    for service in report["services"]:
        try:
            with open(service["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
            service["metrics"] = ServiceMetrics.calculate_complexity_metrics(content)
            service["performance_recommendations"] = (
                ServiceMetrics.generate_performance_recommendations(service["metrics"])
            )
        except Exception as e:
            service["metrics"] = {"error": str(e)}

    return report
