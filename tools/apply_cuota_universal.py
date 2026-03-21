# -*- coding: utf-8 -*-
"""Aplica reglas unificadas de estado de cuota en backend (parches idempotentes)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
AMORT = ROOT / "app/services/prestamos/amortizacion_service.py"
REV = ROOT / "app/api/v1/endpoints/revision_manual.py"
EJEC = ROOT / "app/scripts/ejecutar_correcciones_criticas.py"
DIAG = ROOT / "app/services/diagnostico_critico_service.py"


def main() -> None:
    patch_amortizacion()
    patch_revision_manual()
    patch_ejecutar()
    patch_diagnostico()
    print("done")


def patch_amortizacion() -> None:
    t = AMORT.read_text(encoding="utf-8")
    old_imp = (
        "from app.models.cuota_pago import CuotaPago\n"
        "from .prestamos_calculo import PrestamosCalculo\n"
    )
    new_imp = (
        "from app.services.cuota_estado import (\n"
        "    clasificar_estado_cuota,\n"
        "    dias_retraso_desde_vencimiento,\n"
        "    hoy_negocio,\n"
        ")\n"
        "from .prestamos_calculo import PrestamosCalculo\n"
    )
    if "from app.services.cuota_estado import" not in t:
        if old_imp not in t:
            raise SystemExit("amort: import block mismatch")
        t = t.replace(old_imp, new_imp, 1)
    if "CuotaPago" in t and "CuotaPago(" not in t:
        pass

    marker = "        self.calculo = PrestamosCalculo(db)\n\n"
    helpers = (
        "        self.calculo = PrestamosCalculo(db)\n\n"
        "    @staticmethod\n"
        "    def _float_cuota_monto(cuota) -> float:\n"
        "        v = getattr(cuota, \"monto\", None)\n"
        "        if v is None:\n"
        "            v = getattr(cuota, \"monto_cuota\", None)\n"
        "        return float(v or 0)\n\n"
        "    @staticmethod\n"
        "    def _float_total_pagado(cuota) -> float:\n"
        "        return float(getattr(cuota, \"total_pagado\", None) or 0)\n\n"
        "    def _cuota_esta_pagada_completa(self, cuota) -> bool:\n"
        "        return self._float_total_pagado(cuota) >= self._float_cuota_monto(cuota) - 0.01\n\n"
    )
    if "_float_cuota_monto" not in t and marker in t:
        t = t.replace(marker, helpers, 1)

    t = t.replace(
        "fecha_inicio = prestamo.fecha_base_calculo or date.today()",
        "fecha_inicio = prestamo.fecha_base_calculo or hoy_negocio()",
    )

    old_reg = '''    def registrar_pago_cuota(
        self,
        cuota_id: int,
        monto_pagado: float,
        fecha_pago: Optional[date] = None
    ) -> Dict:
        """
        Registra un pago de cuota.

        Args:
            cuota_id: ID de la cuota
            monto_pagado: Monto pagado
            fecha_pago: Fecha del pago (default: hoy)

        Returns:
            Información actualizada de la cuota
        """
        if fecha_pago is None:
            fecha_pago = date.today()

        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        monto_cuota = float(getattr(cuota, 'monto_cuota', 0.0))
        monto_actual = float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0

        # Actualizar monto pagado
        nuevo_total = monto_actual + monto_pagado
        monto_restante = max(monto_cuota - nuevo_total, 0.0)

        # Determinar estado
        if monto_restante <= 0:
            estado = 'PAGADO'
            pagado = True
        elif nuevo_total > 0:
            estado = 'PARCIAL'
            pagado = False
        else:
            estado = 'PENDIENTE'
            pagado = False

        # Actualizar cuota
        if hasattr(cuota, 'monto_pagado'):
            cuota.monto_pagado = Decimal(str(nuevo_total))
        if hasattr(cuota, 'estado'):
            cuota.estado = estado
        if hasattr(cuota, 'pagado'):
            cuota.pagado = pagado

        self.db.add(cuota)
        self.db.commit()
        self.db.refresh(cuota)

        # Registrar movimiento de pago si existe tabla CuotaPago
        try:
            pago = CuotaPago(
                cuota_id=cuota_id,
                monto=Decimal(str(monto_pagado)),
                fecha_pago=fecha_pago,
            )
            self.db.add(pago)
            self.db.commit()
        except Exception:
            # Si la tabla CuotaPago no existe, continuar
            pass

        return self.obtener_cuota(cuota_id)
'''

    new_reg = '''    def registrar_pago_cuota(
        self,
        cuota_id: int,
        monto_pagado: float,
        fecha_pago: Optional[date] = None
    ) -> Dict:
        """
        Registra un pago de cuota.

        Args:
            cuota_id: ID de la cuota
            monto_pagado: Monto pagado
            fecha_pago: Fecha del pago (default: hoy negocio Caracas)

        Returns:
            Información actualizada de la cuota
        """
        if fecha_pago is None:
            fecha_pago = hoy_negocio()

        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        monto_cuota = self._float_cuota_monto(cuota)
        monto_actual = self._float_total_pagado(cuota)
        nuevo_total = monto_actual + float(monto_pagado or 0)

        estado = clasificar_estado_cuota(
            nuevo_total,
            monto_cuota,
            getattr(cuota, "fecha_vencimiento", None),
            fecha_pago,
        )

        if hasattr(cuota, "total_pagado"):
            cuota.total_pagado = Decimal(str(round(nuevo_total, 2)))
        if hasattr(cuota, "estado"):
            cuota.estado = estado

        self.db.add(cuota)
        self.db.commit()
        self.db.refresh(cuota)

        return self.obtener_cuota(cuota_id)
'''

    if old_reg in t:
        t = t.replace(old_reg, new_reg, 1)
    if "from app.models.cuota_pago import CuotaPago\n" in t and "CuotaPago(" not in t:
        t = t.replace("from app.models.cuota_pago import CuotaPago\n", "", 1)

    old_calc = '''        hoy = date.today()

        for cuota in cuotas:
            estado = getattr(cuota, 'estado', 'PENDIENTE')
            fecha_vencimiento = getattr(cuota, 'fecha_vencimiento', None)
            monto_cuota = float(getattr(cuota, 'monto_cuota', 0.0)) or 0.0
            monto_pagado = float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0

            if estado == 'PAGADO':
                cuotas_pagadas += 1
            elif estado == 'PARCIAL':
                cuotas_parciales += 1
                saldo_total += monto_cuota - monto_pagado
            else:
                cuotas_pendientes += 1
                saldo_total += monto_cuota - monto_pagado

                # Verificar atraso
                if fecha_vencimiento and fecha_vencimiento < hoy:
                    cuotas_en_atraso += 1

            monto_pagado_total += monto_pagado

            # Próxima cuota sin pagar
            if proxima_cuota_vencimiento is None and estado != 'PAGADO':
                proxima_cuota_vencimiento = fecha_vencimiento
'''

    new_calc = '''        hoy = hoy_negocio()

        for cuota in cuotas:
            fecha_vencimiento = getattr(cuota, "fecha_vencimiento", None)
            monto_cuota = self._float_cuota_monto(cuota)
            paid = self._float_total_pagado(cuota)
            estado = clasificar_estado_cuota(
                paid, monto_cuota, fecha_vencimiento, hoy
            )

            if estado in ("PAGADO", "PAGO_ADELANTADO"):
                cuotas_pagadas += 1
            elif estado == "PARCIAL":
                cuotas_parciales += 1
                saldo_total += max(monto_cuota - paid, 0.0)
            else:
                cuotas_pendientes += 1
                saldo_total += max(monto_cuota - paid, 0.0)
                if dias_retraso_desde_vencimiento(fecha_vencimiento, hoy) >= 1:
                    cuotas_en_atraso += 1

            monto_pagado_total += paid

            if proxima_cuota_vencimiento is None and estado not in (
                "PAGADO",
                "PAGO_ADELANTADO",
            ):
                proxima_cuota_vencimiento = fecha_vencimiento
'''

    if old_calc in t:
        t = t.replace(old_calc, new_calc, 1)

    old_venc = '''    def obtener_cuotas_vencidas(self, prestamo_id: int) -> List[Dict]:
        """Obtiene todas las cuotas vencidas de un préstamo."""
        hoy = date.today()

        cuotas = self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != 'PAGADO'
            )
        ).order_by(Cuota.numero_cuota).all()

        return [self._serializar_cuota(c) for c in cuotas]
'''

    new_venc = '''    def obtener_cuotas_vencidas(self, prestamo_id: int) -> List[Dict]:
        """Cuotas no cubiertas al 100% con al menos 1 dia de retraso (Caracas)."""
        hoy = hoy_negocio()
        cuotas = (
            self.db.query(Cuota)
            .filter(Cuota.prestamo_id == prestamo_id)
            .order_by(Cuota.numero_cuota)
            .all()
        )
        out = []
        for c in cuotas:
            if self._cuota_esta_pagada_completa(c):
                continue
            if dias_retraso_desde_vencimiento(c.fecha_vencimiento, hoy) >= 1:
                out.append(c)
        return [self._serializar_cuota(c) for c in out]
'''

    if old_venc in t:
        t = t.replace(old_venc, new_venc, 1)

    old_prox = '''        hoy = date.today()
        fecha_limite = hoy + timedelta(days=dias_adelante)

        cuotas = self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_vencimiento >= hoy,
                Cuota.fecha_vencimiento <= fecha_limite,
                Cuota.estado != 'PAGADO'
            )
        ).order_by(Cuota.numero_cuota).all()

        return [self._serializar_cuota(c) for c in cuotas]
'''

    new_prox = '''        hoy = hoy_negocio()
        fecha_limite = hoy + timedelta(days=dias_adelante)

        cuotas = self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_vencimiento >= hoy,
                Cuota.fecha_vencimiento <= fecha_limite,
            )
        ).order_by(Cuota.numero_cuota).all()

        return [
            self._serializar_cuota(c)
            for c in cuotas
            if not self._cuota_esta_pagada_completa(c)
        ]
'''

    if old_prox in t:
        t = t.replace(old_prox, new_prox, 1)

    old_pen = '''        hoy = date.today()
        if fecha_vencimiento >= hoy:
            return 0.0

        dias_atraso = (hoy - fecha_vencimiento).days
        monto_cuota = float(getattr(cuota, 'monto_cuota', 0.0)) or 0.0
'''

    new_pen = '''        hoy = hoy_negocio()
        fv = fecha_vencimiento
        if isinstance(fv, datetime):
            fv = fv.date()
        if fv is None or fv >= hoy:
            return 0.0

        dias_atraso = dias_retraso_desde_vencimiento(fv, hoy)
        monto_cuota = self._float_cuota_monto(cuota)
'''

    if old_pen in t:
        t = t.replace(old_pen, new_pen, 1)

    old_ser = """            'monto_cuota': float(getattr(cuota, 'monto_cuota', 0.0)),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0,
        }"""

    new_ser = """            'monto_cuota': self._float_cuota_monto(cuota),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': self._float_total_pagado(cuota),
            'total_pagado': self._float_total_pagado(cuota),
        }"""

    if old_ser in t:
        t = t.replace(old_ser, new_ser, 1)

    t = t.replace(
        "fecha_inicio = getattr(cuota_anterior, 'fecha_vencimiento', date.today())",
        "fecha_inicio = getattr(cuota_anterior, 'fecha_vencimiento', hoy_negocio())",
    )

    old_item = """                'monto_cuota': float(cuota.monto_cuota) if hasattr(cuota, 'monto_cuota') else 0.0,
                'interes_cuota': float(cuota.interes_cuota) if hasattr(cuota, 'interes_cuota') else 0.0,
                'amortizacion_cuota': float(cuota.amortizacion_cuota) if hasattr(cuota, 'amortizacion_cuota') else 0.0,
                'saldo_vigente': float(cuota.saldo_vigente) if hasattr(cuota, 'saldo_vigente') else 0.0,
                'estado': getattr(cuota, 'estado', 'PENDIENTE'),
                'pagado': getattr(cuota, 'pagado', False),
                'monto_pagado': float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0,
            }"""

    new_item = """                'monto_cuota': AmortizacionService._float_cuota_monto(cuota),
                'interes_cuota': float(cuota.interes_cuota) if hasattr(cuota, 'interes_cuota') else 0.0,
                'amortizacion_cuota': float(cuota.amortizacion_cuota) if hasattr(cuota, 'amortizacion_cuota') else 0.0,
                'saldo_vigente': float(cuota.saldo_vigente) if hasattr(cuota, 'saldo_vigente') else 0.0,
                'estado': getattr(cuota, 'estado', 'PENDIENTE'),
                'pagado': getattr(cuota, 'pagado', False),
                'monto_pagado': AmortizacionService._float_total_pagado(cuota),
                'total_pagado': AmortizacionService._float_total_pagado(cuota),
            }"""

    if old_item in t:
        t = t.replace(old_item, new_item, 1)

    old_obt = """            'monto_cuota': float(getattr(cuota, 'monto_cuota', 0.0)),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': float(getattr(cuota, 'monto_pagado', 0.0)),
        }"""

    new_obt = """            'monto_cuota': self._float_cuota_monto(cuota),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': self._float_total_pagado(cuota),
            'total_pagado': self._float_total_pagado(cuota),
        }"""

    if old_obt in t:
        t = t.replace(old_obt, new_obt, 1)

    AMORT.write_text(t, encoding="utf-8")
    print("amortizacion_service OK")


def patch_revision_manual() -> None:
    t = REV.read_text(encoding="utf-8")
    if "literal_column" not in t.split("from sqlalchemy import", 1)[1].split("\n", 1)[0]:
        t = t.replace(
            "from sqlalchemy import select, func, and_, case\n",
            "from sqlalchemy import select, func, and_, case, literal_column\n",
            1,
        )

    old_field = (
        '    estado: Optional[str] = Field(None, pattern="^(pendiente|pagado|conciliado|PENDIENTE|PAGADO|CONCILIADO)$")'
    )
    new_field = """    estado: Optional[str] = Field(
        None,
        pattern="^(?i)(pendiente|parcial|vencido|mora|pagado|pago_adelantado|cancelada|PENDIENTE|PARCIAL|VENCIDO|MORA|PAGADO|PAGO_ADELANTADO|CANCELADA)$",
    )"""
    if old_field in t:
        t = t.replace(old_field, new_field, 1)

    old_agg = """    hoy = date.today()
    umbral_moroso = hoy - timedelta(days=89)
    cedula_trim = cedula.strip() if cedula and cedula.strip() else None
