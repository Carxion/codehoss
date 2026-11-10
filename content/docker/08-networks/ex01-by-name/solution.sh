docker build -t netdemo:1 .
docker network create appnet
docker run -d --name db --network appnet netdemo:1 python db.py
docker run -d --name app --network appnet -p 8084:8000 netdemo:1 python app.py
