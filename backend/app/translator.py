import uuid
from typing import Tuple, Dict, Any, Optional


class LinkProvisioningTranslator:
  """Translates high-level provisioning requests to KMS commands."""

  QOS_TO_SLA_MAP = {
    "low": {"sla_level": "normal", "key_rate_multiplier": 1},
    "normal": {"sla_level": "high", "key_rate_multiplier": 2},
    "high": {"sla_level": "critical", "key_rate_multiplier": 5},
  }

  SUPPORTED_QOS_LEVELS = set(QOS_TO_SLA_MAP.keys())

  def validate_request(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a provisioning request payload.
    
    Args:
      payload: Dict with required keys: target_node, qos_level
      Optional keys: duration_seconds, key_rate_required
    
    Returns:
      Tuple of (is_valid: bool, error_message: Optional[str])
    """
    required_fields = ["target_node", "qos_level"]
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
      return False, f"Missing required fields: {', '.join(missing_fields)}"

    target_node = payload.get("target_node")
    if not isinstance(target_node, str) or not target_node.strip():
      return False, "target_node must be a non-empty string"

    qos_level = payload.get("qos_level")
    if qos_level not in self.SUPPORTED_QOS_LEVELS:
      return False, f"Invalid qos_level '{qos_level}'. Supported: {sorted(self.SUPPORTED_QOS_LEVELS)}"

    default_key_rate = 10 * self.QOS_TO_SLA_MAP[qos_level]["key_rate_multiplier"]

    if "duration_seconds" in payload:
      duration = payload["duration_seconds"]
      if not isinstance(duration, int) or duration <= 0:
        return False, "duration_seconds must be a positive integer"

    if "key_rate_required" in payload:
      key_rate = payload["key_rate_required"]
      if isinstance(key_rate, bool) or not isinstance(key_rate, (int, float)) or key_rate <= 0:
        return False, "key_rate_required must be a positive number"
      payload["key_rate_required"] = int(key_rate)
    else:
      payload["key_rate_required"] = default_key_rate

    return True, None

  def map_to_kms_command(
    self,
    request: Dict[str, Any],
    link_id: Optional[str] = None,
  ) -> Dict[str, Any]:
    """
    Maps a high-level provisioning request to KMS link_config command.
    
    Args:
      request: Validated provisioning request
      link_id: Optional link ID; generated if not provided
    
    Returns:
      Dict with KMS link_config payload: link_id, target_node, sla_level, key_rate_required
    """
    if not link_id:
      link_id = f"link-{str(uuid.uuid4())[:8]}"

    qos_level = request["qos_level"]
    sla_config = self.QOS_TO_SLA_MAP[qos_level]

    key_rate_required = int(
      request.get("key_rate_required", 10 * sla_config["key_rate_multiplier"])
    )

    kms_command = {
      "link_id": link_id,
      "target_node": request["target_node"],
      "sla_level": sla_config["sla_level"],
      "key_rate_required": key_rate_required,
    }

    return kms_command
