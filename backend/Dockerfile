# ---- builder: install all Python dependencies into a venv ----
FROM python:3.12-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
# Minimal stub so pip can resolve the local package during dep installation
RUN mkdir -p app && touch app/__init__.py
RUN pip install --no-cache-dir ".[dev]"

# ---- runtime: lean image with venv + application source ----
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# /app takes precedence over the stale package copy inside the venv
ENV PYTHONPATH=/app

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
