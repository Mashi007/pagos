#!/usr/bin/env python3
"""
Test para validar las actualizaciones de fechas y emails
Fechas: DD/MM/YYYY (día 2 dígitos, mes 2 dígitos, año 4 dígitos)
Email: Conversión automática a minúsculas (incluyendo @)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.validators_service import ValidadorFecha, ValidadorEmail

def test_fechas_validas():
    """Test de fechas válidas"""
    print("🧪 TESTING FECHAS VÁLIDAS (DD/MM/YYYY)")
    print("=" * 50)
    
    casos_validos = [
        ("01/01/2024", "Primer día del año"),
        ("15/03/2024", "Fecha media"),
        ("31/12/2024", "Último día del año"),
        ("29/02/2024", "29 de febrero (año bisiesto)"),
        ("01/01/2000", "Año 2000"),
        ("31/01/2024", "Último día de enero"),
        ("30/04/2024", "Último día de abril"),
    ]
    
    for fecha, descripcion in casos_validos:
        resultado = ValidadorFecha.validar_fecha_entrega(fecha)
        estado = "✅ VÁLIDA" if resultado["valido"] else "❌ INVÁLIDA"
        print(f"{estado} {fecha:12} ({descripcion})")
        if resultado["valido"]:
            print(f"    Formateada: {resultado['valor_formateado']}")
        else:
            print(f"    Error: {resultado['error']}")

def test_fechas_invalidas():
    """Test de fechas inválidas"""
    print("\n🚫 TESTING FECHAS INVÁLIDAS")
    print("=" * 50)
    
    casos_invalidos = [
        ("1/1/2024", "Día y mes sin cero inicial"),
        ("01/1/2024", "Mes sin cero inicial"),
        ("1/01/2024", "Día sin cero inicial"),
        ("01/01/24", "Año de 2 dígitos"),
        ("01-01-2024", "Separador guión"),
        ("2024-01-01", "Formato YYYY-MM-DD"),
        ("32/01/2024", "Día inválido"),
        ("01/13/2024", "Mes inválido"),
        ("29/02/2023", "29 de febrero en año no bisiesto"),
        ("31/04/2024", "31 de abril"),
        ("", "Vacía"),
        ("abc/01/2024", "Contiene letras"),
        ("01/01/1899", "Año muy antiguo"),
        ("01/01/2101", "Año muy futuro"),
    ]
    
    for fecha, descripcion in casos_invalidos:
        resultado = ValidadorFecha.validar_fecha_entrega(fecha)
        estado = "✅ VÁLIDA" if resultado["valido"] else "❌ INVÁLIDA"
        print(f"{estado} {fecha:15} ({descripcion})")
        if resultado["valido"]:
            print(f"    ⚠️  Debería ser inválida pero fue aceptada!")
        else:
            print(f"    Error: {resultado['error']}")

def test_emails_validos():
    """Test de emails válidos"""
    print("\n📧 TESTING EMAILS VÁLIDOS")
    print("=" * 50)
    
    casos_validos = [
        ("usuario@ejemplo.com", "Email básico"),
        ("USUARIO@EJEMPLO.COM", "Email en mayúsculas"),
        (" Usuario@Ejemplo.com ", "Email con espacios"),
        ("usuario.nombre@dominio.com", "Email con punto"),
        ("usuario+tag@ejemplo.com", "Email con +"),
        ("usuario123@ejemplo.com", "Email con números"),
        ("usuario_apellido@ejemplo.com", "Email con guión bajo"),
    ]
    
    for email, descripcion in casos_validos:
        resultado = ValidadorEmail.validar_email(email)
        estado = "✅ VÁLIDO" if resultado["valido"] else "❌ INVÁLIDO"
        print(f"{estado} {email:25} ({descripcion})")
        if resultado["valido"]:
            print(f"    Normalizado: {resultado['valor_formateado']}")
            if resultado.get("cambios_aplicados"):
                print(f"    Cambios: {', '.join(resultado['cambios_aplicados'])}")
        else:
            print(f"    Error: {resultado['error']}")

def test_emails_invalidos():
    """Test de emails inválidos"""
    print("\n🚫 TESTING EMAILS INVÁLIDOS")
    print("=" * 50)
    
    casos_invalidos = [
        ("", "Vacío"),
        ("usuario", "Sin @ ni dominio"),
        ("@ejemplo.com", "Sin usuario"),
        ("usuario@", "Sin dominio"),
        ("usuario@ejemplo", "Sin extensión"),
        ("usuario@.com", "Dominio vacío"),
        ("@.com", "Usuario y dominio vacíos"),
        ("usuario@ejemplo..com", "Doble punto"),
        ("usuario@ejemplo.com.", "Punto al final"),
        ("usuario@tempmail.org", "Dominio bloqueado"),
        ("usuario@10minutemail.com", "Dominio bloqueado"),
    ]
    
    for email, descripcion in casos_invalidos:
        resultado = ValidadorEmail.validar_email(email)
        estado = "✅ VÁLIDO" if resultado["valido"] else "❌ INVÁLIDO"
        print(f"{estado} {email:25} ({descripcion})")
        if resultado["valido"]:
            print(f"    ⚠️  Debería ser inválido pero fue aceptado!")
        else:
            print(f"    Error: {resultado['error']}")

def test_normalizacion_email():
    """Test de normalización de emails"""
    print("\n🔄 TESTING NORMALIZACIÓN DE EMAILS")
    print("=" * 50)
    
    casos_normalizacion = [
        ("USUARIO@EJEMPLO.COM", "Todo en mayúsculas"),
        (" Usuario@Ejemplo.com ", "Con espacios"),
        ("Usuario@Ejemplo.Com", "Mezcla mayúsculas/minúsculas"),
        ("  USUARIO@EJEMPLO.COM  ", "Espacios y mayúsculas"),
    ]
    
    for email, descripcion in casos_normalizacion:
        resultado = ValidadorEmail.validar_email(email)
        if resultado["valido"]:
            print(f"✅ {email:25} → {resultado['valor_formateado']} ({descripcion})")
            if resultado.get("cambios_aplicados"):
                print(f"    Cambios: {', '.join(resultado['cambios_aplicados'])}")
            normalizacion = resultado.get("normalizacion", {})
            if normalizacion.get("convertido_minusculas"):
                print(f"    ✓ Convertido a minúsculas")
            if normalizacion.get("espacios_removidos"):
                print(f"    ✓ Espacios removidos")
        else:
            print(f"❌ {email:25} ({descripcion}) - Error: {resultado['error']}")

def test_requisitos_fecha():
    """Test de requisitos específicos de fecha"""
    print("\n📋 TESTING REQUISITOS ESPECÍFICOS DE FECHA")
    print("=" * 50)
    
    requisitos = [
        ("01/01/2024", "Día 2 dígitos", "✓"),
        ("1/01/2024", "Día 2 dígitos", "✗"),
        ("01/01/2024", "Mes 2 dígitos", "✓"),
        ("01/1/2024", "Mes 2 dígitos", "✗"),
        ("01/01/2024", "Año 4 dígitos", "✓"),
        ("01/01/24", "Año 4 dígitos", "✗"),
        ("01/01/2024", "Separador /", "✓"),
        ("01-01-2024", "Separador /", "✗"),
    ]
    
    for fecha, requisito, esperado in requisitos:
        resultado = ValidadorFecha.validar_fecha_entrega(fecha)
        estado = "✅" if resultado["valido"] else "❌"
        resultado_esperado = "✅" if esperado == "✓" else "❌"
        print(f"{estado} {fecha:12} - {requisito}: {estado} (esperado: {resultado_esperado})")

if __name__ == "__main__":
    print("🧪 TEST DE VALIDACIÓN DE FECHAS Y EMAILS")
    print("Fechas: DD/MM/YYYY (día 2 dígitos, mes 2 dígitos, año 4 dígitos)")
    print("Email: Conversión automática a minúsculas (incluyendo @)")
    print("=" * 80)
    
    test_fechas_validas()
    test_fechas_invalidas()
    test_emails_validos()
    test_emails_invalidos()
    test_normalizacion_email()
    test_requisitos_fecha()
    
    print("\n" + "=" * 80)
    print("🏁 TEST COMPLETADO")
