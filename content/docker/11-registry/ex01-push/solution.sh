docker run -d --name registry -p 5000:5000 registry:3.1.2
sleep 2
docker build -t hello-app:1.0 .
docker tag hello-app:1.0 localhost:5000/hello-app:1.0
docker push localhost:5000/hello-app:1.0
