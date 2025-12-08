FROM python:3.11.13 AS runtime

WORKDIR /api

COPY vendor vendor
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache pip install -r requirements.txt

COPY . .

RUN apt-get update -qq && apt-get install ffmpeg -y

ENTRYPOINT [ "/api/start-safety-worker.sh" ]
