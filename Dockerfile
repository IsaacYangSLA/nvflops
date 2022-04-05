FROM python:3.8.13-alpine

LABEL maintainer="negonefiveonec@gmail.com"

RUN apk add openssl curl ca-certificates build-base && \
    printf "%s%s%s%s\n" \
    "@nginx " \
    "http://nginx.org/packages/alpine/v" \
    `egrep -o '^[0-9]+\.[0-9]+' /etc/alpine-release` \
    "/main" \
    | tee -a /etc/apk/repositories && \
    curl -o /tmp/nginx_signing.rsa.pub https://nginx.org/keys/nginx_signing.rsa.pub && \
    mv /tmp/nginx_signing.rsa.pub /etc/apk/keys/ && \
    apk add nginx@nginx

RUN python -m pip install --upgrade --no-cache-dir pip \
  && python -m pip install nvflops

