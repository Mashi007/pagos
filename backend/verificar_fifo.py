"""Compat: nombre historico; delega en verificar_cascada."""
from __future__ import annotations

from verificar_cascada import main, verificar_cascada

verificar_fifo = verificar_cascada

if __name__ == "__main__":
    main()
