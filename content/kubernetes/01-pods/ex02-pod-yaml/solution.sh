kubectl apply -f pod.yaml
kubectl wait --for=condition=Ready pod/web --timeout=90s
