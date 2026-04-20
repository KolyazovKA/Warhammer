# ── Stage 1: install Python dependencies into an isolated venv ──────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: lean runtime image ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root user
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src/backend/ .

RUN mkdir -p /app/files /app/choma_db \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/docs')" \
    || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
