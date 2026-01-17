# Home Assistant Add-on Dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18
FROM ${BUILD_FROM}

# Install curl for healthcheck
RUN apk add --no-cache curl

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY run.sh /

# Make run script executable
RUN chmod a+x /run.sh

# Labels for Home Assistant
LABEL \
    io.hass.name="North Herts Bin Collection" \
    io.hass.description="Bin collection schedule for North Hertfordshire" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"

CMD [ "/run.sh" ]
