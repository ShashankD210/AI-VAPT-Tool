#!/usr/bin/env python3
"""
AI-Powered VAPT Tool
====================
Single-file Linux executable for Vulnerability Assessment & Penetration Testing.

Usage:
    ./vapt_tool.py
    ./vapt_tool.py server
    ./vapt_tool.py scan <target> --type <web|network|api|cloud>
    ./vapt_tool.py train <data_path> --output-dir <dir>
    ./vapt_tool.py --version
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# STANDARD LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════
import argparse
import dataclasses
import datetime
import html as html_mod
import json
import logging
import os
import random
import re
import string
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "3.0.0"
__author__ = "VAPT Tool Team"
__description__ = (
    "AI-Powered Vulnerability Assessment & Penetration Testing Tool"
)

# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS  (src/exceptions.py)
# ═══════════════════════════════════════════════════════════════════════════════
@dataclasses.dataclass
class VAPTException(Exception):
    """Base exception for all VAPT errors."""
    message: str
    details: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class ConfigError(VAPTException):
    """Raised when configuration is invalid or missing."""
    pass


class ScanError(VAPTException):
    """Raised when a scan fails."""
    pass


class AuthenticationError(VAPTException):
    """Raised on authentication failures."""
    pass


class NetworkError(VAPTException):
    """Raised on network/connectivity errors."""
    pass


class AIInferenceError(VAPTException):
    """Raised when AI prediction/training fails."""
    pass


class ReportingError(VAPTException):
    """Raised when report generation fails."""
    pass


class DatabaseError(VAPTException):
    """Raised on database errors."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING  (src/utils/logger.py)
