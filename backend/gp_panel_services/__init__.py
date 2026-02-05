"""GP Panel Comparison services."""

from .panel_processor import (
    PanelClinic,
    PanelComparison,
    extract_panel_clinics,
    compare_panels,
    generate_comparison_excel,
    generate_email_draft,
    SHEET_CONFIG
)

__all__ = [
    'PanelClinic',
    'PanelComparison',
    'extract_panel_clinics',
    'compare_panels',
    'generate_comparison_excel',
    'generate_email_draft',
    'SHEET_CONFIG'
]
