"""
SCRIPT MAESTRO - EJECUTAR AUDITORIA COMPLETA
Ejecuta todas las auditorías y genera reportes consolidados

Uso:
    python ejecutar_auditoria_completa.py

Autor: Sistema de Auditoría Automatizado
Fecha: 2025-01-27
"""

import sys
import io
from datetime import datetime
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from auditoria_completa_bd import AuditoriaBD
from verificar_flujo_datos import VerificadorFlujoDatos


def main():
    """Ejecuta todas las auditorías"""
    print("=" * 80)
    print("AUDITORIA COMPLETA DEL SISTEMA")
    print("=" * 80)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    directorio_reportes = project_root / "Documentos" / "Auditorias"
    directorio_reportes.mkdir(parents=True, exist_ok=True)

    resultados_consolidados = {
        "fecha": datetime.now().isoformat(),
        "auditoria_bd": None,
        "flujo_datos": None,
    }

    # 1. Ejecutar auditoría completa de BD
    print("\n" + "=" * 80)
    print("EJECUTANDO AUDITORIA COMPLETA DE BASE DE DATOS")
    print("=" * 80)
    auditoria = None
    try:
        auditoria = AuditoriaBD()
        resultados_auditoria = auditoria.ejecutar_auditoria_completa()

        archivo_reporte = directorio_reportes / f"REPORTE_AUDITORIA_BD_{fecha_str}.txt"
        reporte = auditoria.generar_reporte(str(archivo_reporte))

        resultados_consolidados["auditoria_bd"] = {
            "estado": "COMPLETADO",
            "problemas_criticos": len(resultados_auditoria["problemas_criticos"]),
            "problemas_medios": len(resultados_auditoria["problemas_medios"]),
            "problemas_menores": len(resultados_auditoria["problemas_menores"]),
            "archivo_reporte": str(archivo_reporte),
        }

        print(f"\n[OK] Auditoria de BD completada. Reporte: {archivo_reporte}")

    except Exception as e:
        print(f"\n[ERROR] Error en auditoria de BD: {e}")
        resultados_consolidados["auditoria_bd"] = {
            "estado": "ERROR",
            "error": str(e),
        }
    finally:
        if auditoria:
            auditoria.cerrar()

    # 2. Ejecutar verificación de flujo de datos
    print("\n" + "=" * 80)
    print("EJECUTANDO VERIFICACION DE FLUJO DE DATOS")
    print("=" * 80)
    verificador = None
    try:
        verificador = VerificadorFlujoDatos()
        resultados_flujo = verificador.verificar_flujo_completo()

        archivo_reporte_flujo = directorio_reportes / f"REPORTE_FLUJO_DATOS_{fecha_str}.txt"
        reporte_flujo = verificador.generar_reporte()

        with open(archivo_reporte_flujo, "w", encoding="utf-8") as f:
            f.write(reporte_flujo)

        resultados_consolidados["flujo_datos"] = {
            "estado": "COMPLETADO",
            "total_problemas": resultados_flujo["total_problemas"],
            "archivo_reporte": str(archivo_reporte_flujo),
        }

        print(f"\n[OK] Verificacion de flujo completada. Reporte: {archivo_reporte_flujo}")

    except Exception as e:
        print(f"\n[ERROR] Error en verificacion de flujo: {e}")
        resultados_consolidados["flujo_datos"] = {
            "estado": "ERROR",
            "error": str(e),
        }
    finally:
        if verificador:
            verificador.cerrar()

    # 3. Generar reporte consolidado
    print("\n" + "=" * 80)
    print("GENERANDO REPORTE CONSOLIDADO")
    print("=" * 80)

    archivo_consolidado = directorio_reportes / f"REPORTE_CONSOLIDADO_{fecha_str}.txt"
    with open(archivo_consolidado, "w", encoding="utf-8", errors='replace') as f:
        f.write("=" * 80 + "\n")
        f.write("REPORTE CONSOLIDADO DE AUDITORIA\n")
        f.write("=" * 80 + "\n")
        f.write(f"Fecha: {resultados_consolidados['fecha']}\n")
        f.write("\n")

        # Resumen de auditoría BD
        if resultados_consolidados["auditoria_bd"]:
            f.write("1. AUDITORÍA DE BASE DE DATOS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Estado: {resultados_consolidados['auditoria_bd']['estado']}\n")
            if resultados_consolidados["auditoria_bd"]["estado"] == "COMPLETADO":
                f.write(
                    f"  [CRITICO] Criticos: {resultados_consolidados['auditoria_bd']['problemas_criticos']}\n"
                )
                f.write(
                    f"  [MEDIO] Medios: {resultados_consolidados['auditoria_bd']['problemas_medios']}\n"
                )
                f.write(
                    f"  [MENOR] Menores: {resultados_consolidados['auditoria_bd']['problemas_menores']}\n"
                )
                f.write(f"  Archivo: {resultados_consolidados['auditoria_bd']['archivo_reporte']}\n")
            else:
                f.write(f"  Error: {resultados_consolidados['auditoria_bd'].get('error', 'Desconocido')}\n")
            f.write("\n")

        # Resumen de flujo de datos
        if resultados_consolidados["flujo_datos"]:
            f.write("2. VERIFICACIÓN DE FLUJO DE DATOS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Estado: {resultados_consolidados['flujo_datos']['estado']}\n")
            if resultados_consolidados["flujo_datos"]["estado"] == "COMPLETADO":
                f.write(
                    f"  Total de problemas: {resultados_consolidados['flujo_datos']['total_problemas']}\n"
                )
                f.write(f"  Archivo: {resultados_consolidados['flujo_datos']['archivo_reporte']}\n")
            else:
                f.write(f"  Error: {resultados_consolidados['flujo_datos'].get('error', 'Desconocido')}\n")
            f.write("\n")

        f.write("=" * 80 + "\n")

    print(f"\n[OK] Reporte consolidado generado: {archivo_consolidado}")

    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)

    if resultados_consolidados["auditoria_bd"]:
        if resultados_consolidados["auditoria_bd"]["estado"] == "COMPLETADO":
            print(
                f"Auditoría BD: {resultados_consolidados['auditoria_bd']['problemas_criticos']} críticos, "
                f"{resultados_consolidados['auditoria_bd']['problemas_medios']} medios, "
                f"{resultados_consolidados['auditoria_bd']['problemas_menores']} menores"
            )
        else:
            print(f"Auditoría BD: ERROR - {resultados_consolidados['auditoria_bd'].get('error', 'Desconocido')}")

    if resultados_consolidados["flujo_datos"]:
        if resultados_consolidados["flujo_datos"]["estado"] == "COMPLETADO":
            print(f"Flujo de datos: {resultados_consolidados['flujo_datos']['total_problemas']} problemas encontrados")
        else:
            print(f"Flujo de datos: ERROR - {resultados_consolidados['flujo_datos'].get('error', 'Desconocido')}")

    print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
