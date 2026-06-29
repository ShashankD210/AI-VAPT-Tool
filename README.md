# AI-VAPT Tool

AI-Powered Vulnerability Assessment & Penetration Testing Tool for detecting security vulnerabilities and CVEs.

## Quick Start
```bash
# Install dependencies
pip install fastapi uvicorn pyyaml celery requests beautifulsoup4 weasyprint

# Run a web vulnerability scan (auto-generates reports)
python3 vapt_tool.py scan https://target.com --type web -o ./reports
```

## Commands

| Command | Description |
|---------|-------------|
| `server` | Start the API server |
| `scan <target> --type <web|network|api|cloud>` | Run vulnerability scan |
| `agent generate-env --seed <seed>` | Generate random environment block |
| `agent parse-env [file]` | Parse environment details |
| `agent random-scan --count N --type <type>` | Generate random CVE data |
| `report html <input> -o <output>` | Generate HTML report |
| `train <data> --output-dir <dir>` | Train AI models |

## Scan Types
- **web**: Security headers, XSS, SQL injection
- **network**: Open ports with CVEs (SSH, Redis, MySQL, etc.)
- **api**: Missing headers, credential exposure
- **cloud**: Public buckets, metadata endpoints

## Output
After each scan, generates: `scan_<type>_<target>.json`, `scan_<type>_<target>.html`, `scan_<type>_<target>.pdf`

Use `--no-report` to skip report generation.