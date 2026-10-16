import pytest
from src.workers.db_worker import is_identity_free_key

@pytest.mark.parametrize("key, expected", [
    ("transaction_id", True),
    ("query_fingerprint", True),
    ("user_id", False),
    ("customer_email", False),
    ("account_number", False),
])
def test_is_identity_free_key(key: str, expected: bool):
    assert is_identity_free_key(key) is expected