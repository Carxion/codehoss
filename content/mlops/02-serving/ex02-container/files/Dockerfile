# Two stages:
#   1. "train": python:3.12-alpine, copy data/, model.py and train.py into /app, run train.py
#   2. the image we ship: python:3.12-alpine, copy model.py and serve.py, plus ONLY the
#      model/ folder from the train stage (COPY --from=train ...); expose 8080 and run serve.py
