set -x -e
docker build -t mytst . 
docker stop test1 || true
docker rm test1 || true

docker run --name=test1 -p 514:514/udp -ti --entrypoint=sh  mytst

