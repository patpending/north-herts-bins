#!/usr/bin/with-contenv bashio
# Home Assistant Add-on run script
# shellcheck shell=bash

set -e

# Read configuration from Home Assistant add-on options
if bashio::fs.file_exists "/data/options.json"; then
    CONFIG_PATH="/data/options.json"

    UPRN=$(bashio::config 'uprn')
    CACHE_TTL=$(bashio::config 'cache_ttl')

    bashio::log.info "Starting North Herts Bin Collection service..."
    bashio::log.info "UPRN: ${UPRN}"
    bashio::log.info "Cache TTL: ${CACHE_TTL}s"

    # Export environment variables for the app
    export DEFAULT_UPRN="${UPRN}"
    export CACHE_TTL_SECONDS="${CACHE_TTL}"
else
    # Running outside Home Assistant (development mode)
    echo "Running in development mode..."
    export DEFAULT_UPRN="${DEFAULT_UPRN:-010070035296}"
    export CACHE_TTL_SECONDS="${CACHE_TTL_SECONDS:-3600}"
fi

# Start the FastAPI server
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
