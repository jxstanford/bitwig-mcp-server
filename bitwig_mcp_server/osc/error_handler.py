"""
Error Handler for Bitwig OSC integration.

This module provides centralized error handling functions for the OSC integration.
"""

import logging
import time
from typing import Any, Callable, Dict, Set, Tuple

from .exceptions import (
    BitwigOSCError,
    FeatureNotSupportedError,
    InvalidParameterError,
    TimeoutError,
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handles errors and retries for OSC communication."""

    def __init__(self):
        """Initialize the error handler."""
        # Track known Bitwig features and capabilities
        self.supported_features: Set[str] = set()
        self.unsupported_features: Set[str] = set()

        # Keep track of recent errors for diagnostics
        self.recent_errors: Dict[str, Tuple[float, BitwigOSCError]] = {}
        self.max_recent_errors = 10

        # Connection status tracking
        self.connection_status = {
            "last_successful_comm": 0.0,
            "consecutive_timeouts": 0,
            "last_error": None,
        }

    def clear_errors(self) -> None:
        """Clear all tracked errors."""
        self.recent_errors.clear()
        self.connection_status["consecutive_timeouts"] = 0
        self.connection_status["last_error"] = None

    def record_error(self, category: str, error: BitwigOSCError) -> None:
        """Record an error for diagnostics.

        Args:
            category: Error category (e.g., 'transport', 'track', 'device')
            error: The error that occurred
        """
        # Add to recent errors, with timestamp
        self.recent_errors[category] = (time.time(), error)

        # If we have too many errors, remove the oldest one
        if len(self.recent_errors) > self.max_recent_errors:
            oldest_category = min(
                self.recent_errors, key=lambda k: self.recent_errors[k][0]
            )
            self.recent_errors.pop(oldest_category)

        # Update connection status for certain error types
        if isinstance(error, TimeoutError):
            self.connection_status["consecutive_timeouts"] += 1
        else:
            self.connection_status["consecutive_timeouts"] = 0

        self.connection_status["last_error"] = error
        logger.error(f"{category}: {error}")

    def record_success(self) -> None:
        """Record a successful communication."""
        self.connection_status["last_successful_comm"] = time.time()
        self.connection_status["consecutive_timeouts"] = 0

    def check_connection_health(self) -> bool:
        """Check if the connection to Bitwig seems healthy.

        Returns:
            True if the connection seems healthy, False otherwise
        """
        # If we've had more than 3 consecutive timeouts, connection is unhealthy
        if self.connection_status["consecutive_timeouts"] > 3:
            return False

        # If we haven't had a successful communication in 10 seconds, connection is unhealthy
        if (
            self.connection_status["last_successful_comm"] > 0
            and time.time() - self.connection_status["last_successful_comm"] > 10
        ):
            return False

        return True

    def validate_track_index(self, track_index: int, max_tracks: int = 128) -> int:
        """Validate a track index.

        Args:
            track_index: Track index (1-based)
            max_tracks: Maximum track index

        Returns:
            The validated track index

        Raises:
            InvalidParameterError: If the track index is invalid
        """
        if not isinstance(track_index, int):
            raise InvalidParameterError(
                "track_index", track_index, "must be an integer"
            )

        if track_index < 1:
            raise InvalidParameterError(
                "track_index", track_index, "must be at least 1 (1-based indexing)"
            )

        if track_index > max_tracks:
            raise InvalidParameterError(
                "track_index", track_index, f"must be at most {max_tracks}"
            )

        return track_index

    def validate_parameter_index(self, param_index: int, max_params: int = 8) -> int:
        """Validate a parameter index.

        Args:
            param_index: Parameter index (1-based)
            max_params: Maximum parameter index

        Returns:
            The validated parameter index

        Raises:
            InvalidParameterError: If the parameter index is invalid
        """
        if not isinstance(param_index, int):
            raise InvalidParameterError(
                "param_index", param_index, "must be an integer"
            )

        if param_index < 1:
            raise InvalidParameterError(
                "param_index", param_index, "must be at least 1 (1-based indexing)"
            )

        if param_index > max_params:
            raise InvalidParameterError(
                "param_index", param_index, f"must be at most {max_params}"
            )

        return param_index

    def validate_float_value(
        self, name: str, value: float, min_val: float, max_val: float
    ) -> float:
        """Validate a float value within a range.

        Args:
            name: Parameter name
            value: Parameter value
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            The validated value (clamped if outside range)

        Raises:
            InvalidParameterError: If the value is not a number
        """
        if not isinstance(value, (int, float)):
            raise InvalidParameterError(name, value, "must be a number")

        # Clamp the value to the allowed range and warn if outside
        if value < min_val:
            logger.warning(
                f"{name} value {value} below allowed range ({min_val}-{max_val}), clamping to {min_val}"
            )
            return min_val

        if value > max_val:
            logger.warning(
                f"{name} value {value} above allowed range ({min_val}-{max_val}), clamping to {max_val}"
            )
            return max_val

        return value

    def retry_with_timeout(
        self,
        operation: Callable,
        operation_name: str,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        timeout: float = 5.0,
        *args,
        **kwargs,
    ) -> Any:
        """Retry an operation with timeout.

        Args:
            operation: Function to call
            operation_name: Name of the operation (for error reporting)
            max_retries: Maximum number of retries
            retry_delay: Delay between retries
            timeout: Timeout for the operation
            *args: Arguments to pass to the operation
            **kwargs: Keyword arguments to pass to the operation

        Returns:
            The result of the operation

        Raises:
            TimeoutError: If the operation times out
            Exception: Other exceptions raised by the operation
        """
        last_error = None
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                # Check if we've already exceeded the timeout
                if time.time() - start_time > timeout:
                    raise TimeoutError(operation_name, timeout)

                # Calculate remaining timeout
                remaining_timeout = timeout - (time.time() - start_time)

                # Call the operation with a timeout parameter if it accepts one
                if "timeout" in kwargs:
                    kwargs["timeout"] = remaining_timeout

                result = operation(*args, **kwargs)
                self.record_success()
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} for {operation_name} failed: {e}"
                )

                # If we've used up all retries, re-raise the last error
                if attempt == max_retries - 1:
                    if time.time() - start_time > timeout:
                        error = TimeoutError(operation_name, timeout)
                        self.record_error(operation_name, error)
                        raise error
                    else:
                        if isinstance(last_error, BitwigOSCError):
                            self.record_error(operation_name, last_error)
                        raise last_error

                # Otherwise, wait and retry
                time.sleep(retry_delay)

        # This should never happen, but just in case
        raise TimeoutError(operation_name, timeout)

    def check_feature_supported(self, feature: str, requirement: str) -> bool:
        """Check if a feature is supported.

        Args:
            feature: Feature name
            requirement: Requirement for the feature

        Returns:
            True if the feature is supported, False otherwise

        Raises:
            FeatureNotSupportedError: If the feature is known to be unsupported
        """
        # If we know it's supported, return True
        if feature in self.supported_features:
            return True

        # If we know it's not supported, raise an error
        if feature in self.unsupported_features:
            raise FeatureNotSupportedError(feature, requirement)

        # Otherwise, we don't know yet, so return False
        return False

    def mark_feature_supported(self, feature: str) -> None:
        """Mark a feature as supported.

        Args:
            feature: Feature name
        """
        self.supported_features.add(feature)
        self.unsupported_features.discard(feature)

    def mark_feature_unsupported(self, feature: str) -> None:
        """Mark a feature as unsupported.

        Args:
            feature: Feature name
        """
        self.unsupported_features.add(feature)
        self.supported_features.discard(feature)

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get diagnostic information.

        Returns:
            Dictionary with diagnostic information
        """
        return {
            "connection_status": {
                "last_successful_comm": self.connection_status["last_successful_comm"],
                "consecutive_timeouts": self.connection_status["consecutive_timeouts"],
                "last_error": str(self.connection_status["last_error"])
                if self.connection_status["last_error"]
                else None,
                "connection_healthy": self.check_connection_health(),
            },
            "recent_errors": {
                category: {
                    "timestamp": timestamp,
                    "error": str(error),
                }
                for category, (timestamp, error) in self.recent_errors.items()
            },
            "supported_features": list(self.supported_features),
            "unsupported_features": list(self.unsupported_features),
        }
