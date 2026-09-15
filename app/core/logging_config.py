import logging

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def setup_logging(level: str) -> None:
    """
    Send every `app.*` logger to stderr with timestamp, level and name.

    Only the `app` logger is configured: uvicorn keeps its own setup and
    third-party libraries (pymongo, httpx) do not flood the output.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    app_logger = logging.getLogger("app")
    app_logger.handlers = [handler]  # idempotent across reloads
    app_logger.setLevel(level.upper())
    app_logger.propagate = False
