import sys
import logging
import structlog
from typing import Any


def configure_logging():
    """
    Configura o logging estruturado (JSON) para a aplicação.
    Intercepta logs da standard library e os redireciona para o structlog.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]

    # Configuração para renderizar logs
    if sys.stderr.isatty():
        # Se for terminal (dev), usa cores
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # Se for arquivo/pipe (prod/docker), usa JSON
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
