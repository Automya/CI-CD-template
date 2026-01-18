#!/bin/bash
# Workflow Sync Tool - macOS Launcher
# Doble clic para ejecutar la aplicación interactiva de terminal

cd "$(dirname "$0")"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    ERROR: Python no encontrado             ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Python 3 es requerido para ejecutar esta herramienta.${NC}"
    echo ""
    echo -e "${CYAN}Opciones de instalación:${NC}"
    echo ""
    echo "  1. Homebrew (recomendado):"
    echo -e "     ${GREEN}brew install python3${NC}"
    echo ""
    echo "  2. Descarga oficial:"
    echo -e "     ${GREEN}https://www.python.org/downloads/${NC}"
    echo ""
    echo "  3. Xcode Command Line Tools:"
    echo -e "     ${GREEN}xcode-select --install${NC}"
    echo ""
    read -p "Presiona Enter para salir..."
    exit 1
fi

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}Instalando pip...${NC}"
    python3 -m ensurepip --upgrade 2>/dev/null || {
        echo -e "${RED}Error: No se pudo instalar pip${NC}"
        echo "Instala pip manualmente: python3 -m ensurepip"
        read -p "Presiona Enter para salir..."
        exit 1
    }
fi

# Verificar PyGithub
if ! python3 -c "import github" 2>/dev/null; then
    echo -e "${CYAN}Instalando dependencias...${NC}"
    pip3 install PyGithub --quiet || {
        echo -e "${RED}Error: No se pudo instalar PyGithub${NC}"
        echo "Intenta manualmente: pip3 install PyGithub"
        read -p "Presiona Enter para salir..."
        exit 1
    }
    echo -e "${GREEN}✓ Dependencias instaladas${NC}"
    echo ""
fi

# Ejecutar aplicación interactiva
python3 interactive.py