"""

    new_agg = """    hoy_lit = literal_column("(CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date")
    dias_retraso = func.greatest(0, hoy_lit - Cuota.fecha_vencimiento)
    no_pago_completo = func.coalesce(Cuota.total_pagado, 0) < (Cuota.monto - 0.01)
    cedula_trim = cedula.strip() if cedula and cedula.strip() else None
"""

    if old_agg in t:
        t = t.replace(old_agg, new_agg, 1)

    old_sub = """    agg_subq = (
        select(
            Cuota.prestamo_id,
            func.coalesce(func.sum(case((Cuota.fecha_pago.isnot(None), Cuota.total_pagado), else_=0)), 0).label("total_abonos"),
            func.sum(case((and_(Cuota.fecha_vencimiento < hoy, Cuota.fecha_pago.is_(None)), 1), else_=0)).label("vencidas"),
            func.sum(case((and_(Cuota.fecha_vencimiento < umbral_moroso, Cuota.fecha_pago.is_(None)), 1), else_=0)).label("morosas"),
        )
        .where(Cuota.prestamo_id.in_(prestamo_ids))
        .group_by(Cuota.prestamo_id)
    )
"""

    new_sub = """    agg_subq = (
        select(
            Cuota.prestamo_id,
            func.coalesce(func.sum(Cuota.total_pagado), 0).label("total_abonos"),
            func.sum(
                case(
                    (
                        and_(no_pago_completo, dias_retraso >= 1, dias_retraso < 92),
                        1,
                    ),
                    else_=0,
                )
            ).label("vencidas"),
            func.sum(
                case(
                    (and_(no_pago_completo, dias_retraso >= 92), 1),
                    else_=0,
                )
            ).label("morosas"),
        )
        .where(Cuota.prestamo_id.in_(prestamo_ids))
        .group_by(Cuota.prestamo_id)
    )
