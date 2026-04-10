from prometheus_client import Histogram

EXTERNAL_LATENCY = Histogram(
    "external_request_latency_seconds",
    "Latency of external service",
    ["service", "operation"]
)


import time

from prometheus_client import Histogram

def create_service_metrics(service_name: str):


    def decorator(operation: str):
        def wrapper(func):
            async def inner(instance, *args, **kwargs):
                import time
                start = time.perf_counter()

                result = await func(instance, *args, **kwargs)

                EXTERNAL_LATENCY.labels(
                    service=service_name,
                    operation=operation
                ).observe(time.perf_counter() - start)

                return result

            return inner
        return wrapper

    return decorator