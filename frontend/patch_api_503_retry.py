# -*- coding: utf-8 -*-
"""Add 503 to retry condition in api.ts."""
import os
path = os.path.join(os.path.dirname(__file__), "src", "services", "api.ts")
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

# Retry on 503 as well as 500
c = c.replace(
    "error.response?.status === 500 &&",
    "(error.response?.status === 500 || error.response?.status === 503) &&",
)
# Optional: make log show actual status
c = c.replace(
    "Error 500 (intento ",
    "Error ${error.response?.status} (intento ",
)
# Fix: the second replace might break the template literal - in JS it's `Error 500 (intento ${...`
# So we need "Error 500 " -> "Error ${error.response?.status} " only in that console.warn line
import re
c = re.sub(
    r'console\.warn\(`\?\? \[ApiClient\] Error 500 \(intento',
    'console.warn(`⚠️ [ApiClient] Error ${error.response?.status} (intento',
    c,
    1,
)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("api.ts: retry on 503 added")
