docker build -t notes:2 .
docker run -d --name notes -p 8083:8000 notes:2
