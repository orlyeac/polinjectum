"""Custom exceptions for the polinjectum DI framework."""


class RegistrationError(Exception):
    """Raised when a dependency registration fails.

    Examples:
        >>> raise RegistrationError("Cannot register None as a factory")
        Traceback (most recent call last):
            ...
        polinjectum.exceptions.RegistrationError: Cannot register None as a factory
    """


class ResolutionError(Exception):
    """Raised when a dependency cannot be resolved.

    Includes the dependency chain to help diagnose circular or missing
    dependency issues.

    Args:
        message: Description of the resolution failure.
        chain: The dependency resolution chain that led to the failure.

    Examples:
        >>> raise ResolutionError("No registration found for MyService")
        Traceback (most recent call last):
            ...
        polinjectum.exceptions.ResolutionError: No registration found for MyService
    """

    def __init__(self, message: str, chain: "list[str] | None" = None) -> None:
        if chain:
            chain_str = " -> ".join(chain)
            message = f"{message} (resolution chain: {chain_str})"
        super().__init__(message)
        self.chain = chain or []
