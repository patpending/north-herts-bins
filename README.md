# North Hertfordshire Bin Collection Service

A standalone service for checking bin collection schedules in North Hertfordshire, with full Home Assistant integration.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 to view your bin collections.

## Docker Deployment

```bash
# Using docker-compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t north-herts-bins .
docker run -d -p 8000:8000 --name north-herts-bins north-herts-bins
```

### Running on Home Assistant Server

For detailed instructions on running this alongside Home Assistant, see:
**[docs/HOMEASSISTANT_DOCKER.md](docs/HOMEASSISTANT_DOCKER.md)**

Quick start for HA Docker installations:
```bash
git clone https://github.com/patpending/north-herts-bins.git
cd north-herts-bins
docker-compose -f docker-compose.homeassistant.yml up -d
```

---

# Home Assistant Integration

This service provides a REST API specifically designed for Home Assistant integration. Below is a complete guide to setting up sensors, automations, and dashboard cards.

## Prerequisites

1. The bin collection service must be running and accessible from your Home Assistant instance
2. You need your property's UPRN (already configured: `010070035296`)
3. If running on the same machine as Home Assistant, use `http://localhost:8000`
4. If running on a different machine, use that machine's IP address (e.g., `http://192.168.1.100:8000`)

## Step 1: Add the REST Sensor

Add the following to your `configuration.yaml`:

### Option A: Simple Next Bin Sensor (Recommended)

Returns only the next bin collection - clean and simple:

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

This gives you:
- `sensor.next_bin` = "Mixed recycling bin"
- `state_attr('sensor.next_bin', 'days')` = 3
- `state_attr('sensor.next_bin', 'date')` = "Tuesday, 20 January 2026"

### Option B: Full Collection Data

If you want all upcoming collections:

```yaml
sensor:
  - platform: rest
    name: "Bin Collection"
    resource: "http://localhost:8000/api/homeassistant?uprn=010070035296"
    method: GET
    value_template: "{{ value_json.state }}"
    json_attributes:
      - days_until
      - next_date
      - collections
    scan_interval: 3600
```

After adding this, restart Home Assistant or reload the YAML configuration.

## Step 2: Create Template Sensors (Optional but Recommended)

Template sensors give you more control and create separate entities for each piece of data. Add to `configuration.yaml`:

```yaml
template:
  - sensor:
      # Days until next collection
      - name: "Bin Collection Days"
        unique_id: bin_collection_days
        state: "{{ state_attr('sensor.bin_collection', 'days_until') }}"
        unit_of_measurement: "days"
        icon: mdi:calendar-clock

      # Next collection date (formatted)
      - name: "Bin Collection Date"
        unique_id: bin_collection_date
        state: "{{ state_attr('sensor.bin_collection', 'next_date') }}"
        icon: mdi:calendar

      # Next bin type with appropriate icon
      - name: "Next Bin Type"
        unique_id: next_bin_type
        state: "{{ states('sensor.bin_collection') }}"
        icon: >-
          {% set bin = states('sensor.bin_collection') | lower %}
          {% if 'recycl' in bin %}
            mdi:recycle
          {% elif 'refuse' in bin or 'non-recyclable' in bin %}
            mdi:trash-can
          {% elif 'cardboard' in bin or 'paper' in bin %}
            mdi:package-variant
          {% elif 'garden' in bin %}
            mdi:leaf
          {% else %}
            mdi:delete
          {% endif %}

      # Boolean: Is collection today?
      - name: "Bin Collection Today"
        unique_id: bin_collection_today
        state: "{{ state_attr('sensor.bin_collection', 'days_until') == 0 }}"
        icon: mdi:alert-circle

      # Boolean: Is collection tomorrow?
      - name: "Bin Collection Tomorrow"
        unique_id: bin_collection_tomorrow
        state: "{{ state_attr('sensor.bin_collection', 'days_until') == 1 }}"
        icon: mdi:alert

  # Binary sensors for automations
  - binary_sensor:
      - name: "Bin Day Today"
        unique_id: bin_day_today
        state: "{{ state_attr('sensor.bin_collection', 'days_until') == 0 }}"
        device_class: problem

      - name: "Bin Day Tomorrow"
        unique_id: bin_day_tomorrow
        state: "{{ state_attr('sensor.bin_collection', 'days_until') == 1 }}"
```

