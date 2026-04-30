import contextlib
import functools
import logging
import time
from typing import Any, Callable, Iterator, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def _get_logger() -> logging.Logger:
    logger = logging.getLogger("routeplanner.timing")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def timeit(label: str | None = None) -> Callable[[F], F]:
    """Decorator to log execution time for a function."""

    def decorator(func: F) -> F:
        name = label or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            message = f"TIMING {name}: {elapsed:.4f} seconds"
            _get_logger().info(message)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


@contextlib.contextmanager
def timed_block(label: str) -> Iterator[None]:
    """Context manager for timing a code block."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        message = f"TIMING {label}: {elapsed:.4f} seconds"
        _get_logger().info(message)
