FROM python:3.12-alpine
WORKDIR /app
COPY server.py .
HEALTHCHECK --interval=2s --timeout=2s --start-period=5s --retries=3 CMD wget -qO- http://127.0.0.1:8000/health || exit 1
CMD ["python", "server.py"]
