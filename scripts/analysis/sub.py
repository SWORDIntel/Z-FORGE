#!/usr/bin/env python3
"""subdomain_enumerator.py

Automated Certificate‑Transparency + DNS brute‑force sub‑domain discovery.

* Logs to console and rotating file with GMT timestamps.
* Configurable via CLI flags.
* Resumable (stores progress to tmp JSON).
* Thread‑pooled DNS look‑ups with progress‑bar.

Author : SWORD‑EPI – 2025-07-22
"""

import argparse
import concurrent.futures
import json
import logging
import logging.handlers
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import requests
import dns.exception
import dns.resolver
from tqdm import tqdm

# ---------------------------------------------------------------------------#
# Configuration constants – tweak if you want to hard‑code defaults here
# ---------------------------------------------------------------------------#
CRT_SH_API_URL = "https://crt.sh/?q=africuniabank.com&output=json"
DNS_RESOLVERS = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "9.9.9.9"]
DEFAULT_WORDLIST = Path(__file__).with_name("subdomains-top1million-110000.txt")
STATE_FILE = Path(".enum_state.json")          # Progress snapshot for resume
LOG_FILE = Path("sub_enum.log")
THREADS = 50                                   # reasonable default
REQUEST_TIMEOUT = 20
DNS_TIMEOUT = 5


# ---------------------------------------------------------------------------#
# Helper utilities                                                            #
# ---------------------------------------------------------------------------#

def utc_ts() -> str:
    """Return current time as ISO‑8601 in **GMT**."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class GMTFormatter(logging.Formatter):
    """Prefix every log line with 'GMT: <timestamp> |' per user spec."""

    def format(self, record):
        record.asctime = utc_ts()
        original = super().format(record)
        return f"GMT: {record.asctime} | {record.message}"


def setup_logging(verbose: bool = False) -> None:
    """Configure console & rotating file logs."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = GMTFormatter("%(message)s")

    root = logging.getLogger()
    root.setLevel(level)

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Rotating file (5×2 MB)
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)


def jitter_sleep(base: float = 1.0, variance: float = 0.3) -> None:
    """Sleep with ±variance jitter to mimic human network traffic."""
    if base <= 0:
        return
    delta = base * variance
    time.sleep(random.uniform(max(0.01, base - delta), base + delta))


# ---------------------------------------------------------------------------#
# Certificate Transparency enumeration                                        #
# ---------------------------------------------------------------------------#

def enumerate_ct_log(domain: str) -> Set[str]:
    """Query crt.sh JSON interface and extract hostnames."""
    logging.info("Initiating CT‑log enumeration for %s", domain)
    query = f"%.{domain}"
    url = CRT_SH_API_URL.format(query=query)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }

    session = requests.Session()
    session.headers.update(headers)

    subdomains: Set[str] = set()

    try:
        jitter_sleep()
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        certs = resp.json()

        for cert in certs:
            if common := cert.get("common_name"):
                subdomains.add(common.lower())
            if san_block := cert.get("name_value"):
                for san in san_block.split():
                    san = san.strip().lower()
                    if san.startswith("*."):
                        subdomains.add(san[2:])
                    else:
                        subdomains.add(san)
        logging.info("CT‑log enumeration complete. %d candidates collected.", len(subdomains))
    except requests.RequestException as exc:
        logging.error("Failed CT‑log request: %s", exc)
    except json.JSONDecodeError:
        logging.error("Malformed JSON from crt.sh – possible rate‑limit.")
    return subdomains


# ---------------------------------------------------------------------------#
# DNS brute‑force enumeration                                                 #
# ---------------------------------------------------------------------------#

def build_resolver() -> dns.resolver.Resolver:
    res = dns.resolver.Resolver()
    res.nameservers = DNS_RESOLVERS
    res.timeout = DNS_TIMEOUT
    res.lifetime = DNS_TIMEOUT
    return res


def resolve_host(host: str, resolver: dns.resolver.Resolver) -> Tuple[str, List[str]]:
    """Resolve A records for *host*. Returns tuple(host,[ips]) or raises."""
    answers = resolver.resolve(host, "A")
    return host, [r.address for r in answers]


def enumerate_dns(
    domain: str,
    wordlist: Iterable[str],
    threads: int = THREADS,
    resume: bool = True,
) -> Dict[str, List[str]]:
    """Thread‑pooled brute‑force DNS look‑up; returns {host: [ips]} mapping."""
    logging.info("Starting DNS brute‑force (%d threads)…", threads)
    resolver = build_resolver()
    resolved: Dict[str, List[str]] = {}

    # Optional resume
    if resume and STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as fh:
                resolved = json.load(fh)
            logging.info("Resuming from previous state file (%d hosts already).", len(resolved))
        except Exception:
            logging.warning("Could not parse state file; starting fresh.")

    want: List[str] = [
        f"{sub}.{domain}" for sub in wordlist if f"{sub}.{domain}" not in resolved
    ]

    # Graceful shutdown on ^C
    stop_flag = {"stop": False}

    def sigint_handler(sig, frame):
        stop_flag["stop"] = True
        logging.warning("Interrupt received – shutting down after current batch.")
    signal.signal(signal.SIGINT, sigint_handler)

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {
            executor.submit(resolve_host, host, resolver): host for host in want
        }

        for fut in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="DNS",
            unit="host",
        ):
            if stop_flag["stop"]:
                break
            host = futures[fut]
            try:
                h, ips = fut.result()
                resolved[h] = ips
                logging.debug("Resolved %-50s %s", h, ", ".join(ips))
            except (
                dns.resolver.NXDOMAIN,
                dns.resolver.NoAnswer,
                dns.resolver.NoNameservers,
                dns.exception.Timeout,
            ):
                pass  # silence expected failures
            except Exception as e:
                logging.error("Unexpected error resolving %s: %s", host, e)

    # Save progress
    try:
        with STATE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(resolved, fh, indent=2)
    except Exception as e:
        logging.error("Failed to write state file: %s", e)

    logging.info("DNS brute‑force complete. %d live hosts discovered.", len(resolved))
    return resolved


# ---------------------------------------------------------------------------#
# Helper: read wordlist                                                       #
# ---------------------------------------------------------------------------#

def load_wordlist(path: Path) -> List[str]:
    if not path.exists():
        logging.error("Wordlist not found at %s", path)
        return []
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        return [line.strip().lower() for line in fh if line.strip()]


# ---------------------------------------------------------------------------#
# CLI entry‑point                                                             #
# ---------------------------------------------------------------------------#

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated sub‑domain enumeration (CT + DNS brute)."
    )
    parser.add_argument("domain", help="Target apex domain, e.g. example.com")
    parser.add_argument(
        "-w",
        "--wordlist",
        type=Path,
        default=DEFAULT_WORDLIST,
        help=f"Path to sub‑domain wordlist (default: {DEFAULT_WORDLIST})",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=THREADS,
        help="Concurrent DNS worker threads (default: %(default)s)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging")
    parser.add_argument(
        "--no-resume", dest="resume", action="store_false", help="Disable resume feature"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write combined results to JSON/CSV path (auto‑format by extension)",
    )
    return parser.parse_args()


