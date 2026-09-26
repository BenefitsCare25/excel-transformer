"""Select observed values without manufacturing missing data."""

from collections import defaultdict
import re


MIN_FIELD_SCORE = 0.90
CONFUSABLES = (frozenset("0O"), frozenset("1IL"), frozenset("2Z"), frozenset("5S"), frozenset("8B"))


def confusable_equal(first: str, second: str) -> bool:
    return len(first) == len(second) and all(
        a == b or any({a, b} <= group for group in CONFUSABLES) for a, b in zip(first.upper(), second.upper()))


def _well_formed(options: list[dict], formats: tuple[str, ...]) -> list[dict]:
    """Drop readings that only differ from a well-formed reading by confusable characters."""
    matching = [item for item in options if any(re.fullmatch(pattern, str(item["value"])) for pattern in formats)]
    if not matching or len(matching) == len(options):
        return options
    others = [item for item in options if item not in matching]
    if all(any(confusable_equal(str(item["value"]), str(good["value"])) for good in matching) for item in others):
        return matching
    return options


def resolve_field(observations: list[dict], formats: tuple[str, ...] = ()) -> tuple[object, list[dict], bool]:
    candidates = defaultdict(list)
    for observation in observations:
        if observation["value"] is not None:
            candidates[observation["value"]].append(observation)
    options = []
    for value, readings in candidates.items():
        locations = {(item["page"], tuple(item["box"])) for item in readings}
        options.append({
            "value": value,
            "score": max(item["score"] for item in readings),
            "pages": sorted({item["page"] for item in readings}),
            "locations": len(locations),
        })
    if not options:
        return None, [], True
    options.sort(key=lambda item: (len(item["pages"]), item["locations"], item["score"]), reverse=True)
    eligible = _well_formed(options, formats) if formats else options
    credible = [item for item in eligible if item["score"] >= MIN_FIELD_SCORE]
    selected = credible[0] if credible else eligible[0]
    unresolved = (len(credible) > 1 or selected["score"] < MIN_FIELD_SCORE
                  or any(item.get("unresolved", False) for item in candidates[selected["value"]]))
    return selected["value"], options, unresolved
