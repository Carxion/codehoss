FROM python:3.12-alpine AS train
WORKDIR /app
COPY data/ data/
COPY model.py train.py check_metrics.py ./
# Build arguments are environment variables while this stage builds.
ARG MODEL_VERSION=1.0.0
ARG MAX_MAE=25000
RUN python train.py && python check_metrics.py

FROM python:3.12-alpine
WORKDIR /app
COPY model.py serve.py ./
COPY --from=train /app/model/ model/
EXPOSE 8080
CMD ["python", "serve.py"]
