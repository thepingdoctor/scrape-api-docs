#!/bin/bash
# Script to run the FastAPI application

set -e

echo "Starting Documentation Scraper API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements-api.txt

# Create necessary directories
mkdir -p data logs exports

# Run the API
echo "Starting API server on http://0.0.0.0:8000"
echo "API docs available at http://localhost:8000/api/docs"
echo ""

uvicorn src.scrape_api_docs.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
