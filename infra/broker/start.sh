#!/usr/bin/env bash
# Writes the broker user list from env (no secrets in git, NFR-07), then starts EMQX.
set -euo pipefail

users=/opt/emqx/data/bootstrap-users.csv
{
  echo "user_id,password,is_superuser"
  echo "edge-bridge,${MQTT_EDGE_BRIDGE_PASSWORD:?},false"
  echo "ignition,${MQTT_IGNITION_PASSWORD:?},false"
  echo "mes-api,${MQTT_MES_API_PASSWORD:?},false"
} > "$users"
chmod 600 "$users"

exec /usr/bin/docker-entrypoint.sh /opt/emqx/bin/emqx foreground
