docker build -t fixme:1 .
docker run -d --name fixme -p 8085:8000 fixme:1
