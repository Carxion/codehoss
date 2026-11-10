docker build -t web:1 .
docker run -d --name web -p 8080:8000 web:1
