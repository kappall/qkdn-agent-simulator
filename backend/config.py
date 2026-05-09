import logging

# Service ports
KMS_PORT: int = 8000
AGENT_PORT: int = 8001

# Core resilience settings
CIRCUIT_BREAKER_THRESHOLD: int = 3
BACKOFF_MAX_DELAY: int = 60
TOKEN_BUCKET_CAPACITY: int = 10
TOKEN_BUCKET_REFILL_RATE: int = 2

# Logging defaults
LOG_LEVEL: int = logging.DEBUG