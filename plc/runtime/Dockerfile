# L1 soft-PLC: OpenPLC Runtime v3 at a pinned commit, headless, running plc/src (ADR 0005).
# Build context: repo root (docker-compose.yml).

FROM debian:trixie-20251020 AS openplc
ARG OPENPLC_COMMIT=b5d41356dab4aeadca0dd7ca64ba542f870b595d
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates git \
 && git clone https://github.com/thiagoralves/OpenPLC_v3.git /workdir \
 && git -C /workdir checkout "$OPENPLC_COMMIT"
WORKDIR /workdir
# Slow layer (C++ deps, ~3 min); cached until the commit changes.
RUN ./install.sh docker && rm -rf /var/lib/apt/lists/*

FROM openplc
COPY plc/scripts/build.sh /plc/scripts/build.sh
COPY plc/src /plc/src
COPY plc/runtime/configure.sql plc/runtime/start.sh /plc/runtime/
COPY plc/runtime/mbconfig.cfg /workdir/webserver/mbconfig.template
WORKDIR /workdir/webserver
RUN /plc/scripts/build.sh /workdir/webserver/st_files/line1.st \
 && /workdir/.venv/bin/python3 -c "import sqlite3; c = sqlite3.connect('openplc.db'); c.executescript(open('/plc/runtime/configure.sql').read()); c.commit()" \
 && echo line1.st > active_program \
 && cd scripts && ./compile_program.sh line1.st

# 502: Modbus server for the edge bridge (and the FAT suite). 8080: web UI, monitoring only.
EXPOSE 502 8080
ENTRYPOINT ["/plc/runtime/start.sh"]
