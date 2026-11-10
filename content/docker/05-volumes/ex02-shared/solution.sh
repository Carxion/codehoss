docker run -d --name writer -v shared:/shared alpine:3.22 sh -c 'while true; do date > /shared/now.txt; sleep 1; done'
sleep 2
