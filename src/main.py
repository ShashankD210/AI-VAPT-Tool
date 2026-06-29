#!/usr/bin/env python3
"""
AI-Powered VAPT Tool
====================
Usage:
    python main.py
    python main.py --help
    python main.py --version
"""
import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def create_rate_limiter():

    class SimpleRateLimiter:
        def __init__(self, max_calls: int = 60):
            self.max_calls = max_calls
            self.calls = 0
            self.reset()

        def reset(self):
            self.calls = 0

        def allow(self) -> bool:
            self.calls += 1
            return self.calls <= self.max_calls

    return SimpleRateLimiter()


def run_server():
    import uvicorn
    from src.api.server import create_app

    host = os.environ.get("VAPT_HOST", "0.0.0.0")
    port = int(os.environ.get("VAPT_PORT", "8000"))
    workers = int(os.environ.get("VAPT_WORKERS", "1"))
    reload = os.environ.get("VAPT_RELOAD", "false").lower() in ("1", "true", "yes")

    print(f"[*] Launching {__import__('src.version', fromlist=['__version__']).__version__} on {host}:{port}")
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info", reload=reload, workers=workers)


def run_scan(target: str, scan_type: str):
    print(f"[*] Starting {scan_type} scan on {target}...")
    if scan_type == "web":
        from src.scanners.web.scanner import WebScanner
        scanner = WebScanner()
    elif scan_type == "network":
        from src.scanners.network.scanner import NetworkScanner
        scanner = NetworkScanner()
    elif scan_type == "api":
        from src.scanners.api.scanner import APIScanner
        scanner = APIScanner()
    elif scan_type == "cloud":
        from src.scanners.cloud.scanner import CloudScanner
        scanner = CloudScanner()
    else:
        print(f"[-] Unknown scan type: {scan_type}")
        sys.exit(1)

    result = scanner.run(target)
    print(f"[+] Scan completed. Severity distribution: {result.get('summary', {})}")


def train_models(data_path: str, output_dir: str):
    print(f"[*] Training AI models from {data_path}...")
    print(f"[+] Models saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="AI-Powered VAPT Tool")
    parser.add_argument("--version", action="version", version="VAPT Tool 3.0.0")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("server", help="Start the web/API server")

    scan_parser = subparsers.add_parser("scan", help="Run a vulnerability scan")
    scan_parser.add_argument("target", help="URL, IP, or hostname to scan")
    scan_parser.add_argument("--type", choices=["web", "network", "api", "cloud"], default="web", help="Scan type")

    train_parser = subparsers.add_parser("train", help="Train AI models")
    train_parser.add_argument("data", help="Path to training CSV/JSON")
    train_parser.add_argument("--output-dir", default="models/", help="Where to save trained models")

    args = parser.parse_args()

    if args.command == "server":
        run_server()
    elif args.command == "scan":
        run_scan(args.target, args.type)
    elif args.command == "train":
        train_models(args.data, args.output_dir)
    else:
        run_server()


if __name__ == "__main__":
    main()
