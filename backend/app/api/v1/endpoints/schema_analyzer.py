"""Sistema de Análisis de Esquema de Base de Datos
Identifica inconsistencias específicas entre modelos y esquema real
"""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
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
                    "ALTER TABLE analistas ADD COLUMN created_at TIMESTAMP "
                    "DEFAULT CURRENT_TIMESTAMP;"
                ),
                "description": "Agregar columna created_at faltante que causa error 503",
                "priority": "critical",
            }
        )
        
        # Fix para queries que usan created_at
        fixes["model_fixes"].append(
            {
                "file": "app/models/analista.py",
                "fix_type": "add_column",
                "description": "Agregar campo created_at al modelo Analista",
                "code": "created_at = Column(DateTime, default=datetime.utcnow)",
                "priority": "critical",
            }
        )
        
        return fixes
    
    def validate_schema_consistency(self, db: Session) -> Dict[str, Any]:
        """Validar consistencia general del esquema"""
        validation = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "table_validations": {},
            "critical_errors": [],
            "warnings": [],
        }
        
        try:
            all_valid = True
            
            for table in self.critical_tables:
                table_analysis = self._analyze_table_schema(db, table)
                table_valid = table_analysis.get("schema_consistency", False)
                
                validation["table_validations"][table] = {
                    "valid": table_valid,
                    "issues": table_analysis.get("critical_issues", [])
                }
                
                if not table_valid:
                    all_valid = False
                    validation["critical_errors"].extend(
                        table_analysis.get("critical_issues", [])
                    )
            
            validation["overall_status"] = "valid" if all_valid else "invalid"
            
        except Exception as e:
            logger.error(f"Error validando consistencia del esquema: {e}")
            validation["overall_status"] = "error"
            validation["critical_errors"].append({
                "type": "validation_error",
                "error": str(e)
            })
        
        return validation

# Instancia global del analizador de esquema
schema_analyzer = DatabaseSchemaAnalyzer()

# ============================================
# ENDPOINTS DE ANÁLISIS DE ESQUEMA
# ============================================

@router.get("/schema-analysis")
async def analyze_database_schema(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analizar esquema de base de datos"""
    try:
        analysis = schema_analyzer.analyze_schema_inconsistencies(db)
        
        return {
            "success": True,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error analizando esquema de BD: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/schema-fixes")
async def get_schema_fixes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener fixes para problemas de esquema"""
    try:
        fixes = schema_analyzer.generate_schema_fixes(db)
        
        return {
            "success": True,
            "fixes": fixes
        }
        
    except Exception as e:
        logger.error(f"Error generando fixes de esquema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/schema-validation")
async def validate_schema_consistency(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validar consistencia del esquema"""
    try:
        validation = schema_analyzer.validate_schema_consistency(db)
        
        return {
            "success": True,
            "validation": validation
        }
        
    except Exception as e:
        logger.error(f"Error validando esquema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/table-analysis/{table_name}")
async def analyze_specific_table(
    table_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analizar tabla específica"""
    try:
        if table_name not in schema_analyzer.critical_tables:
            raise HTTPException(
                status_code=400,
                detail=f"Tabla {table_name} no está en la lista de tablas críticas"
            )
        
        analysis = schema_analyzer._analyze_table_schema(db, table_name)
        
        return {
            "success": True,
            "table_analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analizando tabla {table_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )