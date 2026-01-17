# Running on Home Assistant Server

This guide covers how to run the North Herts Bin Collection service as a Docker container on your Home Assistant server.

## Quick Reference

| HA Installation Type | Recommended Method |
|---------------------|-------------------|
| Home Assistant OS (HAOS) | [Option 1: Portainer Add-on](#option-1-home-assistant-os-with-portainer) |
| Home Assistant Container | [Option 2: Docker Compose](#option-2-home-assistant-container-docker) |
| Home Assistant Supervised | [Option 2: Docker Compose](#option-2-home-assistant-container-docker) |
| Home Assistant Core | [Option 3: Systemd Service](#option-3-home-assistant-core) |

---

## Option 1: Home Assistant OS with Portainer

If you're running Home Assistant OS (the recommended installation), you can use the Portainer add-on to manage Docker containers.

### Step 1: Install Portainer Add-on

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three dots (⋮) in the top right → **Repositories**
3. Add this repository: `https://github.com/alexbelgium/hassio-addons`
4. Find and install **Portainer**
5. Start Portainer and open the Web UI

### Step 2: Create the Container in Portainer

1. Open Portainer Web UI
2. Go to **Containers** → **Add Container**
3. Configure:
   - **Name**: `north-herts-bins`
   - **Image**: Build from the GitHub repo (see below) or use a pre-built image

Since there's no pre-built image on Docker Hub, you'll need to build it:

#### Option A: Build on the HA Server

SSH into your HA server (enable SSH add-on first):

```bash
# Clone the repository
cd /root
git clone https://github.com/patpending/north-herts-bins.git
cd north-herts-bins

# Build the image
docker build -t north-herts-bins .

# Run the container
docker run -d \
  --name north-herts-bins \
  --restart unless-stopped \
  -p 8000:8000 \
  north-herts-bins
```

#### Option B: Use Docker Compose in Portainer

1. In Portainer, go to **Stacks** → **Add Stack**
2. Name it `north-herts-bins`
3. Paste this compose file:

```yaml
version: "3.8"

services:
  north-herts-bins:
    build:
      context: https://github.com/patpending/north-herts-bins.git
    container_name: north-herts-bins
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - CACHE_TTL_SECONDS=3600
```

4. Click **Deploy the stack**

### Step 3: Configure Home Assistant Sensor

Add to your `configuration.yaml`:

```yaml
sensor:
  - platform: rest
    name: "Next Bin"
    resource: "http://homeassistant.local:8000/api/sensor/next?uprn=010070035296"
    value_template: "{{ value_json.state }}"
    json_attributes:
      - days
      - date
    scan_interval: 3600
```

**Note**: On HA OS, use `homeassistant.local` or the IP address of your HA server.

---

## Option 2: Home Assistant Container (Docker)

If you're running Home Assistant as a Docker container, you can run this service alongside it.

### Step 1: Create Project Directory

```bash
# On your server
mkdir -p /opt/north-herts-bins
cd /opt/north-herts-bins

# Clone the repository
git clone https://github.com/patpending/north-herts-bins.git .
```

### Step 2: Create Docker Compose File

Create `/opt/north-herts-bins/docker-compose.yml`:

```yaml
version: "3.8"

services:
  north-herts-bins:
    build: .
    container_name: north-herts-bins
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - TZ=Europe/London
      - CACHE_TTL_SECONDS=3600
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 5m
      timeout: 10s
      retries: 3
      start_period: 30s
```

### Step 3: Start the Service

```bash
cd /opt/north-herts-bins
docker-compose up -d
```

### Step 4: Verify It's Running

```bash
# Check container status
docker ps | grep north-herts-bins

# Test the API
curl http://localhost:8000/api/sensor/next?uprn=010070035296
```

### Step 5: Configure Home Assistant

Add to your Home Assistant `configuration.yaml`:

```yaml
sensor:
  - platform: rest
    name: "Next Bin"
    resource: "http://172.17.0.1:8000/api/sensor/next?uprn=010070035296"
    value_template: "{{ value_json.state }}"
    json_attributes:
      - days
      - date
    scan_interval: 3600
```

**Important**: Use `172.17.0.1` (Docker gateway) if HA is also in Docker, or the host's IP address.

### Alternative: Same Docker Network

If you want containers to communicate by name, use the same network:

```yaml
# docker-compose.yml for north-herts-bins
version: "3.8"

services:
  north-herts-bins:
    build: .
    container_name: north-herts-bins
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - TZ=Europe/London
    networks:
      - homeassistant

networks:
  homeassistant:
    external: true
    name: homeassistant_default  # Change to match your HA network name
```

Find your HA network name:
```bash
docker network ls | grep home
```

Then in HA config, use:
```yaml
resource: "http://north-herts-bins:8000/api/sensor/next?uprn=010070035296"
```

---

## Option 3: Home Assistant Core

If you're running Home Assistant Core directly (not in Docker), run as a systemd service.

### Step 1: Clone and Install

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/patpending/north-herts-bins.git
cd north-herts-bins

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Create Systemd Service

```bash
sudo nano /etc/systemd/system/north-herts-bins.service
```

```ini
[Unit]
Description=North Herts Bin Collection Service
After=network.target

[Service]
Type=simple
User=homeassistant
Group=homeassistant
WorkingDirectory=/opt/north-herts-bins
Environment="PATH=/opt/north-herts-bins/venv/bin"
ExecStart=/opt/north-herts-bins/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 3: Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable north-herts-bins
sudo systemctl start north-herts-bins

# Check status
sudo systemctl status north-herts-bins
```

### Step 4: Configure Home Assistant

```yaml
sensor:
  - platform: rest
    name: "Next Bin"
    resource: "http://localhost:8000/api/sensor/next?uprn=010070035296"
    value_template: "{{ value_json.state }}"
    json_attributes:
      - days
      - date
    scan_interval: 3600
```

---

## Complete Home Assistant Configuration

Once the service is running, add this to your `configuration.yaml`:

```yaml
# Bin Collection Sensor
sensor:
  - platform: rest
    name: "Next Bin"
    resource: "http://localhost:8000/api/sensor/next?uprn=010070035296"
    value_template: "{{ value_json.state }}"
    json_attributes:
      - days
      - date
    scan_interval: 3600

# Template sensors for easier use
template:
  - sensor:
      - name: "Bin Collection Days"
        state: "{{ state_attr('sensor.next_bin', 'days') }}"
        unit_of_measurement: "days"
        icon: >-
          {% set days = state_attr('sensor.next_bin', 'days') | int(-1) %}
          {% if days == 0 %}mdi:alert-circle
          {% elif days == 1 %}mdi:alert
          {% else %}mdi:calendar{% endif %}

  - binary_sensor:
      - name: "Bin Day Tomorrow"
        state: "{{ state_attr('sensor.next_bin', 'days') == 1 }}"

# Automation for reminders
automation:
  - id: bin_reminder_evening
    alias: "Bin Reminder - Evening"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.next_bin', 'days') == 1 }}"
    action:
      - service: notify.notify
        data:
          title: "Bin Collection Tomorrow"
          message: "Put out your {{ states('sensor.next_bin') }}"
```

---

## Updating the Service

### Docker

```bash
cd /opt/north-herts-bins
git pull
docker-compose build --no-cache
docker-compose up -d
```

### Systemd

```bash
cd /opt/north-herts-bins
git pull
sudo systemctl restart north-herts-bins
```

---

## Troubleshooting

### Check if service is running

```bash
# Docker
docker logs north-herts-bins

# Systemd
sudo journalctl -u north-herts-bins -f
```

### Test API from HA server

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/sensor/next?uprn=010070035296
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Check container is running: `docker ps` |
| "Host not found" | Use IP address instead of hostname |
| Sensor shows "unavailable" | Check HA logs, verify URL is accessible |
| Data not updating | Default is hourly; manually refresh in Developer Tools |

### Firewall

If running on a separate machine, ensure port 8000 is open:

```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp

# CentOS/RHEL
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

---

## Network Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Home Assistant Server                 │
│                                                          │
│  ┌──────────────────┐      ┌──────────────────────────┐ │
│  │                  │      │                          │ │
│  │  Home Assistant  │─────▶│  north-herts-bins:8000   │ │
│  │   (Container)    │ HTTP │      (Container)         │ │
│  │                  │      │                          │ │
│  └──────────────────┘      └──────────────────────────┘ │
│          │                            │                  │
│          │                            │                  │
└──────────┼────────────────────────────┼──────────────────┘
           │                            │
           ▼                            ▼
    Home Assistant              North Herts Council
      Dashboard                    Cloud9 API
```