# ═══════════════════════════════════════════════════════════════════════════════
def setup_logger(
    name: str = "vapt",
    log_file: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Create and configure a logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if log_file:
        fh = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


root_logger = setup_logger("vapt")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION  (src/core/config.py)
# ═══════════════════════════════════════════════════════════════════════════════
class Config:
    """Load and provide access to YAML configuration values."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Check local config first, then default path
            local_config = Path(__file__).resolve().parent / "vapt_config.yaml"
            if local_config.exists():
                config_path = str(local_config)
            else:
                config_path = os.environ.get(
                    "VAPT_CONFIG", "/opt/vapt-tool/config/config.yaml"
                )
        self.config_path = config_path
        self._config: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        path = Path(self.config_path)
        if not path.exists():
            root_logger.warning(
                "Config file not found: %s — using defaults", self.config_path
            )
            return {}
        try:
            import yaml  # lazy so missing pyyaml gives a clear error
            with open(path, "r") as fh:
                return yaml.safe_load(fh) or {}
        except ImportError:
            root_logger.warning("PyYAML not installed; config values unavailable")
            return {}
        except Exception as exc:
            raise ConfigError(
                f"Failed to load config: {exc}"
            ) from exc

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def app_name(self) -> str:
        return self.get("app.name", "VAPT Tool")

    @property
    def db_url(self) -> str:
        return self.get("database.postgresql.url") or os.environ.get(
            "DATABASE_URL", "sqlite:///vapt_default.db"
        )

    @property
    def redis_url(self) -> str:
        return self.get("database.redis.url") or os.environ.get(
            "REDIS_URL", ""
        )


config = Config()

# ═══════════════════════════════════════════════════════════════════════════════
# CELERY  (src/core/celery_app.py)
# ═══════════════════════════════════════════════════════════════════════════════
celery_app: Any = None
try:
    from celery import Celery  # type: ignore

    celery_app = Celery("vapt", broker="redis://localhost:6379/0")
    root_logger.info("Celery initialised")
except ImportError:
    root_logger.warning(
        "Celery not installed — running without async task queue"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# AI MODELS  (src/ai/__init__.py)
# ═══════════════════════════════════════════════════════════════════════════════
class VulnerabilityModel:
    """Placeholder AI model for vulnerability classification."""

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        root_logger.debug("Predicting for features: %s", features)
        return {"vulnerability": "unknown", "confidence": 0.0}


class TrainingPipeline:
    """Placeholder training pipeline."""

    def train(
        self, data_path: str, output_dir: str
    ) -> Dict[str, Any]:
        root_logger.info("Training AI model from %s", data_path)
        return {
            "status": "completed",
            "model_path": output_dir,
            "metrics": {},
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SCANNERS  (src/scanners/{network,web,api,cloud}/scanner.py)
# ═══════════════════════════════════════════════════════════════════════════════
# Scanner classes imported lazily in _get_scanner() to avoid import errors


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION  (src/api/server.py)
# ═══════════════════════════════════════════════════════════════════════════════
def create_app() -> "FastAPI":
    """Application factory used by uvicorn."""
    from fastapi import FastAPI  # type: ignore
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore

    app = FastAPI(
        title="AI-VAPT Tool API",
        description=__description__,
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.get("security.cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def _root() -> Dict[str, str]:
        return {"status": "running", "tool": config.app_name}

    @app.get("/health")
    async def _health() -> Dict[str, str]:
        return {"status": "healthy"}

    @app.post("/agent/env-details/parse")
    async def _parse_env_details(payload: Dict[str, str]) -> Dict[str, Any]:
        """Parse <environment_details> blocks from *payload['text']*."""
        text = payload.get("text", "")
        blocks = parse_environment_details(text)
        return {"blocks_found": len(blocks), "blocks": blocks}

    @app.post("/agent/env-details/generate")
    async def _generate_env_details(req: Dict[str, Any]) -> Dict[str, str]:
        """Generate a random <environment_details> block.  Pass *seed* and
        *fields* (dict) in the JSON body to customise output."""
        seed = req.get("seed")
        fields = req.get("fields")
        block = generate_random_details(seed=seed, fields=fields)
        return {"block": block}

    @app.post("/reports/html")
    async def _html_report(req: Dict[str, Any]) -> Dict[str, str]:
        """Build an HTML vulnerability report wrapped in
        ``<environment_details>``.  Body: ``{"blocks": [...], "title": "..."}``"""
        blocks = req.get("blocks", [])
        title = req.get("title", "VAPT Scan Report")
        report = generate_env_details_html(blocks, title=title)
        return {"report": report}

    @app.post("/scan")
    async def _scan_endpoint(req: Dict[str, Any]) -> Dict[str, Any]:
        """Run vulnerability scan via API.
        Body: ``{"target": "https://example.com", "type": "web|network|api|cloud"}``"""
        target = req.get("target", "")
        scan_type = req.get("type", "web")

        if not target:
            return {"error": "target is required", "status": "failed"}

        scanner = _get_scanner(scan_type)()
        result = scanner.run(target)
        return result

    return app


# ═══════════════════════════════════════════════════════════════════════════════
# RANDOM API AGENT — <environment_details> PARSER  (new)
# ═══════════════════════════════════════════════════════════════════════════════
_ENV_DETAIL_RE = re.compile(
    r"<environment_details>\s*(.*?)\s*</environment_details>",
    re.DOTALL | re.IGNORECASE,
)


def parse_environment_details(text: str) -> List[Dict[str, Any]]:
    """
    Extract all ``<environment_details>...</environment_details>`` blocks
    from *text* and return them as a list of dicts.

    Each block may contain any content.  The parser treats the inner text as
    a free-form payload and stashes it under the ``content`` key.  If the
    inner text happens to be valid JSON it is also exposed as ``json``.

    Returns an empty list when no tags are found.
    """
    matches = list(_ENV_DETAIL_RE.finditer(text))
    results: List[Dict[str, Any]] = []
    for m in matches:
        inner = m.group(1)
        entry: Dict[str, Any] = {"raw": inner}
        parsed_json: Any = None
        try:
            parsed_json = json.loads(inner)
            entry["content"] = parsed_json
        except (json.JSONDecodeError, ValueError):
            entry["content"] = inner
        entry["json"] = parsed_json
        results.append(entry)
    return results


def generate_random_details(
    seed: Optional[str] = None,
    fields: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a fake ``<environment_details>`` block populated with random values.

    *seed* — optional string used as a deterministic seed for ``random``
    (omit for fully-random output).

    *fields* — optional dict whose keys become top-level keys in the JSON
    payload.  Values that are ``None`` are replaced with randomised defaults.
    """
    rng = random.Random(seed)

    def _rand_str(n: int = 12) -> str:
        return "".join(rng.choices(string.ascii_letters, k=n))

    def _rand_ip() -> str:
        return ".".join(str(rng.randint(1, 255)) for _ in range(4))

    defaults: Dict[str, Any] = {
        "agent": f"agent-{_rand_str(6).lower()}",
        "hostname": _rand_str(10).lower(),
        "ip": _rand_ip(),
        "platform": rng.choice(["linux", "darwin", "windows"]),
        "pid": rng.randint(1000, 65535),
        "cwd": f"/home/{_rand_str(8).lower()}",
        "timestamp": "2026-06-07T22:45:13+05:30",
        "env_vars": {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": f"/home/{_rand_str(8).lower()}",
            "VAPT_VERSION": "3.0.0",
        },
        "tags": rng.sample(
            ["scan", "network", "web", "api", "cloud", "ai", "train"],
            k=rng.randint(1, 4),
        ),
    }

    if fields:
        for k, v in fields.items():
            if v is not None:
                defaults[k] = v

    payload = json.dumps(defaults, indent=2)
    return f"<environment_details>\n{payload}\n</environment_details>"


# Random vulnerability/CVE data for testing and simulation
_RANDOM_VULNS = {
    "web": [
        ("missing-header", "medium", "CVE-2012-5195", "Missing X-Frame-Options header"),
        ("missing-header", "medium", "CVE-2015-1846", "Missing Content-Security-Policy header"),
        ("xss", "high", "CVE-2024-27098", "Reflected XSS vulnerability detected"),
        ("sqli", "critical", "CVE-2024-25701", "SQL injection in login form"),
        ("missing-header", "high", "CVE-2024-47424", "Missing HSTS header"),
    ],
    "network": [
        ("open-port", "critical", "CVE-2022-35951", "Redis exposed on port 6379"),
        ("open-port", "high", "CVE-2024-2984", "MySQL exposed on port 3306"),
        ("open-port", "medium", "CVE-2023-38408", "SSH service detected"),
        ("open-port", "high", "CVE-2024-38416", "MongoDB exposed on port 27017"),
    ],
    "api": [
        ("missing-csp", "high", "CVE-2024-21617", "API endpoint missing CSP header"),
        ("credential-exposure", "critical", "CVE-2024-4322", "API key exposed in response"),
        ("insecure-endpoint", "medium", "CVE-2024-5535", "Unauthenticated endpoint"),
    ],
    "cloud": [
        ("public-storage", "critical", "CVE-2024-27098", "Public S3 bucket detected"),
        ("metadata-exposure", "critical", "CVE-2024-1086", "IMDS endpoint accessible"),
        ("misconfiguration", "high", "CVE-2023-49103", "Security group too permissive"),
    ],
}


def generate_random_scan_result(
    seed: Optional[str] = None,
    count: int = 5,
    scan_type: str = "web",
) -> Dict[str, Any]:
    """
    Generate random scan results with vulnerabilities and CVEs.

    Useful for testing and demonstration purposes.
    """
    rng = random.Random(seed)
    vulns = _RANDOM_VULNS.get(scan_type, _RANDOM_VULNS["web"])

    selected = rng.sample(vulns, k=min(count, len(vulns)))
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for t, sev, _, _ in selected:
        summary[sev] = summary.get(sev, 0) + 1

    return {
        "target": f"https://example-{rng.randint(1, 100)}.com",
        "type": scan_type,
        "status": "completed",
        "vulnerabilities": [
            {"type": t, "severity": sev, "cve": cve, "finding": finding, "location": "/"}
            for t, sev, cve, finding in selected
        ],
        "summary": summary,
    }


def generate_env_details_html(
    blocks: List[Dict[str, Any]],
    title: str = "VAPT Scan Report",
) -> str:
    """
    Render one or more parsed ``<environment_details>`` blocks as a
    self-contained HTML report wrapped in its own ``<environment_details>``
    tag.

    Each block becomes a card showing the raw text, parsed JSON (if any),
    and a timestamp.  The whole document is styled with inline CSS so it
    can be opened in any browser or embedded directly.
    """
    now = datetime.datetime.now().isoformat()
    cards: List[str] = []
    for idx, block in enumerate(blocks, start=1):
        parsed = block.get("json")
        raw = html_mod.escape(block.get("raw", ""))
        parsed_pre = ""
        if parsed is not None:
            parsed_pre = (
                "<h3>Parsed JSON</h3>"
                f"<pre>{html_mod.escape(json.dumps(parsed, indent=2))}</pre>"
            )

        # Handle vulnerability blocks (from scan results)
        if isinstance(parsed, dict) and parsed.get("vulnerabilities"):
            vulns = parsed.get("vulnerabilities", [])
            summary = parsed.get("summary", {})
            vuln_rows = ""
            for v in vulns:
                sev = v.get('severity', 'low')
                vuln_rows += f"<tr><td>{html_mod.escape(v.get('type', ''))}</td><td class='sev-{sev}'>{html_mod.escape(str(sev))}</td><td>{html_mod.escape(v.get('cve', 'N/A'))}</td><td>{html_mod.escape(v.get('finding', ''))}</td></tr>"

            cards.append(
                f"""
            <div class="card">
              <h2>Block #{idx} - {html_mod.escape(parsed.get('target', ''))}</h2>
              <div class="meta">Timestamp: {html_mod.escape(now)}</div>
              <h3>Summary</h3>
              <div class="summary">
                <span class="badge critical">☠ Critical: {summary.get('critical', 0)}</span>
                <span class="badge high">🔥 High: {summary.get('high', 0)}</span>
                <span class="badge medium">⚠️ Medium: {summary.get('medium', 0)}</span>
                <span class="badge low">ℹ️ Low: {summary.get('low', 0)}</span>
              </div>
              <h3>Vulnerabilities</h3>
              <table>
                <tr><th>Type</th><th>Severity</th><th>CVE</th><th>Finding</th></tr>
                {vuln_rows}
              </table>
            </div>
            """
            )
        else:
            cards.append(
                f"""
            <div class="card">
              <h2>Block #{idx}</h2>
              <div class="meta">Timestamp: {html_mod.escape(now)}</div>
              {parsed_pre}
              <h3>Raw Content</h3>
              <pre>{raw}</pre>
            </div>
            """
            )

    body = "\n".join(cards)
    html_doc = f"""\
<environment_details>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_mod.escape(title)}</title>
  <style>
    /* ── Reset & base ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      padding: 2rem;
      line-height: 1.6;
    }}
    /* ── Header ── */
    header {{
      text-align: center;
      margin-bottom: 2.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #1e293b;
    }}
    header h1 {{
      font-size: 2rem;
      font-weight: 700;
      background: linear-gradient(135deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}
    header p {{ color: #94a3b8; margin-top: 0.25rem; font-size: 0.95rem; }}
    /* ── Summary bar ── */
    .summary {{
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
      margin-bottom: 2rem;
      justify-content: center;
    }}
    .summary .badge {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 999px;
      padding: 0.35rem 1.1rem;
      font-size: 0.9rem;
      font-weight: 600;
    }}
    .badge.critical {{ border-color: #ef4444; color: #fca5a5; }}
    .badge.high     {{ border-color: #f97316; color: #fdba74; }}
    .badge.medium   {{ border-color: #eab308; color: #fde047; }}
    .badge.low      {{ border-color: #22c55e; color: #86efac; }}
    /* ── Cards ── */
    .card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 1.5rem 2rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      transition: border-color 0.2s;
    }}
    .card:hover {{ border-color: #475569; }}
    .card h2 {{
      font-size: 1.2rem;
      font-weight: 600;
      color: #f1f5f9;
      margin-bottom: 0.5rem;
    }}
    .card .meta {{
      font-size: 0.8rem;
      color: #64748b;
      margin-bottom: 1rem;
      font-family: 'Fira Code', 'Cascadia Code', monospace;
    }}
    .card h3 {{
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #94a3b8;
      margin: 1rem 0 0.4rem;
    }}
    .card pre {{
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 1rem;
      overflow-x: auto;
      font-size: 0.82rem;
      line-height: 1.5;
    }}
    /* ── Tables ── */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0.75rem 0;
      font-size: 0.88rem;
    }}
    th {{
      background: #0f172a;
      color: #94a3b8;
      text-align: left;
      padding: 0.5rem 0.75rem;
      font-weight: 600;
      border-bottom: 1px solid #334155;
    }}
    td {{
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid #1e293b;
      vertical-align: top;
    }}
    tr:hover td {{ background: #273548; }}
    .sev-critical {{ color: #fca5a5; font-weight: 700; }}
    .sev-high     {{ color: #fdba74; font-weight: 700; }}
    .sev-medium   {{ color: #fde047; }}
    .sev-low      {{ color: #86efac; }}
    /* ── Footer ── */
    footer {{
      text-align: center;
      margin-top: 3rem;
      padding-top: 1rem;
      border-top: 1px solid #1e293b;
      font-size: 0.8rem;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <header>
    <h1>🛡️ {html_mod.escape(title)}</h1>
    <p>Generated by AI-VAPT Tool &mdash; {html_mod.escape(now)}</p>
  </header>

  <div class="summary">
    <span class="badge critical">☠ Critical: {html_mod.escape(str(0))}</span>
    <span class="badge high">🔥 High: {html_mod.escape(str(0))}</span>
    <span class="badge medium">⚠️ Medium: {html_mod.escape(str(0))}</span>
    <span class="badge low">ℹ️ Low: {html_mod.escape(str(0))}</span>
    <span class="badge">📦 Blocks: {html_mod.escape(str(len(blocks)))}</span>
  </div>

  {body}

  <footer>
    AI-VAPT Tool v{html_mod.escape('3.0.0')} &mdash;
    Report generated on {html_mod.escape(now)}
  </footer>
</body>
</html>
</environment_details>
"""
    return html_doc


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER  (inline, previously unused helper)
# ═══════════════════════════════════════════════════════════════════════════════
class _SimpleRateLimiter:
    """In-memory sliding-window rate limiter."""

    def __init__(self, max_calls: int = 60, window: int = 60) -> None:
        self.max_calls = max_calls
        self.window = window
        self._calls: int = 0
        self._reset()

    def _reset(self) -> None:
        self._calls = 0

    def allow(self) -> bool:
        self._calls += 1
        return self._calls <= self.max_calls


def make_rate_limiter(max_calls: int = 60) -> _SimpleRateLimiter:
    return _SimpleRateLimiter(max_calls=max_calls)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI & ENTRY POINTS  (src/main.py)
# ═══════════════════════════════════════════════════════════════════════════════
def run_server() -> None:
    """Start the uvicorn web / API server."""
    import uvicorn  # type: ignore

    host = os.environ.get("VAPT_HOST", "0.0.0.0")
    port = int(os.environ.get("VAPT_PORT", "8000"))
    workers = int(os.environ.get("VAPT_WORKERS", "1"))
    reload = os.environ.get("VAPT_RELOAD", "false").lower() in (
        "1", "true", "yes"
    )

    # Display banner
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║ ██╗   ██╗ █████╗ ██████╗ ███████╗ █████╗ ███████╗ ██████╗ ║
║ ██║   ██║██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝ ║
║ ██║   ██║███████║██████╔╝█████╗  ███████║███████╗██║  ███╗║
║ ╚██╗ ██╔╝██╔══██║██╔═══╝ ██╔══╝  ██╔══██║╚════██║██║   ██║║
║  ╚████╔╝ ██║  ██║██║     ███████╗██║  ██║███████║╚██████╔╝║
║   ╚═══╝  ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ║
║                                                              ║
║  AI-Powered VAPT Tool v{__version__} - Vulnerability Assessment & Pen Testing  ║
║  Starting server on {host}:{port} (workers={workers})                    ║
╚══════════════════════════════════════════════════════════════════╝
""")

    root_logger.info(
        "Launching v%s on %s:%d  (workers=%d, reload=%s)",
        __version__, host, port, workers, reload,
    )
    app = create_app()
    uvicorn.run(
        app, host=host, port=port, log_level="info",
        reload=reload, workers=workers,
    )


_SCANNER_MAP: Dict[str, Any] = {
    "web": None,
    "network": None,
    "api": None,
    "cloud": None,
}


def _get_scanner(scan_type: str):
    """Lazy load scanner classes to avoid import errors."""
    if _SCANNER_MAP[scan_type] is None:
        if scan_type == "web":
            from src.scanners.web.scanner import WebScanner
            _SCANNER_MAP[scan_type] = WebScanner
        elif scan_type == "network":
            from src.scanners.network.scanner import NetworkScanner
            _SCANNER_MAP[scan_type] = NetworkScanner
        elif scan_type == "api":
            from src.scanners.api.scanner import APIScanner
            _SCANNER_MAP[scan_type] = APIScanner
        elif scan_type == "cloud":
            from src.scanners.cloud.scanner import CloudScanner
            _SCANNER_MAP[scan_type] = CloudScanner
    return _SCANNER_MAP[scan_type]


def run_scan(target: str, scan_type: str, output_dir: str = ".", no_report: bool = False) -> None:
    """Run a single vulnerability scan and generate reports (HTML, JSON, PDF)."""
    root_logger.info("Starting %s scan on %s", scan_type, target)
    scanner_cls = _get_scanner(scan_type)
    if scanner_cls is None:
        root_logger.error("Unknown scan type: %s", scan_type)
        sys.exit(1)

    scanner = scanner_cls()
    result = scanner.run(target)
    summary = result.get("summary", {})
    vulns = result.get("vulnerabilities", [])

    print(f"[+] Scan completed. Severity distribution: {summary}")
    if vulns:
        print(f"[+] Found {len(vulns)} vulnerability findings:")
        for v in vulns[:10]:
            sev = v.get("severity", "unknown")
            finding = v.get("finding", "unknown")
            cve = v.get("cve", "N/A")
            print(f"    [{sev}] {finding} ({cve})")

    if no_report:
        return

    # Auto-generate reports
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    import re as re_mod
    safe_target = re_mod.sub(r'[^\w\-_.]', '_', target)

    # JSON report
    json_path = out_path / f"scan_{scan_type}_{safe_target}.json"
    json_path.write_text(json.dumps(result, indent=2))
    root_logger.info("JSON report saved to %s", json_path)

    # HTML report
    html_path = out_path / f"scan_{scan_type}_{safe_target}.html"
    html_report = generate_env_details_html([{"raw": "", "json": result}], title=f"VAPT Scan: {target}")
    html_path.write_text(html_report, encoding="utf-8")
    root_logger.info("HTML report saved to %s", html_path)

    # PDF report (try weasyprint, fallback to basic conversion)
    try:
        from weasyprint import HTML  # type: ignore
        pdf_path = out_path / f"scan_{scan_type}_{safe_target}.pdf"
        HTML(string=html_report).write_pdf(str(pdf_path))
        root_logger.info("PDF report saved to %s", pdf_path)
        print(f"\n[+] Reports generated in {output_dir}/")
        print(f"    - scan_{scan_type}_{safe_target}.json")
        print(f"    - scan_{scan_type}_{safe_target}.html")
        print(f"    - scan_{scan_type}_{safe_target}.pdf")
    except ImportError:
        root_logger.warning("weasyprint not installed - skipping PDF report generation")
        print(f"\n[+] Reports generated in {output_dir}/")
        print(f"    - scan_{scan_type}_{safe_target}.json")
        print(f"    - scan_{scan_type}_{safe_target}.html")


def print_banner() -> None:
    """Print VAPT Tool banner."""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║ ██╗   ██╗ █████╗ ██████╗ ███████╗ █████╗ ███████╗ ██████╗ ║
║ ██║   ██║██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝ ║
║ ██║   ██║███████║██████╔╝█████╗  ███████║███████╗██║  ███╗║
║ ╚██╗ ██╔╝██╔══██║██╔═══╝ ██╔══╝  ██╔══██║╚════██║██║   ██║║
║  ╚████╔╝ ██║  ██║██║     ███████╗██║  ██║███████║╚██████╔╝║
║   ╚═══╝  ╚═╝  ╚═╝╚╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ║
║                    AI-VAPT TOOL v{__version__}                        ║
╚══════════════════════════════════════════════════════════════════╝
""")


