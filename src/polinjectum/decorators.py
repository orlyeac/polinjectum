"""Decorator helpers for polinjectum.

These decorators provide cleaner syntax for common DI patterns.
"""

import functools
import inspect
from typing import Any, Callable, Optional, Type, TypeVar, Union, overload

from polinjectum.exceptions import RegistrationError
from polinjectum.lifecycle import Lifecycle

T = TypeVar("T", bound=type)
F = TypeVar("F", bound=Callable[..., Any])


@overload
def injectable(target: T) -> T: ...


@overload
def injectable(target: F) -> F: ...


@overload
def injectable(
    *,
    interface: Optional[type] = ...,
    qualifier: Optional[str] = ...,
    lifecycle: Lifecycle = ...,
) -> Callable[[Union[T, F]], Union[T, F]]: ...


def injectable(
    target: "T | F | None" = None,
    *,
    interface: Optional[type] = None,
    qualifier: Optional[str] = None,
    lifecycle: Lifecycle = Lifecycle.SINGLETON,
) -> Any:
    """Register a class or factory function with the container.

    Can be used bare (``@injectable``) or with arguments
    (``@injectable(interface=MyABC, qualifier="primary")``).

    **On a class:** registers the class as both the interface and the factory
    (unless ``interface`` is specified).

    **On a function/method:** uses the function as a factory and registers it
    under the function's **return type annotation** as the interface (unless
    ``interface`` is specified). The return annotation is required when no
    explicit ``interface`` is given.

    Args:
        target: The class or function (supplied automatically when used bare).
        interface: The type to register under. Defaults to the class itself
            (for classes) or the return annotation (for functions).
        qualifier: Optional qualifier string.
        lifecycle: ``Lifecycle.SINGLETON`` (default) or ``Lifecycle.TRANSIENT``.

    Returns:
        The class or function, unmodified (but now registered in the container).

    Raises:
        RegistrationError: If used on a function without a return annotation
            and no explicit ``interface`` is provided.

    Examples:
        On a class:

        >>> from polinjectum import PolInjectumContainer
        >>> PolInjectumContainer.reset()
        >>> @injectable
        ... class Greeter:
        ...     def greet(self) -> str:
        ...         return "hello"
        >>> PolInjectumContainer().get_me(Greeter).greet()
        'hello'

        On a factory function:

        >>> PolInjectumContainer.reset()
        >>> class Database:
        ...     def __init__(self, url: str):
        ...         self.url = url
        >>> @injectable
        ... def create_database() -> Database:
        ...     return Database("postgresql://localhost/mydb")
        >>> PolInjectumContainer().get_me(Database).url
        'postgresql://localhost/mydb'
    """
    def decorator(inner: Any) -> Any:
        from polinjectum.polinjectum_container import PolInjectumContainer

        container = PolInjectumContainer()

        if inspect.isclass(inner):
            reg_interface = interface if interface is not None else inner
            factory = inner
        else:
            if interface is not None:
                reg_interface = interface
            else:
                hints = getattr(inner, "__annotations__", {})
                return_type = hints.get("return")
                if return_type is None:
                    raise RegistrationError(
                        f"@injectable on function '{inner.__name__}' requires a "
                        f"return type annotation or an explicit 'interface' argument"
                    )
                reg_interface = return_type
            factory = inner

        container.meet(
            reg_interface,
            qualifier=qualifier,
            factory_function=factory,
            lifecycle=lifecycle,
        )
        return inner

    if target is not None:
        return decorator(target)
    return decorator


def inject(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Resolve type-hinted parameters from the container at call time.

    Parameters that the caller supplies explicitly are left as-is.
    Only missing arguments whose type annotations match a container
    registration are resolved automatically.

    Args:
        fn: The function or method to wrap.

    Returns:
        A wrapper that auto-resolves dependencies before calling *fn*.

    Examples:
        >>> from polinjectum import PolInjectumContainer
        >>> PolInjectumContainer.reset()
        >>> container = PolInjectumContainer()
        >>> container.meet(int, qualifier=None, factory_function=lambda: 42)
        >>> @inject
        ... def show_number(n: int) -> str:
        ...     return str(n)
        >>> show_number()
        '42'
    """
    sig = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from polinjectum.polinjectum_container import PolInjectumContainer

        container = PolInjectumContainer()
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        for name, param in sig.parameters.items():
            if name in bound.arguments:
                continue
            if param.annotation is inspect.Parameter.empty:
                continue

            dep_type = param.annotation
            key = (dep_type, None)
            if key in container._registry:
                kwargs[name] = container.get_me(dep_type)

        return fn(*args, **kwargs)

    return wrapper
