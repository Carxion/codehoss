docker build -t greeter-web:1 .
docker run -d --name hello -p 8081:8000 greeter-web:1
docker run -d --name hola -e GREETING=Hola -p 8082:8000 greeter-web:1
