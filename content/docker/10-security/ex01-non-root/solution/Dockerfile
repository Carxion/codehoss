FROM python:3.12-alpine
WORKDIR /app
COPY whoami.py .
RUN adduser -D app
USER app
CMD ["python", "whoami.py"]
