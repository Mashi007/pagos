"""One-off fixes for corrupted TS patterns (incomplete ternaries, bad BOM)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

DOUBLE_BOM = "\ufeff"  # after wrong decode sometimes
# UTF-8 BOM read as Latin-1 then UTF-8 produces this sequence at start:
MOJIBAKE_BOM_BYTES = b"\xc3\xaf\xc2\xbb\xc2\xbf"


def strip_bad_bom_bytes(data: bytes) -> bytes:
    if data.startswith(MOJIBAKE_BOM_BYTES):
        return data[len(MOJIBAKE_BOM_BYTES) :]
    return data


def fix_exceljs(content: str) -> str:
    # Incomplete ternaries introduced by corruption: `expr ? '')`  -> nullish coalescing
    content = content.replace(
        ".map((x: any) => x?.text ? '').join('')",
        ".map((x: any) => x?.text ?? '').join('')",
    )
    content = content.replace(
        "headers.map(header => row[header] ? '')",
        "headers.map(header => row[header] ?? '')",
    )
    return content


def fix_export_utils_interes(content: str) -> str:
    # Avoid problematic identifier if compiler chokes on composed chars
    return content.replace(
        "(d.Interés as number)",
        "(d['Interés'] as number)",
    )


def restore_pago_excel_validation() -> None:
    """Restore from git object if current file has box-drawing garbage at start."""
    import subprocess

    target = SRC / "utils" / "pagoExcelValidation.ts"
    data = target.read_bytes()
    if data.startswith(b"/**") or data.startswith(b"\xef\xbb\xbf/**"):
        return
    # Known-good-ish snapshot (starts with /**)
    blob = subprocess.check_output(
        ["git", "show", "d2e01e2b:frontend/src/utils/pagoExcelValidation.ts"],
        cwd=ROOT.parent,
    )
    blob = strip_bad_bom_bytes(blob)
    if blob.startswith(b"\xff\xfe"):
        text = blob[2:].decode("utf-16-le")
    elif blob.startswith(b"\xfe\xff"):
        text = blob[2:].decode("utf-16-be")
    else:
        text = blob.decode("utf-8", errors="replace")
    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    target.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    # Strip mojibake BOM from all TS/TSX
    for path in list(SRC.rglob("*.ts")) + list(SRC.rglob("*.tsx")):
        raw = path.read_bytes()
        new_raw = strip_bad_bom_bytes(raw)
        if new_raw != raw:
            path.write_bytes(new_raw)

    exceljs = SRC / "types" / "exceljs.ts"
    if exceljs.exists():
        t = exceljs.read_text(encoding="utf-8")
        nt = fix_exceljs(t)
        if nt != t:
            exceljs.write_text(nt, encoding="utf-8", newline="\n")

    export_utils = SRC / "utils" / "exportUtils.ts"
    if export_utils.exists():
        t = export_utils.read_text(encoding="utf-8")
        nt = fix_export_utils_interes(t)
        if nt != t:
            export_utils.write_text(nt, encoding="utf-8", newline="\n")

    restore_pago_excel_validation()

if __name__ == "__main__":
    main()
