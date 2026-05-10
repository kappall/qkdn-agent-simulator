import logging

# Service ports and urls
KMS_PORT: int = 8027
KMS_URL: str = "http://127.0.0.1:8027"
AGENT_PORT: int = 8028
AGENT_URL: str = "http://127.0.0.1:8028"

# Core resilience settings
CIRCUIT_BREAKER_THRESHOLD: int = 3
CIRCUIT_BREAKER_RESET_TIMEOUT: int = 30
BACKOFF_MAX_DELAY: int = 60
TOKEN_BUCKET_CAPACITY: int = 10
TOKEN_BUCKET_REFILL_RATE: int = 2

# Logging defaults
LOG_LEVEL: int = logging.DEBUG