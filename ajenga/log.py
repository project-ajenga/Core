import logging
import os
import sys
from logging import Logger
from logging.handlers import RotatingFileHandler

import ajenga

LOG_DIR: str = ajenga.config.LOG_DIR

log_dir = os.path.expanduser(LOG_DIR)
os.makedirs(log_dir, exist_ok=True)


def get_logger(name: str, file_name: str = None) -> Logger:
    formatter = logging.Formatter('[%(asctime)s %(name)s] %(levelname)s: %(message)s')
    logger_ = logging.getLogger(name)
    while logger_.hasHandlers():
        del logger_.handlers[0]
    default_handler = logging.StreamHandler(sys.stdout)
    default_handler.setFormatter(formatter)
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, f'error-{file_name if file_name else name}.log'), maxBytes=1024 * 1024 * 64, encoding='utf8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    critical_handler = RotatingFileHandler(
        os.path.join(log_dir, f'critical-{file_name if file_name else name}.log'), maxBytes=1024 * 1024 * 64, encoding='utf8')
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(formatter)
    info_handler = RotatingFileHandler(
        os.path.join(log_dir, f'info-{file_name if file_name else name}.log'), maxBytes=1024 * 1024 * 64, encoding='utf8')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    logger_.addHandler(default_handler)
    logger_.addHandler(error_handler)
    logger_.addHandler(critical_handler)
    logger_.addHandler(info_handler)
    logger_.setLevel(logging.DEBUG)
    return logger_


logger = get_logger('ajenga')
