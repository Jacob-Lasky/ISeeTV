import inspect
import logging
import os


class ContextualLogger(logging.Logger):
    def _add_context(self, msg) -> str:
        func_name = inspect.currentframe().f_back.f_back.f_code.co_name
        return f"[{func_name}]: {msg}"

    def debug(self, msg, *args, **kwargs):
        return super().debug(self._add_context(msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        return super().info(self._add_context(msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return super().warning(self._add_context(msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return super().error(self._add_context(msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return super().critical(self._add_context(msg), *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        return super().exception(self._add_context(msg), *args, **kwargs)


logging.setLoggerClass(ContextualLogger)


def get_logger(name: str = __name__) -> ContextualLogger:
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()

        log_format = os.getenv(
            "LOG_FORMAT",
            "%(asctime)s | %(levelname)s:\t%(message)s",
        )
        formatter = logging.Formatter(
            fmt=log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Set level from environment or default to INFO
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logger.setLevel(log_level)

    return logger
