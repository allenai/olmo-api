FROM python:3.11.3 as runtime

WORKDIR /api

COPY vendor vendor
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache pip install -r requirements.txt

COPY . .

ENTRYPOINT [ "/api/start.sh" ]
