"""Quick smoke test for JWT auth."""
from backend.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)

# password hashing
h = hash_password("testpass123")
assert verify_password("testpass123", h)
assert not verify_password("wrong", h)
print("OK: password hashing")

# token create + decode
at = create_access_token(user_id=42, role="auditor")
payload = decode_token(at)
assert payload["sub"] == "42"
assert payload["role"] == "auditor"
assert payload["type"] == "access"
print(f"OK: access token (sub={payload['sub']}, role={payload['role']})")

rt = create_refresh_token(user_id=42, role="auditor")
payload2 = decode_token(rt)
assert payload2["type"] == "refresh"
print("OK: refresh token")

print("All auth tests passed")
