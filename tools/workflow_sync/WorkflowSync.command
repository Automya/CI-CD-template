#!/bin/bash
# Workflow Sync Tool - macOS Launcher
# Doble clic para ejecutar la aplicación interactiva de terminal

cd "$(dirname "$0")"

# Verificar PyGithub
python3 -c "import github" 2>/dev/null || pip3 install PyGithub --quiet

# Ejecutar aplicación interactiva
python3 interactive.py
