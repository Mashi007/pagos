# -*- coding: utf-8 -*-
"""Parche unificado: reglas de estado de cuota (Caracas, VENCIDO/MORA 92d)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend")

AMORT_PATH = ROOT / "app/services/prestamos/amortizacion_service.py"
REV_PATH = ROOT / "app/api/v1/endpoints/revision_manual.py"
EJEC_PATH = ROOT / "app/scripts/ejecutar_correcciones_criticas.py"
DIAG_PATH = ROOT / "app/services/diagnostico_critico_service.py"


def patch_amortizacion() -> None:
    t = AMORT_PATH.read_text(encoding="utf-8")
    if "from app.services.cuota_estado import" in t:
        print("amortizacion: ya importa cuota_estado, re-sincronizando bloques clave")
    old_imp = (
        "from app.models.cuota_pago import CuotaPago\n"
        "from .prestamos_calculo import PrestamosCalculo\n"
    )
    new_imp = (
        "from app.models.cuota_pago import CuotaPago\n"
        "from app.services.cuota_estado import (\n"
        "    clasificar_estado_cuota,\n"
        "    dias_retraso_desde_vencimiento,\n"
        "    hoy_negocio,\n"
        ")\n"
        "from .prestamos_calculo import PrestamosCalculo\n"
    )
    if old_imp not in t:
        raise SystemExit("amortizacion: bloque de import no coincide")
    t = t.replace(old_imp, new_imp, 1)

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
    if marker not in t:
        raise SystemExit("amortizacion: marker __init__ no encontrado")
    if "_float_cuota_monto" not in t:
        t = t.replace(marker, helpers, 1)

    t = t.replace(
        "fecha_inicio = prestamo.fecha_base_calculo or date.today()",
        "fecha_inicio = prestamo.fecha_base_calculo or hoy_negocio()",
        1,
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

    if old_reg not in t:
        raise SystemExit("amortizacion: registrar_pago_cuota bloque no coincide")
    t = t.replace(old_reg, new_reg, 1)

    # CuotaPago puede quedar sin uso; dejar import si otros metodos lo usan - grep
    if "CuotaPago(" not in t:
        t = t.replace(
            "from app.models.cuota_pago import CuotaPago\n",
            "",
            1,
        )

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

    if old_calc not in t:
        raise SystemExit("amortizacion: loop calcular_estado_amortizacion no coincide")
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

    if old_venc not in t:
        raise SystemExit("amortizacion: obtener_cuotas_vencidas no coincide")
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

    if old_prox not in t:
        raise SystemExit("amortizacion: obtener_cuotas_proximas no coincide")
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

    if old_pen not in t:
        raise SystemExit("amortizacion: penalizacion bloque no coincide")
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

    if old_ser not in t:
        raise SystemExit("amortizacion: _serializar_cuota dict no coincide")
    t = t.replace(old_ser, new_ser, 1)

    t = t.replace(
        "fecha_inicio = getattr(cuota_anterior, 'fecha_vencimiento', date.today())",
        "fecha_inicio = getattr(cuota_anterior, 'fecha_vencimiento', hoy_negocio())",
        1,
    )
    t = t.replace(
        "fecha_inicio = prestamo.fecha_base_calculo or date.today()",
        "fecha_inicio = prestamo.fecha_base_calculo or hoy_negocio()",
        1,
    )

    # obtener_tabla item dict: monto_pagado -> total_pagado alignment
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

    AMORT_PATH.write_text(t, encoding="utf-8")
    print("amortizacion_service: OK")


def patch_revision_manual() -> None:
    t = REV_PATH.read_text(encoding="utf-8")
    old_imp = "from sqlalchemy import select, func, and_, case\n"
    new_imp = "from sqlalchemy import select, func, and_, case, literal_column\n"
    if old_imp not in t:
        raise SystemExit("revision_manual: import sqlalchemy no coincide")
    t = t.replace(old_imp, new_imp, 1)

    t = t.replace(
        "    estado: Optional[str] = Field(None, pattern=\"^(pendiente|pagado|conciliado|PENDIENTE|PAGADO|CONCILIADO)$\")",
        "    estado: Optional[str] = Field(\n"
        "        None,\n"
        "        pattern=\"^(?i)(pendiente|parcial|vencido|mora|pagado|pago_adelantado|cancelada|PENDIENTE|PARCIAL|VENCIDO|MORA|PAGADO|PAGO_ADELANTADO|CANCELADA)$\",\n"
        "    )",
        1,
    )

    old_agg = """    hoy = date.today()
    umbral_moroso = hoy - timedelta(days=89)
    cedula_trim = cedula.strip() if cedula and cedula.strip() else None
