# The CodeHoss server: API, browser app and the course content, plus the Docker CLI it
# uses to run sandboxes. It needs a Docker engine to talk to (DOCKER_HOST); the Helm
# chart (deploy/helm/codehoss) runs one beside it.
#
#   docker build -t codehoss .
#   docker run -p 8000:8000 -v /var/run/docker.sock:/var/run/docker.sock codehoss

FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ src/
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
# The Docker CLI (with buildx, for `dojo build-images`) from the official image.
COPY --from=docker:29-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:29-cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
RUN groupadd --gid 10001 dojo && useradd --uid 10001 --gid 10001 --create-home dojo
WORKDIR /app
COPY --from=app /app/.venv /app/.venv
COPY --from=app /app/src /app/src
COPY --from=web /web/dist /app/web/dist
# A pristine copy of the courses; the chart seeds the live content volume from it.
COPY content/ /app/content/
COPY content/ /app/content.dist/
RUN mkdir -p /app/var && chown -R dojo:dojo /app/var /app/content
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 \
    DOJO_CONTENT=/app/content DOJO_DB=/app/var/dojo.db
USER dojo
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["dojo", "serve", "--host", "0.0.0.0", "--port", "8000"]
