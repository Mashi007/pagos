"""
Script de prueba para el webhook de WhatsApp
Ejecutar con: python test_whatsapp_webhook.py
"""
import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
WEBHOOK_URL = f"{BASE_URL}/api/v1/whatsapp/webhook"

# Token de verificación (debe coincidir con el configurado)
VERIFY_TOKEN = "mi_token_secreto_12345"


def test_webhook_verification():
    """Prueba la verificación del webhook"""
    print("=" * 60)
    print("TEST 1: Verificación del Webhook")
    print("=" * 60)
    
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "123456789",
        "hub.verify_token": VERIFY_TOKEN
    }
    
    try:
        response = requests.get(WEBHOOK_URL, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200 and response.text == "123456789":
            print("✅ Verificación exitosa!")
        else:
            print("❌ Verificación fallida")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print()


def test_webhook_verification_invalid_token():
    """Prueba la verificación con token inválido"""
    print("=" * 60)
    print("TEST 2: Verificación con Token Inválido")
    print("=" * 60)
    
    params = {
        "hub.mode": "subscribe",
        "hub.challenge": "123456789",
        "hub.verify_token": "token_invalido"
    }
    
    try:
        response = requests.get(WEBHOOK_URL, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.text else 'No content'}")
        
        if response.status_code == 403:
            print("✅ Rechazo correcto de token inválido")
        else:
            print("❌ Debería rechazar el token inválido")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print()


def test_receive_message():
    """Prueba recibir un mensaje de WhatsApp"""
    print("=" * 60)
    print("TEST 3: Recibir Mensaje de WhatsApp")
    print("=" * 60)
    
    # Payload simulado de Meta
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry_id_123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "+1234567890",
                                "phone_number_id": "phone_number_id_123"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Usuario de Prueba"
                                    },
                                    "wa_id": "1234567890"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "1234567890",
                                    "id": f"wamid.test_{int(datetime.now().timestamp())}",
                                    "timestamp": str(int(datetime.now().timestamp())),
                                    "type": "text",
                                    "text": {
                                        "body": "Hola, este es un mensaje de prueba"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ Mensaje procesado exitosamente")
            else:
                print("❌ Error procesando mensaje")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print()


def test_receive_multiple_messages():
    """Prueba recibir múltiples mensajes"""
    print("=" * 60)
    print("TEST 4: Recibir Múltiples Mensajes")
    print("=" * 60)
    
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry_id_123",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "+1234567890",
                                "phone_number_id": "phone_number_id_123"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Usuario 1"},
                                    "wa_id": "1111111111"
                                },
                                {
                                    "profile": {"name": "Usuario 2"},
                                    "wa_id": "2222222222"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "1111111111",
                                    "id": f"wamid.msg1_{int(datetime.now().timestamp())}",
                                    "timestamp": str(int(datetime.now().timestamp())),
                                    "type": "text",
                                    "text": {"body": "Mensaje 1"}
                                },
                                {
                                    "from": "2222222222",
                                    "id": f"wamid.msg2_{int(datetime.now().timestamp())}",
                                    "timestamp": str(int(datetime.now().timestamp())),
                                    "type": "text",
                                    "text": {"body": "Mensaje 2"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ Múltiples mensajes procesados exitosamente")
            else:
                print("❌ Error procesando mensajes")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PRUEBAS DEL WEBHOOK DE WHATSAPP")
    print("=" * 60)
    print(f"URL Base: {BASE_URL}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"Verify Token: {VERIFY_TOKEN}")
    print("=" * 60 + "\n")
    
    # Ejecutar pruebas
    test_webhook_verification()
    test_webhook_verification_invalid_token()
    test_receive_message()
    test_receive_multiple_messages()
    
    print("=" * 60)
    print("PRUEBAS COMPLETADAS")
    print("=" * 60)
