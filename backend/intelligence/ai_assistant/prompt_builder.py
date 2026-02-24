"""
Builds context-aware prompts for different wizard steps.
"""
import json
from typing import Dict, List, Optional


RULE_SCHEMA_SUMMARY = """
Valid rule types and their config structure:

PRESENCE_RULE:
  config: {
    "only_in_file_b": {"outcome_label": "Addition", "color": "#C6EFCE"},
    "only_in_file_a": {"outcome_label": "Deletion", "color": "#FFC7CE"}
  }

CHANGE_RULE:
  config: {"fields": ["Field1", "Field2"], "outcome_label": "Changed", "color": "#FFEB9C"}

CONDITION_RULE:
  config: {
    "conditions": [{"field": "FieldName", "operator": "OPERATOR", "value": "optional_value"}],
    "condition_join": "AND",
    "outcome_label": "Label {FieldName}",
    "color": "#FFC7CE"
  }
  Valid operators: is_empty, is_not_empty, equals, not_equals, contains, starts_with,
                  changed_from_empty, changed_to_empty, date_is_before, date_is_after,
                  changed_from_pattern, changed_to_pattern

ROW_MATCH:
  config: {"method": "exact", "fuzzy_threshold": 0.8}
  method: "exact" | "fuzzy"

FORMULA_RULE:
  config: {"column_actions": {"ColName": "compare_value|compare_expression|skip"}}
"""

SYSTEM_PROMPT_NL_TO_RULE = f"""You are an Excel comparison rule converter.
Your ONLY job is to convert natural language descriptions into valid rule JSON.

{RULE_SCHEMA_SUMMARY}

CRITICAL RULES:
- Output ONLY a valid JSON object with keys "rule_type" and "config"
- Never output Python code, explanations, or markdown
- Never hallucinate field names - use ONLY the column names provided
- If you cannot determine a specific field, use a placeholder like "FieldName"
- Output must be parseable by json.loads()

Examples:
User: "mark as addition if only in new file"
Output: {{"rule_type": "PRESENCE_RULE", "config": {{"only_in_file_b": {{"outcome_label": "Addition", "color": "#C6EFCE"}}, "only_in_file_a": {{"outcome_label": "Deletion", "color": "#FFC7CE"}}}}}}

User: "flag as terminated if last day of service is filled and category is empty"
Output: {{"rule_type": "CONDITION_RULE", "config": {{"conditions": [{{"field": "Last Day of Service", "operator": "is_not_empty"}}, {{"field": "Category", "operator": "is_empty"}}], "condition_join": "AND", "outcome_label": "Deletion wef {{Last Day of Service}}", "color": "#FFC7CE"}}}}

User: "compare employee name and department fields"
Output: {{"rule_type": "CHANGE_RULE", "config": {{"fields": ["Employee Name", "Department"], "outcome_label": "Changed", "color": "#FFEB9C"}}}}
"""

SYSTEM_PROMPT_TEMPLATE_SUGGEST = """You are an Excel analysis assistant.
Given a list of column names from an Excel file, suggest which pre-built template best matches.

Available templates: mediacorp_el, gp_panel, renewal_comparison, clinic_matcher, none

Respond with ONLY the template slug (one of the above), no explanation.
If no template matches well, respond with "none".
"""

SYSTEM_PROMPT_CHAT = """You are an Excel comparison wizard assistant embedded in a web application.
Help users configure comparison rules for their Excel files.

You can help with:
- Understanding what rule types to use
- Explaining what operators do
- Suggesting which columns to use as unique keys
- Describing how the comparison will work

Keep responses concise and practical. When you suggest a rule, format it as JSON wrapped in ```json blocks.
"""


def build_nl_to_rule_prompt(natural_language: str, column_names: List[str]) -> str:
    """Build user prompt for NL → rule conversion."""
    cols_str = ', '.join(f'"{c}"' for c in column_names)
    return f"""Available columns: [{cols_str}]

User description: "{natural_language}"

Output the rule JSON:"""


def build_template_suggest_prompt(columns: List[str], sheet_name: str) -> str:
    cols_str = ', '.join(columns[:30])  # Limit to avoid token overflow
    return f"""Sheet name: "{sheet_name}"
Columns: {cols_str}

Which template?"""


def build_chat_prompt(message: str, context: Optional[Dict] = None) -> str:
    """Build chat prompt with optional wizard context."""
    ctx_str = ''
    if context:
        ctx_str = f"\nCurrent wizard context:\n{json.dumps(context, indent=2)}\n"
    return f"{ctx_str}\nUser: {message}"
