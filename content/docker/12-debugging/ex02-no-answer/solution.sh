docker build -t bind:1 .
docker run -d --name bind -p 8086:8000 bind:1