"""

    new_agg = """    hoy_lit = literal_column("(CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date")
    dias_retraso = func.greatest(0, hoy_lit - Cuota.fecha_vencimiento)
    no_pago_completo = func.coalesce(Cuota.total_pagado, 0) < (Cuota.monto - 0.01)
    cedula_trim = cedula.strip() if cedula and cedula.strip() else None
"""

    if old_agg not in t:
        raise SystemExit("revision_manual: bloque hoy/umbral no coincide")
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

    if old_sub not in t:
        raise SystemExit("revision_manual: agg_subq no coincide")
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

    REV_PATH.write_text(t, encoding="utf-8")
    print("revision_manual: OK")


def patch_ejecutar() -> None:
    t = EJEC_PATH.read_text(encoding="utf-8")
    ins = "from sqlalchemy import text\n"
    if "cuota_estado" not in t:
        t = t.replace(
            ins,
            ins + "from app.services.cuota_estado import SQL_PG_ESTADO_CUOTA_CASE_CORRELATED\n",
            1,
        )

    t = t.replace(
        "JOIN cuotas c ON pr.id = c.prestamo_id AND c.estado IN ('PENDIENTE', 'MORA', 'PARCIAL')",
        "JOIN cuotas c ON pr.id = c.prestamo_id AND c.estado IN ('PENDIENTE', 'VENCIDO', 'MORA', 'PARCIAL')",
        1,
    )
    t = t.replace(
        "LEAST(p.monto_pagado, c.monto - COALESCE((",
        "LEAST(p.monto_pagado, c.monto_cuota - COALESCE((",
        1,
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

    if old_inc not in t:
        raise SystemExit("ejecutar: inconsistencias query no coincide")
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

    case_sql = "{SQL_PG_ESTADO_CUOTA_CASE_CORRELATED}"
    new_upd = f"""        case_sql = SQL_PG_ESTADO_CUOTA_CASE_CORRELATED
        result = db.execute(text(f'''
            UPDATE cuotas c SET estado = ({{case_sql}})
            WHERE c.estado IS DISTINCT FROM ({{case_sql}})
        '''))
"""

    if old_upd not in t:
        raise SystemExit("ejecutar: UPDATE estados no coincide")
    t = t.replace(old_upd, new_upd, 1)

    # Fix f-string: we need double braces for literal in file - the new_upd uses {{case_sql}} which becomes {case_sql} in f-string... 
    # Actually we wrote Python source - the file should contain:
    # result = db.execute(text(f'''
    #     UPDATE cuotas c SET estado = ({case_sql})
    #     WHERE c.estado IS DISTINCT FROM ({case_sql})
    # '''))
    # with case_sql = variable - not f-string inside text - use format

    # Re-read - my new_upd is wrong. I need to write valid Python:
    # case_sql = SQL_PG_ESTADO_CUOTA_CASE_CORRELATED
    # result = db.execute(text(f"UPDATE cuotas c SET estado = ({case_sql}) WHERE ..."))

    EJEC_PATH.write_text(t, encoding="utf-8")
    # Re-read and fix botched replacement
    t2 = EJEC_PATH.read_text(encoding="utf-8")
    if "{{case_sql}}" in t2 or "case_sql = SQL_PG" in t2 and "f'''" in t2:
        pass

    print("ejecutar: checking UPDATE block...")
    if "case_sql = SQL_PG_ESTADO_CUOTA_CASE_CORRELATED" not in t2:
        raise SystemExit("ejecutar: case_sql line missing")

    EJEC_PATH.write_text(t2, encoding="utf-8")
    print("ejecutar: OK")


def fix_ejecutar_fstring() -> None:
    """Corrige el bloque UPDATE si quedó con llaves mal escapadas."""
    t = EJEC_PATH.read_text(encoding="utf-8")
    bad = """        case_sql = SQL_PG_ESTADO_CUOTA_CASE_CORRELATED
        result = db.execute(text(f'''
            UPDATE cuotas c SET estado = ({case_sql})
            WHERE c.estado IS DISTINCT FROM ({case_sql})
        '''))
