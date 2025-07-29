#!/usr/bin/env python3
"""
ckan_dkan_probe.py
~~~~~~~~~~~~~~~~~~

Tiny yet robust inventory crawler for CKAN & DKAN government data portals.

Features
--------
* Auto‑detect CKAN vs DKAN from the base URL.
* Enumerates every dataset & resource, with resumable pagination.
* Verbose, colour‑friendly console logs + tqdm progress bars.
* Exponential back‑off, status‑code retry, and rotating User‑Agents.
* Saves results and crawler state to JSON so you can safely resume.

Usage
-----
# Crawl a single portal
python ckan_dkan_probe.py --url https://catalog.data.gov \
                          --output data_inventory.json \
                          --state crawl_state.json

# Crawl many portals listed in a text file (one URL per line)
python ckan_dkan_probe.py --url-list portals.txt \
                          --output data_inventory.json \
                          --state crawl_state.json
"""
import argparse
import json
import logging
import pathlib
import random
import sys
import time
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter, Retry
from tqdm import tqdm

################################################################################
# ----------------------------  CONFIGURATION  --------------------------------#
################################################################################
UA_POOL = [
    # Minimal but diverse UA strings; feel free to extend.
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/537.36 Chrome/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/126.0",
]

REQUEST_TIMEOUT = (10, 30)  # (connect, read) seconds
MAX_RETRIES = 5             # per‑request retries on 5xx or connect issues
BACKOFF_FACTOR = 1          # exponential back‑off base
PAGE_SIZE = 100             # datasets per page (CKAN) / customise per portal

################################################################################
# -----------------------  SESSION & RETRY HELPERS  --------------------------- #
################################################################################
def build_session() -> requests.Session:
    """Return a hardened requests.Session with retry and rotating UA."""
    session = requests.Session()
    retries = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": random.choice(UA_POOL)})
    return session


################################################################################
# --------------------------  PORTAL DETECTION  ------------------------------- #
################################################################################
def detect_portal_type(base_url: str, session: requests.Session) -> str:
    """
    Detect whether the portal is CKAN or DKAN.

    Returns
    -------
    "ckan" or "dkan"

    Raises
    ------
    RuntimeError if detection fails.
    """
    logging.debug("Detecting portal type for %s …", base_url)
    # CKAN probe: /api/3/action/site_read (public endpoint)
    try:
        r = session.get(f"{base_url.rstrip('/')}/api/3/action/site_read",
                        timeout=REQUEST_TIMEOUT)
        if r.ok and r.json().get("success"):
            logging.info("Detected CKAN portal (%s)", base_url)
            return "ckan"
    except Exception as err:
        logging.debug("CKAN probe failed: %s", err)

    # DKAN probe: /api/1/metastore/schemas/dataset/items?limit=1
    try:
        probe = f"{base_url.rstrip('/')}/api/1/metastore/schemas/dataset/items?limit=1"
        r = session.get(probe, timeout=REQUEST_TIMEOUT)
        if r.ok and r.headers.get("Content-Type", "").startswith("application/json"):
            logging.info("Detected DKAN portal (%s)", base_url)
            return "dkan"
    except Exception as err:
        logging.debug("DKAN probe failed: %s", err)

    raise RuntimeError(f"Unable to detect portal type for {base_url}")


################################################################################
# -----------------------  CKAN ENUMERATION LOGIC  ---------------------------- #
################################################################################
def enumerate_ckan(base_url: str,
                   session: requests.Session,
                   start_offset: int = 0) -> Dict[str, dict]:
    """
    Enumerate all datasets and resources for a CKAN portal.

    Parameters
    ----------
    base_url : str
        The root of the portal (no trailing slash).
    start_offset : int
        Resume offset for dataset pagination.
    Returns
    -------
    Dict keyed by dataset_id with metadata incl. list of resources.
    """
    logging.info("Starting CKAN crawl on %s (offset=%d)", base_url, start_offset)
    inventory: Dict[str, dict] = {}
    total_count = None
    offset = start_offset
    pbar = tqdm(disable=False, unit="dataset", desc="Datasets")

    while True:
        params = {"rows": PAGE_SIZE, "start": offset}
        url = f"{base_url.rstrip('/')}/api/3/action/package_search"
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            logging.warning("package_search failed @%d: %s", offset, resp.text)
            break
        data = resp.json()
        # CKAN returns success bool and result
        if not data.get("success"):
            logging.error("CKAN returned success=false @%d", offset)
            break
        result = data["result"]
        total_count = result["count"] if total_count is None else total_count
        datasets = result["results"]

        if not datasets:
            break  # Done

        for ds in datasets:
            ds_id = ds["id"]
            inventory[ds_id] = {
                "title": ds.get("title"),
                "name": ds.get("name"),
                "metadata_modified": ds.get("metadata_modified"),
                "resources": [],
            }

            # Fetch full dataset incl. resources
            detail = session.get(
                f"{base_url.rstrip('/')}/api/3/action/package_show",
                params={"id": ds_id},
                timeout=REQUEST_TIMEOUT,
            )
            if detail.ok and detail.json().get("success"):
                full = detail.json()["result"]
                inventory[ds_id]["resources"] = [
                    {
                        "id": res["id"],
                        "name": res.get("name"),
                        "format": res.get("format"),
                        "url": res.get("url"),
                        "last_modified": res.get("last_modified"),
                    }
                    for res in full.get("resources", [])
                ]
            pbar.update(1)

        offset += PAGE_SIZE
        if offset >= total_count:
            break

    pbar.close()
    logging.info("CKAN crawl finished: %d datasets", len(inventory))
    return inventory, offset  # Return offset to support resumption


