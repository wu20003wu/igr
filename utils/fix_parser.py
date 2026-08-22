"""Pure FIX message parsing helpers (no Flask)."""
import re


def extract_tag_value(fix_string, tag):
    """Extracts the value of a given tag from a FIX string."""
    pattern = f"(?:^|\\|){tag}=([^|]+)"
    match = re.search(pattern, fix_string)
    if match:
        return match.group(1)
    return None
