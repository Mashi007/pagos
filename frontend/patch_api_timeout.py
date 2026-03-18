# Add check-emails / check-cedulas to slow endpoints with 60s timeout
path = "src/services/api.ts"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old1 = """                            url.includes('/pagos/gmail/run-now') // Pipeline Gmail: puede tardar si el backend es s"""
# We need to find the exact string - try with the line that ends isSlowEndpoint
old_slow = """                            url.includes('/pagos/gmail/run-now') // Pipeline Gmail: puede tardar si el backend es sncrono (credenciales OAuth)"""

# Try without special chars
old_slow2 = "url.includes('/pagos/gmail/run-now')"
new_slow2 = "url.includes('/pagos/gmail/run-now') ||\n                            url.includes('/clientes/check-emails') ||\n                            url.includes('/clientes/check-cedulas')"

# Replace: the line that has only run-now and then newline (so we add the two new lines before the closing of isSlowEndpoint)
import re
# Pattern: run-now') followed by optional comment and newline, then spaces and const defaultTimeout
content2 = content.replace(
    "url.includes('/pagos/gmail/run-now') // Pipeline Gmail: puede tardar si el backend es sncrono (credenciales OAuth)",
    "url.includes('/pagos/gmail/run-now') || // Pipeline Gmail\n                            url.includes('/clientes/check-emails') ||\n                            url.includes('/clientes/check-cedulas')"
)
if content2 == content:
    # try without special o
    content2 = content.replace(
        "url.includes('/pagos/gmail/run-now')",
        "url.includes('/pagos/gmail/run-now') ||\n                            url.includes('/clientes/check-emails') ||\n                            url.includes('/clientes/check-cedulas')",
        1
    )
# But that might replace the wrong one (in defaultTimeout). So we need to replace only the one in isSlowEndpoint.
# The isSlowEndpoint block ends with "run-now')" and newline. So find the occurrence that is followed by ")" and newline and "      const defaultTimeout"
idx = content.find("url.includes('/pagos/gmail/run-now')")
if idx != -1:
    # Check which occurrence: we want the one in the isSlowEndpoint block (first occurrence in post())
    content2 = content[:idx] + "url.includes('/pagos/gmail/run-now') ||\n                            url.includes('/clientes/check-emails') ||\n                            url.includes('/clientes/check-cedulas')" + content[idx + len("url.includes('/pagos/gmail/run-now')"):]
    # Now add 60000 for check-emails/check-cedulas in the defaultTimeout ternary
    old_ternary = ": 300000)\n        : DEFAULT_TIMEOUT_MS"
    new_ternary = ": (url.includes('/clientes/check-emails') || url.includes('/clientes/check-cedulas')) ? 60000\n          : 300000)\n        : DEFAULT_TIMEOUT_MS"
    content2 = content2.replace(old_ternary, new_ternary)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content2)
    print("api.ts patched OK")
else:
    print("pattern not found")
