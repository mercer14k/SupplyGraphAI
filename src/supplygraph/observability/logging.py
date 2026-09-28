import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

trace_id = ContextVar("trace_id", default="startup")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
                "trace_id": trace_id.get(),
                **getattr(record, "event_data", {}),
            },
            default=str,
        )


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("supplygraph")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
