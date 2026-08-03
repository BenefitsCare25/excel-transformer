"""Flex Report services.

Plugin-style monthly report factory: each client company is one adapter module in
``flex_services/companies/`` that declares its own upload slots and transformation
logic. The platform handles uploads, ephemeral run storage, validation surfacing
and downloads.
"""

from .errors import FlexInputError
from .registry import catalog, get, load, load_errors
from .run_store import (
    RETENTION_MINUTES,
    create_run,
    discard_run,
    finalize_run,
    is_valid_run_id,
    output_path,
    purge_expired,
    read_manifest,
    start_reaper,
    zip_run,
)

__all__ = [
    'FlexInputError',
    'catalog',
    'get',
    'load',
    'load_errors',
    'RETENTION_MINUTES',
    'create_run',
    'discard_run',
    'finalize_run',
    'is_valid_run_id',
    'output_path',
    'purge_expired',
    'read_manifest',
    'start_reaper',
    'zip_run',
]
