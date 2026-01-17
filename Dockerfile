ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install dependencies
RUN apk add --no-cache python3 py3-pip curl

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY run.sh /

RUN chmod +x /run.sh

CMD [ "/run.sh" ]
