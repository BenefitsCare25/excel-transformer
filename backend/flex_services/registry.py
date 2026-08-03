"""Flex Report company adapter registry.

Each client company is one Python module in ``flex_services/companies/`` exposing:

    COMPANY = {
        "id": "stm",
        "name": "STMicroelectronics (STM)",
        "status": "active",
        "files": [{"key": ..., "label": ..., "required": True}, ...],
        "notes": "What this adapter generates",
    }

    def run(files: dict, pay_month: str, outdir: str) -> dict

To onboard a company: add the module, then add its module name to ACTIVE_MODULES
and drop one placeholder. No platform code changes are needed — the UI renders
each company's upload slots from its own spec.
"""
import importlib
import logging

logger = logging.getLogger(__name__)

ACTIVE_MODULES = ['stm']

# Reserved slots for companies whose logic is not configured yet.
PLACEHOLDER_COUNT = 17

_registry = {}
_load_errors = {}
_loaded = False


def load():
    """Import every active adapter once. A broken adapter is skipped, not fatal."""
    global _loaded
    if _loaded:
        return _registry

    for module_name in ACTIVE_MODULES:
        try:
            module = importlib.import_module(f'flex_services.companies.{module_name}')
            spec = getattr(module, 'COMPANY', None)
            if not spec or not spec.get('id') or not callable(getattr(module, 'run', None)):
                raise AttributeError('module must expose COMPANY dict and run() callable')
            _registry[spec['id']] = module
            logger.info(f"Flex Report: loaded company adapter '{spec['id']}' ({spec.get('name')})")
        except Exception as exc:
            _load_errors[module_name] = str(exc)
            logger.error(f"Flex Report: failed to load adapter '{module_name}': {exc}")

    _loaded = True
    return _registry


def catalog():
    """Company list for the UI: active adapters first, then pending slots."""
    load()
    items = []
    for module in _registry.values():
        spec = module.COMPANY
        items.append({
            'id': spec['id'],
            'name': spec['name'],
            'status': spec.get('status', 'active'),
            'files': spec.get('files', []),
            'notes': spec.get('notes', ''),
        })

    for offset in range(PLACEHOLDER_COUNT):
        number = offset + 2
        items.append({
            'id': f'pending-{number}',
            'name': f'Company {number:02d}',
            'status': 'pending',
            'files': [],
            'notes': 'Logic not configured yet.',
        })

    return items


def get(company_id):
    """Return the adapter module for a company id, or None."""
    return load().get(company_id)


def load_errors():
    """Adapters that failed to import, keyed by module name."""
    load()
    return dict(_load_errors)
