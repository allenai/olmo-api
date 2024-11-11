FROM alpine:3

WORKDIR /psql-client

RUN apk --no-cache add postgresql-client jq

COPY . .

RUN chmod +x ./start.sh

ENTRYPOINT [ "sh", "/psql-client/start.sh" ]
# CMD ["psql", "-d", "${POSTGRES_CONNECTION_STRING}", "-f", "./delete_expired_messages.sql"]