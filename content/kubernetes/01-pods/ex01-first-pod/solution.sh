kubectl run hello --image=python:3.12-alpine --restart=Never -- python -c "print('Hello from Kubernetes')"
kubectl wait --for=jsonpath='{.status.phase}'=Succeeded pod/hello --timeout=60s
