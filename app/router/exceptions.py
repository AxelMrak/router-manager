"""Router client exceptions."""

from __future__ import annotations


class RouterError(Exception):
    """Base exception for router client errors."""

    pass


class RouterConnectionError(RouterError):
    """Raised when the router cannot be reached."""

    pass


class RouterAuthError(RouterError):
    """Raised when authentication fails or token has expired."""

    pass


class RouterTimeoutError(RouterError):
    """Raised when a request to the router times out."""

    pass


class RouterAPIError(RouterError):
    """Raised when the API returns an unexpected or erroneous response."""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        response: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.response = response