"""HTTP endpoints for local hospital bill processing."""

from io import BytesIO
import os
import re

from flask import Blueprint, current_app, jsonify, request, send_file
from . import jobs

hospital_blueprint = Blueprint("hospital", __name__, url_prefix="/api/hospital")
RUN_ID = re.compile(r"^[0-9a-f]{32}$")


@hospital_blueprint.after_request
def prevent_cache(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@hospital_blueprint.post("/process")
def process_hospital_bill():
    from .processor import MAX_BYTES

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename or not uploaded.filename.lower().endswith(".pdf"):
        return jsonify(error="Select a PDF hospital bill."), 400
    if request.content_length and request.content_length > MAX_BYTES + 1024 * 1024:
        return jsonify(error="PDF is too large (25 MB limit)."), 413
    source = uploaded.read(MAX_BYTES + 1)
    if len(source) > MAX_BYTES:
        return jsonify(error="PDF is too large (25 MB limit)."), 413
    if not source.startswith(b"%PDF-"):
        return jsonify(error="Upload a valid PDF file."), 400
    run_id = jobs.submit(source, current_app.config["HOSPITAL_OUTPUT_DIR"],
                         current_app.logger)
    if run_id is None:
        return jsonify(error="Another hospital bill is processing. Try again shortly."), 429
    return jsonify(run_id=run_id), 202


@hospital_blueprint.get("/status/<run_id>")
def hospital_status(run_id):
    if not RUN_ID.fullmatch(run_id):
        return jsonify(error="Invalid result ID."), 400
    result = jobs.status(run_id)
    if result is None:
        return jsonify(error="Processing was interrupted or the result expired. Please retry."), 404
    result.pop("finished_at", None)
    return jsonify(result)


@hospital_blueprint.get("/redacted/<run_id>")
def download_redacted(run_id):
    if not RUN_ID.fullmatch(run_id):
        return jsonify(error="Invalid result ID."), 400
    path = os.path.join(current_app.config["HOSPITAL_OUTPUT_DIR"], f"{run_id}_redacted.pdf")
    if not os.path.isfile(path):
        return jsonify(error="Redacted PDF expired or was not found."), 404
    return send_file(path, mimetype="application/pdf", as_attachment=True,
                     download_name="hospital_bill_redacted.pdf")


@hospital_blueprint.post("/export")
def export_hospital_workbook():
    from .processor import make_workbook

    payload = request.get_json(silent=True) or {}
    try:
        output = make_workbook(payload.get("rows"))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return send_file(BytesIO(output), mimetype=(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ), as_attachment=True, download_name="hospital_bills.xlsx")
