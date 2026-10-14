#!/bin/bash
# Resolves the sim host (libmodbus needs an IP, not a name), writes mbconfig.cfg and starts the
# OpenPLC webserver, which starts the runtime in RUN mode (configure.sql).
set -euo pipefail
cd /workdir/webserver

SIM_HOST="${PLC_SIM_HOST:-sim}"
until SIM_IP="$(getent hosts "$SIM_HOST" | awk '{print $1; exit}')" && [ -n "$SIM_IP" ]; do
    echo "waiting for $SIM_HOST to resolve..."
    sleep 1
done

sed -e "s/@SIM_HOST@/$SIM_IP/g" \
    -e "s/^Polling_Period = .*/Polling_Period = \"${PLC_POLL_MS:-50}\"/" \
    -e "s/^Timeout = .*/Timeout = \"${PLC_SLAVE_TIMEOUT_MS:-250}\"/" \
    mbconfig.template > mbconfig.cfg
echo "slave devices: $SIM_HOST ($SIM_IP), poll ${PLC_POLL_MS:-50} ms, timeout ${PLC_SLAVE_TIMEOUT_MS:-250} ms"

exec /workdir/.venv/bin/python3 webserver.py
