FROM python:3.12-alpine AS train
WORKDIR /app
COPY data/ data/
COPY model.py train.py ./
RUN python train.py

FROM python:3.12-alpine
WORKDIR /app
COPY model.py serve.py ./
COPY --from=train /app/model/ model/
EXPOSE 8080
CMD ["python", "serve.py"]
