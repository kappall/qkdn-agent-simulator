import logging
import json

from app.config import LOG_LEVEL

class JsonFormatter(logging.Formatter):
  def format(self, record):
    log_record = {
      'timestamp': self.formatTime(record, self.datefmt),
      'level': record.levelname,
      'service': record.name,
      'message': record.getMessage()
    }
    if record.exc_info:
      log_record['traceback'] = self.formatException(record.exc_info)
    return json.dumps(log_record)

def setup_logging(name: str)-> logging.Logger:
  logger = logging.getLogger(name)
  logger.setLevel(LOG_LEVEL)
  if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

  return logger