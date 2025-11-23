import sys
import logging


class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m'
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        formatted = f"{timestamp} | {record.levelname:<7} | {record.name:<15} | {record.getMessage()}"
        return f"{color}{formatted}{self.RESET}"


def setup_logger(name: str = "telegram_bot", level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    logger.handlers.clear()
    
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(ColorFormatter())
    logger.addHandler(ch)
    
    return logger


logger = setup_logger()
