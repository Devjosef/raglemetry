from src.ingestion.scrubbers import (
    sanitize_text_content,
    sanitize_sql_statement,
    scrub_audit_payload,
)

def test_sanitize_text_content_removes_emails_and_tokens():
    raw_text = "User admin@corp.com failed auth with Bearer secret_token_123 at IP 192.168.1.1"
    clean = sanitize_text_content(raw_text)
    
    assert "admin@corp.com" not in clean
    assert "secret_token_123" not in clean
    assert "192.168.1.1" not in clean
    assert "Bearer [REDACTED]" in clean

def test_sanitize_sql_statement_strips_string_literals():
    raw_sql = "SELECT * FROM users WHERE email = 'john@doe.com' AND status = 'ACTIVE'"
    clean = sanitize_sql_statement(raw_sql)
    
    assert "'john@doe.com'" not in clean
    assert "'ACTIVE'" not in clean
    assert clean == "SELECT * FROM users WHERE email = ? AND status = ?"

def test_scrub_audit_payload_recursively_cleans_nested_dicts():
    raw_payload = {
        "user_data": {
            "email": "user@test.com",
            "query": "SELECT * FROM accounts WHERE name = 'Alice'"
        },
        "logs": ["Token: Bearer xyz123"]
    }
    scrubbed = scrub_audit_payload(raw_payload)
    
    assert scrubbed["user_data"]["email"] == "[REDACTED]"
    assert scrubbed["user_data"]["query"] == "SELECT * FROM accounts WHERE name = ?"
    assert "xyz123" not in scrubbed["logs"][0]
    assert "Bearer [REDACTED]" in scrubbed["logs"][0]