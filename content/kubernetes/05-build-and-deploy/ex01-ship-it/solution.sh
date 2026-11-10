docker build -q -t docker:5000/hello-k8s:1 .
docker push -q docker:5000/hello-k8s:1
kubectl apply -f deployment.yaml -f service.yaml
kubectl rollout status deployment/hello --timeout=90s
