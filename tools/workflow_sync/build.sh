#!/bin/bash
# Build script for Workflow Sync Tool
# Genera un ejecutable standalone usando PyInstaller

set -euo pipefail

cd "$(dirname "$0")"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           Workflow Sync - Build Script                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 no está instalado${NC}"
    exit 1
fi

# Verificar/instalar PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo -e "${YELLOW}Instalando PyInstaller...${NC}"
    pip3 install pyinstaller --quiet
    echo -e "${GREEN}✓ PyInstaller instalado${NC}"
fi

# Verificar/instalar PyGithub
if ! python3 -c "import github" 2>/dev/null; then
    echo -e "${YELLOW}Instalando PyGithub...${NC}"
    pip3 install PyGithub --quiet
    echo -e "${GREEN}✓ PyGithub instalado${NC}"
fi

# Limpiar builds anteriores
echo -e "${CYAN}Limpiando builds anteriores...${NC}"
rm -rf build dist

# Construir
echo -e "${CYAN}Construyendo ejecutable...${NC}"
echo ""

python3 -m PyInstaller WorkflowSync.spec --noconfirm

echo ""

# Verificar resultado
if [ -f "dist/WorkflowSync" ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  ✓ Build exitoso                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Ejecutable: ${CYAN}dist/WorkflowSync${NC}"
    echo -e "App Bundle: ${CYAN}dist/WorkflowSync.app${NC}"
    echo ""
    echo -e "${YELLOW}Para distribuir:${NC}"
    echo "  - Copia dist/WorkflowSync.app a /Applications"
    echo "  - O comparte el archivo dist/WorkflowSync directamente"
    echo ""

    # Mostrar tamaño
    SIZE=$(du -h dist/WorkflowSync | cut -f1)
    echo -e "Tamaño del ejecutable: ${CYAN}${SIZE}${NC}"
else
    echo -e "${RED}Error: El build falló${NC}"
    exit 1
fi
