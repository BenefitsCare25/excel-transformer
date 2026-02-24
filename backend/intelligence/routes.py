"""
Flask Blueprint for the Intelligence Platform.
Registers all /api/intel/* endpoints.
"""
import io
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from flask import Blueprint, jsonify, request, send_file

from .excel_analyzer import (
    read_sheet_dual_pass, extract_values_grid, get_formula_cells,
    analyze_columns, classify_column_formulas,
    detect_header_row, extract_header_names,
)
from .rule_engine import (
    ComparisonTemplate, validate_template, execute_template,
)
from .output_builder import build_comparison_report
from .ai_assistant import (
    AIProviderFactory,
    build_nl_to_rule_prompt, build_template_suggest_prompt, build_chat_prompt,
    SYSTEM_PROMPT_NL_TO_RULE, SYSTEM_PROMPT_TEMPLATE_SUGGEST, SYSTEM_PROMPT_CHAT,
    parse_rule_from_ai, parse_template_slug,
)

logger = logging.getLogger(__name__)

intel_bp = Blueprint('intel', __name__, url_prefix='/api/intel')

# ── In-memory session store ────────────────────────────────────────────────────
_sessions: Dict[str, Dict] = {}
_sessions_lock = threading.Lock()
SESSION_TTL_SECONDS = 3600  # 1 hour


def _cleanup_sessions():
    """Background thread: remove expired sessions."""
    while True:
        time.sleep(300)
        now = time.time()
        with _sessions_lock:
            expired = [sid for sid, s in _sessions.items()
                       if now - s.get('created_at', 0) > SESSION_TTL_SECONDS]
            for sid in expired:
                _sessions.pop(sid, None)
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired intel sessions")


threading.Thread(target=_cleanup_sessions, daemon=True).start()


def _get_session(session_id: str) -> Optional[Dict]:
    with _sessions_lock:
        return _sessions.get(session_id)


def _set_session(session_id: str, data: Dict):
    with _sessions_lock:
        _sessions[session_id] = {**data, 'created_at': time.time()}


# ── Template registry ─────────────────────────────────────────────────────────
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'built_in_templates')
_user_templates: Dict[str, Dict] = {}  # session-scoped user templates