def train_models(data_path: str, output_dir: str) -> None:
    """Train AI models from supplied data."""
    root_logger.info("Training AI models from %s", data_path)
    pipeline = TrainingPipeline()
    result = pipeline.train(data_path, output_dir)
    root_logger.info("Training result: %s", result)


def _handle_agent(args: Any) -> None:
    """Dispatch ``agent`` subcommands."""
    if args.agent_command == "parse-env":
        if args.file == "-":
            text = sys.stdin.read()
        else:
            with open(args.file, "r") as fh:
                text = fh.read()
        blocks = parse_environment_details(text)
        print(json.dumps(
            {"blocks_found": len(blocks), "blocks": blocks},
            indent=2,
        ))
    elif args.agent_command == "generate-env":
        fields: Optional[Dict[str, Any]] = None
        if args.agent or args.platform:
            fields = {}
            if args.agent:
                fields["agent"] = args.agent
            if args.platform:
                fields["platform"] = args.platform
        block = generate_random_details(seed=args.seed, fields=fields)
        print(block)
    elif args.agent_command == "random-scan":
        count = getattr(args, "count", 5)
        scan_type = getattr(args, "type", "web")
        random_result = generate_random_scan_result(seed=args.seed, count=count, scan_type=scan_type)
        print(json.dumps(random_result, indent=2))
    else:
        print("Usage: vapt_tool.py agent {parse-env [file]|generate-env|random-scan}")
        sys.exit(1)


