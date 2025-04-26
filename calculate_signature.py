import hmac
import hashlib
import json

secret = "mytestsecret"

payload_dict = {
  "event": "order.created",
  "data": {
    "order_id": 12345,
    "amount": 50.0,
    "customer": "test@example.com"
  },
  "timestamp": "2025-04-26T10:05:00Z"
}

payload_string = json.dumps(payload_dict)

signature_bytes = hmac.new(
    secret.encode('utf-8'),
    payload_string.encode('utf-8'),
    hashlib.sha256
).digest()

signature_hex = signature_bytes.hex()
signature_header_value = f"sha256={signature_hex}"

print(f"Payload string: {payload_string}")
print(f"Signature header value: {signature_header_value}")
