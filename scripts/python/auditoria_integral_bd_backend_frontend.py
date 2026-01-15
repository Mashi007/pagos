"""
Auditoría Integral de Base de Datos, Backend y Frontend
Revisa coherencia entre modelos, esquemas, endpoints y servicios frontend
"""

import ast
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configuración de rutas
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"


@dataclass
class ModelField:
    """Campo de un modelo ORM"""
    name: str
    type: str
    nullable: bool = True
    unique: bool = False
    index: bool = False
    default: str = None
    foreign_key: str = None


@dataclass
class SchemaField:
    """Campo de un schema Pydantic"""
    name: str
    type: str
    optional: bool = True
    default: str = None


@dataclass
class Endpoint:
    """Endpoint de la API"""
    path: str
    method: str
    function_name: str
    file: str
    response_model: str = None
    tags: List[str] = field(default_factory=list)


@dataclass
class FrontendService:
    """Servicio del frontend"""
    name: str
    methods: List[str] = field(default_factory=list)
    endpoints_used: List[str] = field(default_factory=list)


@dataclass
class AuditResult:
    """Resultado de auditoría"""
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    message: str
    file: str = None
    line: int = None
    recommendation: str = None


class AuditoriaIntegral:
    """Auditoría integral del sistema"""

    def __init__(self):
        self.models: Dict[str, Dict[str, ModelField]] = {}
        self.schemas: Dict[str, Dict[str, SchemaField]] = {}
        self.endpoints: List[Endpoint] = []
        self.frontend_services: Dict[str, FrontendService] = {}
        self.issues: List[AuditResult] = []
        self.db_indexes: Set[str] = set()

    def run_audit(self):
        """Ejecuta la auditoría completa"""
        print("[*] Iniciando auditoria integral...")
        
        # 1. Auditar modelos de BD
        print("\n[1] Auditando modelos de base de datos...")
        self.audit_models()
        
        # 2. Auditar esquemas Pydantic
        print("\n[2] Auditando esquemas Pydantic...")
        self.audit_schemas()
        
        # 3. Auditar endpoints
        print("\n[3] Auditando endpoints del backend...")
        self.audit_endpoints()
        
        # 4. Auditar servicios frontend
        print("\n[4] Auditando servicios del frontend...")
        self.audit_frontend_services()
        
        # 5. Verificar coherencia modelos-esquemas
        print("\n[5] Verificando coherencia modelos-esquemas...")
        self.verify_model_schema_coherence()
        
        # 6. Verificar coherencia endpoints-frontend
        print("\n[6] Verificando coherencia endpoints-frontend...")
        self.verify_endpoint_frontend_coherence()
        
        # 7. Auditar índices de BD
        print("\n[7] Auditando indices de base de datos...")
        self.audit_database_indexes()
        
        # 8. Auditar migraciones
        print("\n[8] Auditando migraciones...")
        self.audit_migrations()
        
        # Generar informe
        self.generate_report()

    def audit_models(self):
        """Audita los modelos ORM"""
        models_dir = BACKEND_ROOT / "app" / "models"
        
        for model_file in models_dir.glob("*.py"):
            if model_file.name == "__init__.py":
                continue
                
            try:
                with open(model_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if self._is_sqlalchemy_model(node, content):
                                model_name = node.name
                                self.models[model_name] = {}
                                
                                # Extraer campos
                                for item in node.body:
                                    if isinstance(item, ast.Assign):
                                        for target in item.targets:
                                            if isinstance(target, ast.Name):
                                                field_name = target.id
                                                field_info = self._extract_field_info(item, content)
                                                if field_info:
                                                    self.models[model_name][field_name] = field_info
                                    
            except Exception as e:
                self.issues.append(AuditResult(
                    category="MODELS",
                    severity="MEDIUM",
                    message=f"Error al procesar modelo {model_file.name}: {str(e)}",
                    file=str(model_file)
                ))

    def audit_schemas(self):
        """Audita los esquemas Pydantic"""
        schemas_dir = BACKEND_ROOT / "app" / "schemas"
        
        for schema_file in schemas_dir.glob("*.py"):
            if schema_file.name == "__init__.py":
                continue
                
            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if self._is_pydantic_model(node, content):
                                schema_name = node.name
                                self.schemas[schema_name] = {}
                                
                                # Extraer campos
                                for item in node.body:
                                    if isinstance(item, ast.AnnAssign):
                                        if isinstance(item.target, ast.Name):
                                            field_name = item.target.id
                                            field_info = self._extract_schema_field_info(item, content)
                                            if field_info:
                                                self.schemas[schema_name][field_name] = field_info
                                    
            except Exception as e:
                self.issues.append(AuditResult(
                    category="SCHEMAS",
                    severity="MEDIUM",
                    message=f"Error al procesar schema {schema_file.name}: {str(e)}",
                    file=str(schema_file)
                ))

    def audit_endpoints(self):
        """Audita los endpoints del backend"""
        endpoints_dir = BACKEND_ROOT / "app" / "api" / "v1" / "endpoints"
        
        for endpoint_file in endpoints_dir.glob("*.py"):
            if endpoint_file.name == "__init__.py":
                continue
                
            try:
                with open(endpoint_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # Buscar decoradores @router.get, @router.post, etc.
                    for match in re.finditer(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', content):
                        method = match.group(1).upper()
                        path = match.group(2)
                        
                        # Buscar función asociada
                        lines = content[:match.end()].split('\n')
                        func_match = re.search(r'def\s+(\w+)', content[match.end():match.end()+500])
                        func_name = func_match.group(1) if func_match else "unknown"
                        
                        # Buscar response_model
                        response_model_match = re.search(r'response_model\s*=\s*(\w+)', content[match.end():match.end()+200])
                        response_model = response_model_match.group(1) if response_model_match else None
                        
                        endpoint = Endpoint(
                            path=path,
                            method=method,
                            function_name=func_name,
                            file=str(endpoint_file),
                            response_model=response_model
                        )
                        self.endpoints.append(endpoint)
                        
            except Exception as e:
                self.issues.append(AuditResult(
                    category="ENDPOINTS",
                    severity="MEDIUM",
                    message=f"Error al procesar endpoint {endpoint_file.name}: {str(e)}",
                    file=str(endpoint_file)
                ))

    def audit_frontend_services(self):
        """Audita los servicios del frontend"""
        services_dir = FRONTEND_ROOT / "src" / "services"
        
        for service_file in services_dir.glob("*.ts"):
            try:
                with open(service_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    service_name = service_file.stem.replace("Service", "")
                    service = FrontendService(name=service_name)
                    
                    # Buscar métodos y endpoints usados
                    api_calls = re.findall(r'apiClient\.(get|post|put|delete|patch)\(["\']([^"\']+)', content)
                    for method, path in api_calls:
                        service.methods.append(method.upper())
                        service.endpoints_used.append(path)
                    
                    self.frontend_services[service_name] = service
                    
            except Exception as e:
                self.issues.append(AuditResult(
                    category="FRONTEND",
                    severity="MEDIUM",
                    message=f"Error al procesar servicio {service_file.name}: {str(e)}",
                    file=str(service_file)
                ))

    def verify_model_schema_coherence(self):
        """Verifica coherencia entre modelos y esquemas"""
        # Mapear nombres de modelos a esquemas
        model_to_schema = {
            "User": "UserResponse",
            "Cliente": "ClienteResponse",
            "Prestamo": "PrestamoResponse",
            "Pago": "PagoResponse",
            "Cuota": "CuotaResponse",
        }
        
        for model_name, schema_name in model_to_schema.items():
            if model_name in self.models and schema_name in self.schemas:
                model_fields = set(self.models[model_name].keys())
                schema_fields = set(self.schemas[schema_name].keys())
                
                # Campos en modelo pero no en schema
                missing_in_schema = model_fields - schema_fields
                if missing_in_schema:
                    self.issues.append(AuditResult(
                        category="COHERENCE",
                        severity="HIGH",
                        message=f"Campos en modelo {model_name} pero no en schema {schema_name}: {missing_in_schema}",
                        recommendation=f"Agregar campos faltantes al schema {schema_name}"
                    ))
                
                # Campos en schema pero no en modelo (puede ser normal si son calculados)
                # Solo reportar si hay muchos
                extra_in_schema = schema_fields - model_fields
                if len(extra_in_schema) > 5:
                    self.issues.append(AuditResult(
                        category="COHERENCE",
                        severity="LOW",
                        message=f"Muchos campos en schema {schema_name} pero no en modelo {model_name}: {len(extra_in_schema)} campos",
                        recommendation="Verificar si son campos calculados o si falta sincronización"
                    ))

    def verify_endpoint_frontend_coherence(self):
        """Verifica coherencia entre endpoints y servicios frontend"""
        # Mapear endpoints del backend
        backend_endpoints = {}
        for endpoint in self.endpoints:
            key = f"{endpoint.method} {endpoint.path}"
            backend_endpoints[key] = endpoint
        
        # Verificar que los endpoints usados en frontend existan en backend
        frontend_endpoints_used = set()
        for service in self.frontend_services.values():
            for path in service.endpoints_used:
                # Normalizar path (remover query params, etc.)
                normalized_path = path.split('?')[0]
                frontend_endpoints_used.add(normalized_path)
        
        # Verificar endpoints del backend que no se usan en frontend
        backend_paths = {ep.path for ep in self.endpoints}
        unused_endpoints = backend_paths - frontend_endpoints_used
        
        if len(unused_endpoints) > 10:
            self.issues.append(AuditResult(
                category="COHERENCE",
                severity="MEDIUM",
                message=f"{len(unused_endpoints)} endpoints del backend no se usan en el frontend",
                recommendation="Revisar si son endpoints obsoletos o si falta implementación en frontend"
            ))

    def audit_database_indexes(self):
        """Audita índices de base de datos"""
        sql_dir = SCRIPTS_ROOT / "sql"
        
        # Buscar scripts SQL con índices
        for sql_file in sql_dir.glob("*.sql"):
            try:
                with open(sql_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # Buscar CREATE INDEX
                    indexes = re.findall(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', content, re.IGNORECASE)
                    for index_name in indexes:
                        self.db_indexes.add(index_name)
                        
            except Exception as e:
                self.issues.append(AuditResult(
                    category="DATABASE",
                    severity="LOW",
                    message=f"Error al procesar script SQL {sql_file.name}: {str(e)}",
                    file=str(sql_file)
                ))
        
        # Verificar índices críticos faltantes
        critical_indexes = [
            "idx_clientes_cedula",
            "idx_prestamos_cliente_id",
            "idx_cuotas_prestamo_id",
            "idx_pagos_prestamo_id",
        ]
        
        for idx in critical_indexes:
            if idx not in self.db_indexes:
                self.issues.append(AuditResult(
                    category="DATABASE",
                    severity="HIGH",
                    message=f"Índice crítico faltante: {idx}",
                    recommendation=f"Crear índice {idx} para mejorar rendimiento de consultas"
                ))

    def audit_migrations(self):
        """Audita migraciones de Alembic"""
        migrations_dir = BACKEND_ROOT / "alembic" / "versions"
        
        migration_files = list(migrations_dir.glob("*.py"))
        
        if len(migration_files) == 0:
            self.issues.append(AuditResult(
                category="MIGRATIONS",
                severity="CRITICAL",
                message="No se encontraron archivos de migración",
                recommendation="Verificar configuración de Alembic"
            ))
            return
        
        # Verificar nombres de migraciones
        for migration_file in migration_files:
            # Verificar formato de nombre
            if not re.match(r'^\d{8}_\w+|^[a-f0-9]{12}_\w+', migration_file.stem):
                self.issues.append(AuditResult(
                    category="MIGRATIONS",
                    severity="LOW",
                    message=f"Nombre de migración no sigue convención: {migration_file.name}",
                    file=str(migration_file),
                    recommendation="Usar formato: YYYYMMDD_descripcion o hash_descripcion"
                ))

    def _is_sqlalchemy_model(self, node: ast.ClassDef, content: str) -> bool:
        """Verifica si una clase es un modelo SQLAlchemy"""
        # Buscar herencia de Base
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Base":
                return True
            if isinstance(base, ast.Attribute):
                if base.attr == "Base":
                    return True
        return False

    def _is_pydantic_model(self, node: ast.ClassDef, content: str) -> bool:
        """Verifica si una clase es un modelo Pydantic"""
        # Buscar herencia de BaseModel
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
            if isinstance(base, ast.Attribute):
                if base.attr == "BaseModel":
                    return True
        return False

    def _extract_field_info(self, node: ast.Assign, content: str) -> ModelField:
        """Extrae información de un campo de modelo"""
        if not isinstance(node.value, ast.Call):
            return None
        
        # Buscar Column(...)
        if isinstance(node.value.func, ast.Name) and node.value.func.id == "Column":
            field_name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else None
            if not field_name:
                return None
            
            # Extraer tipo y propiedades básicas
            field_type = "Unknown"
            nullable = True
            unique = False
            index = False
            
            for keyword in node.value.keywords:
                if keyword.arg == "nullable":
                    nullable = self._get_bool_value(keyword.value)
                elif keyword.arg == "unique":
                    unique = self._get_bool_value(keyword.value)
                elif keyword.arg == "index":
                    index = self._get_bool_value(keyword.value)
            
            # Extraer tipo del primer argumento
            if node.value.args:
                if isinstance(node.value.args[0], ast.Name):
                    field_type = node.value.args[0].id
            
            return ModelField(
                name=field_name,
                type=field_type,
                nullable=nullable,
                unique=unique,
                index=index
            )
        
        return None

    def _extract_schema_field_info(self, node: ast.AnnAssign, content: str) -> SchemaField:
        """Extrae información de un campo de schema"""
        field_name = node.target.id if isinstance(node.target, ast.Name) else None
        if not field_name:
            return None
        
        # Determinar tipo
        field_type = "Unknown"
        optional = True
        
        if isinstance(node.annotation, ast.Name):
            field_type = node.annotation.id
        elif isinstance(node.annotation, ast.Subscript):
            if isinstance(node.annotation.value, ast.Name):
                field_type = node.annotation.value.id
                if field_type == "Optional":
                    optional = True
        
        return SchemaField(
            name=field_name,
            type=field_type,
            optional=optional
        )

    def _get_bool_value(self, node: ast.AST) -> bool:
        """Obtiene valor booleano de un nodo AST"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.NameConstant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in ("True", "False"):
                return node.id == "True"
        return False

    def generate_report(self):
        """Genera informe de auditoría"""
        report_path = PROJECT_ROOT / "Documentos" / "Auditorias" / "AUDITORIA_INTEGRAL_BD_BACKEND_FRONTEND.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 🔍 AUDITORÍA INTEGRAL: BASE DE DATOS, BACKEND Y FRONTEND\n\n")
            f.write(f"**Fecha:** {self._get_current_date()}\n\n")
            f.write("---\n\n")
            
            # Resumen ejecutivo
            f.write("## 📊 RESUMEN EJECUTIVO\n\n")
            f.write(f"- **Modelos auditados:** {len(self.models)}\n")
            f.write(f"- **Esquemas auditados:** {len(self.schemas)}\n")
            f.write(f"- **Endpoints auditados:** {len(self.endpoints)}\n")
            f.write(f"- **Servicios frontend auditados:** {len(self.frontend_services)}\n")
            f.write(f"- **Índices encontrados:** {len(self.db_indexes)}\n")
            f.write(f"- **Problemas encontrados:** {len(self.issues)}\n\n")
            
            # Problemas por severidad
            issues_by_severity = defaultdict(list)
            for issue in self.issues:
                issues_by_severity[issue.severity].append(issue)
            
            f.write("### Problemas por Severidad\n\n")
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                count = len(issues_by_severity[severity])
                if count > 0:
                    f.write(f"- **{severity}:** {count}\n")
            f.write("\n---\n\n")
            
            # Detalle de problemas
            f.write("## ⚠️ PROBLEMAS ENCONTRADOS\n\n")
            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                if issues_by_severity[severity]:
                    f.write(f"### {severity}\n\n")
                    for issue in issues_by_severity[severity]:
                        f.write(f"**Categoría:** {issue.category}\n\n")
                        f.write(f"**Mensaje:** {issue.message}\n\n")
                        if issue.file:
                            f.write(f"**Archivo:** `{issue.file}`\n\n")
                        if issue.recommendation:
                            f.write(f"**Recomendación:** {issue.recommendation}\n\n")
                        f.write("---\n\n")
            
            # Estadísticas detalladas
            f.write("## 📈 ESTADÍSTICAS DETALLADAS\n\n")
            
            f.write("### Modelos de Base de Datos\n\n")
            for model_name, fields in self.models.items():
                f.write(f"- **{model_name}:** {len(fields)} campos\n")
            f.write("\n")
            
            f.write("### Endpoints por Método HTTP\n\n")
            endpoints_by_method = defaultdict(int)
            for endpoint in self.endpoints:
                endpoints_by_method[endpoint.method] += 1
            
            for method, count in sorted(endpoints_by_method.items()):
                f.write(f"- **{method}:** {count}\n")
            f.write("\n")
            
            f.write("### Servicios Frontend\n\n")
            for service_name, service in self.frontend_services.items():
                f.write(f"- **{service_name}:** {len(service.endpoints_used)} endpoints usados\n")
            f.write("\n")
            
            # Recomendaciones generales
            f.write("## 💡 RECOMENDACIONES GENERALES\n\n")
            f.write("1. **Sincronización Modelos-Schemas:** Revisar y sincronizar campos faltantes\n")
            f.write("2. **Índices de BD:** Crear índices críticos para mejorar rendimiento\n")
            f.write("3. **Endpoints no usados:** Revisar si son obsoletos o necesitan implementación en frontend\n")
            f.write("4. **Migraciones:** Verificar que todas las migraciones estén aplicadas\n")
            f.write("5. **Documentación:** Mantener documentación actualizada de endpoints\n")
            f.write("\n")
        
        print(f"\n[OK] Informe generado en: {report_path}")

    def _get_current_date(self) -> str:
        """Obtiene fecha actual en formato legible"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    import sys
    import io
    # Configurar stdout para UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    auditoria = AuditoriaIntegral()
    auditoria.run_audit()
    print("\n[OK] Auditoria completada")
