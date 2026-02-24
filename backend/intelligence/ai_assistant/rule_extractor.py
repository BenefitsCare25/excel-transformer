"""
Parses AI text response → validated rule JSON dict.
Security boundary: AI output is always validated before entering wizard state.
"""
import json
import re
from typing import Dict, Optional, Tuple

from ..rule_engine.rule_validator import validate_rule


def extract_json_from_response(text: str) -> Optional[str]:
    """Extract JSON object from AI response text."""
    # Try direct parse first
    text = text.strip()
    if text.startswith('{'):
        return text

    # Look for ```json blocks
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)

    # Look for any JSON object in the text
    match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', text, re.DOTALL)
    if match:
        return match.group(1)

    return None


def parse_rule_from_ai(ai_response: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Parse and validate a rule dict from AI response text.

    Returns:
        (rule_dict, None) on success
        (None, error_message) on failure
    """
    json_str = extract_json_from_response(ai_response)
    if not json_str:
        return None, "No valid JSON found in AI response. Please rephrase your rule description."

    try:
        rule = json.loads(json_str)
    except json.JSONDecodeError as e:
        return None, f"AI response was not valid JSON: {e}"

    if not isinstance(rule, dict):
        return None, "AI response must be a JSON object with 'rule_type' and 'config' keys."

    is_valid, errors = validate_rule(rule)
    if not is_valid:
        return None, f"AI generated an invalid rule: {'; '.join(errors)}"

    return rule, None


def parse_template_slug(ai_response: str) -> str:
    """Extract template suggestion slug from AI response."""
    valid_slugs = {'mediacorp_el', 'gp_panel', 'renewal_comparison', 'clinic_matcher', 'none'}
    response = ai_response.strip().lower()
    for slug in valid_slugs:
        if slug in response:
            return slug
    return 'none'
