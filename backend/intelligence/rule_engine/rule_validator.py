"""
Validates rule JSON dicts against the schema before executing or storing.
"""
from typing import Dict, List, Tuple

from .rule_schema import (
    VALID_RULE_TYPES, VALID_OPERATORS, VALID_FORMULA_ACTIONS, VALID_MATCH_METHODS
)


def validate_rule(rule: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a single rule dict. Returns (is_valid, list_of_errors).
    """
    errors = []

    if 'rule_type' not in rule:
        errors.append("Missing 'rule_type'")
        return False, errors

    rt = rule['rule_type']
    if rt not in VALID_RULE_TYPES:
        errors.append(f"Unknown rule_type '{rt}'. Valid: {VALID_RULE_TYPES}")
        return False, errors

    config = rule.get('config', {})

    if rt == 'PRESENCE_RULE':
        for key in ['only_in_file_b', 'only_in_file_a']:
            if key in config:
                entry = config[key]
                if 'outcome_label' not in entry:
                    errors.append(f"PRESENCE_RULE.{key} missing 'outcome_label'")

    elif rt == 'CHANGE_RULE':
        if 'fields' not in config or not isinstance(config['fields'], list):
            errors.append("CHANGE_RULE.config must have 'fields' (list)")

    elif rt == 'CONDITION_RULE':
        if 'conditions' not in config:
            errors.append("CONDITION_RULE.config must have 'conditions'")
        else:
            for i, cond in enumerate(config['conditions']):
                if 'field' not in cond:
                    errors.append(f"CONDITION_RULE.conditions[{i}] missing 'field'")
                op = cond.get('operator')
                if op not in VALID_OPERATORS:
                    errors.append(f"CONDITION_RULE.conditions[{i}] invalid operator '{op}'")
        if 'outcome_label' not in config:
            errors.append("CONDITION_RULE.config missing 'outcome_label'")
        join = config.get('condition_join', 'AND')
        if join not in ('AND', 'OR'):
            errors.append(f"CONDITION_RULE.condition_join must be 'AND' or 'OR', got '{join}'")

    elif rt == 'ROW_MATCH':
        method = config.get('method', 'exact')
        if method not in VALID_MATCH_METHODS:
            errors.append(f"ROW_MATCH.method must be one of {VALID_MATCH_METHODS}")
        threshold = config.get('fuzzy_threshold', 0.8)
        if not (0.0 <= float(threshold) <= 1.0):
            errors.append("ROW_MATCH.fuzzy_threshold must be between 0.0 and 1.0")

    elif rt == 'FORMULA_RULE':
        actions = config.get('column_actions', {})
        for col, action in actions.items():
            if action not in VALID_FORMULA_ACTIONS:
                errors.append(f"FORMULA_RULE.column_actions['{col}'] invalid action '{action}'")

    return len(errors) == 0, errors


def validate_template(template: Dict) -> Tuple[bool, List[str]]:
    """
    Validate an entire comparison template dict.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    required_keys = ['template_name', 'sheet_config', 'column_mapping', 'rules']
    for k in required_keys:
        if k not in template:
            errors.append(f"Missing required key: '{k}'")

    if errors:
        return False, errors

    sc = template.get('sheet_config', {})
    if 'file_a_sheet' not in sc:
        errors.append("sheet_config missing 'file_a_sheet'")

    cm = template.get('column_mapping', {})
    if 'unique_key' not in cm or not cm['unique_key']:
        errors.append("column_mapping must have non-empty 'unique_key'")

    for i, rule in enumerate(template.get('rules', [])):
        rule_valid, rule_errors = validate_rule(rule)
        if not rule_valid:
            for err in rule_errors:
                errors.append(f"rules[{i}]: {err}")

    return len(errors) == 0, errors
