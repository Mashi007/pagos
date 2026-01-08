"""
🔍 AUDITORÍA COMPLETA DE BASE DE DATOS
Sistema de Cobranzas y Gestión de Créditos

Este script realiza una auditoría exhaustiva de:
1. Conexiones de tablas (Foreign Keys e integridad referencial)
2. Cálculos financieros (amortización, mora, intereses)
3. Interacción entre tablas
4. Captura y clasificación de datos
5. Movimiento de cálculos entre tablas

Autor: Sistema de Auditoría Automatizado
Fecha: 2025-01-27
"""

import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import (
    and_,
    func,
    inspect,
    or_,
    select,
    text,
)
from sqlalchemy.orm import Session

# Importar configuración de base de datos
from app.db.session import SessionLocal, engine
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.prestamo_evaluacion import PrestamoEvaluacion


class AuditoriaBD:
    """Clase principal para auditoría completa de base de datos"""

    def __init__(self, db: Optional[Session] = None):
        """
        Inicializa la auditoría

        Args:
            db: Sesión de base de datos (opcional, se crea automáticamente si no se proporciona)
        """
        self.db = db or SessionLocal()
        self.resultados: Dict = {
            "fecha_auditoria": datetime.now().isoformat(),
            "conexiones_tablas": {},
            "integridad_referencial": {},
            "calculos_financieros": {},
            "coherencia_datos": {},
            "problemas_criticos": [],
            "problemas_medios": [],
            "problemas_menores": [],
            "resumen": {},
        }

    def ejecutar_auditoria_completa(self) -> Dict:
        """
        Ejecuta la auditoría completa del sistema

        Returns:
            Dict con todos los resultados de la auditoría
        """
        print("🔍 Iniciando auditoría completa de base de datos...")
        print("=" * 80)

        # 1. Verificar conexiones de tablas
        print("\n📊 1. Verificando conexiones de tablas (Foreign Keys)...")
        self.verificar_conexiones_tablas()

        # 2. Verificar integridad referencial
        print("\n🔗 2. Verificando integridad referencial...")
        self.verificar_integridad_referencial()

        # 3. Verificar cálculos financieros
        print("\n💰 3. Verificando cálculos financieros...")
        self.verificar_calculos_financieros()

        # 4. Verificar coherencia de datos
        print("\n📋 4. Verificando coherencia de datos entre tablas...")
        self.verificar_coherencia_datos()

        # 5. Generar resumen
        print("\n📊 5. Generando resumen de auditoría...")
        self.generar_resumen()

        return self.resultados

    def verificar_conexiones_tablas(self):
        """Verifica todas las conexiones de tablas (Foreign Keys)"""
        inspector = inspect(engine)

        # Obtener todas las tablas
        tablas = inspector.get_table_names()

        conexiones = {}
        problemas = []

        # Tablas principales a verificar
        tablas_principales = [
            "clientes",
            "prestamos",
            "pagos",
            "cuotas",
            "prestamos_evaluacion",
            "aprobaciones",
            "notificaciones",
            "tickets",
        ]

        for tabla in tablas_principales:
            if tabla not in tablas:
                problemas.append(f"⚠️ Tabla '{tabla}' no existe en la base de datos")
                continue

            fks = inspector.get_foreign_keys(tabla)
            conexiones[tabla] = {
                "foreign_keys": [],
                "total_fks": len(fks),
            }

            for fk in fks:
                conexiones[tabla]["foreign_keys"].append({
                    "nombre": fk.get("name", "SIN_NOMBRE"),
                    "columna": fk.get("constrained_columns", [None])[0] if fk.get("constrained_columns") else "N/A",
                    "tabla_referenciada": fk.get("referred_table", "N/A"),
                    "columna_referenciada": fk.get("referred_columns", [None])[0] if fk.get("referred_columns") else "N/A",
                })

            # Verificar Foreign Keys esperados pero faltantes
            fks_esperados = self._obtener_fks_esperados(tabla)
            fks_encontrados = [fk.get("referred_table", "N/A") for fk in fks if fk.get("referred_table")]

            for fk_esperado in fks_esperados:
                if fk_esperado["tabla"] not in fks_encontrados:
                    problemas.append(
                        f"⚠️ Tabla '{tabla}': Falta FK a '{fk_esperado['tabla']}' "
                        f"(columna: {fk_esperado['columna']})"
                    )

        self.resultados["conexiones_tablas"] = conexiones
        self.resultados["problemas_medios"].extend(problemas)

        print(f"✅ Verificadas {len(tablas_principales)} tablas principales")
        if problemas:
            print(f"⚠️ Encontrados {len(problemas)} problemas de conexión")

    def _obtener_fks_esperados(self, tabla: str) -> List[Dict]:
        """Obtiene los Foreign Keys esperados para una tabla"""
        fks_esperados = {
            "pagos": [
                {"tabla": "prestamos", "columna": "prestamo_id"},
                {"tabla": "clientes", "columna": "cliente_id"},
            ],
            "prestamos": [
                {"tabla": "clientes", "columna": "cliente_id"},
            ],
            "cuotas": [
                {"tabla": "prestamos", "columna": "prestamo_id"},
            ],
            "prestamos_evaluacion": [
                {"tabla": "prestamos", "columna": "prestamo_id"},
            ],
        }
        return fks_esperados.get(tabla, [])

    def verificar_integridad_referencial(self):
        """Verifica la integridad referencial de las relaciones"""
        problemas = []

        # 1. Verificar pagos con prestamo_id inválido
        print("   Verificando pagos con prestamo_id inválido...")
        pagos_huérfanos = (
            self.db.query(Pago)
            .filter(Pago.prestamo_id.isnot(None))
            .outerjoin(Prestamo, Pago.prestamo_id == Prestamo.id)
            .filter(Prestamo.id.is_(None))
            .count()
        )
        if pagos_huérfanos > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "pagos",
                "problema": f"{pagos_huérfanos} pagos con prestamo_id que no existe en prestamos",
                "cantidad": pagos_huérfanos,
            })

        # 2. Verificar pagos con cliente_id inválido
        print("   Verificando pagos con cliente_id inválido...")
        pagos_cliente_invalido = (
            self.db.query(Pago)
            .filter(Pago.cliente_id.isnot(None))
            .outerjoin(Cliente, Pago.cliente_id == Cliente.id)
            .filter(Cliente.id.is_(None))
            .count()
        )
        if pagos_cliente_invalido > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "pagos",
                "problema": f"{pagos_cliente_invalido} pagos con cliente_id que no existe en clientes",
                "cantidad": pagos_cliente_invalido,
            })

        # 3. Verificar cuotas con prestamo_id inválido
        print("   Verificando cuotas con prestamo_id inválido...")
        cuotas_huerfanas = (
            self.db.query(Cuota)
            .outerjoin(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.id.is_(None))
            .count()
        )
        if cuotas_huerfanas > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "cuotas",
                "problema": f"{cuotas_huerfanas} cuotas con prestamo_id que no existe en prestamos",
                "cantidad": cuotas_huerfanas,
            })

        # 4. Verificar prestamos con cliente_id inválido
        print("   Verificando préstamos con cliente_id inválido...")
        prestamos_cliente_invalido = (
            self.db.query(Prestamo.id)
            .outerjoin(Cliente, Prestamo.cliente_id == Cliente.id)
            .filter(Cliente.id.is_(None))
            .count()
        )
        if prestamos_cliente_invalido > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "prestamos",
                "problema": f"{prestamos_cliente_invalido} préstamos con cliente_id que no existe en clientes",
                "cantidad": prestamos_cliente_invalido,
            })

        # 5. Verificar prestamos_evaluacion con prestamo_id inválido
        print("   Verificando evaluaciones con prestamo_id inválido...")
        evaluaciones_huerfanas = (
            self.db.query(PrestamoEvaluacion)
            .outerjoin(Prestamo, PrestamoEvaluacion.prestamo_id == Prestamo.id)
            .filter(Prestamo.id.is_(None))
            .count()
        )
        if evaluaciones_huerfanas > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "prestamos_evaluacion",
                "problema": f"{evaluaciones_huerfanas} evaluaciones con prestamo_id que no existe",
                "cantidad": evaluaciones_huerfanas,
            })

        # 6. Verificar pagos con cédula que no existe en clientes
        print("   Verificando pagos con cédula que no existe en clientes...")
        pagos_cedula_invalida = (
            self.db.query(Pago.cedula)
            .distinct()
            .outerjoin(Cliente, Pago.cedula == Cliente.cedula)
            .filter(Cliente.cedula.is_(None))
            .count()
        )
        if pagos_cedula_invalida > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "pagos",
                "problema": f"{pagos_cedula_invalida} cédulas únicas en pagos que no existen en clientes",
                "cantidad": pagos_cedula_invalida,
            })

        self.resultados["integridad_referencial"] = {
            "problemas": problemas,
            "total_problemas": len(problemas),
        }

        # Clasificar problemas
        for problema in problemas:
            if problema["tipo"] == "CRITICO":
                self.resultados["problemas_criticos"].append(problema)
            elif problema["tipo"] == "MEDIO":
                self.resultados["problemas_medios"].append(problema)

        print(f"✅ Verificada integridad referencial: {len(problemas)} problemas encontrados")

    def verificar_calculos_financieros(self):
        """Verifica los cálculos financieros en el sistema"""
        problemas = []
        verificaciones = {}

        # 1. Verificar coherencia en cuotas: monto_cuota = monto_capital + monto_interes
        print("   Verificando coherencia de montos en cuotas...")
        cuotas_incoherentes = (
            self.db.query(Cuota)
            .filter(
                func.abs(
                    Cuota.monto_cuota - (Cuota.monto_capital + Cuota.monto_interes)
                )
                > Decimal("0.01")
            )
            .count()
        )
        verificaciones["cuotas_monto_coherente"] = {
            "total": self.db.query(Cuota).count(),
            "incoherentes": cuotas_incoherentes,
            "porcentaje": (
                (cuotas_incoherentes / self.db.query(Cuota).count() * 100)
                if self.db.query(Cuota).count() > 0
                else 0
            ),
        }
        if cuotas_incoherentes > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "cuotas",
                "problema": f"{cuotas_incoherentes} cuotas donde monto_cuota ≠ monto_capital + monto_interes",
                "cantidad": cuotas_incoherentes,
            })

        # 2. Verificar coherencia en pagos aplicados: total_pagado = capital_pagado + interes_pagado + mora_pagada
        print("   Verificando coherencia de pagos aplicados en cuotas...")
        cuotas_pago_incoherente = (
            self.db.query(Cuota)
            .filter(
                func.abs(
                    Cuota.total_pagado
                    - (Cuota.capital_pagado + Cuota.interes_pagado + Cuota.mora_pagada)
                )
                > Decimal("0.01")
            )
            .count()
        )
        verificaciones["cuotas_pago_coherente"] = {
            "total": self.db.query(Cuota).filter(Cuota.total_pagado > 0).count(),
            "incoherentes": cuotas_pago_incoherente,
        }
        if cuotas_pago_incoherente > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "cuotas",
                "problema": f"{cuotas_pago_incoherente} cuotas donde total_pagado ≠ capital_pagado + interes_pagado + mora_pagada",
                "cantidad": cuotas_pago_incoherente,
            })

        # 3. Verificar coherencia en pendientes: capital_pendiente + interes_pendiente = monto_cuota - total_pagado
        print("   Verificando coherencia de montos pendientes en cuotas...")
        cuotas_pendiente_incoherente = (
            self.db.query(Cuota)
            .filter(
                func.abs(
                    (Cuota.capital_pendiente + Cuota.interes_pendiente)
                    - (Cuota.monto_cuota - Cuota.total_pagado)
                )
                > Decimal("0.01")
            )
            .count()
        )
        verificaciones["cuotas_pendiente_coherente"] = {
            "total": self.db.query(Cuota).count(),
            "incoherentes": cuotas_pendiente_incoherente,
        }
        if cuotas_pendiente_incoherente > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "cuotas",
                "problema": f"{cuotas_pendiente_incoherente} cuotas donde pendientes no coinciden con monto_cuota - total_pagado",
                "cantidad": cuotas_pendiente_incoherente,
            })

        # 4. Verificar cálculo de mora: si fecha_pago > fecha_vencimiento, debe haber mora
        print("   Verificando cálculo automático de mora...")
        cuotas_con_mora_esperada = (
            self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.fecha_pago.isnot(None),
                    Cuota.fecha_pago > Cuota.fecha_vencimiento,
                    or_(
                        Cuota.dias_mora == 0,
                        Cuota.monto_mora == 0,
                    ),
                )
            )
            .count()
        )
        verificaciones["cuotas_mora_calculada"] = {
            "total": self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.fecha_pago.isnot(None),
                    Cuota.fecha_pago > Cuota.fecha_vencimiento,
                )
            )
            .count(),
            "sin_mora": cuotas_con_mora_esperada,
        }
        if cuotas_con_mora_esperada > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "cuotas",
                "problema": f"{cuotas_con_mora_esperada} cuotas pagadas después de vencimiento sin mora calculada",
                "cantidad": cuotas_con_mora_esperada,
            })

        # 5. Verificar saldos de capital: saldo_capital_final debe ser coherente
        print("   Verificando coherencia de saldos de capital...")
        cuotas_saldo_incoherente = (
            self.db.query(Cuota)
            .filter(
                func.abs(
                    Cuota.saldo_capital_final
                    - (Cuota.saldo_capital_inicial - Cuota.monto_capital)
                )
                > Decimal("0.01")
            )
            .count()
        )
        verificaciones["cuotas_saldo_coherente"] = {
            "total": self.db.query(Cuota).count(),
            "incoherentes": cuotas_saldo_incoherente,
        }
        if cuotas_saldo_incoherente > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "cuotas",
                "problema": f"{cuotas_saldo_incoherente} cuotas donde saldo_capital_final no coincide con cálculo",
                "cantidad": cuotas_saldo_incoherente,
            })

        # 6. Verificar suma de pagos vs total en tabla pagos
        print("   Verificando suma de pagos por préstamo...")
        # Obtener préstamos con pagos
        prestamos_con_pagos = (
            self.db.query(Prestamo.id, func.sum(Pago.monto_pagado).label("total_pagado"))
            .join(Pago, Prestamo.id == Pago.prestamo_id)
            .filter(Pago.activo == True)
            .group_by(Prestamo.id)
            .all()
        )

        problemas_suma_pagos = 0
        for prestamo_id, total_pagado_bd in prestamos_con_pagos:
            # Sumar total_pagado de cuotas
            total_pagado_cuotas = (
                self.db.query(func.sum(Cuota.total_pagado))
                .filter(Cuota.prestamo_id == prestamo_id)
                .scalar()
                or Decimal("0.00")
            )

            if abs(total_pagado_bd - total_pagado_cuotas) > Decimal("0.01"):
                problemas_suma_pagos += 1

        verificaciones["suma_pagos_coherente"] = {
            "total_prestamos": len(prestamos_con_pagos),
            "incoherentes": problemas_suma_pagos,
        }
        if problemas_suma_pagos > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "pagos/cuotas",
                "problema": f"{problemas_suma_pagos} préstamos donde suma de pagos no coincide con suma de cuotas",
                "cantidad": problemas_suma_pagos,
            })

        self.resultados["calculos_financieros"] = {
            "verificaciones": verificaciones,
            "problemas": problemas,
            "total_problemas": len(problemas),
        }

        # Clasificar problemas
        for problema in problemas:
            if problema["tipo"] == "CRITICO":
                self.resultados["problemas_criticos"].append(problema)
            elif problema["tipo"] == "MEDIO":
                self.resultados["problemas_medios"].append(problema)

        print(f"✅ Verificados cálculos financieros: {len(problemas)} problemas encontrados")

    def verificar_coherencia_datos(self):
        """Verifica la coherencia de datos entre tablas relacionadas"""
        problemas = []
        verificaciones = {}

        # 1. Verificar que cédulas coincidan entre tablas
        print("   Verificando coherencia de cédulas entre tablas...")
        # Prestamos con cédula diferente a cliente
        prestamos_cedula_diferente = (
            self.db.query(Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .filter(Prestamo.cedula != Cliente.cedula)
            .count()
        )
        verificaciones["prestamos_cedula_coherente"] = {
            "total": self.db.query(Prestamo).count(),
            "incoherentes": prestamos_cedula_diferente,
        }
        if prestamos_cedula_diferente > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "prestamos/clientes",
                "problema": f"{prestamos_cedula_diferente} préstamos con cédula diferente a la del cliente",
                "cantidad": prestamos_cedula_diferente,
            })

        # 2. Verificar que número de cuotas coincida
        print("   Verificando número de cuotas por préstamo...")
        prestamos_cuotas_incorrectas = (
            self.db.query(Prestamo.id, Prestamo.numero_cuotas)
            .join(Cuota, Prestamo.id == Cuota.prestamo_id)
            .group_by(Prestamo.id, Prestamo.numero_cuotas)
            .having(func.count(Cuota.id) != Prestamo.numero_cuotas)
            .count()
        )
        verificaciones["prestamos_cuotas_coherente"] = {
            "total": self.db.query(Prestamo).count(),
            "incoherentes": prestamos_cuotas_incorrectas,
        }
        if prestamos_cuotas_incorrectas > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "prestamos/cuotas",
                "problema": f"{prestamos_cuotas_incorrectas} préstamos con número de cuotas incorrecto",
                "cantidad": prestamos_cuotas_incorrectas,
            })

        # 3. Verificar que cuotas estén numeradas correctamente (1, 2, 3, ...)
        print("   Verificando numeración de cuotas...")
        cuotas_numeracion_incorrecta = (
            self.db.query(Cuota.prestamo_id)
            .group_by(Cuota.prestamo_id)
            .having(
                func.max(Cuota.numero_cuota) != func.count(Cuota.id)
            )
            .count()
        )
        verificaciones["cuotas_numeracion_coherente"] = {
            "total": self.db.query(Prestamo).count(),
            "incoherentes": cuotas_numeracion_incorrecta,
        }
        if cuotas_numeracion_incorrecta > 0:
            problemas.append({
                "tipo": "MENOR",
                "tabla": "cuotas",
                "problema": f"{cuotas_numeracion_incorrecta} préstamos con numeración de cuotas incorrecta",
                "cantidad": cuotas_numeracion_incorrecta,
            })

        # 4. Verificar estados de cuotas vs pagos
        print("   Verificando estados de cuotas...")
        cuotas_pagadas_sin_pago = (
            self.db.query(Cuota)
            .filter(
                and_(
                    Cuota.estado == "PAGADO",
                    Cuota.total_pagado == 0,
                )
            )
            .count()
        )
        verificaciones["cuotas_estado_coherente"] = {
            "total": self.db.query(Cuota).count(),
            "incoherentes": cuotas_pagadas_sin_pago,
        }
        if cuotas_pagadas_sin_pago > 0:
            problemas.append({
                "tipo": "MEDIO",
                "tabla": "cuotas",
                "problema": f"{cuotas_pagadas_sin_pago} cuotas marcadas como PAGADO sin pagos aplicados",
                "cantidad": cuotas_pagadas_sin_pago,
            })

        # 5. Verificar que préstamos aprobados tengan cuotas generadas
        print("   Verificando que préstamos aprobados tengan cuotas...")
        prestamos_sin_cuotas = (
            self.db.query(Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .outerjoin(Cuota, Prestamo.id == Cuota.prestamo_id)
            .filter(Cuota.id.is_(None))
            .count()
        )
        verificaciones["prestamos_cuotas_generadas"] = {
            "total": self.db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count(),
            "sin_cuotas": prestamos_sin_cuotas,
        }
        if prestamos_sin_cuotas > 0:
            problemas.append({
                "tipo": "CRITICO",
                "tabla": "prestamos/cuotas",
                "problema": f"{prestamos_sin_cuotas} préstamos APROBADOS sin cuotas generadas",
                "cantidad": prestamos_sin_cuotas,
            })

        self.resultados["coherencia_datos"] = {
            "verificaciones": verificaciones,
            "problemas": problemas,
            "total_problemas": len(problemas),
        }

        # Clasificar problemas
        for problema in problemas:
            if problema["tipo"] == "CRITICO":
                self.resultados["problemas_criticos"].append(problema)
            elif problema["tipo"] == "MEDIO":
                self.resultados["problemas_medios"].append(problema)
            elif problema["tipo"] == "MENOR":
                self.resultados["problemas_menores"].append(problema)

        print(f"✅ Verificada coherencia de datos: {len(problemas)} problemas encontrados")

    def generar_resumen(self):
        """Genera un resumen ejecutivo de la auditoría"""
        total_criticos = len(self.resultados["problemas_criticos"])
        total_medios = len(self.resultados["problemas_medios"])
        total_menores = len(self.resultados["problemas_menores"])

        self.resultados["resumen"] = {
            "total_problemas": total_criticos + total_medios + total_menores,
            "problemas_criticos": total_criticos,
            "problemas_medios": total_medios,
            "problemas_menores": total_menores,
            "estado_general": (
                "CRITICO" if total_criticos > 0
                else "ATENCION" if total_medios > 0
                else "OK" if total_menores == 0
                else "MENORES"
            ),
        }

        print("\n" + "=" * 80)
        print("📊 RESUMEN DE AUDITORÍA")
        print("=" * 80)
        print(f"🔴 Problemas Críticos: {total_criticos}")
        print(f"🟡 Problemas Medios: {total_medios}")
        print(f"🟢 Problemas Menores: {total_menores}")
        print(f"📈 Estado General: {self.resultados['resumen']['estado_general']}")
        print("=" * 80)

    def generar_reporte(self, archivo_salida: Optional[str] = None) -> str:
        """
        Genera un reporte detallado en formato texto

        Args:
            archivo_salida: Ruta del archivo de salida (opcional)

        Returns:
            Contenido del reporte
        """
        reporte = []
        reporte.append("=" * 80)
        reporte.append("🔍 REPORTE DE AUDITORÍA COMPLETA DE BASE DE DATOS")
        reporte.append("=" * 80)
        reporte.append(f"Fecha: {self.resultados['fecha_auditoria']}")
        reporte.append("")

        # Resumen ejecutivo
        resumen = self.resultados["resumen"]
        reporte.append("📊 RESUMEN EJECUTIVO")
        reporte.append("-" * 80)
        reporte.append(f"Estado General: {resumen['estado_general']}")
        reporte.append(f"Total de Problemas: {resumen['total_problemas']}")
        reporte.append(f"  🔴 Críticos: {resumen['problemas_criticos']}")
        reporte.append(f"  🟡 Medios: {resumen['problemas_medios']}")
        reporte.append(f"  🟢 Menores: {resumen['problemas_menores']}")
        reporte.append("")

        # Problemas críticos
        if self.resultados["problemas_criticos"]:
            reporte.append("🔴 PROBLEMAS CRÍTICOS")
            reporte.append("-" * 80)
            for i, problema in enumerate(self.resultados["problemas_criticos"], 1):
                reporte.append(f"{i}. [{problema['tabla']}] {problema['problema']}")
                if "cantidad" in problema:
                    reporte.append(f"   Cantidad afectada: {problema['cantidad']}")
            reporte.append("")

        # Problemas medios
        if self.resultados["problemas_medios"]:
            reporte.append("🟡 PROBLEMAS MEDIOS")
            reporte.append("-" * 80)
            for i, problema in enumerate(self.resultados["problemas_medios"], 1):
                reporte.append(f"{i}. [{problema['tabla']}] {problema['problema']}")
                if "cantidad" in problema:
                    reporte.append(f"   Cantidad afectada: {problema['cantidad']}")
            reporte.append("")

        # Problemas menores
        if self.resultados["problemas_menores"]:
            reporte.append("🟢 PROBLEMAS MENORES")
            reporte.append("-" * 80)
            for i, problema in enumerate(self.resultados["problemas_menores"], 1):
                reporte.append(f"{i}. [{problema['tabla']}] {problema['problema']}")
                if "cantidad" in problema:
                    reporte.append(f"   Cantidad afectada: {problema['cantidad']}")
            reporte.append("")

        # Detalles de verificaciones
        reporte.append("📋 DETALLES DE VERIFICACIONES")
        reporte.append("-" * 80)

        # Conexiones de tablas
        if self.resultados["conexiones_tablas"]:
            reporte.append("\n1. CONEXIONES DE TABLAS (Foreign Keys)")
            for tabla, info in self.resultados["conexiones_tablas"].items():
                reporte.append(f"   {tabla}: {info['total_fks']} Foreign Keys")
                for fk in info["foreign_keys"]:
                    reporte.append(
                        f"      - {fk['columna']} → {fk['tabla_referenciada']}.{fk['columna_referenciada']}"
                    )

        # Cálculos financieros
        if self.resultados["calculos_financieros"].get("verificaciones"):
            reporte.append("\n2. VERIFICACIÓN DE CÁLCULOS FINANCIEROS")
            for nombre, datos in self.resultados["calculos_financieros"]["verificaciones"].items():
                reporte.append(f"   {nombre}:")
                for key, value in datos.items():
                    reporte.append(f"      {key}: {value}")

        # Coherencia de datos
        if self.resultados["coherencia_datos"].get("verificaciones"):
            reporte.append("\n3. VERIFICACIÓN DE COHERENCIA DE DATOS")
            for nombre, datos in self.resultados["coherencia_datos"]["verificaciones"].items():
                reporte.append(f"   {nombre}:")
                for key, value in datos.items():
                    reporte.append(f"      {key}: {value}")

        reporte.append("")
        reporte.append("=" * 80)
        reporte.append("Fin del Reporte")
        reporte.append("=" * 80)

        contenido = "\n".join(reporte)

        if archivo_salida:
            with open(archivo_salida, "w", encoding="utf-8") as f:
                f.write(contenido)
            print(f"\n✅ Reporte guardado en: {archivo_salida}")

        return contenido

    def cerrar(self):
        """Cierra la conexión a la base de datos"""
        if self.db:
            self.db.close()


def main():
    """Función principal"""
    auditoria = None
    try:
        # Crear instancia de auditoría
        auditoria = AuditoriaBD()

        # Ejecutar auditoría completa
        resultados = auditoria.ejecutar_auditoria_completa()

        # Generar reporte
        fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_reporte = project_root / "Documentos" / "Auditorias" / f"REPORTE_AUDITORIA_BD_{fecha_str}.txt"

        # Crear directorio si no existe
        archivo_reporte.parent.mkdir(parents=True, exist_ok=True)

        reporte = auditoria.generar_reporte(str(archivo_reporte))

        # Mostrar reporte en consola
        print("\n" + reporte)

        return 0

    except Exception as e:
        print(f"\n❌ Error durante la auditoría: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        if auditoria:
            auditoria.cerrar()


if __name__ == "__main__":
    sys.exit(main())
