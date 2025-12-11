#!/bin/bash
#
# AWS Credentials Manager - Launcher
#
# Script rápido para lanzar el gestor de credenciales AWS
#
# Uso:
#   ./configure_aws_credentials.sh
#

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}AWS Credentials Manager${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Ruta al script Python
PYTHON_SCRIPT="$SCRIPT_DIR/utils/aws_credentials_manager.py"

# Verificar que existe
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: Script no encontrado en $PYTHON_SCRIPT"
    exit 1
fi

# Ejecutar
echo "🚀 Lanzando interfaz gráfica..."
echo ""
python3 "$PYTHON_SCRIPT"
