kubectl apply -f cronjob.yaml
kubectl create job report-now --from=cronjob/report
kubectl wait --for=condition=Complete job/report-now --timeout=90s
