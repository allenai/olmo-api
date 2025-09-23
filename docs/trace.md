# Traces

We have added open telemetry to the app to assist with monitoring.

## Local

On local you can go to:
http://localhost:16686/trace

When the docker compose is running. This will capture local calls and show you there trace.

## Production

In production you can go to
https://console.cloud.google.com/traces/explore

## Setup

We are currently sending logs directly to google with no sidecar setup.
