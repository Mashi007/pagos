"""
Sistema de Análisis de Esquema de Base de Datos
Identifica inconsistencias específicas entre modelos y esquema real
"""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE ANÁLISIS DE ESQUEMA DE BD
# ============================================


class DatabaseSchemaAnalyzer:
    """Analizador específico para inconsistencias de esquema de BD"""

    def __init__(self):
        self.schema_inconsistencies = deque(maxlen=1000)
        self.model_vs_schema_analysis = {}
        self.critical_tables = ["analistas", "clientes", "users", "usuarios"]
        self.expected_columns = {
            "analistas": [
                "id",
                "nombre",
                "activo",
                "created_at",
                "updated_at",
            ],
            "clientes": [
                "id",
                "cedula",
                "nombres",
                "apellidos",
                "estado",
                "created_at",
                "updated_at",
                "fecha_registro",
            ],
            "users": ["id", "email", "is_active", "created_at", "updated_at"],
            "usuarios": [
                "id",
                "email",
                "is_active",
                "created_at",
                "updated_at",
            ],
        }
        self.lock = threading.Lock()

    def analyze_schema_inconsistencies(self, db: Session) -> Dict[str, Any]:
        """Analizar inconsistencias específicas del esquema"""
        with self.lock:
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "critical_issues": [],
                "schema_analysis": {},
                "recommendations": [],
            }

            for table in self.critical_tables:
                table_analysis = self._analyze_table_schema(db, table)
                analysis["schema_analysis"][table] = table_analysis

                if table_analysis["critical_issues"]:
                    analysis["critical_issues"].extend(
                        table_analysis["critical_issues"]
                    )

            return analysis

    def _analyze_table_schema(
        self, db: Session, table_name: str
    ) -> Dict[str, Any]:
        """Analizar esquema específico de una tabla"""
        try:
            # Obtener columnas reales de la BD
            query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """

            result = db.execute(query, (table_name,))
            real_columns = [row[0] for row in result.fetchall()]

            # Comparar con columnas esperadas
            expected = self.expected_columns.get(table_name, [])
            missing_columns = [
                col for col in expected if col not in real_columns
            ]
            extra_columns = [
                col for col in real_columns if col not in expected
            ]

            critical_issues = []
            if missing_columns:
                critical_issues.append(
                    {
                        "type": "missing_columns",
                        "table": table_name,
                        "columns": missing_columns,
                        "severity": "critical",
                        "impact": "causes_503_errors",
                    }
                )

            if extra_columns:
                critical_issues.append(
                    {
                        "type": "extra_columns",
                        "table": table_name,
                        "columns": extra_columns,
                        "severity": "warning",
                        "impact": "potential_confusion",
                    }
                )

            return {
                "table_name": table_name,
                "real_columns": real_columns,
                "expected_columns": expected,
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
                "critical_issues": critical_issues,
                "schema_consistency": len(missing_columns) == 0,
            }

        except Exception as e:
            logger.error(
                f"Error analizando esquema de tabla {table_name}: {e}"
            )
            return {
                "table_name": table_name,
                "error": str(e),
                "critical_issues": [
                    {"type": "analysis_error", "error": str(e)}
                ],
            }

    def generate_schema_fixes(self, db: Session) -> Dict[str, Any]:
        """Generar fixes específicos para el esquema"""
        fixes = {
            "timestamp": datetime.now().isoformat(),
            "sql_fixes": [],
            "model_fixes": [],
            "priority": "high",
        }

        # Fix específico para tabla analistas
        fixes["sql_fixes"].append(
            {
                "table": "analistas",
                "fix_type": "add_column",
                "sql": (
                    "ALTER TABLE analistas ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                ),
                "description": "Agregar columna created_at faltante que causa error 503",
                "priority": "critical",
            }
        )

        # Fix para queries que usan created_at
        fixes["model_fixes"].append(
            {
                "file": "backend/app/api/v1/endpoints/analistas.py",
                "fix_type": "query_fix",
                "description": "Cambiar queries de created_at a updated_at en tabla analistas",
                "priority": "critical",
            }
        )

        return fixes

    def monitor_schema_changes(self, db: Session) -> Dict[str, Any]:
        """Monitorear cambios en el esquema en tiempo real"""
        with self.lock:
            current_state = {}

            for table in self.critical_tables:
                try:
                    query = """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """

                    result = db.execute(query, (table,))
                    current_state[table] = [
                        row[0] for row in result.fetchall()
                    ]

                except Exception as e:
                    current_state[table] = {"error": str(e)}

            return {
                "timestamp": datetime.now().isoformat(),
                "current_schema_state": current_state,
                "monitoring_active": True,
            }


# Instancia global del analizador de esquema
schema_analyzer = DatabaseSchemaAnalyzer()

# ============================================
# ENDPOINTS DE ANÁLISIS DE ESQUEMA
# ============================================


@router.get("/schema-inconsistencies")
async def get_schema_inconsistencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔍 Analizar inconsistencias específicas del esquema de BD
    """
    try:
        analysis = schema_analyzer.analyze_schema_inconsistencies(db)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": analysis,
        }

    except Exception as e:
        logger.error(f"Error analizando inconsistencias de esquema: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/schema-fixes")
async def get_schema_fixes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    🔧 Generar fixes específicos para el esquema
    """
    try:
        fixes = schema_analyzer.generate_schema_fixes(db)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "fixes": fixes,
        }

    except Exception as e:
        logger.error(f"Error generando fixes de esquema: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


@router.get("/schema-monitoring")
async def get_schema_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    📊 Monitorear estado actual del esquema
    """
    try:
        monitoring = schema_analyzer.monitor_schema_changes(db)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "monitoring": monitoring,
        }

    except Exception as e:
        logger.error(f"Error monitoreando esquema: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }
