#!/bin/bash
# Local development run script
# Usage: ./run_local.sh

set -e

# Default configuration (override with environment variables)
export DEFAULT_UPRN="${DEFAULT_UPRN:-010070035296}"
export CACHE_TTL_SECONDS="${CACHE_TTL_SECONDS:-3600}"

echo "=================================="
echo "North Herts Bin Collection Service"
echo "=================================="
echo "UPRN: ${DEFAULT_UPRN}"
echo "Cache TTL: ${CACHE_TTL_SECONDS}s"
echo ""
echo "Web UI: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "=================================="
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    else
        echo "Tip: Create a virtual environment with: python3 -m venv venv"
    fi
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the server with auto-reload for development
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
