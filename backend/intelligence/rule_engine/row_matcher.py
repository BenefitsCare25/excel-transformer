"""
Row matching: exact key matching and fuzzy matching via difflib.
"""
import difflib
from typing import Any, Dict, List, Optional, Tuple


def make_key(row: Dict, key_fields: List[str]) -> str:
    """Build a composite key string from a row dict."""
    parts = []
    for field in key_fields:
        val = row.get(field, '')
        parts.append(str(val).strip().lower() if val is not None else '')
    return '|'.join(parts)


def build_key_index(rows: List[Dict], key_fields: List[str]) -> Dict[str, int]:
    """Return a dict mapping composite key → row index."""
    index = {}
    for i, row in enumerate(rows):
        key = make_key(row, key_fields)
        if key not in index:  # First occurrence wins
            index[key] = i
    return index


def exact_match(rows_a: List[Dict], rows_b: List[Dict],
                key_fields: List[str]) -> Tuple[List[Tuple], List[int], List[int]]:
    """
    Exact key match between two row lists.

    Returns:
        matched_pairs: List of (idx_a, idx_b) tuples
        only_in_a: List of row indices from rows_a with no match in rows_b
        only_in_b: List of row indices from rows_b with no match in rows_a
    """
    index_b = build_key_index(rows_b, key_fields)
    index_a = build_key_index(rows_a, key_fields)

    matched_pairs = []
    matched_b_indices = set()

    for i, row in enumerate(rows_a):
        key = make_key(row, key_fields)
        if key in index_b:
            j = index_b[key]
            matched_pairs.append((i, j))
            matched_b_indices.add(j)

    only_in_a = [i for i in range(len(rows_a))
                 if make_key(rows_a[i], key_fields) not in index_b]
    only_in_b = [j for j in range(len(rows_b))
                 if j not in matched_b_indices]

    return matched_pairs, only_in_a, only_in_b


def fuzzy_match(rows_a: List[Dict], rows_b: List[Dict],
                key_fields: List[str],
                threshold: float = 0.8) -> Tuple[List[Tuple], List[int], List[int]]:
    """
    Fuzzy key match using difflib.SequenceMatcher.

    For each row in A, finds the best match in B above `threshold`.
    Uses greedy matching (first-best, no global optimization).

    Returns same structure as exact_match.
    """
    keys_a = [make_key(row, key_fields) for row in rows_a]
    keys_b = [make_key(row, key_fields) for row in rows_b]

    matched_pairs = []
    used_b = set()

    for i, key_a in enumerate(keys_a):
        # Try exact first
        try:
            j = keys_b.index(key_a)
            if j not in used_b:
                matched_pairs.append((i, j))
                used_b.add(j)
                continue
        except ValueError:
            pass

        # Fuzzy fallback
        best_score = threshold
        best_j = None
        for j, key_b in enumerate(keys_b):
            if j in used_b:
                continue
            score = difflib.SequenceMatcher(None, key_a, key_b).ratio()
            if score > best_score:
                best_score = score
                best_j = j

        if best_j is not None:
            matched_pairs.append((i, best_j))
            used_b.add(best_j)

    matched_a = {p[0] for p in matched_pairs}
    matched_b = {p[1] for p in matched_pairs}

    only_in_a = [i for i in range(len(rows_a)) if i not in matched_a]
    only_in_b = [j for j in range(len(rows_b)) if j not in matched_b]

    return matched_pairs, only_in_a, only_in_b
