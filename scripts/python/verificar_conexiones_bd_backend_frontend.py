"""
Script para verificar que las conexiones entre base de datos, backend y frontend están correctamente configuradas.

Verifica:
1. Backend -> Base de Datos: Conexión y acceso a tablas principales
2. Frontend -> Backend: Configuración de API URL y endpoints disponibles
3. Variables de entorno críticas
4. CORS configurado correctamente
"""

import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, quote, urlunparse

# Agregar backend al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
        logger.info(f"✅ Archivo .env encontrado y cargado: {env_file}")
except ImportError:
    logger.warning("⚠️ python-dotenv no disponible, usando solo variables de entorno del sistema")
except Exception as e:
    logger.warning(f"⚠️ Error cargando .env: {e}")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verificar_backend_bd():
    """Verifica la conexión del backend a la base de datos."""
    logger.info("=" * 80)
    logger.info("🔍 VERIFICACIÓN: BACKEND -> BASE DE DATOS")
    logger.info("=" * 80)
    
    resultados = {
        'conexion_ok': False,
        'tablas_accesibles': [],
        'tablas_no_accesibles': [],
        'errores': []
    }
    
    # Obtener DATABASE_URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        resultados['errores'].append("DATABASE_URL no está configurada")
        logger.error("❌ DATABASE_URL no está configurada")
        return resultados
    
    logger.info(f"✅ DATABASE_URL encontrada: {DATABASE_URL[:30]}...")
    
    # Manejar encoding de DATABASE_URL
    try:
        parsed = urlparse(DATABASE_URL)
        if parsed.username:
            encoded_username = quote(parsed.username, safe='')
            encoded_password = quote(parsed.password or '', safe='')
            encoded_netloc = f"{encoded_username}:{encoded_password}@{parsed.hostname}"
            if parsed.port:
                encoded_netloc += f":{parsed.port}"
            DATABASE_URL = urlunparse((
                parsed.scheme,
                encoded_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
    except Exception as e:
        logger.warning(f"⚠️ No se pudo procesar DATABASE_URL para encoding: {e}")
    
    # Intentar conectar
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={'client_encoding': 'utf8'},
            pool_pre_ping=True
        )
        
        # Test de conexión básico
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.fetchone():
                resultados['conexion_ok'] = True
                logger.info("✅ Conexión a base de datos exitosa")
        
        # Verificar acceso a tablas principales
        tablas_principales = ['prestamos', 'pagos', 'cuotas', 'clientes']
        
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            for tabla in tablas_principales:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {tabla} LIMIT 1"))
                    count = result.fetchone()[0]
                    resultados['tablas_accesibles'].append({
                        'tabla': tabla,
                        'registros': count
                    })
                    logger.info(f"✅ Tabla '{tabla}': {count:,} registros")
                except Exception as e:
                    resultados['tablas_no_accesibles'].append({
                        'tabla': tabla,
                        'error': str(e)
                    })
                    logger.error(f"❌ Error accediendo tabla '{tabla}': {str(e)}")
        finally:
            db.close()
            
    except Exception as e:
        resultados['errores'].append(f"Error de conexión: {str(e)}")
        logger.error(f"❌ Error conectando a base de datos: {str(e)}")
    
    return resultados


def verificar_configuracion_backend():
    """Verifica la configuración del backend."""
    logger.info("=" * 80)
    logger.info("🔍 VERIFICACIÓN: CONFIGURACIÓN BACKEND")
    logger.info("=" * 80)
    
    resultados = {
        'variables_ok': [],
        'variables_faltantes': [],
        'configuracion_cors': {}
    }
    
    # Verificar variables críticas
    variables_criticas = {
        'DATABASE_URL': 'Conexión a base de datos',
        'SECRET_KEY': 'Clave secreta para JWT',
        'ENVIRONMENT': 'Entorno de ejecución'
    }
    
    for var, descripcion in variables_criticas.items():
        valor = os.getenv(var)
        if valor:
            # Ocultar valores sensibles
            if 'SECRET' in var or 'PASSWORD' in var or 'KEY' in var:
                valor_muestra = valor[:10] + "..." if len(valor) > 10 else "***"
            elif 'DATABASE_URL' in var:
                valor_muestra = valor[:30] + "..." if len(valor) > 30 else valor
            else:
                valor_muestra = valor
            
            resultados['variables_ok'].append({
                'variable': var,
                'descripcion': descripcion,
                'valor': valor_muestra
            })
            logger.info(f"✅ {var}: {valor_muestra}")
        else:
            resultados['variables_faltantes'].append({
                'variable': var,
                'descripcion': descripcion
            })
            logger.warning(f"⚠️ {var} no configurada: {descripcion}")
    
    # Verificar CORS
    try:
        from app.core.config import settings
        cors_origins = settings.CORS_ORIGINS
        resultados['configuracion_cors'] = {
            'origins': cors_origins,
            'allow_credentials': settings.CORS_ALLOW_CREDENTIALS,
            'allow_methods': settings.CORS_ALLOW_METHODS
        }
        logger.info(f"✅ CORS configurado: {len(cors_origins)} origins permitidos")
        for origin in cors_origins:
            logger.info(f"   - {origin}")
    except Exception as e:
        resultados['configuracion_cors']['error'] = str(e)
        logger.error(f"❌ Error obteniendo configuración CORS: {str(e)}")
    
    return resultados


def verificar_configuracion_frontend():
    """Verifica la configuración del frontend."""
    logger.info("=" * 80)
    logger.info("🔍 VERIFICACIÓN: CONFIGURACIÓN FRONTEND")
    logger.info("=" * 80)
    
    resultados = {
        'api_url_configurada': False,
        'api_url': None,
        'archivos_config': {}
    }
    
    # Verificar archivo env.ts
    env_ts_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "config" / "env.ts"
    if env_ts_path.exists():
        contenido = env_ts_path.read_text(encoding='utf-8')
        resultados['archivos_config']['env.ts'] = {
            'existe': True,
            'contiene_api_url': 'API_URL' in contenido or 'VITE_API_URL' in contenido
        }
        logger.info("✅ Archivo env.ts encontrado")
    else:
        resultados['archivos_config']['env.ts'] = {'existe': False}
        logger.warning("⚠️ Archivo env.ts no encontrado")
    
    # Verificar archivo api.ts
    api_ts_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "services" / "api.ts"
    if api_ts_path.exists():
        contenido = api_ts_path.read_text(encoding='utf-8')
        resultados['archivos_config']['api.ts'] = {
            'existe': True,
            'usa_env': 'env.API_URL' in contenido or 'API_BASE_URL' in contenido
        }
        logger.info("✅ Archivo api.ts encontrado")
    else:
        resultados['archivos_config']['api.ts'] = {'existe': False}
        logger.warning("⚠️ Archivo api.ts no encontrado")
    
    # Verificar server.js (proxy)
    server_js_path = Path(__file__).parent.parent.parent / "frontend" / "server.js"
    if server_js_path.exists():
        contenido = server_js_path.read_text(encoding='utf-8')
        tiene_proxy = '/api' in contenido or 'proxy' in contenido.lower()
        resultados['archivos_config']['server.js'] = {
            'existe': True,
            'tiene_proxy': tiene_proxy
        }
        logger.info(f"✅ Archivo server.js encontrado (proxy: {tiene_proxy})")
    else:
        resultados['archivos_config']['server.js'] = {'existe': False}
        logger.warning("⚠️ Archivo server.js no encontrado")
    
    # Verificar variables de entorno del frontend (si existen)
    vite_api_url = os.getenv("VITE_API_URL")
    if vite_api_url:
        resultados['api_url_configurada'] = True
        resultados['api_url'] = vite_api_url
        logger.info(f"✅ VITE_API_URL configurada: {vite_api_url}")
    else:
        logger.info("ℹ️ VITE_API_URL no configurada (usará rutas relativas)")
    
    return resultados


def verificar_endpoints_backend():
    """Verifica que los endpoints principales del backend estén disponibles."""
    logger.info("=" * 80)
    logger.info("🔍 VERIFICACIÓN: ENDPOINTS BACKEND")
    logger.info("=" * 80)
    
    resultados = {
        'endpoints_encontrados': [],
        'endpoints_faltantes': []
    }
    
    # Verificar que los archivos de endpoints principales existan
    endpoints_principales = [
        ('pagos', 'backend/app/api/v1/endpoints/pagos.py'),
        ('prestamos', 'backend/app/api/v1/endpoints/prestamos.py'),
        ('cuotas', 'backend/app/api/v1/endpoints/amortizacion.py'),
        ('clientes', 'backend/app/api/v1/endpoints/clientes.py'),
        ('auth', 'backend/app/api/v1/endpoints/auth.py'),
        ('health', 'backend/app/api/v1/endpoints/health.py'),
    ]
    
    base_path = Path(__file__).parent.parent.parent
    
    for nombre, ruta in endpoints_principales:
        archivo_path = base_path / ruta
        if archivo_path.exists():
            resultados['endpoints_encontrados'].append(nombre)
            logger.info(f"✅ Endpoint '{nombre}' encontrado")
        else:
            resultados['endpoints_faltantes'].append({
                'nombre': nombre,
                'ruta': ruta
            })
            logger.warning(f"⚠️ Endpoint '{nombre}' no encontrado en {ruta}")
    
    return resultados


def main():
    """Función principal de verificación."""
    logger.info("=" * 80)
    logger.info("🚀 INICIANDO VERIFICACIÓN DE CONEXIONES")
    logger.info("=" * 80)
    
    resultados_totales = {
        'backend_bd': {},
        'configuracion_backend': {},
        'configuracion_frontend': {},
        'endpoints_backend': {}
    }
    
    # 1. Verificar Backend -> Base de Datos
    resultados_totales['backend_bd'] = verificar_backend_bd()
    
    # 2. Verificar Configuración Backend
    resultados_totales['configuracion_backend'] = verificar_configuracion_backend()
    
    # 3. Verificar Configuración Frontend
    resultados_totales['configuracion_frontend'] = verificar_configuracion_frontend()
    
    # 4. Verificar Endpoints Backend
    resultados_totales['endpoints_backend'] = verificar_endpoints_backend()
    
    # Resumen final
    logger.info("=" * 80)
    logger.info("📊 RESUMEN DE VERIFICACIÓN")
    logger.info("=" * 80)
    
    # Backend -> BD
    if resultados_totales['backend_bd']['conexion_ok']:
        logger.info("✅ Backend -> Base de Datos: CONECTADO")
        logger.info(f"   Tablas accesibles: {len(resultados_totales['backend_bd']['tablas_accesibles'])}")
    else:
        logger.error("❌ Backend -> Base de Datos: ERROR DE CONEXIÓN")
        for error in resultados_totales['backend_bd']['errores']:
            logger.error(f"   - {error}")
    
    # Configuración Backend
    variables_ok = len(resultados_totales['configuracion_backend']['variables_ok'])
    variables_faltantes = len(resultados_totales['configuracion_backend']['variables_faltantes'])
    if variables_faltantes == 0:
        logger.info(f"✅ Configuración Backend: COMPLETA ({variables_ok} variables)")
    else:
        logger.warning(f"⚠️ Configuración Backend: {variables_faltantes} variables faltantes")
    
    # Configuración Frontend
    archivos_ok = sum(1 for archivo in resultados_totales['configuracion_frontend']['archivos_config'].values() if archivo.get('existe'))
    logger.info(f"✅ Configuración Frontend: {archivos_ok} archivos de configuración encontrados")
    
    # Endpoints
    endpoints_ok = len(resultados_totales['endpoints_backend']['endpoints_encontrados'])
    endpoints_faltantes = len(resultados_totales['endpoints_backend']['endpoints_faltantes'])
    if endpoints_faltantes == 0:
        logger.info(f"✅ Endpoints Backend: TODOS ENCONTRADOS ({endpoints_ok})")
    else:
        logger.warning(f"⚠️ Endpoints Backend: {endpoints_faltantes} endpoints faltantes")
    
    logger.info("=" * 80)
    
    # Determinar estado general
    estado_general = "✅ CORRECTO"
    if not resultados_totales['backend_bd']['conexion_ok']:
        estado_general = "❌ ERROR CRÍTICO"
    elif variables_faltantes > 0 or endpoints_faltantes > 0:
        estado_general = "⚠️ ADVERTENCIAS"
    
    logger.info(f"ESTADO GENERAL: {estado_general}")
    logger.info("=" * 80)
    
    return resultados_totales


if __name__ == "__main__":
    main()
