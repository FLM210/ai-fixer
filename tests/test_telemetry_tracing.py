from app.telemetry.tracing import setup_tracing


def test_setup_tracing_returns_tracer() -> None:
    tracer = setup_tracing(service_name='k8s-fixer-test', endpoint=None)
    assert tracer is not None
    assert hasattr(tracer, 'start_span')
