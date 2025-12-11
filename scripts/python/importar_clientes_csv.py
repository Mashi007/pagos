"""
Script para importar clientes desde CSV sin necesidad de privilegios especiales.

Este script lee un archivo CSV y hace INSERT directo en la base de datos,
evitando el problema de permisos de COPY.

USO:
    cd backend
    py scripts/python/importar_clientes_csv.py ruta/al/archivo.csv
"""

import sys
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.session import SessionLocal
from app.models.cliente import Cliente
from sqlalchemy import text

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def normalizar_cedula(cedula: str) -> str:
    """Normaliza cédula: Formato V/J/E + 7-10 números, sin guiones ni símbolos"""
    if not cedula:
        return 'Z999999999'
    
    # Eliminar guiones, espacios y símbolos
    cedula_limpia = cedula.strip().replace('-', '').replace(' ', '').replace('.', '').replace('_', '')
    
    # Validar formato: debe comenzar con V, J o E, seguido de 7-10 números
    import re
    if re.match(r'^[VJE][0-9]{7,10}$', cedula_limpia):
        return cedula_limpia
    
    # Si no cumple formato, usar default
    return 'Z999999999'


def normalizar_email(email: str) -> str:
    """Normaliza email: convierte a minúsculas, valida formato internacional"""
    if not email:
        return 'no-email@rapicredit.com'
    
    email_limpio = email.strip().lower()
    
    # Validar formato internacional: usuario@dominio.extension
    import re
    if re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email_limpio):
        return email_limpio
    
    # Si no cumple formato, usar default
    return 'no-email@rapicredit.com'


def normalizar_estado(estado: Optional[str]) -> str:
    """Normaliza estado: default ACTIVO si es inválido"""
    if not estado or not estado.strip():
        return 'ACTIVO'
    estado_limpio = estado.strip().upper()
    if estado_limpio in ['ACTIVO', 'INACTIVO', 'FINALIZADO']:
        return estado_limpio
    return 'ACTIVO'


def normalizar_nombres(nombres: str) -> str:
    """Normaliza nombres: convierte a mayúsculas"""
    if not nombres or not nombres.strip():
        return 'Nombre Apellido'
    return nombres.strip().upper()


def normalizar_telefono(telefono: str) -> str:
    """Normaliza teléfono: Formato +53 + quitar 0 inicial + exactamente 10 números"""
    if not telefono:
        return '+539999999999'
    
    # Limpiar espacios, guiones y paréntesis
    telefono_limpio = telefono.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    import re
    
    # Si ya está en formato +53XXXXXXXXXX (12 caracteres: +53 + 10 números)
    if re.match(r'^\+53[0-9]{10}$', telefono_limpio):
        return telefono_limpio
    
    # Si está en formato +530XXXXXXXXX (13 caracteres: +53 + 0 + 9 números), quitar el 0
    if re.match(r'^\+530[0-9]{9}$', telefono_limpio):
        return '+53' + telefono_limpio[3:]
    
    # Si está en formato 0XXXXXXXXXX (11 caracteres: 0 + 10 números), agregar +53 y quitar 0
    if re.match(r'^0[0-9]{10}$', telefono_limpio):
        return '+53' + telefono_limpio[1:]
    
    # Si está en formato XXXXXXXXXX (10 números), agregar +53
    if re.match(r'^[0-9]{10}$', telefono_limpio):
        return '+53' + telefono_limpio
    
    # Si no cumple formato, usar default
    return '+539999999999'


def convertir_fecha(fecha_str: Optional[str], formato_entrada: str = 'DD/MM/YYYY') -> Optional[str]:
    """Convierte fecha de DD/MM/YYYY a YYYY-MM-DD"""
    if not fecha_str or not fecha_str.strip():
        return None
    
    fecha_str = fecha_str.strip()
    
    # Si ya está en formato YYYY-MM-DD, retornar
    import re
    if re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_str):
        return fecha_str
    
    # Intentar convertir desde DD/MM/YYYY
    try:
        from datetime import datetime
        if '/' in fecha_str:
            # Formato DD/MM/YYYY
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y')
            return fecha.strftime('%Y-%m-%d')
        elif '-' in fecha_str and len(fecha_str.split('-')[0]) == 2:
            # Formato DD-MM-YYYY
            fecha = datetime.strptime(fecha_str, '%d-%m-%Y')
            return fecha.strftime('%Y-%m-%d')
    except ValueError:
        pass
    
    # Si no se puede convertir, retornar None (se usará default)
    return None


