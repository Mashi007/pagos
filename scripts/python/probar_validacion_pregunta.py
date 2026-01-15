#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la validación de preguntas del Chat AI
"""

import sys
import io
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar backend al path para imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def _obtener_palabras_clave_bd():
    """Retorna lista de palabras clave que indican preguntas sobre BD"""
    return [
        # Entidades principales
        "cliente",
        "clientes",
        "prestamo",
        "prestamos",
        "préstamo",
        "préstamos",
        "pago",
        "pagos",
        "cuota",
        "cuotas",
        "mora",
        "morosidad",
        "pendiente",
        "pagada",
        # Identificación y búsqueda
        "cedula",
        "cédula",
        "cedula:",
        "cédula:",
        "documento",
        "dni",
        "ci",
        "nombre",
        "nombres",
        "apellido",
        "apellidos",
        # Estadísticas y análisis
        "total",
        "suma",
        "promedio",
        "cantidad",
        "cuantos",
        "cuantas",
        "cuanto",
        "cuanta",
        "estadistica",
        "estadisticas",
        "estadística",
        "estadísticas",
        "analisis",
        "análisis",
        "datos",
        "informacion",
        "información",
        # Fechas y períodos
        "fecha",
        "fechas",
        "dia",
        "día",
        "dias",
        "días",
        "mes",
        "meses",
        "año",
        "años",
        "semana",
        "semanas",
        "hoy",
        "ayer",
        "mañana",
        # Montos y valores
        "monto",
        "montos",
        "precio",
        "precios",
        "valor",
        "valores",
        "dinero",
        "bs",
        "bolivares",
        "bolívares",
        # Estados y condiciones
        "estado",
        "estados",
        "activo",
        "activos",
        "inactivo",
        "inactivos",
        "aprobado",
        "aprobados",
        "rechazado",
        "rechazados",
        "vencido",
        "vencidos",
        "vencimiento",
        # Acciones y consultas
        "buscar",
        "busca",
        "encontrar",
        "encuentra",
        "mostrar",
        "muestra",
        "listar",
        "lista",
        "obtener",
        "obtiene",
        "consultar",
        "consulta",
        "ver",
        "cual",
        "cuál",
        "como",
        "cómo",
        "donde",
        "dónde",
        "quien",
        "quién",
        "que",
        "qué",
        "tiene",
        "tienen",
        "tener",
    ]

def _validar_pregunta_es_sobre_bd(pregunta: str):
    """
    Valida que la pregunta sea sobre la base de datos.
    Retorna True si es válida, False si no.
    """
    pregunta_lower = pregunta.lower().strip()
    palabras_clave_bd = _obtener_palabras_clave_bd()
    es_pregunta_bd = any(palabra in pregunta_lower for palabra in palabras_clave_bd)
    
    return es_pregunta_bd

def main():
    """Función principal"""
    print("=" * 70)
    print("PRUEBA DE VALIDACIÓN DE PREGUNTAS")
    print("=" * 70)
    print()
    
    # Casos de prueba
    casos_prueba = [
        ("CUAL ES EL NOMBRE QUE TIENEN CEDULA v123456789", True),
        ("DIME COMO SE LLAMA EL CLIENTE QUE TIENE CEDULA v123456789", True),
        ("¿Cuántos préstamos hay?", True),
        ("¿Cuál es el total de pagos del mes?", True),
        ("Muéstrame los clientes en mora", True),
        ("¿Qué tiempo hace hoy?", False),
        ("¿Cómo se hace un pastel?", False),
        ("Hola, ¿cómo estás?", False),
    ]
    
    for pregunta, esperado in casos_prueba:
        resultado = _validar_pregunta_es_sobre_bd(pregunta)
        estado = "✅" if resultado == esperado else "❌"
        print(f"{estado} Pregunta: {pregunta[:60]}...")
        print(f"   Resultado: {'VÁLIDA' if resultado else 'RECHAZADA'} (Esperado: {'VÁLIDA' if esperado else 'RECHAZADA'})")
        
        if resultado:
            # Mostrar qué palabras clave se encontraron
            pregunta_lower = pregunta.lower()
            palabras_encontradas = [palabra for palabra in _obtener_palabras_clave_bd() if palabra in pregunta_lower]
            if palabras_encontradas:
                print(f"   Palabras clave encontradas: {', '.join(palabras_encontradas[:5])}")
        print()
    
    print("=" * 70)
    print("PRUEBA COMPLETADA")
    print("=" * 70)

if __name__ == "__main__":
    main()
