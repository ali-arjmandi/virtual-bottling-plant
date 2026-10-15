#!/bin/sh
# Local dev PKI for MQTT over TLS (UNS-01): a CA and a broker server certificate.
# Run by the `certs` one-shot service in docker-compose.yml; does nothing if the files exist.
# Output dir (default infra/certs/out) is gitignored. Not for production use.
set -eu

OUT="${1:-$(dirname "$0")/out}"
DAYS=825
mkdir -p "$OUT"

if [ -f "$OUT/ca.crt" ] && [ -f "$OUT/broker.crt" ]; then
  echo "certs: already present in $OUT"
  exit 0
fi

openssl req -x509 -newkey rsa:2048 -nodes -days "$DAYS" -subj "/CN=Delfts Sap dev CA" \
  -keyout "$OUT/ca.key" -out "$OUT/ca.crt"

openssl req -newkey rsa:2048 -nodes -subj "/CN=broker" \
  -keyout "$OUT/broker.key" -out "$OUT/broker.csr"

cat > "$OUT/broker.ext" <<EXT
subjectAltName = DNS:broker, DNS:localhost, IP:127.0.0.1
extendedKeyUsage = serverAuth
EXT

openssl x509 -req -in "$OUT/broker.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" \
  -CAcreateserial -days "$DAYS" -extfile "$OUT/broker.ext" -out "$OUT/broker.crt"

rm -f "$OUT/broker.csr" "$OUT/broker.ext" "$OUT/ca.srl"
# The broker runs as uid 1000 and the files are written by root: readable by all (dev only).
chmod 644 "$OUT"/*.crt "$OUT/broker.key"
chmod 600 "$OUT/ca.key"
echo "certs: written to $OUT"
