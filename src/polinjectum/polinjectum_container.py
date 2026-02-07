"""Main dependency injection container for polinjectum."""

import inspect
import threading
from typing import Annotated, Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, get_args, get_origin

from polinjectum.exceptions import RegistrationError, ResolutionError
from polinjectum.lifecycle import Lifecycle


class Qualifier:
    """Marker for specifying a qualifier in type annotations.

    Use with ``typing.Annotated`` to indicate which qualified registration
    should be injected for a constructor parameter during auto-wiring.

    Args:
        name: The qualifier string matching a ``meet(..., qualifier=name)`` call.

    Examples:
        >>> from typing import Annotated
        >>> from polinjectum import Qualifier
        >>> class MyService:
        ...     def __init__(self, cache: Annotated[Cache, Qualifier("redis")]):
        ...         self.cache = cache
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"Qualifier({self.name!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Qualifier) and self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

T = TypeVar("T")

_RegistryEntry = Tuple[Callable[..., Any], Lifecycle, Optional[Any]]


class PolInjectumContainer:
    """A lightweight dependency injection container.

    This container is a singleton — only one instance exists per process.
    Dependencies are registered with ``meet`` and resolved with ``get_me``
    or ``get_me_list``.

    Examples:
        >>> container = PolInjectumContainer()
        >>> container.meet(int, qualifier="port", factory_function=lambda: 8080)
        >>> container.get_me(int, qualifier="port")
        8080
    """

    _instance: "Optional[PolInjectumContainer]" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "PolInjectumContainer":
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._registry: Dict[Tuple[type, Optional[str]], _RegistryEntry] = {}
                cls._instance = instance
            return cls._instance

    def meet(
        self,
        base: type,
        qualifier: Optional[str] = None,
        factory_function: Optional[Callable[..., Any]] = None,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> None:
        """Register a dependency in the container.

        Args:
            base: The type (or abstract base class) this registration satisfies.
            qualifier: An optional string to distinguish multiple
                implementations of the same base type.
            factory_function: A callable that produces the dependency instance.
                If ``None``, *base* itself is used as the factory (it must
                be callable).
            lifecycle: ``Lifecycle.SINGLETON`` (default) or
                ``Lifecycle.TRANSIENT``.

        Raises:
            RegistrationError: If the factory is not callable.

        Examples:
            >>> container = PolInjectumContainer()
            >>> container.meet(list, factory_function=list)
        """
        if factory_function is None:
            factory_function = base

        if not callable(factory_function):
            raise RegistrationError(
                f"factory_function must be callable, got {type(factory_function).__name__}"
            )

        key = (base, qualifier)
        if key in self._registry:
            label = base.__name__
            if qualifier:
                label = f"{label}[{qualifier}]"
            raise RegistrationError(
                f"Duplicate registration for {label}"
            )
        self._registry[key] = (factory_function, lifecycle, None)

    def get_me(
        self,
        base: type,
        qualifier: Optional[str] = None,
        _chain: Optional[List[str]] = None,
    ) -> Any:
        """Resolve a dependency from the container.

        For ``Lifecycle.SINGLETON`` registrations the factory is called once;
        subsequent calls return the cached instance.  For
        ``Lifecycle.TRANSIENT`` a new instance is produced every time.

        Auto-wiring is supported: if the factory's ``__init__`` (or callable
        signature) has type-hinted parameters, they are resolved from the
        container automatically.

        Args:
            base: The type to resolve.
            qualifier: Optional qualifier to select a specific registration.

        Returns:
            The resolved dependency instance.

        Raises:
            ResolutionError: If no registration is found for the given
                base/qualifier combination.

        Examples:
            >>> container = PolInjectumContainer()
            >>> container.meet(str, factory_function=lambda: "hello")
            >>> container.get_me(str)
            'hello'
        """
        if _chain is None:
            _chain = []

        key = (base, qualifier)
        entry = self._registry.get(key)
        if entry is None:
            if qualifier is None:
                alternatives = [
                    (q, e) for (b, q), e in self._registry.items() if b is base
                ]
                if len(alternatives) == 1:
                    return self.get_me(base, qualifier=alternatives[0][0], _chain=_chain)
                elif len(alternatives) > 1:
                    qualifiers = sorted(q for q, _ in alternatives)
                    label = base.__name__
                    raise ResolutionError(
                        f"Ambiguous resolution for {label}: "
                        f"multiple qualified registrations exist "
                        f"({', '.join(repr(q) for q in qualifiers)}). "
                        f"Specify a qualifier.",
                        chain=_chain + [label],
                    )
            label = base.__name__
            if qualifier:
                label = f"{label}[{qualifier}]"
            raise ResolutionError(
                f"No registration found for {label}",
                chain=_chain + [label],
            )

        factory, lifecycle, cached = entry

        if lifecycle is Lifecycle.SINGLETON and cached is not None:
            return cached

        instance = self._create_instance(factory, _chain)

        if lifecycle is Lifecycle.SINGLETON:
            self._registry[key] = (factory, lifecycle, instance)

        return instance

    def get_me_list(self, base: type) -> List[Any]:
        """Resolve all registered implementations for a base type.

        Returns instances for every qualifier (including ``None``) that was
        registered under *base*.

        Args:
            base: The type whose implementations should be resolved.

        Returns:
            A list of resolved instances (may be empty).

        Examples:
            >>> container = PolInjectumContainer()
            >>> container.meet(int, qualifier="a", factory_function=lambda: 1)
            >>> container.meet(int, qualifier="b", factory_function=lambda: 2)
            >>> sorted(container.get_me_list(int))
            [1, 2]
        """
        results: List[Any] = []
        for (reg_base, qualifier), _ in list(self._registry.items()):
            if reg_base is base:
                results.append(self.get_me(base, qualifier))
        return results

    def _create_instance(
        self,
        factory: Callable[..., Any],
        chain: List[str],
    ) -> Any:
        """Create an instance using *factory*, auto-wiring dependencies.

        Inspects the factory's signature and resolves any parameters whose
        type annotations correspond to registrations in this container.

        Supports ``Annotated[SomeType, Qualifier("name")]`` to resolve
        qualified dependencies.
        """
        try:
            sig = inspect.signature(factory)
        except (ValueError, TypeError):
            return factory()

        kwargs: Dict[str, Any] = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.annotation is inspect.Parameter.empty:
                continue
            if param.default is not inspect.Parameter.empty:
                continue

            dep_type, dep_qualifier = self._extract_type_and_qualifier(param.annotation)
            label = getattr(dep_type, "__name__", str(dep_type))
            if dep_qualifier:
                label = f"{label}[{dep_qualifier}]"
            new_chain = chain + [label]

            try:
                kwargs[name] = self.get_me(dep_type, qualifier=dep_qualifier, _chain=new_chain)
            except ResolutionError:
                raise ResolutionError(
                    f"Cannot auto-wire parameter '{name}' of type {label}",
                    chain=new_chain,
                )

        return factory(**kwargs)

    @staticmethod
    def _extract_type_and_qualifier(
        annotation: Any,
    ) -> Tuple[type, Optional[str]]:
        """Extract base type and optional Qualifier from an annotation.

        If the annotation is ``Annotated[T, Qualifier("x")]``, returns
        ``(T, "x")``.  Otherwise returns ``(annotation, None)``.
        """
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            base_type = args[0]
            for extra in args[1:]:
                if isinstance(extra, Qualifier):
                    return base_type, extra.name
            return base_type, None
        return annotation, None

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton, clearing all registrations.

        Intended for use in tests to ensure a clean state between test cases.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance._registry.clear()
            cls._instance = None