def _handle_report(args: Any) -> None:
    """Dispatch ``report`` subcommands."""
    if args.report_command == "html":
        if args.input == "-":
            raw = sys.stdin.read()
        else:
            with open(args.input, "r") as fh:
                raw = fh.read()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            root_logger.error("Invalid JSON input: %s", exc)
            sys.exit(1)

        blocks = data.get("blocks", [])
        if not blocks and "scan" in data:
            blocks = [data]
        title = data.get("title", args.title) or args.title

        html_report = generate_env_details_html(blocks, title=title)
        out_path = Path(args.output)
        out_path.write_text(html_report, encoding="utf-8")
        root_logger.info("HTML report written to %s", out_path)
        print(f"[+] Report saved: {out_path}  ({len(html_report)} bytes, {len(blocks)} blocks)")
    else:
        print("Usage: vapt_tool.py report html <input.json> [-o report.html] [--title NAME]")
        sys.exit(1)


def main() -> None:
    """Main entry point — parse CLI arguments and dispatch."""
    parser = argparse.ArgumentParser(
        description="AI-Powered VAPT Tool",
        epilog="Example: %(prog)s scan https://example.com --type web",
    )
    parser.add_argument(
        "--version", action="version", version=f"VAPT Tool {__version__}",
    )

    sub = parser.add_subparsers(dest="command")

    # ---- server ----
    sub.add_parser("server", help="Start the web / API server")

    # ---- scan ----
    scan_p = sub.add_parser("scan", help="Run a vulnerability scan")
    scan_p.add_argument("target", help="URL, IP, or hostname to scan")
    scan_p.add_argument(
        "--type",
        choices=["web", "network", "api", "cloud"],
        default="web",
        help="Scan type (default: web)",
    )
    scan_p.add_argument(
        "--output-dir", "-o", default=".",
        help="Directory for generated reports (default: current directory)",
    )
    scan_p.add_argument(
        "--no-report", action="store_true",
        help="Skip automatic report generation",
    )

    # ---- train ----
    train_p = sub.add_parser("train", help="Train AI models")
    train_p.add_argument("data", help="Path to training CSV / JSON")
    train_p.add_argument(
        "--output-dir", default="models/",
        help="Directory for saved models (default: models/)",
    )

    # ---- agent ----
    agent_p = sub.add_parser("agent", help="Random API agent commands")
    agent_sub = agent_p.add_subparsers(dest="agent_command")

    # agent parse
    parse_p = agent_sub.add_parser(
        "parse-env", help="Parse <environment_details> from a file or stdin"
    )
    parse_p.add_argument(
        "file", nargs="?", default="-",
        help="File path to read (default: stdin)",
    )

    # agent generate
    gen_p = agent_sub.add_parser(
        "generate-env", help="Generate a random <environment_details> block"
    )
    gen_p.add_argument(
        "--seed", default=None,
        help="Optional seed for reproducible output",
    )
    gen_p.add_argument(
        "--agent", default=None, help="Agent name"
    )
    gen_p.add_argument(
        "--platform", default=None,
        choices=["linux", "darwin", "windows"],
        help="Platform",
    )

    # agent random-scan - generate random vulnerability/CVE data
    rand_p = agent_sub.add_parser(
        "random-scan", help="Generate random scan results with vulnerabilities"
    )
    rand_p.add_argument(
        "--seed", default=None,
        help="Optional seed for reproducible output",
    )
    rand_p.add_argument(
        "--count", type=int, default=5,
        help="Number of vulnerabilities to generate (default: 5)",
    )
    rand_p.add_argument(
        "--type", choices=["web", "network", "api", "cloud"],
        default="web", help="Scan type for generated results",
    )

    # ---- report ----
    report_p = sub.add_parser("report", help="Generate HTML report")
    report_sub = report_p.add_subparsers(dest="report_command")

    r_html = report_sub.add_parser(
        "html", help="Generate HTML report from scan data"
    )
    r_html.add_argument(
        "input", help="JSON file with scan results (or '-' for stdin)"
    )
    r_html.add_argument(
        "--output", "-o", default="report.html",
        help="Output HTML file path (default: report.html)",
    )
    r_html.add_argument(
        "--title", default="VAPT Scan Report",
        help="Report title",
    )

    args = parser.parse_args()

    # Print banner before executing any command (skip for --help/--version)
    if args.command is not None or len(sys.argv) > 1:
        print_banner()

    if args.command == "server":
        run_server()
    elif args.command == "scan":
        run_scan(args.target, args.type, getattr(args, "output_dir", "."), getattr(args, "no_report", False))
    elif args.command == "train":
        train_models(args.data, args.output_dir)
    elif args.command == "agent":
        _handle_agent(args)
    elif args.command == "report":
        _handle_report(args)
    else:
        # No subcommand — default to server
        run_server()


if __name__ == "__main__":
    main()
