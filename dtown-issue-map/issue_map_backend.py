from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "public"
ARCHIVE_DIR = DATA_DIR / "archive"
KML_PATH = DATA_DIR / "issues.kml"
STATUS_PATH = DATA_DIR / "statuses.json"

STATUS_VALUES = {"fixed", "pending", "down"}
DEFAULT_STATUS = "pending"

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_vercel_runtime() -> bool:
    return os.getenv("VERCEL") == "1" or bool(os.getenv("VERCEL_ENV"))


def get_storage_state() -> dict[str, Any]:
    if is_vercel_runtime():
        return {
            "read_only": True,
            "reason": (
                "This Vercel deployment is running in read-only file storage. "
                "Map viewing works, but status updates and KML uploads need persistent storage "
                "such as Vercel Blob or a database."
            ),
        }
    return {"read_only": False, "reason": ""}


def ensure_writable_storage() -> None:
    storage = get_storage_state()
    if storage["read_only"]:
        raise RuntimeError(storage["reason"])


def normalize_name(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if not STATUS_PATH.exists():
        STATUS_PATH.write_text(
            json.dumps({"items": {}, "updated_at": utc_now_iso()}, indent=2),
            encoding="utf-8",
        )


def load_status_store() -> dict[str, Any]:
    ensure_data_files()
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        payload = {"items": {}, "updated_at": utc_now_iso()}
    if not isinstance(payload, dict):
        payload = {"items": {}, "updated_at": utc_now_iso()}
    items = payload.get("items")
    if not isinstance(items, dict):
        payload["items"] = {}
    payload.setdefault("updated_at", utc_now_iso())
    return payload


def save_status_store(payload: dict[str, Any]) -> None:
    payload["updated_at"] = utc_now_iso()
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_kml_points(kml_path: Path) -> list[dict[str, Any]]:
    if not kml_path.exists():
        return []
    root = ET.parse(kml_path).getroot()
    points: list[dict[str, Any]] = []
    for index, placemark in enumerate(root.findall(".//kml:Placemark", KML_NS), start=1):
        name = (placemark.findtext("kml:name", default="", namespaces=KML_NS) or "").strip()
        description = (placemark.findtext("kml:description", default="", namespaces=KML_NS) or "").strip()
        coordinates = (
            placemark.findtext(".//kml:Point/kml:coordinates", default="", namespaces=KML_NS) or ""
        ).strip()
        if not coordinates:
            continue
        parts = [piece.strip() for piece in coordinates.split(",")]
        if len(parts) < 2:
            continue
        try:
            longitude = float(parts[0])
            latitude = float(parts[1])
            altitude = float(parts[2]) if len(parts) > 2 and parts[2] else 0.0
        except ValueError:
            continue
        feature_id = placemark.attrib.get("id") or f"{normalize_name(name) or 'issue-point'}-{index}"
        points.append(
            {
                "id": feature_id,
                "name": name or f"Issue Point {index}",
                "description": description,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "normalized_name": normalize_name(name or f"Issue Point {index}"),
            }
        )
    return points


def match_status_entry(
    point: dict[str, Any],
    status_items: dict[str, Any],
    slug_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if point["id"] in status_items and isinstance(status_items[point["id"]], dict):
        return status_items[point["id"]]
    return slug_lookup.get(point["normalized_name"], {})


def build_issue_payload() -> dict[str, Any]:
    status_store = load_status_store()
    status_items = status_store.get("items", {})
    slug_lookup = {}
    for item in status_items.values():
        if isinstance(item, dict) and item.get("normalized_name"):
            slug_lookup[item["normalized_name"]] = item

    points = parse_kml_points(KML_PATH)
    features = []
    bounds = {"min_lat": None, "max_lat": None, "min_lng": None, "max_lng": None}

    for point in points:
        status_entry = match_status_entry(point, status_items, slug_lookup)
        status = status_entry.get("status") if status_entry.get("status") in STATUS_VALUES else DEFAULT_STATUS
        feature = {
            "id": point["id"],
            "name": point["name"],
            "description": point["description"],
            "status": status,
            "notes": status_entry.get("notes", ""),
            "reported_by": status_entry.get("reported_by", ""),
            "last_updated": status_entry.get("last_updated", ""),
            "latitude": point["latitude"],
            "longitude": point["longitude"],
            "altitude": point["altitude"],
        }
        features.append(feature)
        bounds["min_lat"] = point["latitude"] if bounds["min_lat"] is None else min(bounds["min_lat"], point["latitude"])
        bounds["max_lat"] = point["latitude"] if bounds["max_lat"] is None else max(bounds["max_lat"], point["latitude"])
        bounds["min_lng"] = point["longitude"] if bounds["min_lng"] is None else min(bounds["min_lng"], point["longitude"])
        bounds["max_lng"] = point["longitude"] if bounds["max_lng"] is None else max(bounds["max_lng"], point["longitude"])

    counts = {
        "all": len(features),
        "fixed": sum(1 for feature in features if feature["status"] == "fixed"),
        "pending": sum(1 for feature in features if feature["status"] == "pending"),
        "down": sum(1 for feature in features if feature["status"] == "down"),
    }

    return {
        "project_name": "Downtown Kingston Live Issues Map",
        "kml_file": KML_PATH.name,
        "kml_last_modified": datetime.fromtimestamp(KML_PATH.stat().st_mtime, UTC).isoformat().replace("+00:00", "Z")
        if KML_PATH.exists()
        else "",
        "status_last_modified": status_store.get("updated_at", ""),
        "features": features,
        "counts": counts,
        "bounds": bounds,
        "storage": get_storage_state(),
    }


def sync_status_store_to_points(points: list[dict[str, Any]]) -> dict[str, Any]:
    existing = load_status_store()
    old_items = existing.get("items", {})
    slug_lookup = {}
    for item in old_items.values():
        if isinstance(item, dict) and item.get("normalized_name"):
            slug_lookup[item["normalized_name"]] = item

    new_items: dict[str, Any] = {}
    for point in points:
        status_entry = {}
        if point["id"] in old_items and isinstance(old_items[point["id"]], dict):
            status_entry = dict(old_items[point["id"]])
        elif point["normalized_name"] in slug_lookup:
            status_entry = dict(slug_lookup[point["normalized_name"]])
        status_entry.setdefault("status", DEFAULT_STATUS)
        status_entry.setdefault("notes", "")
        status_entry.setdefault("reported_by", "")
        status_entry.setdefault("last_updated", "")
        status_entry["normalized_name"] = point["normalized_name"]
        status_entry["display_name"] = point["name"]
        new_items[point["id"]] = status_entry
    payload = {"items": new_items, "updated_at": utc_now_iso()}
    save_status_store(payload)
    return payload


def update_status_entries(payload: Any) -> dict[str, Any]:
    ensure_writable_storage()
    status_store = load_status_store()
    issues = build_issue_payload()["features"]
    issue_lookup = {issue["id"]: issue for issue in issues}

    if isinstance(payload, dict) and "items" in payload and isinstance(payload["items"], list):
        updates = payload["items"]
    elif isinstance(payload, list):
        updates = payload
    else:
        updates = [payload]

    for update in updates:
        if not isinstance(update, dict):
            continue
        feature_id = str(update.get("id", "")).strip()
        if feature_id not in issue_lookup:
            continue
        issue = issue_lookup[feature_id]
        item = status_store["items"].setdefault(
            feature_id,
            {
                "normalized_name": normalize_name(issue["name"]),
                "display_name": issue["name"],
                "status": DEFAULT_STATUS,
                "notes": "",
                "reported_by": "",
                "last_updated": "",
            },
        )
        next_status = str(update.get("status", item.get("status", DEFAULT_STATUS))).strip().lower()
        if next_status in STATUS_VALUES:
            item["status"] = next_status
        item["notes"] = str(update.get("notes", item.get("notes", ""))).strip()
        item["reported_by"] = str(update.get("reported_by", item.get("reported_by", ""))).strip()
        item["last_updated"] = utc_now_iso()
        item["normalized_name"] = normalize_name(issue["name"])
        item["display_name"] = issue["name"]

    save_status_store(status_store)
    return build_issue_payload()


def replace_kml_file(kml_text: str, filename: str = "") -> dict[str, Any]:
    ensure_writable_storage()
    ensure_data_files()
    if "<kml" not in kml_text.lower():
        raise ValueError("Uploaded file does not appear to be valid KML.")

    if KML_PATH.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{stamp}_{filename or KML_PATH.name}"
        shutil.copy2(KML_PATH, ARCHIVE_DIR / archive_name)

    KML_PATH.write_text(kml_text, encoding="utf-8")
    points = parse_kml_points(KML_PATH)
    sync_status_store_to_points(points)
    return build_issue_payload()


def initialize_data_store() -> None:
    ensure_data_files()
    points = parse_kml_points(KML_PATH)
    sync_status_store_to_points(points)
