FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --gid 10001 harnessuser && \
    useradd --uid 10001 --gid harnessuser --create-home --shell /usr/sbin/nologin harnessuser

COPY pyproject.toml README.md LICENSE MANIFEST.in ./
COPY src ./src
COPY artifacts ./artifacts

RUN pip install --no-cache-dir . && \
    chown -R harnessuser:harnessuser /app

USER harnessuser
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "harness.api:app", "--host", "0.0.0.0", "--port", "8000"]
