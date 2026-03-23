"""One-off patch: crear_pagos_batch partial success after validation."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGOS_PY = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"


def main() -> None:
    text = PAGOS_PY.read_text(encoding="utf-8")

    # Phase 1: dict instead of list + early return only when all rows invalid
    pat_phase1 = re.compile(
        r"        # Fase 1: validacion \(sin insertar\)\. Si hay errores, devolver sin commit\.\r?\n"
        r"\r?\n"
        r"        validation_errors: list\[dict\] = \[\]\r?\n"
        r"(.*?)"
        r"        if validation_errors:\r?\n"
        r"\r?\n"
        r"            return \{\"results\": \[{\"index\": e\[\"index\"\], \"success\": False, \"error\": e\[\"error\"\], \"status_code\": e\[\"status_code\"\]} for e in validation_errors\], \"ok_count\": 0, \"fail_count\": len\(validation_errors\)\}\r?\n"
        r"\r?\n"
        r"\r?\n"
        r"        cedulas_lote = \{\r?\n"
        r"\r?\n"
        r"            \(p\.cedula_cliente or \"\"\)\.strip\(\)\.upper\(\)\r?\n"
        r"\r?\n"
        r"            for p in pagos_list\r?\n"
        r"\r?\n"
        r"            if \(p\.cedula_cliente or \"\"\)\.strip\(\)\r?\n"
        r"\r?\n"
        r"        \}\r?\n"
        r"\r?\n"
        r"        alinear_cedulas_clientes_existentes\(db, cedulas_lote\)",
        re.DOTALL,
    )

    m = pat_phase1.search(text)
    if not m:
        raise SystemExit("Phase1 block pattern not found")

    inner = m.group(1)
    inner_new = inner.replace("validation_errors: list[dict] = []", "errors_by_index: dict[int, dict] = {}")
    inner_new = inner_new.replace(
        'validation_errors.append({"index": idx, "error": "Ya existe un pago con ese numero de documento.", "status_code": 409})',
        'errors_by_index[idx] = {"error": "Ya existe un pago con ese numero de documento.", "status_code": 409}',
    )
    inner_new = re.sub(
        r"validation_errors\.append\(\s*\{\s*\"index\": idx,\s*\"error\": f\"La .+?\",\s*\"status_code\": 400,\s*\}\s*\)",
        'errors_by_index[idx] = {\n\n                        "error": f"La cédula no tiene préstamo registrado: {cedula_normalizada}",\n\n                        "status_code": 400,\n\n                    }',
        inner_new,
        count=1,
        flags=re.DOTALL,
    )
    inner_new = inner_new.replace(
        'validation_errors.append({"index": idx, "error": f"Credito #{payload.prestamo_id} no existe.", "status_code": 400})',
        'errors_by_index[idx] = {"error": f"Credito #{payload.prestamo_id} no existe.", "status_code": 400}',
    )
    inner_new = inner_new.replace(
        'validation_errors.append({"index": idx, "error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404})',
        'errors_by_index[idx] = {"error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404}',
    )

    replacement_tail = """        if len(errors_by_index) == len(pagos_list):

            results = [
                {
                    "index": i,
                    "success": False,
                    "error": errors_by_index[i]["error"],
                    "status_code": errors_by_index[i]["status_code"],
                }
                for i in sorted(errors_by_index)
            ]

            return {"results": results, "ok_count": 0, "fail_count": len(results)}

        cedulas_lote = {
            (pagos_list[i].cedula_cliente or "").strip().upper()
            for i in range(len(pagos_list))
            if i not in errors_by_index and (pagos_list[i].cedula_cliente or "").strip()
        }

        alinear_cedulas_clientes_existentes(db, cedulas_lote)"""

    new_block = (
        "        # Fase 1: validacion (sin insertar). Errores por indice; las filas validas se insertan en fase 2.\n\n"
        + inner_new
        + replacement_tail
    )

    text2 = text[: m.start()] + new_block + text[m.end() :]

    # Phase 2: skip invalid indices, sort results, ok/fail counts
    pat_phase2 = re.compile(
        r"        # Fase 2: transaccion unica\. Crear todos los pagos \(flush\), aplicar a cuotas, un commit al final\.\r?\n"
        r"\r?\n"
        r"        results: list\[dict\] = \[\]\r?\n"
        r"\r?\n"
        r"        try:\r?\n"
        r"\r?\n"
        r"            for idx, payload in enumerate\(pagos_list\):\r?\n"
        r"\r?\n"
        r"                num_doc = docs_en_payload\[idx\] if idx < len\(docs_en_payload\) else normalize_documento\(payload\.numero_documento\)\r?\n"
        r"(.*?)"
        r"                results\.append\(\{\"index\": idx, \"success\": True, \"pago\": _pago_to_response\(row\)\}\)\r?\n"
        r"\r?\n"
        r"            db\.commit\(\)\r?\n"
        r"\r?\n"
        r"            return \{\"results\": results, \"ok_count\": len\(results\), \"fail_count\": 0\}\r?\n",
        re.DOTALL,
    )

    m2 = pat_phase2.search(text2)
    if not m2:
        raise SystemExit("Phase2 block pattern not found")

    phase2_inner = m2.group(1)
    phase2_new = (
        "                if idx in errors_by_index:\n\n"
        "                    err = errors_by_index[idx]\n\n"
        "                    results.append(\n\n"
        "                        {\n\n"
        '                            "index": idx,\n\n'
        '                            "success": False,\n\n'
        '                            "error": err["error"],\n\n'
        '                            "status_code": err["status_code"],\n\n'
        "                        }\n\n"
        "                    )\n\n"
        "                    continue\n\n"
        + phase2_inner
    )

    phase2_full = (
        "        # Fase 2: transaccion unica. Crear pagos validos (flush), aplicar a cuotas, un commit al final.\n\n"
        "        results: list[dict] = []\n\n"
        "        try:\n\n"
        "            for idx, payload in enumerate(pagos_list):\n\n"
        "                num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)\n\n"
        + phase2_new
        + "                results.append({\"index\": idx, \"success\": True, \"pago\": _pago_to_response(row)})\n\n"
        "            db.commit()\n\n"
        "            results.sort(key=lambda r: r[\"index\"])\n\n"
        "            ok_count = sum(1 for r in results if r.get(\"success\"))\n\n"
        "            fail_count = len(results) - ok_count\n\n"
        '            return {"results": results, "ok_count": ok_count, "fail_count": fail_count}\n'
    )

    text3 = text2[: m2.start()] + phase2_full + text2[m2.end() :]

    if "validation_errors" in text3[text3.find("def crear_pagos_batch") : text3.find("@router.post(\"\", response_model=dict", text3.find("def crear_pagos_batch"))]:
        raise SystemExit("validation_errors still present in crear_pagos_batch")

    PAGOS_PY.write_text(text3, encoding="utf-8", newline="\n")
    print("Patched", PAGOS_PY)


if __name__ == "__main__":
    main()