## Step 3: Set Up Automations

### Evening Reminder (Day Before Collection)

```yaml
automation:
  - id: bin_collection_evening_reminder
    alias: "Bin Collection - Evening Reminder"
    description: "Remind to put bins out the evening before collection"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.bin_collection', 'days_until') == 1 }}"
    action:
      - service: notify.notify  # Change to your notification service
        data:
          title: "🗑️ Bin Collection Tomorrow"
          message: "Put out your {{ states('sensor.bin_collection') }} tomorrow"
      # Optional: Send to mobile app with actionable notification
      - service: notify.mobile_app_your_phone  # Change to your device
        data:
          title: "Bin Collection Tomorrow"
          message: "{{ states('sensor.bin_collection') }} collection is tomorrow ({{ state_attr('sensor.bin_collection', 'next_date') }})"
          data:
            tag: "bin-reminder"
            actions:
              - action: "MARK_DONE"
                title: "Done"
```

### Morning Reminder (Collection Day)

```yaml
  - id: bin_collection_morning_reminder
    alias: "Bin Collection - Morning Reminder"
    description: "Morning reminder on collection day"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.bin_collection', 'days_until') == 0 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🗑️ Bin Day Today!"
          message: "{{ states('sensor.bin_collection') }} collection is TODAY"
          data:
            tag: "bin-reminder"
            priority: high
            ttl: 0
```

### Announcement via Speaker (Optional)

```yaml
  - id: bin_collection_voice_reminder
    alias: "Bin Collection - Voice Reminder"
    description: "Announce bin collection via smart speaker"
    trigger:
      - platform: time
        at: "19:00:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.bin_collection', 'days_until') == 1 }}"
    action:
      - service: tts.speak
        target:
          entity_id: tts.google_en  # Change to your TTS entity
        data:
          media_player_entity_id: media_player.living_room_speaker  # Change to your speaker
          message: "Reminder: Put out the {{ states('sensor.bin_collection') }} for collection tomorrow"
```

## Step 4: Dashboard Cards

### Simple Entity Card

```yaml
type: entities
title: Bin Collection
entities:
  - entity: sensor.bin_collection
    name: Next Bin
  - entity: sensor.bin_collection_date
    name: Collection Date
  - entity: sensor.bin_collection_days
    name: Days Until
```

### Markdown Card (More Detail)

```yaml
type: markdown
title: Bin Collection
content: |
  ## Next Collection
  **{{ states('sensor.bin_collection') }}**

  📅 {{ state_attr('sensor.bin_collection', 'next_date') }}

  {% set days = state_attr('sensor.bin_collection', 'days_until') %}
  {% if days == 0 %}
  ⚠️ **Collection is TODAY!**
  {% elif days == 1 %}
  ⏰ Collection is **tomorrow**
  {% else %}
  📆 {{ days }} days until collection
  {% endif %}

  ---
  ### Upcoming Collections
  {% for c in state_attr('sensor.bin_collection', 'collections')[:4] %}
  - **{{ c.bin_type }}**: {{ c.collection_date_formatted }} ({{ c.days_until }} days)
  {% endfor %}
```

### Conditional Card (Shows Warning on Collection Days)

```yaml
type: conditional
conditions:
  - condition: numeric_state
    entity: sensor.bin_collection_days
    below: 2
card:
  type: markdown
  content: |
    ## 🗑️ Bin Reminder
    {% set days = state_attr('sensor.bin_collection', 'days_until') %}
    {% if days == 0 %}
    **{{ states('sensor.bin_collection') }}** collection is **TODAY**!
    {% else %}
    Put out **{{ states('sensor.bin_collection') }}** tonight for tomorrow's collection.
    {% endif %}
```

### Mushroom Chips Card (Compact)

