import re
from typing import Dict, Any

class MetadataScrubber:
    def __init__(self, mask_str: str = "[REDACTED]"):
        self.mask_str = mask_str


EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# Matches authorization header formats cleanly:
# 1. "Token: Bearer secret" -> "Token: Bearer [REDACTED]"
# 2. "Bearer secret" -> "Bearer [REDACTED]"
# 3. "api_key: secret" or "password=secret" -> "api_key: [REDACTED]"
AUTH_HEADER_REGEX = re.compile(
    r'\b((?:token|authorization|auth)\s*[:=]\s*)?(bearer)\s+[^\s"\'`,]+|\b(token|api[_-]?key|password|secret|auth)\s*[:=]\s*["\']?[^\s"\'`,]+["\']?',
    flags=re.IGNORECASE
)

INLINE_STRING_LITERALS = re.compile(r"'[^']*'|\"[^\"]*\"")
IP_ADDRESS_REGEX = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')


def sanitize_text_content(text: str, mask: str = "[REDACTED]") -> str:
    if not text:
        return ""
    
    clean = EMAIL_REGEX.sub(mask, text)
    
    def _mask_auth(match: re.Match) -> str:
        matched_str = match.group(0)
        
        # If "Bearer" is in the matched string (e.g. "Token: Bearer secret" or "Bearer secret")
        if "bearer" in matched_str.lower():
            if ":" in matched_str:
                prefix = matched_str.split(":")[0]
                return f"{prefix}: Bearer {mask}"
            elif "=" in matched_str:
                prefix = matched_str.split("=")[0]
                return f"{prefix}=Bearer {mask}"
            return f"Bearer {mask}"
        
        # Standard key: value or key=value pair
        if ":" in matched_str:
            key = matched_str.split(":")[0]
            return f"{key}: {mask}"
        if "=" in matched_str:
            key = matched_str.split("=")[0]
            return f"{key}={mask}"
            
        return f"{match.group(1)} {mask}"

    clean = AUTH_HEADER_REGEX.sub(_mask_auth, clean)
    clean = IP_ADDRESS_REGEX.sub(mask, clean)
    return clean


def sanitize_sql_statement(sql_query: str) -> str:
    if not sql_query:
        return ""
    return INLINE_STRING_LITERALS.sub("?", sql_query)


def scrub_audit_payload(payload: Dict[str, Any], mask: str = "[REDACTED]") -> Dict[str, Any]:
    scrubbed = {}
    for key, value in payload.items():
        key_lower = str(key).lower()
        
        if any(term in key_lower for term in ("sql", "query", "statement")):
            if isinstance(value, str):
                scrubbed[key] = sanitize_sql_statement(value)
            else:
                scrubbed[key] = value
        elif isinstance(value, str):
            scrubbed[key] = sanitize_text_content(value, mask=mask)
        elif isinstance(value, dict):
            scrubbed[key] = scrub_audit_payload(value, mask=mask)
        elif isinstance(value, list):
            scrubbed[key] = [
                scrub_audit_payload(item, mask=mask) if isinstance(item, dict)
                else sanitize_text_content(item, mask=mask) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            scrubbed[key] = value
            
    return scrubbed