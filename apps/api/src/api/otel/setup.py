from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import set_tracer_provider
from pydantic_ai import Agent, InstrumentationSettings

from api.config import settings

agent_instrumentation_settings = InstrumentationSettings(
    version=4,
    include_content=False,
    include_binary_content=False,
)


def setup_otel() -> None:
    resource = Resource.create(attributes={SERVICE_NAME: settings.OTEL_SERVICE_NAME})
    tracer_provider = TracerProvider(resource=resource)

    if settings.OTEL_COLLECTOR_TYPE == "local":
        tracer_provider.add_span_processor(span_processor=SimpleSpanProcessor(OTLPSpanExporter()))
    elif settings.OTEL_COLLECTOR_TYPE == "cloud":
        tracer_provider.add_span_processor(
            BatchSpanProcessor(CloudTraceSpanExporter(project_id=settings.OTEL_GCP_PROJECT_ID))
        )

    set_tracer_provider(tracer_provider)
    Agent.instrument_all(agent_instrumentation_settings)
