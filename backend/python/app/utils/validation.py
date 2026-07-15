from typing import Optional


def normalize_entity_id(value) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            parsed = int(value)
            return parsed if parsed > 0 else None
    return None
