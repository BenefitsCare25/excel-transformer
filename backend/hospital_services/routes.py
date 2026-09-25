"""HTTP endpoints for local hospital bill processing."""

from io import BytesIO
import os
import re
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, send_file

from .processor import MAX_BYTES, make_workbook, process_pdf


hospital_blueprint = Blueprint("hospital", __name__, url_prefix="/api/hospital")
RUN_ID = re.compile(r"^[0-9a-f]{32}$")


@hospital_blueprint.after_request
def prevent_cache(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@hospital_blueprint.post("/process")
def process_hospital_bill():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename or not uploaded.filename.lower().endswith(".pdf"):
        return jsonify(error="Select a PDF hospital bill."), 400
    if request.content_length and request.content_length > MAX_BYTES + 1024 * 1024:
        return jsonify(error="PDF is too large (25 MB limit)."), 413
    source = uploaded.read(MAX_BYTES + 1)
    try:
        pdf_bytes, rows, redactions, warnings = process_pdf(source)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:
        current_app.logger.exception("Hospital bill processing failed")
        return jsonify(error="Could not process the hospital bill."), 500

    run_id = uuid4().hex
    path = os.path.join(current_app.config["HOSPITAL_OUTPUT_DIR"], f"{run_id}_redacted.pdf")
    with open(path, "wb") as output:
        output.write(pdf_bytes)
    return jsonify(run_id=run_id, rows=rows, redactions=redactions,
                   warnings=warnings, retention_minutes=15)


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
    payload = request.get_json(silent=True) or {}
    try:
        output = make_workbook(payload.get("rows"))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return send_file(BytesIO(output), mimetype=(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ), as_attachment=True, download_name="hospital_bills.xlsx")