"""

    if old_sub in t:
        t = t.replace(old_sub, new_sub, 1)

    t = t.replace(
        '        estados_validos = ["PENDIENTE", "PAGADO", "CONCILIADO"]',
        '        estados_validos = [\n'
        '            "PENDIENTE",\n'
        '            "PARCIAL",\n'
        '            "VENCIDO",\n'
        '            "MORA",\n'
        '            "PAGADO",\n'
        '            "PAGO_ADELANTADO",\n'
        '            "CANCELADA",\n'
        "        ]",
        1,
    )

    REV.write_text(t, encoding="utf-8")
    print("revision_manual OK")


def patch_ejecutar() -> None:
    t = EJEC.read_text(encoding="utf-8")
    if "SQL_PG_ESTADO_CUOTA_CASE_CORRELATED" not in t:
        t = t.replace(
            "from sqlalchemy import text\n",
            "from sqlalchemy import text\n"
            "from app.services.cuota_estado import SQL_PG_ESTADO_CUOTA_CASE_CORRELATED\n",
            1,
        )

    t = t.replace(
        "JOIN cuotas c ON pr.id = c.prestamo_id AND c.estado IN ('PENDIENTE', 'MORA', 'PARCIAL')",
        "JOIN cuotas c ON pr.id = c.prestamo_id AND c.estado IN ('PENDIENTE', 'VENCIDO', 'MORA', 'PARCIAL')",
    )
    t = t.replace(
        "LEAST(p.monto_pagado, c.monto - COALESCE((",
        "LEAST(p.monto_pagado, c.monto_cuota - COALESCE((",
    )

    old_inc = """            SELECT COUNT(*) FROM cuotas c
            LEFT JOIN cuota_pagos cp ON c.id = cp.cuota_id
            WHERE c.estado NOT IN ('PAGADO', 'PARCIAL', 'MORA', 'PENDIENTE', 'CANCELADA')
        """

    new_inc = """            SELECT COUNT(*) FROM cuotas c
            WHERE c.estado NOT IN (
              'PAGADO', 'PAGO_ADELANTADO', 'PARCIAL', 'VENCIDO',
              'MORA', 'PENDIENTE', 'CANCELADA'
            )
        """

    if old_inc in t:
        t = t.replace(old_inc, new_inc, 1)

    old_upd = """        result = db.execute(text('''
            UPDATE cuotas c SET estado = CASE 
                WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) >= c.monto - 0.01 THEN 'PAGADO'
                WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) > 0 THEN 'PARCIAL'
                WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                ELSE 'PENDIENTE' END
            WHERE c.estado IS NULL
        '''))