def _load_builtin_templates() -> Dict[str, Dict]:
    templates = {}
    if not os.path.isdir(_TEMPLATES_DIR):
        return templates
    for fname in os.listdir(_TEMPLATES_DIR):
        if fname.endswith('.json'):
            path = os.path.join(_TEMPLATES_DIR, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    slug = data.get('slug', fname.replace('.json', ''))
                    templates[slug] = data
            except Exception as e:
                logger.error(f"Failed to load template {fname}: {e}")
    return templates


_builtin_templates = _load_builtin_templates()


# ── Helper: AI provider from request headers ──────────────────────────────────
def _get_ai_provider_from_request():
    """Extract AI provider from request headers. Falls back to platform key."""
    provider_name = request.headers.get('X-AI-Provider', 'anthropic').lower()
    api_key = request.headers.get('X-AI-Key', '')
    model = request.headers.get('X-AI-Model', '')

    # Fall back to platform key if no BYOK
    if not api_key:
        platform_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not platform_key:
            return None, "No AI API key provided. Please configure an API key in AI Settings."
        api_key = platform_key
        provider_name = 'anthropic'
        model = model or 'claude-haiku-4-5-20251001'

    try:
        provider = AIProviderFactory.get_provider(provider_name, api_key, model or None)
        return provider, None
    except Exception as e:
        return None, str(e)


# ── File analysis ─────────────────────────────────────────────────────────────
def _analyze_file(filepath: str) -> Dict:
    """Run dual-pass analysis on a single Excel file."""
    sheets_data = read_sheet_dual_pass(filepath)
    result = {'sheets': []}

    for sheet_name, raw_data in sheets_data.items():
        values_grid = extract_values_grid(raw_data)
        formula_cells = get_formula_cells(raw_data)

        if not values_grid:
            continue

        header_row = detect_header_row(values_grid)
        headers = extract_header_names(values_grid, header_row)

        # Build per-column formula grids
        formula_grid = []
        for row in raw_data['rows']:
            formula_grid.append([cell['formula'] for cell in row])

        columns = analyze_columns(values_grid, formula_grid, header_row)

        # Classify formula types per column
        for col_info in columns:
            if col_info.get('formula_info') and col_info['formula_count'] > 0:
                col_idx = col_info['index']
                col_formulas = [
                    formula_grid[r][col_idx] if col_idx < len(formula_grid[r]) else None
                    for r in range(header_row + 1, len(formula_grid))
                ]
                formula_type = classify_column_formulas([f for f in col_formulas if f])
                if col_info['formula_info']:
                    col_info['formula_info']['formula_type'] = formula_type

        # Suggest template based on column names
        suggested_template = _suggest_template_heuristic(headers, sheet_name)

        result['sheets'].append({
            'name': sheet_name,
            'header_row': header_row,
            'row_count': len(values_grid) - header_row - 1,
            'columns': columns,
            'merged_cells': raw_data.get('merged_cells', []),
            'suggested_template': suggested_template,
            'formula_summary': {
                'total_formula_cells': len(formula_cells),
                'formula_columns': [c['name'] for c in columns if c.get('detected_type') == 'formula'],
            },
        })

    return result


def _suggest_template_heuristic(headers: list, sheet_name: str) -> Optional[str]:
    """Simple keyword-based template suggestion (no AI needed)."""
    headers_lower = ' '.join(h.lower() for h in headers if h)
    sheet_lower = sheet_name.lower()

    if any(kw in headers_lower for kw in ['staff id', 'nric', 'fin', 'entity']) or 'employee' in sheet_lower:
        return 'mediacorp_el'
    if any(kw in headers_lower for kw in ['provider code', 'clinic name', 'operating hours']) or 'gp' in sheet_lower:
        return 'gp_panel'
    if any(kw in headers_lower for kw in ['premium', 'sum insured', 'renewal']):
        return 'renewal_comparison'
    if any(kw in headers_lower for kw in ['panel', 'postal code']) and 'clinic' in headers_lower:
        return 'clinic_matcher'
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@intel_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Upload 1-2 Excel files and return column analysis.
    Returns ColumnAnalysis JSON with session_id.
    """
    if not request.files:
        return jsonify({'error': 'No files uploaded'}), 400

    session_id = str(uuid.uuid4())
    file_results = {}
    temp_paths = {}

    for key in ['file_a', 'file_b']:
        f = request.files.get(key)
        if not f:
            continue
        if not f.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': f'{key}: Only .xlsx and .xls files supported'}), 400

        # Save to temp
        import tempfile
        suffix = '.xlsx' if f.filename.lower().endswith('.xlsx') else '.xls'
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        f.save(tmp.name)
        tmp.close()
        temp_paths[key] = tmp.name

        try:
            file_results[key] = _analyze_file(tmp.name)
        except Exception as e:
            logger.error(f"Analysis failed for {key}: {e}")
            return jsonify({'error': f'Failed to analyze {key}: {str(e)}'}), 500

    if not file_results:
        return jsonify({'error': 'No valid files provided'}), 400

    # Store in session
    _set_session(session_id, {
        'file_analysis': file_results,
        'temp_paths': temp_paths,
        'template': None,
        'result': None,
    })

    response = {'session_id': session_id, **file_results}
    return jsonify(response)


@intel_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Check session status and recover wizard state."""
    session = _get_session(session_id)
    if not session:
        return jsonify({'error': 'Session expired or not found'}), 404
    return jsonify({
        'session_id': session_id,
        'has_analysis': 'file_analysis' in session,
        'has_template': session.get('template') is not None,
        'has_result': session.get('result') is not None,
    })


@intel_bp.route('/process', methods=['POST'])
def process():
    """
    Run the rule engine against uploaded files using the provided template config.

    Body: { session_id, template: {...}, dry_run: false }
    Returns: download_url or inline preview rows.
    """
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Request body required (JSON)'}), 400

    session_id = body.get('session_id')
    template_dict = body.get('template')
    dry_run = body.get('dry_run', False)

    if not session_id or not template_dict:
        return jsonify({'error': 'session_id and template are required'}), 400

    session = _get_session(session_id)
    if not session:
        return jsonify({'error': 'Session expired. Please re-upload files.'}), 404

    # Validate template
    is_valid, errors = validate_template(template_dict)
    if not is_valid:
        return jsonify({'error': 'Invalid template', 'details': errors}), 400

    template = ComparisonTemplate.from_dict(template_dict)

    temp_paths = session.get('temp_paths', {})
    path_a = temp_paths.get('file_a')
    path_b = temp_paths.get('file_b', path_a)

    if not path_a:
        return jsonify({'error': 'No files available in session. Please re-upload.'}), 400

    try:
        sc = template.sheet_config
        df_a = pd.read_excel(path_a, sheet_name=sc.file_a_sheet, header=sc.header_row)
        df_b = pd.read_excel(path_b, sheet_name=sc.file_b_sheet or sc.file_a_sheet, header=sc.header_row)

        result = execute_template(template, df_a, df_b)
    except Exception as e:
        logger.error(f"Process failed: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

    if dry_run:
        # Return first 20 rows for preview
        preview = result['rows'][:20]
        return jsonify({'preview': preview, 'summary': result['summary']})

    # Build Excel report
    try:
        report_bytes = build_comparison_report(
            result=result,
            template_name=template.template_name,
            compare_fields=template.column_mapping.compare_fields,
            key_fields=template.column_mapping.unique_key,
            display_fields=template.column_mapping.display_fields,
            add_remarks=template.output_config.add_remarks_column,
            include_summary=template.output_config.include_summary_sheet,
            highlight_changed_cells=template.output_config.highlight_changed_cells,
        )
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return jsonify({'error': f'Report generation failed: {str(e)}'}), 500

    # Store result in session for download
    result_id = str(uuid.uuid4())
    session['result'] = {'id': result_id, 'bytes': report_bytes, 'summary': result['summary']}
    _set_session(session_id, session)

    date_str = datetime.now().strftime('%Y%m%d')
    filename_template = template.output_config.output_filename_template
    filename = filename_template.replace('{date}', date_str) + '.xlsx'

    return jsonify({
        'download_id': result_id,
        'download_url': f'/api/intel/download/{session_id}/{result_id}',
        'filename': filename,
        'summary': result['summary'],
    })


@intel_bp.route('/download/<session_id>/<result_id>', methods=['GET'])
def download(session_id, result_id):
    """Download the processed comparison Excel file."""
    session = _get_session(session_id)
    if not session:
        return jsonify({'error': 'Session expired'}), 404

    result_data = session.get('result', {})
    if not result_data or result_data.get('id') != result_id:
        return jsonify({'error': 'Result not found'}), 404

    report_bytes = result_data['bytes']
    date_str = datetime.now().strftime('%Y%m%d')
    filename = f'comparison_{date_str}.xlsx'

    return send_file(
        io.BytesIO(report_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


@intel_bp.route('/templates', methods=['GET'])
def list_templates():
    """List all available built-in and user templates."""
    templates = []
    for slug, tmpl in _builtin_templates.items():
        templates.append({
            'slug': slug,
            'name': tmpl.get('template_name', slug),
            'description': tmpl.get('description', ''),
            'is_builtin': True,
        })
    return jsonify({'templates': templates})


@intel_bp.route('/templates/<slug>', methods=['GET'])
def get_template(slug):
    """Get a specific template by slug."""
    if slug in _builtin_templates:
        return jsonify(_builtin_templates[slug])
    if slug in _user_templates:
        return jsonify(_user_templates[slug])
    return jsonify({'error': f"Template '{slug}' not found"}), 404


@intel_bp.route('/templates', methods=['POST'])
def save_template():
    """Save a user-defined template (session-scoped)."""
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Request body required'}), 400

    is_valid, errors = validate_template(body)
    if not is_valid:
        return jsonify({'error': 'Invalid template', 'details': errors}), 400

    slug = body.get('slug') or body.get('template_name', '').lower().replace(' ', '_')
    _user_templates[slug] = body
    return jsonify({'slug': slug, 'message': 'Template saved'})


# ── AI Endpoints ──────────────────────────────────────────────────────────────

@intel_bp.route('/ai/suggest', methods=['POST'])
def ai_suggest():
    """Suggest a template from column analysis (uses AI or heuristic fallback)."""
    body = request.get_json() or {}
    columns = body.get('columns', [])
    sheet_name = body.get('sheet_name', '')

    # Try heuristic first (fast, no token cost)
    heuristic_slug = _suggest_template_heuristic(columns, sheet_name)

    provider, err = _get_ai_provider_from_request()
    if err or not provider:
        # Return heuristic result without AI
        return jsonify({'suggested_template': heuristic_slug, 'confidence': 'heuristic'})

    try:
        user_prompt = build_template_suggest_prompt(columns, sheet_name)
        ai_response = provider.complete(SYSTEM_PROMPT_TEMPLATE_SUGGEST, user_prompt, max_tokens=20)
        ai_slug = parse_template_slug(ai_response)
        slug = ai_slug if ai_slug != 'none' else heuristic_slug
    except Exception as e:
        logger.warning(f"AI template suggestion failed: {e}, using heuristic")
        slug = heuristic_slug

    return jsonify({'suggested_template': slug, 'confidence': 'ai' if provider else 'heuristic'})


@intel_bp.route('/ai/nl-to-rule', methods=['POST'])
def nl_to_rule():
    """Convert natural language description to a validated rule JSON card."""
    body = request.get_json() or {}
    description = body.get('description', '').strip()
    columns = body.get('columns', [])

    if not description:
        return jsonify({'error': 'description is required'}), 400

    provider, err = _get_ai_provider_from_request()
    if err or not provider:
        return jsonify({'error': err or 'AI provider not configured'}), 503

    try:
        user_prompt = build_nl_to_rule_prompt(description, columns)
        ai_response = provider.complete(SYSTEM_PROMPT_NL_TO_RULE, user_prompt, max_tokens=512)
        rule, parse_err = parse_rule_from_ai(ai_response)
        if parse_err:
            return jsonify({'error': parse_err}), 422
        return jsonify({'rule': rule})
    except Exception as e:
        logger.error(f"NL-to-rule failed: {e}")
        return jsonify({'error': f'AI request failed: {str(e)}'}), 500


@intel_bp.route('/ai/chat', methods=['POST'])
def ai_chat():
    """Context-aware AI chat for wizard assistance."""
    body = request.get_json() or {}
    message = body.get('message', '').strip()
    context = body.get('context')

    if not message:
        return jsonify({'error': 'message is required'}), 400

    provider, err = _get_ai_provider_from_request()
    if err or not provider:
        return jsonify({'error': err or 'AI provider not configured'}), 503

    try:
        user_prompt = build_chat_prompt(message, context)
        response = provider.complete(SYSTEM_PROMPT_CHAT, user_prompt, max_tokens=1024)
        return jsonify({'response': response})
    except Exception as e:
        logger.error(f"AI chat failed: {e}")
        return jsonify({'error': f'AI request failed: {str(e)}'}), 500


@intel_bp.route('/ai/test', methods=['POST'])
def ai_test():
    """Test an AI provider key without storing it."""
    provider, err = _get_ai_provider_from_request()
    if err or not provider:
        return jsonify({'success': False, 'error': err or 'No provider configured'}), 400

    try:
        ok = provider.test_connection()
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@intel_bp.route('/providers', methods=['GET'])
def list_providers():
    """Return available AI providers and their models."""
    return jsonify(AIProviderFactory.list_providers())
