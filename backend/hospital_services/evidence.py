"""Select observed values without manufacturing missing data."""

from collections import defaultdict


MIN_FIELD_SCORE = 0.90


def resolve_field(observations: list[dict]) -> tuple[object, list[dict], bool]:
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
    credible = [item for item in options if item["score"] >= MIN_FIELD_SCORE]
    selected = credible[0] if credible else options[0]
    unresolved = (len(credible) > 1 or selected["score"] < MIN_FIELD_SCORE
                  or any(item.get("unresolved", False) for item in candidates[selected["value"]]))
    return selected["value"], options, unresolved
