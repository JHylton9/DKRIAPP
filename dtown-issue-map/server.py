from __future__ import annotations

import argparse

from app import app
from issue_map_backend import build_issue_payload, initialize_data_store


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Downtown Kingston issue map server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--check", action="store_true", help="Validate the KML and status files without starting the server.")
    args = parser.parse_args()

    initialize_data_store()

    if args.check:
        payload = build_issue_payload()
        print(f"points: {len(payload['features'])}")
        print(f"kml: {payload['kml_file']}")
        print(f"counts: {payload['counts']}")
        return 0

    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
