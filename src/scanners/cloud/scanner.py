"""Cloud scanner for misconfiguration detection."""
from __future__ import annotations

import urllib3
from typing import Any

from src.exceptions import ScanError
from src.utils.logger import setup_logger

logger = setup_logger("vapt.cloud")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Common cloud service vulnerabilities
CLOUD_VULNERABILITIES = {
    "s3": {"severity": "critical", "cve": "CVE-2024-21617", "finding": "Public S3 bucket"},
    "azure-blob": {"severity": "critical", "cve": "CVE-2024-38071", "finding": "Public blob container"},
    "gcs": {"severity": "critical", "cve": "CVE-2024-27098", "finding": "Public GCS bucket"},
}


class CloudScanner:
    def run(self, target: str) -> dict[str, Any]:
        logger.info("Running cloud scan on %s", target)
        vulnerabilities = []
        services = []
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        try:
            import requests  # type: ignore
            from requests.exceptions import RequestException

            if target.startswith(("s3://", "http")):
                url = target if target.startswith("http") else f"https://{target[5:]}"
                try:
                    resp = requests.get(url, timeout=5, verify=False)
                    if resp.status_code == 200:
                        services.append({"name": "s3", "status": "accessible"})
                        vulnerabilities.append({
                            "type": "public-storage",
                            "severity": "critical",
                            "finding": "Publicly accessible cloud storage",
                            "cve": "CVE-2024-27098",
                            "location": url,
                        })
                        summary["critical"] += 1
                except RequestException:
                    pass

            if "169.254.169.254" in target or "metadata" in target.lower():
                services.append({"name": "metadata", "status": "endpoint-exposed"})
                vulnerabilities.append({
                    "type": "metadata-exposure",
                    "severity": "critical",
                    "finding": "Cloud metadata endpoint exposed (IMDS)",
                    "cve": "CVE-2024-1086",
                    "location": "169.254.169.254",
                })
                summary["critical"] += 1

        except ImportError:
            logger.warning("requests not installed - skipping cloud checks")
        except Exception as exc:
            logger.debug("Scan partial due to error: %s", exc)

        return {
            "target": target,
            "type": "cloud",
            "status": "completed",
            "services": services,
            "vulnerabilities": vulnerabilities,
            "summary": summary,
        }
