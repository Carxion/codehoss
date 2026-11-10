FROM python:3.12-alpine AS base
WORKDIR /app
COPY app.py .

FROM base AS test
COPY test_app.py .
RUN python -m unittest -v

FROM base AS final
CMD ["python", "app.py"]