def leer_csv(archivo_csv: str) -> List[Dict]:
    """Lee el archivo CSV y retorna lista de diccionarios"""
    clientes = []
    
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for fila in reader:
                clientes.append(fila)
        
        logger.info(f"✅ Leídos {len(clientes)} registros del CSV")
        return clientes
    
    except FileNotFoundError:
        logger.error(f"❌ Archivo no encontrado: {archivo_csv}")
        raise
    except Exception as e:
        logger.error(f"❌ Error al leer CSV: {e}")
        raise


def hacer_backup(db):
    """Crea backups de tablas antes de importar"""
    logger.info("📦 Creando backups...")
    
    # Backup de clientes
    db.execute(text("""
        DROP TABLE IF EXISTS clientes_backup_antes_importacion;
        CREATE TABLE clientes_backup_antes_importacion AS 
        SELECT * FROM clientes;
    """))
    
    # Backup de préstamos
    db.execute(text("""
        DROP TABLE IF EXISTS prestamos_backup_antes_importacion;
        CREATE TABLE prestamos_backup_antes_importacion AS 
        SELECT * FROM prestamos;
    """))
    
    db.commit()
    logger.info("✅ Backups creados")


def eliminar_datos_existentes(db):
    """Elimina datos existentes respetando Foreign Keys"""
    logger.info("🗑️  Eliminando datos existentes...")
    
    # Eliminar préstamos primero
    result = db.execute(text("DELETE FROM prestamos WHERE cliente_id IS NOT NULL"))
    logger.info(f"   Eliminados {result.rowcount} préstamos")
    
    # Eliminar otras tablas dependientes
    tablas_dependientes = [
        'tickets',
        'notificaciones',
        'conversaciones_whatsapp',
        'comunicaciones_email',
        'conversaciones_ai'
    ]
    
    for tabla in tablas_dependientes:
        try:
            result = db.execute(text(f"""
                DELETE FROM {tabla} 
                WHERE cliente_id IS NOT NULL
            """))
            logger.info(f"   Eliminados {result.rowcount} registros de {tabla}")
        except Exception:
            # Tabla no existe, continuar
            pass
    
    # Eliminar clientes
    result = db.execute(text("DELETE FROM clientes"))
    logger.info(f"   Eliminados {result.rowcount} clientes")
    
    db.commit()
    logger.info("✅ Datos existentes eliminados")


def importar_clientes(db, clientes: List[Dict]):
    """Importa clientes desde lista de diccionarios"""
    logger.info(f"📥 Importando {len(clientes)} clientes...")
    
    insertados = 0
    errores = []
    
    for idx, cliente_data in enumerate(clientes, 1):
        try:
            # Normalizar datos
            cedula = normalizar_cedula(cliente_data.get('cedula', ''))
            nombres = cliente_data.get('nombres', '').strip()
            
            # Validar campos obligatorios
            if not cedula or not nombres:
                errores.append({
                    'fila': idx + 1,
                    'error': 'Cédula o nombres vacíos',
                    'datos': cliente_data
                })
                continue
            
            # Crear nuevo cliente
            nuevo_cliente = Cliente(
                cedula=cedula,
                nombres=nombres,
                telefono=cliente_data.get('telefono', '+589999999999').strip(),
                email=normalizar_email(cliente_data.get('email', 'buscaremail@noemail.com')),
                direccion=cliente_data.get('direccion', 'Actualizar dirección').strip(),
                fecha_nacimiento=cliente_data.get('fecha_nacimiento') or '2000-01-01',
                ocupacion=cliente_data.get('ocupacion', 'Actualizar ocupación').strip(),
                estado=normalizar_estado(cliente_data.get('estado')),
                activo=cliente_data.get('activo', 'true').lower() in ['true', '1', 'yes'],
                fecha_registro=cliente_data.get('fecha_registro') or None,
                fecha_actualizacion=None,  # Se actualiza automáticamente
                usuario_registro=cliente_data.get('usuario_registro', 'SISTEMA'),
                notas=cliente_data.get('notas', 'No hay observaciones')
            )
            
            db.add(nuevo_cliente)
            insertados += 1
            
            # Commit cada 100 registros para mejor rendimiento
            if insertados % 100 == 0:
                db.commit()
                logger.info(f"   Procesados {insertados}/{len(clientes)} registros...")
        
        except Exception as e:
            errores.append({
                'fila': idx + 1,
                'error': str(e),
                'datos': cliente_data
            })
            logger.warning(f"   ⚠️  Error en fila {idx + 1}: {e}")
    
    # Commit final
    db.commit()
    
    logger.info(f"✅ Importados {insertados} clientes")
    if errores:
        logger.warning(f"⚠️  {len(errores)} errores durante la importación")
        for error in errores[:10]:  # Mostrar primeros 10 errores
            logger.warning(f"   Fila {error['fila']}: {error['error']}")
    
    return insertados, errores


