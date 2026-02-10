from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import set_tracer_provider

from api.config import settings


class CustomAttributeSpanProcessor(SpanProcessor):
    # ignoring formatting on this because its inherited (even though its probably safe to change the signature)
    def on_start(self, span, parent_context=None):  # noqa: ARG002, PLR6301
        span.set_attributes({
            "service.name": settings.OTEL_SERVICE_NAME,
        })

    def on_end(self, span):
        pass


def setup_otel() -> None:
    tracer_provider = TracerProvider()

    tracer_provider.add_span_processor(CustomAttributeSpanProcessor())

    if settings.OTEL_COLLECTOR_TYPE == "local":
        tracer_provider.add_span_processor(span_processor=SimpleSpanProcessor(OTLPSpanExporter()))
    elif settings.OTEL_COLLECTOR_TYPE == "cloud":
        tracer_provider.add_span_processor(
            BatchSpanProcessor(CloudTraceSpanExporter(project_id=settings.OTEL_GCP_PROJECT_ID))
        )

    set_tracer_provider(tracer_provider)
