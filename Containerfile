FROM python:3-alpine
LABEL org.opencontainers.image.source https://github.com/yuusou/container-autocompose

WORKDIR /usr/src/app

COPY . .

RUN python ./setup.py install

ENTRYPOINT [ "python", "./autocompose.py" ]
