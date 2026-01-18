"""
Punto de entrada para ejecución como módulo.

Permite ejecutar: python -m workflow_sync
"""

import sys

from workflow_sync.cli import main

if __name__ == "__main__":
    sys.exit(main())
