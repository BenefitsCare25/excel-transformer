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


def _is_pdf(stream) -> bool:
    header = stream.read(5)
    stream.seek(0)
    return header == b"%PDF-"


@hospital_blueprint.post("/process")
def process_hospital_bill():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename or not uploaded.filename.lower().endswith(".pdf"):
        return jsonify(error="Select a PDF hospital bill."), 400
    if not _is_pdf(uploaded.stream):
        return jsonify(error="Upload a valid PDF file."), 400
    run_id = jobs.submit(uploaded.stream, current_app.config["HOSPITAL_OUTPUT_DIR"], current_app.logger)
    return jsonify(run_id=run_id), 202


@hospital_blueprint.route("/batches/<batch_id>", methods=["GET", "POST"])
def hospital_batch(batch_id):
    from .queue_store import batch

    if not RUN_ID.fullmatch(batch_id):
        return jsonify(error="Invalid batch ID."), 400
    existing = batch(batch_id, current_app.config["HOSPITAL_OUTPUT_DIR"])
    if existing is not None:
        return jsonify(existing), 200
    if request.method == "GET":
        return jsonify(error="This upload was not accepted. Select the PDFs and upload them again."), 404
    uploaded = request.files.getlist("files")
    if not uploaded:
        return jsonify(error="Choose at least one hospital bill PDF."), 400
    files = []
    for item in uploaded:
        filename = PureWindowsPath(item.filename or "").name
        if not filename.lower().endswith(".pdf") or len(filename) > 200:
            return jsonify(error="Each document must have a PDF filename of at most 200 characters."), 400
        if not _is_pdf(item.stream):
            return jsonify(error=f"{filename}: upload a valid PDF file."), 400
        files.append((filename, item.stream))
    result = jobs.submit_batch(batch_id, files, current_app.config["HOSPITAL_OUTPUT_DIR"], current_app.logger)
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
