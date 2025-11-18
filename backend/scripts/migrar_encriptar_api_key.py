"""
Script de migración para encriptar API Key de OpenAI existente
Ejecutar: python -m app.scripts.migrar_encriptar_api_key
"""

import logging
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy.orm import Session

from app.core.encryption import encrypt_api_key, decrypt_api_key, is_encrypted
from app.db.session import SessionLocal
from app.models.configuracion_sistema import ConfiguracionSistema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrar_api_key(db: Session) -> bool:
    """
    Encripta la API Key de OpenAI si no está encriptada.
    
    Returns:
        True si la migración fue exitosa, False en caso contrario
    """
    try:
        # Buscar la configuración de API Key
        config = (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == "AI",
                ConfiguracionSistema.clave == "openai_api_key",
            )
            .first()
        )

        if not config or not config.valor:
            logger.warning("⚠️ No se encontró API Key para encriptar")
            return False

        valor_actual = config.valor.strip()

        # Verificar si ya está encriptada
        if is_encrypted(valor_actual):
            logger.info("✅ API Key ya está encriptada")
            # Verificar que se puede desencriptar correctamente
            try:
                decrypted = decrypt_api_key(valor_actual)
                if decrypted and decrypted.startswith("sk-"):
                    logger.info("✅ API Key encriptada es válida y se puede desencriptar")
                    return True
                else:
                    logger.warning("⚠️ API Key encriptada no parece válida al desencriptar")
            except Exception as e:
                logger.error(f"❌ Error al desencriptar API Key: {e}")
                return False

        # Si no está encriptada, encriptarla
        logger.info("🔐 Encriptando API Key...")
        
        # Validar que la API Key tiene el formato correcto
        if not valor_actual.startswith("sk-"):
            logger.warning(f"⚠️ API Key no tiene formato válido (no empieza con 'sk-'): {valor_actual[:10]}...")
            # Continuar de todas formas, puede ser una API Key válida con otro formato

        try:
            valor_encriptado = encrypt_api_key(valor_actual)
            
            # Verificar que se puede desencriptar
            valor_desencriptado = decrypt_api_key(valor_encriptado)
            if valor_desencriptado != valor_actual:
                logger.error("❌ Error: La API Key encriptada no coincide con la original")
                return False

            # Guardar la API Key encriptada
            config.valor = valor_encriptado
            db.commit()
            
            logger.info("✅ API Key encriptada y guardada exitosamente")
            logger.info(f"   Formato original: {valor_actual[:10]}...{valor_actual[-4:]}")
            logger.info(f"   Formato encriptado: {valor_encriptado[:20]}...")
            
            return True

        except Exception as e:
            logger.error(f"❌ Error al encriptar API Key: {e}", exc_info=True)
            db.rollback()
            return False

    except Exception as e:
        logger.error(f"❌ Error en la migración: {e}", exc_info=True)
        db.rollback()
        return False


def main():
    """Función principal"""
    logger.info("=" * 60)
    logger.info("MIGRACIÓN: Encriptar API Key de OpenAI")
    logger.info("=" * 60)
    
    db: Session = SessionLocal()
    try:
        success = migrar_api_key(db)
        if success:
            logger.info("=" * 60)
            logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("=" * 60)
            logger.error("❌ MIGRACIÓN FALLÓ")
            logger.error("=" * 60)
            return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

