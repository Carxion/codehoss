docker build -t netdemo:1 .
docker network create --internal backend
docker run -d --name vault --network backend netdemo:1 python db.py
sleep 2
