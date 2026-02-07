"""Lifecycle management for dependencies."""

from enum import Enum


class Lifecycle(Enum):
    """Defines the lifecycle of a registered dependency.

    Attributes:
        SINGLETON: The same instance is returned on every resolution.
        TRANSIENT: A new instance is created on every resolution.

    Examples:
        >>> Lifecycle.SINGLETON
        <Lifecycle.SINGLETON: 'singleton'>
        >>> Lifecycle.TRANSIENT
        <Lifecycle.TRANSIENT: 'transient'>
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"