"""
    good = """        case_sql = SQL_PG_ESTADO_CUOTA_CASE_CORRELATED
        result = db.execute(
            text(f"UPDATE cuotas c SET estado = ({case_sql}) "
                 f"WHERE c.estado IS DISTINCT FROM ({case_sql})")
        )
"""
    if bad in t:
        t = t.replace(bad, good, 1)
        EJEC_PATH.write_text(t, encoding="utf-8")
        print("ejecutar: fstring corregido")


def patch_diagnostico() -> None:
    t = DIAG_PATH.read_text(encoding="utf-8")
    ins = "from sqlalchemy import and_, text\n"
    if "SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE" not in t:
        t = t.replace(
            ins,
            ins + "from app.services.cuota_estado import SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE\n",
            1,
        )

    old_case_block = """              CASE 
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
                WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                ELSE 'PENDIENTE'
              END as estado_calculado,"""

    new_case_block = (
        "              "
        + "{SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE} as estado_calculado,"
    )

    if old_case_block not in t:
        raise SystemExit("diagnostico: bloque CASE diagnostico no encontrado")
    t = t.replace(old_case_block, new_case_block, 1)

    # Use f-string file-level: diagnostic file needs case_sql variable before query - replace with .format
    t = t.replace(
        "{SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE} as estado_calculado,",
        "{agg} as estado_calculado,",
        1,
    )

    # Inject agg = ... at start of method - find def diagnosticar_estados_inconsistentes
    marker = "    def diagnosticar_estados_inconsistentes(db: Session) -> dict:\n"
    idx = t.find(marker)
    if idx < 0:
        raise SystemExit("diagnostico: metodo no encontrado")
    insert_at = t.find('        """Diagnostica', idx)
    agg_line = (
        '        agg = SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE\n'
        '        cuotas_mora = db.query(text(f\'\'\'\n'
    )
    # The query starts with cuotas_mora = db.query(text(''' - replace opening
    old_open = (
        "        cuotas_mora = db.query(text('''\n"
        "            SELECT \n"
    )
    if old_open not in t:
        raise SystemExit("diagnostico: apertura query no encontrada")
    t = t.replace(
        old_open,
        "        cuotas_mora = db.query(text(f'''\n            SELECT \n",
        1,
    )

    # Replace {agg} placeholder - need to fix closing ''' to '''))  - actually f''' with {agg}
    t = t.replace("{agg} as estado_calculado,", "{agg} as estado_calculado,")
    t = t.replace("{agg}", "{SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE}", 1)

    # Add f prefix already. Now use variable in f-string:
    t = t.replace(
        "cuotas_mora = db.query(text(f'''",
        "cuotas_mora = db.query(text(f'''",
        1,
    )

    # Replace the line with {SQL_PG...} inside f-string - must be single brace
    t = t.replace(
        "{SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE} as estado_calculado,",
        f"{SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE} as estado_calculado,",
    )

This script got too messy. Let me simplify patch_diagnostico by reading current file and doing precise replace.

I'll abort the write tool partial script and instead run smaller patches manually.

Actually the Write already created a broken file. I need to delete it and create a clean script or fix patch_ejecutar in the file.

Let me read what was written to tools/_patch_universal_cuota_estado.py
</think>


<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
Read