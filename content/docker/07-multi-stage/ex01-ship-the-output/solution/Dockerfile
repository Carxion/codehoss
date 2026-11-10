FROM python:3.12-alpine AS build
WORKDIR /src
COPY . .
RUN python build.py

FROM python:3.12-alpine
COPY --from=build /src/site /site
CMD ["python", "-m", "http.server", "-d", "/site", "8000"]
