# -*- coding: utf-8 -*-
"""Wrap ::-webkit-scrollbar rules in @supports to avoid Firefox 'mal selector' warning."""
import os
path = os.path.join(os.path.dirname(__file__), "src", "index.css")
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

old = """/* Scrollbar personalizado */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-secondary;
}

::-webkit-scrollbar-thumb {
  @apply bg-muted-foreground rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-primary;
}
"""

new = """/* Scrollbar personalizado (solo WebKit/Blink; evita "mal selector" en Firefox) */
@supports selector(::-webkit-scrollbar) {
  ::-webkit-scrollbar {
    width: 8px;
  }

  ::-webkit-scrollbar-track {
    @apply bg-secondary;
  }

  ::-webkit-scrollbar-thumb {
    @apply bg-muted-foreground rounded-full;
  }

  ::-webkit-scrollbar-thumb:hover {
    @apply bg-primary;
  }
}
"""

if old in c:
    c = c.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("index.css: webkit-scrollbar rules wrapped in @supports")
else:
    print("Block not found (maybe already patched or format changed)")
