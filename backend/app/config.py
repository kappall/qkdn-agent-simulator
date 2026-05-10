import logging

# Service ports and urls
KMS_PORT: int = 8027
KMS_URL: str = "http://127.0.0.1:8027"
AGENT_PORT: int = 8028
AGENT_URL: str = "http://127.0.0.1:8028"

# Core resilience settings
CIRCUIT_BREAKER_THRESHOLD: int = 3
CIRCUIT_BREAKER_RESET_TIMEOUT: int = 30

# Exponential backoff retry settings
BACKOFF_INITIAL_DELAY: float = 1.0
BACKOFF_MULTIPLIER: float = 2.0
BACKOFF_MAX_DELAY: float = 60.0
BACKOFF_MAX_ATTEMPTS: int = 5

# Token bucket rate limiting settings
# Global rate limiter for SDN Agent endpoints
TOKEN_BUCKET_CAPACITY: float = 10.0  # Maximum tokens in bucket
TOKEN_BUCKET_REFILL_RATE: float = 2.0  # Tokens added per second

# Endpoint-specific rate limits
PROVISION_LINK_RATE_LIMIT: float = 5.0  # Max requests per second for provision_link
POLL_LINK_STATUS_RATE_LIMIT: float = 10.0  # Max requests per second for poll_link_status
KMS_STATUS_RATE_LIMIT: float = 20.0  # Max requests per second for KMS status checks

# Logging defaults
LOG_LEVEL: int = logging.DEBUG