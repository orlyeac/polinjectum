"""polinjectum — A lightweight dependency injection framework for Python."""

from polinjectum.decorators import inject, injectable
from polinjectum.exceptions import RegistrationError, ResolutionError
from polinjectum.lifecycle import Lifecycle
from polinjectum.polinjectum_container import PolInjectumContainer

__all__ = [
    "PolInjectumContainer",
    "Lifecycle",
    "RegistrationError",
    "ResolutionError",
    "inject",
    "injectable",
]
