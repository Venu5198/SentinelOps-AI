from fastapi import FastAPI, Response, status
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import logging
import sys

app = FastAPI(title="Order Service (Monitored Target)")
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("order-service")

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP Request Duration Seconds", ["endpoint"])

is_failing = False


@app.get("/health")
def health():
    if is_failing:
        REQUEST_COUNT.labels(method="GET", endpoint="/health", status="500").inc()
        logger.error("Internal Server Error: DatabaseConnectionTimeout in OrderServicePool")
        return Response(
            content='{"status": "unhealthy", "error": "DatabaseConnectionTimeout"}',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "healthy", "service": "order-service"}


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/simulate-failure")
def simulate_failure():
    global is_failing
    is_failing = True
    logger.warning("FAILURE SIMULATION INJECTED: order-service is now failing with HTTP 500")
    return {"status": "failure_injected", "is_failing": True}


@app.post("/reset-failure")
def reset_failure():
    global is_failing
    is_failing = False
    logger.info("FAILURE RESET: order-service restored to healthy state")
    return {"status": "failure_reset", "is_failing": False}

