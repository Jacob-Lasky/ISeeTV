import os
import sys
import logging


class ColorFormatter(logging.Formatter):
    COLORS = {
        "GREY": "38;5;241m",  # Darker grey
        "YELLOW": "38;5;130m",  # Darker yellow
        "RED": "38;5;124m",  # Darker red
        "LIGHT_GREEN": "38;5;118m",  # Light green
        "GREEN": "38;5;28m",  # Darker green
        "LIGHT_BLUE": "38;5;117m",  # Light blue
        "BLUE": "38;5;25m",  # Darker blue
    }

    START = "\x1b["
    END = "\x1b[0m"

    def __init__(self, fmt, color, log_level):
        super().__init__()
        self.fmt = fmt
        self.color = self.COLORS[color]

        # use red color
        if log_level in ["WARNING", "ERROR", "CRITICAL"]:
            self.color = self.START + self.COLORS["RED"] + self.fmt + self.END
        else:
            self.color = self.START + self.color + self.fmt + self.END

    def format(self, record):
        formatter = logging.Formatter(self.color, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class Logger:
    COLORS = ColorFormatter.COLORS

    def __init__(
        self,
        name: str,
        verbose: bool,
        log_level: str,
        color: str = "GREY",
    ):
        self.logger = logging.getLogger(name)
        self.verbose = verbose.lower() == "true"
        self.log_level = log_level.upper()
        self.name = name

        formatter = ColorFormatter(
            fmt=self.message_format(), color=color, log_level=log_level
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        self.logger.setLevel(log_level)
        self.logger.addHandler(handler)

    def message_format(self):
        if self.verbose:
            return "%(name)s | %(levelname)s: %(asctime)s - %(filename)s:%(module)s:%(lineno)d - %(message)s"
        else:
            return "%(name)s | %(levelname)s: %(asctime)s - %(message)s"

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)
