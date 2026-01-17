#!/usr/bin/with-contenv bashio
# Home Assistant Add-on run script

set -e

# Read configuration from Home Assistant add-on options
UPRN=$(bashio::config 'uprn')
CACHE_TTL=$(bashio::config 'cache_ttl')

bashio::log.info "Starting North Herts Bin Collection service..."
bashio::log.info "UPRN: ${UPRN}"
bashio::log.info "Cache TTL: ${CACHE_TTL}s"

# Export environment variables for the app
export DEFAULT_UPRN="${UPRN}"
export CACHE_TTL_SECONDS="${CACHE_TTL}"

# Start the FastAPI server
cd /app
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
