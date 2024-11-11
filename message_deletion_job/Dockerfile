FROM alpine:3

WORKDIR /psql-client

RUN apk --no-cache add postgresql-client

ADD ./delete_expired_messages.sql ./

CMD ["psql", "-d", "${POSTGRES_CONNECTION_STRING}", "-f", "./delete_expired_messages.sql"]