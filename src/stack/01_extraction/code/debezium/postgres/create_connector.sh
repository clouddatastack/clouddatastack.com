#!/usr/bin/env bash
set -euo pipefail

# Usage: ./create_connector.sh http://<connect-host>:8083 connector_postgres_generic.json

CONNECT_URL=${1:-http://localhost:8083}
CONFIG_FILE=${2:-connector_postgres_generic.json}

curl -s -X POST \
  -H "Content-Type: application/json" \
  --data @"${CONFIG_FILE}" \
  "${CONNECT_URL}/connectors" | jq .
