# L0 simulator. Build context is the repo root (the sim needs contracts/).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app/sim

COPY sim/pyproject.toml sim/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY contracts /app/contracts
COPY sim/src ./src
COPY sim/config ./config
COPY sim/scenarios ./scenarios
RUN uv sync --frozen --no-dev && useradd --system --no-create-home sim
# harness/ (Phase 1 stub controller) is deliberately not part of the image.

USER sim
ENV PATH=/app/sim/.venv/bin:$PATH \
    SIM_MODBUS_PORT=5020 \
    SIM_API_PORT=8000
EXPOSE 5020 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "-m", "sim"]