"""

    new_upd = """        case_sql = SQL_PG_ESTADO_CUOTA_CASE_CORRELATED
        result = db.execute(
            text(
                "UPDATE cuotas c SET estado = ("
                + case_sql
                + ") WHERE c.estado IS DISTINCT FROM ("
                + case_sql
                + ")"
            )
        )
"""

    if old_upd in t:
        t = t.replace(old_upd, new_upd, 1)

    t = re.sub(r"\bc\.monto\b", "c.monto_cuota", t)

    EJEC.write_text(t, encoding="utf-8")
    print("ejecutar_correcciones_criticas OK")


def _sql_pg_estado_cuota_aggregate() -> str:
    ce = (ROOT / "app/services/cuota_estado.py").read_text(encoding="utf-8")
    m = re.search(
        r'SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE = """(.*?)"""',
        ce,
        re.DOTALL,
    )
    if not m:
        raise SystemExit("cuota_estado.py: no se encontro SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE")
    return m.group(1).strip()


def patch_diagnostico() -> None:
    agg = _sql_pg_estado_cuota_aggregate()
    t = DIAG.read_text(encoding="utf-8")

    old_case_select = """              CASE 
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
                WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                ELSE 'PENDIENTE'
              END as estado_calculado,"""

    new_case_select = "              " + agg + " as estado_calculado,"

    if old_case_select in t:
        t = t.replace(old_case_select, new_case_select, 1)

    old_inner = """                    CASE 
                      WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
                      WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
                      WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                      ELSE 'PENDIENTE'
                    END as estado_correcto"""

    new_inner = "\n                    " + agg + " as estado_correcto"

    if old_inner in t:
        t = t.replace(old_inner, new_inner, 1)

    t = re.sub(r"\bc\.monto\b", "c.monto_cuota", t)

    DIAG.write_text(t, encoding="utf-8")
    print("diagnostico_critico_service OK")


if __name__ == "__main__":
    main()