def verificar_importacion(db):
    """Verifica que la importación fue exitosa"""
    logger.info("🔍 Verificando importación...")
    
    # Total de registros
    result = db.execute(text("SELECT COUNT(*) FROM clientes"))
    total = result.scalar()
    logger.info(f"   Total de clientes: {total}")
    
    # Verificar normalización
    result = db.execute(text("SELECT COUNT(*) FROM clientes WHERE cedula !~ '-'"))
    logger.info(f"   Cédulas sin guiones: {result.scalar()}")
    
    result = db.execute(text("SELECT COUNT(*) FROM clientes WHERE email = LOWER(email)"))
    logger.info(f"   Emails normalizados: {result.scalar()}")
    
    result = db.execute(text("SELECT COUNT(*) FROM clientes WHERE estado IN ('ACTIVO', 'INACTIVO', 'FINALIZADO')"))
    logger.info(f"   Estados válidos: {result.scalar()}")


def comparar_bases(db):
    """Compara la base actual con el backup"""
    logger.info("📊 Comparando bases...")
    
    # Totales
    result = db.execute(text("SELECT COUNT(*) FROM clientes_backup_antes_importacion"))
    total_antes = result.scalar()
    
    result = db.execute(text("SELECT COUNT(*) FROM clientes"))
    total_despues = result.scalar()
    
    logger.info(f"   Base anterior: {total_antes} clientes")
    logger.info(f"   Base nueva: {total_despues} clientes")
    logger.info(f"   Diferencia: {total_despues - total_antes} clientes")
    
    # Por estado
    result = db.execute(text("""
        SELECT estado, COUNT(*) as cantidad
        FROM clientes_backup_antes_importacion
        GROUP BY estado
        ORDER BY estado
    """))
    logger.info("   Base anterior por estado:")
    for row in result:
        logger.info(f"      {row.estado}: {row.cantidad}")
    
    result = db.execute(text("""
        SELECT estado, COUNT(*) as cantidad
        FROM clientes
        GROUP BY estado
        ORDER BY estado
    """))
    logger.info("   Base nueva por estado:")
    for row in result:
        logger.info(f"      {row.estado}: {row.cantidad}")


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("Uso: py scripts/python/importar_clientes_csv.py ruta/al/archivo.csv")
        sys.exit(1)
    
    archivo_csv = sys.argv[1]
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("📥 IMPORTACIÓN DE CLIENTES DESDE CSV")
    logger.info("=" * 60)
    logger.info(f"\nArchivo: {archivo_csv}\n")
    
    db = SessionLocal()
    
    try:
        # Leer CSV
        clientes = leer_csv(archivo_csv)
        
        if not clientes:
            logger.error("❌ El archivo CSV está vacío")
            return
        
        # Confirmar
        respuesta = input(f"¿Importar {len(clientes)} clientes? Esto reemplazará todos los datos actuales. (s/n): ")
        if respuesta.lower() != 's':
            logger.info("❌ Importación cancelada")
            return
        
        # Hacer backup
        hacer_backup(db)
        
        # Eliminar datos existentes
        eliminar_datos_existentes(db)
        
        # Importar nuevos datos
        insertados, errores = importar_clientes(db, clientes)
        
        # Verificar
        verificar_importacion(db)
        
        # Comparar
        comparar_bases(db)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ IMPORTACIÓN COMPLETA")
        logger.info("=" * 60)
        logger.info(f"   Importados: {insertados} clientes")
        if errores:
            logger.info(f"   Errores: {len(errores)}")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error durante la importación: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

