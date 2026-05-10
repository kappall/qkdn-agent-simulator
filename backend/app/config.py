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

TOKEN_BUCKET_CAPACITY: int = 10
TOKEN_BUCKET_REFILL_RATE: int = 2

# Logging defaults
LOG_LEVEL: int = logging.DEBUG