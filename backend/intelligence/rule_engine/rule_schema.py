"""
Pydantic-like rule schema using dataclasses (no pydantic dependency).
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VALID_RULE_TYPES = {
    'PRESENCE_RULE', 'CHANGE_RULE', 'CONDITION_RULE', 'ROW_MATCH', 'FORMULA_RULE'
}

VALID_OPERATORS = {
    'is_empty', 'is_not_empty', 'equals', 'not_equals', 'contains',
    'starts_with', 'changed_from_empty', 'changed_to_empty',
    'date_is_before', 'date_is_after',
    'changed_from_pattern', 'changed_to_pattern',
}

VALID_FORMULA_ACTIONS = {'compare_value', 'compare_expression', 'skip'}
VALID_MATCH_METHODS = {'exact', 'fuzzy'}


@dataclass
class Condition:
    field: str
    operator: str
    value: Optional[Any] = None  # Not used for is_empty/is_not_empty

    def to_dict(self) -> Dict:
        return {'field': self.field, 'operator': self.operator, 'value': self.value}

    @classmethod
    def from_dict(cls, d: Dict) -> 'Condition':
        return cls(field=d['field'], operator=d['operator'], value=d.get('value'))


@dataclass
class PresenceRuleConfig:
    only_in_file_b: Dict = field(default_factory=lambda: {'outcome_label': 'Addition', 'color': '#C6EFCE'})
    only_in_file_a: Dict = field(default_factory=lambda: {'outcome_label': 'Deletion', 'color': '#FFC7CE'})

    def to_dict(self):
        return {'only_in_file_b': self.only_in_file_b, 'only_in_file_a': self.only_in_file_a}

    @classmethod
    def from_dict(cls, d: Dict) -> 'PresenceRuleConfig':
        return cls(only_in_file_b=d.get('only_in_file_b', {}), only_in_file_a=d.get('only_in_file_a', {}))


@dataclass
class ChangeRuleConfig:
    fields: List[str]
    outcome_label: str = 'Changed'
    color: str = '#FFEB9C'

    def to_dict(self):
        return {'fields': self.fields, 'outcome_label': self.outcome_label, 'color': self.color}

    @classmethod
    def from_dict(cls, d: Dict) -> 'ChangeRuleConfig':
        return cls(fields=d['fields'], outcome_label=d.get('outcome_label', 'Changed'), color=d.get('color', '#FFEB9C'))


@dataclass
class ConditionRuleConfig:
    conditions: List[Condition]
    condition_join: str  # 'AND' | 'OR'
    outcome_label: str
    color: str = '#FFC7CE'

    def to_dict(self):
        return {
            'conditions': [c.to_dict() for c in self.conditions],
            'condition_join': self.condition_join,
            'outcome_label': self.outcome_label,
            'color': self.color,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'ConditionRuleConfig':
        conditions = [Condition.from_dict(c) for c in d.get('conditions', [])]
        return cls(
            conditions=conditions,
            condition_join=d.get('condition_join', 'AND'),
            outcome_label=d['outcome_label'],
            color=d.get('color', '#FFC7CE'),
        )


@dataclass
class RowMatchConfig:
    method: str = 'exact'  # 'exact' | 'fuzzy'
    fuzzy_threshold: float = 0.8

    def to_dict(self):
        return {'method': self.method, 'fuzzy_threshold': self.fuzzy_threshold}

    @classmethod
    def from_dict(cls, d: Dict) -> 'RowMatchConfig':
        return cls(method=d.get('method', 'exact'), fuzzy_threshold=float(d.get('fuzzy_threshold', 0.8)))


@dataclass
class FormulaRuleConfig:
    column_actions: Dict[str, str]  # column_name → 'compare_value' | 'compare_expression' | 'skip'

    def to_dict(self):
        return {'column_actions': self.column_actions}

    @classmethod
    def from_dict(cls, d: Dict) -> 'FormulaRuleConfig':
        return cls(column_actions=d.get('column_actions', {}))


@dataclass
class Rule:
    rule_type: str
    config: Dict

    def to_dict(self):
        return {'rule_type': self.rule_type, 'config': self.config}

    @classmethod
    def from_dict(cls, d: Dict) -> 'Rule':
        return cls(rule_type=d['rule_type'], config=d.get('config', {}))


@dataclass
class SheetConfig:
    file_a_sheet: str
    file_b_sheet: Optional[str] = None  # Defaults to file_a_sheet if None
    header_row: int = 0

    def to_dict(self):
        return {'file_a_sheet': self.file_a_sheet, 'file_b_sheet': self.file_b_sheet, 'header_row': self.header_row}


@dataclass
class ColumnMapping:
    unique_key: List[str]
    compare_fields: List[str] = field(default_factory=list)
    formula_fields: Dict[str, str] = field(default_factory=dict)
    ignored_fields: List[str] = field(default_factory=list)
    display_fields: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'unique_key': self.unique_key,
            'compare_fields': self.compare_fields,
            'formula_fields': self.formula_fields,
            'ignored_fields': self.ignored_fields,
            'display_fields': self.display_fields,
        }


@dataclass
class OutputConfig:
    add_remarks_column: bool = True
    include_summary_sheet: bool = True
    highlight_changed_cells: bool = True
    output_filename_template: str = 'comparison_{date}'

    def to_dict(self):
        return {
            'add_remarks_column': self.add_remarks_column,
            'include_summary_sheet': self.include_summary_sheet,
            'highlight_changed_cells': self.highlight_changed_cells,
            'output_filename_template': self.output_filename_template,
        }


@dataclass
class ComparisonTemplate:
    template_name: str
    sheet_config: SheetConfig
    column_mapping: ColumnMapping
    rules: List[Rule]
    output_config: OutputConfig = field(default_factory=OutputConfig)

    def to_dict(self):
        return {
            'template_name': self.template_name,
            'sheet_config': self.sheet_config.to_dict(),
            'column_mapping': self.column_mapping.to_dict(),
            'rules': [r.to_dict() for r in self.rules],
            'output_config': self.output_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'ComparisonTemplate':
        sc = d['sheet_config']
        cm = d['column_mapping']
        oc = d.get('output_config', {})
        return cls(
            template_name=d['template_name'],
            sheet_config=SheetConfig(
                file_a_sheet=sc['file_a_sheet'],
                file_b_sheet=sc.get('file_b_sheet'),
                header_row=sc.get('header_row', 0),
            ),
            column_mapping=ColumnMapping(
                unique_key=cm['unique_key'],
                compare_fields=cm.get('compare_fields', []),
                formula_fields=cm.get('formula_fields', {}),
                ignored_fields=cm.get('ignored_fields', []),
                display_fields=cm.get('display_fields', []),
            ),
            rules=[Rule.from_dict(r) for r in d.get('rules', [])],
            output_config=OutputConfig(
                add_remarks_column=oc.get('add_remarks_column', True),
                include_summary_sheet=oc.get('include_summary_sheet', True),
                highlight_changed_cells=oc.get('highlight_changed_cells', True),
                output_filename_template=oc.get('output_filename_template', 'comparison_{date}'),
            ),
        )
