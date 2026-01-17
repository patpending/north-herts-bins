# North Hertfordshire Bin Collection

A Home Assistant add-on for checking bin collection schedules in North Hertfordshire.

## Features

- Shows your next bin collection date
- Web UI for viewing all upcoming collections
- REST API for Home Assistant sensors
- Configurable via add-on options

---

## Installation

### Home Assistant Add-on (Recommended)

1. **Add the repository to Home Assistant:**
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the menu (⋮) → **Repositories**
   - Add: `https://github.com/patpending/north-herts-bins`
   - Click **Add** → **Close**

2. **Install the add-on:**
   - Find "North Herts Bin Collection" in the add-on store
   - Click **Install**

3. **Configure:**
   - Go to the **Configuration** tab
   - Set your UPRN (find it using the web UI first, or see below)
   - Click **Save**

4. **Start the add-on:**
   - Go to the **Info** tab
   - Click **Start**
   - Enable **Start on boot** if desired

5. **Open Web UI:**
   - Click **Open Web UI** to view your bin collections

### Finding Your UPRN

1. Start the add-on with any UPRN
2. Open the Web UI
3. Click "Change" to search for your address
4. Enter your postcode and select your address
5. Your UPRN will be shown at the bottom of the results
6. Update the add-on configuration with your UPRN

---

## Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `uprn` | Your property's UPRN | `010070035296` |
| `cache_ttl` | Cache duration in seconds | `3600` (1 hour) |

Example configuration:
```yaml
uprn: "010070035296"
cache_ttl: 3600
```

---

## Home Assistant Sensors

Once the add-on is running, add these sensors to your `configuration.yaml`:

### Simple Sensor (Recommended)

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

**Note:** Replace `homeassistant.local` with your HA hostname/IP if needed.

### Template Sensors

```yaml
template:
  - sensor:
      - name: "Bin Collection Days"
        state: "{{ state_attr('sensor.next_bin', 'days') }}"
        unit_of_measurement: "days"
        icon: mdi:calendar-clock

  - binary_sensor:
      - name: "Bin Day Tomorrow"
        state: "{{ state_attr('sensor.next_bin', 'days') == 1 }}"
```

### Automation Example

```yaml
automation:
  - alias: "Bin Reminder"
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

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web UI |
| `GET /api/sensor/next?uprn=X` | Simple sensor format |
| `GET /api/collections?uprn=X` | All collections |
| `GET /api/addresses?postcode=X` | Address lookup |
| `GET /api/health` | Health check |

---

## Local Development

For development without Home Assistant:

```bash
# Clone the repository
git clone https://github.com/patpending/north-herts-bins.git
cd north-herts-bins

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
./run_local.sh
```

Or manually:
```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_UPRN` | Default property UPRN | `010070035296` |
| `CACHE_TTL_SECONDS` | Cache duration | `3600` |

---

## Project Structure

```
north-herts-bins/
├── config.yaml          # HA add-on configuration
├── Dockerfile           # Add-on container build
├── run.sh              # Add-on entry point
├── run_local.sh        # Local development script
├── app/
│   ├── main.py         # FastAPI application
│   └── scraper.py      # North Herts API client
├── templates/
│   └── index.html      # Web interface
└── static/             # Static assets
```

---

## Troubleshooting

### Add-on won't start
- Check the add-on logs in Home Assistant
- Verify your UPRN is valid (numbers only)

### Sensor shows "unavailable"
- Ensure the add-on is running
- Check the URL is accessible: `curl http://homeassistant.local:8000/api/health`
- Try using the IP address instead of hostname

### Wrong bin data
- The data comes from North Herts Council's API
- Try clearing the cache: `POST /api/cache/clear`
- Check the official council website to compare

---

## Credits

- API approach inspired by [UKBinCollectionData](https://github.com/robbrad/UKBinCollectionData)
- Data provided by North Hertfordshire District Council

## License

MIT License
