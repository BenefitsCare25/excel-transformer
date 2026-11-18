"""HTTP endpoint for the combined Adj Listing report (Renewal Comparison tab)."""

import json
import logging
import os
import tempfile
import traceback
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .processor import process_adj_listing
from .reader import LIFE_PRODUCTS

logger = logging.getLogger(__name__)

adj_listing_blueprint = Blueprint('renewal_adj_listing', __name__, url_prefix='/api/renewal/adj-listing')

FILE_KEYS = ('file_1', 'file_2')
MAX_FCL = 1_000_000_000


def _bad_request(error: str, details: str):
    return jsonify({'error': error, 'details': details}), 400


def _validated_files():
    for key in FILE_KEYS:
        uploaded = request.files.get(key)
        if uploaded is None or not uploaded.filename:
            return None, _bad_request(f'Missing file: {key}', 'Upload both renewal listing files.')
        if not uploaded.filename.lower().endswith('.xlsx'):
            return None, _bad_request(f'Invalid file type for {uploaded.filename}', 'Only .xlsx files are supported.')
    return [request.files[k] for k in FILE_KEYS], None


def _parse_limits(raw: str) -> dict:
    """{'GTL': {'fcl': 800000, 'age': 71}} from the form; blanks mean 'use the listing header'."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError('Limits must be valid JSON.') from exc
    if not isinstance(data, dict):
        raise ValueError('Limits must be an object keyed by product code.')
    limits = {}
    for code, entry in data.items():
        if code not in LIFE_PRODUCTS or not isinstance(entry, dict):
            raise ValueError(f"Unknown life product '{code}' in limits.")
        cleaned = {}
        for key, low, high in (('fcl', 0, MAX_FCL), ('age', 1, 120)):
            value = entry.get(key)
            if value in (None, ''):
                continue
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{code} {key.upper()} must be a number.") from exc
            if not low <= number <= high:
                raise ValueError(f"{code} {key.upper()} must be between {low:,} and {high:,}.")
            cleaned[key] = number
        if cleaned:
            limits[code] = cleaned
    return limits


@adj_listing_blueprint.post('/generate')
def generate_adj_listing():
    files, error = _validated_files()
    if error:
        return error
    try:
        divisor = int(request.form.get('pro_rata_divisor', 2))
    except ValueError:
        return _bad_request('Invalid pro-rata divisor', 'Pro-rata divisor must be a whole number.')
    if not 1 <= divisor <= 12:
        return _bad_request('Invalid pro-rata divisor', 'Pro-rata divisor must be between 1 and 12.')
    client_label = (request.form.get('client_label') or '').strip()[:40]
    try:
        limits = _parse_limits(request.form.get('limits', ''))
        output_name = f"Renewal_Adj_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.xlsx"
        output_path = os.path.join(current_app.config['PROCESSED_FOLDER'], output_name)
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = []
            for key, uploaded in zip(FILE_KEYS, files):
                path = os.path.join(temp_dir, secure_filename(f"{key}_{uploaded.filename}") or f"{key}.xlsx")
                uploaded.save(path)
                paths.append(path)
            result = process_adj_listing(
                paths[0], paths[1], files[0].filename, files[1].filename, output_path,
                pro_rata_divisor=divisor, client_label=client_label, limits=limits,
            )
    except ValueError as exc:
        logger.warning("Adj listing validation error: %s", exc)
        return _bad_request('Validation failed', str(exc))
    except Exception as exc:  # noqa: BLE001 — surface a 500 with a logged traceback
        logger.error("Adj listing failed: %s\n%s", exc, traceback.format_exc())
        return jsonify({'error': 'Processing failed', 'details': str(exc)}), 500
    result.update(success=True, download_filename=output_name)
    return jsonify(result)
