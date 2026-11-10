sed 's/Hola/Hello/' deployment.yaml | kubectl apply -f -
kubectl rollout status deployment/greeter --timeout=90s
kubectl apply -f deployment.yaml
kubectl rollout status deployment/greeter --timeout=90s
