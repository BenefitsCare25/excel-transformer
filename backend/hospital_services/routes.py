"""HTTP endpoints for local hospital bill processing."""

from io import BytesIO
import os
import re
from pathlib import PureWindowsPath

from flask import Blueprint, current_app, jsonify, request, send_file
from . import jobs

hospital_blueprint = Blueprint("hospital", __name__, url_prefix="/api/hospital")
RUN_ID = re.compile(r"^[0-9a-f]{32}$")


@hospital_blueprint.before_app_request
def resume_queue():
    jobs.start(current_app.config["HOSPITAL_OUTPUT_DIR"], current_app.logger)


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
    try:
        run_id = jobs.submit(source, current_app.config["HOSPITAL_OUTPUT_DIR"], current_app.logger)
    except ValueError as exc:
        return jsonify(error=str(exc)), 429
    return jsonify(run_id=run_id), 202


@hospital_blueprint.route("/batches/<batch_id>", methods=["GET", "POST"])
def hospital_batch(batch_id):
    from .processor import MAX_BYTES
    from .queue_store import batch

    if not RUN_ID.fullmatch(batch_id):
        return jsonify(error="Invalid batch ID."), 400
    existing = batch(batch_id, current_app.config["HOSPITAL_OUTPUT_DIR"])
    if existing is not None:
        return jsonify(existing), 200
    if request.method == "GET":
        return jsonify(error="This upload was not accepted. Select the PDFs and upload them again."), 404
    if request.content_length and request.content_length > 5 * MAX_BYTES + 1024 * 1024:
        return jsonify(error="Batch is too large. Choose up to five PDFs, each up to 25 MB."), 413
    uploaded = request.files.getlist("files")
    if not 1 <= len(uploaded) <= 5:
        return jsonify(error="Choose one to five hospital bill PDFs."), 400
    files = []
    for item in uploaded:
        filename = PureWindowsPath(item.filename or "").name
        if not filename.lower().endswith(".pdf") or len(filename) > 200:
            return jsonify(error="Each document must have a PDF filename of at most 200 characters."), 400
        source = item.read(MAX_BYTES + 1)
        if len(source) > MAX_BYTES:
            return jsonify(error=f"{filename}: PDF is too large (25 MB limit)."), 413
        if not source.startswith(b"%PDF-"):
            return jsonify(error=f"{filename}: upload a valid PDF file."), 400
        files.append((filename, source))
    try:
        result = jobs.submit_batch(batch_id, files, current_app.config["HOSPITAL_OUTPUT_DIR"], current_app.logger)
    except ValueError as exc:
        return jsonify(error=str(exc)), 429
    return jsonify(result), 202


@hospital_blueprint.get("/status/<run_id>")
def hospital_status(run_id):
    if not RUN_ID.fullmatch(run_id):
        return jsonify(error="Invalid result ID."), 400
    result = jobs.status(run_id, current_app.config["HOSPITAL_OUTPUT_DIR"])
    if result is None:
        return jsonify(error="Processing was interrupted or the result was not found."), 404
    return jsonify(result)


@hospital_blueprint.get("/redacted/<run_id>")
def download_redacted(run_id):
    if not RUN_ID.fullmatch(run_id):
        return jsonify(error="Invalid result ID."), 400
    path = os.path.join(current_app.config["HOSPITAL_OUTPUT_DIR"], f"{run_id}_redacted.pdf")
    if not os.path.isfile(path):
        return jsonify(error="Redacted PDF was not found."), 404
    return send_file(path, mimetype="application/pdf", as_attachment=True,
                     download_name="hospital_bill_redacted.pdf")


@hospital_blueprint.delete("/runs/<run_id>")
def delete_hospital_run(run_id):
    if not RUN_ID.fullmatch(run_id):
        return jsonify(error="Invalid result ID."), 400
    try:
        if not jobs.delete(run_id, current_app.config["HOSPITAL_OUTPUT_DIR"]):
            return jsonify(error="This bill is still processing. Try again when it finishes."), 409
    except OSError:
        current_app.logger.exception("Could not delete hospital run %s", run_id)
        return jsonify(error="Could not delete saved bill data. Please retry."), 500
    return "", 204


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
