#!/bin/sh
set -e

# Read config from options.json
CONFIG_PATH="/data/options.json"

if [ -f "$CONFIG_PATH" ]; then
    UPRN=$(cat "$CONFIG_PATH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('uprn','010070035296'))")
    CACHE_TTL=$(cat "$CONFIG_PATH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cache_ttl',3600))")
else
    UPRN="010070035296"
    CACHE_TTL="3600"
fi

echo "Starting North Herts Bin Collection..."
echo "UPRN: ${UPRN}"
echo "Cache TTL: ${CACHE_TTL}s"

export DEFAULT_UPRN="${UPRN}"
export CACHE_TTL_SECONDS="${CACHE_TTL}"

cd /app
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
