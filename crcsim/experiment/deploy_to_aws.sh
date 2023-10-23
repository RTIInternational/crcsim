#!/usr/bin/env bash

docker buildx build --platform linux/amd64 -t crcsim . &&

aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 547883312134.dkr.ecr.us-east-2.amazonaws.com &&

docker tag crcsim:latest 547883312134.dkr.ecr.us-east-2.amazonaws.com/crcsim:latest &&

docker push 547883312134.dkr.ecr.us-east-2.amazonaws.com/crcsim:latest