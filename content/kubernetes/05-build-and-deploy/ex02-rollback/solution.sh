docker build -q -t docker:5000/shop:1 . && docker push -q docker:5000/shop:1
docker build -q -t docker:5000/shop:2 -f Dockerfile.v2 . && docker push -q docker:5000/shop:2
kubectl apply -f deployment.yaml -f service.yaml
kubectl rollout status deployment/shop --timeout=90s
kubectl set image deployment/shop shop=docker:5000/shop:2
sleep 10
kubectl rollout undo deployment/shop
kubectl rollout status deployment/shop --timeout=90s
