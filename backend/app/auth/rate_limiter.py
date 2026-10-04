"""Rate Limiter for Authentication Endpoints — APP-26.

Implements APP-26 specification:
- Max 5 failed login attempts per client IP within a 5-minute (300 s) sliding window.
- Exceeding limit returns HTTP 429 Too Many Requests with Retry-After header.
- Successful login clears the failure history for that IP.
"""

from collections import deque
import time
from typing import Dict


class LoginRateLimiter:
    """In-memory sliding window rate limiter for login attempts."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: Dict[str, deque] = {}

    def is_rate_limited(self, ip: str, now: float | None = None) -> tuple[bool, int]:
        """Check if an IP is currently rate-limited.
        
        Returns:
            (is_limited, retry_after_seconds)
        """
        current_time = now if now is not None else time.time()
        timestamps = self._failures.get(ip)
        if not timestamps:
            return False, 0

        # Purge timestamps outside the sliding window
        while timestamps and (current_time - timestamps[0]) > self.window_seconds:
            timestamps.popleft()

        if len(timestamps) >= self.max_failures:
            oldest = timestamps[0]
            retry_after = max(1, int(self.window_seconds - (current_time - oldest)))
            return True, retry_after

        return False, 0

    def record_failure(self, ip: str, now: float | None = None) -> None:
        """Record a failed login attempt for an IP."""
        current_time = now if now is not None else time.time()
        if ip not in self._failures:
            self._failures[ip] = deque()
        self._failures[ip].append(current_time)

    def record_success(self, ip: str) -> None:
        """Clear failures on successful login."""
        if ip in self._failures:
            del self._failures[ip]

    def reset(self) -> None:
        """Reset all rate limiter state (useful for test suites)."""
        self._failures.clear()


# Global login rate limiter instance
login_rate_limiter = LoginRateLimiter(max_failures=5, window_seconds=300)
