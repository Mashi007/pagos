# backend/app/api/v1/endpoints/health.py"""Health Checks con Análisis de Impacto en PerformanceImplementa monitoreo de salud
# typing \nimport Any, Dict\nimport psutil\nfrom fastapi \nimport APIRouter, Depends, Response, status\nfrom sqlalchemy
# \nimport text\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_db\nfrom app.core.config \nimport
# settings\nfrom app.db.base \nimport Base\nfrom app.db.session \nimport engine# Constantes de
# configuraciónCACHE_DURATION_SECONDS = 30HEALTH_CHECK_TIMEOUT = 5MAX_RESPONSE_TIME_MS = 100CPU_THRESHOLD_PERCENT =
# "aprobaciones", "auditorias", "clientes", "users",]router = APIRouter()logger = logging.getLogger(__name__)# Cache para
# get_system_metrics() -> Dict[str, Any]:\n """ Obtiene métricas del sistema para análisis de impacto """ try:\n cpu_percent
# = psutil.cpu_percent(interval=0.1) memory = psutil.virtual_memory() disk = psutil.disk_usage("/") return 
# logger.warning(f"Error obteniendo métricas del sistema:\n {e}") return 
# }\ndef check_database_cached() -> Dict[str, Any]:\n """ Verifica la DB con cache para reducir carga y análisis de impacto
# _last_db_check["cache_duration"] ):\n try:\n \nfrom app.db.init_db \nimport check_database_connection db_status =
# _last_db_check@router.get("/cors-debug")async \ndef cors_debug():\n """Endpoint para debuggear CORS""" return 
# }@router.get("/health/render")@router.head("/health/render")async \ndef render_health_check():\n """ Health check
# optimizado para Render - Respuesta ultra rápida - Acepta tanto GET como HEAD - Sin verificaciones de DB para evitar
# status_code=status.HTTP_200_OK)async \ndef detailed_health_check(response:\n Response):\n """ Health check detallado con
# análisis de impacto en performance - Verifica DB con métricas de respuesta - Incluye métricas del sistema - Análisis de
# system_metrics = get_system_metrics() # Verificar DB con cache db_check = check_database_cached() # Calcular tiempo total
# system_metrics["cpu_percent"], "memory_usage_percent":\n system_metrics["memory_percent"], "impact_level":\n 
# {system_metrics['cpu_percent']:\n.1f}%" + f"exceeds threshold {CPU_THRESHOLD_PERCENT}%" ), "severity":\n "WARNING", } ) if
# system_metrics["memory_percent"] > MEMORY_THRESHOLD_PERCENT:\n impact_analysis["alerts"].append
# "message":\n ( f"Memory usage {system_metrics['memory_percent']:\n.1f}% exceeds threshold {MEMORY_THRESHOLD_PERCENT}%" ),
# "severity":\n "WARNING", } ) if system_metrics["disk_percent"] > DISK_THRESHOLD_PERCENT:\n
# impact_analysis["alerts"].append
# {system_metrics['disk_percent']:\n.1f}% exceeds threshold {DISK_THRESHOLD_PERCENT}%" ), "severity":\n "CRITICAL", } ) #
# Determinar estado general overall_status = "healthy" if not db_check["status"]:\n overall_status = "unhealthy" elif
# "environment":\n settings.ENVIRONMENT, "version":\n settings.APP_VERSION, } except Exception as e:\n logger.error
# en health check detallado:\n {e}") response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE return 
# db_status = True except Exception as e:\n logger.error(f"❌ Readiness check failed:\n {e}") db_status = False if not
# db_status:\n return Response
# media_type="application/json", ) return 
# Eliminada:\n {table}") except Exception as e:\n logger.warning(f" ⚠️ Error eliminando {table}:\n {e}") db.commit()
# as e:\n db.rollback() logger.error(f"❌ Error:\n {str(e)}") return 
# {str(e)}"}
