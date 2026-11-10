docker build -t flaky:1 .
docker run -d --name flaky --restart on-failure:3 flaky:1
sleep 4
