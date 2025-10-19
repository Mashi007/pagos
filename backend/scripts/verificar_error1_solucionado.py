#!/usr/bin/env python3
"""
Script para verificar que el error de clientes está solucionado
"""

import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://pagos-f2qf.onrender.com"

def verificar_clientes():
    """Verificar que el endpoint de clientes funciona"""
    logger.info("🔍 VERIFICANDO ENDPOINT DE CLIENTES")
    logger.info("=" * 60)
    
    try:
        # Login como admin
        credenciales = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                               json=credenciales, 
                               timeout=10)
        
        if response.status_code != 200:
            logger.error(f"❌ Error login: {response.status_code}")
            return
        
        data = response.json()
        token = data['access_token']
        headers = {"Authorization": f"Bearer {token}"}
        
        # Probar endpoint de clientes
        response = requests.get(f"{BASE_URL}/api/v1/clientes/?page=1&per_page=5", 
                              headers=headers, 
                              timeout=10)
        
        logger.info(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            clientes = response.json()
            logger.info(f"✅ Clientes obtenidos: {len(clientes.get('items', []))}")
            logger.info("🎉 ERROR 1 SOLUCIONADO - Endpoint de clientes funciona")
        else:
            logger.error(f"❌ Error: {response.status_code}")
            logger.error(f"📄 Respuesta: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")

def main():
    logger.info("🔍 VERIFICACIÓN DE ERROR 1 SOLUCIONADO")
    logger.info("=" * 80)
    
    verificar_clientes()

if __name__ == "__main__":
    main()
