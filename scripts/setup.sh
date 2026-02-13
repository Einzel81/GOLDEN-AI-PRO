#!/bin/bash

# Golden-AI Pro Setup Script
# ===========================

set -e

echo "🚀 Setting up Golden-AI Pro..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo -e "${RED}Error: Python 3.10+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python version check passed${NC}"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p models
mkdir -p data
mkdir -p cache
mkdir -p logs/trades

# Copy environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env file with your settings${NC}"
fi

# Download NLTK data (for sentiment analysis)
python -c "import nltk; nltk.download('vader_lexicon', quiet=True)" 2>/dev/null || true

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your MT5 credentials"
echo "2. Run: docker-compose up -d"
echo "3. Or run locally: python -m src.api.main"
echo ""
echo "For help, visit: https://docs.golden-ai.pro"
