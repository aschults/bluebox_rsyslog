set -x -e
docker build -t mytst . 
docker stop test1 || true
docker rm test1 || true

docker run -e rsyslog_debug=1 --name=test1 -ti --entrypoint=sh  mytst

