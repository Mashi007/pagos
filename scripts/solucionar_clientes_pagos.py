"""
Script para resolver el problema de cédulas en pagos sin cliente activo
Similar a solucionar_clientes_prestamos.py pero para pagos
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
from app.models.cliente import Cliente
from datetime import datetime

def print_section(title: str):
    """Imprime un separador de sección"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def obtener_cedulas_problema(db):
    """Obtiene las cédulas en pagos sin cliente activo"""
    resultado = db.execute(text("""
        SELECT DISTINCT p.cedula, COUNT(*) as cantidad_pagos, SUM(p.monto_pagado) as total
        FROM pagos p
        LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
        WHERE p.activo = TRUE AND c.id IS NULL
        GROUP BY p.cedula
        ORDER BY cantidad_pagos DESC
    """)).fetchall()
    
    return [(cedula, cantidad, total) for cedula, cantidad, total in resultado]

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

def crear_clientes_faltantes(db, pagos_info, dry_run=True):
    """Crea clientes básicos para pagos huérfanos"""
    if not pagos_info:
        return 0
    
    creados = 0
    
    for cedula, nombres_pago in pagos_info:
        # Verificar si ya existe un cliente (aunque esté inactivo)
        cliente_existente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        
        if cliente_existente:
            print(f"Cliente ya existe para cédula {cedula} (ID: {cliente_existente.id})")
            continue
        
        if dry_run:
            print(f"DRY RUN: Se crearía cliente para cédula {cedula} - {nombres_pago}")
            creados += 1
        else:
            nuevo_cliente = Cliente(
                cedula=cedula,
                nombres=nombres_pago or f"Cliente {cedula}",
                telefono="+589999999999",
                email="buscaremail@noemail.com",
                direccion="Actualizar dirección",
                fecha_nacimiento=datetime(2000, 1, 1).date(),
                ocupacion="Actualizar ocupación",
                estado="ACTIVO",
                activo=True,
                fecha_registro=datetime.now(),
                usuario_registro="sistema@rapicreditca.com",
                notas=f"Cliente creado automáticamente para pago existente"
            )
            
            db.add(nuevo_cliente)
            db.commit()
            db.refresh(nuevo_cliente)
            
            print(f"Cliente creado: ID {nuevo_cliente.id} - {cedula} - {nombres_pago}")
            creados += 1
    
    return creados

def main():
    """Función principal"""
    import os
    
    # Configurar encoding UTF-8 para Windows
    if sys.platform == 'win32':
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    
    print_section("SOLUCIONAR CLIENTES FALTANTES EN PAGOS")
    
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
        print("Buscando cédulas en pagos sin cliente activo...")
        cedulas_problema = obtener_cedulas_problema(db)
        
        if not cedulas_problema:
            print("OK: No se encontraron cédulas con problema")
            return
        
        cedulas = [cedula for cedula, _, _ in cedulas_problema]
        print(f"Se encontraron {len(cedulas)} cédulas con problema:")
        for cedula, cantidad, total in cedulas_problema:
            print(f"   - {cedula}: {cantidad} pagos, Total: ${total:,.2f}")
        
        # Obtener información de pagos para crear clientes
        pagos_info = db.execute(text(f"""
            SELECT DISTINCT cedula, nombres
            FROM pagos
            WHERE cedula IN ('{"', '".join(cedulas)}') AND activo = TRUE
        """)).fetchall()
        
        print("\n" + "="*80)
        print("OPCIONES DE SOLUCION:")
        print("="*80)
        print("\n1. ACTIVAR CLIENTES INACTIVOS (Recomendado)")
        print("2. CREAR CLIENTES FALTANTES")
        print("3. VER SOLO (DRY RUN)")
        
        opcion = input("\nSeleccione opción (1-3) o Enter para salir: ").strip()
        
        if opcion == "1":
            print("\nActivando clientes inactivos...")
            activar_clientes_inactivos(db, cedulas, dry_run=False)
        elif opcion == "2":
            print("\nCreando clientes faltantes...")
            crear_clientes_faltantes(db, pagos_info, dry_run=False)
        elif opcion == "3":
            print("\n=== DRY RUN - ACTIVAR CLIENTES ===")
            activar_clientes_inactivos(db, cedulas, dry_run=True)
            print("\n=== DRY RUN - CREAR CLIENTES ===")
            crear_clientes_faltantes(db, pagos_info, dry_run=True)
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
