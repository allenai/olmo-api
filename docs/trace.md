# Traces

We have added open telemetry to the app to assist with monitoring.

## Local

On local we are using [jaegarui](https://www.jaegertracing.io/docs/2.10/) to explore traces

When the docker compose is running. This will capture local calls and show you there trace.

You can see these traces by going to http://localhost:16686/trace

## Production

In production you can go to
https://console.cloud.google.com/traces/explore

## Setup

We are currently sending logs directly to google with no sidecar setup.
