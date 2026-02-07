"""Decorator helpers for polinjectum.

These decorators provide cleaner syntax for common DI patterns.
They are stubs for now and will be fully implemented in a later phase.
"""

from typing import Any, Callable, TypeVar

T = TypeVar("T")


def injectable(cls: type) -> type:
    """Mark a class as injectable.

    Currently a pass-through stub — the class is returned unchanged.
    Future versions will support auto-registration with the container.

    Args:
        cls: The class to mark as injectable.

    Returns:
        The class, unmodified.

    Examples:
        >>> @injectable
        ... class MyService:
        ...     pass
        >>> MyService  # doctest: +ELLIPSIS
        <class '...MyService'>
    """
    return cls


def inject(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a function or method for explicit injection.

    Currently a pass-through stub — the function is returned unchanged.
    Future versions will resolve parameters from the container at call time.

    Args:
        fn: The function or method to mark for injection.

    Returns:
        The function, unmodified.

    Examples:
        >>> @inject
        ... def greet(name: str) -> str:
        ...     return f"Hello, {name}"
        >>> greet("world")
        'Hello, world'
    """
    return fn
