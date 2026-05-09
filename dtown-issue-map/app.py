from __future__ import annotations

from http import HTTPStatus

from flask import Flask, jsonify, request, send_from_directory

from issue_map_backend import (
    PUBLIC_DIR,
    build_issue_payload,
    initialize_data_store,
    load_status_store,
    replace_kml_file,
    update_status_entries,
)


app = Flask(__name__, static_folder=str(PUBLIC_DIR / "static"), static_url_path="/static")
initialize_data_store()


@app.after_request
def add_cors_headers(response):
    if request.path.startswith("/api/"):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.route("/", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/admin", methods=["GET"])
@app.route("/admin/", methods=["GET"])
@app.route("/admin.html", methods=["GET"])
def admin():
    return send_from_directory(PUBLIC_DIR, "admin.html")


@app.route("/api/issues", methods=["GET", "OPTIONS"])
def api_issues():
    if request.method == "OPTIONS":
        return ("", HTTPStatus.NO_CONTENT)
    return jsonify(build_issue_payload())


@app.route("/api/statuses", methods=["GET", "POST", "OPTIONS"])
def api_statuses():
    if request.method == "OPTIONS":
        return ("", HTTPStatus.NO_CONTENT)
    if request.method == "GET":
        return jsonify(load_status_store())
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Expected JSON request body."}), HTTPStatus.BAD_REQUEST
    try:
        return jsonify(update_status_entries(payload))
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE


@app.route("/api/kml", methods=["POST", "OPTIONS"])
def api_kml():
    if request.method == "OPTIONS":
        return ("", HTTPStatus.NO_CONTENT)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Expected JSON request body."}), HTTPStatus.BAD_REQUEST
    kml_text = str(payload.get("kml_text", ""))
    filename = str(payload.get("filename", "")).strip()
    try:
        response = replace_kml_file(kml_text, filename=filename)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
