docker ps -q --filter name=^registry$ | grep -q . || docker run -d --name registry -p 5000:5000 registry:3.1.2
sleep 2
docker build -t hello-app:1.1 .
docker tag hello-app:1.1 localhost:5000/hello-app:1.1
docker tag hello-app:1.1 localhost:5000/hello-app:latest
docker push --all-tags localhost:5000/hello-app
