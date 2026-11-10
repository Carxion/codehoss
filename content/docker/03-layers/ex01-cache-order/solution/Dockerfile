FROM python:3.12-alpine
WORKDIR /app
COPY setup.py words.txt ./
RUN python setup.py
COPY app.py ./
CMD ["python", "app.py"]
