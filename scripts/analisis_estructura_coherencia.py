"""
Script de análisis de estructura de columnas y coherencia entre tablas y endpoints
Revisa:
1. Estructura de columnas de cada tabla
2. Relaciones entre tablas (Foreign Keys)
3. Coherencia entre modelos ORM y endpoints
4. Uso correcto de columnas en endpoints
"""

import sys
from pathlib import Path
from collections import defaultdict

# Agregar el directorio raíz y backend al path para importar módulos
root_dir = Path(__file__).parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from datetime import datetime
# import importlib
# import inspect as py_inspect

def print_section(title: str):
    """Imprime un separador de sección"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_subsection(title: str):
    """Imprime un separador de subsección"""
    print(f"\n--- {title} ---")

def safe_print(text: str):
    """Imprime texto de forma segura manejando encoding"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback: reemplazar caracteres problemáticos
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)

def analizar_estructura_tablas(db):
    """Analiza la estructura de columnas de todas las tablas"""
    print_section("1. ESTRUCTURA DE COLUMNAS DE TABLAS")
    
    inspector = inspect(db.bind)
    tablas_principales = ['clientes', 'prestamos', 'pagos', 'cuotas']
    
    estructuras = {}
    
    for tabla_nombre in tablas_principales:
        if tabla_nombre not in inspector.get_table_names():
            print(f"ADVERTENCIA: Tabla '{tabla_nombre}' no existe en la base de datos")
            continue
            
        print_subsection(f"Tabla: {tabla_nombre}")
        
        # Obtener columnas de la tabla
        columnas = inspector.get_columns(tabla_nombre)
        foreign_keys = inspector.get_foreign_keys(tabla_nombre)
        indexes = inspector.get_indexes(tabla_nombre)
        primary_keys = inspector.get_pk_constraint(tabla_nombre)
        
        estructuras[tabla_nombre] = {
            'columnas': columnas,
            'foreign_keys': foreign_keys,
            'indexes': indexes,
            'primary_keys': primary_keys
        }
        
        print(f"Total de columnas: {len(columnas)}")
        print(f"Foreign Keys: {len(foreign_keys)}")
        print(f"Indices: {len(indexes)}")
        
        # Mostrar columnas principales
        print("\nColumnas principales:")
        for col in columnas[:15]:  # Mostrar primeras 15
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            tipo = str(col['type'])
            default = f" DEFAULT {col['default']}" if col.get('default') else ""
            print(f"   - {col['name']}: {tipo} {nullable}{default}")
        
        if len(columnas) > 15:
            print(f"   ... y {len(columnas) - 15} columnas más")
        
        # Mostrar Foreign Keys
        if foreign_keys:
            print("\nForeign Keys:")
            for fk in foreign_keys:
                print(f"   - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        
        # Mostrar índices importantes
        if indexes:
            print("\nIndices:")
            for idx in indexes[:5]:  # Mostrar primeros 5
                unique = "UNIQUE" if idx.get('unique', False) else ""
                # Filtrar valores None de column_names
                col_names = idx.get('column_names', [])
                cols = ", ".join(str(c) for c in col_names if c is not None)
                idx_name = idx.get('name', 'sin_nombre')
                print(f"   - {idx_name}: {cols} {unique}")
    
    return estructuras

def analizar_modelos_orm():
    """Analiza los modelos ORM y sus columnas"""
    print_section("2. ESTRUCTURA DE MODELOS ORM")
    
    modelos = {
        'Cliente': Cliente,
        'Prestamo': Prestamo,
        'Pago': Pago,
        'Cuota': Cuota
    }
    
    estructuras_orm = {}
    
    for nombre_modelo, modelo in modelos.items():
        print_subsection(f"Modelo: {nombre_modelo}")
        
        # Obtener información del modelo
        tabla_nombre = modelo.__tablename__
        columnas_orm = []
        relaciones_orm = []
        
        # Obtener columnas del modelo
        for attr_name in dir(modelo):
            attr = getattr(modelo, attr_name)
            if hasattr(attr, 'property') and hasattr(attr.property, 'columns'):
                # Es una columna
                col_info = {
                    'name': attr_name,
                    'type': str(attr.property.columns[0].type),
                    'nullable': attr.property.columns[0].nullable,
                    'primary_key': attr.property.columns[0].primary_key,
                    'foreign_key': bool(attr.property.columns[0].foreign_keys)
                }
                columnas_orm.append(col_info)
            elif hasattr(attr, 'property') and hasattr(attr.property, 'mapper'):
                # Es una relación
                relaciones_orm.append({
                    'name': attr_name,
                    'target': str(attr.property.mapper.class_.__name__)
                })
        
        estructuras_orm[nombre_modelo] = {
            'tabla': tabla_nombre,
            'columnas': columnas_orm,
            'relaciones': relaciones_orm
        }
        
        print(f"Tabla: {tabla_nombre}")
        print(f"Columnas en modelo: {len(columnas_orm)}")
        print(f"Relaciones: {len(relaciones_orm)}")
        
        if relaciones_orm:
            print("\nRelaciones ORM:")
            for rel in relaciones_orm:
                print(f"   - {rel['name']} -> {rel['target']}")
    
    return estructuras_orm

def comparar_estructuras_bd_orm(db, estructuras_bd, estructuras_orm):
    """Compara la estructura de BD con los modelos ORM"""
    print_section("3. COMPARACIÓN BD vs MODELOS ORM")
    
    problemas = []
    
    # Mapeo de tablas a modelos
    tabla_modelo_map = {
        'clientes': 'Cliente',
        'prestamos': 'Prestamo',
        'pagos': 'Pago',
        'cuotas': 'Cuota'
    }
    
    for tabla_nombre, modelo_nombre in tabla_modelo_map.items():
        if tabla_nombre not in estructuras_bd:
            continue
            
        if modelo_nombre not in estructuras_orm:
            problemas.append(f"ERROR: Modelo {modelo_nombre} no encontrado en codigo")
            continue
        
        print_subsection(f"Comparación: {tabla_nombre} vs {modelo_nombre}")
        
        columnas_bd = {col['name']: col for col in estructuras_bd[tabla_nombre]['columnas']}
        columnas_orm = {col['name']: col for col in estructuras_orm[modelo_nombre]['columnas']}
        
        # Columnas en BD pero no en modelo ORM
        columnas_faltantes_orm = set(columnas_bd.keys()) - set(columnas_orm.keys())
        if columnas_faltantes_orm:
            print(f"ADVERTENCIA: Columnas en BD pero NO en modelo ORM ({len(columnas_faltantes_orm)}):")
            for col in sorted(columnas_faltantes_orm):
                print(f"   - {col}")
            problemas.append(f"ADVERTENCIA {tabla_nombre}: {len(columnas_faltantes_orm)} columnas en BD sin modelo ORM")
        
        # Columnas en modelo ORM pero no en BD
        columnas_faltantes_bd = set(columnas_orm.keys()) - set(columnas_bd.keys())
        if columnas_faltantes_bd:
            print(f"ERROR: Columnas en modelo ORM pero NO en BD ({len(columnas_faltantes_bd)}):")
            for col in sorted(columnas_faltantes_bd):
                print(f"   - {col}")
            problemas.append(f"ERROR {tabla_nombre}: {len(columnas_faltantes_bd)} columnas en modelo sin BD")
        
        # Verificar tipos de datos
        print(f"\nOK: Columnas coincidentes: {len(set(columnas_bd.keys()) & set(columnas_orm.keys()))}")
        
        if not columnas_faltantes_orm and not columnas_faltantes_bd:
            print("OK: La estructura coincide perfectamente")
    
    return problemas

def analizar_relaciones_tablas(db):
    """Analiza las relaciones entre tablas"""
    print_section("4. ANÁLISIS DE RELACIONES ENTRE TABLAS")
    
    inspector = inspect(db.bind)
    
    # Mapeo de relaciones esperadas
    relaciones_esperadas = {
        'prestamos': [
            {'columna': 'cliente_id', 'tabla_ref': 'clientes', 'columna_ref': 'id'},
            {'columna': 'concesionario_id', 'tabla_ref': 'concesionarios', 'columna_ref': 'id'},
            {'columna': 'analista_id', 'tabla_ref': 'analistas', 'columna_ref': 'id'},
            {'columna': 'modelo_vehiculo_id', 'tabla_ref': 'modelos_vehiculos', 'columna_ref': 'id'},
        ],
        'pagos': [
            {'columna': 'cliente_id', 'tabla_ref': 'clientes', 'columna_ref': 'id'},
            {'columna': 'prestamo_id', 'tabla_ref': 'prestamos', 'columna_ref': 'id'},
        ],
        'cuotas': [
            {'columna': 'prestamo_id', 'tabla_ref': 'prestamos', 'columna_ref': 'id'},
        ]
    }
    
    problemas_relaciones = []
    
    for tabla_nombre, relaciones in relaciones_esperadas.items():
        if tabla_nombre not in inspector.get_table_names():
            continue
        
        print_subsection(f"Relaciones de tabla: {tabla_nombre}")
        
        foreign_keys_reales = inspector.get_foreign_keys(tabla_nombre)
        fk_map = {}
        for fk in foreign_keys_reales:
            col = fk['constrained_columns'][0]
            fk_map[col] = {
                'tabla_ref': fk['referred_table'],
                'columna_ref': fk['referred_columns'][0]
            }
        
        for rel_esperada in relaciones:
            col = rel_esperada['columna']
            tabla_ref = rel_esperada['tabla_ref']
            col_ref = rel_esperada['columna_ref']
            
            if col in fk_map:
                fk_real = fk_map[col]
                if fk_real['tabla_ref'] == tabla_ref and fk_real['columna_ref'] == col_ref:
                    print(f"OK: {col} -> {tabla_ref}.{col_ref} (correcto)")
                else:
                    print(f"ADVERTENCIA: {col} -> {fk_real['tabla_ref']}.{fk_real['columna_ref']} (esperado: {tabla_ref}.{col_ref})")
                    problemas_relaciones.append(f"{tabla_nombre}.{col}: FK incorrecta")
            else:
                print(f"ERROR: {col} -> {tabla_ref}.{col_ref} (FALTA Foreign Key)")
                problemas_relaciones.append(f"{tabla_nombre}.{col}: Falta FK")
    
    return problemas_relaciones

def analizar_coherencia_endpoints(db):
    """Analiza la coherencia entre endpoints y estructura de datos"""
    print_section("5. COHERENCIA ENTRE ENDPOINTS Y ESTRUCTURA DE DATOS")
    
    # Verificar uso de columnas en endpoints principales
    endpoints_verificar = {
        'prestamos': {
            'archivo': 'backend/app/api/v1/endpoints/prestamos.py',
            'endpoints': ['buscar_prestamos_por_cedula', 'listar_prestamos', 'crear_prestamo'],
            'columnas_criticas': ['cedula', 'cliente_id', 'estado', 'total_financiamiento']
        },
        'pagos': {
            'archivo': 'backend/app/api/v1/endpoints/pagos.py',
            'endpoints': ['listar_pagos', 'crear_pago'],
            'columnas_criticas': ['cedula', 'prestamo_id', 'monto_pagado', 'fecha_pago']
        },
        'cuotas': {
            'archivo': 'backend/app/api/v1/endpoints/amortizacion.py',
            'endpoints': ['obtener_cuotas_multiples_prestamos', 'obtener_cuotas_prestamo'],
            'columnas_criticas': ['prestamo_id', 'numero_cuota', 'estado', 'total_pagado']
        }
    }
    
    problemas_endpoints = []
    
    for modulo_nombre, info in endpoints_verificar.items():
        print_subsection(f"Módulo: {modulo_nombre}")
        
        archivo_path = Path(root_dir) / info['archivo']
        if not archivo_path.exists():
            print(f"ADVERTENCIA: Archivo no encontrado: {info['archivo']}")
            continue
        
        # Leer archivo y buscar uso de columnas
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            print(f"Archivo: {info['archivo']}")
            
            # Verificar que se usen las columnas críticas
            columnas_encontradas = []
            columnas_faltantes = []
            
            for columna in info['columnas_criticas']:
                # Buscar uso de la columna en el código
                patrones = [
                    f".{columna}",  # objeto.columna
                    f"Prestamo.{columna}",  # Prestamo.columna
                    f"Pago.{columna}",  # Pago.columna
                    f"Cuota.{columna}",  # Cuota.columna
                    f"Cliente.{columna}",  # Cliente.columna
                    f"'{columna}'",  # 'columna' en strings
                    f'"{columna}"',  # "columna" en strings
                ]
                
                encontrado = any(patron in contenido for patron in patrones)
                if encontrado:
                    columnas_encontradas.append(columna)
                else:
                    columnas_faltantes.append(columna)
            
            if columnas_encontradas:
                print(f"OK: Columnas usadas: {', '.join(columnas_encontradas)}")
            
            if columnas_faltantes:
                print(f"ADVERTENCIA: Columnas criticas no encontradas en codigo: {', '.join(columnas_faltantes)}")
                problemas_endpoints.append(f"{modulo_nombre}: Columnas no usadas: {', '.join(columnas_faltantes)}")
            else:
                print("OK: Todas las columnas criticas estan siendo usadas")
                
        except Exception as e:
            print(f"ERROR: Error al leer archivo: {e}")
            problemas_endpoints.append(f"{modulo_nombre}: Error al analizar archivo")
    
    return problemas_endpoints

def analizar_coherencia_cedulas(db):
    """Analiza la coherencia en el uso de cédulas entre tablas"""
    print_section("6. COHERENCIA EN USO DE CÉDULAS ENTRE TABLAS")
    
    problemas_cedulas = []
    
    # Verificar que las cédulas en préstamos existan en clientes
    print_subsection("Cédulas en préstamos vs clientes")
    cedulas_prestamos_sin_cliente = db.execute(text("""
        SELECT DISTINCT p.cedula, COUNT(*) as cantidad_prestamos
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
        WHERE c.id IS NULL
        GROUP BY p.cedula
        ORDER BY cantidad_prestamos DESC
        LIMIT 10
    """)).fetchall()
    
    if cedulas_prestamos_sin_cliente:
        print(f"ERROR: Se encontraron {len(cedulas_prestamos_sin_cliente)} cedulas en prestamos sin cliente activo:")
        for cedula, cantidad in cedulas_prestamos_sin_cliente:
            print(f"   - Cédula {cedula}: {cantidad} préstamos")
        problemas_cedulas.append(f"{len(cedulas_prestamos_sin_cliente)} cédulas en préstamos sin cliente")
    else:
        print("OK: Todas las cedulas de prestamos tienen cliente activo")
    
    # Verificar que las cédulas en pagos existan en clientes
    print_subsection("Cédulas en pagos vs clientes")
    cedulas_pagos_sin_cliente = db.execute(text("""
        SELECT DISTINCT p.cedula, COUNT(*) as cantidad_pagos
        FROM pagos p
        LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
        WHERE p.activo = TRUE AND c.id IS NULL
        GROUP BY p.cedula
        ORDER BY cantidad_pagos DESC
        LIMIT 10
    """)).fetchall()
    
    if cedulas_pagos_sin_cliente:
        print(f"❌ Se encontraron {len(cedulas_pagos_sin_cliente)} cédulas en pagos sin cliente activo:")
        for cedula, cantidad in cedulas_pagos_sin_cliente:
            print(f"   - Cédula {cedula}: {cantidad} pagos")
        problemas_cedulas.append(f"{len(cedulas_pagos_sin_cliente)} cédulas en pagos sin cliente")
    else:
        print("OK: Todas las cedulas de pagos tienen cliente activo")
    
    # Verificar coherencia entre cliente_id y cedula en préstamos
    print_subsection("Coherencia cliente_id vs cedula en préstamos")
    prestamos_incoherentes = db.execute(text("""
        SELECT p.id, p.cedula, p.cliente_id, c.cedula as cedula_cliente
        FROM prestamos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE c.id IS NULL OR p.cedula != c.cedula
        LIMIT 10
    """)).fetchall()
    
    if prestamos_incoherentes:
        print(f"❌ Se encontraron {len(prestamos_incoherentes)} préstamos con inconsistencia cliente_id/cedula:")
        for prestamo_id, cedula_prestamo, cliente_id, cedula_cliente in prestamos_incoherentes:
            if cliente_id is None:
                print(f"   - Préstamo ID {prestamo_id}: cliente_id={cliente_id} (NULL)")
            else:
                print(f"   - Préstamo ID {prestamo_id}: cedula_prestamo={cedula_prestamo}, cedula_cliente={cedula_cliente}")
        problemas_cedulas.append(f"{len(prestamos_incoherentes)} préstamos con inconsistencia cliente_id/cedula")
    else:
        print("OK: Todos los prestamos tienen coherencia entre cliente_id y cedula")
    
    # Verificar coherencia entre cliente_id y cedula en pagos
    print_subsection("Coherencia cliente_id vs cedula en pagos")
    pagos_incoherentes = db.execute(text("""
        SELECT p.id, p.cedula, p.cliente_id, c.cedula as cedula_cliente
        FROM pagos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.activo = TRUE AND (c.id IS NULL OR p.cedula != c.cedula)
        LIMIT 10
    """)).fetchall()
    
    if pagos_incoherentes:
        print(f"⚠️  Se encontraron {len(pagos_incoherentes)} pagos con inconsistencia cliente_id/cedula:")
        print("   (Nota: cliente_id puede ser NULL en pagos, esto es normal)")
        for pago_id, cedula_pago, cliente_id, cedula_cliente in pagos_incoherentes[:5]:
            if cliente_id is None:
                print(f"   - Pago ID {pago_id}: cliente_id={cliente_id} (NULL) - cédula={cedula_pago}")
            else:
                print(f"   - Pago ID {pago_id}: cedula_pago={cedula_pago}, cedula_cliente={cedula_cliente}")
    else:
        print("OK: Todos los pagos tienen coherencia entre cliente_id y cedula")
    
    return problemas_cedulas

def analizar_procesos_negocio(db):
    """Analiza la coherencia de los procesos de negocio"""
    print_section("7. COHERENCIA DE PROCESOS DE NEGOCIO")
    
    problemas_procesos = []
    
    # Proceso 1: Préstamo aprobado debe tener cuotas
    print_subsection("Proceso: Préstamo aprobado → Cuotas generadas")
    prestamos_aprobados_sin_cuotas = db.execute(text("""
        SELECT p.id, p.cedula, p.numero_cuotas, p.fecha_aprobacion
        FROM prestamos p
        LEFT JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO' AND c.id IS NULL
        ORDER BY p.fecha_aprobacion DESC
        LIMIT 10
    """)).fetchall()
    
    if prestamos_aprobados_sin_cuotas:
        print(f"❌ Se encontraron {len(prestamos_aprobados_sin_cuotas)} préstamos aprobados sin cuotas:")
        for prestamo_id, cedula, num_cuotas, fecha_aprob in prestamos_aprobados_sin_cuotas:
            print(f"   - Préstamo ID {prestamo_id} (Cédula: {cedula}, Cuotas esperadas: {num_cuotas}, Aprobado: {fecha_aprob})")
        problemas_procesos.append(f"{len(prestamos_aprobados_sin_cuotas)} préstamos aprobados sin cuotas")
    else:
        print("OK: Todos los prestamos aprobados tienen cuotas generadas")
    
    # Proceso 2: Cuotas deben tener préstamo válido
    print_subsection("Proceso: Cuota → Préstamo válido")
    cuotas_sin_prestamo_valido = db.execute(text("""
        SELECT c.id, c.prestamo_id, c.numero_cuota
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL OR p.estado != 'APROBADO'
        LIMIT 10
    """)).fetchall()
    
    if cuotas_sin_prestamo_valido:
        print(f"⚠️  Se encontraron {len(cuotas_sin_prestamo_valido)} cuotas con préstamo inválido o no aprobado:")
        for cuota_id, prestamo_id, numero in cuotas_sin_prestamo_valido:
            print(f"   - Cuota ID {cuota_id} (Préstamo ID: {prestamo_id}, Cuota #: {numero})")
        problemas_procesos.append(f"{len(cuotas_sin_prestamo_valido)} cuotas con préstamo inválido")
    else:
        print("OK: Todas las cuotas tienen prestamo valido y aprobado")
    
    # Proceso 3: Pagos deben estar relacionados con préstamos aprobados
    print_subsection("Proceso: Pago → Préstamo aprobado")
    pagos_sin_prestamo_aprobado = db.execute(text("""
        SELECT DISTINCT p.cedula, COUNT(*) as cantidad_pagos, SUM(p.monto_pagado) as total
        FROM pagos p
        LEFT JOIN prestamos pr ON p.cedula = pr.cedula AND pr.estado = 'APROBADO'
        WHERE p.activo = TRUE AND pr.id IS NULL
        GROUP BY p.cedula
        ORDER BY cantidad_pagos DESC
        LIMIT 10
    """)).fetchall()
    
    if pagos_sin_prestamo_aprobado:
        print(f"⚠️  Se encontraron {len(pagos_sin_prestamo_aprobado)} cédulas con pagos pero sin préstamos aprobados:")
        for cedula, cantidad, total in pagos_sin_prestamo_aprobado:
            print(f"   - Cédula {cedula}: {cantidad} pagos, Total: ${total:,.2f}")
        problemas_procesos.append(f"{len(pagos_sin_prestamo_aprobado)} cédulas con pagos sin préstamos aprobados")
    else:
        print("OK: Todos los pagos estan relacionados con prestamos aprobados")
    
    return problemas_procesos

def main():
    """Función principal"""
    import os
    import sys
    
    # Configurar encoding UTF-8 para Windows
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    
    print("\n" + "="*80)
    print("  ANALISIS DE ESTRUCTURA Y COHERENCIA")
    print("  Sistema de Prestamos y Pagos")
    print("="*80)
    print(f"\nFecha de analisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        db_url = settings.DATABASE_URL
        db_info = db_url.split('@')[-1] if '@' in db_url else 'N/A'
        print(f"Base de datos: {db_info}")
    except Exception:
        print("Base de datos: N/A (error al obtener URL)")
    
    # Crear conexión a la base de datos usando el mismo método que backend/app/db/session.py
    try:
        import os
        from urllib.parse import urlparse, urlunparse, quote_plus
        
        # Intentar cargar desde .env si existe
        try:
            from dotenv import load_dotenv
            env_file = root_dir / ".env"
            if not env_file.exists():
                env_file = backend_dir / ".env"
            if env_file.exists():
                load_dotenv(env_file, override=False)
        except ImportError:
            pass
        
        # Obtener URL desde variable de entorno o settings
        db_url_raw = os.getenv("DATABASE_URL", str(settings.DATABASE_URL))
        
        # Manejar encoding de la URL (mismo método que session.py)
        try:
            # Intentar parsear la URL
            parsed = urlparse(db_url_raw)
            
            # Codificar username y password si existen
            username = quote_plus(parsed.username) if parsed.username else None
            password = quote_plus(parsed.password) if parsed.password else None
            
            # Reconstruir netloc
            if username and password:
                netloc = f"{username}:{password}@{parsed.hostname}"
            elif username:
                netloc = f"{username}@{parsed.hostname}"
            else:
                netloc = parsed.hostname
            
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            
            # Reconstruir URL completa
            db_url = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        except Exception as parse_error:
            # Si falla el parseo, usar la URL original
            print(f"ADVERTENCIA: No se pudo parsear URL: {parse_error}")
            db_url = db_url_raw
        
        # Crear engine
        engine = create_engine(
            db_url, 
            pool_pre_ping=True, 
            connect_args={
                "connect_timeout": 10,
                "client_encoding": "utf8"
            }
        )
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
    except UnicodeDecodeError as e:
        print(f"\nERROR: Problema de encoding en URL de conexion")
        print("La URL contiene caracteres especiales que no se pueden decodificar")
        print("Sugerencia: Configura DATABASE_URL como variable de entorno y codifica la contraseña usando urllib.parse.quote_plus()")
        print("Ejemplo: from urllib.parse import quote_plus; password_encoded = quote_plus('tu_password')")
        return
    except Exception as e:
        error_msg = str(e)
        if "UnicodeDecodeError" in error_msg or "codec" in error_msg.lower():
            print(f"\nERROR: Problema de encoding al conectar a la base de datos")
            print("La URL de conexion contiene caracteres especiales que no se pueden decodificar")
            print("Sugerencia: Configura DATABASE_URL como variable de entorno y codifica la contraseña usando urllib.parse.quote_plus()")
        else:
            print(f"\nERROR: No se pudo conectar a la base de datos: {error_msg}")
            print("Verifica que la base de datos este disponible y que DATABASE_URL este configurado correctamente.")
        return
    
    try:
        # Ejecutar análisis
        estructuras_bd = analizar_estructura_tablas(db)
        estructuras_orm = analizar_modelos_orm()
        problemas_bd_orm = comparar_estructuras_bd_orm(db, estructuras_bd, estructuras_orm)
        problemas_relaciones = analizar_relaciones_tablas(db)
        problemas_endpoints = analizar_coherencia_endpoints(db)
        problemas_cedulas = analizar_coherencia_cedulas(db)
        problemas_procesos = analizar_procesos_negocio(db)
        
        # Resumen final
        print_section("RESUMEN FINAL")
        
        todos_problemas = problemas_bd_orm + problemas_relaciones + problemas_endpoints + problemas_cedulas + problemas_procesos
        
        print("ESTADISTICAS:")
        print(f"   - Problemas BD vs ORM: {len(problemas_bd_orm)}")
        print(f"   - Problemas de relaciones: {len(problemas_relaciones)}")
        print(f"   - Problemas en endpoints: {len(problemas_endpoints)}")
        print(f"   - Problemas de cedulas: {len(problemas_cedulas)}")
        print(f"   - Problemas de procesos: {len(problemas_procesos)}")
        print(f"   - TOTAL DE PROBLEMAS: {len(todos_problemas)}")
        
        if todos_problemas:
            print("\nADVERTENCIA: Problemas encontrados:")
            for i, problema in enumerate(todos_problemas, 1):
                print(f"   {i}. {problema}")
        else:
            print("\nOK: No se encontraron problemas de coherencia")
        
        print("\n" + "="*80)
        print("  Análisis completado")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\nERROR: Error durante el analisis: {str(e)}")
        import traceback
        try:
            traceback.print_exc()
        except UnicodeEncodeError:
            # Fallback para Windows sin UTF-8
            print("Error detallado no disponible debido a problemas de encoding")
    finally:
        try:
            db.close()
        except:
            pass

if __name__ == "__main__":
    main()
