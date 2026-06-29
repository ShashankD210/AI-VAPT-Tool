# VAPT Tool - Development Notes

## Configuration
- Local config: `vapt_config.yaml` (auto-detected, no root required)
- Default system config: `/opt/vapt-tool/config/config.yaml`
- Override: Set `VAPT_CONFIG` environment variable

## Test Commands
```bash
# Syntax check
python3 -m py_compile vapt_tool.py src/**/*.py

# Run CLI
python3 vapt_tool.py --help
python3 vapt_tool.py --version

# Test scanners
python3 vapt_tool.py scan https://example.com --type web

# Test agent commands
python3 vapt_tool.py agent generate-env --seed test
python3 vapt_tool.py agent parse-env -

# Test report generation
python3 vapt_tool.py report html input.json -o report.html
```

## Dependencies
- Core: `fastapi`, `uvicorn[standard]`, `pyyaml`
- Optional: `celery` (for async task queue)

### Usage Guide

### Server Mode
```bash
# Start API server (default)
python3 vapt_tool.py server

# With environment variables
VAPT_HOST=127.0.0.1 VAPT_PORT=9000 python3 vapt_tool.py server

# With reload for development
VAPT_RELOAD=true python3 vapt_tool.py server
```

### Vulnerability Scanning (auto-generates reports)
```bash
# Web application scan - creates JSON, HTML, PDF reports
python3 vapt_tool.py scan https://target.com --type web -o ./reports

# Network scan - creates JSON, HTML, PDF reports
python3 vapt_tool.py scan 192.168.1.1 --type network -o ./reports

# API scan - creates JSON, HTML, PDF reports
python3 vapt_tool.py scan https://api.example.com --type api -o ./reports

# Cloud scan - creates JSON, HTML, PDF reports
python3 vapt_tool.py scan aws --type cloud -o ./reports

# Skip auto-report generation
python3 vapt_tool.py scan https://target.com --type web --no-report
```

### Agent Commands
```bash
# Generate random environment details block
python3 vapt_tool.py agent generate-env --seed myseed

# Generate with custom fields
python3 vapt_tool.py agent generate-env --seed abc --agent "my-agent" --platform linux

# Parse environment details from file
python3 vapt_tool.py agent parse-env scan_results.txt

# Parse from stdin
cat scan_output.txt | python3 vapt_tool.py agent parse-env -

# Generate random scan results (for testing)
python3 vapt_tool.py agent random-scan --seed test --count 5 --type web
python3 vapt_tool.py agent random-scan --type network
```

### Report Generation
```bash
# Generate HTML report from JSON file
python3 vapt_tool.py report html scan_results.json -o report.html

# Generate with custom title
python3 vapt_tool.py report html scan_results.json --title "Security Audit Report"

# Generate from stdin
cat scan_data.json | python3 vapt_tool.py report html - -o output.html
```

### AI Model Training
```bash
# Train models from CSV data
python3 vapt_tool.py train training_data.csv --output-dir ./models

# Train from JSON data
python3 vapt_tool.py train scan_data.json --output-dir ./trained_models
```

## Vulnerability Detection

Scanners now detect:
- **Web**: Missing security headers (X-Frame-Options, CSP, HSTS), XSS patterns, SQL injection indicators
- **Network**: Open ports with known vulnerable services (SSH, FTP, Redis, MySQL, MongoDB)
- **API**: Missing security headers, credential exposure in responses
- **Cloud**: Public cloud storage buckets, metadata endpoint exposure

Each finding includes CVE identifiers where applicable and severity ratings (critical/high/medium/low).

## API Endpoints
```bash
# Root and health
curl http://localhost:8000/
curl http://localhost:8000/health

# Run vulnerability scan via API
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"target": "https://example.com", "type": "web"}'

# Generate random scan via API
curl -X POST http://localhost:8000/agent/random-scan \
  -H "Content-Type: application/json" \
  -d '{"seed": "test", "count": 3, "type": "web"}'

# Parse environment details
curl -X POST http://localhost:8000/agent/env-details/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "<environment_details>{\"test\": 1}</environment_details>"}'

# Generate HTML report
curl -X POST http://localhost:8000/reports/html \
  -H "Content-Type: application/json" \
  -d '{"blocks": [{"raw": "test", "json": {"vulnerabilities": []}}]}'
```