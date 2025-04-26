#!/bin/bash

set -e

SERVICE_URL="http://54.175.17.226:8000"
SUBSCRIPTIONS_API_URL="${SERVICE_URL}/api/subscriptions"
INGESTION_API_BASE_URL="${SERVICE_URL}/api/ingest"
STATUS_API_BASE_URL="${SERVICE_URL}/api/status/delivery_tasks"

SUBSCRIPTION_SECRET="mysecret"
WEBHOOK_SECRET_HEADER="X-Hub-Signature-256"
WEBHOOK_EVENT_TYPE_HEADER="X-Event-Type"

# --- Sample Webhook Payload ---
PAYLOAD_JSON='{
  "event": "order.created",
  "data": {
    "order_id": '$((RANDOM % 100000 + 200000))',
    "amount": 100.0,
    "customer": "demo@example.com"
  },
  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
}'

event_type=$(echo "${PAYLOAD_JSON}" | jq -r '.event')

if [ -z "$event_type" ] || [ "$event_type" == "null" ]; then
  echo "Error: Failed to extract event type from PAYLOAD_JSON. Exiting."
  exit 1
fi

echo "Extracted event type: ${event_type}"
echo ""

PAYLOAD_FILE=$(mktemp /tmp/payload.XXXXXX.json)

echo "${PAYLOAD_JSON}" | grep -v '#' > "${PAYLOAD_FILE}"

# --- Create a Subscription ---
echo "--- Creating a new subscription ---"
# Construct the JSON payload for the subscription creation
SUBSCRIPTION_JSON_PAYLOAD="{
  \"target_url\": \"https://webhook.site/$(uuidgen)\",
  \"secret\": \"${SUBSCRIPTION_SECRET}\",
  \"event_type_filter\": \"${event_type}\"
}"

echo "--- JSON payload for subscription creation ---"
echo "${SUBSCRIPTION_JSON_PAYLOAD}"
echo "--------------------------------------------"

echo "--- Targeting URL: ${SUBSCRIPTIONS_API_URL} ---"

# Use tee to print the response while capturing it
CREATE_SUB_RESPONSE=$(curl -s -X POST \
  "${SUBSCRIPTIONS_API_URL}" \
  -H 'Content-Type: application/json' \
  -d "${SUBSCRIPTION_JSON_PAYLOAD}" | tee /dev/stderr)

SUBSCRIPTION_ID=$(echo "${CREATE_SUB_RESPONSE}" | jq -r '.id')

if [ -z "$SUBSCRIPTION_ID" ] || [ "$SUBSCRIPTION_ID" == "null" ]; then
  echo "Error: Failed to create subscription. Exiting."
  # No file cleanup here, leave the file for inspection
  exit 1
fi

echo "Successfully created subscription with ID: ${SUBSCRIPTION_ID}"
echo ""

# --- Calculate Signature ---
echo "--- Calculating signature for the payload ---"
echo "Attempting to run: python3 calculate_signature.py \"${SUBSCRIPTION_SECRET}\" \"${PAYLOAD_FILE}\""
echo "--- Content of temporary payload file (${PAYLOAD_FILE}) ---"
cat "${PAYLOAD_FILE}" # Print the content of the temporary file (should be comment-free)
echo "---------------------------------------------------"

PYTHON_OUTPUT=$(python3 calculate_signature.py "${SUBSCRIPTION_SECRET}" "${PAYLOAD_FILE}" 2>&1)
PYTHON_EXIT_STATUS=$?

if [ $PYTHON_EXIT_STATUS -ne 0 ]; then
  echo "Error: calculate_signature.py failed with exit status $PYTHON_EXIT_STATUS."
  echo "--- Python Error Output ---"
  echo "${PYTHON_OUTPUT}"
  echo "---------------------------"
  exit 1
fi

SIGNATURE_HEADER_VALUE=$(echo "${PYTHON_OUTPUT}" | tail -n 1)


# Check if the signature value was captured
if [ -z "$SIGNATURE_HEADER_VALUE" ]; then
  echo "Error: Failed to capture signature from calculate_signature.py output. Output was empty. Exiting."
  echo "--- Full Python Output ---"
  echo "${PYTHON_OUTPUT}"
  echo "--------------------------"
  exit 1
fi

SIGNATURE_HEADER_VALUE="${WEBHOOK_SECRET_HEADER}: ${SIGNATURE_HEADER_VALUE}"


echo "Calculated Signature Header: ${SIGNATURE_HEADER_VALUE}"
echo ""

echo "--- Signature calculated successfully, cleaning up temporary file ---"
rm "${PAYLOAD_FILE}"
echo "--- Temporary file ${PAYLOAD_FILE} deleted ---"
echo ""

echo "--- Sending first ingestion request (expecting cache miss and DB lookup) ---"
echo "--- Targeting URL: ${INGESTION_API_BASE_URL}/${SUBSCRIPTION_ID} ---"

echo "--- Executing curl command for first ingestion ---"
echo "curl -s -X POST \\"
echo "  \"${INGESTION_API_BASE_URL}/${SUBSCRIPTION_ID}\" \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H \"${WEBHOOK_EVENT_TYPE_HEADER}: ${event_type}\" \\"
echo "  -H \"${SIGNATURE_HEADER_VALUE}\" \\"
echo "  -d \"${PAYLOAD_JSON}\""
echo "--------------------------------------------------"

FIRST_INGEST_RESPONSE=$(curl -s -X POST \
  "${INGESTION_API_BASE_URL}/${SUBSCRIPTION_ID}" \
  -H 'Content-Type: application/json' \
  -H "${WEBHOOK_EVENT_TYPE_HEADER}: ${event_type}" \
  -H "${SIGNATURE_HEADER_VALUE}" \
  -d "${PAYLOAD_JSON}")

echo "First ingestion response: ${FIRST_INGEST_RESPONSE}"
echo ""
sleep 2 # Give the worker a moment to potentially process and cache

echo "--- Sending second ingestion request (expecting cache hit) ---"
echo "--- Targeting URL: ${INGESTION_API_BASE_URL}/${SUBSCRIPTION_ID} ---"
echo "--- Executing curl command for second ingestion ---"
echo "curl -s -X POST \\"
echo "  \"${INGESTION_API_BASE_URL}/${SUBSCRIPTION_ID}\" \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H \"${WEBHOOK_EVENT_TYPE_HEADER}: ${event_type}\" \\"
echo "  -H \"${SIGNATURE_HEADER_VALUE}\" \\" # Use the full header string here
echo "  -d \"${PAYLOAD_JSON}\""
echo "---------------------------------------------------"

SECOND_INGEST_RESPONSE=$(curl -s -X POST \
  "${INGESTION_API_BASE_URL}/${SUBSCRIPTION_ID}" \
  -H 'Content-Type: application/json' \
  -H "${WEBHOOK_EVENT_TYPE_HEADER}: ${event_type}" \
  -H "${SIGNATURE_HEADER_VALUE}" \
  -d "${PAYLOAD_JSON}")

echo "Second ingestion response: ${SECOND_INGEST_RESPONSE}"
echo ""

echo "--- Check the logs of your 'redis' and 'app' containers now ---"
echo "Run: docker-compose logs redis"
echo "Look for GET and SET/SETEX commands around the time the script ran."
echo ""
echo "Run: docker-compose logs app"
echo "Look for log messages indicating cache hit/miss if you added them in ingestion.py."
echo ""
