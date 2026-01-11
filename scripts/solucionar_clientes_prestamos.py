"""
Script para resolver el problema de cédulas en préstamos sin cliente activo
Opción A: Activar clientes existentes inactivos
Opción B: Crear clientes básicos para préstamos huérfanos
Opción C: Marcar préstamos como históricos
"""

import sys
from pathlib import Path

# Agregar el directorio raíz y backend al path para importar módulos
root_dir = Path(__file__).parent.parent
backend_dir = root_dir / "backend"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.prestamo import Prestamo
from app.models.cliente import Cliente
from datetime import datetime

def print_section(title: str):
    """Imprime un separador de sección"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def obtener_cedulas_problema(db):
    """Obtiene las cédulas en préstamos sin cliente activo"""
    resultado = db.execute(text("""
        SELECT DISTINCT p.cedula, COUNT(*) as cantidad_prestamos
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
        WHERE c.id IS NULL
        GROUP BY p.cedula
        ORDER BY cantidad_prestamos DESC
    """)).fetchall()
    
    return [(cedula, cantidad) for cedula, cantidad in resultado]

def verificar_clientes_inactivos(db, cedulas):
    """Verifica si existen clientes inactivos con estas cédulas"""
    if not cedulas:
        return []
    
    cedulas_str = "', '".join(cedulas)
    resultado = db.execute(text(f"""
        SELECT cedula, activo, nombres, COUNT(*) as cantidad
        FROM clientes 
        WHERE cedula IN ('{cedulas_str}')
        GROUP BY cedula, activo, nombres
        ORDER BY cedula
    """)).fetchall()
    
    return resultado

def activar_clientes_inactivos(db, cedulas, dry_run=True):
    """Activa clientes inactivos con las cédulas proporcionadas"""
    if not cedulas:
        return 0
    
    cedulas_str = "', '".join(cedulas)
    
    if dry_run:
        print("DRY RUN: Se activarían los siguientes clientes:")
        clientes = db.execute(text(f"""
            SELECT id, cedula, nombres, activo, fecha_registro
            FROM clientes
            WHERE cedula IN ('{cedulas_str}') AND activo = FALSE
        """)).fetchall()
        
        for cliente_id, cedula, nombres, activo, fecha_registro in clientes:
            print(f"   - ID {cliente_id}: {cedula} - {nombres} (Registrado: {fecha_registro})")
        
        return len(clientes)
    else:
        resultado = db.execute(text(f"""
            UPDATE clientes 
            SET activo = TRUE, 
                fecha_actualizacion = CURRENT_TIMESTAMP,
                estado = 'ACTIVO'
            WHERE cedula IN ('{cedulas_str}') AND activo = FALSE
            RETURNING id, cedula, nombres
        """))
        
        actualizados = resultado.fetchall()
        db.commit()
        
        print(f"Clientes activados: {len(actualizados)}")
        for cliente_id, cedula, nombres in actualizados:
            print(f"   - ID {cliente_id}: {cedula} - {nombres}")
        
        return len(actualizados)

def crear_clientes_faltantes(db, prestamos_info, dry_run=True):
    """Crea clientes básicos para préstamos huérfanos"""
    if not prestamos_info:
        return 0
    
    creados = 0
    
    for cedula, nombres_prestamo in prestamos_info:
        # Verificar si ya existe un cliente (aunque esté inactivo)
        cliente_existente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        
        if cliente_existente:
            print(f"Cliente ya existe para cédula {cedula} (ID: {cliente_existente.id})")
            continue
        
        if dry_run:
            print(f"DRY RUN: Se crearía cliente para cédula {cedula} - {nombres_prestamo}")
            creados += 1
        else:
            nuevo_cliente = Cliente(
                cedula=cedula,
                nombres=nombres_prestamo or f"Cliente {cedula}",
                telefono="+589999999999",
                email="buscaremail@noemail.com",
                direccion="Actualizar dirección",
                fecha_nacimiento=datetime(2000, 1, 1).date(),
                ocupacion="Actualizar ocupación",
                estado="ACTIVO",
                activo=True,
                fecha_registro=datetime.now(),
                usuario_registro="sistema@rapicreditca.com",
                notas=f"Cliente creado automáticamente para préstamo existente"
            )
            
            db.add(nuevo_cliente)
            db.commit()
            db.refresh(nuevo_cliente)
            
            print(f"Cliente creado: ID {nuevo_cliente.id} - {cedula} - {nombres_prestamo}")
            creados += 1
    
    return creados

def marcar_prestamos_historicos(db, cedulas, dry_run=True):
    """Marca préstamos como históricos si no se pueden vincular"""
    if not cedulas:
        return 0
    
    cedulas_str = "', '".join(cedulas)
    
    if dry_run:
        prestamos = db.execute(text(f"""
            SELECT id, cedula, nombres, estado, fecha_registro
            FROM prestamos
            WHERE cedula IN ('{cedulas_str}')
            ORDER BY fecha_registro DESC
        """)).fetchall()
        
        print(f"DRY RUN: Se marcarían {len(prestamos)} préstamos como HISTORICO")
        for prestamo_id, cedula, nombres, estado, fecha_registro in prestamos[:5]:
            print(f"   - Préstamo ID {prestamo_id}: {cedula} - {nombres} ({estado}, {fecha_registro})")
        
        return len(prestamos)
    else:
        resultado = db.execute(text(f"""
            UPDATE prestamos 
            SET estado = 'HISTORICO',
                observaciones = COALESCE(observaciones, '') || ' - Cliente no encontrado (marcado automáticamente)'
            WHERE cedula IN ('{cedulas_str}')
            RETURNING id, cedula
        """))
        
        actualizados = resultado.fetchall()
        db.commit()
        
        print(f"Préstamos marcados como HISTORICO: {len(actualizados)}")
        return len(actualizados)

def main():
    """Función principal"""
    import os
    
    # Configurar encoding UTF-8 para Windows
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    
    print_section("SOLUCIONAR CLIENTES FALTANTES EN PRESTAMOS")
    
    # Conectar a BD
    try:
        from urllib.parse import urlparse, urlunparse, quote_plus
        from dotenv import load_dotenv
        
        env_file = root_dir / ".env"
        if not env_file.exists():
            env_file = backend_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)
        
        db_url_raw = os.getenv("DATABASE_URL", str(settings.DATABASE_URL))
        
        parsed = urlparse(db_url_raw)
        username = quote_plus(parsed.username) if parsed.username else None
        password = quote_plus(parsed.password) if parsed.password else None
        
        if username and password:
            netloc = f"{username}:{password}@{parsed.hostname}"
        elif username:
            netloc = f"{username}@{parsed.hostname}"
        else:
            netloc = parsed.hostname
        
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        
        db_url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
    except Exception as e:
        print(f"ERROR: No se pudo conectar a la base de datos: {str(e)}")
        return
    
    try:
        # Obtener cédulas con problema
        print("Buscando cédulas en préstamos sin cliente activo...")
        cedulas_problema = obtener_cedulas_problema(db)
        
        if not cedulas_problema:
            print("OK: No se encontraron cédulas con problema")
            return
        
        cedulas = [cedula for cedula, _ in cedulas_problema]
        print(f"Se encontraron {len(cedulas)} cédulas con problema:")
        for cedula, cantidad in cedulas_problema:
            print(f"   - {cedula}: {cantidad} préstamos")
        
        # Verificar clientes inactivos
        print("\nVerificando clientes inactivos...")
        clientes_inactivos = verificar_clientes_inactivos(db, cedulas)
        
        if clientes_inactivos:
            print(f"Se encontraron {len(clientes_inactivos)} clientes inactivos:")
            for cedula, activo, nombres, cantidad in clientes_inactivos:
                print(f"   - {cedula}: {nombres} (activo={activo})")
        
        # Obtener información de préstamos para crear clientes
        prestamos_info = db.execute(text(f"""
            SELECT DISTINCT cedula, nombres
            FROM prestamos
            WHERE cedula IN ('{"', '".join(cedulas)}')
        """)).fetchall()
        
        print("\n" + "="*80)
        print("OPCIONES DE SOLUCION:")
        print("="*80)
        print("\n1. ACTIVAR CLIENTES INACTIVOS (Recomendado)")
        print("2. CREAR CLIENTES FALTANTES")
        print("3. MARCAR PRESTAMOS COMO HISTORICOS")
        print("4. VER SOLO (DRY RUN)")
        
        opcion = input("\nSeleccione opción (1-4) o Enter para salir: ").strip()
        
        if opcion == "1":
            print("\nActivando clientes inactivos...")
            activar_clientes_inactivos(db, cedulas, dry_run=False)
        elif opcion == "2":
            print("\nCreando clientes faltantes...")
            crear_clientes_faltantes(db, prestamos_info, dry_run=False)
        elif opcion == "3":
            print("\nMarcando préstamos como históricos...")
            marcar_prestamos_historicos(db, cedulas, dry_run=False)
        elif opcion == "4":
            print("\n=== DRY RUN - ACTIVAR CLIENTES ===")
            activar_clientes_inactivos(db, cedulas, dry_run=True)
            print("\n=== DRY RUN - CREAR CLIENTES ===")
            crear_clientes_faltantes(db, prestamos_info, dry_run=True)
            print("\n=== DRY RUN - MARCAR HISTORICOS ===")
            marcar_prestamos_historicos(db, cedulas, dry_run=True)
        else:
            print("Operación cancelada")
            return
        
        # Validar resultado
        print("\n" + "="*80)
        print("VALIDACION FINAL")
        print("="*80)
        cedulas_restantes = obtener_cedulas_problema(db)
        if cedulas_restantes:
            print(f"ADVERTENCIA: Aún quedan {len(cedulas_restantes)} cédulas con problema")
        else:
            print("OK: Todas las cédulas tienen cliente activo")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
