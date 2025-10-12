"""
Налаштування логування для бота
Підтримує JSON формат та кольорові логи в консолі
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

import structlog
from pythonjsonlogger import jsonlogger


def setup_logger(
    log_level: str = "INFO",
    log_file: Path = None,
    log_format: str = "json"
):
    """
    Налаштування системи логування
    
    Args:
        log_level: Рівень логування (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Шлях до файлу логів
        log_format: Формат логів (json або text)
    """
    # Конвертація рівня логування
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Створення директорії для логів
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Налаштування root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Очищення існуючих handlers
    root_logger.handlers.clear()
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if log_format == "json":
        # JSON формат для продакшну
        console_formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Текстовий формат для розробки
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File Handler
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        # Завжди JSON для файлів
        file_formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Налаштування сторонніх логерів
    _configure_third_party_loggers()
    
    # Structured logging setup
    _setup_structlog(numeric_level)
    
    logging.info(
        f"Logger initialized",
        extra={
            "log_level": log_level,
            "log_file": str(log_file) if log_file else None,
            "log_format": log_format
        }
    )


def _configure_third_party_loggers():
    """Налаштування рівня логування для сторонніх бібліотек"""
    # Зменшуємо verbosity сторонніх бібліотек
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def _setup_structlog(log_level: int):
    """Налаштування structlog для structured logging"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class ColoredFormatter(logging.Formatter):
    """Formatter з кольоровим виводом для консолі"""
    
    # ANSI коди кольорів
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record):
        """Форматування запису з кольорами"""
        # Зберігаємо оригінальний levelname
        levelname = record.levelname
        
        # Додаємо колір до levelname
        if levelname in self.COLORS:
            colored_levelname = (
                f"{self.COLORS[levelname]}{self.BOLD}"
                f"{levelname}{self.RESET}"
            )
            record.levelname = colored_levelname
        
        # Форматуємо запис
        formatted = super().format(record)
        
        # Відновлюємо оригінальний levelname
        record.levelname = levelname
        
        return formatted


class ContextLogger:
    """
    Wrapper для logger з додатковим контекстом
    Використовується для логування з автоматичним додаванням контексту
    """
    
    def __init__(self, name: str, **default_context):
        self.logger = logging.getLogger(name)
        self.default_context = default_context
    
    def _log(self, level: int, msg: str, **kwargs):
        """Внутрішній метод логування"""
        context = {**self.default_context, **kwargs}
        self.logger.log(level, msg, extra=context)
    
    def debug(self, msg: str, **kwargs):
        """Debug level log"""
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """Info level log"""
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Warning level log"""
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        """Error level log"""
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Critical level log"""
        self._log(logging.CRITICAL, msg, **kwargs)
    
    def exception(self, msg: str, **kwargs):
        """Exception level log (з traceback)"""
        context = {**self.default_context, **kwargs}
        self.logger.exception(msg, extra=context)


def get_logger(name: str, **context) -> ContextLogger:
    """
    Отримати logger з контекстом
    
    Args:
        name: Ім'я logger
        **context: Додатковий контекст для всіх логів
    
    Returns:
        ContextLogger instance
    
    Example:
        >>> logger = get_logger(__name__, user_id=123)
        >>> logger.info("User action", action="generate_outfit")
    """
    return ContextLogger(name, **context)


# Декоратор для логування функцій
def log_function_call(logger: logging.Logger = None):
    """
    Декоратор для автоматичного логування викликів функцій
    
    Example:
        >>> @log_function_call()
        >>> async def process_user(user_id: int):
        >>>     pass
    """
    import functools
    import inspect
    
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                f"Calling {func_name}",
                extra={"args": str(args), "kwargs": str(kwargs)}
            )
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"{func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(
                    f"{func_name} failed: {e}",
                    extra={"error": str(e)},
                    exc_info=True
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                f"Calling {func_name}",
                extra={"args": str(args), "kwargs": str(kwargs)}
            )
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(
                    f"{func_name} failed: {e}",
                    extra={"error": str(e)},
                    exc_info=True
                )
                raise
        
        # Визначаємо чи функція async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Функція для логування метрик
def log_metric(metric_name: str, value: float, **tags):
    """
    Логування метрики для моніторингу
    
    Args:
        metric_name: Назва метрики
        value: Значення метрики
        **tags: Додаткові теги
    
    Example:
        >>> log_metric("ai_generation_time", 12.5, user_id=123, provider="gemini")
    """
    logger = logging.getLogger("metrics")
    logger.info(
        f"Metric: {metric_name}",
        extra={
            "metric_name": metric_name,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
            **tags
        }
    )


# Функція для логування подій користувача
def log_user_action(
    user_id: int,
    action: str,
    **details
):
    """
    Логування дій користувача
    
    Args:
        user_id: Telegram ID користувача
        action: Тип дії
        **details: Додаткові деталі
    
    Example:
        >>> log_user_action(123, "generate_outfit", season="summer")
    """
    logger = logging.getLogger("user_actions")
    logger.info(
        f"User action: {action}",
        extra={
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            **details
        }
    )


# Функція для логування помилок з контекстом
def log_error_with_context(
    error: Exception,
    context: dict,
    logger_name: str = "errors"
):
    """
    Логування помилки з повним контекстом
    
    Args:
        error: Exception об'єкт
        context: Контекст помилки
        logger_name: Ім'я logger
    """
    logger = logging.getLogger(logger_name)
    logger.error(
        f"Error: {str(error)}",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        },
        exc_info=True
    )


# Приклад використання
if __name__ == "__main__":
    # Налаштування logger
    setup_logger(
        log_level="DEBUG",
        log_file=Path("logs/test.log"),
        log_format="text"
    )
    
    # Звичайний logging
    logger = logging.getLogger(__name__)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Context logger
    ctx_logger = get_logger(__name__, service="test")
    ctx_logger.info("Testing context logger", user_id=123)
    
    # Метрики
    log_metric("test_metric", 42.0, tag1="value1")
    
    # User action
    log_user_action(123, "test_action", detail="test")
    
    print("\n✓ Logger test completed")