# Changelog

## [1.0.0] - 2026-01-17

### Added
- Initial release as Home Assistant add-on
- Web UI for viewing bin collections
- REST API endpoints for Home Assistant sensors
- Configurable UPRN via add-on options
- Support for all architectures (amd64, aarch64, armv7, armhf, i386)
- Local development script (run_local.sh)

### Bin Types Supported
- Mixed recycling bin
- Cardboard & paper bin
- Non-recyclable refuse bin
- Garden waste bin

### API Endpoints
- `/api/sensor/next` - Simple next bin sensor
- `/api/collections` - All upcoming collections
- `/api/addresses` - Address lookup by postcode
- `/api/health` - Health check
