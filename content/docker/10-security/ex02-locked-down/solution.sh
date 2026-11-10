docker build -t heartbeat:1 .
docker run -d --name locked --read-only --tmpfs /tmp --cap-drop ALL heartbeat:1
sleep 2
