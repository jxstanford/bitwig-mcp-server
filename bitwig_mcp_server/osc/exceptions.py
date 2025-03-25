"""
Bitwig OSC Exceptions

This module defines custom exceptions for the Bitwig OSC integration.
"""

from typing import Optional


class BitwigOSCError(Exception):
    """Base exception class for Bitwig OSC errors."""

    def __init__(self, message: str):
        """Initialize with an error message."""
        self.message = message
        super().__init__(message)


class ConnectionError(BitwigOSCError):
    """Error when connection to Bitwig Studio fails."""

    def __init__(
        self,
        message: str = "Failed to connect to Bitwig Studio",
        details: Optional[str] = None,
    ):
        """Initialize with an optional detailed message."""
        self.details = details
        full_message = f"{message}" + (f": {details}" if details else "")
        super().__init__(full_message)


class TimeoutError(BitwigOSCError):
    """Error when an OSC operation times out."""

    def __init__(self, operation: str, timeout: float):
        """Initialize with operation name and timeout value."""
        self.operation = operation
        self.timeout = timeout
        message = f"Operation '{operation}' timed out after {timeout} seconds"
        super().__init__(message)


class InvalidParameterError(BitwigOSCError):
    """Error when an invalid parameter is provided."""

    def __init__(self, parameter: str, value: any, reason: str):
        """Initialize with parameter name, value and reason."""
        self.parameter = parameter
        self.value = value
        self.reason = reason
        message = f"Invalid parameter '{parameter}' with value '{value}': {reason}"
        super().__init__(message)


class ResourceNotFoundError(BitwigOSCError):
    """Error when a requested resource does not exist."""

    def __init__(self, resource_type: str, identifier: str):
        """Initialize with resource type and identifier."""
        self.resource_type = resource_type
        self.identifier = identifier
        message = f"{resource_type} not found: {identifier}"
        super().__init__(message)


class BitwigNotRespondingError(BitwigOSCError):
    """Error when Bitwig is not responding to OSC messages."""

    def __init__(self, address: Optional[str] = None):
        """Initialize with an optional OSC address."""
        self.address = address
        message = "Bitwig Studio is not responding to OSC messages"
        if address:
            message += f" at address {address}"
        super().__init__(message)


class OSCServerError(BitwigOSCError):
    """Error when the OSC server encounters an issue."""

    def __init__(self, message: str, details: Optional[Exception] = None):
        """Initialize with message and optional exception details."""
        self.details = details
        full_message = message
        if details:
            full_message += f": {str(details)}"
        super().__init__(full_message)


class FeatureNotSupportedError(BitwigOSCError):
    """Error when a feature is not supported by the current Bitwig OSC setup."""

    def __init__(self, feature: str, requirement: Optional[str] = None):
        """Initialize with feature name and optional requirement."""
        self.feature = feature
        self.requirement = requirement
        message = f"Feature not supported: {feature}"
        if requirement:
            message += f". Requires: {requirement}"
        super().__init__(message)
