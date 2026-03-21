# -*- coding: utf-8 -*-
"""
Unifica estado de cuota: un solo calculo en backend (cuota_estado + etiqueta).
Anade estado_etiqueta en API y exportaciones; PDF estado cuenta arma etiqueta al vuelo de datos.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
prestamos = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
ec_pub = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"
ec_pdf = ROOT / "backend" / "app" / "services" / "estado_cuenta_pdf.py"


def patch_prestamos() -> None:
    t = prestamos.read_text(encoding="utf-8")
    if '"estado_etiqueta": etiqueta_estado_cuota(estado_mostrar)' in t.split("get_cuotas_prestamo", 1)[1][:2500]:
        print("prestamos get_cuotas: skip")
    else:
        t = t.replace(
            '"estado": estado_mostrar,\n\n            "dias_mora"',
            '"estado": estado_mostrar,\n\n            "estado_etiqueta": etiqueta_estado_cuota(estado_mostrar),\n\n            "dias_mora"',
            1,
        )
    if '"estado_etiqueta": etiqueta_estado_cuota(estado_mostrar)' not in t.split("_obtener_cuotas_para_export", 1)[1][:1200]:
        t = t.replace(
            '"estado": estado_mostrar,\n\n        })',
            '"estado": estado_mostrar,\n\n            "estado_etiqueta": etiqueta_estado_cuota(estado_mostrar),\n\n        })',
            1,
        )
    else:
        print("prestamos export: ok or skip")

    t = t.replace(
        '                c["estado"],\n\n            ])',
        '                c.get("estado_etiqueta") or c.get("estado") or "-",\n\n            ])',
        1,
    )

    old_ex = '            c["estado"],\n\n        ])'
    new_ex = '            c.get("estado_etiqueta") or c.get("estado") or "-",\n\n        ])'
    if old_ex in t:
        t = t.replace(old_ex, new_ex, 1)

    prestamos.write_text(t, encoding="utf-8", newline="\n")
    print("prestamos.py updated")


def patch_estado_cuenta_publico() -> None:
    t = ec_pub.read_text(encoding="utf-8")
    if "etiqueta_estado_cuota" not in t.split("cuota_estado import", 1)[1][:80]:
        t = t.replace(
            "from app.services.cuota_estado import estado_cuota_para_mostrar, hoy_negocio",
            "from app.services.cuota_estado import (\n    estado_cuota_para_mostrar,\n    etiqueta_estado_cuota,\n    hoy_negocio,\n)",
        )

    pend_needle = '"estado": estado_mostrar,\n\n            })'
    pend_repl = '"estado": estado_mostrar,\n\n                "estado_etiqueta": etiqueta_estado_cuota(estado_mostrar),\n\n            })'
    if pend_needle in t and '"estado_etiqueta": etiqueta_estado_cuota(estado_mostrar)' not in t.split("cuotas_pendientes.append", 1)[1][:400]:
        t = t.replace(pend_needle, pend_repl, 1)

    amort_needle = '"estado": estado_mostrar,\n\n        })'
    amort_repl = '"estado": estado_mostrar,\n\n            "estado_etiqueta": etiqueta_estado_cuota(estado_mostrar),\n\n        })'
    # unique to _obtener_amortizacion resultado.append
    if (
        '"pago_conciliado_display": pago_conciliado_display' in t
        and '"estado_etiqueta"' not in t.split("def _obtener_amortizacion_prestamo", 1)[1][:900]
    ):
        t = t.replace(
            '"pago_conciliado_display": pago_conciliado_display,\n\n            "estado": estado_mostrar,',
            '"pago_conciliado_display": pago_conciliado_display,\n\n            "estado": estado_mostrar,\n\n            "estado_etiqueta": etiqueta_estado_cuota(estado_mostrar),',
            1,
        )

    ec_pub.write_text(t, encoding="utf-8", newline="\n")
    print("estado_cuenta_publico.py updated")


def patch_estado_cuenta_pdf_service() -> None:
    t = ec_pdf.read_text(encoding="utf-8")
    # Cuotas pendientes row: prefer estado_etiqueta
    t = t.replace(
        "etiqueta_estado_cuota(str(c.get(\"estado\") or \"\"))[:28],",
        '(c.get("estado_etiqueta") or etiqueta_estado_cuota(str(c.get("estado") or "")))[:32],',
        1,
    )

    # Amortizacion: use precomputed estado_etiqueta when present
    old_am = """                estado_codigo = (c.get("estado") or "").strip().upper()

                estado_etiqueta = etiqueta_estado_cuota(c.get("estado") or "")"""
    new_am = """                estado_codigo = (c.get("estado") or "").strip().upper()

                estado_etiqueta = (c.get("estado_etiqueta") or "").strip() or etiqueta_estado_cuota(c.get("estado") or "")"""
    if old_am in t:
        t = t.replace(old_am, new_am, 1)

    # obtener_datos_estado_cuenta_prestamo cuotas_pendientes
    t2 = t.split("def obtener_datos_estado_cuenta_prestamo", 1)[1]
    if '"estado_etiqueta"' not in t2.split("cuotas_pendientes.append", 1)[0][-800:]:
        t = t.replace(
            '"estado": estado_mostrar,\n\n        })',
            '"estado": estado_mostrar,\n\n            "estado_etiqueta": etiqueta_estado_cuota(estado_mostrar),\n\n        })',
            1,
        )

    if "cuotas_data.append" in t and '"estado_etiqueta"' not in t.split("cuotas_data.append", 1)[1][:500]:
        t = t.replace(
            '"pago_conciliado_display": pago_conc_display,\n\n                    "estado": estado_cuota,',
            '"pago_conciliado_display": pago_conc_display,\n\n                    "estado": estado_cuota,\n\n                    "estado_etiqueta": etiqueta_estado_cuota(estado_cuota),',
            1,
        )

    ec_pdf.write_text(t, encoding="utf-8", newline="\n")
    print("estado_cuenta_pdf.py updated")


def main() -> None:
    patch_prestamos()
    patch_estado_cuenta_publico()
    patch_estado_cuenta_pdf_service()


if __name__ == "__main__":
    main()
