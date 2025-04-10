import logging

logger = logging.getLogger(__name__)


def log_capacity_warning(factory, current_usage, capacity, action_type="check"):
    """Log capacity warnings and issues"""
    usage_percentage = (current_usage / capacity * 100) if capacity else 100

    if usage_percentage >= 90:
        logger.warning(
            f"CRITICAL: Factory {factory.factory_details.factory_name} at {usage_percentage:.1f}% "
            f"capacity ({current_usage:.1f}/{capacity}kg). Action: {action_type}"
        )
    elif usage_percentage >= 75:
        logger.info(
            f"Warning: Factory {factory.factory_details.factory_name} at {usage_percentage:.1f}% "
            f"capacity ({current_usage:.1f}/{capacity}kg). Action: {action_type}"
        )


def log_capacity_change(factory, old_usage, new_usage, action_type="update"):
    """Log capacity changes"""
    capacity = factory.factory_details.production_capacity
    change = new_usage - old_usage

    logger.info(
        f"Capacity Change: Factory {factory.factory_details.factory_name} - "
        f"Change: {change:+.1f}kg ({old_usage:.1f}->{new_usage:.1f}). "
        f"New usage: {(new_usage / capacity * 100):.1f}%. Action: {action_type}"
    )


def format_capacity_message(current_usage, capacity, available):
    """Format capacity status message"""
    usage_percentage = (current_usage / capacity * 100) if capacity else 100

    if usage_percentage >= 90:
        return {
            "level": "danger",
            "message": f"Storage nearly full! Only {available:.1f}kg remaining.",
            "icon": "exclamation-triangle",
        }
    elif usage_percentage >= 75:
        return {
            "level": "warning",
            "message": f"Storage space getting low. {available:.1f}kg remaining.",
            "icon": "exclamation-circle",
        }
    else:
        return {
            "level": "info",
            "message": f"{available:.1f}kg storage space available.",
            "icon": "info-circle",
        }


def validate_capacity_request(factory, requested_quantity):
    """Validate a capacity request and return detailed response"""
    details = factory.factory_details
    current_usage = details.get_current_capacity_usage()
    capacity = details.production_capacity

    if not capacity:
        return {
            "valid": False,
            "message": "Factory capacity not set.",
            "current_usage": current_usage,
            "requested": requested_quantity,
            "available": 0,
        }

    available = capacity - current_usage
    would_use = current_usage + requested_quantity

    if would_use > capacity:
        log_capacity_warning(factory, would_use, capacity, "request_denied")
        return {
            "valid": False,
            "message": f"Would exceed capacity by {(would_use - capacity):.1f}kg",
            "current_usage": current_usage,
            "requested": requested_quantity,
            "available": available,
        }

    return {
        "valid": True,
        "message": "Capacity available",
        "current_usage": current_usage,
        "requested": requested_quantity,
        "available": available,
    }
