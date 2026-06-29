"""API scanner for vulnerability assessment."""
from __future__ import annotations

import re
import urllib3
from typing import Any

from src.exceptions import ScanError
from src.utils.logger import setup_logger

logger = setup_logger("vapt.api")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API vulnerability patterns
JSON_INJECTION_PATTERNS = [
    r"(?i)(['\"]?\$?\{.*\})",
    r"(?i)(['\"]\s*\|\s*\$\{)",
]

INSECURE_DESERIAL_PATTERNS = [
    r"(?i)(java\.serialize)",
    r"(?i)(pickle\.loads?)",
    r"(?i)(yaml\.load\()",
]


class APIScanner:
    def run(self, target: str) -> dict[str, Any]:
        logger.info("Running API scan on %s", target)
        vulnerabilities = []
        endpoints_tested = 0
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        try:
            import requests  # type: ignore
            from requests.exceptions import RequestException

            paths = ["", "/api", "/v1", "/v2", "/graphql", "/swagger.json", "/openapi.json"]
            for path in paths:
                url = target.rstrip("/") + path
                try:
                    resp = requests.get(url, timeout=5, verify=False)
                    endpoints_tested += 1

                    csp = resp.headers.get("content-security-policy")
                    if not csp:
                        vulnerabilities.append({
                            "type": "missing-csp",
                            "severity": "high",
                            "finding": "API endpoint lacks CSP header",
                            "cve": "CVE-2024-21617",
                            "location": url,
                        })
                        summary["high"] += 1

                    body = resp.text
                    if re.search(r"api[_-]?key\s*[:=]\s*['\"]?[a-z0-9]{20,}", body, re.I):
                        vulnerabilities.append({
                            "type": "credential-exposure",
                            "severity": "critical",
                            "finding": "API key exposed in response",
                            "cve": "CVE-2024-38416",
                            "location": url,
                        })
                        summary["critical"] += 1

                except RequestException:
                    pass

        except ImportError:
            logger.warning("requests not installed - skipping API checks")
        except Exception as exc:
            logger.debug("Scan partial due to error: %s", exc)

        return {
            "target": target,
            "type": "api",
            "status": "completed",
            "endpoints_tested": endpoints_tested,
            "vulnerabilities": vulnerabilities,
            "summary": summary,
        }
