FROM node:24-bookworm-slim AS node
FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /usr/local/bin/uv
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN apt-get update && apt-get install -y --no-install-recommends git libstdc++6 && rm -rf /var/lib/apt/lists/* && ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /work
RUN mkdir -p /opt/maintenance
COPY . .
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON=/usr/local/bin/python UV_PYTHON_DOWNLOADS=never
ARG EXTRA_DEV=0
RUN if [ "$EXTRA_DEV" = "1" ]; then uv sync --frozen --extra dev; else uv sync --frozen; fi
RUN uv pip install --python /opt/venv/bin/python --no-deps pytest-repeat==0.9.4
RUN if [ -f frontend/package-lock.json ]; then npm --prefix frontend ci --ignore-scripts && mv frontend/node_modules /node_modules; elif [ -f package-lock.json ]; then npm ci --ignore-scripts && mv node_modules /node_modules; fi
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/work/src:/work HOME=/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
USER 10001:10001
ENTRYPOINT ["/opt/venv/bin/python"]