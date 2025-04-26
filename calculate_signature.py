import hmac
import hashlib
import json

secret = "mysecret"

payload_dict = {
  "event": "order.created",
  "data": {
    "order_id": 12345,
    "amount": 100.0,
    "customer": "demo@example.com"
  },
  "timestamp": "2025-04-26T21:47:17.140015+00:00"
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
