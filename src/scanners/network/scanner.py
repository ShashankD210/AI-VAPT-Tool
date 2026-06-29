"""Network scanner for vulnerability assessment."""
from __future__ import annotations

from typing import Any

from src.exceptions import ScanError
from src.utils.logger import setup_logger

logger = setup_logger("vapt.network")

# Common vulnerable services and their CVEs
VULNERABLE_SERVICES = {
    21: {"service": "ftp", "severity": "high", "cve": "CVE-2019-4058"},
    22: {"service": "ssh", "severity": "medium", "cve": "CVE-2023-38408"},
    23: {"service": "telnet", "severity": "critical", "cve": "CVE-2022-32165"},
    25: {"service": "smtp", "severity": "medium", "cve": "CVE-2023-49103"},
    80: {"service": "http", "severity": "medium", "cve": "CVE-2024-38416"},
    443: {"service": "https", "severity": "medium", "cve": "CVE-2024-47424"},
    3306: {"service": "mysql", "severity": "high", "cve": "CVE-2024-2984"},
    5432: {"service": "postgresql", "severity": "high", "cve": "CVE-2024-4322"},
    6379: {"service": "redis", "severity": "critical", "cve": "CVE-2022-35951"},
    27017: {"service": "mongodb", "severity": "high", "cve": "CVE-2024-5535"},
}


class NetworkScanner:
    def run(self, target: str) -> dict[str, Any]:
        logger.info("Running network scan on %s", target)
        vulnerabilities = []
        open_ports = []
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        try:
            import nmap  # type: ignore

            scanner = nmap.PortScanner()
            scanner.scan(target, arguments="-sT -T4 --top-ports 100")

            for host in scanner.all_hosts():
                for proto in scanner[host].all_protocols():
                    ports = scanner[host][proto].keys()
                    for port in ports:
                        state = scanner[host][proto][port]["state"]
                        if state == "open":
                            open_ports.append(port)
                            svc_info = VULNERABLE_SERVICES.get(port, {})
                            if svc_info:
                                vulnerabilities.append({
                                    "type": "open-port",
                                    "severity": svc_info["severity"],
                                    "finding": f"Open port {port} - {svc_info['service']} service",
                                    "cve": svc_info["cve"],
                                    "location": f"{target}:{port}",
                                })
                                summary[svc_info["severity"]] += 1

        except ImportError:
            logger.warning("python-nmap not installed - skipping port scanning")
        except Exception as exc:
            logger.debug("Scan partial due to error: %s", exc)

        return {
            "target": target,
            "type": "network",
            "status": "completed",
            "open_ports": open_ports,
            "vulnerabilities": vulnerabilities,
            "summary": summary,
        }
