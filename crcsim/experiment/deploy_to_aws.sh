#!/usr/bin/env bash

docker build --add-host=cds-mallard-web.rti.org:10.162.35.16 -t crcsim . &&

aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 810875545305.dkr.ecr.us-west-1.amazonaws.com &&

docker tag crcsim:latest 810875545305.dkr.ecr.us-west-1.amazonaws.com/crcsim:latest &&

docker push 810875545305.dkr.ecr.us-west-1.amazonaws.com/crcsim:latest