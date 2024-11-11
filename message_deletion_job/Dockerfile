FROM alpine:3

WORKDIR /psql-client

RUN apk --no-cache add postgresql-client jq

COPY . .

ENTRYPOINT [ "sh", "/psql-client/start.sh" ]