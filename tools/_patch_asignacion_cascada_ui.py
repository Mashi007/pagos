# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_frontend() -> None:
    p = ROOT / "frontend" / "src" / "pages" / "EstadoCuentaPublicoPage.tsx"
    t = p.read_text(encoding="utf-8")
    old = """                <p className="-mt-4 pb-2 text-center text-sm text-slate-500">
                  Los datos reflejan el estado al momento de esta consulta. Cada
                  nueva consulta muestra los pagos más recientes.
                </p>"""
    new = """                <p className="-mt-4 pb-2 text-center text-sm text-slate-500">
                  Los datos reflejan el estado al momento de esta consulta. Cada
                  nueva consulta muestra los pagos más recientes.
                </p>
                <p className="pb-2 text-center text-xs text-slate-500">
                  Los pagos a cuotas se muestran según{' '}
                  <span className="font-semibold text-slate-600">
                    asignación en cascada
                  </span>
                  : se aplican en orden por número de cuota.
                </p>"""
    if old not in t:
        raise SystemExit("EstadoCuentaPublicoPage: bloque no encontrado")
    p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
    print("OK frontend EstadoCuentaPublicoPage.tsx")


def patch_pdf() -> None:
    p = ROOT / "backend" / "app" / "services" / "estado_cuenta_pdf.py"
    t = p.read_text(encoding="utf-8")
    old = """    story.append(Spacer(1, 12))



    # ----- Tabla Préstamos -----"""
    # File may use Préstamos or Prestamos - check
    if old not in t:
        old = """    story.append(Spacer(1, 12))



    # ----- Tabla Prestamos -----"""
    if old not in t:
        # Fallback: search line by line
        lines = t.splitlines(keepends=True)
        out = []
        i = 0
        inserted = False
        while i < len(lines):
            out.append(lines[i])
            if (
                not inserted
                and i + 1 < len(lines)
                and "story.append(Spacer(1, 12))" in lines[i]
                and "# ----- Tabla" in lines[i + 2]
            ):
                out.append(
                    "\n    story.append(\n"
                    '        Paragraph(\n'
                    '            "Asignación en cascada: los pagos conciliados se aplican a las cuotas "\n'
                    '            "en orden por número de cuota.",\n'
                    '            styles["InfoText"],\n'
                    "        )\n"
                    "    )\n"
                    "    story.append(Spacer(1, 8))\n"
                )
                inserted = True
            i += 1
        if not inserted:
            raise SystemExit("estado_cuenta_pdf: punto de inserción no encontrado")
        p.write_text("".join(out), encoding="utf-8", newline="\n")
        print("OK backend estado_cuenta_pdf.py (fallback)")
        return

    new = """    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "Asignación en cascada: los pagos conciliados se aplican a las cuotas "
            "en orden por número de cuota.",
            styles["InfoText"],
        )
    )
    story.append(Spacer(1, 8))

    # ----- Tabla Préstamos -----"""
    if "# ----- Tabla Préstamos -----" not in t:
        new = new.replace("# ----- Tabla Préstamos -----", "# ----- Tabla Prestamos -----")
    p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
    print("OK backend estado_cuenta_pdf.py")


if __name__ == "__main__":
    patch_frontend()
    patch_pdf()
