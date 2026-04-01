"""OpenTelemetry 初始化与 Tracer 获取。"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

_tracer_provider: TracerProvider | None = None


def setup_tracing(service_name: str | None = None) -> TracerProvider:
    """初始化 OpenTelemetry TracerProvider 并注册为全局。

    通过环境变量 OTEL_EXPORTER_OTLP_ENDPOINT 控制 exporter 目标地址。
    未设置时不导出 traces（本地开发不报错）。
    """
    global _tracer_provider
    if _tracer_provider is not None:
        return _tracer_provider

    name = service_name or os.getenv("OTEL_SERVICE_NAME", "ops-brain")
    resource = Resource.create({"service.name": name})

    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider


def get_tracer(name: str = "ops-brain") -> trace.Tracer:
    """获取命名 Tracer，用于在业务代码中创建 span。"""
    return trace.get_tracer(name)


def close_tracing() -> None:
    """关闭 TracerProvider（应用退出时调用）。"""
    global _tracer_provider
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception:
            pass
        _tracer_provider = None