If you have the Mushroom cards installed:

```yaml
type: custom:mushroom-chips-card
chips:
  - type: template
    icon: >-
      {% set bin = states('sensor.bin_collection') | lower %}
      {% if 'recycl' in bin %}mdi:recycle
      {% elif 'refuse' in bin %}mdi:trash-can
      {% elif 'cardboard' in bin %}mdi:package-variant
      {% elif 'garden' in bin %}mdi:leaf
      {% else %}mdi:delete{% endif %}
    icon_color: >-
      {% set days = state_attr('sensor.bin_collection', 'days_until') %}
      {% if days == 0 %}red
      {% elif days == 1 %}orange
      {% elif days <= 3 %}green
      {% else %}grey{% endif %}
    content: >-
      {% set days = state_attr('sensor.bin_collection', 'days_until') %}
      {% if days == 0 %}Today
      {% elif days == 1 %}Tomorrow
      {% else %}{{ days }}d{% endif %}
    tap_action:
      action: more-info
      entity: sensor.bin_collection
```

## Step 5: Scripts (Optional)

Create a script to manually refresh the bin data:

```yaml
script:
  refresh_bin_collection:
    alias: "Refresh Bin Collection Data"
    sequence:
      - service: homeassistant.update_entity
        target:
          entity_id: sensor.bin_collection
```

## API Endpoints Reference

| Endpoint | Description |
|----------|-------------|
| `GET /api/sensor/next?uprn=XXXXX` | Simple next bin sensor (recommended for HA) |
| `GET /api/homeassistant?uprn=XXXXX` | Full Home Assistant formatted response |
| `GET /api/collections?uprn=XXXXX` | All collection data |
| `GET /api/next?uprn=XXXXX` | Next collection (detailed) |
| `GET /api/health` | Service health check |
| `GET /docs` | Swagger API documentation |

### Response Format (Home Assistant Endpoint)

```json
{
  "state": "Mixed recycling bin",
  "days_until": 3,
  "next_date": "Tuesday, 20 January 2026",
  "collections": [
    {
      "bin_type": "Mixed recycling bin",
      "collection_date": "2026-01-20T00:00:00",
      "collection_date_formatted": "Tuesday, 20 January 2026",
      "days_until": 3
    },
    ...
  ]
}
```

## Troubleshooting

### Sensor shows "unavailable" or "unknown"

1. Check the service is running: `curl http://localhost:8000/api/health`
2. Verify the URL is accessible from Home Assistant
3. Check Home Assistant logs: Settings → System → Logs
4. Try the API directly: `curl "http://localhost:8000/api/homeassistant?uprn=010070035296"`

### Sensor not updating

1. Default update interval is 1 hour (`scan_interval: 3600`)
2. Manually refresh: Developer Tools → Services → `homeassistant.update_entity`
3. Check if the service has cached stale data: `POST /api/cache/clear`

### Running on a different machine

If Home Assistant and this service are on different machines:

1. Ensure the service binds to `0.0.0.0`: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
2. Check firewall allows port 8000
3. Use the machine's IP address in the sensor configuration

### Docker networking with Home Assistant

If both run in Docker:

```yaml
# docker-compose.yml
services:
  north-herts-bins:
    build: .
    container_name: north-herts-bins
    ports:
      - "8000:8000"
    networks:
      - homeassistant

networks:
  homeassistant:
    external: true  # Use Home Assistant's network
```

Then use `http://north-herts-bins:8000` as the URL in Home Assistant.

## Running as a Systemd Service

To run the service automatically on boot (Linux):

```bash
sudo nano /etc/systemd/system/north-herts-bins.service
```

```ini
[Unit]
Description=North Herts Bin Collection Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/north-herts-bins
ExecStart=/usr/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable north-herts-bins
sudo systemctl start north-herts-bins
```

## Credits

- Approach inspired by [UKBinCollectionData](https://github.com/robbrad/UKBinCollectionData)
- API credentials from the official North Herts Council mobile app
- Data provided by North Hertfordshire District Council

## License

MIT License
