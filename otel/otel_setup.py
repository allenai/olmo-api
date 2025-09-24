from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import set_tracer_provider

from src.config.get_config import get_config


class CustomAttributeSpanProcessor(SpanProcessor):
    # This class forces the service.name onto the span. For some reason OLTPSpanExporter will not send the process tags, so this is a way to force it.
    def on_start(self, span, parent_context=None):
        span.set_attributes({
            "service.name": "olmo-api",
        })

    def on_end(self, span):
        pass


def setup_otel():
    cfg = get_config()

    tracer_provider = TracerProvider()

    tracer_provider.add_span_processor(CustomAttributeSpanProcessor())

    if cfg.otel.collector_type == "local":
        tracer_provider.add_span_processor(span_processor=SimpleSpanProcessor(OTLPSpanExporter()))
    if cfg.otel.collector_type == "cloud":
        tracer_provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id="ai2-reviz")))

    set_tracer_provider(tracer_provider)
