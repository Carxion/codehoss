FROM python:3.12-alpine
WORKDIR /src
COPY . .
RUN python build.py
CMD ["python", "-m", "http.server", "-d", "/src/site", "8000"]
