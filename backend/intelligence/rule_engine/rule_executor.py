"""
Orchestrates rule execution against two DataFrames to produce a comparison result.
"""
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

from .rule_schema import ComparisonTemplate
from .row_matcher import exact_match, fuzzy_match
from .change_detector import (
    fields_changed, evaluate_conditions, resolve_outcome_label, _is_empty
)


def dataframe_to_rows(df: pd.DataFrame) -> List[Dict]:
    """Convert DataFrame to list of dicts with string column names."""
    return df.where(pd.notnull(df), None).to_dict(orient='records')


def execute_template(template: ComparisonTemplate,
                     df_a: pd.DataFrame,
                     df_b: pd.DataFrame) -> Dict[str, Any]:
    """
    Run all rules from `template` against df_a (old) and df_b (new).

    Returns a result dict:
    {
        'rows': [{...row data, 'remarks': '...', 'color': '#xxxxxx', 'changed_fields': [...]}],
        'summary': {'total': int, 'additions': int, 'deletions': int, 'changes': int, 'unchanged': int},
    }
    """
    rows_a = dataframe_to_rows(df_a)
    rows_b = dataframe_to_rows(df_b)

    key_fields = template.column_mapping.unique_key
    compare_fields = template.column_mapping.compare_fields
    display_fields = template.column_mapping.display_fields

    # Determine match method from ROW_MATCH rule if present
    match_method = 'exact'
    fuzzy_threshold = 0.8
    for rule in template.rules:
        if rule.rule_type == 'ROW_MATCH':
            match_method = rule.config.get('method', 'exact')
            fuzzy_threshold = float(rule.config.get('fuzzy_threshold', 0.8))
            break

    # Match rows
    if match_method == 'fuzzy':
        matched_pairs, only_a, only_b = fuzzy_match(rows_a, rows_b, key_fields, fuzzy_threshold)
    else:
        matched_pairs, only_a, only_b = exact_match(rows_a, rows_b, key_fields)

    # Pull PRESENCE_RULE config
    presence_cfg = {}
    for rule in template.rules:
        if rule.rule_type == 'PRESENCE_RULE':
            presence_cfg = rule.config
            break

    # Pull CHANGE_RULE configs
    change_rules = [r for r in template.rules if r.rule_type == 'CHANGE_RULE']

    # Pull CONDITION_RULEs
    condition_rules = [r for r in template.rules if r.rule_type == 'CONDITION_RULE']

    result_rows = []

    # --- Process rows only in B (additions) ---
    only_in_b_cfg = presence_cfg.get('only_in_file_b', {'outcome_label': 'Addition', 'color': '#C6EFCE'})
    for j in only_b:
        row_b = rows_b[j]
        remarks = only_in_b_cfg.get('outcome_label', 'Addition')
        color = only_in_b_cfg.get('color', '#C6EFCE')

        # Check condition rules on additions
        cond_label, cond_color = _apply_condition_rules(None, row_b, condition_rules)
        if cond_label:
            remarks = cond_label
            color = cond_color

        result_rows.append({
            **_build_output_row(row_b, key_fields, compare_fields, display_fields),
            'source': 'B',
            'remarks': remarks,
            'color': color,
            'changed_fields': [],
        })

    # --- Process rows only in A (deletions) ---
    only_in_a_cfg = presence_cfg.get('only_in_file_a', {'outcome_label': 'Deletion', 'color': '#FFC7CE'})
    for i in only_a:
        row_a = rows_a[i]
        remarks = only_in_a_cfg.get('outcome_label', 'Deletion')
        color = only_in_a_cfg.get('color', '#FFC7CE')

        cond_label, cond_color = _apply_condition_rules(row_a, None, condition_rules)
        if cond_label:
            remarks = cond_label
            color = cond_color

        result_rows.append({
            **_build_output_row(row_a, key_fields, compare_fields, display_fields),
            'source': 'A',
            'remarks': resolve_outcome_label(remarks, row_a),
            'color': color,
            'changed_fields': [],
        })

    # --- Process matched pairs ---
    for i, j in matched_pairs:
        row_a = rows_a[i]
        row_b = rows_b[j]

        # Check condition rules first (higher priority)
        cond_label, cond_color = _apply_condition_rules(row_a, row_b, condition_rules)
        if cond_label:
            result_rows.append({
                **_build_output_row(row_b, key_fields, compare_fields, display_fields),
                'source': 'matched',
                'remarks': resolve_outcome_label(cond_label, row_b),
                'color': cond_color,
                'changed_fields': fields_changed(row_a, row_b, compare_fields),
            })
            continue

        # Check CHANGE_RULEs
        for change_rule in change_rules:
            cfg = change_rule.config
            check_fields = cfg.get('fields', compare_fields)
            changed = fields_changed(row_a, row_b, check_fields)
            if changed:
                result_rows.append({
                    **_build_output_row(row_b, key_fields, compare_fields, display_fields),
                    'source': 'matched',
                    'remarks': cfg.get('outcome_label', 'Changed'),
                    'color': cfg.get('color', '#FFEB9C'),
                    'changed_fields': changed,
                })
                break
        else:
            # Check general field changes
            changed = fields_changed(row_a, row_b, compare_fields)
            if changed:
                result_rows.append({
                    **_build_output_row(row_b, key_fields, compare_fields, display_fields),
                    'source': 'matched',
                    'remarks': 'Changed',
                    'color': '#FFEB9C',
                    'changed_fields': changed,
                })
            else:
                result_rows.append({
                    **_build_output_row(row_b, key_fields, compare_fields, display_fields),
                    'source': 'matched',
                    'remarks': '',
                    'color': None,
                    'changed_fields': [],
                })

    summary = _build_summary(result_rows)
    return {'rows': result_rows, 'summary': summary}


def _apply_condition_rules(row_a, row_b, condition_rules):
    """Apply condition rules and return (label, color) or (None, None)."""
    for rule in condition_rules:
        cfg = rule.config
        conditions = cfg.get('conditions', [])
        join = cfg.get('condition_join', 'AND')
        if evaluate_conditions(row_a, row_b, conditions, join):
            label = cfg.get('outcome_label', 'Flagged')
            color = cfg.get('color', '#FFC7CE')
            return label, color
    return None, None


def _build_output_row(row: Dict, key_fields: List[str],
                      compare_fields: List[str], display_fields: List[str]) -> Dict:
    """Build output row with all relevant fields."""
    output = {}
    all_fields = list(dict.fromkeys(key_fields + display_fields + compare_fields))
    for f in all_fields:
        output[f] = row.get(f)
    return output


def _build_summary(result_rows: List[Dict]) -> Dict:
    additions = sum(1 for r in result_rows if r.get('source') == 'B')
    deletions = sum(1 for r in result_rows if r.get('source') == 'A')
    changes = sum(1 for r in result_rows if r.get('source') == 'matched' and r.get('changed_fields'))
    unchanged = sum(1 for r in result_rows if r.get('source') == 'matched' and not r.get('changed_fields'))
    return {
        'total': len(result_rows),
        'additions': additions,
        'deletions': deletions,
        'changes': changes,
        'unchanged': unchanged,
    }
