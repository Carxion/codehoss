docker build -q -t house-api:1 .
docker run -d --name house-api -p 8080:8080 house-api:1