################################################################################
# -----------------------  DKAN ENUMERATION LOGIC  ---------------------------- #
################################################################################
def enumerate_dkan(base_url: str,
                   session: requests.Session,
                   start_offset: int = 0) -> Dict[str, dict]:
    """
    Enumerate datasets for a DKAN portal via Metastore API.

    Note: DKAN implementations vary. We use the official pattern documented in
    DKAN 1.x: /api/1/metastore/schemas/dataset/items.

    Returns inventory dict similarly shaped as enumerate_ckan.
    """
    logging.info("Starting DKAN crawl on %s (offset=%d)", base_url, start_offset)
    inventory: Dict[str, dict] = {}
    offset = start_offset
    pbar = tqdm(disable=False, unit="dataset", desc="Datasets")

    while True:
        params = {"limit": PAGE_SIZE, "offset": offset}
        url = f"{base_url.rstrip('/')}/api/1/metastore/schemas/dataset/items"
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if not resp.ok:
            logging.warning("Metastore items failed @%d: %s", offset, resp.text)
            break
        data = resp.json()
        datasets = data.get("data", [])
        if not datasets:
            break

        for ds in datasets:
            ds_id = ds.get("identifier")
            if not ds_id:
                continue
            inventory[ds_id] = {
                "title": ds.get("title"),
                "modified": ds.get("modified"),
                "resources": [],
            }

            # DKAN resource enumeration is typically via datastore/query
            # but dataset metadata often embeds distribution list
            for distr in ds.get("distribution", []):
                inventory[ds_id]["resources"].append(
                    {
                        "id": distr.get("identifier"),
                        "format": distr.get("format"),
                        "url": distr.get("accessURL") or distr.get("downloadURL"),
                    }
                )
            pbar.update(1)

        offset += PAGE_SIZE

    pbar.close()
    logging.info("DKAN crawl finished: %d datasets", len(inventory))
    return inventory, offset


################################################################################
# ----------------------------  STATE HELPERS  --------------------------------#
################################################################################
def load_state(path: pathlib.Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    return {}


def save_state(path: pathlib.Path, state: dict) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(state, fp, indent=2)
    tmp.rename(path)
    logging.debug("State saved to %s", path)


################################################################################
# -----------------------------  MAIN DRIVER  ---------------------------------#
################################################################################
def crawl_portal(base_url: str,
                 session: requests.Session,
                 state: dict) -> Dict[str, dict]:
    """
    Crawl a single portal, resuming where possible.

    The state dict tracks:
        state[base_url] = {
            "type": "ckan"|"dkan",
            "offset": <int>,
            "inventory": { ... }
        }
    """
    portal_state = state.get(base_url, {})
    portal_type = portal_state.get("type")
    offset = portal_state.get("offset", 0)
    inventory = portal_state.get("inventory", {})

    # Detect portal type only once
    if not portal_type:
        portal_type = detect_portal_type(base_url, session)

    if portal_type == "ckan":
        new_inventory, new_offset = enumerate_ckan(base_url, session, offset)
    else:
        new_inventory, new_offset = enumerate_dkan(base_url, session, offset)

    # Merge inventories (support resume)
    inventory.update(new_inventory)
    state[base_url] = {
        "type": portal_type,
        "offset": new_offset,
        "inventory": inventory,
    }
    return state


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory CKAN/DKAN portals and output JSON."
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="Single portal base URL (e.g. https://catalog.data.gov)")
    g.add_argument("--url-list", help="Path to text file with portal URLs (one per line)")

    parser.add_argument("--output", required=True, help="Path to write inventory JSON")
    parser.add_argument("--state", required=True, help="Path for resumable crawl state")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable DEBUG log level"
    )
    args = parser.parse_args()

    # Configure logging before doing anything else
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Build resilient requests session
    session = build_session()

    # Load or bootstrap state
    state_path = pathlib.Path(args.state)
    state = load_state(state_path)

    # Build portal list
    portals: List[str] = []
    if args.url:
        portals = [args.url.strip()]
    else:
        with open(args.url_list, "r", encoding="utf-8") as fp:
            portals = [ln.strip() for ln in fp if ln.strip()]

    # Crawl each portal sequentially
    for portal in portals:
        try:
            state = crawl_portal(portal, session, state)
            # Persist intermediate state after each portal
            save_state(state_path, state)
        except Exception as exc:
            logging.exception("Portal crawl failed for %s: %s", portal, exc)

    # Strip inventories out into standalone output file
    inventory_out = {
        portal: data["inventory"] for portal, data in state.items()
    }
    with open(args.output, "w", encoding="utf-8") as fp:
        json.dump(inventory_out, fp, indent=2)

    logging.info("Completed. Inventory written to %s", args.output)


if __name__ == "__main__":
    main()
